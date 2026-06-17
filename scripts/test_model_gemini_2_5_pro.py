import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = "1094200614711"
LOCATION = "global"

print(f"Initializing Vertex AI with project {PROJECT_ID} and location {LOCATION}")
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    print("Vertex AI initialized.")
    
    print("Testing gemini-2.5-pro...")
    model = GenerativeModel("gemini-2.5-pro")
    print("Model gemini-2.5-pro initialized successfully!")
except Exception as e:
    print(f"FAILED to initialize gemini-2.5-pro: {e}")
    import traceback
    traceback.print_exc()
