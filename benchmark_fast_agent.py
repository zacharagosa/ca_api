#!/usr/bin/env python3
"""
Benchmark script to test fast agent response times.
Tests the geminidataanalytics API directly vs through the agent wrapper.
"""
import os
import sys
import time
import json
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.cloud import geminidataanalytics

# Test questions for gaming:events dataset
TEST_QUESTIONS = [
    # Simple counts
    "How many events happened yesterday?",
    "How many users were active today?",
    "Count the number of session_start events this week",
    
    # Simple aggregations
    "What is the total revenue for the last 7 days?",
    "What was the total ad revenue yesterday?",
    "What was total IAP revenue this month?",
    
    # Filtered queries
    "How many events from iOS users today?",
    "Count events from players in the United States this week",
    "How many level_up events happened yesterday?",
    
    # Breakdowns
    "Show events by platform for today",
    "Revenue by country for last 7 days",
    "Top 5 event types by count this week",
    
    # Time series
    "Daily event count for the last 7 days",
    "Revenue trend by day this month",
]

def benchmark_direct_api(question: str, project_id: str, location: str, looker_uri: str, model: str, explore: str):
    """Test direct geminidataanalytics API call."""
    start = time.time()
    
    client = geminidataanalytics.DataAgentServiceClient()
    
    try:
        data_agent_name = f"projects/{project_id}/locations/{location}/dataAgents/la-{looker_uri.replace('https://', '').replace('/', '-')}-{model}-{explore}"
        
        # Create session
        session_request = geminidataanalytics.CreateSessionRequest(
            parent=data_agent_name,
        )
        session = client.create_session(request=session_request)
        session_time = time.time() - start
        
        # Execute query
        query_start = time.time()
        stream_request = geminidataanalytics.StreamQueryDataAgentRequest(
            name=session.name,
            query=question,
        )
        
        response_text = ""
        for chunk in client.stream_query_data_agent(request=stream_request):
            if hasattr(chunk, 'response') and chunk.response:
                response_text += str(chunk.response)
        
        query_time = time.time() - query_start
        total_time = time.time() - start
        
        return {
            "success": True,
            "session_time": round(session_time, 2),
            "query_time": round(query_time, 2),
            "total_time": round(total_time, 2),
            "response_length": len(response_text),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_time": round(time.time() - start, 2),
        }

def main():
    # Load config
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION", "us-central1")
    
    # Load from dataset config
    import yaml
    dataset_name = os.getenv("DATASET_NAME", "events")
    with open(f"datasets/{dataset_name}.yaml") as f:
        dataset = yaml.safe_load(f)
    
    looker_config = dataset.get("looker", {})
    looker_uri = looker_config.get("instance_uri")
    model = looker_config.get("model")
    explore = looker_config.get("explore")
    
    print(f"Testing against: {looker_uri} / {model} / {explore}")
    print(f"Project: {project_id}, Location: {location}")
    print("-" * 60)
    
    results = []
    
    for i, question in enumerate(TEST_QUESTIONS):
        print(f"\n[{i+1}/{len(TEST_QUESTIONS)}] {question[:50]}...")
        
        result = benchmark_direct_api(question, project_id, location, looker_uri, model, explore)
        result["question"] = question
        results.append(result)
        
        if result["success"]:
            print(f"  ✓ Total: {result['total_time']}s (Session: {result['session_time']}s, Query: {result['query_time']}s)")
        else:
            print(f"  ✗ Error: {result.get('error', 'Unknown')[:50]}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r["success"]]
    if successful:
        avg_total = sum(r["total_time"] for r in successful) / len(successful)
        avg_session = sum(r["session_time"] for r in successful) / len(successful)
        avg_query = sum(r["query_time"] for r in successful) / len(successful)
        
        print(f"Successful: {len(successful)}/{len(results)}")
        print(f"Average Total Time: {round(avg_total, 2)}s")
        print(f"  - Session Creation: {round(avg_session, 2)}s ({round(avg_session/avg_total*100, 1)}%)")
        print(f"  - Query Execution: {round(avg_query, 2)}s ({round(avg_query/avg_total*100, 1)}%)")
        
        print("\nFastest queries:")
        for r in sorted(successful, key=lambda x: x["total_time"])[:3]:
            print(f"  {r['total_time']}s - {r['question'][:40]}...")
        
        print("\nSlowest queries:")
        for r in sorted(successful, key=lambda x: x["total_time"], reverse=True)[:3]:
            print(f"  {r['total_time']}s - {r['question'][:40]}...")

if __name__ == "__main__":
    main()
