"""
Pure ADK Agent Definition for Gaming Analytics Intelligence.
Powered by Gemini 3.6 Flash and Google ADK.
"""

import os
from functools import cached_property
from google.adk.agents import llm_agent
from google.adk.models import Gemini
from google.genai import Client
from vertexai.preview.reasoning_engines import AdkApp
from .tools import (
    query_looker_telemetry,
    query_spanner_social_graph,
    create_looker_dashboard,
    generate_looker_embed_url
)

SYSTEM_INSTRUCTION = """You are Gaming Analytics Intelligence, an enterprise autonomous AI agent specialized in mobile gaming intelligence, Looker telemetry metrics, and Google Cloud Spanner social graph clan analytics.

Your capabilities include:
1. Quantitative Looker Metrics: Query DAU, revenue (IAP vs Ads), ARPU, retention (D1, D7, D30), session facts, and cross-game performance via `query_looker_telemetry`.
2. Cloud Spanner Social Graphs: Run ISO GQL queries on clan structures, guild hierarchies, friendships, officers, and whale rosters via `query_spanner_social_graph`.
3. LiveOps Dashboards: Create and manage Looker dashboards on the fly via `create_looker_dashboard`.
4. SSO Dashboard Embedding: Generate signed Looker embed URLs via `generate_looker_embed_url`.

Guidelines:
- When asked quantitative questions (revenue, DAU, retention, sessions, daily trends), ALWAYS call `query_looker_telemetry`.
- When asked about clan hierarchies, social relationships, friendships, or guilds, ALWAYS call `query_spanner_social_graph`.
- When asked cross-domain questions (e.g. 'What is the total revenue of the top 5 Dragonslayers clan members?'), first query the social graph for member gamertags, then query telemetry for their metrics.
- Deliver clear, concise, professional executive summaries with Markdown tables and Looker Explore drill-down links.
"""

PROJECT_ID = os.getenv("PROJECT_ID", "1094200614711")

class GlobalGemini(Gemini):
    """Custom Gemini LLM provider targeting the global Vertex AI endpoint for Gemini 3.6 Flash."""
    @cached_property
    def api_client(self) -> Client:
        return Client(vertexai=True, project=PROJECT_ID, location="global")

my_llm = GlobalGemini(model="gemini-3.6-flash")

root_agent = llm_agent.LlmAgent(
    name="Gaming_Analytics_Intelligence",
    model=my_llm,
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        query_looker_telemetry,
        query_spanner_social_graph,
        create_looker_dashboard,
        generate_looker_embed_url,
    ],
)

class GamingAdkApp(AdkApp):
    """Pure ADK Application supporting both Streaming and Unary Console Playground."""

    def register_operations(self):
        """Register operations for both Unary Console Playground (:query) and Streaming (:streamQuery)."""
        ops = super().register_operations()
        if "" not in ops:
            ops[""] = []
        if "query" not in ops[""]:
            ops[""].append("query")
        return ops

    def set_up(self):
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        agent = self._tmpl_attrs.get("agent")
        if agent and getattr(agent, "__pydantic_private__", None) is None:
            object.__setattr__(agent, "__pydantic_private__", {})
        super().set_up()

    def query(self, *args, **kwargs) -> dict:
        """Unary execution method for Google Cloud Console Playground and REST queries."""
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        msg = ""
        if args:
            msg = args[0]
        else:
            msg = kwargs.get("message") or kwargs.get("prompt") or kwargs.get("question") or ""
        
        user_id = kwargs.get("user_id", "default_user")
        session_id = kwargs.get("session_id", None)
        
        full_text = []
        final_event = {}
        for event in self.stream_query(message=msg, user_id=user_id, session_id=session_id):
            final_event = event
            if isinstance(event, dict):
                content = event.get("content", {})
                parts = content.get("parts", []) if isinstance(content, dict) else []
                for p in parts:
                    if isinstance(p, dict) and "text" in p:
                        full_text.append(p["text"])
        
        return {
            "response": "".join(full_text),
            "event": final_event
        }

    def stream_query(self, *args, **kwargs):
        """Streaming execution method for Gemini Enterprise and SSE consumers."""
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        agent = self._tmpl_attrs.get("agent")
        if agent and getattr(agent, "__pydantic_private__", None) is None:
            object.__setattr__(agent, "__pydantic_private__", {})
        if args:
            msg = args[0]
            user_id = kwargs.pop("user_id", "default_user")
            session_id = kwargs.pop("session_id", None)
            yield from super().stream_query(message=msg, user_id=user_id, session_id=session_id, **kwargs)
        else:
            if "user_id" not in kwargs:
                kwargs["user_id"] = "default_user"
            yield from super().stream_query(**kwargs)

    def streaming_agent_run_with_events(self, request_json: str):
        """Gemini Enterprise (Dolphin) agent event streaming handler."""
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        agent = self._tmpl_attrs.get("agent")
        if agent and getattr(agent, "__pydantic_private__", None) is None:
            object.__setattr__(agent, "__pydantic_private__", {})
        yield from super().streaming_agent_run_with_events(request_json)

app = GamingAdkApp(agent=root_agent)
