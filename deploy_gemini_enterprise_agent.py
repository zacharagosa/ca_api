#!/usr/bin/env python3
"""
Deploy Gaming Analytics Agent to Vertex AI Agent Engine and Agent Registry
for Gemini Enterprise (GE) Integration.
"""

import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID", "1094200614711")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "aragosalooker")
# Vertex AI Reasoning Engines require a regional endpoint (e.g. us-central1)
LOCATION = os.getenv("REASONING_ENGINE_LOCATION", "us-central1")
SERVICE_NAME = "gaming-analytics"

print("==================================================================")
print("  Deploying Gaming Analytics Agent to Gemini Enterprise Platform   ")
print(f"  Project: {PROJECT_ID} ({GCP_PROJECT_ID}) | Location: {LOCATION}")
print("==================================================================")

try:
    import vertexai
    from vertexai.preview import reasoning_engines
    import agent
    
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket="gs://ca_api"
    )
    
    print("\n1. Packaging and deploying Reasoning Engine to Agent Engine...")
    remote_app = reasoning_engines.ReasoningEngine.create(
        reasoning_engine=agent.app,
        requirements=[
            "google-cloud-aiplatform>=1.38.0",
            "google-adk",
            "google-cloud-geminidataanalytics",
            "google-cloud-spanner",
            "looker-sdk",
            "pyyaml",
            "requests",
            "dotenv",
        ],
        extra_packages=[
            "./agent.py",
            "./base_instructions.yaml",
            "./agent_config.yaml",
            "./datasets",
            "./looker_embed.py",
            "./conversation_manager.py",
        ],
        display_name="Gaming Analytics Intelligence",
        description="Enterprise autonomous AI agent for Looker metrics, Spanner graph clan hierarchies, and LiveOps dashboards."
    )
    
    print("\n✅ Deployment to Agent Engine successful!")
    print(f"   Resource Name: {remote_app.resource_name}")
    print(f"   Operation: {remote_app.operation_name}")
    
    # Save deployment metadata
    deployment_record = {
        "project_id": PROJECT_ID,
        "location": LOCATION,
        "resource_name": remote_app.resource_name,
        "display_name": "Gaming Analytics Intelligence",
        "timestamp": str(os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip())
    }
    
    with open("gemini_enterprise_deployment.json", "w") as f:
        json.dump(deployment_record, f, indent=2)
        
    print("\n2. Agent Registry Integration:")
    print("   To import this deployed Reasoning Engine into Gemini Enterprise:")
    print("   a. Open Google Cloud Console -> Gemini Enterprise -> Agents (or go/ge).")
    print("   b. Click 'Add Agent' -> 'From Agent Registry / Agent Engine'.")
    print(f"   c. Select resource: {remote_app.resource_name}")
    print("   d. Publish to your team / organization.")
    
except Exception as e:
    print(f"\n⚠️ Deployment to Vertex AI Agent Engine encountered: {e}")
    print("\nAlternative (Immediate & Recommended for Demos):")
    print("Use the Gemini Enterprise OpenAPI Agent Designer integration via:")
    print("  Spec: https://ca-api-1094200614711.us-central1.run.app/openapi.yaml")
    print("  Config: gemini_enterprise_agent_config.json")
