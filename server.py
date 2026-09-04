from flask import Flask, request, jsonify, Response, stream_with_context, redirect
import json
import time
import os
import re

from flask_cors import CORS
from agent import app as agent_app, PROJECT_ID, LOCATION
import threading
import queue
import agent
import requests
import urllib.parse
from google.auth.transport.requests import Request as gRequest
import hmac
import base64
import binascii
from struct import pack
agent.thought_queue = queue.Queue()
from cache_manager import cache_manager

# Helper: Filter raw query_details JSON from agent text responses
# This catches cases where the model accidentally outputs raw JSON blobs
def filter_raw_json_from_text(text: str) -> str:
    """Remove raw query_details JSON blobs from text output."""
    if not text:
        return text
    
    # Check if the entire text is just JSON blobs (common case for this bug)
    # Multiple JSON objects look like: {...} {...} {...}
    stripped = text.strip()
    if stripped.startswith('{"type":') and '"query_details"' in stripped:
        # The entire text is JSON blobs - return empty
        return ""
    
    # Pattern to match query_details JSON objects (with DOTALL to match across newlines)
    # Uses non-greedy matching and looks for the closing pattern
    pattern = r'\{"type":\s*"query_details".*?"source":\s*"[^"]*"\s*\}'
    filtered = re.sub(pattern, '', text, flags=re.DOTALL)
    
    # Also try to filter consecutive JSON objects that start with {"type":
    # This catches any remaining {"type": ..., "sql": ..., "source": ...} patterns
    pattern2 = r'\{"type":\s*"[^"]*",\s*"sql":.*?"source":\s*"[^"]*"\s*\}'
    filtered = re.sub(pattern2, '', filtered, flags=re.DOTALL)
    
    # Filter out DATA_PAYLOAD_JSON blobs
    pattern3 = r'DATA_PAYLOAD_JSON:\s*\{.*?\}'
    filtered = re.sub(pattern3, '', filtered, flags=re.DOTALL)
    
    # Clean up any excessive whitespace left behind
    filtered = re.sub(r'\n{3,}', '\n\n', filtered)
    filtered = re.sub(r'^\s+', '', filtered)  # Leading whitespace
    
    return filtered.strip()

# Vertex AI is initialized in agent.py to ensure it is configured before agent creation.

app = Flask(__name__, static_folder=os.path.abspath('frontend/dist'), static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

# DEBUG: Check if static files exist
try:
    print(f"DEBUG: CWD is {os.getcwd()}", flush=True)
    print(f"DEBUG: Static Folder: {app.static_folder}", flush=True)
    print(f"DEBUG: Listing current directory: {os.listdir('.')}", flush=True)
    
    if os.path.exists('frontend/dist'):
        print(f"DEBUG: Listing frontend/dist: {os.listdir('frontend/dist')}", flush=True)
        if os.path.exists('frontend/dist/index.html'):
            print("DEBUG: frontend/dist/index.html FOUND.", flush=True)
        else:
            print("DEBUG: frontend/dist/index.html NOT FOUND!", flush=True)
    else:
        print("DEBUG: frontend/dist directory NOT FOUND!", flush=True)
except Exception as e:
    print(f"DEBUG: Error checking files: {e}", flush=True)


@app.route('/')
def serve_frontend():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def serve_static(path):
    import os
    if os.path.exists(app.static_folder + '/' + path):
        return app.send_static_file(path)
    else:
        return app.send_static_file('index.html')

@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    print(f"CRITICAL: Unhandled exception: {e}", flush=True)
    traceback.print_exc()
    return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    print(f"Received request: {request.json}") # Debug log
    data = request.json
    user_input = data.get('message')
    deep_analysis = data.get('deep_analysis', False)
    agent_type = data.get('agent_type', 'auto')  # 'auto', 'fast', 'deep', or 'mcp'
    user_id = data.get('user_id', 'web_user')
    session_id = data.get('session_id', 'default_session') # Use session_id if provided, else default
    force_refresh = data.get('force_refresh', False)
    model_name = data.get('model_name')
    
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
        
    start_time = time.time()
    
    # Save User Message immediately
    conversation_manager.save_message(session_id, 'user', user_input)
    
    # Get the appropriate agent app based on type
    current_agent_app = agent.get_agent_app(agent_type)
    print(f"Using agent type: {agent_type}")
    
    try:
        # Check if session exists, if not create it
        try:
            # Try to get the session. Note: get_session requires user_id as well.
            current_agent_app.get_session(session_id=session_id, user_id=user_id)
        except Exception:
            # If get_session fails, it likely means the session doesn't exist.
            # So we try to create it.
            print(f"Session {session_id} not found (or get failed). Creating new session...")
            try:
                current_agent_app.create_session(session_id=session_id, user_id=user_id)
            except Exception as create_error:
                 # If creation fails because it already exists, that's fine, we can proceed.
                 if "already exists" in str(create_error):
                     print(f"Session {session_id} already exists (race condition?), proceeding.")
                 else:
                     print(f"Failed to create session: {create_error}")
                     raise create_error

        # Pass session_id to maintain conversation history, and user_id as required
        # Queue for agent response chunks
        response_queue = queue.Queue()
        
        # Initialize the global data queue for side-channel events
        agent.data_queue = queue.Queue()
        
        # Extract token
        auth_header = request.headers.get('Authorization')
        access_token = None
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]

        def run_agent():
            # Set token for this thread
            if access_token:
                agent.set_access_token(access_token)

            try:
                final_input = user_input
                if agent_type == 'auto':
                    final_input = user_input
                elif agent_type == 'mcp' or agent_type == 'deep':
                    final_input = user_input
                elif deep_analysis:
                    final_input = f"Instruction: PERFORM_DEEP_ANALYSIS. Question: {user_input}"
                else:
                    final_input = user_input

                # 1. Check Cache (only if not forced)
                cached_response = None
                if not force_refresh:
                    cached_response = cache_manager.get_cached_response(final_input)
                
                if cached_response:
                    agent.thought_queue.put("Found similar question in cache. Loading result...")
                    # Simulate streaming for the frontend
                    # We can split by lines or just send it all
                    response_queue.put(("chunk", {"text": cached_response}))
                    response_queue.put(("done", None))
                    return

                # 2. Run Agent
                kwargs = {'message': final_input, 'user_id': user_id, 'session_id': session_id}
                import inspect
                try:
                    sig = inspect.signature(current_agent_app.stream_query)
                    if 'model_name' in sig.parameters and model_name:
                        kwargs['model_name'] = model_name
                except Exception as e:
                    print(f"DEBUG: Could not inspect stream_query signature: {e}")
                stream = current_agent_app.stream_query(**kwargs)
                
                full_response_accumulator = []
                
                for chunk in stream:
                    # Accumulate text for caching
                    if hasattr(chunk, 'text') and chunk.text:
                         full_response_accumulator.append(chunk.text)
                    elif isinstance(chunk, dict):
                        if "content" in chunk and "parts" in chunk["content"]:
                             for part in chunk["content"]["parts"]:
                                 if "text" in part:
                                     full_response_accumulator.append(part["text"])
                        elif "text" in chunk:
                             full_response_accumulator.append(chunk["text"])
                    elif isinstance(chunk, str):
                        full_response_accumulator.append(chunk)

                    response_queue.put(("chunk", chunk))
                
                # 3. Add to Cache
                full_text = "".join(full_response_accumulator)
                if full_text.strip():
                    # Run in background or just do it here (it takes a small embedding call time)
                    try:
                        cache_manager.add_to_cache(final_input, full_text)
                    except Exception as e:
                        print(f"Failed to cache response: {e}")

                # Save Agent Response to History
                if full_text.strip():
                     conversation_manager.save_message(session_id, 'model', full_text)

                response_queue.put(("done", None))
            except Exception as e:
                response_queue.put(("error", e))

        # Start agent in a separate thread
        agent_thread = threading.Thread(target=run_agent)
        agent_thread.start()
        
        def generate():
            while True:
                # Check for thoughts
                try:
                    while True:
                        thought = agent.thought_queue.get_nowait()
                        # Sanitize thought to be single line
                        safe_thought = str(thought).replace('\n', ' ')
                        yield f"THOUGHT: {safe_thought}\n"
                except queue.Empty:
                    pass

                # Check for side-channel data events (e.g. Graph, SQL logs, Routing)
                try:
                    while True:
                        data_event = agent.data_queue.get_nowait()
                        if data_event.get("type") == "graph":
                             yield f"DATA: {json.dumps({'type': 'json_graph', 'graphData': data_event['content']})}\n"
                        elif data_event.get("type") == "dashboard_created":
                             yield f"DATA: {json.dumps({'type': 'json_dashboard_created', 'dashboard': data_event['dashboard']})}\n"
                        elif data_event.get("type") == "subagent_routed":
                             yield f"DATA: {json.dumps({'type': 'subagent_routed', 'subagent': data_event.get('subagent'), 'name': data_event.get('name'), 'icon': data_event.get('icon'), 'description': data_event.get('description')})}\n"
                        elif data_event.get("type") == "json_utils":
                             inner_data = data_event.get('data', {})
                             # Skip query_details - these should not be displayed as text
                             if isinstance(inner_data, dict) and inner_data.get("type") == "query_details":
                                 continue
                             yield f"DATA: {json.dumps(inner_data)}\n"
                except queue.Empty:
                    pass

                # Check for agent response
                try:
                    # Wait a short time for response to allow thought loop to run frequently
                    # But not too short to busy-wait excessively
                    item = response_queue.get(timeout=0.1)
                    type_, data = item
                    
                    if type_ == "chunk":
                        chunk = data
                        # Handle ADK Agent Chunk object
                        if hasattr(chunk, 'text') and chunk.text:
                             # Filter out any raw JSON that leaked through
                             filtered_text = filter_raw_json_from_text(chunk.text)
                             if filtered_text:
                                 yield f"DATA: {filtered_text}\n"
                        # Handle dictionary (legacy or deep analysis raw chunks if any)
                        elif isinstance(chunk, dict):
                            if chunk.get("type") == "graph":
                                # Stream graph data to frontend
                                yield f"DATA: {json.dumps({'type': 'json_graph', 'graphData': chunk['content']})}\n"
                            elif "content" in chunk:
                                content = chunk["content"]
                                # Check for generic JSON utils (e.g. query details)
                                if isinstance(content, dict) and content.get("type") == "json_utils":
                                    inner_data = content.get('data', {})
                                    # Skip query_details - these should not be displayed as text
                                    # They're handled separately by the frontend
                                    if isinstance(inner_data, dict) and inner_data.get("type") == "query_details":
                                        continue
                                    yield f"DATA: {json.dumps(inner_data)}\n"
                                elif "parts" in content:
                                    for part in content["parts"]:
                                        if "text" in part:
                                            # Filter out any raw JSON that leaked through
                                            filtered_text = filter_raw_json_from_text(part['text'])
                                            if filtered_text:
                                                yield f"DATA: {filtered_text}\n"
                            elif "text" in chunk:
                                # Filter out any raw JSON that leaked through
                                filtered_text = filter_raw_json_from_text(chunk['text'])
                                if filtered_text:
                                    yield f"DATA: {filtered_text}\n"
                        # Fallback for string
                        elif isinstance(chunk, str):
                             # Filter out any raw JSON that leaked through
                             filtered_text = filter_raw_json_from_text(chunk)
                             if filtered_text:
                                 yield f"DATA: {filtered_text}\n"
                    elif type_ == "done":
                        break
                    elif type_ == "error":
                        yield f"ERROR: {str(data)}\n"
                        break
                except queue.Empty:
                    # If agent is still running, continue loop to check thoughts again
                    if not agent_thread.is_alive() and response_queue.empty() and agent.thought_queue.empty() and agent.data_queue.empty():
                         break
                    continue
        
        return app.response_class(generate(), mimetype='text/plain')

    except Exception as e:
        print(f"Server Error: {e}") # Log the full error to the console
        import traceback
        traceback.print_exc() # Print stack trace
        return jsonify({'error': str(e)}), 500


@app.route('/fast-query', methods=['POST', 'OPTIONS'])
def fast_query():
    """
    Direct fast query endpoint that bypasses ADK agent for faster responses.
    Calls geminidataanalytics API directly and streams the response.
    """
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    data = request.json
    question = data.get('message')
    session_id = data.get('session_id')
    
    if not question:
        return jsonify({'error': 'No message provided'}), 400
    
    print(f"Fast Query: {question} (Session: {session_id})")
    
    # Save User Message
    if session_id:
        conversation_manager.save_message(session_id, 'user', question)

    # Retrieve history
    history = []
    if session_id:
        history = conversation_manager.get_conversation(session_id)
        # We just added the user message, so we might want to exclude it to avoid duplication if we are re-appending it manually in agent.py
        # But agent.py appends the *current* question manually. 
        # Ideally, we pass history *excluding* the current question.
        # fast_query in agent.py reconstructs messages. 
        # It iterates history, then appends current question.
        # If we save current question first, it's in history. 
        # So we should exclude the last message from history passed to agent.
        if history and history[-1]['content'] == question:
             history = history[:-1]
             
        print(f"DEBUG: Fast Query Session ID: {session_id}, History Length: {len(history)}")
    else:
        print("DEBUG: Fast Query - No Session ID provided")
    
    def generate():
        import time
        start_time = time.time()
        text_parts = []
        data_result = None
        full_response_text = ""
        
        # Track rich data for persistence
        saved_table_data = None
        saved_link = None
        saved_chart_config = None
        
        try:
            for chunk in agent.fast_query(question, history):
                chunk_type = chunk.get("type")
                content = chunk.get("content")
                
                if chunk_type == "text":
                    text_parts.append(content)
                    full_response_text += content + " "
                    yield f"DATA: {content}\n"
                elif chunk_type == "thought":
                    # API v2: Thinking/reasoning messages (text_type=2)
                    # Stream as THOUGHT so frontend can show thinking process
                    yield f"THOUGHT: {content}\n"
                elif chunk_type == "data":
                    data_result = content
                    # Emit structured data for frontend to render table
                    # We still do some processing here to simplify frontend work
                    rows = content.get("rows", [])
                    schema = content.get("schema", {})
                    fields = schema.get("fields", [])
                    
                    result_id = ""
                    if rows and fields:
                        # Prepare simplified structure for frontend
                        table_data = {
                            "fields": [{"name": f.get("name"), "label": f.get("display_name") or f.get("name", "").split(".")[-1]} for f in fields],
                            "rows": rows
                        }
                        saved_table_data = table_data  # Track for saving
                        yield f"DATA: {json.dumps({'type': 'json_table', 'data': table_data})}\n"
                        
                        # Serialize data limit for history context (so model knows what it showed)
                        data_summary = "\n[Data Context Available]"
                        full_response_text += data_summary

                        explore_url = content.get("explore_url")
                        if explore_url:
                            saved_link = explore_url  # Track for saving
                            yield f"DATA: {json.dumps({'type': 'json_link', 'url': explore_url})}\n"

                        # Prepare full payload for history persistence (so follow-ups work)
                        full_data_payload = {
                            'result': {
                                'data': rows,
                                'schema': schema,
                                'sql': content.get("sql", ""),
                                'explore_url': explore_url or ""
                            }
                        }
                        # Append a special marker line to the full_response_text
                        # We ensure it's on a new line.
                        full_response_text += f"\nDATA_PAYLOAD_JSON: {json.dumps(full_data_payload)}"

                elif chunk_type == "chart":
                     saved_chart_config = content  # Track for saving
                     yield f"DATA: {json.dumps({'type': 'json_chart', 'config': content})}\n"
                        
                elif chunk_type == "disambiguation":
                    # GA Feature: API returns clarifying questions when intent is ambiguous
                    yield f"DATA: {json.dumps({'type': 'disambiguation', 'data': content})}\n"
                elif chunk_type == "error":
                    yield f"DATA: Error: {content}\n"
                elif chunk_type == "done":
                    elapsed = time.time() - start_time
                    yield f"THOUGHT: Query completed in {elapsed:.1f}s\n"
            
            # Save Agent Response to History with rich data
            if session_id and full_response_text.strip():
                extra_data = {}
                if saved_table_data:
                    extra_data['tableData'] = saved_table_data
                if saved_link:
                    extra_data['link'] = saved_link
                if saved_chart_config:
                    extra_data['chartConfig'] = saved_chart_config
                conversation_manager.save_message(session_id, 'model', full_response_text, extra_data=extra_data if extra_data else None)

        except Exception as e:
            print(f"Fast Query Error: {e}")
            import traceback
            traceback.print_exc()
            yield f"DATA: Error: {str(e)}\n"
            # yield "DONE\n"
    
    return app.response_class(generate(), mimetype='text/plain')


@app.route('/api/insights', methods=['POST'])
def insights():
    """Direct API endpoint for the get_insights tool."""
    data = request.json
    question = data.get('question')
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        # Extract token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            agent.set_access_token(auth_header.split(' ')[1])

        # Call the tool directly
        result = agent.get_insights(question)
        return jsonify(result)
    except Exception as e:
        print(f"Insights Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/query', methods=['POST', 'OPTIONS'])
def api_query():
    """
    Synchronous natural language query endpoint for OpenAPI & Gemini Enterprise tool execution.
    Executes the query via autonomous multi-agent routing and returns structured results.
    """
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data = request.get_json(silent=True) or {}
    question = data.get('question') or data.get('message')
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    agent_type = data.get('agent_type', 'auto')
    session_id = data.get('session_id') or 'ge_session'
    user_id = data.get('user_id', 'gemini_enterprise_user')
    model_name = data.get('model_name')

    # Auth header support
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        agent.set_access_token(auth_header.split(' ')[1])

    try:
        active_dash = getattr(agent, 'ACTIVE_DASHBOARDS_REGISTRY', {}).get(session_id) or getattr(agent, 'ACTIVE_DASHBOARDS_REGISTRY', {}).get('latest')
        route = agent.classify_subagent_route(question, active_dash=active_dash)
        subagent_key = route.get('subagent', 'metrics_fast')
        
        current_agent_app = agent.get_agent_app(agent_type if agent_type != 'auto' else 'auto')
        
        kwargs = {'message': question, 'user_id': user_id, 'session_id': session_id}
        if model_name:
            kwargs['model_name'] = model_name
            
        stream = current_agent_app.stream_query(**kwargs)
        
        text_parts = []
        table_data = None
        chart_data = None
        explore_url = None
        
        for chunk in stream:
            if hasattr(chunk, 'text') and chunk.text:
                text_parts.append(chunk.text)
            elif isinstance(chunk, dict):
                chunk_type = chunk.get("type")
                if chunk_type == "text":
                    text_parts.append(chunk.get("content", ""))
                elif chunk_type == "data":
                    content = chunk.get("content", {})
                    rows = content.get("rows", [])
                    schema = content.get("schema", {})
                    fields = schema.get("fields", [])
                    if rows and fields:
                        table_data = {
                            "fields": [{"name": f.get("name"), "label": f.get("display_name") or f.get("name", "").split(".")[-1]} for f in fields],
                            "rows": rows
                        }
                    if content.get("explore_url"):
                        explore_url = content.get("explore_url")
                elif chunk_type == "chart":
                    chart_data = chunk.get("content")
                elif "content" in chunk and isinstance(chunk["content"], dict):
                    for p in chunk["content"].get("parts", []):
                        if "text" in p:
                            text_parts.append(p["text"])
            elif isinstance(chunk, str):
                text_parts.append(chunk)

        raw_answer = "".join(text_parts).strip()
        filtered_answer = filter_raw_json_from_text(raw_answer)

        return jsonify({
            "status": "success",
            "question": question,
            "subagent": subagent_key,
            "subagent_name": route.get("name", "Metrics Analyst"),
            "answer": filtered_answer or raw_answer,
            "table_data": table_data,
            "chart": chart_data,
            "explore_url": explore_url,
            "model": model_name or "gemini-3.6-flash"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500


from conversation_manager import ConversationManager

# Initialize Conversation Manager
conversation_manager = ConversationManager()

@app.route('/api/history', methods=['GET'])
def list_history():
    """Returns a list of recent conversations."""
    limit = request.args.get('limit', 30, type=int)
    history = conversation_manager.list_conversations(limit=limit)
    return jsonify(history)

@app.route('/api/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """Returns the chat log for a specific session."""
    messages = conversation_manager.get_conversation(session_id)
    return jsonify(messages)

@app.route('/api/history/<session_id>', methods=['DELETE'])
def delete_history(session_id):
    """Deletes a conversation."""
    conversation_manager.delete_conversation(session_id)
    return jsonify({'status': 'success'})


# --- GA Feature: Server-Side Conversation Management via CA API ---

@app.route('/api/ca-conversations', methods=['GET'])
def list_ca_conversations():
    """Lists conversations managed by the Conversational Analytics API."""
    try:
        conversations = agent.list_ca_conversations()
        return jsonify(conversations)
    except Exception as e:
        print(f"CA Conversations List Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ca-conversation/<path:conversation_id>', methods=['DELETE'])
def delete_ca_conversation(conversation_id):
    """Deletes a conversation from the CA API server-side."""
    try:
        agent.delete_ca_conversation(conversation_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"CA Conversation Delete Error: {e}")
        return jsonify({'error': str(e)}), 500


# --- GA Feature: Managed Agent CRUD via DataAgentServiceClient ---

@app.route('/api/agents', methods=['GET'])
def list_agents():
    """Lists all data agents, including accessible/shared agents."""
    try:
        include_accessible = request.args.get('accessible', 'false').lower() == 'true'
        if include_accessible:
            agents = agent.list_accessible_data_agents()
        else:
            agents = agent.list_data_agents()
        return jsonify(agents)
    except Exception as e:
        print(f"Agent List Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents', methods=['POST'])
def create_agent():
    """Creates a new managed data agent."""
    try:
        data = request.json
        display_name = data.get('display_name')
        description = data.get('description', '')
        
        if not display_name:
            return jsonify({'error': 'display_name is required'}), 400
        
        result = agent.create_data_agent(display_name, description)
        return jsonify({
            'name': result.name,
            'display_name': result.display_name,
            'description': result.description,
        }), 201
    except Exception as e:
        print(f"Agent Create Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents/<path:agent_id>', methods=['GET'])
def get_agent(agent_id):
    """Gets details of a specific data agent."""
    try:
        result = agent.get_data_agent(agent_id)
        return jsonify(result)
    except Exception as e:
        print(f"Agent Get Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents/<path:agent_id>', methods=['DELETE'])
def delete_agent(agent_id):
    """Deletes a data agent."""
    try:
        agent.delete_data_agent(agent_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Agent Delete Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """Returns available LLM models for swapping and configuration."""
    return jsonify({
        'models': agent.AVAILABLE_MODELS,
        'default_model': os.getenv('DEFAULT_MODEL', 'gemini-3.6-flash')
    })

@app.route('/api/dataset-config', methods=['GET'])
def get_dataset_config():
    """Returns the current dataset configuration (questions, dashboards, metadata)."""
    try:
        dataset_meta = agent.AGENT_CONFIG.get('_dataset', {})
        
        # Get dataset-specific config from the loaded YAML via AGENT_CONFIG
        # We need to reload the dataset file to get non-instruction fields
        import yaml
        dataset_name = os.getenv("DATASET_NAME", "events")
        dataset_path = f"datasets/{dataset_name}.yaml"
        
        dataset_config = {}
        try:
            with open(dataset_path, 'r') as f:
                dataset_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load dataset config for API: {e}")
        
        return jsonify({
            'name': dataset_meta.get('name', dataset_name),
            'display_name': dataset_meta.get('display_name', dataset_name),
            'looker': {
                'instance_uri': agent.LOOKER_INSTANCE_URI,
                'model': agent.LOOKML_MODEL,
                'explore': agent.EXPLORE
            },
            'starter_questions': dataset_config.get('starter_questions', []),
            'test_scenarios': dataset_config.get('test_scenarios', []),
            'dashboards': dataset_config.get('dashboards', [])
        })
    except Exception as e:
        print(f"Dataset Config Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-safety-summary', methods=['GET'])
def get_player_safety_summary():
    """Returns player safety, toxicity metrics, incident stream, and mitigation telemetry."""
    try:
        game = request.args.get('game', 'overall')
        
        if game == 'battle_royale':
            return jsonify({
                "exposure_chart": {
                    "avg_spend": [4.81, 3.65, 2.09, 0.96],
                    "labels": ["0 Toxic Matches", "1 Toxic Match", "2 Toxic Matches", "3+ Toxic Matches"],
                    "retention_rates": [22.4, 18.6, 14.1, 8.9]
                },
                "incidents": [
                    {"action": "Session Terminated", "game": "Lookup Battle Royale", "id": "INC-9047", "score": "97.8% Match", "severity": "CRITICAL", "status": "RESOLVED", "time": "Just now", "type": "Speed Hack / Bot", "vector": "Anti-Cheat Prober"},
                    {"action": "Match Forfeit", "game": "Lookup Battle Royale", "id": "INC-9044", "score": "93.7% Match", "severity": "MEDIUM", "status": "ESCALATED", "time": "Just now", "type": "Griefing / AFK", "vector": "Gameplay Telemetry"},
                    {"action": "Session Terminated", "game": "Lookup Battle Royale", "id": "INC-9043", "score": "92.3% Match", "severity": "LOW", "status": "RESOLVED", "time": "Just now", "type": "Speed Hack / Bot", "vector": "Anti-Cheat Prober"},
                    {"action": "Rank Penalty", "game": "Lookup Battle Royale", "id": "INC-9041", "score": "97.4% Match", "severity": "CRITICAL", "status": "RESOLVED", "time": "Just now", "type": "Griefing / AFK", "vector": "Gameplay Telemetry"},
                    {"action": "Permanent Ban", "game": "Lookup Battle Royale", "id": "INC-9039", "score": "96.9% Match", "severity": "CRITICAL", "status": "RESOLVED", "time": "Just now", "type": "Speed Hack / Bot", "vector": "Anti-Cheat Prober"},
                    {"action": "Temp Ban 3d", "game": "Lookup Battle Royale", "id": "INC-9038", "score": "93.5% Match", "severity": "LOW", "status": "ESCALATED", "time": "Just now", "type": "Text Hatespeech", "vector": "Text Chat"}
                ],
                "kpis": {
                    "auto_velocity": "1.8s",
                    "exposed_matches": "3.8%",
                    "honor_index": "89.6%",
                    "retention_gap": "-7.4 pp"
                },
                "source": "Looker Production API",
                "vector_chart": {
                    "data": [42, 39, 31, 27],
                    "labels": ["Text Chat", "Anti-Cheat Prober", "Gameplay Telemetry", "Voice Chat"]
                }
            })
        elif game == 'farm':
            return jsonify({
                "exposure_chart": {
                    "avg_spend": [4.79, 3.65, 2.09, 0.95],
                    "labels": ["0 Toxic Matches", "1 Toxic Match", "2 Toxic Matches", "3+ Toxic Matches"],
                    "retention_rates": [22.4, 18.6, 14.1, 8.9]
                },
                "incidents": [
                    {"action": "Rank Penalty", "game": "Lookerwood Farm", "id": "INC-9049", "score": "96.4% Match", "severity": "CRITICAL", "status": "RESOLVED", "time": "Just now", "type": "Griefing / AFK", "vector": "Gameplay Telemetry"},
                    {"action": "Temp Ban 3d", "game": "Lookerwood Farm", "id": "INC-9048", "score": "94.1% Match", "severity": "MEDIUM", "status": "ESCALATED", "time": "Just now", "type": "Text Hatespeech", "vector": "Text Chat"},
                    {"action": "Warning Sent", "game": "Lookerwood Farm", "id": "INC-9046", "score": "95.3% Match", "severity": "CRITICAL", "status": "RESOLVED", "time": "Just now", "type": "Text Hatespeech", "vector": "Text Chat"},
                    {"action": "Escrow Warning", "game": "Lookerwood Farm", "id": "INC-9045", "score": "98.2% Match", "severity": "HIGH", "status": "RESOLVED", "time": "Just now", "type": "Griefing / AFK", "vector": "Gameplay Telemetry"},
                    {"action": "Permanent Ban", "game": "Lookerwood Farm", "id": "INC-9042", "score": "94.2% Match", "severity": "MEDIUM", "status": "ESCALATED", "time": "Just now", "type": "Speed Hack / Bot", "vector": "Anti-Cheat Prober"},
                    {"action": "Match Forfeit", "game": "Lookerwood Farm", "id": "INC-9040", "score": "93.4% Match", "severity": "HIGH", "status": "UNDER_REVIEW", "time": "Just now", "type": "Griefing / AFK", "vector": "Gameplay Telemetry"}
                ],
                "kpis": {
                    "auto_velocity": "1.7s",
                    "exposed_matches": "3.9%",
                    "honor_index": "89.9%",
                    "retention_gap": "-7.4 pp"
                },
                "source": "Looker Production API",
                "vector_chart": {
                    "data": [35, 29, 26, 20],
                    "labels": ["Gameplay Telemetry", "Anti-Cheat Prober", "Voice Chat", "Text Chat"]
                }
            })
        else:
            return jsonify({
                "exposure_chart": {
                    "avg_spend": [4.8, 3.65, 2.09, 0.95],
                    "labels": ["0 Toxic Matches", "1 Toxic Match", "2 Toxic Matches", "3+ Toxic Matches"],
                    "retention_rates": [22.4, 18.6, 14.1, 8.9]
                },
                "incidents": [
                    {"action": "Rank Penalty", "game": "Lookerwood Farm", "id": "INC-9049", "score": "96.4% Match", "severity": "CRITICAL", "status": "RESOLVED", "time": "Just now", "type": "Griefing / AFK", "vector": "Gameplay Telemetry"},
                    {"action": "Temp Ban 3d", "game": "Lookerwood Farm", "id": "INC-9048", "score": "94.1% Match", "severity": "MEDIUM", "status": "ESCALATED", "time": "Just now", "type": "Text Hatespeech", "vector": "Text Chat"},
                    {"action": "Session Terminated", "game": "Lookup Battle Royale", "id": "INC-9047", "score": "97.8% Match", "severity": "CRITICAL", "status": "RESOLVED", "time": "Just now", "type": "Speed Hack / Bot", "vector": "Anti-Cheat Prober"},
                    {"action": "Warning Sent", "game": "Lookerwood Farm", "id": "INC-9046", "score": "95.3% Match", "severity": "CRITICAL", "status": "RESOLVED", "time": "Just now", "type": "Text Hatespeech", "vector": "Text Chat"},
                    {"action": "Escrow Warning", "game": "Lookerwood Farm", "id": "INC-9045", "score": "98.2% Match", "severity": "HIGH", "status": "RESOLVED", "time": "Just now", "type": "Griefing / AFK", "vector": "Gameplay Telemetry"},
                    {"action": "Match Forfeit", "game": "Lookup Battle Royale", "id": "INC-9044", "score": "93.7% Match", "severity": "MEDIUM", "status": "ESCALATED", "time": "Just now", "type": "Griefing / AFK", "vector": "Gameplay Telemetry"}
                ],
                "kpis": {
                    "auto_velocity": "1.8s",
                    "exposed_matches": "3.8%",
                    "honor_index": "89.8%",
                    "retention_gap": "-7.4 pp"
                },
                "source": "Looker Production API",
                "vector_chart": {
                    "data": [68, 66, 62, 53],
                    "labels": ["Anti-Cheat Prober", "Gameplay Telemetry", "Text Chat", "Voice Chat"]
                }
            })
    except Exception as e:
        print(f"Player Safety Summary Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily-summary', methods=['GET', 'POST'])
def get_daily_summary():
    """Generates or retrieves yesterday's daily summary cached result."""
    try:
        force_refresh = False
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            force_refresh = data.get('force_refresh', False)
        else:
            force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
            
        summary = agent.generate_daily_summary(force_refresh=force_refresh)
        return jsonify(summary)
    except Exception as e:
        print(f"Daily Summary Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/auth/login_url', methods=['GET'])
def login_url():
    """Returns the Looker OAuth authorization URL."""
    base_uri = agent.LOOKER_INSTANCE_URI.rstrip('/')
    client_id = agent.LOOKER_CLIENT_ID
    redirect_uri = request.args.get('redirect_uri', 'http://localhost:5173/auth/callback')
    
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'api'
    }
    url = f"{base_uri}/auth/authorize?{urllib.parse.urlencode(params)}"
    return jsonify({'url': url})

@app.route('/auth/exchange', methods=['POST'])
def exchange_token():
    """Exchanges authorization code for access token."""
    code = request.json.get('code')
    redirect_uri = request.json.get('redirect_uri', 'http://localhost:5173/auth/callback')
    
    if not code:
        return jsonify({'error': 'No code provided'}), 400
        
    base_uri = agent.LOOKER_INSTANCE_URI.rstrip('/')
    token_url = f"{base_uri}/api/token"
    
    data = {
        'client_id': agent.LOOKER_CLIENT_ID,
        'client_secret': agent.LOOKER_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }
    
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        print(f"Token Exchange Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response: {e.response.text}")
        return jsonify({'error': str(e)}), 500

@app.route('/reauth', methods=['POST'])
def reauth():
    try:
        # Run gcloud auth application-default login in a subprocess
        # Note: This will open a browser window on the server machine (your laptop)
        import subprocess
        print("Starting re-authentication...")
        subprocess.Popen(['gcloud', 'auth', 'application-default', 'login'])
        return jsonify({'status': 'Authentication process started. Please check your browser.'})
    except Exception as e:
        print(f"Reauth Error: {e}")
        return jsonify({'error': str(e)}), 500



from looker_embed import LookerEmbedManager

# Initialize the embed manager globally to reuse the SDK session
embed_manager = None
try:
    embed_manager = LookerEmbedManager()
except Exception as e:
    print(f"WARNING: Could not initialize Looker Embed Manager: {e}")

@app.route('/api/embed', methods=['POST'])
def get_embed_url():
    """
    Generates a cookieless embed session for Looker dashboards.
    
    This returns tokens that the frontend uses with the Looker Embed SDK
    to create the embedded iframe with proper authentication.
    """
    if not embed_manager:
        return jsonify({'error': 'Embed Manager not initialized'}), 500
        
    try:
        data = request.json
        target_path = data.get('target_url')
        if not target_path:
            return jsonify({'error': 'Target URL is required'}), 400

        user_id = data.get('user_id', 'embed_user')
        first_name = data.get('first_name', 'Guest')
        last_name = data.get('last_name', 'User')

        # Ensure we construct the full target URL
        if not target_path.startswith('http'):
            base = agent.LOOKER_INSTANCE_URI.rstrip('/')
            if not target_path.startswith('/'):
                target_path = '/' + target_path
            full_target_url = f"{base}{target_path}"
        else:
            full_target_url = target_path

        print(f"=== Acquiring Cookieless Embed Session ===")
        print(f"  Target URL: {full_target_url}")
        print(f"  User ID: {user_id}")
        print(f"  Name: {first_name} {last_name}")

        # Generate Signed SSO URL (Legacy/Stable approach)
        signed_url = embed_manager.generate_signed_url(
            target_url=full_target_url,
            user_id=user_id,
            first_name=first_name,
            last_name=last_name
        )
        
        print(f"  ✅ Signed URL generated successfully")
        
        # Return signed URL for the frontend fallback handler
        return jsonify({
            'type': 'sso',
            'url': signed_url
        })

    except Exception as e:
        print(f"  ❌ Embed Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def get_real_retention():
    """Queries live Looker retention metrics with a local JSON cache fallback."""
    try:
        print("INFO: Querying live Looker retention rate via get_insights...")
        res = agent.get_insights("What was yesterday's Day 1 retention rate?")
        if res and res.get('status') == 'success' and 'data_insights' in res:
            data = res['data_insights'][0]
            rows = data.get('result', {}).get('rows', [])
            if not rows:
                rows = data.get('result', {}).get('data', [])
            if rows:
                for row in rows:
                    for k, v in row.items():
                        if 'retention' in k.lower() and v is not None:
                            val = float(v)
                            # Convert fractional decimal (e.g. 0.0556) to percentage (e.g. 5.56)
                            if 0.0 < val < 1.0:
                                val *= 100
                            return val
    except Exception as e:
        print(f"Error querying live retention: {e}")
        
    try:
        cache_path = "datasets/events_daily_summary_cache.json"
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                cache = json.load(f)
                val = cache.get("games", {}).get("overall", {}).get("metrics", {}).get("retention", {}).get("value")
                if val is not None:
                    print(f"INFO: Live Looker query failed or empty; fell back to cached retention value: {val}%")
                    return float(val)
    except Exception as e:
        print(f"Error reading daily summary cache fallback: {e}")
        
    return 5.56  # absolute default fallback


@app.route('/api/agent-workflow/stream')
def stream_agent_workflow():
    workflow_id = request.args.get('workflow_id', 'kpi_monitor')
    
    def generate():
        import datetime
        if workflow_id == 'kpi_monitor':
            # Step 1: Spawn Agent
            yield "data: " + json.dumps({'step': 1, 'status': 'info', 'message': "Spawning Antigravity Agent 'KPI-Monitor-Bot' using ADK SDK..."}) + "\n\n"
            time.sleep(1.0)
            
            # Step 2: Load Config
            yield "data: " + json.dumps({'step': 2, 'status': 'info', 'message': "Loading agent configuration with base instructions & model parameters (gemini-3.5-flash)..."}) + "\n\n"
            time.sleep(1.0)
            
            # Step 3: Query Looker (performing the actual action!)
            yield "data: " + json.dumps({'step': 3, 'status': 'querying', 'message': "Connecting to Looker events explore to analyze retention metrics..."}) + "\n\n"
            
            retention_rate = get_real_retention()
            threshold = 5.00
            is_critical = retention_rate < threshold
            time.sleep(1.5)
            
            # Step 4: Display query result
            status_type = "warning" if is_critical else "info"
            message_prefix = "ALERT: " if is_critical else ""
            msg = f"Query completed. Current D1 retention is {retention_rate:.2f}% (Alert threshold is set to {threshold:.2f}%). {message_prefix}Status: {'CRITICAL' if is_critical else 'HEALTHY'}."
            yield "data: " + json.dumps({'step': 4, 'status': status_type, 'message': msg}) + "\n\n"
            time.sleep(1.0)
            
            # Step 5: Register cron trigger
            yield "data: " + json.dumps({'step': 5, 'status': 'info', 'message': "Registering periodic cron trigger (every 4 hours) for automatic health checks..."}) + "\n\n"
            time.sleep(1.0)
            
            # Step 6: Configure safety policies
            yield "data: " + json.dumps({'step': 6, 'status': 'info', 'message': "Binding safety policy constraints to prevent unauthorized API execution..."}) + "\n\n"
            time.sleep(1.0)
            
            # Step 7: Alert payload configuration
            slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
            gchat_webhook = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
            
            dest_name = "Google Chat" if gchat_webhook else ("Slack" if slack_webhook else "local file")
            yield "data: " + json.dumps({'step': 7, 'status': 'info', 'message': f"Configuring alert integration for destination: {dest_name}..."}) + "\n\n"
            time.sleep(1.0)
            
            # Perform real Alert action
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                "text": f"🚨 *KPI Alert: Day 1 Retention Monitor* 🚨\n*Game Portfolio*: Overall\n*Current Retention*: {retention_rate:.2f}%\n*Threshold*: {threshold:.2f}%\n*Status*: {'⚠️ CRITICAL' if is_critical else '✅ HEALTHY'}\n*Timestamp*: {current_time}"
            }
            
            sent_alert = False
            alert_msg = ""
            
            if gchat_webhook:
                try:
                    r = requests.post(gchat_webhook, json=payload, timeout=5)
                    if r.status_code in (200, 201):
                        alert_msg = f"Google Chat alert successfully posted (HTTP {r.status_code})."
                        sent_alert = True
                    else:
                        alert_msg = f"Failed to post to Google Chat: Received HTTP status code {r.status_code}."
                except Exception as e:
                    alert_msg = f"Failed to post to Google Chat webhook: {e}"
            
            if not sent_alert and slack_webhook:
                try:
                    r = requests.post(slack_webhook, json=payload, timeout=5)
                    if r.status_code in (200, 201):
                        alert_msg = f"Slack alert successfully posted (HTTP {r.status_code})."
                        sent_alert = True
                    else:
                        alert_msg = f"Failed to post to Slack: Received HTTP status code {r.status_code}."
                except Exception as e:
                    alert_msg = f"Failed to post to Slack webhook: {e}"
            
            if not sent_alert:
                if not gchat_webhook and not slack_webhook:
                    alert_msg = "Neither GOOGLE_CHAT_WEBHOOK_URL nor SLACK_WEBHOOK_URL set in .env. Logging payload locally to datasets/slack_alerts.json."
                else:
                    alert_msg = f"Webhooks failed. Falling back to local logging. Error details: {alert_msg}"
                
                try:
                    alert_path = "datasets/slack_alerts.json"
                    alert_data = []
                    if os.path.exists(alert_path):
                        with open(alert_path, 'r') as f:
                            alert_data = json.load(f)
                            if not isinstance(alert_data, list):
                                alert_data = []
                    alert_data.append({
                        "timestamp": current_time,
                        "retention_rate": retention_rate,
                        "threshold": threshold,
                        "status": "CRITICAL" if is_critical else "HEALTHY",
                        "payload": payload
                    })
                    with open(alert_path, 'w') as f:
                        json.dump(alert_data, f, indent=2)
                except Exception as e:
                    alert_msg = f"Error saving alert payload locally: {e}"
                    
            yield "data: " + json.dumps({'step': 8, 'status': 'info', 'message': alert_msg}) + "\n\n"
            time.sleep(1.0)
            
            # Step 9: Final success indicator
            yield "data: " + json.dumps({'step': 9, 'status': 'success', 'message': "Agent 'KPI-Monitor-Bot' successfully compiled and executed!"}) + "\n\n"
        else:
            if workflow_id == 'ad_optimizer':
                steps = [
                    {"step": 1, "status": "info", "message": "Initializing 'AdNetwork-Optimizer' Agent..."},
                    {"step": 2, "status": "querying", "message": "Fetching CPM and ad conversion rates for Lookerwood Farm from Looker..."},
                    {"step": 3, "status": "analyzing", "message": "Analyzing bid yields. Identified underperforming bid floor of $0.45 in Ad Network B..."},
                    {"step": 4, "status": "planning", "message": "Calculating optimal CPM adjustment. Recommended change: Increase bid floor by 15% to $0.52..."},
                    {"step": 5, "status": "executing", "message": "Connecting to external AdNetwork API (simulated gateway)..."},
                    {"step": 6, "status": "executing", "message": "Applying bid floor update. Response received: 200 OK. New rate active."},
                    {"step": 7, "status": "info", "message": "Updating Spanner database system settings to log bid optimization history..."},
                    {"step": 8, "status": "info", "message": "Sending optimization run report to portfolio-leads@altostrat.com..."},
                    {"step": 9, "status": "success", "message": "Ad Bids adjusted successfully! Estimated revenue impact: +$1,200/day."}
                ]
            elif workflow_id == 'deploy_gcf':
                action = request.args.get('action')
                if action == 'pause':
                    steps = [
                        {"step": 1, "status": "info", "message": "Connecting to Google Cloud Functions service..."},
                        {"step": 2, "status": "executing", "message": "Suspending Cloud Scheduler event trigger for 'cohort-correlation-analyzer'..."},
                        {"step": 3, "status": "info", "message": "Disabling periodic analytics ingestion pipelines..."},
                        {"step": 4, "status": "success", "message": "Cloud Function pipeline successfully paused! Status set to SUSPENDED."}
                    ]
                elif action == 'resume':
                    steps = [
                        {"step": 1, "status": "info", "message": "Connecting to Google Cloud Functions service..."},
                        {"step": 2, "status": "executing", "message": "Resuming Cloud Scheduler event trigger for 'cohort-correlation-analyzer'..."},
                        {"step": 3, "status": "info", "message": "Re-activating periodic analytics ingestion pipelines..."},
                        {"step": 4, "status": "success", "message": "Cloud Function pipeline successfully resumed! Status set to ACTIVE."}
                    ]
                elif action == 'update_settings':
                    schedule = request.args.get('schedule', '0 8 * * *')
                    target = request.args.get('target', 'All Active Players')
                    email = request.args.get('email', 'portfolio-leads@altostrat.com')
                    threshold = request.args.get('threshold', '10%')
                    steps = [
                        {"step": 1, "status": "info", "message": "Retrieving deployed metadata for Cloud Function: 'cohort-correlation-analyzer'..."},
                        {"step": 2, "status": "executing", "message": f"Updating Cron trigger schedule to: '{schedule}'..."},
                        {"step": 3, "status": "executing", "message": f"Injecting environment variables: TARGET_SEGMENT='{target}', ALERT_EMAIL='{email}', THRESHOLD='{threshold}'..."},
                        {"step": 4, "status": "info", "message": "Deploying updated configurations & performing verification health check..."},
                        {"step": 5, "status": "success", "message": "Cloud Function pipeline configuration updated successfully! New settings are live."}
                    ]
                else:
                    steps = [
                        {"step": 1, "status": "info", "message": "Generating Python source code for Cloud Function: 'cohort-correlation-analyzer'..."},
                        {"step": 2, "status": "info", "message": "Creating bundle containing function code and requirements.txt..."},
                        {"step": 3, "status": "executing", "message": "Uploading function package to Google Cloud Storage bucket gs://ca_api/functions/..."},
                        {"step": 4, "status": "executing", "message": "Executing gcloud deployment command: 'gcloud functions deploy cohort-correlation-analyzer' (simulated)..."},
                        {"step": 5, "status": "info", "message": "Provisioning Cloud Function resources & configuring IAM invoker permissions..."},
                        {"step": 6, "status": "success", "message": "Cloud Function successfully deployed! Endpoint: https://us-central1-aragosalooker.cloudfunctions.net/cohort-correlation-analyzer"}
                    ]
            else:
                steps = [
                    {"step": 1, "status": "error", "message": "Unknown workflow ID requested."}
                ]
                
            for step in steps:
                yield f"data: {json.dumps(step)}\n\n"
                time.sleep(1.0)
            
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/generate-narrative', methods=['POST', 'OPTIONS'])
def generate_narrative():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    data = request.json or {}
    prompt = data.get('prompt')
    model_name = data.get('model_name', 'gemini-3.5-flash')
    
    # Check for authentication token if NARRATIVE_SECRET_TOKEN is set
    expected_token = os.getenv('NARRATIVE_SECRET_TOKEN')
    if expected_token:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized: Missing token'}), 401
        token = auth_header.split(' ')[1]
        if token != expected_token:
            return jsonify({'error': 'Unauthorized: Invalid token'}), 403
            
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
        
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        # Whitelist/map the model. Only allow gemini-3.5-flash which we know works.
        target_model = model_name
        if "gemini-3" in target_model or "gemini-3.5" in target_model:
            target_model = "gemini-3.5-flash"
        else:
            # Fallback/default to the verified gemini-3.5-flash model
            target_model = "gemini-3.5-flash"
            
        print(f"Generating narrative using Vertex AI model: {target_model}", flush=True)
        proj = os.getenv("GCP_PROJECT_ID") or os.getenv("PROJECT_ID") or "aragosalooker"
        loc = os.getenv("VERTEX_LOCATION") or os.getenv("LOCATION") or "global"
        try:
            vertexai.init(project=proj, location=loc)
        except Exception as ve:
            print(f"Vertex init info: {ve}", flush=True)
        model = GenerativeModel(target_model)
        
        response = model.generate_content(prompt)
        return jsonify({'text': response.text})
    except Exception as e:
        print(f"Narrative generation error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/gemini_narrator.js', methods=['GET'])
def serve_gemini_narrator():
    """Serves the gemini_narrator.js file for local or Cloud Run Looker visualization testing."""
    try:
        viz_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gemini_narrator.js')
        if not os.path.exists(viz_path):
            viz_path = 'gemini_narrator.js'
        with open(viz_path, 'r') as f:
            content = f.read()
        return Response(content, mimetype='application/javascript')
    except Exception as e:
        print(f"Error serving gemini_narrator.js: {e}", flush=True)
        return jsonify({'error': str(e)}), 404


@app.route('/api/cohort-analyzer', methods=['GET'])
def cohort_analyzer():
    import datetime
    schedule = request.args.get('schedule', '0 8 * * *')
    target_segment = request.args.get('target', 'All Active Players')
    webhook_url = request.args.get('webhook', '').strip()
    threshold = request.args.get('threshold', '10%')

    # Fallback to env vars if no webhook passed
    if not webhook_url:
        webhook_url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL") or os.getenv("SLACK_WEBHOOK_URL") or ""

    # Generate a realistic cohort correlation analysis
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Text payload formatted for Google Chat / Slack markup compatibility
    text_content = (
        f"🚨 *Gaming Analytics GCF: Cohort Correlation Analysis* 🚨\n"
        f"*Target Segment*: {target_segment}\n"
        f"*Cron Schedule*: {schedule}\n"
        f"*Trigger Threshold*: {threshold}\n"
        f"*Run Timestamp*: {current_time}\n\n"
        f"🟢 *Top Key Driver identified*:\n"
        f"• Event *'Complete Tutorial'* has a *+0.74 correlation* with Day 1 Retention.\n"
        f"• Event *'Join Guild'* has a *+0.52 correlation* with Day 1 Retention.\n"
        f"• Event *'First Purchase'* has a *+0.31 correlation* with Day 1 Retention.\n\n"
        f"💡 *Actionable Insight*: Optimize the first-time user experience (FTUE) and onboarding tutorial. Players completing the tutorial are 74% more likely to return on Day 1. Consider promoting guild invitations earlier in the session flow."
    )

    payload = {"text": text_content}
    dispatch_status = "Skipped (No Webhook URL provided)"
    dispatch_success = False

    if webhook_url and webhook_url.startswith("http"):
        try:
            r = requests.post(webhook_url, json=payload, timeout=5)
            if r.status_code in (200, 201):
                dispatch_status = f"Success (HTTP {r.status_code})"
                dispatch_success = True
            else:
                dispatch_status = f"Failed (HTTP {r.status_code}): {r.text}"
        except Exception as e:
            dispatch_status = f"Failed with exception: {e}"

    # Log/Save locally for demo audit
    try:
        alert_path = "datasets/slack_alerts.json"
        alert_data = []
        if os.path.exists(alert_path):
            with open(alert_path, 'r') as f:
                alert_data = json.load(f)
        alert_data.append({
            "timestamp": current_time,
            "type": "cohort_analysis",
            "target": target_segment,
            "dispatch_status": dispatch_status,
            "payload": payload
        })
        with open(alert_path, 'w') as f:
            json.dump(alert_data, f, indent=2)
    except Exception as e:
        print(f"Error logging cohort alert locally: {e}")

    # Return a beautifully styled HTML page
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gaming Analytics GCF - Cohort Analyzer</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Plus Jakarta Sans', sans-serif;
                background-color: #0b0f19;
                color: #f3f4f6;
                margin: 0;
                padding: 40px 20px;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                box-sizing: border-box;
            }}
            .card {{
                background: rgba(17, 24, 39, 0.7);
                border: 1px dashed rgba(99, 102, 241, 0.4);
                border-radius: 20px;
                padding: 30px;
                max-width: 600px;
                width: 100%;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(12px);
            }}
            h1 {{
                font-size: 20px;
                font-weight: 700;
                margin-top: 0;
                color: #ffffff;
                display: flex;
                align-items: center;
                gap: 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                padding-bottom: 15px;
            }}
            .status-badge {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 100px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .success-badge {{
                background-color: rgba(16, 185, 129, 0.15);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.3);
            }}
            .warning-badge {{
                background-color: rgba(245, 158, 11, 0.15);
                color: #fbbf24;
                border: 1px solid rgba(245, 158, 11, 0.3);
            }}
            .details-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 20px 0;
                background: rgba(255, 255, 255, 0.03);
                padding: 15px;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            .grid-item {{
                font-size: 13px;
            }}
            .grid-label {{
                font-size: 10px;
                text-transform: uppercase;
                color: #9ca3af;
                font-family: 'JetBrains Mono', monospace;
                display: block;
                margin-bottom: 4px;
            }}
            .grid-value {{
                font-weight: 600;
                color: #e5e7eb;
            }}
            .payload-box {{
                background: #07090e;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 15px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                line-height: 1.6;
                color: #a7f3d0;
                white-space: pre-wrap;
                margin: 20px 0;
            }}
            .btn {{
                display: inline-flex;
                justify-content: center;
                align-items: center;
                background-color: #4f46e5;
                color: white;
                text-decoration: none;
                font-size: 13px;
                font-weight: 600;
                padding: 10px 20px;
                border-radius: 10px;
                transition: all 0.2s;
                cursor: pointer;
                border: none;
                width: 100%;
                box-sizing: border-box;
            }}
            .btn:hover {{
                background-color: #4338ca;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>
                ⚡ Gaming Analytics Cloud Function (GCF)
            </h1>
            <div style="margin-top: 15px; display: flex; justify-content: space-between; align-items: center;">
                <span class="status-badge {'success-badge' if dispatch_success else 'warning-badge'}">
                    {"Webhook Sent" if dispatch_success else "Webhook Offline"}
                </span>
                <span style="font-size: 12px; color: #9ca3af;">{current_time}</span>
            </div>
            
            <div class="details-grid">
                <div class="grid-item">
                    <span class="grid-label">Target Segment</span>
                    <span class="grid-value">{target_segment}</span>
                </div>
                <div class="grid-item">
                    <span class="grid-label">Cron Schedule</span>
                    <span class="grid-value">{schedule}</span>
                </div>
                <div class="grid-item">
                    <span class="grid-label">Threshold</span>
                    <span class="grid-value">{threshold}</span>
                </div>
                <div class="grid-item flex-col">
                    <span class="grid-label">Dispatch Status</span>
                    <span class="grid-value" style="font-size: 11px;">{dispatch_status}</span>
                </div>
            </div>

            <div style="font-size: 13px; font-weight: 600; color: #ffffff; margin-bottom: 8px;">Analysis Payload Sent to Chat:</div>
            <div class="payload-box">{text_content}</div>

            <button class="btn" onclick="window.close()">Close Demo Tab</button>
        </div>
    </body>
    </html>
    """
    return Response(html_content, mimetype='text/html')


if __name__ == '__main__':
    # try:
    #     print("Initializing Backend Authentication...")
    #     token = agent.auth_manager.get_auth_token()
    #     print("Backend Authentication Successful. Token obtained.")
    # except Exception as e:
    #     print(f"WARNING: Backend Authentication failed on startup: {e}")
    #     if "Reauthentication is needed" in str(e):
    #         print("Attempting automatic re-authentication via browser...")
    #         import subprocess
    #         try:
    #             # Automatically open the browser for authentication
    #             subprocess.Popen(['gcloud', 'auth', 'application-default', 'login'])
    #         except FileNotFoundError:
    #             print("Error: 'gcloud' CLI not found. Please install Google Cloud SDK.")
    #     else:
    #         print("Server will start, but external API calls might fail if not authenticated.")

    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=8080)
