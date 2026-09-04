#!/usr/bin/env python3
"""
Deploy Pure ADK Gaming Analytics Agent to Vertex AI Agent Engine.
Powered by Gemini 3.6 Flash, Looker CA API v2, Spanner Graph, and Looker LiveOps Dashboard MCP.
"""

import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID", "1094200614711")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "aragosalooker")
LOCATION = os.getenv("REASONING_ENGINE_LOCATION", "us-central1")

print("==================================================================")
print("   Deploying Pure Google ADK Agent to Vertex AI Agent Engine       ")
print(f"   Project: {PROJECT_ID} ({GCP_PROJECT_ID}) | Location: {LOCATION}")
print("==================================================================")

try:
    import vertexai
    from vertexai.preview import reasoning_engines
    from adk_agent import app
    
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket="gs://ca_api"
    )
    
    print("\n1. Packaging and deploying pure AdkApp to Vertex AI Agent Engine...")
    remote_app = reasoning_engines.ReasoningEngine.create(
        reasoning_engine=app,
        requirements=[
            "google-cloud-aiplatform[agent_engines,adk]>=1.75.0",
            "google-adk>=1.0.0",
            "google-cloud-geminidataanalytics",
            "google-cloud-spanner",
            "looker-sdk",
            "pyyaml",
            "requests",
            "python-dotenv",
        ],
        extra_packages=[
            "./adk_agent",
            "./agent.py",
            "./auth.py",
            "./looker_embed.py",
            "./datasets",
            "./base_instructions.yaml",
            "./agent_config.yaml",
        ],
        display_name="Gaming Analytics Intelligence (ADK)",
        description="Enterprise autonomous AI agent for Looker metrics, Spanner graph clan hierarchies, and LiveOps dashboards (Pure ADK Architecture on Gemini 3.6 Flash)."
    )
    
    print("\n✅ Deployment to Agent Engine successful!")
    print(f"   Resource Name: {remote_app.resource_name}")
    
    # Save deployment metadata
    deployment_record = {
        "project_id": PROJECT_ID,
        "gcp_project_id": GCP_PROJECT_ID,
        "location": LOCATION,
        "resource_name": remote_app.resource_name,
        "display_name": "Gaming Analytics Intelligence (ADK)",
        "framework": "google-adk",
        "model": "gemini-3.8-flash",
        "timestamp": str(os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip())
    }
    
    with open("gemini_enterprise_deployment.json", "w") as f:
        json.dump(deployment_record, f, indent=2)
        
    print("\n2. Agent Registry Integration & LiveOps Capabilities:")
    print(f"   - Reasoning Engine URI: {remote_app.resource_name}")
    print("   - Model: Gemini 3.8 Flash")
    print("   - Looker Telemetry Metrics: Active")
    print("   - Spanner Graph Analytics: Active")
    print("   - Looker Dashboard Creation & Embedding: Active")
    
except Exception as e:
    print(f"\n❌ Deployment error: {e}")
    sys.exit(1)
