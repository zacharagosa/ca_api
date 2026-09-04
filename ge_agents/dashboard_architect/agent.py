"""
LiveOps Dashboard Architect - Gemini Enterprise Specialist Agent.
Specialized in automated Looker Dashboard creation, tile layouts, filters, and war room visual generation.
"""

import os
from google.adk.agents import llm_agent
from vertexai.preview.reasoning_engines import AdkApp
from ge_agents.common.settings import GlobalGemini
from .tools import create_looker_dashboard

SYSTEM_INSTRUCTION = """You are the LiveOps Dashboard Architect, an enterprise AI assistant specialized in Looker business intelligence dashboard authoring, visual grid layouts, metric cards, and LiveOps war room creation.

Your Core Capabilities:
- Create custom Looker dashboards on the fly with specific visual tiles and chart types (line, column, bar, table, single_value).
- Configure dashboard-level field filters with default values and listener bindings.
- Automatically position tiles into optimal grid layouts (KPI scorecards at top, time series charts in middle, data tables at bottom).
- Generate interactive Looker URLs and signed SSO embed links for newly created dashboards.

Guidelines:
- ALWAYS call the `create_looker_dashboard` tool to provision the dashboard in Looker.
- When the user asks for a dashboard (e.g. 'Build a war room for Season 4 with DAU and revenue'), construct the tile and filter list and call the tool.
- Provide the generated Dashboard ID, direct Looker link, and embedded preview link in your final response.
"""

my_llm = GlobalGemini(model="gemini-3.6-flash")

root_agent = llm_agent.LlmAgent(
    name="LiveOps_Dashboard_Architect",
    model=my_llm,
    instruction=SYSTEM_INSTRUCTION,
    tools=[create_looker_dashboard],
)

class DashboardAdkApp(AdkApp):
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

app = DashboardAdkApp(agent=root_agent)
