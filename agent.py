import os
import json
import time
import yaml
from dotenv import load_dotenv

# Load and merge agent configuration from base + dataset-specific files
def load_agent_config():
    """
    Loads base instructions and merges with dataset-specific instructions.
    Dataset is determined by DATASET_NAME environment variable (default: events).
    """
    config = {}
    
    # Load base instructions
    try:
        with open('base_instructions.yaml', 'r') as f:
            config = yaml.safe_load(f) or {}
        print("INFO: Loaded base_instructions.yaml")
    except Exception as e:
        print(f"WARNING: Failed to load base_instructions.yaml: {e}")
    
    # Determine dataset and load dataset-specific config
    dataset_name = os.getenv("DATASET_NAME", "events")
    dataset_path = f"datasets/{dataset_name}.yaml"
    
    try:
        with open(dataset_path, 'r') as f:
            dataset_config = yaml.safe_load(f) or {}
        print(f"INFO: Loaded dataset config: {dataset_path}")
        
        # Merge dataset-specific instructions into base config
        # Single 'instructions' block gets appended to ALL agent types
        dataset_instruction = dataset_config.get('instructions', '')
        
        if dataset_instruction:
            for agent_key in ['get_insights', 'unified_agent', 'deep_analysis']:
                if agent_key in config:
                    # Find the instruction key (system_instruction or instruction)
                    if 'system_instruction' in config[agent_key]:
                        config[agent_key]['system_instruction'] += "\n\n" + dataset_instruction
                    elif 'instruction' in config[agent_key]:
                        config[agent_key]['instruction'] += "\n\n" + dataset_instruction
                        
        # Also expose dataset metadata
        config['_dataset'] = {
            'name': dataset_config.get('name', dataset_name),
            'display_name': dataset_config.get('display_name', dataset_name),
            'looker': dataset_config.get('looker', {})
        }
        
    except Exception as e:
        print(f"WARNING: Failed to load dataset config {dataset_path}: {e}")
    
    return config

AGENT_CONFIG = load_agent_config()

load_dotenv()
import threading
from google.cloud import geminidataanalytics

from google.adk.agents import Agent
from google.adk.tools import agent_tool
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from google.auth import default
from google.auth.transport.requests import Request as gRequest

class AuthTokenManager:
    def __init__(self):
        self._credentials = None
        self.SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

    def get_credentials(self):
        # Force reload if explicit reauth was requested widely or just standard check
        if self._credentials is None:
            self._credentials, _ = default(scopes=self.SCOPES)
        
        try:
             if not self._credentials.valid:
                self._credentials.refresh(gRequest())
        except Exception as e:
             print(f"DEBUG: Credential refresh failed ({e}), reloading from default...")
             # Force reload if refresh fails (e.g. token revoked, file changed)
             self._credentials, _ = default(scopes=self.SCOPES)
             # Try refreshing the new one if needed (though default() usually gives fresh-ish)
             if not self._credentials.valid:
                 self._credentials.refresh(gRequest())
             
        return self._credentials

    def get_auth_token(self) -> str:
        return self.get_credentials().token

# Global instance
auth_manager = AuthTokenManager()
import vertexai
from vertexai.preview import reasoning_engines
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part, ToolConfig

# Configuration - Load Looker config from dataset, with fallback to env vars
dataset_looker = AGENT_CONFIG.get('_dataset', {}).get('looker', {})

# Per-dataset Looker credentials - read env var names from dataset config
_client_id_env = dataset_looker.get('client_id_env', 'LOOKER_CLIENT_ID')
_client_secret_env = dataset_looker.get('client_secret_env', 'LOOKER_CLIENT_SECRET')

LOOKER_CLIENT_ID = os.getenv(_client_id_env) or os.getenv("LOOKER_CLIENT_ID")
LOOKER_CLIENT_SECRET = os.getenv(_client_secret_env) or os.getenv("LOOKER_CLIENT_SECRET")
LOOKER_INSTANCE_URI = dataset_looker.get('instance_uri') or os.getenv("LOOKER_INSTANCE_URI")
LOOKML_MODEL = dataset_looker.get('model') or os.getenv("LOOKML_MODEL", "gaming")
EXPLORE = dataset_looker.get('explore') or os.getenv("EXPLORE", "events")

print(f"INFO: Using Looker instance: {LOOKER_INSTANCE_URI}, model: {LOOKML_MODEL}, explore: {EXPLORE}")
PROJECT_ID = os.getenv("PROJECT_ID", "1094200614711")
if PROJECT_ID == "aragosalooker":
    PROJECT_ID = "1094200614711" # Force numeric ID if default/old string is found
LOCATION = os.getenv("LOCATION", "global")
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket="gs://ca_api",
)


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





# Global client and cached objects to avoid re-init overhead
global_data_chat_client = None
_cached_credentials = None
_cached_datasource_refs = None

def _get_cached_client():
    """Returns cached DataChatServiceClient, creating if needed."""
    global global_data_chat_client
    if global_data_chat_client is None:
        log_debug("Initializing Global DataChatServiceClient...")
        global_data_chat_client = geminidataanalytics.DataChatServiceClient(
            credentials=auth_manager.get_credentials()
        )
    return global_data_chat_client

def _get_cached_datasource():
    """Returns cached datasource references, creating if needed."""
    global _cached_credentials, _cached_datasource_refs
    
    if _cached_datasource_refs is None:
        _cached_credentials = geminidataanalytics.Credentials(
            oauth=geminidataanalytics.OAuthCredentials(
                secret=geminidataanalytics.OAuthCredentials.SecretBased(
                    client_id=LOOKER_CLIENT_ID, client_secret=LOOKER_CLIENT_SECRET
                ),
            )
        )
        
        looker_explore_reference = geminidataanalytics.LookerExploreReference(
            looker_instance_uri=LOOKER_INSTANCE_URI, lookml_model=LOOKML_MODEL, explore=EXPLORE
        )
        
        _cached_datasource_refs = geminidataanalytics.DatasourceReferences(
            looker=geminidataanalytics.LookerExploreReferences(
                explore_references=[looker_explore_reference],
                credentials=_cached_credentials
            ),
        )
    
    return _cached_datasource_refs

def fast_query(question: str, history: list = []):
    """
    Streamlined query function that bypasses ADK agent for fast responses.
    Yields chunks as they arrive for SSE streaming.
    
    Args:
        question: The question to ask
        history: List of conversation messages
        
    Yields:
        dict: Chunks with type (text, data, done) and content
    """
    client = _get_cached_client()
    datasource_refs = _get_cached_datasource()
    
    # Updated system instruction to support explicit chart requests
    system_instruction = "Answer directly with data. Be concise. If the user EXPLICITLY asks for a chart or visualization, prepend the exact string 'SHOW_CHART' to the text part of your response. CRITICAL: When using the `generate_chart` tool, you MUST call it with NO ARGUMENTS (e.g. `generate_chart()`). The tool automatically uses the active data context. If you provide ANY `data_source` argument (like a name or ID), the tool will FAIL."
    
    inline_context = geminidataanalytics.Context(
        system_instruction=system_instruction,
        datasource_references=datasource_refs,
        options=geminidataanalytics.ConversationOptions(
            analysis=geminidataanalytics.AnalysisOptions(
                python=geminidataanalytics.AnalysisOptions.Python(enabled=False)
            )
        ),
    )
    
    messages = []
    
    # Populate history
    # Sort history by timestamp if needed, but assuming list is ordered
    for msg in history:
        role = msg.get('role')
        content = msg.get('content')
        if not content:
            continue
            
        g_msg = geminidataanalytics.Message()
        if role == 'user':
            g_msg.user_message.text = content
            messages.append(g_msg)
        elif role == 'model' or role == 'agent':
            if "DATA_PAYLOAD_JSON: " in content:
                # This message contains a data payload we need to restore
                try:
                    parts = content.split("DATA_PAYLOAD_JSON: ")
                    text_part = parts[0].strip()
                    json_str = parts[1].strip()
                    
                    # 1. If there's significantly substantive text, add it as a separate text message first
                    if text_part:
                         text_msg = geminidataanalytics.Message()
                         text_msg.system_message.text = {'parts': [text_part]}
                         messages.append(text_msg)
                    
                    # 2. Add the Data Message
                    # Robust cleanup: Ensure we only parse valid JSON if there is trailing garbage
                    # Use a loop to try parsing if there are multiple lines? 
                    # Usually json_str is the rest of the string.
                    # If there are newlines within the JSON, standard load works.
                    # The error "Extra data: line 2 column 1" implies there is *another* JSON object or text after the first one.
                    # We will try to parse just the first valid object.
                    try:
                        data_payload = json.loads(json_str)
                    except json.JSONDecodeError as ide:
                        # Fallback: maybe there is extra content after the JSON?
                        # This works if `json.loads` is strict. We can likely ignore the rest.
                        decoder = json.JSONDecoder()
                        data_payload, _ = decoder.raw_decode(json_str)
                    
                    # Fix for "Protocol message DataResult/DataMessage has no 'sql' field"
                    # Structure: SystemMessage (DataMessage) -> result (DataResult) -> data, schema
                    inner_payload = data_payload
                    if 'result' in data_payload:
                         inner_payload = data_payload['result']
                    
                    clean_inner_payload = {}
                    if 'data' in inner_payload:
                        clean_inner_payload['data'] = inner_payload['data']
                    if 'schema' in inner_payload:
                        clean_inner_payload['schema'] = inner_payload['schema']
                    
                    # Try giving it a name?
                    # logic: generate_chart checks active context.
                    clean_inner_payload['name'] = "previous_result" 

                    data_msg = geminidataanalytics.Message()
                    # The SDK expects DataMessage, which has a 'result' field (DataResult), which has 'data'
                    data_msg.system_message.data = {'result': clean_inner_payload}
                    messages.append(data_msg)
                    
                except Exception as e:
                    print(f"Error parsing history data payload: {e}")
                    # Fallback to plain text
                    g_msg.system_message.text = {'parts': [content]} 
                    messages.append(g_msg)
            else:
                # Standard text message
                g_msg.system_message.text = {'parts': [content]} 
                messages.append(g_msg)

    # Append current message with dynamic hint for charts
    final_question = question
    lc_question = question.lower()
    if any(k in lc_question for k in ["chart", "graph", "plot", "visualize"]):
        final_question += " (IMPORTANT SYSTEM INSTRUCTION: Call `generate_chart()` with NO arguments. Do NOT provide a name. Do NOT provide an ID. Just `generate_chart()`.)"

    current_msg = geminidataanalytics.Message()
    current_msg.user_message.text = final_question
    messages.append(current_msg)
    
    request = geminidataanalytics.ChatRequest(
        inline_context=inline_context,
        parent=f"projects/{PROJECT_ID}/locations/global",
        messages=messages,
    )
    
    
    # Retry loop for handling "DataResult not found" errors caused by model hallucination
    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            stream = client.chat(request=request)
            
            for item in stream:
                kind = item._pb.WhichOneof("kind")
                
                if kind == "system_message":
                    message_dict = geminidataanalytics.SystemMessage.to_dict(item.system_message)
                    
                    if "text" in message_dict:
                        # text is a dict with 'parts' array containing the actual text
                        text_data = message_dict["text"]
                        if isinstance(text_data, dict) and "parts" in text_data:
                            text_content = " ".join(text_data["parts"])
                        elif isinstance(text_data, str):
                            text_content = text_data
                        else:
                            text_content = str(text_data)
                        yield {"type": "text", "content": text_content}
                    elif "data" in message_dict:
                        data = message_dict["data"]
                        result = data.get("result", {})
                        
                        # Fallback URL logic
                        if 'explore_url' not in result:
                            try:
                                fields = [f['name'] for f in result.get('schema', {}).get('fields', []) if 'name' in f]
                                if fields:
                                    fields_str = ",".join(fields)
                                    base_uri = LOOKER_INSTANCE_URI.rstrip('/')
                                    # Simple fallback URL
                                    result['explore_url'] = f"{base_uri}/explore/{LOOKML_MODEL}/{EXPLORE}?fields={fields_str}&toggle=dat,pik,vis"
                            except Exception:
                                pass

                        yield {
                            "type": "data",
                            "content": {
                                "rows": result.get("data", []),  # data is array of flat objects
                                "schema": result.get("schema", {}),
                                "sql": result.get("sql", ""),
                                "explore_url": result.get("explore_url", ""),
                            }
                        }
                    elif "chart" in message_dict:
                         yield {"type": "chart", "content": message_dict["chart"]}
            
            yield {"type": "done", "content": None}
            break # Success, exit retry loop
            
        except Exception as e:
            error_str = str(e)
            if "DataResult not found" in error_str and attempt < max_retries:
                print(f"DEBUG: Caught DataResult error: {error_str}. Retrying with correction...")
                
                # Append a correction message to the history
                correction_msg = geminidataanalytics.Message()
                correction_msg.user_message.text = "SYSTEM ERROR: You called `generate_chart()` with an argument. This is FORBIDDEN. You MUST call it with NO arguments (e.g. `generate_chart()`) to use the current data context. Try again immediately with NO arguments."
                messages.append(correction_msg)
                
                # Update request with new messages
                request = geminidataanalytics.ChatRequest(
                    inline_context=inline_context,
                    parent=f"projects/{PROJECT_ID}/locations/global",
                    messages=messages,
                )
                continue # Retry
            else:
                yield {"type": "error", "content": error_str}
                break


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
 
    global global_data_chat_client
    if global_data_chat_client is None:
        log_debug("Initializing Global DataChatServiceClient...")
        global_data_chat_client = geminidataanalytics.DataChatServiceClient(
            credentials=auth_manager.get_credentials()
        )
    data_chat_client = global_data_chat_client

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

    system_instruction = AGENT_CONFIG.get('get_insights', {}).get('system_instruction', """You are a specialized AI data analyst...""")

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
    log_thought("Entering Deep Analysis Mode (Gemini 3.0 Pro)...")
    
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
    
    analysis_tools = Tool(
        function_declarations=[get_insights_func]
    )

    # Initialize the model
    model = GenerativeModel(
        "gemini-3-flash-preview",
        tools=[analysis_tools],
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO,
            )
        ),
        system_instruction=AGENT_CONFIG.get('deep_analysis', {}).get('system_instruction', """You are a Senior Data Analyst. The user has a complex request.
        Your goal is to provide a comprehensive analysis by breaking down the problem, asking multiple questions to Looker AND the Knowledge Base, and synthesizing the results.

        CRITICAL OUTPUT FORMATTING:
        When presenting key metrics or comparisons, do NOT just write text. Use the special JSON block format below so the interface renders them as beautiful UI cards.

        For Single Metrics:
        ```json-metric
        { "label": "Retention Rate", "value": "45%", "trend": "+5%", "description": "Day 1 Retention for iOS" }
        ```

        For Comparisons (Use multiple blocks or a list):
        ```json-metric
        [
          { "label": "iOS Session", "value": "14m", "description": "Avg Duration" },
          { "label": "Android Session", "value": "11m", "description": "Avg Duration" }
        ]
        ```

        Always intersperse these blocks with your analysis text.
        """)
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
    try:
        # We need to consume the generator here since tools must return a value, not a generator
        for chunk in run_deep_analysis(question):
            content = chunk.get('content', {})
            parts = content.get('parts', [])
            for part in parts:
                text = part.get('text', '')
                if text:
                    full_report += text
    except Exception as e:
        return f"Error during deep analysis execution: {str(e)}"

    if not full_report:
        return "Deep analysis completed but produced no final report. Please try refining your question."

    return full_report

# Visualization Agent
visualization_agent = Agent(
    model="gemini-3-flash-preview",
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



unified_agent = Agent(
    model="gemini-3-flash-preview",
    name="UnifiedAnalyticsAgent",
    instruction=AGENT_CONFIG.get('unified_agent', {}).get('instruction', """You are an expert mobile gaming data analyst..."""),
    tools=[
        get_insights,
        perform_deep_analysis,

        # Wrap the sub-agent as a tool
        agent_tool.AgentTool(agent=visualization_agent)
    ],
)

# MCP Agent for Looker Toolbox (create dashboards, analyze LookML, etc.)
mcp_agent = None
mcp_app = None

try:
    mcp_toolset = MCPToolset(
        connection_params=StdioConnectionParams(
            command="./toolbox",
            args=["--stdio", "--prebuilt", "looker"],
            env={
                "LOOKER_BASE_URL": LOOKER_INSTANCE_URI,
                "LOOKER_CLIENT_ID": LOOKER_CLIENT_ID,
                "LOOKER_CLIENT_SECRET": LOOKER_CLIENT_SECRET,
                "LOOKER_VERIFY_SSL": "true",
            }
        )
    )
    
    mcp_agent = Agent(
        model="gemini-3-flash-preview",
        name="LookerToolboxAgent",
        instruction="""You are a Looker admin assistant with access to Looker Toolbox via MCP.
        
You have access to powerful tools to interact with Looker:

**Model & Query Tools:**
- get_models, get_explores, get_dimensions, get_measures
- query (run queries), query_sql, query_url

**Content Tools:**
- make_dashboard (create dashboards), add_dashboard_element, add_dashboard_filter
- make_look (create Looks), run_look, run_dashboard
- get_dashboards, get_looks, generate_embed_url

**LookML Authoring:**
- get_projects, get_project_files, get_project_file
- create_project_file, update_project_file, delete_project_file
- dev_mode (activate dev mode)

**Health Tools:**
- health_pulse, health_analyze, health_vacuum

When asked to create content, use the appropriate tools and return the URL.
Always be helpful and explain what you're doing.""",
        tools=[mcp_toolset],
    )
    
    mcp_app = reasoning_engines.AdkApp(
        agent=mcp_agent,
        enable_tracing=False,
    )
    print("INFO: MCP Looker Toolbox agent initialized successfully")
except Exception as e:
    print(f"WARNING: Failed to initialize MCP Agent: {e}")

# vertexai.init is moved to the entry point (chat.py or deploy.py)
# to avoid hardcoding the staging bucket in the remote environment.

# Create the main App (unified agent)
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

# Export both apps for server.py to route between them
def get_agent_app(agent_type="fast"):
    """Returns the appropriate agent app based on type."""
    if agent_type == "mcp" and mcp_app:
        return mcp_app
    return app
