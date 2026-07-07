#!/usr/bin/env python3
"""
Test script to run the new fast agent features locally.
Executes sample questions against agent.fast_query and logs the streamed chunks.
"""
import os
import sys
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

import vertexai
from agent import fast_query

PROJECT_ID = os.getenv("PROJECT_ID", "1094200614711")
LOCATION = os.getenv("LOCATION", "global")

def test_question(question: str):
    print("\n" + "=" * 80)
    print(f"QUESTION: {question}")
    print("=" * 80)
    
    try:
        for chunk in fast_query(question):
            chunk_type = chunk.get("type")
            content = chunk.get("content")
            
            if chunk_type == "thought":
                # Print thoughts in dim color or marked
                print(f"[THOUGHT]: {content}")
            elif chunk_type == "text":
                print(f"[TEXT]: {content}")
            elif chunk_type == "data":
                print(f"[DATA]: Found {len(content.get('rows', []))} rows.")
                print(f"  Explore URL: {content.get('explore_url')}")
                if content.get('rows'):
                    print(f"  Sample Row: {content['rows'][0]}")
            elif chunk_type == "chart":
                print("[CHART]: Vega Config received:")
                print(json.dumps(content, indent=2))
            elif chunk_type == "disambiguation":
                print("[DISAMBIGUATION]: Suggestions received:")
                print(json.dumps(content, indent=2))
            elif chunk_type == "error":
                print(f"[ERROR]: {content}")
            elif chunk_type == "done":
                print("[DONE]")
    except Exception as e:
        print(f"[EXCEPTION]: {e}")

def main():
    print(f"Initializing Vertex AI with project={PROJECT_ID}, location={LOCATION}...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    test_cases = [
        # 1. Chart Visualization request
        "Plot a line chart of daily active users (DAU) for the last 7 days.",
        
        # 2. Disambiguation request
        "Show revenue numbers.",
        
        # 3. Glossary Term request
        "What was the ARPU for Lookerwood Farm yesterday?",
        
        # 4. Standard text query with reasoning/thoughts
        "What was the top country by total revenue yesterday?"
    ]
    
    # Allow running a specific index or custom query
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.isdigit():
            idx = int(arg) - 1
            if 0 <= idx < len(test_cases):
                test_question(test_cases[idx])
            else:
                print(f"Invalid index. Please select 1 to {len(test_cases)}.")
        else:
            test_question(arg)
    else:
        print("Running all test cases sequentially...")
        for case in test_cases:
            test_question(case)

if __name__ == "__main__":
    main()
