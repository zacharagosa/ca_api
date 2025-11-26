import os
from google.cloud import geminidataanalytics
from google.adk.agents import Agent
from google.adk.tools import agent_tool
import google.auth
import google.auth.transport.requests
import vertexai
from vertexai.preview import reasoning_engines

# Configuration - In a real app, use environment variables
LOOKER_CLIENT_ID = os.getenv("LOOKER_CLIENT_ID", "9cR2K4JdGYjZCBCm6HGs")
LOOKER_CLIENT_SECRET = os.getenv("LOOKER_CLIENT_SECRET", "8YP9CWFVhdzxF2dvPsyJhQdR")
LOOKER_INSTANCE_URI = os.getenv("LOOKER_INSTANCE_URI", "https://3417a175-fe20-4370-974f-2f2b535340ab.looker.app")
LOOKML_MODEL = "gaming"
EXPLORE = "events"
PROJECT_ID = "aragosalooker"
LOCATION = "us-central1"

import queue
thought_queue = queue.Queue()

def log_thought(message):
    """Logs a thought to the queue for the frontend to consume."""
    print(f"Logging thought: {message}")
    thought_queue.put(message)

def get_insights(question: str):
    """Queries the Conversational Analytics API using a question as input.

    Use this tool to generate the data for data insights.

    Args:
        question: The question to post to the API.

    Returns:
        A dictionary containing the status of the operation and the insights from
        the API, categorized by type (e.g., text_insights, data_insights) to make
        the output easier for an LLM to understand and process.
    """

    data_chat_client = geminidataanalytics.DataChatServiceClient()

    credentials = geminidataanalytics.Credentials(
        oauth=geminidataanalytics.OAuthCredentials(
            secret=geminidataanalytics.OAuthCredentials.SecretBased(
                client_id=LOOKER_CLIENT_ID, client_secret=LOOKER_CLIENT_SECRET
            ),
        )
    )

    looker_explore_reference = geminidataanalytics.LookerExploreReference(
        looker_instance_uri=LOOKER_INSTANCE_URI, lookml_model=LOOKML_MODEL, explore=EXPLORE
    )

    # Connect to your Looker datasource
    datasource_references = geminidataanalytics.DatasourceReferences(
        looker=geminidataanalytics.LookerExploreReferences(
            explore_references=[looker_explore_reference],
            credentials=credentials 
        ),
    )

    system_instruction = "You are a specialized AI data analyst for a mobile gaming company. Your primary function is to answer natural language questions from a user by constructing and executing precise queries against a Looker instance."

    # Context set-up for 'Chat using Inline Context'
    inline_context = geminidataanalytics.Context(
        system_instruction=system_instruction,
        datasource_references=datasource_references,
        options=geminidataanalytics.ConversationOptions(
            analysis=geminidataanalytics.AnalysisOptions(
                python=geminidataanalytics.AnalysisOptions.Python(
                    enabled=False
                )
            )
        ),
    )

    messages = [geminidataanalytics.Message()]
    messages[0].user_message.text = question

    request = geminidataanalytics.ChatRequest(
        inline_context=inline_context,
        parent=f"projects/{PROJECT_ID}/locations/global",
        messages=messages,
    )

    log_thought(f"Analyzing question: {question}")
    
    # Make the request
    try:
        log_thought("Querying Looker data...")
        stream = data_chat_client.chat(request=request)
    except Exception as e:
        log_thought(f"Error querying data: {e}")
        raise e

    # Categorize insights from the stream for a more descriptive output
    text_insights = []
    schema_insights = []
    data_insights = []

    log_thought("Processing results...")
    for item in stream:
        if item._pb.WhichOneof("kind") == "system_message":
            message_dict = geminidataanalytics.SystemMessage.to_dict(
                item.system_message
            )
            if "text" in message_dict:
                text_insights.append(message_dict["text"])
            elif "schema" in message_dict:
                schema_insights.append(message_dict["schema"])
            elif "data" in message_dict:
                # IMPORTANT: The agent needs the 'data' list inside the result
                # message_dict['data'] is the wrapper. 
                # message_dict['data']['result']['data'] is the actual list of rows.
                # We should pass the whole wrapper so the agent can see metadata, but verify it's correct.
                data_insights.append(message_dict["data"])
                
                # Extract and log the SQL query if available
                result_data = message_dict['data'].get('result', {})
                if 'sql' in result_data:
                     log_thought(f"Generated SQL: {result_data['sql']}")
                
                # Check for Explore URL
                if 'explore_url' in result_data:
                    url = result_data['explore_url']
                    log_thought(f"Explore URL found: {url}")
                    # We won't append to text_insights here to avoid messing up the data flow for now.
                    # The agent might be getting confused if text_insights has mixed content.
                else:
                     # Fallback if SQL isn't directly exposed, or just log fields
                     pass

    # Build a descriptive response dictionary that is easier for the LLM to parse
    response = {"status": "success"}
    if text_insights:
        response["text_insights"] = text_insights
    if schema_insights:
        response["schema_insights"] = schema_insights
    if data_insights:
        response["data_insights"] = data_insights

    return response

# Agent to get data insights
data_agent = Agent(
    model="gemini-2.5-pro",
    name="DataAgent",
    description="Retrieves raw data from Looker based on user questions.",
    instruction="""You are an agent that retrieves raw data. The tool 'get_insights' queries a governed semantic layer.
    Your task is to call the 'get_insights' tool with the user's question.
    From the tool's dictionary output, find the 'data_insights' list. Within that list, find the dictionary that contains a 'result' key.
    Extract the list of records from the 'data' key which is inside 'result'.
    
    CRITICAL: You MUST return this list of records as a JSON string. 
    
    Example output format:
    [{"date": "2023-01-01", "revenue": 100}, {"date": "2023-01-02", "revenue": 150}]
    
    Do not add any other text, markdown formatting, or summarization. Just the raw JSON string.
    """,
    tools=[get_insights],
)

# Visualization Agent
visualization_agent = Agent(
    model="gemini-2.5-pro",
    name="VisualizationAgent",
    description="Tool that generates the specific JSON configuration required for rendering charts. Use this whenever the user asks for a visualization or the data represents a trend.",
    instruction="""You are a data visualization expert. Your task is to take raw data (in JSON format) and a user question, and generate a JSON configuration for a Recharts chart.
    
    The output must be a valid JSON object with the following structure:
    {
        "type": "bar" | "line" | "pie" | "area",
        "title": "Chart Title",
        "xAxisKey": "key_for_x_axis",
        "data": [ ... the data array ... ],
        "series": [
            { "dataKey": "key_for_series_1", "name": "Series 1 Name", "fill": "#8884d8" },
            ...
        ]
    }
    
    Choose the most appropriate chart type for the data.
    - Use "line" for trends over time.
    - Use "bar" for categorical comparisons.
    - Use "pie" for parts of a whole (only if few categories).
    
    IMPORTANT: 
    1. You MUST use the actual data provided in the input. Do NOT use placeholder data.
    2. Map the `xAxisKey` and `dataKey` exactly to the keys present in the `data` array.
    3. Return ONLY the JSON string. Do not add markdown formatting or explanations.
    """
)

# ... (rest of the file)

root_agent = Agent(
    model="gemini-2.5-pro",
    name="RootAgent",
    instruction="""You are a helpful mobile gaming data analyst.
    
    Your goal is to answer user questions about their game data.
    
    1.  **Use the `get_insights` tool** to retrieve data from Looker.
    2.  **Analyze the tool output**:
        -   Look for `data_insights` which contains the actual query results.
        -   Look for `text_insights` for any additional context or SQL queries.
    3.  **Answer the question**:
        -   The `get_insights` tool will return a JSON string of data.
        -   **Step 1**: Parse this JSON string to ensure it is valid data.
        -   **Step 2**: **ALWAYS** output the data as a Markdown table.
            -   If it's a single value, make a one-row table.
            -   If it's multiple rows, make a full table.
        -   **Step 3**: If the data has multiple rows (e.g. time series, categories), **YOU MUST CALL** the `VisualizationAgent` tool.
            -   Pass the data JSON to `VisualizationAgent` and wait for its response.
        -   **Step 4**: Output the JSON returned by `VisualizationAgent` in a code block with the language `json-chart`.
        -   **Step 5**: Add a brief summary.
        
    4.  **Formatting**:
        -   **CRITICAL**: You MUST output the data table.
        -   **CRITICAL**: For charts, use the `json-chart` language tag.
          Example:
          ```json-chart
          { ... json from VisualizationAgent ... }
          ```
    
    5.  **Important**:
        -   Do NOT hallucinate data. Use ONLY what is returned by the tools.
        -   If the user asks for a chart, you MUST use the `VisualizationAgent`.
    """,
    tools=[
        get_insights, 
        # Wrap the sub-agent as a tool
        agent_tool.AgentTool(agent=visualization_agent)
    ],
)

# vertexai.init is moved to the entry point (chat.py or deploy.py)
# to avoid hardcoding the staging bucket in the remote environment.

# Create the App
app = reasoning_engines.AdkApp(
    agent=root_agent,
    enable_tracing=False,
)
