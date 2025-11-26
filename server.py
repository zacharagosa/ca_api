from flask import Flask, request, jsonify
from flask_cors import CORS
from agent import app as agent_app, PROJECT_ID, LOCATION
import vertexai
import threading
import queue
import agent

# Initialize Vertex AI for local execution
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket="gs://ca_api",
)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

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
        print(f"Calling agent_app.stream_query for session {session_id}...")
        
        def generate():
            try:
                stream = agent_app.stream_query(message=user_input, user_id=user_id, session_id=session_id)
                for chunk in stream:
                    # Check for thoughts in the global queue
                    try:
                        while True:
                            thought = agent.thought_queue.get_nowait()
                            yield f"THOUGHT: {thought}\n"
                    except queue.Empty:
                        pass

                    if isinstance(chunk, dict) and "content" in chunk:
                        content = chunk["content"]
                        if "parts" in content:
                            for part in content["parts"]:
                                if "text" in part:
                                    yield f"DATA: {part['text']}\n"
            except Exception as e:
                print(f"Agent Error: {e}")
                yield f"ERROR: {str(e)}\n"
        
        return app.response_class(generate(), mimetype='text/plain')

    except Exception as e:
        print(f"Server Error: {e}") # Log the full error to the console
        import traceback
        traceback.print_exc() # Print stack trace
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
