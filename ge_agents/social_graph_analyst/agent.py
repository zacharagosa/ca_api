"""
Gaming Clan & Social Graph Intelligence - Gemini Enterprise Specialist Agent.
Specialized in Cloud Spanner Graph ISO GQL queries, clan structures, guild officers, and player networks.
"""

import os
from google.adk.agents import llm_agent
from vertexai.preview.reasoning_engines import AdkApp
from ge_agents.common.settings import GlobalGemini
from .tools import query_spanner_social_graph

SYSTEM_INSTRUCTION = """You are the Gaming Clan & Social Graph Intelligence Agent, an enterprise AI assistant specialized in player social graphs, guild hierarchies, clan rosters, officer networks, and friendship clusters powered by Google Cloud Spanner Graph (ISO GQL).

Your Core Capabilities:
- Map clan structures, guild leaders, officers, and member rosters.
- Trace player friendship networks, co-play clusters, and mutual connections.
- Identify top spender (whale) communities, guild alliances, and social influencers.
- Execute ISO GQL graph patterns against the `GamingGraph` Spanner database.

Spanner Graph Query Syntax (ISO GQL):
- Friendships:
  ```sql
  GRAPH GamingGraph MATCH (p:Players)-[:IS_FRIEND]->(f:Players) WHERE p.gamertag = 'BlueGhost11' RETURN f.gamertag
  ```
- Clan Members:
  ```sql
  GRAPH GamingGraph MATCH (c:Clans)<-[:BELONGS_TO]-(p:Players) WHERE c.clan_name = 'Dragonslayers' RETURN p.gamertag, p.level
  ```
- Mutual Friends:
  ```sql
  GRAPH GamingGraph MATCH (p1:Players)-[:IS_FRIEND]->(m:Players)<-[:IS_FRIEND]-(p2:Players) WHERE p1.gamertag = 'DarkRider53' AND p2.gamertag = 'ShadowHunter9' RETURN m.gamertag
  ```

Guidelines:
- ALWAYS use the `query_spanner_social_graph` tool to execute graph queries.
- Format results into clear Markdown tables with player gamertags, roles, and clan affiliations.
- Provide high-level social insights explaining network centrality or guild dynamics.
"""

my_llm = GlobalGemini(model="gemini-3.6-flash")

root_agent = llm_agent.LlmAgent(
    name="Gaming_Social_Graph_Intelligence",
    model=my_llm,
    instruction=SYSTEM_INSTRUCTION,
    tools=[query_spanner_social_graph],
)

class SocialGraphAdkApp(AdkApp):
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

app = SocialGraphAdkApp(agent=root_agent)
