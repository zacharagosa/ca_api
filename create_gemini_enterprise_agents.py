#!/usr/bin/env python3
"""
Create the 4 Specialist Agents in Gemini Enterprise (Discovery Engine) automatically.
"""

import os
import json
import subprocess
import requests

PROJECT_NUMBER = "1094200614711"
ENGINE_ID = "gemini-enterprise-17641948_1764194881063"

SPECIALIST_AGENTS = [
    {
        "displayName": "Gaming Telemetry Analyst",
        "description": "Enterprise AI specialist for Looker quantitative gaming KPI metrics (DAU, MAU, IAP & Ad revenue, D1/D7/D30 retention curves, and ARPU).",
        "reasoningEngine": "projects/1094200614711/locations/us-central1/reasoningEngines/1658654522186137600",
        "toolDescription": "Queries Looker telemetry database for DAU, revenue, retention, and ARPU metrics."
    },
    {
        "displayName": "Gaming Clan & Social Graph Intelligence",
        "description": "Enterprise AI specialist for player social graphs, guild hierarchies, clan rosters, officer networks, and whale clusters powered by Spanner ISO GQL.",
        "reasoningEngine": "projects/1094200614711/locations/us-central1/reasoningEngines/4847203058364448768",
        "toolDescription": "Queries Google Cloud Spanner graph for clan hierarchies, friendships, and player social networks."
    },
    {
        "displayName": "LiveOps Dashboard Architect",
        "description": "Enterprise AI specialist for automated Looker dashboard authoring, visual grid layouts, metric tiles, and LiveOps war room creation.",
        "reasoningEngine": "projects/1094200614711/locations/us-central1/reasoningEngines/8536777053087727616",
        "toolDescription": "Creates and configures custom Looker dashboards, visual tiles, and LiveOps war rooms on the fly."
    },
    {
        "displayName": "Gaming SSO Embed & Portal Manager",
        "description": "Enterprise AI specialist for generating signed Looker Single Sign-On (SSO) embedding URLs for dashboards and war room portals.",
        "reasoningEngine": "projects/1094200614711/locations/us-central1/reasoningEngines/9070453608931131392",
        "toolDescription": "Generates cryptographically signed SSO embed URLs for Looker dashboards and explores."
    }
]

def get_access_token():
    return subprocess.check_output(["gcloud", "auth", "print-access-token"]).decode().strip()

def create_ge_agent(spec):
    token = get_access_token()
    url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{PROJECT_NUMBER}/locations/global/collections/default_collection/engines/{ENGINE_ID}/assistants/default_assistant/agents"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": PROJECT_NUMBER
    }
    
    payload = {
        "displayName": spec["displayName"],
        "description": spec["description"],
        "adkAgentDefinition": {
            "toolSettings": {
                "toolDescription": spec["toolDescription"]
            },
            "provisionedReasoningEngine": {
                "reasoningEngine": spec["reasoningEngine"]
            }
        },
        "state": "ENABLED",
        "agentInvocationSpec": {
            "invocationMode": "AUTOMATIC"
        }
    }
    
    print(f"\nCreating Gemini Enterprise Agent: '{spec['displayName']}'...")
    resp = requests.post(url, headers=headers, json=payload)
    
    if resp.status_code in [200, 201]:
        data = resp.json()
        print(f"✅ Successfully created agent: {data.get('name')}")
        return data
    else:
        print(f"❌ Failed to create agent ({resp.status_code}): {resp.text}")
        return None

def main():
    print("==================================================================")
    print("   Provisioning 4 Specialist Agents into Gemini Enterprise         ")
    print(f"   Engine: {ENGINE_ID} | Project: {PROJECT_NUMBER}")
    print("==================================================================")
    
    created = []
    for spec in SPECIALIST_AGENTS:
        res = create_ge_agent(spec)
        if res:
            created.append({
                "displayName": spec["displayName"],
                "ge_agent_name": res.get("name"),
                "reasoningEngine": spec["reasoningEngine"],
                "state": res.get("state", "ENABLED")
            })
            
    with open("gemini_enterprise_created_agents.json", "w") as f:
        json.dump(created, f, indent=2)
        
    print("\n==================================================================")
    print(f"   🎉 Successfully created {len(created)}/4 Agents in Gemini Enterprise!")
    print("==================================================================")

if __name__ == "__main__":
    main()
