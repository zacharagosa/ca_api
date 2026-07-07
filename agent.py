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
    
    Architecture:
    - common: Shared constraints applied to ALL agents
    - fast_mode: Operational rules for fast agent
    - deep_mode: Operational rules for deep agent
    - dataset: Domain knowledge from datasets/{name}.yaml
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
    
    dataset_instruction = ""
    try:
        with open(dataset_path, 'r') as f:
            dataset_config = yaml.safe_load(f) or {}
        print(f"INFO: Loaded dataset config: {dataset_path}")
        
        # New split instructions
        looker_inst = dataset_config.get('looker_instructions', '')
        spanner_inst = dataset_config.get('spanner_instructions', '')
        
        # Backward compatibility
        legacy_inst = dataset_config.get('instructions', '')
        
        if looker_inst or spanner_inst:
            dataset_instruction = f"""
### DATASET RULES

**FOR ANALYTICS (Tool: get_insights)**:
{looker_inst}

**FOR GRAPH (Tool: query_spanner)**:
{spanner_inst}
"""
        else:
            dataset_instruction = legacy_inst
        
        # Expose dataset metadata
        config['_dataset'] = {
            'name': dataset_config.get('name', dataset_name),
            'display_name': dataset_config.get('display_name', dataset_name),
            'looker': dataset_config.get('looker', {}),
            'spanner': dataset_config.get('spanner', {})
        }
    except Exception as e:
        print(f"WARNING: Failed to load dataset config {dataset_path}: {e}")
    
    # helper to safely get nested keys
    def get_inst(section, key='system_instruction'):
        return config.get(section, {}).get(key, '')

    # Build Computed Instructions
    # 1. Common constraints (Model rules + Analysis rules)
    common_instruction = get_inst('common', 'model_constraints') + "\n\n" + get_inst('common', 'analysis_rules')
    
    # 2. Fast Mode = Common + Fast Mode Operational + Dataset
    fast_final = f"{common_instruction}\n\n{get_inst('fast_mode')}\n\n{dataset_instruction}"
    
    # 3. Deep Mode = Common + Deep Mode Operational + Dataset
    deep_final = f"{common_instruction}\n\n{get_inst('deep_mode')}\n\n{dataset_instruction}"
    
    # 4. Unified Agent (Legacy/Router) = Use existing instruction block but append dataset
    unified_final = get_inst('unified_agent', 'instruction') + "\n\n" + dataset_instruction

    # Store computed instructions
    config['_computed'] = {
        'fast_mode': fast_final,
        'deep_mode': deep_final,
        'unified_agent': unified_final
    }
    print("DEBUG: Final Deep Mode Instruction:\n", deep_final[:500] + "..." + deep_final[-500:])
    
    # Substitute placeholders in all computed instructions with actual Looker config values
    looker_config = config.get('_dataset', {}).get('looker', {})
    model_name = looker_config.get('model') or os.getenv("LOOKML_MODEL", "gaming")
    explore_name = looker_config.get('explore') or os.getenv("EXPLORE", "events")
    
    for key in ['fast_mode', 'deep_mode', 'unified_agent']:
        config['_computed'][key] = config['_computed'][key].replace(
            '{LOOKML_MODEL}', model_name
        ).replace(
            '{EXPLORE}', explore_name
        )
    
    return config

AGENT_CONFIG = load_agent_config()

load_dotenv()
import threading
# from google.cloud import geminidataanalytics
from google.api_core import client_options as client_options_lib

from google.adk.agents import Agent
from google.adk.tools import agent_tool
# from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
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
import random

def retry_api_call(func, retries=3, delay=1, backoff=2, jitter=0.1, error_msg="API call failed"):
    """
    Retries a function call with exponential backoff and jitter.
    Useful for handling transient network errors or dropped connections.
    """
    last_exception = None
    for attempt in range(retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            error_str = str(e)
            # Check for fatal errors where retry assumes no value (e.g. invalid argument)
            # But "connection" or "pool" errors are always worth retrying
            is_connection_error = any(k in error_str for k in ["Connection", "RemoteDisconnected", "503", "504", "429", "Resource exhausted"])
            
            if not is_connection_error and attempt < retries:
                # If it's NOT a clear connection error, we might still want to retry for unknown glitches,
                # but maybe be more conservative? For now, we retry generic exceptions too as Vertex can be flaky.
                pass

            if attempt < retries:
                sleep_time = (delay * (backoff ** attempt)) + (random.random() * jitter)
                print(f"WARNING: {error_msg} (Attempt {attempt+1}/{retries}). Retrying in {sleep_time:.2f}s... Error: {error_str[:100]}...")
                time.sleep(sleep_time)
            
    raise last_exception


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

# Spanner Config
dataset_spanner = AGENT_CONFIG.get('_dataset', {}).get('spanner', {})
SPANNER_PROJECT_ID = dataset_spanner.get('project_id')
SPANNER_INSTANCE_ID = dataset_spanner.get('instance_id')
SPANNER_DATABASE_ID = dataset_spanner.get('database_id')

if SPANNER_INSTANCE_ID:
    print(f"INFO: Spanner configured: {SPANNER_PROJECT_ID}/{SPANNER_INSTANCE_ID}/{SPANNER_DATABASE_ID}")

print(f"INFO: Using Looker instance: {LOOKER_INSTANCE_URI}, model: {LOOKML_MODEL}, explore: {EXPLORE}")
PROJECT_ID = os.getenv("PROJECT_ID", "1094200614711")
if PROJECT_ID == "aragosalooker":
    PROJECT_ID = "1094200614711" # Force numeric ID if default/old string is found
LOCATION = os.getenv("LOCATION", "global")

# GA API: Regional endpoint support for data residency compliance
CA_API_LOCATION = os.getenv("CA_API_LOCATION", "global")

def _build_ca_api_endpoint(location: str) -> str:
    """Builds the correct CA API endpoint URL based on location.
    
    Supports:
    - 'global' -> geminidataanalytics.googleapis.com
    - Regional (e.g. 'us-east4') -> geminidataanalytics-{location}.googleapis.com
    - Multi-regional (e.g. 'eu', 'us') -> geminidataanalytics.{location}.rep.googleapis.com
    """
    if location == "global" or not location:
        return "geminidataanalytics.googleapis.com"
    elif location in ("eu", "us"):
        # Multi-regional endpoints
        return f"geminidataanalytics.{location}.rep.googleapis.com"
    else:
        # Regional endpoints (e.g. us-east4, europe-west1)
        return f"geminidataanalytics-{location}.googleapis.com"

CA_API_ENDPOINT = _build_ca_api_endpoint(CA_API_LOCATION)
print(f"INFO: CA API endpoint: {CA_API_ENDPOINT} (location: {CA_API_LOCATION})")

try:
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket="gs://ca_api",
    )
    print("INFO: Vertex AI initialized successfully")
except Exception as e:
    print(f"WARNING: Vertex AI initialization failed: {e}")


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
_cached_agent_service_client = None
_cached_credentials = None
_cached_datasource_refs = None
_cached_context_authoring = None  # Cached glossary terms + example queries

def _get_ca_client_options():
    """Returns client_options configured for the correct CA API endpoint."""
    return client_options_lib.ClientOptions(api_endpoint=CA_API_ENDPOINT)

def _get_cached_client():
    """Returns cached DataChatServiceClient, creating if needed."""
    global global_data_chat_client
    from google.cloud import geminidataanalytics
    if global_data_chat_client is None:
        log_debug(f"Initializing DataChatServiceClient (endpoint: {CA_API_ENDPOINT})...")
        global_data_chat_client = geminidataanalytics.DataChatServiceClient(
            credentials=auth_manager.get_credentials(),
            client_options=_get_ca_client_options()
        )
    return global_data_chat_client

def _get_agent_service_client():
    """Returns cached DataAgentServiceClient for managed agent CRUD operations."""
    global _cached_agent_service_client
    from google.cloud import geminidataanalytics
    if _cached_agent_service_client is None:
        log_debug(f"Initializing DataAgentServiceClient (endpoint: {CA_API_ENDPOINT})...")
        _cached_agent_service_client = geminidataanalytics.DataAgentServiceClient(
            credentials=auth_manager.get_credentials(),
            client_options=_get_ca_client_options()
        )
    return _cached_agent_service_client


# --- Context Authoring: Glossary Terms & Example Queries (GA Feature) ---

def _load_context_authoring():
    """Loads glossary terms and example queries from the dataset config.
    
    GA API Feature: Context authoring gives the API's model domain-specific
    grounding context natively — more effective than system instruction hacks.
    """
    global _cached_context_authoring
    from google.cloud import geminidataanalytics
    
    if _cached_context_authoring is not None:
        return _cached_context_authoring
    
    dataset_name = os.getenv("DATASET_NAME", "events")
    dataset_path = f"datasets/{dataset_name}.yaml"
    
    glossary_terms = []
    example_queries = []
    
    try:
        with open(dataset_path, 'r') as f:
            dataset_config = yaml.safe_load(f) or {}
        
        # Load glossary terms
        raw_glossary = dataset_config.get('glossary', [])
        for item in raw_glossary:
            if isinstance(item, dict) and 'term' in item:
                gt = geminidataanalytics.GlossaryTerm(
                    display_name=item['term'],
                    description=item.get('definition', '')
                )
                glossary_terms.append(gt)
        
        if glossary_terms:
            print(f"INFO: Loaded {len(glossary_terms)} glossary terms for context authoring")
        
        # Load verified/example questions
        raw_examples = dataset_config.get('verified_questions', [])
        for item in raw_examples:
            if isinstance(item, dict) and 'question' in item:
                eq = geminidataanalytics.ExampleQuery(
                    natural_language_question=item['question'],
                    sql_query=item.get('sql', '')
                )
                example_queries.append(eq)
        
        if example_queries:
            print(f"INFO: Loaded {len(example_queries)} verified questions for context authoring")
    
    except Exception as e:
        print(f"WARNING: Could not load context authoring from {dataset_path}: {e}")
    
    _cached_context_authoring = {
        'glossary_terms': glossary_terms,
        'example_queries': example_queries if example_queries else None
    }
    return _cached_context_authoring


# --- Managed Agent CRUD (GA Feature: DataAgentServiceClient) ---

def create_data_agent(display_name: str, description: str = ""):
    """Creates a new managed data agent synchronously."""
    from google.cloud import geminidataanalytics
    client = _get_agent_service_client()
    
    agent = geminidataanalytics.DataAgent(
        display_name=display_name,
        description=description,
    )
    
    request = geminidataanalytics.CreateDataAgentRequest(
        parent=f"projects/{PROJECT_ID}/locations/{CA_API_LOCATION}",
        data_agent=agent,
    )
    
    operation = client.create_data_agent(request=request)
    result = operation.result()  # Synchronous wait
    log_debug(f"Created data agent: {result.name}")
    return result

def list_data_agents():
    """Lists all data agents in the project."""
    client = _get_agent_service_client()
    from google.cloud import geminidataanalytics
    
    request = geminidataanalytics.ListDataAgentsRequest(
        parent=f"projects/{PROJECT_ID}/locations/{CA_API_LOCATION}",
    )
    
    agents = []
    for agent in client.list_data_agents(request=request):
        agents.append({
            'name': agent.name,
            'display_name': agent.display_name,
            'description': agent.description,
            'create_time': agent.create_time.isoformat() if agent.create_time else None,
            'update_time': agent.update_time.isoformat() if agent.update_time else None,
        })
    return agents

def list_accessible_data_agents():
    """Lists all data agents accessible to the current user (including shared agents)."""
    client = _get_agent_service_client()
    from google.cloud import geminidataanalytics
    
    request = geminidataanalytics.ListAccessibleDataAgentsRequest(
        parent=f"projects/{PROJECT_ID}/locations/{CA_API_LOCATION}",
    )
    
    agents = []
    for agent in client.list_accessible_data_agents(request=request):
        agents.append({
            'name': agent.name,
            'display_name': agent.display_name,
            'description': agent.description,
            'create_time': agent.create_time.isoformat() if agent.create_time else None,
        })
    return agents

def get_data_agent(agent_id: str):
    """Gets details of a specific data agent."""
    client = _get_agent_service_client()
    from google.cloud import geminidataanalytics
    
    agent_name = agent_id if '/' in agent_id else f"projects/{PROJECT_ID}/locations/{CA_API_LOCATION}/dataAgents/{agent_id}"
    request = geminidataanalytics.GetDataAgentRequest(name=agent_name)
    
    agent = client.get_data_agent(request=request)
    return {
        'name': agent.name,
        'display_name': agent.display_name,
        'description': agent.description,
        'create_time': agent.create_time.isoformat() if agent.create_time else None,
        'update_time': agent.update_time.isoformat() if agent.update_time else None,
    }

def delete_data_agent(agent_id: str):
    """Deletes a data agent."""
    client = _get_agent_service_client()
    from google.cloud import geminidataanalytics
    
    agent_name = agent_id if '/' in agent_id else f"projects/{PROJECT_ID}/locations/{CA_API_LOCATION}/dataAgents/{agent_id}"
    request = geminidataanalytics.DeleteDataAgentRequest(name=agent_name)
    
    client.delete_data_agent(request=request)
    log_debug(f"Deleted data agent: {agent_name}")
    return True


# --- Server-Side Conversation Management (GA Feature) ---

def delete_ca_conversation(conversation_id: str):
    """Deletes a conversation from the CA API server-side."""
    from google.cloud import geminidataanalytics
    client = _get_cached_client()
    
    conv_name = conversation_id if '/' in conversation_id else f"projects/{PROJECT_ID}/locations/{CA_API_LOCATION}/conversations/{conversation_id}"
    request = geminidataanalytics.DeleteConversationRequest(name=conv_name)
    
    client.delete_conversation(request=request)
    log_debug(f"Deleted CA conversation: {conv_name}")
    return True

def list_ca_conversations():
    """Lists conversations from the CA API."""
    from google.cloud import geminidataanalytics
    client = _get_cached_client()
    
    request = geminidataanalytics.ListConversationsRequest(
        parent=f"projects/{PROJECT_ID}/locations/{CA_API_LOCATION}",
    )
    
    conversations = []
    for conv in client.list_conversations(request=request):
        conversations.append({
            'name': conv.name,
            'create_time': conv.create_time.isoformat() if conv.create_time else None,
            'last_used_time': conv.last_used_time.isoformat() if conv.last_used_time else None,
        })
    return conversations

def _get_cached_datasource():
    """Returns cached datasource references, creating if needed."""
    global _cached_credentials, _cached_datasource_refs
    from google.cloud import geminidataanalytics
    
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
    from google.cloud import geminidataanalytics
    client = _get_cached_client()
    datasource_refs = _get_cached_datasource()
    
    # Updated system instruction to support explicit chart requests
    system_instruction = AGENT_CONFIG.get('_computed', {}).get('fast_mode', '')
    if not system_instruction:
         # Fallback if config failed loading
         print("WARNING: Fast mode instruction missing, using fallback.")
         system_instruction = "Answer directly with data. Be concise."
    
    # GA Feature: Load context authoring (glossary terms + example queries)
    context_authoring = _load_context_authoring()
    
    context_kwargs = {
        'system_instruction': system_instruction,
        'datasource_references': datasource_refs,
        'options': geminidataanalytics.ConversationOptions(
            analysis=geminidataanalytics.AnalysisOptions(
                python=geminidataanalytics.AnalysisOptions.Python(enabled=False)
            )
        ),
    }
    
    # Add glossary terms if available
    if context_authoring.get('glossary_terms'):
        context_kwargs['glossary_terms'] = context_authoring['glossary_terms']
    
    # Add example queries if available
    if context_authoring.get('example_queries'):
        context_kwargs['example_queries'] = context_authoring['example_queries']
    
    inline_context = geminidataanalytics.Context(**context_kwargs)
    
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
        final_question += " (IMPORTANT SYSTEM INSTRUCTION: You MUST print the exact string `SHOW_CHART` on a new line at the end of your response. Do NOT try to generate Python code. Do NOT try to call `generate_chart()`. JUST print `SHOW_CHART`.)"

    current_msg = geminidataanalytics.Message()
    current_msg.user_message.text = final_question
    messages.append(current_msg)
    
    request = geminidataanalytics.ChatRequest(
        inline_context=inline_context,
        parent=f"projects/{PROJECT_ID}/locations/global",
        messages=messages,
    )
    
    
    # Retry loop for handling "DataResult not found" errors caused by model hallucination
    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            stream = client.chat(request=request)
            
            for item in stream:
                kind = item._pb.WhichOneof("kind")
                
                if kind == "system_message":
                    message_dict = geminidataanalytics.SystemMessage.to_dict(item.system_message)
                    
                    if "text" in message_dict:
                        # GA API: Use proper TextMessage.TextType enum instead of hardcoded ints
                        # FINAL_RESPONSE=1, THOUGHT=2 (step-by-step reasoning), PROGRESS=3
                        text_data = message_dict["text"]
                        text_type_raw = text_data.get("text_type", 0) if isinstance(text_data, dict) else 0
                        
                        # Map raw int to enum for clarity
                        try:
                            text_type = geminidataanalytics.TextMessage.TextType(text_type_raw)
                        except ValueError:
                            text_type = geminidataanalytics.TextMessage.TextType.TEXT_TYPE_UNSPECIFIED
                        
                        if isinstance(text_data, dict) and "parts" in text_data:
                            text_content = " ".join(text_data["parts"])
                        elif isinstance(text_data, str):
                            text_content = text_data
                        else:
                            text_content = str(text_data)
                        
                        # Route based on TextType enum
                        if text_type == geminidataanalytics.TextMessage.TextType.THOUGHT:
                            yield {"type": "thought", "content": text_content}
                        elif text_type == geminidataanalytics.TextMessage.TextType.PROGRESS:
                            # PROGRESS = step-by-step reasoning updates (GA feature: Streaming Thoughts)
                            yield {"type": "thought", "content": text_content}
                        else:
                            # FINAL_RESPONSE or TEXT_TYPE_UNSPECIFIED → treat as final answer
                            yield {"type": "text", "content": text_content}
                    
                    elif "schema" in message_dict:
                        # API v2: Schema now comes as separate chunks - skip for now
                        # Could be used to validate data later
                        log_debug(f"Received schema chunk: {len(message_dict.get('schema', {}).get('fields', []))} fields")
                        continue
                    
                    elif "data" in message_dict:
                        data = message_dict["data"]
                        
                        # API v2: Data now streams in TWO chunks:
                        # Chunk 1: {"data": {"query": {...}}} - query definition
                        # Chunk 2: {"data": {"result": {...}}} - actual data
                        
                        # Skip query-only chunks (no result data)
                        if "query" in data and "result" not in data:
                            log_debug(f"Received query chunk: {data['query'].get('name', 'unnamed')}")
                            continue
                        
                        result = data.get("result", {})
                        
                        # Skip if no actual data rows
                        if not result.get("data"):
                            log_debug("Skipping data chunk with no rows")
                            continue
                        
                        # Fallback URL logic (sql and explore_url no longer provided in v2)
                        if 'explore_url' not in result:
                            try:
                                fields = [f['name'] for f in result.get('schema', {}).get('fields', []) if 'name' in f]
                                if fields:
                                    fields_str = ",".join(fields)
                                    base_uri = LOOKER_INSTANCE_URI.rstrip('/')
                                    result['explore_url'] = f"{base_uri}/explore/{LOOKML_MODEL}/{EXPLORE}?fields={fields_str}&toggle=dat,pik,vis"
                            except Exception:
                                pass

                        yield {
                            "type": "data",
                            "content": {
                                "rows": result.get("data", []),
                                "schema": result.get("schema", {}),
                                "sql": result.get("sql", ""),  # May be empty in v2
                                "explore_url": result.get("explore_url", ""),
                            }
                        }
                    
                    elif "chart" in message_dict:
                        chart = message_dict["chart"]
                        
                        # GA API: Chart streams in TWO chunks:
                        # Chunk 1: {"chart": {"query": {...}}} - chart request
                        # Chunk 2: {"chart": {"result": {"vega_config": {...}}}} - chart config
                        
                        # Skip query-only chunks
                        if "query" in chart and "result" not in chart:
                            log_debug(f"Received chart query chunk")
                            continue
                        
                        # Only yield when we have the result with vega_config
                        if "result" in chart:
                            yield {"type": "chart", "content": chart["result"]}
                    
                    elif "error" in message_dict:
                        # GA Feature: Disambiguation handling
                        # When the model is unsure about user intent, it returns
                        # clarifying questions/options in the error message
                        error_data = message_dict["error"]
                        error_msg = ""
                        if isinstance(error_data, dict):
                            error_msg = error_data.get("message", str(error_data))
                            # Check if this is a disambiguation response
                            suggestions = error_data.get("suggestions", [])
                            if suggestions:
                                yield {
                                    "type": "disambiguation",
                                    "content": {
                                        "message": error_msg,
                                        "options": suggestions
                                    }
                                }
                                continue
                        else:
                            error_msg = str(error_data)
                        
                        log_debug(f"Received error message: {error_msg}")
                        yield {"type": "error", "content": error_msg}
                    
                    elif "example_queries" in message_dict:
                        # GA Feature: The API may suggest example queries
                        log_debug(f"Received example queries suggestion from API")
                        continue
            
            yield {"type": "done", "content": None}
            break # Success, exit retry loop
            
        except Exception as e:
            error_str = str(e)
            
            # Handle Rate Limits (429)
            if ("429" in error_str or "Resource exhausted" in error_str) and attempt < max_retries:
                wait_time = 2 ** (attempt + 1) # 2s, 4s, 8s, 16s
                print(f"WARNING: Resource exhausted (429). Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue

            # Handle Looker Hallucinations
            elif "DataResult not found" in error_str and attempt < max_retries:
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
            
            elif "CHART_GENERATION" in error_str and attempt < max_retries:
                print(f"DEBUG: Caught CHART_GENERATION error: {error_str}. Retrying without chart generation...")
                
                # Append a correction message to disable chart generation for this turn
                correction_msg = geminidataanalytics.Message()
                correction_msg.user_message.text = "SYSTEM ERROR: Chart generation failed. Rerun the exact same query to get the data, but DO NOT call `generate_chart()`. Just return the text and data table."
                messages.append(correction_msg)
                
                # Update request with new messages
                request = geminidataanalytics.ChatRequest(
                    inline_context=inline_context,
                    parent=f"projects/{PROJECT_ID}/locations/global",
                    messages=messages,
                )
                continue # Retry
            
            elif "datasource(s) not found" in error_str.lower() and attempt < max_retries:
                print(f"DEBUG: Caught datasource not found error: {error_str}. Retrying with model constraint...")
                
                # Append a correction message forcing correct model usage
                correction_msg = geminidataanalytics.Message()
                correction_msg.user_message.text = f"SYSTEM ERROR: You attempted to query a non-existent datasource. You MUST ONLY use the '{LOOKML_MODEL}' LookML model and the '{EXPLORE}' explore. DO NOT reference 'thelook_ecommerce' or any other model. Rerun your query using ONLY fields from '{EXPLORE}.*'."
                messages.append(correction_msg)
                
                # Update request with new messages
                request = geminidataanalytics.ChatRequest(
                    inline_context=inline_context,
                    parent=f"projects/{PROJECT_ID}/locations/global",
                    messages=messages,
                )
                continue # Retry
                yield {"type": "error", "content": error_str}
                break

# Spanner Caching
_cached_spanner_database = None

def _get_cached_spanner_database():
    global _cached_spanner_database
    if _cached_spanner_database is None:
        try:
            log_debug("Initializing Spanner Connection...")
            from google.cloud import spanner
            client = spanner.Client(project=SPANNER_PROJECT_ID, credentials=auth_manager.get_credentials())
            instance = client.instance(SPANNER_INSTANCE_ID)
            _cached_spanner_database = instance.database(SPANNER_DATABASE_ID)
            log_debug("Spanner Connection Initialized.")
        except Exception as e:
            log_debug(f"Spanner Connection Failed: {e}")
            raise e
    return _cached_spanner_database

import queue

# Global queue for side-channel data events (e.g., graph data from inside tools)
# Must be initialized by the server/caller
data_queue = None

def query_spanner(sql: str):
    """Executes a SQL or Graph Query Language (SQL/PGQ) query on the configured Spanner database.
    
    **CRITICAL TOOL SELECTION RULES:**
    - **ALWAYS USE THIS TOOL** for questions about **CLANS**, **FRIENDS**, **SOCIAL CONNECTIONS**, or **ITEM TRADES**.
    - **NEVER USE get_insights** for "Clan" or "Friend" questions. Looker does NOT have this data.
    - If the user asks about "DragonSlayers" (a clan), you MUST use this tool.
    
    Args:
        sql: The SQL or GQL query to execute.
    
    Returns:
        A dictionary containing the query results (list of rows as dicts).
    """
    if not SPANNER_INSTANCE_ID or not SPANNER_DATABASE_ID:
        return {"error": "Spanner is not configured for this dataset."}
        
    try:
        t_start = time.time()
        log_thought(f"Executing Spanner Query: {sql}")
        
        # Report query details via data_queue if available
        if data_queue:
            try:
                data_queue.put({"type": "json_utils", "data": {"type": "query_details", "sql": sql, "source": "Spanner Graph"}})
            except Exception:
                pass
        
        database = _get_cached_spanner_database()
        
        with database.snapshot() as snapshot:
            results = snapshot.execute_sql(sql)
            
            rows = []
            columns = []
            
            for row in results:
                row_dict = {}
                if not columns and results.fields:
                    columns = [f.name for f in results.fields]
                
                if columns:
                    for i, val in enumerate(row):
                        row_dict[columns[i]] = val
                else:
                    row_dict = {f"col_{i}": val for i, val in enumerate(row)}
                
                rows.append(row_dict)
                
        elapsed = time.time() - t_start
        log_thought(f"Spanner Query returned {len(rows)} rows in {elapsed:.2f}s.")
        
        # Check for graph data and emit if present
        graph_data = extract_graph_from_rows(rows)
        if graph_data:
            log_thought(f"Graph Data Detected: {len(graph_data['nodes'])} nodes, {len(graph_data['links'])} links")
            if data_queue:
                data_queue.put({"type": "graph", "content": graph_data})
            else:
                log_debug("Graph data detected but data_queue is not initialized. Visualization will not be sent.")

        return {"data": rows}
        
    except Exception as e:
        error_msg = f"Spanner Query Failed: {e}"
        log_thought(error_msg)
        return {"error": error_msg}


def extract_graph_from_rows(rows):
    """Heuristic to extract graph nodes/links from SQL rows.
    
    Handles multiple relationship types per row:
    - Clan membership (player -> clan)
    - Friendships (player <-> player)
    - Items (player -> item)
    """
    if not isinstance(rows, list) or not rows:
        return None
        
    nodes = {}
    links = []
    link_set = set()  # Avoid duplicate links
    
    def add_link(source, target, link_type='default'):
        """Add a link if it doesn't already exist."""
        key = (source, target, link_type)
        reverse_key = (target, source, link_type)
        if key not in link_set and reverse_key not in link_set:
            link_set.add(key)
            links.append({'source': source, 'target': target, 'type': link_type})
    
    for row in rows:
        # Standardize keys to lowercase for easier matching
        row_lower = {k.lower(): v for k, v in row.items()}
        
        # === CLAN MEMBERSHIP RELATIONSHIPS ===
        # Check for clan info in the row and add clan-player links
        
        # ID-based clan membership
        if 'player_id' in row and 'clan_id' in row:
            player_id = row['player_id']
            clan_id = row['clan_id']
            player_label = row.get('gamertag') or row.get('player_name') or str(player_id)
            clan_label = row.get('clan_name') or str(clan_id)
            
            nodes[f"clan:{clan_id}"] = {'id': f"clan:{clan_id}", 'group': 'Clan', 'label': clan_label}
            nodes[f"player:{player_id}"] = {'id': f"player:{player_id}", 'group': 'Player', 'label': player_label}
            add_link(f"player:{player_id}", f"clan:{clan_id}", 'membership')
        
        # Name-based clan membership (when IDs not present)
        elif 'clan_name' in row_lower and ('gamertag' in row_lower or 'player_name' in row_lower or 'player' in row_lower):
            clan_name = row_lower['clan_name']
            player_name = row_lower.get('gamertag') or row_lower.get('player_name') or row_lower.get('player')
            
            if clan_name and player_name:
                clan_id = f"clan:{clan_name}"
                player_id = f"player:{player_name}"
                
                nodes[clan_id] = {'id': clan_id, 'group': 'Clan', 'label': clan_name}
                nodes[player_id] = {'id': player_id, 'group': 'Player', 'label': player_name}
                add_link(player_id, clan_id, 'membership')
        
        # === FRIENDSHIP RELATIONSHIPS ===
        # These use 'if' not 'elif' so we can capture friendships even if clan was already captured
        
        # ID-based friendships (initiator/acceptor)
        if 'initiator_id' in row and 'acceptor_id' in row:
            init_id = row['initiator_id']
            acc_id = row['acceptor_id']
            init_label = row.get('initiator_gamertag') or row.get('initiator_name') or str(init_id)
            acc_label = row.get('acceptor_gamertag') or row.get('acceptor_name') or str(acc_id)
            
            nodes[f"player:{init_id}"] = {'id': f"player:{init_id}", 'group': 'Player', 'label': init_label}
            nodes[f"player:{acc_id}"] = {'id': f"player:{acc_id}", 'group': 'Player', 'label': acc_label}
            add_link(f"player:{init_id}", f"player:{acc_id}", 'friendship')
        
        # gamertag + friend_gamertag pattern
        if 'gamertag' in row_lower and 'friend_gamertag' in row_lower:
            p1 = row_lower['gamertag']
            p2 = row_lower['friend_gamertag']
            
            if p1 and p2:
                id1 = f"player:{p1}"
                id2 = f"player:{p2}"
                nodes[id1] = {'id': id1, 'group': 'Player', 'label': p1}
                nodes[id2] = {'id': id2, 'group': 'Player', 'label': p2}
                add_link(id1, id2, 'friendship')
        
        # player + friend pattern (GQL return)
        if 'player' in row_lower and 'friend' in row_lower:
            p1 = row_lower['player']
            p2 = row_lower['friend']
            
            if p1 and p2:
                id1 = f"player:{p1}"
                id2 = f"player:{p2}"
                nodes[id1] = {'id': id1, 'group': 'Player', 'label': p1}
                nodes[id2] = {'id': id2, 'group': 'Player', 'label': p2}
                add_link(id1, id2, 'friendship')
        
        # player_1 + player_2 pattern
        if 'player_1' in row_lower and 'player_2' in row_lower:
            p1 = row_lower['player_1']
            p2 = row_lower['player_2']
            
            if p1 and p2:
                id1 = f"player:{p1}"
                id2 = f"player:{p2}"
                nodes[id1] = {'id': id1, 'group': 'Player', 'label': p1}
                nodes[id2] = {'id': id2, 'group': 'Player', 'label': p2}
                add_link(id1, id2, 'friendship')
        
        # member_a + member_b pattern
        if 'member_a' in row_lower and 'member_b' in row_lower:
            p1 = row_lower['member_a']
            p2 = row_lower['member_b']
            
            if p1 and p2:
                id1 = f"player:{p1}"
                id2 = f"player:{p2}"
                nodes[id1] = {'id': id1, 'group': 'Player', 'label': p1}
                nodes[id2] = {'id': id2, 'group': 'Player', 'label': p2}
                add_link(id1, id2, 'friendship')
        
        # === ITEM RELATIONSHIPS ===
        if 'player_id' in row and 'item_id' in row:
            player_id = row['player_id']
            item_id = row['item_id']
            player_label = row.get('gamertag') or str(player_id)
            item_label = row.get('item_name') or str(item_id)
            
            nodes[f"player:{player_id}"] = {'id': f"player:{player_id}", 'group': 'Player', 'label': player_label}
            nodes[f"item:{item_id}"] = {'id': f"item:{item_id}", 'group': 'Item', 'label': item_label}
            add_link(f"player:{player_id}", f"item:{item_id}", 'ownership')
    
    if not nodes and not links:
        return None
        
    return {'nodes': list(nodes.values()), 'links': links}


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
 
    from google.cloud import geminidataanalytics
    data_chat_client = _get_cached_client()

    # Use cached datasource references
    datasource_references = _get_cached_datasource()

    system_instruction = AGENT_CONFIG.get('get_insights', {}).get('system_instruction', """You are a specialized AI data analyst...""")

    # GA Feature: Load context authoring (glossary terms + example queries)
    context_authoring = _load_context_authoring()
    
    context_kwargs = {
        'system_instruction': system_instruction,
        'datasource_references': datasource_references,
        'options': geminidataanalytics.ConversationOptions(
            analysis=geminidataanalytics.AnalysisOptions(
                python=geminidataanalytics.AnalysisOptions.Python(
                    enabled=False
                )
            )
        ),
    }
    
    # Add glossary terms if available
    if context_authoring.get('glossary_terms'):
        context_kwargs['glossary_terms'] = context_authoring['glossary_terms']
    
    # Add example queries if available
    if context_authoring.get('example_queries'):
        context_kwargs['example_queries'] = context_authoring['example_queries']
    
    # Context set-up for 'Chat using Inline Context'
    inline_context = geminidataanalytics.Context(**context_kwargs)

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
        # stream = data_chat_client.chat(request=request)
        stream = retry_api_call(
            lambda: data_chat_client.chat(request=request),
            retries=3,
            delay=2,
            error_msg="Looker Data Chat query failed"
        )
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
                
                # Normalize data if it's a list (e.g. chunks yielded from gemini-3.5-flash)
                data_dict = message_dict['data']
                if isinstance(data_dict, list):
                    merged_data_dict = {}
                    for item in data_dict:
                        if isinstance(item, dict):
                            for k, v in item.items():
                                if k in merged_data_dict and isinstance(merged_data_dict[k], dict) and isinstance(v, dict):
                                    merged_data_dict[k].update(v)
                                elif k in merged_data_dict and isinstance(merged_data_dict[k], list) and isinstance(v, list):
                                    merged_data_dict[k].extend(v)
                                else:
                                    merged_data_dict[k] = v
                    data_dict = merged_data_dict
                    message_dict['data'] = data_dict
                
                data_insights.append(data_dict)
                
                result_data = data_dict.get('result', {})
                if isinstance(result_data, list):
                    # It's a list of rows, so wrap it in a standard result dict
                    result_data = {"rows": result_data, "schema": {}}
                    data_dict['result'] = result_data
                
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

def extract_tool_argument(args, param_names, default=""):
    """Safely extracts a parameter from function call args of varying shapes."""
    if not args:
        return default
    
    args_dict = {}
    if isinstance(args, list):
        for arg in args:
            if isinstance(arg, dict):
                args_dict.update(arg)
    elif isinstance(args, dict):
        args_dict = args
    elif isinstance(args, str):
        try:
            import json
            loaded = json.loads(args)
            if isinstance(loaded, dict):
                args_dict = loaded
            elif isinstance(loaded, list):
                for item in loaded:
                    if isinstance(item, dict):
                        args_dict.update(item)
        except Exception:
            pass
            
    for name in param_names:
        if name in args_dict:
            return args_dict[name]
            
    if args_dict:
        return list(args_dict.values())[0]
    return default

def run_deep_analysis(question: str, model_name: str = None):
    """Runs a deep analysis using a planning agent loop."""
    if not model_name:
        model_name = os.getenv("DEEP_MODE_MODEL", "gemini-3.5-flash")
        
    log_thought(f"Entering Deep Analysis Mode ({model_name}) - Activating reasoning engine to plan and execute queries across Looker metrics and Spanner Graph...")
    
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
    
    generate_chart_func = FunctionDeclaration(
        name="generate_chart",
        description="Generates the specific JSON configuration required for rendering charts. Use this whenever the user asks for a visualization or the data represents a trend/comparison.",
        parameters={
            "type": "object",
            "properties": {
                "data_and_question": {
                    "type": "string",
                    "description": "The raw data in JSON format, and the question/context about what to visualize."
                }
            },
            "required": ["data_and_question"]
        }
    )
    
    funcs = [get_insights_func, generate_chart_func]
    
    # Add Spanner tool if configured
    if SPANNER_INSTANCE_ID:
        query_spanner_func = FunctionDeclaration(
            name="query_spanner",
            description="Executes a SQL/GQL query on the Spanner Graph database (Players, Clans, Items).",
            parameters={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The SQL or Graph query to execute."
                    }
                },
                "required": ["sql"]
            }
        )
        funcs.append(query_spanner_func)
        print("INFO: Added query_spanner tool to Deep Mode.")

    analysis_tools = Tool(function_declarations=funcs)

    model = GenerativeModel(
        model_name,
        tools=[analysis_tools],
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO
            )
        ),
        system_instruction=AGENT_CONFIG.get('_computed', {}).get('deep_mode', "You are a Senior Data Analyst."),
    )
    
    chat = model.start_chat()
    intermediate_thoughts = []
    
    try:
        t0 = time.time()
        response_stream = retry_api_call(
            lambda: chat.send_message(question, stream=True),
            retries=3,
            delay=2,
            error_msg="Deep Analysis initial chat failed"
        )
        
        # Loop for tool calls (max 10 turns to prevent infinite loops)
        for _ in range(10):
            function_calls = []
            text_parts = []
            
            for chunk in response_stream:
                candidate = chunk.candidates[0]
                for part in candidate.content.parts:
                    if part.function_call:
                        function_calls.append(part.function_call)
                    elif part.text:
                        text_parts.append(part.text)
                        # Stream the text as thought
                        log_thought(part.text)
            
            if function_calls:
                # Store any text parts generated in this turn as intermediate thoughts
                if text_parts:
                    intermediate_thoughts.append("".join(text_parts))
                
                log_thought(f"Deep Analysis: Executing {len(function_calls)} tool call(s)...")
                
                # Execute tools in parallel
                with ThreadPoolExecutor() as executor:
                    # Create a list of futures
                    futures = []
                    for fn in function_calls:
                        log_debug(f"Tool Call: {fn.name}, Args: {fn.args}")
                        if fn.name == "get_insights":
                            question_arg = extract_tool_argument(fn.args, ["question", "query"])
                            futures.append(executor.submit(get_insights, question_arg))
                        elif fn.name == "query_spanner":
                            sql_arg = extract_tool_argument(fn.args, ["sql"])
                            futures.append(executor.submit(query_spanner, sql_arg))
                        elif fn.name == "generate_chart":
                            data_and_question_arg = extract_tool_argument(fn.args, ["data_and_question"])
                            futures.append(executor.submit(generate_chart_config, data_and_question_arg))
                        else:
                            log_debug(f"Unknown tool: {fn.name}")
                            futures.append(None)

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
                             pass
                
                log_thought("Synthesizing findings...")
                t_synth = time.time()
                response_stream = retry_api_call(
                    lambda: chat.send_message(tool_responses, stream=True),
                    retries=3,
                    delay=2,
                    error_msg="Deep Analysis synthesis step failed"
                )
                log_thought(f"Synthesis/Next Step Generated in {time.time() - t_synth:.2f}s")
                
            elif text_parts:
                # Text response (Final answer)
                full_text = "".join(text_parts)
                if intermediate_thoughts:
                    full_text = "\n\n".join(intermediate_thoughts) + "\n\n" + full_text
                yield {'content': {'parts': [{'text': full_text}]}}
                break
            else:
                # No content?
                if intermediate_thoughts:
                    yield {'content': {'parts': [{'text': "\n\n".join(intermediate_thoughts)}]}}
                break
        else:
            # If we hit the max iterations without breaking, yield a final message
            full_text = "I have analyzed the data extensively but reached my maximum reasoning limit. Please try breaking down your question into smaller, more specific pieces."
            if intermediate_thoughts:
                full_text = "\n\n".join(intermediate_thoughts) + "\n\n" + full_text
            yield {'content': {'parts': [{'text': full_text}]}}
    except Exception as e:
        log_thought(f"Deep Analysis Error: {e}")
        full_text = f"An error occurred during deep analysis: {e}"
        if intermediate_thoughts:
            full_text = "\n\n".join(intermediate_thoughts) + "\n\n" + full_text
        yield {'content': {'parts': [{'text': full_text}]}}

def perform_deep_analysis(question: str, model_name: str = None):
    """Performs a deep, multi-step analysis for complex questions.
    
    Use this tool when the user asks for:
    - Comparisons (e.g., "Compare X vs Y", "Analyze performance of A vs B")
    - Root cause analysis (e.g., "Why did revenue drop?")
    - Multi-dimensional breakdowns (e.g., "Break down by Country AND Platform")
    - Open-ended exploration (e.g., "Find the top opportunities")
    
    Args:
        question: The complex user question to analyze.
        model_name: The optional model name to run the analysis on.
        
    Returns:
        A comprehensive markdown report with charts and data.
    """
    full_report = ""
    try:
        # We need to consume the generator here since tools must return a value, not a generator
        for chunk in run_deep_analysis(question, model_name=model_name):
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
    model="gemini-3.5-flash",
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

def generate_chart_config(data_and_question: str) -> str:
    """Generates the specific JSON configuration required for rendering charts from data and a question."""
    log_debug(f"Calling visualization agent with: {data_and_question[:200]}...")
    model = GenerativeModel(
        "gemini-3.5-flash",
        system_instruction=visualization_agent.instruction
    )
    response = retry_api_call(
        lambda: model.generate_content(data_and_question),
        retries=3,
        delay=2,
        error_msg="Visualization agent call failed"
    )
    return response.text

unified_agent = Agent(
    model="gemini-3.5-flash",
    name="UnifiedAnalyticsAgent",
    instruction=AGENT_CONFIG.get('_computed', {}).get('unified_agent', """You are an expert mobile gaming data analyst..."""),
    tools=[
        get_insights,
        query_spanner,
        perform_deep_analysis,

        # Wrap the sub-agent as a tool
        agent_tool.AgentTool(agent=visualization_agent)
    ],
)

# MCP Agent for Looker Toolbox (create dashboards, analyze LookML, etc.)
mcp_agent = None
mcp_app = None

# try:
#     mcp_toolset = MCPToolset(
#         connection_params=StdioConnectionParams(
#             command="./toolbox",
#             args=["--stdio", "--prebuilt", "looker"],
#             env={
#                 "LOOKER_BASE_URL": LOOKER_INSTANCE_URI,
#                 "LOOKER_CLIENT_ID": LOOKER_CLIENT_ID,
#                 "LOOKER_CLIENT_SECRET": LOOKER_CLIENT_SECRET,
#                 "LOOKER_VERIFY_SSL": "true",
#             }
#         )
#     )
    
#     mcp_agent = Agent(
#         model="gemini-3-flash-preview",
#         name="LookerToolboxAgent",
#         instruction="""You are a Looker admin assistant with access to Looker Toolbox via MCP.
        
# You have access to power tools to interact with Looker:

# **Model & Query Tools:**
# - get_models, get_explores, get_dimensions, get_measures
# - query (run queries), query_sql, query_url

# **Content Tools:**
# - make_dashboard (create dashboards), add_dashboard_element, add_dashboard_filter
# - make_look (create Looks), run_look, run_dashboard
# - get_dashboards, get_looks, generate_embed_url

# **LookML Authoring:**
# - get_projects, get_project_files, get_project_file
# - create_project_file, update_project_file, delete_project_file
# - dev_mode (activate dev mode)

# **Health Tools:**
# - health_pulse, health_analyze, health_vacuum

# When asked to create content, use the appropriate tools and return the URL.
# Always be helpful and explain what you're doing.""",
#         tools=[mcp_toolset],
#     )
    
#     mcp_app = reasoning_engines.AdkApp(
#         agent=mcp_agent,
#         enable_tracing=False,
#     )
#     print("INFO: MCP Looker Toolbox agent initialized successfully")
# except Exception as e:
#     print(f"WARNING: Failed to initialize MCP Agent: {e}")

# vertexai.init is moved to the entry point (chat.py or deploy.py)
# to avoid hardcoding the staging bucket in the remote environment.

class DeepAnalysisApp:
    """
    Wrapper for Deep Analysis mode to function as an App for server.py.
    Bypasses the Unified Agent router for lower latency.
    """
    def stream_query(self, message: str, user_id: str = None, session_id: str = None, model_name: str = None):
        # Directly invoke the generator
        return run_deep_analysis(message, model_name=model_name)

    def get_session(self, *args, **kwargs):
        pass

    def create_session(self, *args, **kwargs):
        pass

deep_app = DeepAnalysisApp()


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
    elif agent_type == "deep":
        return deep_app
    return app


def extract_single_number(res):
    try:
        if res and res.get('status') == 'success' and 'data_insights' in res:
            data_ins = res['data_insights']
            if data_ins and isinstance(data_ins, list):
                result = data_ins[0].get('result', {})
                rows = result.get('data') or result.get('rows') or []
                if rows:
                    row = rows[0]
                    for k, v in row.items():
                        if isinstance(v, (int, float)):
                            return v
                        elif isinstance(v, str):
                            try:
                                clean_str = v.replace('$', '').replace(',', '').strip()
                                if '.' in clean_str:
                                    return float(clean_str)
                                return int(clean_str)
                            except ValueError:
                                pass
    except Exception as e:
        log_debug(f"Error extracting single number: {e}")
    return 0


def extract_trend_data(res):
    try:
        if res and res.get('status') == 'success' and 'data_insights' in res:
            data_ins = res['data_insights']
            if data_ins and isinstance(data_ins, list):
                result = data_ins[0].get('result', {})
                return result.get('data') or result.get('rows') or []
    except Exception as e:
        log_debug(f"Error extracting trend data: {e}")
    return []


def build_looker_explore_url(fields, filters):
    """
    Builds a prebuilt Looker Explore URL based on fields and filters.
    """
    import urllib.parse
    base_uri = LOOKER_INSTANCE_URI.rstrip('/')
    params = []
    
    # Add fields
    if fields:
        fields_str = ",".join(fields)
        params.append(("fields", fields_str))
        
    # Add filters
    if filters and isinstance(filters, dict):
        for k, v in filters.items():
            params.append((f"f[{k}]", str(v)))
            
    query_str = urllib.parse.urlencode(params)
    return f"{base_uri}/explore/{LOOKML_MODEL}/{EXPLORE}?{query_str}&toggle=dat,pik,vis"


def generate_daily_summary(force_refresh=False):
    """
    Generates a daily summary of gaming metrics.
    Caches the results to a local file for quick loads.
    """
    import datetime
    
    cache_path = "datasets/events_daily_summary_cache.json"
    if not force_refresh and os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                cached_data = json.load(f)
            # Basic validation of cached data
            if "timestamp" in cached_data and "games" in cached_data:
                log_debug("Returning cached daily summary.")
                return cached_data
        except Exception as e:
            log_debug(f"Error reading daily summary cache: {e}")

    log_thought("Generating new Daily AI Summary insights...")
    
    question_overall = "Daily total revenue, total iap revenue, total ad revenue, active users, number of sessions, new users, and Day 1 retention rate for the last 7 days ending yesterday"
    question_by_game = "Daily total revenue, total iap revenue, total ad revenue, active users, number of sessions, new users, and Day 1 retention rate for the last 7 days ending yesterday, broken down by game name"
    
    raw_res_overall = None
    raw_res_by_game = None
    import time
    
    # 1. Run overall query
    for attempt in range(3):
        try:
            log_debug(f"Running Looker query (attempt {attempt+1}): '{question_overall}'")
            res = get_insights(question_overall)
            if res and res.get('status') == 'success' and 'data_insights' in res:
                raw_res_overall = res
                break
        except Exception as e:
            log_debug(f"Attempt {attempt+1} failed: {e}")
        if attempt < 2:
            time.sleep(2 ** attempt)

    # 2. Run by-game query
    for attempt in range(3):
        try:
            log_debug(f"Running Looker query (attempt {attempt+1}): '{question_by_game}'")
            res = get_insights(question_by_game)
            if res and res.get('status') == 'success' and 'data_insights' in res:
                raw_res_by_game = res
                break
        except Exception as e:
            log_debug(f"Attempt {attempt+1} failed: {e}")
        if attempt < 2:
            time.sleep(2 ** attempt)

    # Helper function to extract value with key prefix tolerance
    def get_val(row, key, default=0.0):
        val = row.get(key)
        if val is None:
            for k, v in row.items():
                if k.endswith("." + key) or k == key:
                    val = v
                    break
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default
            
    def get_change(curr, prev):
        if not prev or prev == 0:
            return 0.0
        return round(((curr - prev) / prev) * 100.0, 2)

    def process_dataset(trend_data):
        trend_data = sorted(trend_data, key=lambda x: x.get("events.event_date", ""))
        yesterday_row = trend_data[-1] if len(trend_data) >= 1 else {}
        day_before_row = trend_data[-2] if len(trend_data) >= 2 else {}
        
        yesterday_rev = get_val(yesterday_row, "total_revenue")
        day_before_rev = get_val(day_before_row, "total_revenue")
        
        yesterday_iap = get_val(yesterday_row, "total_iap_revenue")
        day_before_iap = get_val(day_before_row, "total_iap_revenue")
        
        yesterday_ad = get_val(yesterday_row, "total_ad_revenue")
        day_before_ad = get_val(day_before_row, "total_ad_revenue")
        
        yesterday_dau = get_val(yesterday_row, "number_of_users")
        day_before_dau = get_val(day_before_row, "number_of_users")
        
        yesterday_new_users = get_val(yesterday_row, "number_of_new_users")
        day_before_new_users = get_val(day_before_row, "number_of_new_users")
        
        yesterday_sess = get_val(yesterday_row, "number_of_sesssions")
        day_before_sess = get_val(day_before_row, "number_of_sesssions")
        
        yesterday_ret = get_val(yesterday_row, "d1_retention_rate")
        day_before_ret = get_val(day_before_row, "d1_retention_rate")
        
        yesterday_ret_pct = round(yesterday_ret * 100.0, 2)
        day_before_ret_pct = round(day_before_ret * 100.0, 2)
        
        revenue_change = get_change(yesterday_rev, day_before_rev)
        iap_change = get_change(yesterday_iap, day_before_iap)
        ad_change = get_change(yesterday_ad, day_before_ad)
        dau_change = get_change(yesterday_dau, day_before_dau)
        new_users_change = get_change(yesterday_new_users, day_before_new_users)
        sessions_change = get_change(yesterday_sess, day_before_sess)
        ret_change = round(yesterday_ret_pct - day_before_ret_pct, 2)
        
        return {
            "metrics": {
                "revenue": {
                    "value": yesterday_rev, 
                    "change": revenue_change,
                    "iap_value": yesterday_iap,
                    "iap_change": iap_change,
                    "ad_value": yesterday_ad,
                    "ad_change": ad_change
                },
                "dau": {
                    "value": yesterday_dau, 
                    "change": dau_change,
                    "new_users_value": yesterday_new_users,
                    "new_users_change": new_users_change
                },
                "sessions": {
                    "value": yesterday_sess, 
                    "change": sessions_change
                },
                "retention": {
                    "value": yesterday_ret_pct, 
                    "change": ret_change
                }
            },
            "trends": trend_data
        }

    # Extract raw data lists
    trend_overall = []
    if raw_res_overall:
        trend_overall = extract_trend_data(raw_res_overall)
        
    trend_by_game = []
    if raw_res_by_game:
        trend_by_game = extract_trend_data(raw_res_by_game)
        
    # Group by game
    battle_royale_trend = [r for r in trend_by_game if r.get("events.game_name") == "Lookup Battle Royale"]
    farm_trend = [r for r in trend_by_game if r.get("events.game_name") == "Lookerwood Farm"]
    
    # Process each dataset
    overall_processed = process_dataset(trend_overall)
    br_processed = process_dataset(battle_royale_trend)
    farm_processed = process_dataset(farm_trend)

    # Prompt Gemini for narrative synthesis on the whole comparative data
    prompt = f"""
    You are an expert Gaming Product Analyst. Analyze the following daily performance metrics and 7-day trend data for our two games and the overall business, and synthesize a daily insights dashboard report.
    
    Games:
    1. Lookup Battle Royale (High volume, IAP monetization model)
    2. Lookerwood Farm (Medium volume, Ad monetization model)
    
    OVERALL aggregated Yesterday's Metrics:
    - Total Revenue: ${overall_processed['metrics']['revenue']['value']:,} ({overall_processed['metrics']['revenue']['change']:+}% vs day before)
      - IAP: ${overall_processed['metrics']['revenue']['iap_value']:,} ({overall_processed['metrics']['revenue']['iap_change']:+}% vs day before)
      - Ads: ${overall_processed['metrics']['revenue']['ad_value']:,} ({overall_processed['metrics']['revenue']['ad_change']:+}% vs day before)
    - DAU: {overall_processed['metrics']['dau']['value']:,} ({overall_processed['metrics']['dau']['change']:+}% vs day before)
      - New Users: {overall_processed['metrics']['dau']['new_users_value']:,} ({overall_processed['metrics']['dau']['new_users_change']:+}% vs day before)
    - Sessions: {overall_processed['metrics']['sessions']['value']:,} ({overall_processed['metrics']['sessions']['change']:+}% vs day before)
    - Day 1 Retention: {overall_processed['metrics']['retention']['value']}% ({overall_processed['metrics']['retention']['change']:+}% pts vs day before)
    
    LOOKUP BATTLE ROYALE Yesterday's Metrics:
    - Total Revenue: ${br_processed['metrics']['revenue']['value']:,} ({br_processed['metrics']['revenue']['change']:+}% vs day before)
      - IAP: ${br_processed['metrics']['revenue']['iap_value']:,} ({br_processed['metrics']['revenue']['iap_change']:+}% vs day before)
      - Ads: ${br_processed['metrics']['revenue']['ad_value']:,} ({br_processed['metrics']['revenue']['ad_change']:+}% vs day before)
    - DAU: {br_processed['metrics']['dau']['value']:,} ({br_processed['metrics']['dau']['change']:+}% vs day before)
      - New Users: {br_processed['metrics']['dau']['new_users_value']:,} ({br_processed['metrics']['dau']['new_users_change']:+}% vs day before)
    - Sessions: {br_processed['metrics']['sessions']['value']:,} ({br_processed['metrics']['sessions']['change']:+}% vs day before)
    - Day 1 Retention: {br_processed['metrics']['retention']['value']}% ({br_processed['metrics']['retention']['change']:+}% pts vs day before)
    
    LOOKERWOOD FARM Yesterday's Metrics:
    - Total Revenue: ${farm_processed['metrics']['revenue']['value']:,} ({farm_processed['metrics']['revenue']['change']:+}% vs day before)
      - IAP: ${farm_processed['metrics']['revenue']['iap_value']:,} ({farm_processed['metrics']['revenue']['iap_change']:+}% vs day before)
      - Ads: ${farm_processed['metrics']['revenue']['ad_value']:,} ({farm_processed['metrics']['revenue']['ad_change']:+}% vs day before)
    - DAU: {farm_processed['metrics']['dau']['value']:,} ({farm_processed['metrics']['dau']['change']:+}% vs day before)
      - New Users: {farm_processed['metrics']['dau']['new_users_value']:,} ({farm_processed['metrics']['dau']['new_users_change']:+}% vs day before)
    - Sessions: {farm_processed['metrics']['sessions']['value']:,} ({farm_processed['metrics']['sessions']['change']:+}% vs day before)
    - Day 1 Retention: {farm_processed['metrics']['retention']['value']}% ({farm_processed['metrics']['retention']['change']:+}% pts vs day before)
    
    Raw 7-Day Trend Data (by Game and Overall):
    - Overall: {json.dumps(overall_processed['trends'])}
    - Lookup Battle Royale: {json.dumps(br_processed['trends'])}
    - Lookerwood Farm: {json.dumps(farm_processed['trends'])}
    
    Instructions:
    1. Write a compelling, high-level "game_comparison" narrative (markdown format, about 200 words) summarizing the performance differences between Lookup Battle Royale (IAP-driven) and Lookerwood Farm (Ad-driven). Contrast their monetization mechanics, player retention quality, and operational health.
    
    2. For each view ("overall", "battle_royale", "farm"), generate:
       - A descriptive, high-quality qualitative "executive_summary" (markdown format, about 100-150 words).
       - 3-5 key "highlights" (list of strings) capturing major performance shifts.
       - 3-5 "action_items" representing actionable recommendations. Format each action item EXACTLY as an object with these keys:
         - "text": "Detailed recommendation description...",
         - "fields": ["events.event_date", "events.total_ad_revenue", ...],
         - "filters": {{"events.game_name": "Lookerwood Farm", ...}}
         Only use valid dimensions and measures from the 'events' explore.
       - Recharts configurations for `revenue_mix_trend` (stacked area chart of IAP vs Ad revenue) and `dau_retention_trend` (combo chart: DAU bars on left y-axis, D1 Retention Rate line on right y-axis).
       
       Format `revenue_mix_trend` EXACTLY as follows:
       {{
         "type": "area",
         "xAxisKey": "date",
         "stacked": true,
         "data": [
           {{"date": "YYYY-MM-DD", "iap": 12345, "ad": 6789}},
           ...
         ],
         "series": [
           {{"name": "IAP Revenue", "dataKey": "iap", "strokeColor": "hsl(var(--primary))", "fillColor": "hsla(var(--primary), 0.3)"}},
           {{"name": "Ad Revenue", "dataKey": "ad", "strokeColor": "hsl(var(--chart-2))", "fillColor": "hsla(var(--chart-2), 0.3)"}}
         ],
         "title": "7-Day Revenue Mix Trend (IAP vs. Ads)"
       }}
       
       Format `dau_retention_trend` EXACTLY as follows:
       {{
         "type": "combo",
         "xAxisKey": "date",
         "data": [
           {{"date": "YYYY-MM-DD", "dau": 123456, "retention": 5.56}},
           ...
         ],
         "series": [
           {{"type": "bar", "name": "DAU", "dataKey": "dau", "fillColor": "hsla(var(--primary), 0.2)", "strokeColor": "hsl(var(--primary))", "yAxisID": "left"}},
           {{"type": "line", "name": "D1 Retention Rate (%)", "dataKey": "retention", "strokeColor": "hsl(var(--chart-3))", "fillColor": "hsl(var(--chart-3))", "yAxisID": "right"}}
         ],
         "title": "7-Day Active Users & Retention Trend"
       }}
       
       Make sure the dates are formatted as YYYY-MM-DD. Retention must be a percentage float (e.g. 0.054 -> 5.4).
       
    You MUST return ONLY a valid JSON object. Do not include markdown code block formatting like ```json ... ``` or any other surrounding text.
    Return a single JSON object with these EXACT keys:
    - "game_comparison"
    - "overall": {{ "executive_summary": "...", "highlights": [...], "action_items": [{{"text": "...", "fields": [...], "filters": {{...}}}}, ...], "revenue_mix_trend": {{...}}, "dau_retention_trend": {{...}} }}
    - "battle_royale": {{ "executive_summary": "...", "highlights": [...], "action_items": [{{"text": "...", "fields": [...], "filters": {{...}}}}, ...], "revenue_mix_trend": {{...}}, "dau_retention_trend": {{...}} }}
    - "farm": {{ "executive_summary": "...", "highlights": [...], "action_items": [{{"text": "...", "fields": [...], "filters": {{...}}}}, ...], "revenue_mix_trend": {{...}}, "dau_retention_trend": {{...}} }}
    """

    model_name = os.getenv("DEEP_MODE_MODEL", "gemini-3.5-flash")
    from vertexai.generative_models import GenerativeModel
    model = GenerativeModel(model_name)
    
    try:
        response = retry_api_call(
            lambda: model.generate_content(prompt),
            retries=3,
            delay=2,
            error_msg="Daily summary synthesis failed"
        )
        response_text = response.text.strip()
        
        # Strip markdown code block wrappers if present
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()
            
        summary_json = json.loads(response_text)
    except Exception as e:
        log_debug(f"Failed to generate daily summary narrative: {e}")
        summary_json = None
        if 'response_text' in locals():
            try:
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    summary_json = json.loads(response_text[start_idx:end_idx+1])
            except Exception as e2:
                log_debug(f"Failed to extract JSON substring: {e2}")
        
        if not summary_json:
            # Simple fallback structure
            summary_json = {
                "game_comparison": "Lookerwood Farm and Lookup Battle Royale comparison.",
                "overall": {
                    "executive_summary": "Overall metrics overview.",
                    "highlights": ["Highlights not generated."],
                    "action_items": [{"text": "Monitor overall performance metrics.", "fields": ["events.event_date", "events.total_revenue"], "filters": {}}],
                    "revenue_mix_trend": {"type": "area", "xAxisKey": "date", "stacked": True, "data": [], "series": [{"name": "IAP Revenue", "dataKey": "iap", "strokeColor": "hsl(var(--primary))", "fillColor": "hsla(var(--primary), 0.3)"}, {"name": "Ad Revenue", "dataKey": "ad", "strokeColor": "hsl(var(--chart-2))", "fillColor": "hsla(var(--chart-2), 0.3)"}], "title": "7-Day Revenue Mix Trend (IAP vs. Ads)"},
                    "dau_retention_trend": {"type": "combo", "xAxisKey": "date", "data": [], "series": [{"type": "bar", "name": "DAU", "dataKey": "dau", "fillColor": "hsla(var(--primary), 0.2)", "strokeColor": "hsl(var(--primary))", "yAxisID": "left"}, {"type": "line", "name": "D1 Retention Rate (%)", "dataKey": "retention", "strokeColor": "hsl(var(--chart-3))", "fillColor": "hsl(var(--chart-3))", "yAxisID": "right"}], "title": "7-Day Active Users & Retention Trend"}
                },
                "battle_royale": {
                    "executive_summary": "Lookup Battle Royale metrics overview.",
                    "highlights": [],
                    "action_items": [{"text": "Analyze Battle Royale In-App Purchase trends.", "fields": ["events.event_date", "events.total_iap_revenue"], "filters": {"events.game_name": "Lookup Battle Royale"}}],
                    "revenue_mix_trend": {"type": "area", "xAxisKey": "date", "stacked": True, "data": [], "series": [{"name": "IAP Revenue", "dataKey": "iap", "strokeColor": "hsl(var(--primary))", "fillColor": "hsla(var(--primary), 0.3)"}, {"name": "Ad Revenue", "dataKey": "ad", "strokeColor": "hsl(var(--chart-2))", "fillColor": "hsla(var(--chart-2), 0.3)"}], "title": "7-Day Revenue Mix Trend (IAP vs. Ads)"},
                    "dau_retention_trend": {"type": "combo", "xAxisKey": "date", "data": [], "series": [{"type": "bar", "name": "DAU", "dataKey": "dau", "fillColor": "hsla(var(--primary), 0.2)", "strokeColor": "hsl(var(--primary))", "yAxisID": "left"}, {"type": "line", "name": "D1 Retention Rate (%)", "dataKey": "retention", "strokeColor": "hsl(var(--chart-3))", "fillColor": "hsl(var(--chart-3))", "yAxisID": "right"}], "title": "7-Day Active Users & Retention Trend"}
                },
                "farm": {
                    "executive_summary": "Lookerwood Farm metrics overview.",
                    "highlights": [],
                    "action_items": [{"text": "Investigate Farm ad network and ad revenue trends.", "fields": ["events.event_date", "events.total_ad_revenue"], "filters": {"events.game_name": "Lookerwood Farm"}}],
                    "revenue_mix_trend": {"type": "area", "xAxisKey": "date", "stacked": True, "data": [], "series": [{"name": "IAP Revenue", "dataKey": "iap", "strokeColor": "hsl(var(--primary))", "fillColor": "hsla(var(--primary), 0.3)"}, {"name": "Ad Revenue", "dataKey": "ad", "strokeColor": "hsl(var(--chart-2))", "fillColor": "hsla(var(--chart-2), 0.3)"}], "title": "7-Day Revenue Mix Trend (IAP vs. Ads)"},
                    "dau_retention_trend": {"type": "combo", "xAxisKey": "date", "data": [], "series": [{"type": "bar", "name": "DAU", "dataKey": "dau", "fillColor": "hsla(var(--primary), 0.2)", "strokeColor": "hsl(var(--primary))", "yAxisID": "left"}, {"type": "line", "name": "D1 Retention Rate (%)", "dataKey": "retention", "strokeColor": "hsl(var(--chart-3))", "fillColor": "hsl(var(--chart-3))", "yAxisID": "right"}], "title": "7-Day Active Users & Retention Trend"}
                }
            }

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def process_action_items(action_items_raw):
        processed = []
        if not action_items_raw or not isinstance(action_items_raw, list):
            return [{
                "text": "Monitor performance metrics and system health.",
                "explore_url": build_looker_explore_url(["events.event_date", "events.total_revenue"], {})
            }]
            
        for item in action_items_raw:
            if not isinstance(item, dict):
                processed.append({
                    "text": str(item),
                    "explore_url": build_looker_explore_url(["events.event_date", "events.total_revenue"], {})
                })
                continue
                
            text = item.get("text", "Prebuilt Analysis")
            fields = item.get("fields", ["events.event_date", "events.total_revenue"])
            filters = item.get("filters", {})
            
            explore_url = build_looker_explore_url(fields, filters)
            processed.append({
                "text": text,
                "explore_url": explore_url
            })
            
        return processed

    # Structure games payloads
    final_output = {
        "timestamp": current_time,
        "game_comparison": summary_json.get("game_comparison", ""),
        "games": {
            "overall": {
                "metrics": overall_processed["metrics"],
                "narrative": {
                    "executive_summary": summary_json.get("overall", {}).get("executive_summary", ""),
                    "highlights": summary_json.get("overall", {}).get("highlights", []),
                    "action_items": process_action_items(summary_json.get("overall", {}).get("action_items", []))
                },
                "charts": {
                    "revenue_mix": summary_json.get("overall", {}).get("revenue_mix_trend"),
                    "dau_retention": summary_json.get("overall", {}).get("dau_retention_trend")
                }
            },
            "battle_royale": {
                "metrics": br_processed["metrics"],
                "narrative": {
                    "executive_summary": summary_json.get("battle_royale", {}).get("executive_summary", ""),
                    "highlights": summary_json.get("battle_royale", {}).get("highlights", []),
                    "action_items": process_action_items(summary_json.get("battle_royale", {}).get("action_items", []))
                },
                "charts": {
                    "revenue_mix": summary_json.get("battle_royale", {}).get("revenue_mix_trend"),
                    "dau_retention": summary_json.get("battle_royale", {}).get("dau_retention_trend")
                }
            },
            "farm": {
                "metrics": farm_processed["metrics"],
                "narrative": {
                    "executive_summary": summary_json.get("farm", {}).get("executive_summary", ""),
                    "highlights": summary_json.get("farm", {}).get("highlights", []),
                    "action_items": process_action_items(summary_json.get("farm", {}).get("action_items", []))
                },
                "charts": {
                    "revenue_mix": summary_json.get("farm", {}).get("revenue_mix_trend"),
                    "dau_retention": summary_json.get("farm", {}).get("dau_retention_trend")
                }
            }
        }
    }
    
    # Save cache
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(final_output, f, indent=2)
        log_debug(f"Saved daily summary to cache: {cache_path}")
    except Exception as e:
        log_debug(f"Failed to write cache file: {e}")
        
    return final_output
