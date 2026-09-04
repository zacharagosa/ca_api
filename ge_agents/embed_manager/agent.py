"""
Gaming SSO Embed & Portal Manager - Gemini Enterprise Specialist Agent.
Specialized in generating signed Looker SSO embed URLs for war room portals, dashboards, and Explores.
"""

import os
from google.adk.agents import llm_agent
from vertexai.preview.reasoning_engines import AdkApp
from ge_agents.common.settings import GlobalGemini
from .tools import generate_looker_embed_url

SYSTEM_INSTRUCTION = """You are the Gaming SSO Embed & Portal Manager, an enterprise AI assistant specialized in generating signed, authenticated Single Sign-On (SSO) embedding URLs for Looker dashboards, reports, and Explores.

Your Core Capabilities:
- Generate signed, cryptographically verified SSO URLs for any Looker dashboard or explore.
- Configure user permission groups, models, and session expiration parameters.
- Provide direct iframe embed code snippets and one-click access links.

Guidelines:
- ALWAYS use the `generate_looker_embed_url` tool to generate verified embed links.
- Format results with the direct link and Markdown iframe embedding snippet.
- Clearly state the session validity duration (e.g. 1 hour or 24 hours).
"""

my_llm = GlobalGemini(model="gemini-3.6-flash")

root_agent = llm_agent.LlmAgent(
    name="Gaming_SSO_Embed_Manager",
    model=my_llm,
    instruction=SYSTEM_INSTRUCTION,
    tools=[generate_looker_embed_url],
)

class EmbedAdkApp(AdkApp):
    def register_operations(self):
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
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        msg = args[0] if args else (kwargs.get("message") or kwargs.get("prompt") or kwargs.get("question") or "")
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
        return {"response": "".join(full_text), "event": final_event}

    def stream_query(self, *args, **kwargs):
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
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        agent = self._tmpl_attrs.get("agent")
        if agent and getattr(agent, "__pydantic_private__", None) is None:
            object.__setattr__(agent, "__pydantic_private__", {})
        yield from super().streaming_agent_run_with_events(request_json)

app = EmbedAdkApp(agent=root_agent)
