import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import vertexai
from agent import run_deep_analysis

PROJECT_ID = "1094200614711"
LOCATION = "global"

print(f"Initializing Vertex AI with project {PROJECT_ID} and location {LOCATION}")
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    print("Vertex AI initialized.")
    
    question = "Compare the total IAP revenue and count of active users between iOS and Android users across all games for the last 30 days. Give me a detailed breakdown."
    print(f"Running deep analysis for: {question}")
    
    for chunk in run_deep_analysis(question):
        print(f"Received chunk: {chunk}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
