import os
import json
import time
from dotenv import load_dotenv

load_dotenv()
import threading
from google.cloud import geminidataanalytics
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core.client_options import ClientOptions
from google.adk.agents import Agent
from google.adk.tools import agent_tool
import google.auth
import vertexai
from vertexai.preview import reasoning_engines
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part, ToolConfig

# Configuration - In a real app, use environment variables
LOOKER_CLIENT_ID = os.getenv("LOOKER_CLIENT_ID")
LOOKER_CLIENT_SECRET = os.getenv("LOOKER_CLIENT_SECRET")
LOOKER_INSTANCE_URI = os.getenv("LOOKER_INSTANCE_URI")
LOOKML_MODEL = os.getenv("LOOKML_MODEL", "gaming")
EXPLORE = os.getenv("EXPLORE", "events")
PROJECT_ID = os.getenv("PROJECT_ID", "aragosalooker")
LOCATION = os.getenv("LOCATION", "us-central1")
DATA_STORE_ID = os.getenv("DATA_STORE_ID", "gaming-knowledge") # Default to a placeholder

import queue
from concurrent.futures import ThreadPoolExecutor
thought_queue = None

def log_debug(message):
    """Logs a debug message to Cloud Logging only."""
    print(f"DEBUG: {message}")

def log_thought(message):
    """Logs a thought to the queue for the frontend to consume."""
    print(f"Logging thought: {message}")
    if thought_queue:
        thought_queue.put(message)

# Thread-local storage for request-scoped data (like user tokens)
_thread_local = threading.local()

def set_access_token(token):
    """Sets the Looker access token for the current thread."""
    _thread_local.access_token = token

def get_access_token():
    """Gets the Looker access token for the current thread."""
    return getattr(_thread_local, 'access_token', None)

def search_knowledge_base(query: str):
    """Searches the internal knowledge base (e.g., PDFs, Wiki, Reddit) for context.

    Use this tool to get qualitative information, industry trends, or game mechanics info
    that isn't in the Looker database.

    Args:
        query: The search query string.

    Returns:
        A list of search results with titles, snippets, and links.
    """
    log_thought(f"Searching Knowledge Base for: {query}")
    try:
        # Use ClientOptions to specify the location
        client_options = (
            ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
            if LOCATION != "global"
            else None
        )

        client = discoveryengine.SearchServiceClient(client_options=client_options)

        serving_config = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/dataStores/{DATA_STORE_ID}/servingConfigs/default_search"

        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=5,
            content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                    return_snippet=True
                )
            )
        )

        response = client.search(request)

        results = []
        for result in response.results:
            item = {}
            if hasattr(result.document, 'derived_struct_data'):
                 item['title'] = result.document.derived_struct_data.get('title', 'No Title')
                 item['link'] = result.document.derived_struct_data.get('link', '')
                 # Handle snippets
                 snippets = []
                 if hasattr(result.document, 'derived_struct_data'):
                     snippets_data = result.document.derived_struct_data.get('snippets', [])
                     for s in snippets_data:
                         snippets.append(s.get('snippet', ''))
                 item['snippet'] = " ... ".join(snippets)
            results.append(item)

        log_thought(f"Found {len(results)} results from Knowledge Base.")
        return results

    except Exception as e:
        log_thought(f"Error searching knowledge base: {e}")
        return [{"error": str(e), "message": "Could not retrieve knowledge base results."}]


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

    # Always use service account Looker credentials as we are using Google Sign-In for app auth
    log_debug("Using service account Looker credentials.")
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

    system_instruction = """You are a specialized AI data analyst for a mobile gaming company. Your primary function is to answer natural language questions from a user by constructing and executing precise queries against a Looker instance.
    
    When you generate a response with data, you MUST include a JSON block with type `json-metadata` containing the query details (filters, sorts, fields) AND the generated SQL query in a field named `sql`.
    """

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

    log_thought("Executing Looker Query (this may take a moment)...")
    
    # Iterate through the stream
    t_start_stream = time.time()
    first_chunk_received = False
    
    for i, item in enumerate(stream):
        if not first_chunk_received:
            log_thought(f"Time to First Chunk: {time.time() - t_start_stream:.2f}s")
            first_chunk_received = True
            
        kind = item._pb.WhichOneof("kind")
        log_debug(f"Stream Chunk {i} Kind: {kind}")
        
        if kind == "system_message":
            message_dict = geminidataanalytics.SystemMessage.to_dict(
                item.system_message
            )
            log_debug(f"Chunk {i} Content Keys: {list(message_dict.keys())}")
            
            if "text" in message_dict:
                log_debug(f"Chunk {i} Text: {message_dict['text']}")
                text_insights.append(message_dict["text"])
            elif "schema" in message_dict:
                log_debug(f"Chunk {i} Schema: {message_dict['schema']}")
                schema_insights.append(message_dict["schema"])
            elif "data" in message_dict:
                log_debug(f"Chunk {i} Data: {message_dict['data']}")
                data_insights.append(message_dict["data"])
                
                # Extract and log the SQL query if available
                result_data = message_dict['data'].get('result', {})
                if 'sql' in result_data:
                     log_debug(f"Generated SQL: {result_data['sql']}")
                
                # Check for Explore URL
                if 'explore_url' in result_data:
                    url = result_data['explore_url']
                else:
                    try:
                        # Fallback: Generate URL from schema fields
                        fields = [f['name'] for f in result_data.get('schema', {}).get('fields', []) if 'name' in f]
                        
                        if fields:
                            fields_str = ",".join(fields)
                            base_uri = LOOKER_INSTANCE_URI.rstrip('/')
                            fallback_url = f"{base_uri}/explore/{LOOKML_MODEL}/{EXPLORE}?fields={fields_str}&toggle=dat,pik,vis"
                            
                            # Inject into result_data
                            result_data['explore_url'] = fallback_url
                    except Exception as e:
                        log_debug(f"Error generating fallback URL: {e}")
                        pass
        elif kind == "tool_use":
             log_debug(f"Chunk {i} Tool Use: {item.tool_use}")
             pass
        elif kind == "tool_output":
             log_debug(f"Chunk {i} Tool Output: {item.tool_output}")
             pass
    
    # Wait for stream to complete
    log_thought(f"Stream Consumption Complete. Total Stream Time: {time.time() - t_start_stream:.2f}s")
    log_thought("Stream processing complete.")
    log_debug(f"Data Insights Chunks: {len(data_insights)}")

    # Post-process data_insights to merge chunks
    t_post_process = time.time()
    merged_data = {}
    try:
        for d in data_insights:
            for k, v in d.items():
                merged_data[k] = v
        
        # Robust serialization
        def json_default(obj):
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            return str(obj)
            
        merged_data = json.loads(json.dumps(merged_data, default=json_default))
        log_debug("Merged data serialization successful.")
        
        # Rename keys in rows using field labels for better formatting
        if 'result' in merged_data and 'schema' in merged_data['result'] and 'rows' in merged_data['result']:
            try:
                fields = merged_data['result']['schema'].get('fields', [])
                field_map = {}
                for f in fields:
                    # Prefer label, then title, then name
                    # Looker API usually provides 'title' or 'label_short' or 'label'
                    label = f.get('label_short') or f.get('label') or f.get('title') or f.get('name')
                    if 'name' in f:
                        field_map[f['name']] = label
                
                if field_map:
                    new_rows = []
                    for row in merged_data['result']['rows']:
                        new_row = {}
                        for k, v in row.items():
                            new_row[field_map.get(k, k)] = v
                        new_rows.append(new_row)
                    merged_data['result']['rows'] = new_rows
                    log_debug("Renamed row keys using field labels.")
            except Exception as e:
                log_debug(f"Error renaming keys: {e}")
        
    except Exception as e:
        log_thought(f"Error merging/serializing data: {e}")
        merged_data = {} 

    except Exception as e:
        log_thought(f"Error merging/serializing data: {e}")
        merged_data = {} 
        
    log_thought(f"Local Post-Processing Time: {time.time() - t_post_process:.2f}s")

    # Build a descriptive response dictionary
    response = {"status": "success"}
    
    # Helper for other insights
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(v) for v in obj]
        elif hasattr(obj, 'to_dict'):
            return make_serializable(obj.to_dict())
        elif hasattr(obj, '__dict__'):
            return make_serializable(obj.__dict__)
        else:
            return obj

    if text_insights:
        response["text_insights"] = make_serializable(text_insights)
    if schema_insights:
        response["schema_insights"] = make_serializable(schema_insights)
    if merged_data:
        response["data_insights"] = [merged_data]
        
        # Log summary of the data
        try:
            data_keys = list(merged_data.keys())
            log_debug(f"Final Merged Data Keys: {data_keys}")
            if 'result' in merged_data:
                result_keys = list(merged_data['result'].keys())
                log_debug(f"Result Keys: {result_keys}")
                if 'data' in merged_data['result']:
                    data_len = len(merged_data['result']['data'])
                    log_thought(f"Data Rows Count: {data_len}")
                    if data_len > 0:
                        log_debug(f"First Row Sample: {merged_data['result']['data'][0]}")
        except Exception as e:
            log_debug(f"Error logging summary: {e}")

    return response

def run_deep_analysis(question: str):
    """Runs a deep analysis using a planning agent loop."""
    log_thought("Entering Deep Analysis Mode (Gemini 2.5)...")
    
    # Define the tool for the LLM
    # Initialize the model
    # Define the tool for the LLM
    get_insights_func = FunctionDeclaration(
        name="get_insights",
        description="Queries Looker for data insights based on a natural language question.",
        parameters={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The natural language question to ask Looker."
                }
            },
            "required": ["question"]
        }
    )
    
    search_kb_func = FunctionDeclaration(
        name="search_knowledge_base",
        description="Searches the internal knowledge base for qualitative context.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query."
                }
            },
            "required": ["query"]
        }
    )

    analysis_tools = Tool(
        function_declarations=[get_insights_func, search_kb_func]
    )

    # Initialize the model
    model = GenerativeModel(
        "gemini-2.5-pro",
        tools=[analysis_tools],
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO,
            )
        ),
        system_instruction="""You are a Senior Data Analyst. The user has a complex request.
        Your goal is to provide a comprehensive analysis by breaking down the problem, asking multiple questions to Looker AND the Knowledge Base, and synthesizing the results.

        **Available Tools:**
        - `get_insights(question)`: Queries the SQL database (Looker). Use for quantitative data (metrics, trends).
        - `search_knowledge_base(query)`: Searches external docs/web. Use for qualitative context (e.g. "Why is X trending?", "What is the industry standard?").
        
        Process:
        1. Understand the user's high-level goal.
        2. Formulate a plan.
        3. Execute tool calls. **CRITICAL: Execute multiple tools in parallel** to save time.
        4. Analyze the returned data.
        5. Synthesize a final report.
        
        **PERFORMANCE TIP:**
        - It is much faster to run ONE complex query than multiple simple ones.
        - If you suspect you might need a breakdown (e.g., by Country), include it in the initial query (e.g., "Group by Platform AND Country"). You can always aggregate the data yourself to answer the high-level question.
        - You can output multiple `get_insights` calls in a single turn to run them in parallel.

        **CRITICAL OUTPUT REQUIREMENTS:**

        1. **Evidence & Links:**
           - For every key finding, you MUST cite the source data.
           - The `get_insights` tool returns an `explore_url` in the `data_insights`. You MUST include this as a link: `[View Source Query](explore_url)`.
           
        2. **Visualizations:**
           - You MUST generate charts to visualize trends or comparisons.
           - To create a chart, output a JSON code block (```json) containing the chart configuration.
           - The JSON structure MUST be:
             {
               "type": "bar" | "line" | "pie",
               "title": "Chart Title",
               "xAxisKey": "category_column",
               "stacked": true/false,
               "data": [{"category_column": "Value", "series1": 10, "series2": 20}, ...],
               "series": [{"dataKey": "series1", "name": "Series 1", "fill": "#8884d8", "yAxisID": "left" | "right"}, ...]
             }
           - Ensure data is pivoted correctly for the chart (one row per X-axis value).
           - **Dual Axis**: If comparing two measures with different scales (e.g., Revenue vs Session Length), assign one series `"yAxisID": "right"`.
           
        3. **Report Structure:**
           - **Executive Summary**: High-level answer.
           - **Detailed Analysis**:
             - **Finding 1**: Description.
               - *Chart*: (Insert JSON block here)
               - *Source*: [View Source Query](url)
             - **Finding 2**: ...
        """
    )
    
    chat = model.start_chat()
    
    try:
        t0 = time.time()
        response = chat.send_message(question)
        log_thought(f"Initial Plan Generated in {time.time() - t0:.2f}s")
        
        # Loop for tool calls (max 5 turns to prevent infinite loops)
        for _ in range(5):
            candidate = response.candidates[0]
            
            # Collect all function calls from all parts
            function_calls = []
            text_parts = []
            
            for part in candidate.content.parts:
                if part.function_call:
                    function_calls.append(part.function_call)
                elif part.text:
                    text_parts.append(part.text)

            if function_calls:
                log_thought(f"Deep Analysis: Executing {len(function_calls)} tool call(s)...")
                
                # Execute tools in parallel
                with ThreadPoolExecutor() as executor:
                    # Create a list of futures
                    futures = []
                    for fn in function_calls:
                        log_debug(f"Tool Call: {fn.name}, Args: {fn.args}")
                        if fn.name == "get_insights":
                            # get_insights expects 'question', but the model might call it with 'query' or 'question'
                            # The tool definition for get_insights has 'question'.
                            question_arg = fn.args.get("question") or fn.args.get("query")
                            if not question_arg:
                                # Fallback if neither is present (shouldn't happen with correct schema)
                                question_arg = list(fn.args.values())[0] if fn.args else ""
                                
                            futures.append(executor.submit(get_insights, question_arg))
                        elif fn.name == "search_knowledge_base":
                            query_arg = fn.args.get("query")
                            if not query_arg:
                                query_arg = list(fn.args.values())[0] if fn.args else ""
                            futures.append(executor.submit(search_knowledge_base, query_arg))
                        else:
                            log_debug(f"Unknown tool: {fn.name}")
                            futures.append(None) # Handle unknown tools if necessary

                    # Collect results
                    tool_responses = []
                    for i, future in enumerate(futures):
                        fn = function_calls[i]
                        if future:
                            try:
                                result = future.result()
                                tool_responses.append(
                                    Part.from_function_response(
                                        name=fn.name,
                                        response={"content": result}
                                    )
                                )
                            except Exception as e:
                                tool_responses.append(
                                    Part.from_function_response(
                                        name=fn.name,
                                        response={"content": f"Error: {str(e)}"}
                                    )
                                )
                        else:
                             # Unknown tool
                             pass
                
                log_thought("Synthesizing findings...")
                t_synth = time.time()
                response = chat.send_message(tool_responses)
                log_thought(f"Synthesis/Next Step Generated in {time.time() - t_synth:.2f}s")
                
            elif text_parts:
                # Text response (Final answer)
                # Combine all text parts
                full_text = "".join(text_parts)
                yield {'content': {'parts': [{'text': full_text}]}}
                break
            else:
                # No content?
                break
    except Exception as e:
        log_thought(f"Deep Analysis Error: {e}")
        yield {'content': {'parts': [{'text': f"An error occurred during deep analysis: {e}"}]}}

def perform_deep_analysis(question: str):
    """Performs a deep, multi-step analysis for complex questions.
    
    Use this tool when the user asks for:
    - Comparisons (e.g., "Compare X vs Y", "Analyze performance of A vs B")
    - Root cause analysis (e.g., "Why did revenue drop?")
    - Multi-dimensional breakdowns (e.g., "Break down by Country AND Platform")
    - Open-ended exploration (e.g., "Find the top opportunities")
    
    Args:
        question: The complex user question to analyze.
        
    Returns:
        A comprehensive markdown report with charts and data.
    """
    full_report = ""
    # We need to consume the generator here since tools must return a value, not a generator
    for chunk in run_deep_analysis(question):
        content = chunk.get('content', {})
        parts = content.get('parts', [])
        for part in parts:
            text = part.get('text', '')
            if text:
                full_report += text
    return full_report

# Visualization Agent
visualization_agent = Agent(
    model="gemini-2.5-pro",
    name="VisualizationAgent",
    description="Tool that generates the specific JSON configuration required for rendering charts. Use this whenever the user asks for a visualization or the data represents a trend.",
    instruction="""You are a data visualization expert. Your task is to take raw data (in JSON format) and a user question, and generate a JSON configuration for a Chart.js chart.
    
    The output must be a valid JSON object with the following structure:
    {
        "type": "bar" | "line" | "pie",
        "title": "Chart Title",
        "xAxisKey": "key_for_x_axis",
        "stacked": true | false,
        "data": [ ... the data array ... ],
        "series": [
            { "dataKey": "key_for_series_1", "name": "Series 1 Name", "fill": "#8884d8" },
            ...
        ]
    }
    
    **Handling Data Pivoting (CRITICAL):**
    Raw data often comes in "long" format (e.g., one row per date-category combination). 
    Chart.js requires "wide" format (one row per date, with columns for each category).
    
    If the data has 2 dimensions (e.g., Date and Country) and 1 measure (e.g., Revenue):
    1.  **Pivot the Data**: Transform the array so each X-axis value (Date) appears only once.
    2.  **Create Columns**: The values of the second dimension (Country) become new keys in the object.
        -   Input: `[{"date": "Jan", "country": "US", "rev": 100}, {"date": "Jan", "country": "UK", "rev": 50}]`
        -   Output Data: `[{"date": "Jan", "US": 100, "UK": 50}]`
    3.  **Generate Series**: Create a series for each unique value of the second dimension.
        -   Series: `[{"dataKey": "US", "name": "US"}, {"dataKey": "UK", "name": "UK"}]`
    
    **Stacking vs Grouping (CRITICAL):**
    -   **Stacked (`"stacked": true`)**: Use ONLY for **Additive** measures (e.g., Total Revenue, Total Sessions, Total Installs) where the sum of the series equals the total.
    -   **Grouped (`"stacked": false`)**: Use for **Non-Additive** measures (e.g., Averages, Rates, Ratios, DAU, ARPU, Retention). Stacking these makes no sense.
    
    **Handling Dual Axes:**
    If the chart compares two measures with different scales (e.g., "Revenue" in millions vs "Sessions" in thousands, or "Count" vs "Percentage"):
    1.  Assign the primary measure to the left axis (default).
    2.  Assign the secondary measure to the right axis by adding `"yAxisID": "right"` to its series object.
    
    Choose the most appropriate chart type for the data.
    - Use "line" for trends over time.
    - Use "area" (line chart with fill) for stacked trends over time (e.g. Stacked Revenue by Platform).
    - Use "bar" for categorical comparisons (Stacked or Grouped).
    - Use "pie" for parts of a whole (only if few categories).
    - Use "scatter" for correlation analysis (e.g. Ad Spend vs Revenue) where both axes are numeric.
    - Use "combo" for mixing types (e.g. Bar for Revenue, Line for ROI). For combo charts, specify "type": "bar" or "line" inside each series object.

    **Styling:**
    - For Area charts, set `"fill": true` in the series object.
    
    IMPORTANT: 
    1. You MUST use the actual data provided in the input. Do NOT use placeholder data.
    2. Map the `xAxisKey` and `dataKey` exactly to the keys present in the `data` array.
    3. Return ONLY the JSON string. Do not add markdown formatting or explanations.
    """
)

# ... (rest of the file)

# ... (rest of the file)

unified_agent = Agent(
    model="gemini-2.5-pro",
    name="UnifiedAnalyticsAgent",
    instruction="""You are an expert mobile gaming data analyst.
    
    Your goal is to answer user questions about their game data by choosing the best approach:
    
    **DECISION LOGIC:**
    1.  **IF** the question is simple, direct, or asks for a specific metric (e.g., "What is the DAU?", "Show me revenue by country"), **USE `get_insights`**.
    2.  **IF** the question is complex, requires comparison, root cause analysis, or multi-step reasoning (e.g., "Compare iOS vs Android", "Why is retention dropping?", "Analyze the impact of X"), **USE `perform_deep_analysis`**.
    
    **PATH A: Simple Queries (`get_insights`)**
    1.  Call `get_insights`.
    2.  Output the data as a Markdown table.
    3.  If appropriate, call `VisualizationAgent` to generate a chart.
    4.  Output the chart JSON in a `json-chart` block.
    5.  Output the `explore_url` as `LINK: <url>`.
    6.  Output metadata in `json-metadata`.
    
    **PATH B: Deep Analysis (`perform_deep_analysis`)**
    1.  Call `perform_deep_analysis`.
    2.  Return the output EXACTLY as provided by the tool. Do not summarize or modify it, as it already contains the full report, charts, and links.
    
    **General Rules:**
    -   Always be helpful and professional.
    -   Do not hallucinate data.
    """,
    tools=[
        get_insights,
        perform_deep_analysis,
        search_knowledge_base,
        # Wrap the sub-agent as a tool
        agent_tool.AgentTool(agent=visualization_agent)
    ],
)

# vertexai.init is moved to the entry point (chat.py or deploy.py)
# to avoid hardcoding the staging bucket in the remote environment.

# Create the App
try:
    app = reasoning_engines.AdkApp(
        agent=unified_agent,
        enable_tracing=False,
    )
except Exception as e:
    print(f"WARNING: Failed to initialize Vertex AI Agent: {e}")
    # Fallback/Dummy app for when credentials are missing (e.g., in CI/CD or sandbox)
    class DummyApp:
        def query(self, *args, **kwargs):
            return {"output": "Agent could not be initialized due to missing credentials."}
    app = DummyApp()
