"""
Pure ADK Agent Tools for Looker Telemetry, Spanner Graph, and LiveOps Dashboards.
"""

import os
import json
import yaml
from google.cloud import spanner
from looker_sdk import init40, api_settings, models40

PROJECT_ID = os.getenv("PROJECT_ID", "1094200614711")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "aragosalooker")
LOOKER_INSTANCE_URI = os.getenv("LOOKER_INSTANCE_URI", "https://3417a175-fe20-4370-974f-2f2b535340ab.looker.app")
LOOKER_CLIENT_ID = os.getenv("LOOKER_CLIENT_ID", "DgcB4DCwGPbrczp4cmcN")
LOOKER_CLIENT_SECRET = os.getenv("LOOKER_CLIENT_SECRET", "5dzbFDwdZ4Cd7n8V44XcbYGN")
SPANNER_INSTANCE = os.getenv("SPANNER_INSTANCE_ID", "gaming-instance")
SPANNER_DATABASE = os.getenv("SPANNER_DATABASE_ID", "gaming-graph")

# Ensure environment variables are populated for all Looker SDK callers
os.environ["LOOKERSDK_BASE_URL"] = os.getenv("LOOKERSDK_BASE_URL") or LOOKER_INSTANCE_URI
os.environ["LOOKERSDK_CLIENT_ID"] = os.getenv("LOOKERSDK_CLIENT_ID") or LOOKER_CLIENT_ID
os.environ["LOOKERSDK_CLIENT_SECRET"] = os.getenv("LOOKERSDK_CLIENT_SECRET") or LOOKER_CLIENT_SECRET
os.environ["LOOKER_INSTANCE_URI"] = LOOKER_INSTANCE_URI
os.environ["LOOKER_CLIENT_ID"] = LOOKER_CLIENT_ID
os.environ["LOOKER_CLIENT_SECRET"] = LOOKER_CLIENT_SECRET

_spanner_client = None
_looker_sdk_client = None

class LookerCustomSettings(api_settings.ApiSettings):
    """Custom settings provider for Looker SDK with automatic fallbacks."""
    def read_config(self):
        return {
            'base_url': os.getenv('LOOKERSDK_BASE_URL') or os.getenv('LOOKER_INSTANCE_URI') or LOOKER_INSTANCE_URI,
            'client_id': os.getenv('LOOKERSDK_CLIENT_ID') or os.getenv('LOOKER_CLIENT_ID') or LOOKER_CLIENT_ID,
            'client_secret': os.getenv('LOOKERSDK_CLIENT_SECRET') or os.getenv('LOOKER_CLIENT_SECRET') or LOOKER_CLIENT_SECRET,
            'verify_ssl': 'true'
        }

def _get_spanner_db():
    global _spanner_client
    if _spanner_client is None:
        _spanner_client = spanner.Client(project=GCP_PROJECT_ID)
    instance = _spanner_client.instance(SPANNER_INSTANCE)
    return instance.database(SPANNER_DATABASE)

def _get_looker_sdk():
    global _looker_sdk_client
    if _looker_sdk_client is None:
        _looker_sdk_client = init40(config_settings=LookerCustomSettings())
    return _looker_sdk_client


def query_looker_telemetry(question: str) -> str:
    """Queries Looker quantitative telemetry metrics (DAU, revenue, retention, ARPU, sessions, daily trends).

    Args:
        question: The natural language question about gaming metrics (e.g. 'What was total revenue yesterday by game?', 'Show 30 day DAU trend').

    Returns:
        A Markdown-formatted summary containing quantitative data rows, formatted markdown tables, and a Looker Explore drill-down URL.
    """
    try:
        import agent
        chunks = list(agent.fast_query(question))
        
        text_parts = []
        explore_url = ""
        table_rendered = False
        
        for c in chunks:
            c_type = c.get("type")
            if c_type == "text":
                text_parts.append(c.get("content", ""))
            elif c_type == "data":
                content = c.get("content", {})
                rows = content.get("rows", [])
                schema = content.get("schema", {})
                fields = [
                    f.get("display_name") or f.get("name", "").split(".")[-1]
                    for f in schema.get("fields", [])
                ]
                if rows and fields and not table_rendered:
                    header = "| " + " | ".join(fields) + " |\n| " + " | ".join(["---"] * len(fields)) + " |\n"
                    table_lines = []
                    for r in rows[:30]:
                        vals = []
                        for f in fields:
                            v = r.get(f)
                            if v is None:
                                for k, item_val in r.items():
                                    if k.lower().endswith(f.lower()) or f.lower().endswith(k.lower()):
                                        v = item_val
                                        break
                            vals.append(str(v if v is not None else ""))
                        table_lines.append("| " + " | ".join(vals) + " |")
                    text_parts.append(header + "\n".join(table_lines))
                    table_rendered = True
                if content.get("explore_url"):
                    explore_url = content.get("explore_url")
                    
        if explore_url:
            text_parts.append(f"[📊 Open in Looker Explore]({explore_url})")

        return "\n\n".join(text_parts).strip() or f"Retrieved telemetry metrics for question: {question}"

    except Exception as e:
        return f"Error executing Looker telemetry query: {e}"


def query_spanner_social_graph(gql_query: str) -> str:
    """Executes an ISO GQL graph query against Google Cloud Spanner to analyze player social graphs, clans, officers, and friendships.

    Args:
        gql_query: The Spanner GQL query to execute (e.g. 'GRAPH GamingGraph MATCH (p:Players)-[:IS_FRIEND]->(f:Players) WHERE p.gamertag = \"BlueGhost11\" RETURN f.gamertag').

    Returns:
        A Markdown formatted table containing the graph query results.
    """
    try:
        db = _get_spanner_db()
        with db.snapshot() as snapshot:
            results = snapshot.execute_sql(gql_query)
            data = [list(row) for row in results]
            fields = [field.name for field in results.fields]

        if not data:
            return f"Query executed successfully, but no matching graph records were found.\n\nGQL Query: `{gql_query}`"

        header = "| " + " | ".join(fields) + " |\n| " + " | ".join(["---"] * len(fields)) + " |\n"
        rows = ["| " + " | ".join(str(val) for val in row) + " |" for row in data[:30]]
        table = header + "\n".join(rows)

        return f"**Spanner Graph Results ({len(data)} rows):**\n\n{table}\n\n```sql\n{gql_query}\n```"

    except Exception as e:
        return f"Spanner Graph Query Error: {e}\nQuery attempted: `{gql_query}`"


def create_looker_dashboard(title: str, tiles: list[dict] = None, filters: list[dict] = None, description: str = "") -> str:
    """Creates a new custom Looker LiveOps war room dashboard on the fly with specified visual tiles, metrics, and filters.

    Args:
        title: The title of the dashboard (e.g. 'Season 4 LiveOps War Room', '30-Day DAU & Revenue Executive Dashboard').
        tiles: Optional list of tile definitions. Each tile is a dict with 'title' (string), 'type' (string: 'line', 'column', 'table', or 'single_value'), and 'fields' (list of dimension/measure names like ['events.event_date', 'events.number_of_users']).
        filters: Optional list of dashboard-level filter definitions (e.g. [{'name': 'Date Range', 'field': 'events.event_date', 'default_value': '30 days'}]).
        description: Optional short description for the dashboard.

    Returns:
        A formatted confirmation containing the newly created Dashboard ID, Looker web URL, and signed SSO embed URL.
    """
    try:
        import agent
        res = agent.create_looker_dashboard(
            title=title,
            description=description,
            tiles=tiles,
            filters=filters
        )
        if isinstance(res, dict):
            dash_id = res.get("dashboard_id") or res.get("id")
            dash_url = res.get("dashboard_url") or res.get("url") or f"{LOOKER_INSTANCE_URI}/dashboards/{dash_id}"
            embed_url = res.get("embed_url")
            out = [f"✅ Successfully created Looker LiveOps Dashboard **'{title}'**!"]
            if dash_id:
                out.append(f"- **Dashboard ID:** `{dash_id}`")
            if dash_url:
                out.append(f"- **Looker URL:** [{dash_url}]({dash_url})")
            if embed_url:
                out.append(f"- **Signed Embed Preview:** [Open Live Embed]({embed_url})")
            return "\n\n".join(out)
        return str(res)
    except Exception as e:
        return f"Error creating Looker dashboard: {e}"


def generate_looker_embed_url(dashboard_id: str = "124") -> str:
    """Generates a signed, single-sign-on (SSO) embed URL for embedding Looker dashboards into web portals and war rooms.

    Args:
        dashboard_id: The ID of the dashboard to embed.

    Returns:
        The signed embed URL for embedding in an iframe.
    """
    try:
        from looker_embed import LookerEmbedManager
        mgr = LookerEmbedManager()
        url = mgr.generate_embed_url(
            target_path=f"/embed/dashboards/{dashboard_id}",
            session_length=3600,
            force_logout_login=True
        )
        return f"**Looker Signed Embed URL:**\n{url}"
    except Exception as e:
        return f"Error generating Looker embed URL: {e}"
