"""
Shared Model Configuration and Authentication for Gemini Enterprise Specialist Agents.
"""

import os
from functools import cached_property
from google.adk.models import Gemini
from google.genai import Client

PROJECT_ID = os.getenv("PROJECT_ID", "1094200614711")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "aragosalooker")
LOOKER_INSTANCE_URI = os.getenv("LOOKER_INSTANCE_URI", "https://3417a175-fe20-4370-974f-2f2b535340ab.looker.app")
LOOKER_CLIENT_ID = os.getenv("LOOKER_CLIENT_ID", "DgcB4DCwGPbrczp4cmcN")
LOOKER_CLIENT_SECRET = os.getenv("LOOKER_CLIENT_SECRET", "5dzbFDwdZ4Cd7n8V44XcbYGN")
SPANNER_INSTANCE = os.getenv("SPANNER_INSTANCE_ID", "gaming-instance")
SPANNER_DATABASE = os.getenv("SPANNER_DATABASE_ID", "gaming-graph")

class GlobalGemini(Gemini):
    """Custom Gemini LLM provider targeting the global Vertex AI endpoint for Gemini 3.6 Flash."""
    @cached_property
    def api_client(self) -> Client:
        return Client(vertexai=True, project=PROJECT_ID, location="global")
