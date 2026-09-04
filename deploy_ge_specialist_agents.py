#!/usr/bin/env python3
"""
Deploy 4 Specialized Gaming AI Agents to Vertex AI Agent Engine for Gemini Enterprise (GE).

Agents:
1. Gaming Telemetry Analyst (Looker CA API v2 - DAU, Revenue, Retention)
2. Gaming Clan & Social Graph Intelligence (Spanner ISO GQL Graph)
3. LiveOps Dashboard Architect (Looker LiveOps War Room Builder)
4. Gaming SSO Embed & Portal Manager (Signed Looker Embed Generator)
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID", "1094200614711")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "aragosalooker")
LOCATION = os.getenv("REASONING_ENGINE_LOCATION", "us-central1")

COMMON_REQUIREMENTS = [
    "google-cloud-aiplatform[agent_engines,adk]>=1.75.0",
    "google-adk>=1.0.0",
    "google-cloud-geminidataanalytics",
    "google-cloud-spanner",
    "looker-sdk",
    "pyyaml",
    "requests",
    "python-dotenv",
]

COMMON_EXTRA_PACKAGES = [
    "./ge_agents",
    "./agent.py",
    "./auth.py",
    "./looker_embed.py",
    "./datasets",
    "./base_instructions.yaml",
    "./agent_config.yaml",
]

AGENT_SPECS = {
    "telemetry": {
        "module": "ge_agents.telemetry_analyst.agent",
        "display_name": "Gaming Telemetry Analyst",
        "description": "Enterprise AI specialist for Looker quantitative gaming KPI metrics (DAU, MAU, IAP & Ad revenue, D1/D7/D30 retention curves, and ARPU).",
        "icon": "TrendingUp",
        "category": "Analytics & BI",
    },
    "social_graph": {
        "module": "ge_agents.social_graph_analyst.agent",
        "display_name": "Gaming Clan & Social Graph Intelligence",
        "description": "Enterprise AI specialist for player social graphs, guild hierarchies, clan rosters, officer networks, and whale clusters powered by Spanner ISO GQL.",
        "icon": "Network",
        "category": "Social & Community",
    },
    "dashboard_architect": {
        "module": "ge_agents.dashboard_architect.agent",
        "display_name": "LiveOps Dashboard Architect",
        "description": "Enterprise AI specialist for automated Looker dashboard authoring, visual grid layouts, metric tiles, and LiveOps war room creation.",
        "icon": "LayoutDashboard",
        "category": "LiveOps & Reporting",
    },
    "embed_manager": {
        "module": "ge_agents.embed_manager.agent",
        "display_name": "Gaming SSO Embed & Portal Manager",
        "description": "Enterprise AI specialist for generating signed Looker Single Sign-On (SSO) embedding URLs for dashboards and war room portals.",
        "icon": "ShieldCheck",
        "category": "Security & Embedding",
    },
}

def deploy_agent(key: str, spec: dict):
    import vertexai
    from vertexai.preview import reasoning_engines
    import importlib

    print(f"\n==================================================================")
    print(f"   Deploying: {spec['display_name']} ({key})")
    print(f"==================================================================")

    mod = importlib.import_module(spec["module"])
    agent_app = getattr(mod, "app")

    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket="gs://ca_api"
    )

    remote_app = reasoning_engines.ReasoningEngine.create(
        reasoning_engine=agent_app,
        requirements=COMMON_REQUIREMENTS,
        extra_packages=COMMON_EXTRA_PACKAGES,
        display_name=f"{spec['display_name']} (GE)",
        description=spec["description"]
    )

    print(f"✅ Deployment successful!")
    print(f"   Resource Name: {remote_app.resource_name}")

    return {
        "key": key,
        "display_name": spec["display_name"],
        "description": spec["description"],
        "icon": spec["icon"],
        "category": spec["category"],
        "resource_name": remote_app.resource_name,
        "location": LOCATION,
        "model": "gemini-3.6-flash",
    }

def main():
    parser = argparse.ArgumentParser(description="Deploy GE Specialist Agents")
    parser.add_argument("--agent", choices=["telemetry", "social_graph", "dashboard_architect", "embed_manager", "all"], default="all", help="Agent to deploy")
    args = parser.parse_args()

    results_file = "gemini_enterprise_specialist_agents.json"
    results = {}
    if os.path.exists(results_file):
        try:
            with open(results_file, "r") as f:
                results = json.load(f)
        except Exception:
            results = {}

    targets = AGENT_SPECS.keys() if args.agent == "all" else [args.agent]

    for key in targets:
        spec = AGENT_SPECS[key]
        try:
            record = deploy_agent(key, spec)
            results[key] = record
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            print(f"❌ Failed to deploy {key}: {e}")

    print("\n==================================================================")
    print("   🎉 Gemini Enterprise Specialist Agent Deployment Summary       ")
    print("==================================================================")
    for k, v in results.items():
        print(f"• {v['display_name']}:")
        print(f"    Reasoning Engine: {v['resource_name']}")
        print(f"    Model: {v.get('model', 'gemini-3.6-flash')}")

if __name__ == "__main__":
    main()
