from flask import Flask, request, jsonify
from flask_cors import CORS
from agent import app as agent_app, PROJECT_ID, LOCATION
import vertexai
import threading
import queue
import agent
import requests
import urllib.parse
agent.thought_queue = queue.Queue()

# Initialize Vertex AI for local execution
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket="gs://ca_api",
)

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
    user_id = data.get('user_id', 'web_user')
    session_id = data.get('session_id', 'default_session') # Use session_id if provided, else default
    
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        # Check if session exists, if not create it
        try:
            # Try to get the session. Note: get_session requires user_id as well.
            agent_app.get_session(session_id=session_id, user_id=user_id)
        except Exception:
            # If get_session fails, it likely means the session doesn't exist.
            # So we try to create it.
            print(f"Session {session_id} not found (or get failed). Creating new session...")
            try:
                agent_app.create_session(session_id=session_id, user_id=user_id)
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
                stream = agent_app.stream_query(message=user_input, user_id=user_id, session_id=session_id)
                for chunk in stream:
                    response_queue.put(("chunk", chunk))
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
                        if isinstance(chunk, dict) and "content" in chunk:
                            content = chunk["content"]
                            if "parts" in content:
                                for part in content["parts"]:
                                    if "text" in part:
                                        yield f"DATA: {part['text']}\n"
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

if __name__ == '__main__':
    app.run(port=5001, debug=True)
