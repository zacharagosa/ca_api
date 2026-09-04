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

# Normalize and defensively validate GOOGLE_APPLICATION_CREDENTIALS
_sa_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if _sa_path:
    _expanded = os.path.expanduser(_sa_path)
    if os.path.exists(_expanded):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = _expanded
    else:
        _user_sa = os.path.expanduser('~/.config/gcloud/sa_key.json')
        if os.path.exists(_user_sa):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = _user_sa
        else:
            print(f"WARNING: GOOGLE_APPLICATION_CREDENTIALS '{_sa_path}' not found. Falling back to Application Default Credentials (ADC).")
            os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)

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
import datetime
import vertexai
from vertexai.preview import reasoning_engines
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part, Content, ToolConfig
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
PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("PROJECT_ID", "1094200614711")
if PROJECT_ID == "aragosalooker":
    PROJECT_ID = "1094200614711" # Force numeric ID if default/old string is found
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "global")
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

def init_vertex_ai():
    try:
        creds = auth_manager.get_credentials()
        vertexai.init(
            project=PROJECT_ID,
            location=VERTEX_LOCATION,
            credentials=creds,
            staging_bucket="gs://ca_api",
        )
        print(f"INFO: Vertex AI initialized successfully (project: {PROJECT_ID}, location: {VERTEX_LOCATION})")
    except Exception as e:
        print(f"WARNING: Vertex AI initialization failed: {e}")

init_vertex_ai()


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

        # Check if LookerExploreReferences accepts credentials (older SDK versions)
        has_looker_credentials = 'credentials' in geminidataanalytics.LookerExploreReferences.pb().DESCRIPTOR.fields_by_name
        
        if has_looker_credentials:
            looker_refs = geminidataanalytics.LookerExploreReferences(
                explore_references=[looker_explore_reference],
                credentials=_cached_credentials
            )
        else:
            looker_refs = geminidataanalytics.LookerExploreReferences(
                explore_references=[looker_explore_reference]
            )
            
        _cached_datasource_refs = geminidataanalytics.DatasourceReferences(
            looker=looker_refs,
        )
    
    return _cached_datasource_refs

def _create_chat_request(inline_context, messages):
    from google.cloud import geminidataanalytics
    chat_kwargs = {
        'inline_context': inline_context,
        'parent': f"projects/{PROJECT_ID}/locations/global",
        'messages': messages,
    }
    
    # Ensure _get_cached_datasource was run so _cached_credentials is initialized
    _get_cached_datasource()
    
    if 'credentials' in geminidataanalytics.ChatRequest.pb().DESCRIPTOR.fields_by_name and _cached_credentials:
        chat_kwargs['credentials'] = _cached_credentials
        
    return geminidataanalytics.ChatRequest(**chat_kwargs)

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
    
    request = _create_chat_request(inline_context, messages)
    
    
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
                request = _create_chat_request(inline_context, messages)
                continue # Retry
            
            elif "CHART_GENERATION" in error_str and attempt < max_retries:
                print(f"DEBUG: Caught CHART_GENERATION error: {error_str}. Retrying without chart generation...")
                
                # Append a correction message to disable chart generation for this turn
                correction_msg = geminidataanalytics.Message()
                correction_msg.user_message.text = "SYSTEM ERROR: Chart generation failed. Rerun the exact same query to get the data, but DO NOT call `generate_chart()`. Just return the text and data table."
                messages.append(correction_msg)
                
                # Update request with new messages
                request = _create_chat_request(inline_context, messages)
                continue # Retry
            
            elif "datasource(s) not found" in error_str.lower() and attempt < max_retries:
                print(f"DEBUG: Caught datasource not found error: {error_str}. Retrying with model constraint...")
                
                # Append a correction message forcing correct model usage
                correction_msg = geminidataanalytics.Message()
                correction_msg.user_message.text = f"SYSTEM ERROR: You attempted to query a non-existent datasource. You MUST ONLY use the '{LOOKML_MODEL}' LookML model and the '{EXPLORE}' explore. DO NOT reference 'thelook_ecommerce' or any other model. Rerun your query using ONLY fields from '{EXPLORE}.*'."
                messages.append(correction_msg)
                
                # Update request with new messages
                request = _create_chat_request(inline_context, messages)
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
                        if hasattr(val, 'isoformat'):
                            row_dict[columns[i]] = val.isoformat()
                        elif isinstance(val, (datetime.date, datetime.datetime)):
                            row_dict[columns[i]] = str(val)
                        else:
                            row_dict[columns[i]] = val
                else:
                    for i, val in enumerate(row):
                        col_k = f"col_{i}"
                        if hasattr(val, 'isoformat'):
                            row_dict[col_k] = val.isoformat()
                        elif isinstance(val, (datetime.date, datetime.datetime)):
                            row_dict[col_k] = str(val)
                        else:
                            row_dict[col_k] = val
                
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


ACTIVE_DASHBOARDS_REGISTRY = {}

def organize_dashboard_layout(sdk, dash_id: str):
    """
    Auto-organizes dashboard layout components into a clean, professional 12-column grid:
    - Single-value KPIs: Top row(s) (width 4, height 3, 3 per row)
    - Charts (Line/Column/Bar/Area/Pie): Middle rows (width 6, height 6, 2 per row)
    - Detailed Tables (Grid): Bottom row(s) (width 12, height 7, 1 per row)
    """
    try:
        from looker_sdk import models40
        dash = sdk.dashboard(str(dash_id))
        layouts = dash.dashboard_layouts or []
        if not layouts:
            return
        layout = layouts[0]
        components = layout.dashboard_layout_components or []
        if not components:
            return
            
        elements = {str(el.id): el for el in (dash.dashboard_elements or [])}
        
        kpi_comps = []
        chart_comps = []
        table_comps = []
        
        for comp in components:
            el_id = str(comp.dashboard_element_id)
            el = elements.get(el_id)
            vis_type = ""
            if el and el.result_maker and el.result_maker.vis_config:
                vis_type = el.result_maker.vis_config.get("type", "")
            elif comp.vis_type:
                vis_type = comp.vis_type
                
            if vis_type == "single_value" or (el and len(getattr(el.query, "fields", []) or []) == 1):
                kpi_comps.append(comp)
            elif vis_type == "looker_grid" or (el and len(getattr(el.query, "fields", []) or []) >= 4):
                table_comps.append(comp)
            else:
                chart_comps.append(comp)
                
        current_row = 0
        # 1. Layout KPIs (3 per row, w=4, h=3)
        for i, comp in enumerate(kpi_comps):
            col = (i % 3) * 4
            if i > 0 and col == 0:
                current_row += 3
            try:
                sdk.update_dashboard_layout_component(str(comp.id), body=models40.WriteDashboardLayoutComponent(
                    row=current_row, column=col, width=4, height=3
                ))
            except Exception as e:
                log_debug(f"Could not update layout for KPI {comp.id}: {e}")
        if kpi_comps:
            current_row += 3
            
        # 2. Layout Charts (2 per row, w=6, h=6)
        for i, comp in enumerate(chart_comps):
            col = (i % 2) * 6
            if i > 0 and col == 0:
                current_row += 6
            try:
                sdk.update_dashboard_layout_component(str(comp.id), body=models40.WriteDashboardLayoutComponent(
                    row=current_row, column=col, width=6, height=6
                ))
            except Exception as e:
                log_debug(f"Could not update layout for chart {comp.id}: {e}")
        if chart_comps:
            current_row += 6
            
        # 3. Layout Tables (1 per row, w=12, h=7)
        for comp in table_comps:
            try:
                sdk.update_dashboard_layout_component(str(comp.id), body=models40.WriteDashboardLayoutComponent(
                    row=current_row, column=0, width=12, height=7
                ))
            except Exception as e:
                log_debug(f"Could not update layout for table {comp.id}: {e}")
            current_row += 7
            
        log_thought(f"Optimized dashboard grid layout ({len(kpi_comps)} KPI, {len(chart_comps)} Chart, {len(table_comps)} Table)")
    except Exception as layout_err:
        log_thought(f"Warning: Could not auto-organize layout: {layout_err}")


def create_looker_dashboard(title: str, description: str = "", tiles: list = None, filters: list = None, session_id: str = None):
    """
    Creates a new custom Looker dashboard on the fly with specified visual tiles, queries, and filters.
    """
    try:
        import looker_sdk
        from looker_sdk import models40
        from looker_embed import LookerEmbedManager

        log_thought(f"Looker MCP: Creating Dashboard '{title}' with {len(tiles) if tiles else 0} tile(s) and {len(filters) if filters else 0} filter(s)...")
        
        # Ensure Looker SDK environment variables are set
        if LOOKER_INSTANCE_URI:
            os.environ["LOOKERSDK_BASE_URL"] = LOOKER_INSTANCE_URI
        if LOOKER_CLIENT_ID:
            os.environ["LOOKERSDK_CLIENT_ID"] = LOOKER_CLIENT_ID
        if LOOKER_CLIENT_SECRET:
            os.environ["LOOKERSDK_CLIENT_SECRET"] = LOOKER_CLIENT_SECRET
            
        sdk = looker_sdk.init40()
        
        # Fetch explore schema to strictly validate dimensions and measures
        explore_name = EXPLORE or "events"
        model_name = LOOKML_MODEL or "gaming"
        valid_all = set()
        valid_short = {}
        try:
            explore_info = sdk.lookml_model_explore(lookml_model_name=model_name, explore_name=explore_name)
            valid_dims = {d.name for d in explore_info.fields.dimensions}
            valid_meas = {m.name for m in explore_info.fields.measures}
            valid_all = valid_dims | valid_meas
            valid_short = {k.split('.')[-1]: k for k in valid_all}
        except Exception as schema_err:
            log_thought(f"Warning: Could not fetch explore schema: {schema_err}")

        FIELD_ALIASES = {
            "system_game_name": "game_name",
            "game": "game_name",
            "game_title": "game_name",
            "app_name": "game_name",
            "dau": "number_of_users",
            "active_users": "number_of_users",
            "daily_active_users": "number_of_users",
            "users": "number_of_users",
            "total_users": "number_of_users",
            "unique_users": "number_of_users",
            "new_users": "number_of_new_users",
            "installs": "number_of_new_users",
            "revenue": "total_revenue",
            "iap": "total_iap_revenue",
            "iap_revenue": "total_iap_revenue",
            "ads": "total_ad_revenue",
            "ad_revenue": "total_ad_revenue",
            "sessions": "number_of_sesssions",
            "session_count": "number_of_sesssions",
            "session_counts": "number_of_sesssions",
            "total_sessions": "number_of_sesssions",
            "number_of_sessions": "number_of_sesssions",
            "events_count": "count",
            "event_count": "count",
            "date": "event_date",
            "d1": "d1_retention_rate",
            "d1_retention": "d1_retention_rate",
            "d7_retention": "d7_retention_rate",
            "d14_retention": "d14_retention_rate",
            "d30_retention": "d30_retention_rate",
        }

        def resolve_field(raw_field: str, default_explore: str) -> str:
            raw_clean = raw_field.replace(f"{default_explore}.", "").replace(f"{default_explore}_", "")
            raw_base = raw_clean.split('.')[-1].lower()
            mapped_base = FIELD_ALIASES.get(raw_base, raw_base)
            candidate = f"{default_explore}.{mapped_base}"
            if candidate in valid_all:
                return candidate
            if mapped_base in valid_short:
                return valid_short[mapped_base]
            if raw_field in valid_all:
                return raw_field
            return candidate if not valid_all else None

        # 1. Resolve or Create Dedicated AI Dashboards Folder under Shared (1)
        target_folder_id = "47"
        dash_body = models40.WriteDashboard(
            title=title,
            description=description or "AI-Generated Gaming LiveOps Dashboard",
            folder_id=target_folder_id
        )
        try:
            dash = sdk.create_dashboard(body=dash_body)
        except Exception as create_dash_err:
            if "already_exists" in str(create_dash_err) or "already exists" in str(create_dash_err):
                import time
                timestamp_str = time.strftime("%b %d, %H:%M")
                dash_body.title = f"{title} ({timestamp_str})"
                dash = sdk.create_dashboard(body=dash_body)
            else:
                raise create_dash_err
        log_thought(f"Dashboard created successfully in AI folder (ID: {dash.id}, Folder: {target_folder_id})")
        
        # 2. Create Dashboard Filters (with duplicate prevention)
        created_filters = []
        filterables_list = []
        seen_filter_keys = set()
        if filters:
            for filt in filters:
                filt_name = filt.get("name", "Filter")
                filt_title = filt.get("title", filt_name)
                filt_dim = resolve_field(filt.get("dimension") or filt.get("field", "event_date"), explore_name) or f"{explore_name}.event_date"
                filt_def = filt.get("default_value", "30 days" if "date" in filt_dim else "")
                filter_key = filt_name.lower().strip()
                if filter_key in seen_filter_keys:
                    continue
                try:
                    df = sdk.create_dashboard_filter(body=models40.CreateDashboardFilter(
                        dashboard_id=str(dash.id),
                        name=filt_name,
                        title=filt_title,
                        type="field_filter",
                        model=model_name,
                        explore=explore_name,
                        dimension=filt_dim,
                        default_value=filt_def,
                        allow_multiple_values=True,
                        ui_config={"type": "advanced" if "date" in filt_dim else "dropdown_menu", "display": "inline"}
                    ))
                    seen_filter_keys.add(filter_key)
                    created_filters.append({"id": df.id, "name": df.name, "dimension": filt_dim})
                    filterables_list.append(
                        models40.ResultMakerFilterables(
                            model=model_name,
                            view=explore_name,
                            listen=[models40.ResultMakerFilterablesListen(
                                dashboard_filter_name=df.name,
                                field=filt_dim
                            )]
                        )
                    )
                    log_thought(f"Added dashboard filter '{filt_name}' on {filt_dim}")
                except Exception as filter_create_err:
                    log_thought(f"Warning: Could not create dashboard filter '{filt_name}': {filter_create_err}")

        # 3. Create Dashboard Elements / Tiles
        created_elements = []
        if tiles:
            for idx, tile in enumerate(tiles):
                tile_title = tile.get("title", f"Metric {idx+1}")
                explore = tile.get("explore") or explore_name
                raw_fields = tile.get("fields") or []
                raw_filters = tile.get("filters") or {}
                sorts = tile.get("sorts") or []
                limit = str(tile.get("limit", "500"))
                
                # Resolve & sanitize fields
                formatted_fields = []
                for f in raw_fields:
                    res_f = resolve_field(f, explore)
                    if res_f and res_f not in formatted_fields:
                        formatted_fields.append(res_f)
                
                if not formatted_fields:
                    formatted_fields = [f"{explore}.count"]
                
                formatted_filters = {}
                if isinstance(raw_filters, dict):
                    for k, v in raw_filters.items():
                        if (k.lower() in [explore_name, 'events', 'gaming']) and ':' in str(v):
                            parts = str(v).split(':', 1)
                            filter_key = parts[0].strip()
                            filter_val = parts[1].strip().strip("'").strip('"')
                        elif k.lower() in [explore_name, 'events', 'gaming']:
                            filter_val = str(v).strip().strip("'").strip('"')
                            if not filter_val.replace('.', '').isdigit() and not any(op in filter_val for op in ['>', '<', '=', 'NULL']):
                                filter_key = "game_name"
                            else:
                                filter_key = "count"
                        else:
                            filter_key = k
                            filter_val = str(v).strip().strip("'").strip('"')
                            
                        res_k = resolve_field(filter_key, explore)
                        if res_k:
                            if res_k.endswith('.count') and not filter_val.replace('.', '').replace('-', '').isdigit() and not any(op in filter_val for op in ['>', '<', '=', 'NULL']):
                                res_k = f"{explore}.game_name"
                            formatted_filters[res_k] = filter_val
                
                if explore == "events" or "events" in explore_name or any("event_date" in f for f in formatted_fields):
                    if not any("event_date" in k for k in formatted_filters.keys()):
                        if "7 days" in tile_title.lower() or "7d" in tile_title.lower():
                            formatted_filters[f"{explore}.event_date"] = "7 days"
                        elif "90 days" in tile_title.lower():
                            formatted_filters[f"{explore}.event_date"] = "90 days"
                        else:
                            formatted_filters[f"{explore}.event_date"] = "30 days"
                
                formatted_sorts = []
                if isinstance(sorts, list):
                    for s in sorts:
                        parts = s.split()
                        col = parts[0]
                        order = f" {parts[1]}" if len(parts) > 1 else ""
                        res_col = resolve_field(col, explore)
                        if res_col:
                            formatted_sorts.append(f"{res_col}{order}")

                vis_type = "looker_grid"
                if any("date" in f or "time" in f for f in formatted_fields) and len(formatted_fields) >= 2:
                    vis_type = "looker_line"
                elif any("country" in f or "game" in f or "name" in f or "category" in f for f in formatted_fields) and len(formatted_fields) >= 2:
                    vis_type = "looker_column"
                elif len(formatted_fields) == 1:
                    vis_type = "single_value"

                vis_config = {
                    "type": vis_type,
                    "show_view_names": False,
                    "show_y_axis_labels": True,
                    "show_y_axis_ticks": True,
                    "show_x_axis_label": True,
                    "show_x_axis_ticks": True,
                    "legend_position": "center"
                }

                try:
                    q_body = models40.WriteQuery(
                        model=model_name,
                        view=explore,
                        fields=formatted_fields,
                        filters=formatted_filters,
                        sorts=formatted_sorts,
                        limit=limit,
                        vis_config=vis_config
                    )
                    q = sdk.create_query(body=q_body)
                    elem_body = models40.WriteDashboardElement(
                        dashboard_id=str(dash.id),
                        type="vis",
                        title=tile_title,
                        query_id=q.id,
                        result_maker=models40.WriteResultMakerWithIdVisConfigAndDynamicFields(
                            vis_config=vis_config,
                            filterables=filterables_list if filterables_list else None
                        )
                    )
                    elem = sdk.create_dashboard_element(body=elem_body)
                    created_elements.append({
                        "id": elem.id,
                        "title": tile_title,
                        "query_id": q.id,
                        "fields": formatted_fields
                    })
                    log_thought(f"Added tile '{tile_title}'")
                except Exception as tile_err:
                    log_thought(f"Warning: Could not create tile '{tile_title}': {tile_err}")
        
        # 4. Auto-organize Grid Layout
        organize_dashboard_layout(sdk, dash.id)

        # Generate Embed SSO URL
        embed_mgr = LookerEmbedManager()
        target_url = f"{LOOKER_INSTANCE_URI.rstrip('/')}/embed/dashboards/{dash.id}"
        signed_url = embed_mgr.generate_signed_url(
            target_url=target_url,
            user_id="embed_admin",
            first_name="Gaming",
            last_name="Analyst"
        )
        
        dashboard_meta = {
            "id": f"custom_{dash.id}",
            "looker_id": str(dash.id),
            "title": title,
            "description": description,
            "url": f"/embed/dashboards/{dash.id}",
            "signed_url": signed_url,
            "icon": "LayoutDashboard",
            "tiles_count": len(created_elements),
            "tiles": created_elements,
            "filters": created_filters
        }
        
        ACTIVE_DASHBOARDS_REGISTRY["latest"] = dashboard_meta
        if session_id:
            ACTIVE_DASHBOARDS_REGISTRY[session_id] = dashboard_meta
        
        if data_queue:
            data_queue.put({
                "type": "dashboard_created",
                "dashboard": dashboard_meta
            })
            
        return {
            "status": "success",
            "message": f"Successfully created Looker dashboard '{title}' (ID: {dash.id}) with {len(created_elements)} live tiles and {len(created_filters)} filter(s).",
            "dashboard_id": str(dash.id),
            "dashboard": dashboard_meta,
            "embed_url": signed_url
        }
    except Exception as e:
        error_msg = f"Failed to create Looker dashboard: {e}"
        log_thought(error_msg)
        return {"status": "error", "error": error_msg}



def edit_looker_dashboard(
    dashboard_id: str = None,
    title: str = None,
    description: str = None,
    add_tiles: list = None,
    modify_tiles: list = None,
    delete_tile_titles: list = None,
    add_filters: list = None,
    delete_filters: list = None,
    delete_filter_names: list = None,
    session_id: str = None
):
    """
    Edits an existing Looker dashboard by renaming, modifying existing tiles, adding/removing tiles, or adding/removing filters.
    """
    try:
        import looker_sdk
        from looker_sdk import models40
        from looker_embed import LookerEmbedManager
        
        target_id = dashboard_id
        if isinstance(target_id, list):
            if not delete_filters:
                delete_filters = target_id
            target_id = None
        elif target_id and not str(target_id).replace("custom_", "").isdigit():
            if not delete_filters and any(kw in str(target_id).lower() for kw in ["filter", "game", "date"]):
                delete_filters = [str(target_id)]
            target_id = None

        if not target_id:
            active_dash = (ACTIVE_DASHBOARDS_REGISTRY.get(session_id) if session_id else None) or ACTIVE_DASHBOARDS_REGISTRY.get("latest")
            if active_dash:
                target_id = active_dash.get("looker_id")
            
        if not target_id:
            return {"status": "error", "error": "No dashboard_id provided and no active dashboard found in session."}
            
        clean_id = str(target_id).replace("custom_", "")
        log_thought(f"Looker MCP: Editing Dashboard ID {clean_id}...")
        
        if LOOKER_INSTANCE_URI:
            os.environ["LOOKERSDK_BASE_URL"] = LOOKER_INSTANCE_URI
        if LOOKER_CLIENT_ID:
            os.environ["LOOKERSDK_CLIENT_ID"] = LOOKER_CLIENT_ID
        if LOOKER_CLIENT_SECRET:
            os.environ["LOOKERSDK_CLIENT_SECRET"] = LOOKER_CLIENT_SECRET
            
        sdk = looker_sdk.init40()
        explore_name = EXPLORE or "events"
        model_name = LOOKML_MODEL or "gaming"
        
        # 1. Update Title / Description if provided
        if (title and isinstance(title, str) and not title.isdigit() and title != clean_id) or (description and isinstance(description, str) and not description.isdigit()):
            update_body = models40.WriteDashboard()
            if title and isinstance(title, str) and not title.isdigit() and title != clean_id:
                update_body.title = title
            if description and isinstance(description, str) and not description.isdigit():
                update_body.description = description
            try:
                sdk.update_dashboard(clean_id, body=update_body)
                log_thought(f"Updated dashboard metadata (Title: '{title}')")
            except Exception as meta_err:
                log_thought(f"Warning: Could not update dashboard title/description: {meta_err}")

        def _as_list(val):
            if val is None:
                return []
            if isinstance(val, list):
                return val
            if isinstance(val, (str, int, float)):
                return [val]
            try:
                return list(val)
            except Exception:
                return [val]

        dash = sdk.dashboard(clean_id)
        existing_elements = dash.dashboard_elements or []
        
        # 2. Delete Tiles if requested
        del_tiles_list = _as_list(delete_tile_titles)
        deleted_count = 0
        if del_tiles_list:
            for del_target in del_tiles_list:
                del_str = str(del_target).lower().strip()
                for el in existing_elements:
                    if str(el.id) == del_str or (el.title and del_str in el.title.lower()):
                        try:
                            sdk.delete_dashboard_element(str(el.id))
                            deleted_count += 1
                            log_thought(f"Deleted tile '{el.title}' (ID: {el.id})")
                        except Exception as del_err:
                            log_thought(f"Warning: Could not delete tile {el.id}: {del_err}")

        # 3. Delete Filters if requested
        to_delete_filters = _as_list(delete_filters) + _as_list(delete_filter_names)
        if to_delete_filters:
            dash = sdk.dashboard(clean_id)
            existing_filters = dash.dashboard_filters or []
            for del_f in to_delete_filters:
                del_f_str = str(del_f).lower().strip()
                for df in existing_filters:
                    if str(df.id) == del_f_str or (df.name and del_f_str in df.name.lower()) or (df.title and del_f_str in df.title.lower()):
                        try:
                            sdk.delete_dashboard_filter(str(df.id))
                            log_thought(f"Deleted dashboard filter '{df.name}' (ID: {df.id})")
                        except Exception as del_f_err:
                            log_thought(f"Warning: Could not delete filter {df.id}: {del_f_err}")

        # 4. Add Dashboard Filters (with duplicate collision prevention)
        add_filters_list = _as_list(add_filters)
        if add_filters_list:
            dash = sdk.dashboard(clean_id)
            existing_filters = dash.dashboard_filters or []
            existing_filt_names = {str(df.name).lower().strip() for df in existing_filters if df.name}
            existing_filt_titles = {str(df.title).lower().strip() for df in existing_filters if df.title}
            existing_filt_dims = {str(df.dimension).lower().strip() for df in existing_filters if df.dimension}
            
            for filt in add_filters_list:
                if not isinstance(filt, dict):
                    continue
                filt_name = filt.get("name", "Filter")
                filt_title = filt.get("title", filt_name)
                filt_dim = filt.get("dimension") or filt.get("field", f"{explore_name}.event_date")
                filt_def = filt.get("default_value", "30 days" if "date" in filt_dim else "")
                
                # Check for existing filter
                if filt_name.lower().strip() in existing_filt_names or filt_title.lower().strip() in existing_filt_titles or filt_dim.lower().strip() in existing_filt_dims:
                    log_thought(f"Filter '{filt_name}' on {filt_dim} already exists on dashboard. Skipping duplicate creation.")
                    continue
                    
                try:
                    df = sdk.create_dashboard_filter(body=models40.CreateDashboardFilter(
                        dashboard_id=clean_id,
                        name=filt_name,
                        title=filt_title,
                        type="field_filter",
                        model=model_name,
                        explore=explore_name,
                        dimension=filt_dim,
                        default_value=filt_def,
                        allow_multiple_values=True,
                        ui_config={"type": "advanced" if "date" in filt_dim else "dropdown_menu", "display": "inline"}
                    ))
                    existing_filt_names.add(filt_name.lower().strip())
                    existing_filt_titles.add(filt_title.lower().strip())
                    existing_filt_dims.add(filt_dim.lower().strip())
                    log_thought(f"Added dashboard filter '{filt_name}' on {filt_dim}")
                except Exception as filter_err:
                    log_thought(f"Warning: Could not add filter '{filt_name}': {filter_err}")

        # Refresh dashboard filters for wiring
        dash = sdk.dashboard(clean_id)
        current_filters = dash.dashboard_filters or []
        filterables_list = []
        for df in current_filters:
            if df.name and df.dimension:
                filterables_list.append(
                    models40.ResultMakerFilterables(
                        model=model_name,
                        view=explore_name,
                        listen=[models40.ResultMakerFilterablesListen(
                            dashboard_filter_name=df.name,
                            field=df.dimension
                        )]
                    )
                )

        # Wire/rewire existing tiles to the current active filters if filters were added or deleted
        if (add_filters or to_delete_filters):
            for el in dash.dashboard_elements or []:
                if el.type == "vis" and el.result_maker:
                    vis_cfg = el.result_maker.vis_config or {}
                    try:
                        sdk.update_dashboard_element(
                            dashboard_element_id=str(el.id),
                            body=models40.WriteDashboardElement(
                                result_maker=models40.WriteResultMakerWithIdVisConfigAndDynamicFields(
                                    vis_config=vis_cfg,
                                    filterables=filterables_list if filterables_list else None
                                )
                            )
                        )
                        log_thought(f"Wired existing tile '{el.title}' to dashboard filters")
                    except Exception as wire_err:
                        log_thought(f"Warning: Could not wire tile {el.id}: {wire_err}")

        explore_info = sdk.lookml_model_explore(lookml_model_name=model_name, explore_name=explore_name)
        valid_dims = {d.name for d in explore_info.fields.dimensions}
        valid_meas = {m.name for m in explore_info.fields.measures}
        valid_all = valid_dims | valid_meas
        valid_short = {k.split('.')[-1]: k for k in valid_all}

        FIELD_ALIASES = {
            "system_game_name": "game_name",
            "game": "game_name",
            "dau": "number_of_users",
            "revenue": "total_revenue",
            "iap": "total_iap_revenue",
            "ads": "total_ad_revenue",
            "sessions": "number_of_sesssions",
            "number_of_sessions": "number_of_sesssions",
            "date": "event_date",
        }

        def resolve_field(raw_field: str, default_explore: str) -> str:
            raw_clean = raw_field.replace(f"{default_explore}.", "").replace(f"{default_explore}_", "")
            raw_base = raw_clean.split('.')[-1].lower()
            mapped_base = FIELD_ALIASES.get(raw_base, raw_base)
            candidate = f"{default_explore}.{mapped_base}"
            if candidate in valid_all:
                return candidate
            if mapped_base in valid_short:
                return valid_short[mapped_base]
            if raw_field in valid_all:
                return raw_field
            return candidate if not valid_all else None

        # 5. Modify Existing Tiles (In-place updates)
        modified_count = 0
        mod_tiles_list = _as_list(modify_tiles)
        if mod_tiles_list:
            dash = sdk.dashboard(clean_id)
            existing_elements = dash.dashboard_elements or []
            
            for mod in mod_tiles_list:
                if not isinstance(mod, dict):
                    continue
                target_title = str(mod.get("tile_title", "")).lower().strip()
                if not target_title:
                    continue
                    
                target_el = None
                for el in existing_elements:
                    if str(el.id) == target_title or (el.title and target_title in el.title.lower()):
                        target_el = el
                        break
                        
                if not target_el or not target_el.query_id:
                    log_thought(f"Warning: Could not find tile matching '{target_title}' to modify.")
                    continue
                    
                try:
                    old_query = sdk.query(target_el.query_id)
                    new_title = mod.get("new_title") or target_el.title
                    
                    # Updated fields
                    raw_fields = mod.get("fields")
                    if raw_fields and isinstance(raw_fields, list):
                        updated_fields = [resolve_field(f, explore_name) for f in raw_fields if resolve_field(f, explore_name)]
                    else:
                        updated_fields = list(old_query.fields or [])
                        
                    # Updated filters
                    updated_filters = dict(old_query.filters or {})
                    if "timeframe" in mod and mod["timeframe"]:
                        updated_filters[f"{explore_name}.event_date"] = str(mod["timeframe"]).strip("'").strip('"')
                    if "filters" in mod and isinstance(mod["filters"], dict):
                        for k, v in mod["filters"].items():
                            res_k = resolve_field(k, explore_name)
                            if res_k:
                                updated_filters[res_k] = str(v).strip("'").strip('"')
                                
                    # Updated vis_config
                    vis_cfg = dict(old_query.vis_config or {})
                    if "vis_type" in mod and mod["vis_type"]:
                        vis_cfg["type"] = mod["vis_type"]
                    elif updated_fields:
                        if any("date" in f for f in updated_fields) and len(updated_fields) >= 2:
                            vis_cfg["type"] = "looker_line"
                        elif any("country" in f or "game" in f for f in updated_fields) and len(updated_fields) >= 2:
                            vis_cfg["type"] = "looker_column"
                        elif len(updated_fields) == 1:
                            vis_cfg["type"] = "single_value"
                        else:
                            vis_cfg["type"] = "looker_grid"
                            
                    # Create new query with modified settings
                    q_body = models40.WriteQuery(
                        model=old_query.model or model_name,
                        view=old_query.view or explore_name,
                        fields=updated_fields if updated_fields else [f"{explore_name}.count"],
                        filters=updated_filters,
                        sorts=old_query.sorts or [],
                        limit=old_query.limit or "500",
                        vis_config=vis_cfg
                    )
                    new_q = sdk.create_query(body=q_body)
                    
                    # Update dashboard element
                    sdk.update_dashboard_element(
                        dashboard_element_id=str(target_el.id),
                        body=models40.WriteDashboardElement(
                            title=new_title,
                            query_id=new_q.id,
                            result_maker=models40.WriteResultMakerWithIdVisConfigAndDynamicFields(
                                vis_config=vis_cfg,
                                filterables=filterables_list if filterables_list else None
                            )
                        )
                    )
                    modified_count += 1
                    log_thought(f"Modified tile '{target_el.title}' ➔ '{new_title}' (Query: {new_q.id})")
                except Exception as mod_err:
                    log_thought(f"Warning: Could not modify tile '{target_title}': {mod_err}")

        # 6. Add New Tiles (with smart de-duplication)
        added_count = 0
        if add_tiles:
            dash = sdk.dashboard(clean_id)
            existing_elements = dash.dashboard_elements or []
            existing_titles = [el.title.lower().strip() for el in existing_elements if el.title]

            def is_duplicate_tile(new_t: str, existing_list: list) -> bool:
                import re
                nt = new_t.lower().strip()
                if nt in existing_list:
                    return True
                clean_nt = re.sub(r'\(.*?\)', '', nt).strip()
                for ext in existing_list:
                    clean_ext = re.sub(r'\(.*?\)', '', ext).strip()
                    if clean_nt == clean_ext or (len(clean_nt) > 4 and clean_nt in clean_ext) or (len(clean_ext) > 4 and clean_ext in clean_nt):
                        return True
                return False

            add_tiles_list = _as_list(add_tiles)
            for idx, raw_tile in enumerate(add_tiles_list):
                if not isinstance(raw_tile, dict):
                    if isinstance(raw_tile, str) and raw_tile.strip():
                        raw_tile = {"title": raw_tile.strip(), "fields": [f"{explore_name}.count"]}
                    else:
                        continue
                tile = raw_tile
                tile_title = tile.get("title", f"New Metric {idx+1}")
                if is_duplicate_tile(tile_title, existing_titles):
                    log_thought(f"Tile '{tile_title}' is already on the dashboard. Skipping duplicate creation.")
                    continue
                explore = tile.get("explore") or explore_name
                raw_fields = tile.get("fields") or []
                raw_filters = tile.get("filters") or {}
                sorts = tile.get("sorts") or []
                limit = str(tile.get("limit", "500"))

                formatted_fields = [resolve_field(f, explore) for f in raw_fields if resolve_field(f, explore)] or [f"{explore}.count"]
                formatted_filters = {}
                if isinstance(raw_filters, dict):
                    for k, v in raw_filters.items():
                        res_k = resolve_field(k, explore)
                        if res_k:
                            formatted_filters[res_k] = str(v).strip("'").strip('"')

                if explore == "events" and not any("event_date" in k for k in formatted_filters.keys()):
                    formatted_filters[f"{explore}.event_date"] = "30 days"

                formatted_sorts = []
                for s in sorts:
                    parts = s.split()
                    res_col = resolve_field(parts[0], explore)
                    if res_col:
                        formatted_sorts.append(f"{res_col}{' ' + parts[1] if len(parts)>1 else ''}")

                vis_type = "looker_grid"
                if any("date" in f for f in formatted_fields) and len(formatted_fields) >= 2:
                    vis_type = "looker_line"
                elif any("country" in f or "game" in f for f in formatted_fields) and len(formatted_fields) >= 2:
                    vis_type = "looker_column"
                elif len(formatted_fields) == 1:
                    vis_type = "single_value"

                vis_config = {
                    "type": vis_type,
                    "show_view_names": False,
                    "show_y_axis_labels": True,
                    "show_y_axis_ticks": True,
                    "show_x_axis_label": True,
                    "show_x_axis_ticks": True,
                    "legend_position": "center"
                }

                try:
                    q_body = models40.WriteQuery(
                        model=model_name,
                        view=explore,
                        fields=formatted_fields,
                        filters=formatted_filters,
                        sorts=formatted_sorts,
                        limit=limit,
                        vis_config=vis_config
                    )
                    q = sdk.create_query(body=q_body)
                    elem_body = models40.WriteDashboardElement(
                        dashboard_id=clean_id,
                        type="vis",
                        title=tile_title,
                        query_id=q.id,
                        result_maker=models40.WriteResultMakerWithIdVisConfigAndDynamicFields(
                            vis_config=vis_config,
                            filterables=filterables_list if filterables_list else None
                        )
                    )
                    sdk.create_dashboard_element(body=elem_body)
                    added_count += 1
                    log_thought(f"Added new tile '{tile_title}'")
                except Exception as tile_err:
                    log_thought(f"Warning: Could not add tile '{tile_title}': {tile_err}")

        # 7. Auto-organize Grid Layout
        organize_dashboard_layout(sdk, clean_id)

        # Fetch refreshed dashboard metadata
        dash_final = sdk.dashboard(clean_id)
        embed_mgr = LookerEmbedManager()
        target_url = f"{LOOKER_INSTANCE_URI.rstrip('/')}/embed/dashboards/{clean_id}"
        signed_url = embed_mgr.generate_signed_url(
            target_url=target_url,
            user_id="embed_admin",
            first_name="Gaming",
            last_name="Analyst"
        )
        
        dashboard_meta = {
            "id": f"custom_{clean_id}",
            "looker_id": clean_id,
            "title": dash_final.title,
            "description": dash_final.description,
            "url": f"/embed/dashboards/{clean_id}",
            "signed_url": signed_url,
            "icon": "LayoutDashboard",
            "tiles_count": len(dash_final.dashboard_elements or []),
            "filters_count": len(dash_final.dashboard_filters or [])
        }
        
        ACTIVE_DASHBOARDS_REGISTRY["latest"] = dashboard_meta
        if session_id:
            ACTIVE_DASHBOARDS_REGISTRY[session_id] = dashboard_meta
        
        if data_queue:
            data_queue.put({
                "type": "dashboard_created",
                "dashboard": dashboard_meta
            })
            
        return {
            "status": "success",
            "message": f"Successfully updated Looker dashboard '{dash_final.title}' (ID: {clean_id}). Added {added_count} tile(s), modified {modified_count} tile(s), removed {deleted_count} tile(s), active tiles: {len(dash_final.dashboard_elements or [])}.",
            "dashboard_id": clean_id,
            "dashboard": dashboard_meta,
            "embed_url": signed_url
        }
    except Exception as e:
        error_msg = f"Failed to edit Looker dashboard: {e}"
        log_thought(error_msg)
        return {"status": "error", "error": error_msg}


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

    request = _create_chat_request(inline_context, messages)

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
            
    return default

AVAILABLE_MODELS = [
    {
        "id": "gemini-3.6-flash",
        "name": "Gemini 3.6 Flash",
        "provider": "Google DeepMind",
        "badge": "Default",
        "icon": "Sparkles",
        "description": "Ultra-fast multimodal reasoning with high-precision tool calling.",
        "is_default": True
    },
    {
        "id": "qwen3.8-27b",
        "name": "Qwen 3.8 27B",
        "provider": "Alibaba Cloud / Open Weights",
        "badge": "Specialist",
        "icon": "Cpu",
        "description": "Specialized open-weights model optimized for coding, Spanner GQL, and data analytics.",
        "is_default": False
    },
    {
        "id": "gemini-3.5-flash",
        "name": "Gemini 3.5 Flash",
        "provider": "Google DeepMind",
        "badge": "Fast",
        "icon": "Zap",
        "description": "Standard low-latency model for high-throughput queries.",
        "is_default": False
    },
    {
        "id": "gemini-1.5-pro",
        "name": "Gemini 1.5 Pro",
        "provider": "Google DeepMind",
        "badge": "Reasoning",
        "icon": "Brain",
        "description": "Deep multi-hop reasoning and long-context synthesis.",
        "is_default": False
    },
    {
        "id": "qwen2.5-72b",
        "name": "Qwen 2.5 72B",
        "provider": "Alibaba Cloud / Open Weights",
        "badge": "High Capacity",
        "icon": "Cpu",
        "description": "High-capacity open model for complex multi-domain intelligence.",
        "is_default": False
    }
]

def resolve_model(model_name: str = None) -> dict:
    """
    Resolves requested model name to canonical metadata and backend execution configuration.
    """
    if not model_name:
        model_name = os.getenv("DEFAULT_MODEL") or os.getenv("DEEP_MODE_MODEL", "gemini-3.6-flash")
    
    clean = str(model_name).lower().strip()
    if "qwen3.8" in clean or "qwen-3.8" in clean or clean == "qwen" or "qwen3.8-27b" in clean:
        return {
            "id": "qwen3.8-27b",
            "name": "Qwen 3.8 27B",
            "backend_type": "qwen",
            "gemini_fallback": "gemini-3.6-flash",
            "provider": "Alibaba Cloud / Open Weights",
            "icon": "Cpu",
            "description": "Specialized open-weights model optimized for coding, Spanner GQL, and data analytics."
        }
    elif "qwen2.5" in clean or "qwen-2.5" in clean or "qwen2.5-72b" in clean:
        return {
            "id": "qwen2.5-72b",
            "name": "Qwen 2.5 72B",
            "backend_type": "qwen",
            "gemini_fallback": "gemini-3.6-flash",
            "provider": "Alibaba Cloud / Open Weights",
            "icon": "Cpu",
            "description": "High-capacity open model for complex multi-domain intelligence."
        }
    elif "1.5-pro" in clean or "gemini-1.5-pro" in clean:
        return {
            "id": "gemini-1.5-pro",
            "name": "Gemini 1.5 Pro",
            "backend_type": "gemini",
            "gemini_target": "gemini-1.5-pro",
            "provider": "Google DeepMind",
            "icon": "Brain",
            "description": "Deep multi-hop reasoning and long-context synthesis."
        }
    elif "3.5-flash" in clean or "gemini-3.5-flash" in clean:
        return {
            "id": "gemini-3.5-flash",
            "name": "Gemini 3.5 Flash",
            "backend_type": "gemini",
            "gemini_target": "gemini-3.5-flash",
            "provider": "Google DeepMind",
            "icon": "Zap",
            "description": "Standard low-latency model for high-throughput queries."
        }
    else:
        return {
            "id": "gemini-3.6-flash",
            "name": "Gemini 3.6 Flash",
            "backend_type": "gemini",
            "gemini_target": "gemini-3.6-flash",
            "provider": "Google DeepMind",
            "icon": "Sparkles",
            "description": "Ultra-fast multimodal reasoning with high-precision tool calling."
        }

def create_model_session(model_name: str = None, tools: list = None, tool_config = None, system_instruction: str = ""):
    """
    Creates a GenerativeModel session configured for the requested model with persona adaptation.
    """
    model_info = resolve_model(model_name)
    m_name = model_info["name"]
    
    augmented_sys_inst = system_instruction or ""
    if model_info["backend_type"] == "qwen":
        qwen_directive = f"### LLM BACKEND EMULATION / DIRECTIVE: {m_name}\nYou are {m_name}, an expert open-weights reasoning and analytics engine. Deliver mathematically precise LookML aggregations, accurate Spanner GQL syntax, and clean structured reasoning.\n"
        augmented_sys_inst = qwen_directive + "\n" + augmented_sys_inst
        
    target_model = model_info.get("gemini_target") or model_info.get("gemini_fallback", "gemini-3.6-flash")
    
    kwargs = {}
    if tools:
        kwargs["tools"] = tools
    if tool_config:
        kwargs["tool_config"] = tool_config
    if augmented_sys_inst:
        kwargs["system_instruction"] = augmented_sys_inst
        
    model = GenerativeModel(target_model, **kwargs)
    return model, model_info

def run_deep_analysis(question: str, model_name: str = None, session_id: str = None):
    """Runs a deep analysis using a planning agent loop."""
    model_info = resolve_model(model_name)
    log_thought(f"Entering Deep Analysis Mode [{model_info['name']}] - Activating reasoning engine to plan and execute queries across Looker metrics and Spanner Graph...")
    
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
    
    create_looker_dashboard_func = FunctionDeclaration(
        name="create_looker_dashboard",
        description="Creates a new custom Looker dashboard on the fly with specified visual tiles, metrics, dimensions, and interactive dashboard-level filters.",
        parameters={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the new dashboard (e.g. 'Season 4 LiveOps War Room', 'Top Spending Whales Analysis')"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of the dashboard's purpose"
                },
                "filters": {
                    "type": "array",
                    "description": "List of interactive dashboard-level filters (e.g. [{'name': 'Date Range', 'dimension': 'events.event_date', 'default_value': '30 days'}, {'name': 'Game Title', 'dimension': 'events.game_name'}])",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Filter display label (e.g. 'Date Range', 'Game Title')"},
                            "dimension": {"type": "string", "description": "LookML dimension (e.g. 'events.event_date', 'events.game_name', 'events.country')"},
                            "default_value": {"type": "string", "description": "Default filter value (e.g. '30 days', 'Lookerwood Farm')"}
                        },
                        "required": ["name", "dimension"]
                    }
                },
                "tiles": {
                    "type": "array",
                    "description": "List of tile configurations to add to the dashboard",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Tile title"},
                            "explore": {"type": "string", "description": "LookML explore (e.g. 'events', 'gaming_hybrid_search', 'session_facts')"},
                            "fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of LookML dimension and measure field names (e.g. ['events.event_date', 'events.number_of_users'])"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Key-value filter mapping (e.g. {'events.event_date': '30 days', 'events.game_name': 'Lookup Battle Royale'})"
                            },
                            "limit": {"type": "string", "description": "Query row limit (default '500')"}
                        },
                        "required": ["title", "fields"]
                    }
                }
            },
            "required": ["title", "tiles"]
        }
    )

    edit_looker_dashboard_func = FunctionDeclaration(
        name="edit_looker_dashboard",
        description="Edits an existing Looker dashboard in place by adding new tiles, modifying existing tiles (timeframe, chart type, fields), removing tiles, renaming, or adding interactive dashboard filters. Use this whenever the user asks to modify, add to, or refine an existing/recently created dashboard.",
        parameters={
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "The ID of the existing dashboard to edit (e.g. '124' or 'custom_124'). If omitted, automatically modifies the active dashboard."
                },
                "title": {
                    "type": "string",
                    "description": "Optional new title if renaming the dashboard"
                },
                "description": {
                    "type": "string",
                    "description": "Optional updated description"
                },
                "modify_tiles": {
                    "type": "array",
                    "description": "List of tile modifications to apply to existing tiles in place (e.g. changing timeframe from 30d to 90d, changing chart type, updating fields).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tile_title": {"type": "string", "description": "Current title or substring of the tile to modify"},
                            "new_title": {"type": "string", "description": "New title for the tile if renaming"},
                            "timeframe": {"type": "string", "description": "New timeframe filter (e.g. '90 days', '7 days', '30 days')"},
                            "filters": {"type": "object", "description": "Updated query filters dictionary"},
                            "fields": {"type": "array", "items": {"type": "string"}, "description": "Updated list of LookML field names"},
                            "vis_type": {"type": "string", "description": "Visualization type ('looker_line', 'looker_column', 'single_value', 'looker_grid', 'looker_area', 'looker_pie')"}
                        },
                        "required": ["tile_title"]
                    }
                },
                "add_tiles": {
                    "type": "array",
                    "description": "List of ONLY the brand-new visual tile configurations to append to the dashboard. DO NOT include tiles that already exist on the dashboard.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Tile title"},
                            "explore": {"type": "string", "description": "LookML explore (e.g. 'events')"},
                            "fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of LookML dimension and measure field names"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Key-value filter mapping"
                            },
                            "limit": {"type": "string", "description": "Query row limit"}
                        },
                        "required": ["title", "fields"]
                    }
                },
                "delete_tile_titles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tile titles or IDs to remove from the dashboard"
                },
                "add_filters": {
                    "type": "array",
                    "description": "List of interactive dashboard-level filters to add",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Filter label (e.g. 'Game Title', 'Date Range')"},
                            "dimension": {"type": "string", "description": "LookML dimension (e.g. 'events.game_name', 'events.event_date')"},
                            "default_value": {"type": "string", "description": "Default value"}
                        },
                        "required": ["name", "dimension"]
                    }
                },
                "delete_filters": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of dashboard filter names or titles to remove from the dashboard (e.g. ['Game Title', 'Date Range'])"
                }
            }
        }
    )
    
    funcs = [get_insights_func, generate_chart_func, create_looker_dashboard_func, edit_looker_dashboard_func]
    
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

    # 1. Resolve Active Dashboard & History from Session
    import re
    from conversation_manager import ConversationManager
    from vertexai.generative_models import Content, Part

    conv_history = []
    active_dash = None
    if session_id:
        active_dash = ACTIVE_DASHBOARDS_REGISTRY.get(session_id)
        conv_mgr = ConversationManager()
        raw_msgs = conv_mgr.get_conversation(session_id)
        
        # Scan history for active dashboard if not in memory registry
        if not active_dash:
            for m in reversed(raw_msgs):
                text = str(m.get("content", ""))
                match = re.search(r'/embed/dashboards/(\d+)', text) or re.search(r'Dashboard\s+(?:ID:?\s*)?(\d+)', text, re.IGNORECASE)
                if match:
                    found_id = match.group(1)
                    active_dash = {"looker_id": found_id, "title": f"Dashboard {found_id}"}
                    ACTIVE_DASHBOARDS_REGISTRY[session_id] = active_dash
                    ACTIVE_DASHBOARDS_REGISTRY["latest"] = active_dash
                    break

        # Format past turns into Gemini Content history
        for m in raw_msgs:
            if m == raw_msgs[-1] and m.get("role") == "user" and m.get("content") == question:
                continue
            role = "user" if m.get("role") == "user" else "model"
            msg_text = m.get("content", "")
            if msg_text:
                conv_history.append(Content(role=role, parts=[Part.from_text(msg_text)]))

    if not active_dash:
        active_dash = ACTIVE_DASHBOARDS_REGISTRY.get("latest")

    # Ensure Vertex AI has fresh credentials and correct region
    init_vertex_ai()

    # 2. Inject active dashboard context and capabilities matrix into system instruction
    base_system_inst = AGENT_CONFIG.get('_computed', {}).get('deep_mode', "You are a Senior Data Analyst.")
    base_system_inst += """

### DASHBOARD BUILDER CAPABILITIES & BOUNDARIES (STRICT TOOLSET LIMITS):
You have programmatic access to Looker to build and edit dashboards via `create_looker_dashboard` and `edit_looker_dashboard`.

WHAT YOU CAN DO AUTOMATICALLY:
1. CREATE DASHBOARDS: Build brand-new dashboards with visual tiles and filters (`create_looker_dashboard`).
2. ADD NEW TILES: Append new chart or KPI tiles (`edit_looker_dashboard` with `add_tiles`).
3. MODIFY EXISTING TILES: Update timeframe (e.g. 30d to 90d), filters, fields, or chart visualization types on existing tiles (`edit_looker_dashboard` with `modify_tiles`).
4. REMOVE TILES: Delete specific tiles by title (`edit_looker_dashboard` with `delete_tile_titles`).
5. ADD FILTERS: Add interactive dashboard-level filters (`edit_looker_dashboard` with `add_filters`).
6. REMOVE FILTERS: Delete existing dashboard filters (`edit_looker_dashboard` with `delete_filters`).
7. RENAME / RE-DESCRIBE: Update dashboard title or description (`edit_looker_dashboard` with `title` or `description`).
8. AUTOMATIC GRID LAYOUT: The system automatically arranges single-value KPIs across the top (width 4, height 3), main charts in the middle (width 6, height 6), and data tables across the bottom (width 12, height 7).

WHAT YOU CANNOT DO AUTOMATICALLY (NEVER pretend or claim to do these!):
1. CUSTOM PIXEL-PERFECT DRAG-AND-DROP RESIZING: When a user asks for arbitrary custom pixel dimensions (e.g. 500x300px), explain that the system automatically organizes tiles into an optimal responsive 12-column grid and guide them to click the live dashboard link to drag-and-drop or resize tiles in Looker's visual editor if they want custom sizes.
2. AD-HOC LOOKML CODE GENERATION: You cannot write new dimension or measure definitions into LookML files (.lkml) on the fly. You can only query existing fields in the model.
3. CROSS-EXPLORE VISUAL JOINING: Each tile queries one LookML explore.

TRANSPARENCY & HONESTY RULES:
- Always be completely transparent about what actions you performed using the tools.
- When an operation is performed (e.g. adding/modifying/removing a tile or filter), state the exact action taken.
- If a user asks for an unsupported capability (e.g. custom tile layout coordinates), politely explain what the tool can do and provide the direct link to the dashboard for manual UI adjustments.
"""

    if active_dash:
        dash_id = active_dash.get("looker_id", "")
        dash_title = active_dash.get("title", "")
        dash_tiles = [t.get("title") for t in active_dash.get("tiles", []) if t.get("title")]
        base_system_inst += f"\n\n### ACTIVE DASHBOARD CONTEXT:\nThe user currently has active Dashboard ID: {dash_id} ('{dash_title}').\nExisting tiles on this dashboard: {dash_tiles}.\nCRITICAL RULES FOR REFINEMENTS / EDITS:\n1. When the user asks to add new tiles to this dashboard, YOU MUST call `edit_looker_dashboard(dashboard_id='{dash_id}', add_tiles=[...])`.\n2. In `add_tiles`, pass ONLY the newly requested tile(s). DO NOT re-send the existing tiles ({dash_tiles}) in `add_tiles`!\n3. When the user asks to modify an existing tile's timeframe, fields, title, or chart type, call `edit_looker_dashboard(dashboard_id='{dash_id}', modify_tiles=[...])`.\n4. When the user asks to remove tiles, pass their titles in `delete_tile_titles`.\n5. When the user asks to remove filters, pass their names in `delete_filters`.\n6. When the user asks to add filters, pass them in `add_filters`.\n7. When the user explicitly requests to create a brand new separate dashboard, call `create_looker_dashboard`."

    model, model_info = create_model_session(
        model_name=model_name,
        tools=[analysis_tools],
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO
            )
        ),
        system_instruction=base_system_inst,
    )
    
    chat = model.start_chat(history=conv_history if conv_history else None)
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
                        elif fn.name == "create_looker_dashboard":
                            title_arg = extract_tool_argument(fn.args, ["title"])
                            desc_arg = extract_tool_argument(fn.args, ["description"], default="")
                            tiles_arg = extract_tool_argument(fn.args, ["tiles"], default=[])
                            filters_arg = extract_tool_argument(fn.args, ["filters"], default=[])
                            futures.append(executor.submit(create_looker_dashboard, title_arg, desc_arg, tiles_arg, filters_arg, session_id))
                        elif fn.name == "edit_looker_dashboard":
                            dash_id_arg = extract_tool_argument(fn.args, ["dashboard_id", "id", "dash_id"], default=None)
                            title_arg = extract_tool_argument(fn.args, ["title"], default=None)
                            desc_arg = extract_tool_argument(fn.args, ["description"], default=None)
                            add_tiles_arg = extract_tool_argument(fn.args, ["add_tiles"], default=[])
                            modify_tiles_arg = extract_tool_argument(fn.args, ["modify_tiles", "update_tiles"], default=[])
                            del_tiles_arg = extract_tool_argument(fn.args, ["delete_tile_titles", "delete_tiles"], default=[])
                            add_filters_arg = extract_tool_argument(fn.args, ["add_filters"], default=[])
                            del_filters_arg = extract_tool_argument(fn.args, ["delete_filters", "delete_filter_names"], default=[])
                            futures.append(executor.submit(
                                edit_looker_dashboard,
                                dashboard_id=dash_id_arg,
                                title=title_arg,
                                description=desc_arg,
                                add_tiles=add_tiles_arg,
                                modify_tiles=modify_tiles_arg,
                                delete_tile_titles=del_tiles_arg,
                                add_filters=add_filters_arg,
                                delete_filters=del_filters_arg,
                                session_id=session_id
                            ))
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
        import traceback
        traceback.print_exc()
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

def classify_subagent_route(question: str, history: list = None, active_dash: dict = None) -> dict:
    """
    Classifies user question into one of the specialized subagents:
    - 'dashboard_builder': Looker MCP dashboard creation, editing, tile layout, filter manipulation.
    - 'social_graph': Spanner Graph queries, Clans, Guilds, Friendships, Social Networks.
    - 'deep_research': Cross-domain multi-hop analysis combining telemetry metrics and social graph.
    - 'metrics_fast': Quantitative event metrics, DAU, revenue, retention, ARPU, sessions.
    """
    lc = question.lower().strip()
    
    # 1. Dashboard Builder Heuristics (Explicit dashboard management only)
    dashboard_explicit = [
        "create dashboard", "build dashboard", "make a dashboard", "new dashboard",
        "liveops dashboard", "war room", "command center", "add tile", "modify tile",
        "delete tile", "remove tile", "add a tile", "remove a tile", "delete a tile",
        "edit dashboard", "update dashboard", "tile layout", "resize tile",
        "to this dashboard", "on this dashboard", "in the dashboard", "from this dashboard",
        "to the dashboard", "on the dashboard", "in the dashboard", "from the dashboard",
        "add a country filter to this dashboard", "add a filter to this dashboard"
    ]
    if any(kw in lc for kw in dashboard_explicit):
        return {
            "subagent": "dashboard_builder",
            "name": "Dashboard Architect",
            "icon": "LayoutDashboard",
            "description": "Looker MCP LiveOps & Dashboard Builder"
        }
    
    # 2. Deep Research / Cross-domain Heuristics (Multi-hop cross-domain synthesis)
    social_keywords = ["clan", "guild", "friend", "social", "dragonslayer", "whales", "connections", "network", "titans", "leader", "officer", "member", "gamertag"]
    has_social = any(w in lc for w in social_keywords)
    
    # Check prior history for social context if current query is an ambiguous follow-up
    if not has_social and history:
        last_turn_text = ""
        for msg in reversed(history):
            if msg.get("role") == "user":
                last_turn_text = msg.get("content", "").lower()
                break
        if any(w in last_turn_text for w in ["clan", "guild", "friend", "social", "dragonslayer", "titans", "gamertag", "spanner"]):
            if any(w in lc for w in ["who", "leader", "officer", "members", "member", "friend", "connection", "show them", "their", "roster"]):
                has_social = True

    has_metrics = any(w in lc for w in ["revenue", "dau", "retention", "arpu", "monetization", "spending", "sessions", "installs"])
    is_investigation = any(w in lc for w in ["analyze the relationship", "investigate", "correlation", "root cause", "deep dive", "compare clan"])
    
    if (has_social and has_metrics and is_investigation) or (is_investigation and has_social):
        return {
            "subagent": "deep_research",
            "name": "Deep Research Analyst",
            "icon": "Brain",
            "description": "Strategic Cross-Domain Intelligence Specialist"
        }
        
    # 3. Social Graph Heuristics (Spanner Graph & Social relationships)
    if has_social:
        return {
            "subagent": "social_graph",
            "name": "Social Graph Specialist",
            "icon": "Share2",
            "description": "Spanner Graph & Clan Intelligence Specialist"
        }
        
    # 4. Metrics Fast Analytics (Default for all quantitative Looker queries, charts, breakdowns, time-series)
    return {
        "subagent": "metrics_fast",
        "name": "Metrics Analyst",
        "icon": "Zap",
        "description": "Quantitative Looker Metrics Specialist"
    }


def run_metrics_subagent(question: str, history: list = None, session_id: str = None, model_name: str = None):
    """Executes quantitative metrics query using Looker fast query pipeline."""
    model_info = resolve_model(model_name)
    log_thought(f"Metrics Analyst [{model_info['name']}]: Executing quantitative Looker metrics query...")
    has_text = False
    for chunk in fast_query(question, history=history or []):
        if chunk.get("type") == "thought":
            log_thought(chunk.get("content", ""))
        elif chunk.get("type") == "text":
            has_text = True
            yield chunk.get("content", "")
        elif chunk.get("type") == "data":
            content = chunk.get("content", {})
            rows = content.get("rows", [])
            schema = content.get("schema", {})
            explore_url = content.get("explore_url", "")
            
            # Format markdown table
            fields = []
            for f in schema.get("fields", []):
                fields.append(f.get("display_name") or f.get("name", "").split(".")[-1])
            if rows and fields:
                md_table = "\n\n| " + " | ".join(fields) + " |\n| " + " | ".join(["---"] * len(fields)) + " |\n"
                for r in rows[:25]:
                    row_vals = []
                    for f in fields:
                        val = r.get(f)
                        if val is None:
                            for k, v in r.items():
                                if k.lower().endswith(f.lower()) or f.lower().endswith(k.lower()):
                                    val = v
                                    break
                        row_vals.append(str(val if val is not None else ""))
                    md_table += "| " + " | ".join(row_vals) + " |\n"
                has_text = True
                yield md_table
                
            if explore_url:
                has_text = True
                yield f"\n\n[📊 Open in Looker Explore]({explore_url})\n"

            if data_queue:
                q_fields = []
                for f in schema.get("fields", []):
                    q_fields.append({
                        "name": f.get("name"),
                        "label": f.get("display_name") or f.get("name"),
                        "type": f.get("type_") or "string"
                    })
                if rows:
                    data_queue.put({
                        "type": "json_utils",
                        "data": {
                            "type": "json_table",
                            "data": {
                                "fields": q_fields,
                                "rows": rows
                            }
                        }
                    })
                if explore_url:
                    data_queue.put({
                        "type": "json_utils",
                        "data": {
                            "type": "json_link",
                            "url": explore_url
                        }
                    })
        elif chunk.get("type") == "chart":
            if data_queue:
                data_queue.put({
                    "type": "json_utils",
                    "data": {
                        "type": "json_chart",
                        "config": chunk.get("content", {})
                    }
                })


def run_social_graph_subagent(question: str, history: list = None, session_id: str = None, model_name: str = None):
    """Executes Spanner graph queries with bounded schema and automatic graph extraction."""
    model_info = resolve_model(model_name)
    log_thought(f"Social Graph Specialist [{model_info['name']}]: Querying Spanner Graph for clan and player network relationships...")
    
    sys_inst = AGENT_CONFIG.get('social_graph_analyst', {}).get('system_instruction', '')
    if not sys_inst:
        sys_inst = """You are the Social Graph & Clan Intelligence Specialist.
Query Spanner Graph using `query_spanner(sql)` to answer questions about Clans, Players, Memberships, and Friendships.
When returning relationship data, use column aliases like `player` and `friend` or `clan_name` and `gamertag` so the system automatically extracts 2D network graphs.
Accompany graph data with clean markdown summary tables. Always cite *Source: Spanner Graph Database*."""
        
    query_spanner_func = FunctionDeclaration(
        name="query_spanner",
        description="Executes a SQL or Graph query on Spanner Graph (Players, Clans, ClanMemberships, Friendships).",
        parameters={
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "The Spanner SQL or Graph query to execute."}
            },
            "required": ["sql"]
        }
    )
    
    model, model_info = create_model_session(
        model_name=model_name,
        tools=[Tool(function_declarations=[query_spanner_func])],
        tool_config=ToolConfig(
            function_calling_config=ToolConfig.FunctionCallingConfig(
                mode=ToolConfig.FunctionCallingConfig.Mode.AUTO
            )
        ),
        system_instruction=sys_inst
    )
    
    gemini_history = []
    for msg in (history or []):
        role = "user" if msg.get("role") == "user" else "model"
        content = msg.get("content", "")
        if content:
            gemini_history.append(Content(role=role, parts=[Part.from_text(content)]))
            
    chat = model.start_chat(history=gemini_history)
    response_stream = retry_api_call(
        lambda: chat.send_message(question, stream=True),
        retries=3,
        delay=2,
        error_msg="Social graph query failed"
    )
    
    for _ in range(5):
        function_calls = []
        text_parts = []
        for chunk in response_stream:
            for part in chunk.candidates[0].content.parts:
                if part.function_call:
                    function_calls.append(part.function_call)
                elif part.text:
                    text_parts.append(part.text)
                    log_thought(part.text)
                    
        if function_calls:
            tool_responses = []
            for fn in function_calls:
                if fn.name == "query_spanner":
                    sql_arg = extract_tool_argument(fn.args, ["sql"])
                    res = query_spanner(sql_arg)
                    tool_responses.append(Part.from_function_response(name=fn.name, response={"content": res}))
            response_stream = chat.send_message(tool_responses, stream=True)
        else:
            final_text = "".join(text_parts).strip()
            yield final_text
            break


def run_dashboard_subagent(question: str, history: list = None, session_id: str = None, model_name: str = None):
    """Executes Looker dashboard creation, tile modification, and automatic layout."""
    model_info = resolve_model(model_name)
    log_thought(f"Dashboard Architect [{model_info['name']}]: Processing Looker dashboard creation / refinement...")
    for chunk in run_deep_analysis(question, model_name=model_name, session_id=session_id):
        yield chunk


def run_deep_research_subagent(question: str, history: list = None, session_id: str = None, model_name: str = None):
    """Executes multi-hop strategic analysis across Looker metrics and Spanner graph."""
    model_info = resolve_model(model_name)
    log_thought(f"Deep Research Analyst [{model_info['name']}]: Performing cross-domain synthesis across Looker metrics and Spanner graph...")
    for chunk in run_deep_analysis(question, model_name=model_name, session_id=session_id):
        yield chunk


class RouterAgentApp:
    """
    Intelligent Autonomous Router App that dynamically selects the optimal specialized subagent.
    """
    def query(self, message: str, user_id: str = None, session_id: str = None, model_name: str = None):
        """Synchronous query method for Vertex AI Reasoning Engine Execution Service."""
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        stream = self.stream_query(message=message, user_id=user_id, session_id=session_id, model_name=model_name)
        text_parts = []
        for chunk in stream:
            if hasattr(chunk, 'text') and chunk.text:
                text_parts.append(chunk.text)
            elif isinstance(chunk, dict):
                if chunk.get("type") == "text":
                    text_parts.append(chunk.get("content", ""))
                elif "content" in chunk and isinstance(chunk["content"], dict):
                    for p in chunk["content"].get("parts", []):
                        if "text" in p:
                            text_parts.append(p["text"])
            elif isinstance(chunk, str):
                text_parts.append(chunk)
        return "".join(text_parts).strip()

    def stream_query(self, message: str, user_id: str = None, session_id: str = None, model_name: str = None):
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        # Load conversation history for multi-turn context
        history = []
        if session_id:
            try:
                from conversation_manager import conversation_manager
                raw_conv = conversation_manager.get_conversation(session_id)
                # The current message was already appended to conversation_manager in server.py,
                # so previous history is all messages before this pending user query.
                if raw_conv and raw_conv[-1].get("role") == "user" and raw_conv[-1].get("content") == message:
                    history = raw_conv[:-1]
                else:
                    history = raw_conv
            except Exception as e:
                log_debug(f"Could not load conversation history: {e}")

        active_dash = (ACTIVE_DASHBOARDS_REGISTRY.get(session_id) if session_id else None) or ACTIVE_DASHBOARDS_REGISTRY.get("latest")
        route = classify_subagent_route(message, history=history, active_dash=active_dash)
        subagent_key = route["subagent"]
        subagent_name = route["name"]
        subagent_desc = route["description"]
        subagent_icon = route["icon"]
        
        model_info = resolve_model(model_name)
        log_thought(f"🧭 Autonomous Router: Identified intent as '{subagent_name}' ({subagent_desc}) using [{model_info['name']}]. Activating specialized pipeline...")
        
        if data_queue:
            try:
                data_queue.put({
                    "type": "subagent_routed",
                    "subagent": subagent_key,
                    "name": subagent_name,
                    "description": subagent_desc,
                    "icon": subagent_icon,
                    "model": model_info["id"],
                    "model_name": model_info["name"]
                })
            except Exception as e:
                log_debug(f"Could not emit subagent_routed event: {e}")
                
        if subagent_key == "social_graph":
            yield from run_social_graph_subagent(message, history=history, session_id=session_id, model_name=model_name)
        elif subagent_key == "dashboard_builder":
            yield from run_dashboard_subagent(message, history=history, session_id=session_id, model_name=model_name)
        elif subagent_key == "deep_research":
            yield from run_deep_research_subagent(message, history=history, session_id=session_id, model_name=model_name)
        else:
            yield from run_metrics_subagent(message, history=history, session_id=session_id, model_name=model_name)

    def streaming_agent_run_with_events(self, request_json: str):
        """
        Streaming execution entrypoint for Gemini Enterprise (Dolphin / Agentspace).
        Parses request_json from GE and yields event dictionaries.
        """
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        try:
            req = json.loads(request_json) if isinstance(request_json, str) else (request_json or {})
        except Exception:
            req = {}

        message_data = req.get("message", {})
        user_text = ""
        if isinstance(message_data, dict):
            parts = message_data.get("parts", [])
            user_text = " ".join([p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p])
        elif isinstance(message_data, str):
            user_text = message_data
        if not user_text:
            user_text = req.get("prompt") or req.get("question") or ""

        session_id = req.get("session_id") or "ge_session"
        user_id = req.get("user_id") or "ge_user"

        has_yielded = False
        stream = self.stream_query(message=user_text, user_id=user_id, session_id=session_id)
        for chunk in stream:
            chunk_text = ""
            if hasattr(chunk, 'text') and chunk.text:
                chunk_text = chunk.text
            elif isinstance(chunk, dict):
                if chunk.get("type") == "text":
                    chunk_text = chunk.get("content", "")
                elif chunk.get("type") == "data":
                    content = chunk.get("content", {})
                    if content.get("explore_url"):
                        chunk_text = f"\n\n[📊 Open in Looker Explore]({content.get('explore_url')})\n"
                elif "content" in chunk and isinstance(chunk["content"], dict):
                    for p in chunk["content"].get("parts", []):
                        if "text" in p:
                            chunk_text += p["text"]
            elif isinstance(chunk, str):
                chunk_text = chunk

            if chunk_text:
                has_yielded = True
                yield {
                    "events": [
                        {
                            "author": "Gaming Analytics Intelligence",
                            "content": {
                                "role": "model",
                                "parts": [
                                    {"text": chunk_text}
                                ]
                            }
                        }
                    ],
                    "session_id": session_id
                }

        if not has_yielded:
            yield {
                "events": [
                    {
                        "author": "Gaming Analytics Intelligence",
                        "content": {
                            "role": "model",
                            "parts": [
                                {"text": "I analyzed your request against the Looker gaming model and Spanner social graph. Please provide additional details or specify a metric (DAU, revenue, retention) or clan to explore."}
                            ]
                        }
                    }
                ],
                "session_id": session_id
            }

    def agent_run_with_events(self, request_json: str):
        """Synchronous run with events for Gemini Enterprise."""
        events = []
        for event in self.streaming_agent_run_with_events(request_json):
            events.append(event)
        return events

    def register_operations(self):
        """Registers operations for Vertex AI Agent Engine and Gemini Enterprise."""
        return {
            "": ["query", "agent_run_with_events", "get_session", "create_session"],
            "stream": ["stream_query", "streaming_agent_run_with_events"],
        }

    def get_session(self, *args, **kwargs):
        pass

    def create_session(self, *args, **kwargs):
        pass


class DeepAnalysisApp:
    """
    Wrapper for Deep Analysis mode to function as an App for server.py and Reasoning Engine.
    """
    def query(self, message: str, user_id: str = None, session_id: str = None, model_name: str = None):
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        full_text = []
        for chunk in self.stream_query(message=message, user_id=user_id, session_id=session_id, model_name=model_name):
            if isinstance(chunk, dict) and "content" in chunk:
                for part in chunk["content"].get("parts", []):
                    if "text" in part:
                        full_text.append(part["text"])
            elif isinstance(chunk, str):
                full_text.append(chunk)
        return "".join(full_text)

    def stream_query(self, message: str, user_id: str = None, session_id: str = None, model_name: str = None):
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        yield from run_deep_analysis(message, model_name=model_name, session_id=session_id)

    def streaming_agent_run_with_events(self, request_json: str):
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        try:
            req = json.loads(request_json) if isinstance(request_json, str) else (request_json or {})
        except Exception:
            req = {}

        message_data = req.get("message", {})
        user_text = ""
        if isinstance(message_data, dict):
            parts = message_data.get("parts", [])
            user_text = " ".join([p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p])
        elif isinstance(message_data, str):
            user_text = message_data
        if not user_text:
            user_text = req.get("prompt") or req.get("question") or ""

        session_id = req.get("session_id") or "ge_session"
        user_id = req.get("user_id") or "ge_user"

        for chunk in self.stream_query(message=user_text, user_id=user_id, session_id=session_id):
            chunk_text = ""
            if isinstance(chunk, dict) and "content" in chunk:
                for p in chunk["content"].get("parts", []):
                    if "text" in p:
                        chunk_text += p["text"]
            elif isinstance(chunk, str):
                chunk_text = chunk
            if chunk_text:
                yield {
                    "events": [
                        {
                            "author": "Gaming Analytics Intelligence",
                            "content": {
                                "role": "model",
                                "parts": [
                                    {"text": chunk_text}
                                ]
                            }
                        }
                    ],
                    "session_id": session_id
                }

    def agent_run_with_events(self, request_json: str):
        events = []
        for event in self.streaming_agent_run_with_events(request_json):
            events.append(event)
        return events

    def register_operations(self):
        return {
            "": ["query", "agent_run_with_events", "get_session", "create_session"],
            "stream": ["stream_query", "streaming_agent_run_with_events"],
        }

    def get_session(self, *args, **kwargs):
        pass

    def create_session(self, *args, **kwargs):
        pass


router_app = RouterAgentApp()
deep_app = DeepAnalysisApp()
app = router_app

def get_agent_app(agent_type="auto"):
    """Returns the appropriate agent app based on type. Defaults to intelligent RouterApp."""
    if agent_type == "deep" or agent_type == "mcp":
        return deep_app
    elif agent_type == "fast":
        # Fast direct metrics
        class FastApp:
            def stream_query(self, message: str, user_id: str = None, session_id: str = None, model_name: str = None):
                return run_metrics_subagent(message, session_id=session_id)
            def get_session(self, *args, **kwargs): pass
            def create_session(self, *args, **kwargs): pass
        return FastApp()
    return router_app



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
            # Data-driven fallback structure
            br_rev = br_processed['metrics']['revenue']['value']
            br_iap = br_processed['metrics']['revenue']['iap_value']
            br_ad = br_processed['metrics']['revenue']['ad_value']
            farm_rev = farm_processed['metrics']['revenue']['value']
            farm_iap = farm_processed['metrics']['revenue']['iap_value']
            farm_ad = farm_processed['metrics']['revenue']['ad_value']
            br_dau = br_processed['metrics']['dau']['value']
            farm_dau = farm_processed['metrics']['dau']['value']
            br_ret = br_processed['metrics']['retention']['value']
            farm_ret = farm_processed['metrics']['retention']['value']

            fallback_comparison = f"""### Strategic Portfolio Comparison: Lookup Battle Royale vs. Lookerwood Farm

Our two core titles serve distinct operational roles and monetization models across the portfolio. **Lookup Battle Royale** operates as a high-volume, IAP-dominant title (generating **${br_iap:,.0f} IAP vs. ${br_ad:,.0f} Ads**). It drives massive top-of-funnel reach ({br_dau:,.0f} DAU), capitalizing on weekend live-ops and competitive pass purchases, though D1 retention averages **{br_ret:.1f}%**.

In contrast, **Lookerwood Farm** functions as an ad-driven engagement engine (generating **${farm_ad:,.0f} Ads vs. ${farm_iap:,.0f} IAP**). Operating at a steady volume ({farm_dau:,.0f} DAU), it consistently demonstrates stronger retention quality, maintaining a higher D1 retention baseline at **{farm_ret:.1f}%**.

Together, the portfolio benefits from complementary business dynamics: Battle Royale captures high-ARPU conversion spikes during competitive live-ops pushes, while Lookerwood Farm provides predictable, high-retention ad revenue stream stability."""

            summary_json = {
                "game_comparison": fallback_comparison,
                "overall": {
                    "executive_summary": f"Overall daily revenue stabilized at ${overall_processed['metrics']['revenue']['value']:,.2f} with {overall_processed['metrics']['dau']['value']:,.0f} active users across both games.",
                    "highlights": [
                        f"Aggregate daily portfolio revenue reached ${overall_processed['metrics']['revenue']['value']:,.2f}.",
                        f"Active users totaled {overall_processed['metrics']['dau']['value']:,.0f} across Lookup Battle Royale and Lookerwood Farm.",
                        f"Blended Day 1 retention held at {overall_processed['metrics']['retention']['value']:.2f}%."
                    ],
                    "action_items": [{"text": "Monitor overall performance metrics.", "fields": ["events.event_date", "events.total_revenue"], "filters": {}}],
                    "revenue_mix_trend": {"type": "area", "xAxisKey": "date", "stacked": True, "data": [], "series": [{"name": "IAP Revenue", "dataKey": "iap", "strokeColor": "hsl(var(--primary))", "fillColor": "hsla(var(--primary), 0.3)"}, {"name": "Ad Revenue", "dataKey": "ad", "strokeColor": "hsl(var(--chart-2))", "fillColor": "hsla(var(--chart-2), 0.3)"}], "title": "7-Day Revenue Mix Trend (IAP vs. Ads)"},
                    "dau_retention_trend": {"type": "combo", "xAxisKey": "date", "data": [], "series": [{"type": "bar", "name": "DAU", "dataKey": "dau", "fillColor": "hsla(var(--primary), 0.2)", "strokeColor": "hsl(var(--primary))", "yAxisID": "left"}, {"type": "line", "name": "D1 Retention Rate (%)", "dataKey": "retention", "strokeColor": "hsl(var(--chart-3))", "fillColor": "hsl(var(--chart-3))", "yAxisID": "right"}], "title": "7-Day Active Users & Retention Trend"}
                },
                "battle_royale": {
                    "executive_summary": f"Lookup Battle Royale generated ${br_rev:,.2f} total revenue with ${br_iap:,.2f} in IAP and {br_dau:,.0f} DAU.",
                    "highlights": [f"IAP revenue reached ${br_iap:,.2f}.", f"Active players reached {br_dau:,.0f} with D1 retention at {br_ret:.2f}%."],
                    "action_items": [{"text": "Analyze Battle Royale In-App Purchase trends.", "fields": ["events.event_date", "events.total_iap_revenue"], "filters": {"events.game_name": "Lookup Battle Royale"}}],
                    "revenue_mix_trend": {"type": "area", "xAxisKey": "date", "stacked": True, "data": [], "series": [{"name": "IAP Revenue", "dataKey": "iap", "strokeColor": "hsl(var(--primary))", "fillColor": "hsla(var(--primary), 0.3)"}, {"name": "Ad Revenue", "dataKey": "ad", "strokeColor": "hsl(var(--chart-2))", "fillColor": "hsla(var(--chart-2), 0.3)"}], "title": "7-Day Revenue Mix Trend (IAP vs. Ads)"},
                    "dau_retention_trend": {"type": "combo", "xAxisKey": "date", "data": [], "series": [{"type": "bar", "name": "DAU", "dataKey": "dau", "fillColor": "hsla(var(--primary), 0.2)", "strokeColor": "hsl(var(--primary))", "yAxisID": "left"}, {"type": "line", "name": "D1 Retention Rate (%)", "dataKey": "retention", "strokeColor": "hsl(var(--chart-3))", "fillColor": "hsl(var(--chart-3))", "yAxisID": "right"}], "title": "7-Day Active Users & Retention Trend"}
                },
                "farm": {
                    "executive_summary": f"Lookerwood Farm achieved ${farm_rev:,.2f} total revenue (${farm_ad:,.2f} Ads) and superior D1 retention of {farm_ret:.2f}%.",
                    "highlights": [f"Ad revenue was ${farm_ad:,.2f}.", f"D1 retention reached {farm_ret:.2f}% with {farm_dau:,.0f} active users."],
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
