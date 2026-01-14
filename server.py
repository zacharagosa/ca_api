from flask import Flask, request, jsonify, Response, stream_with_context
import json
import time
import os

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

# Vertex AI is initialized in agent.py to ensure it is configured before agent creation.

app = Flask(__name__, static_folder='frontend/dist', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

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


@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
        
    print(f"Received request: {request.json}") # Debug log
    data = request.json
    user_input = data.get('message')
    deep_analysis = data.get('deep_analysis', False)
    agent_type = data.get('agent_type', 'fast')  # 'fast', 'deep', or 'mcp'
    user_id = data.get('user_id', 'web_user')
    session_id = data.get('session_id', 'default_session') # Use session_id if provided, else default
    force_refresh = data.get('force_refresh', False)
    
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
                # Prepend explicit instruction based on user mode (skip for MCP)
                final_input = user_input
                if agent_type == 'mcp':
                    # MCP agent handles the request directly
                    pass
                elif deep_analysis or agent_type == 'deep':
                    final_input = f"Instruction: PERFORM_DEEP_ANALYSIS. Question: {user_input}"
                else:
                    final_input = f"Instruction: FAST_RESPONSE. Question: {user_input}"

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
                stream = current_agent_app.stream_query(message=final_input, user_id=user_id, session_id=session_id)
                
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
                        yield f"THOUGHT: {thought}\n"
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
                             yield f"DATA: {chunk.text}\n"
                        # Handle dictionary (legacy or deep analysis raw chunks if any)
                        elif isinstance(chunk, dict):
                            if "content" in chunk:
                                content = chunk["content"]
                                if "parts" in content:
                                    for part in content["parts"]:
                                        if "text" in part:
                                            yield f"DATA: {part['text']}\n"
                            elif "text" in chunk:
                                yield f"DATA: {chunk['text']}\n"
                        # Fallback for string
                        elif isinstance(chunk, str):
                             yield f"DATA: {chunk}\n"
                    elif type_ == "done":
                        break
                    elif type_ == "error":
                        yield f"ERROR: {str(data)}\n"
                        break
                except queue.Empty:
                    # If agent is still running, continue loop to check thoughts again
                    if not agent_thread.is_alive() and response_queue.empty() and agent.thought_queue.empty():
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
    """Generates a signed Looker embed URL using the Looker SDK."""
    if not embed_manager:
        return jsonify({'error': 'Embed Manager not initialized'}), 500
        
    try:
        data = request.json
        # Target URL from frontend is likely relative "/embed/...", but SDK might want full or specific format
        # SDK `create_sso_embed_url` often expects the full URL including protocol/host if strictly validation
        # OR just the path. Let's try passing what we receive. 
        # Actually, standard is usually the full URL *except* the /login/embed/ part? 
        # Wait, `target_url` for `create_sso_embed_url` should be the destination URL.
        # e.g. https://<instance>/embed/dashboards/1
        
        target_path = data.get('target_url')
        if not target_path:
            return jsonify({'error': 'Target URL is required'}), 400

        # Ensure we construct the full target URL if we only got a path
        if not target_path.startswith('http'):
             # Looker Instance URI usually has no trailing slash, target_path starts with /
             # But let's be careful.
             base = agent.LOOKER_INSTANCE_URI.rstrip('/')
             if not target_path.startswith('/'):
                 target_path = '/' + target_path
             full_target_url = f"{base}{target_path}"
        else:
            full_target_url = target_path

        user_id = data.get('user_id', 'external_user_123')
        
        signed_url = embed_manager.generate_signed_url(
            target_url=full_target_url,
            user_id=user_id
        )
        
        return jsonify({'url': signed_url})

    except Exception as e:
        print(f"Embed Gen Error: {e}")
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    try:
        print("Initializing Backend Authentication...")
        token = agent.auth_manager.get_auth_token()
        print("Backend Authentication Successful. Token obtained.")
    except Exception as e:
        print(f"WARNING: Backend Authentication failed on startup: {e}")
        if "Reauthentication is needed" in str(e):
            print("Attempting automatic re-authentication via browser...")
            import subprocess
            try:
                # Automatically open the browser for authentication
                subprocess.Popen(['gcloud', 'auth', 'application-default', 'login'])
            except FileNotFoundError:
                print("Error: 'gcloud' CLI not found. Please install Google Cloud SDK.")
        else:
            print("Server will start, but external API calls might fail if not authenticated.")

    app.run(debug=True, host='0.0.0.0', port=8080)
