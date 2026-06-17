import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = "1094200614711"
LOCATION = "global"

print("Initializing Vertex AI...")
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    print("Vertex AI initialized.")

    model = GenerativeModel("gemini-3.5-flash")
    chat = model.start_chat()
    print("Chat session started. Sending message with gemini-3.5-flash...")
    try:
        chat.send_message("Hello", stream=True)
    except Exception as e:
        print(f"Caught exception type: {type(e)}")
        print(f"Exception string: {str(e)}")
        print(f"Exception args: {e.args}")
        import traceback
        traceback.print_exc()
except Exception as e:
    print(f"Setup failed: {e}")
