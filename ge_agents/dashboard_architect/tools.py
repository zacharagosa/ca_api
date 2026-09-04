"""
Looker Dashboard Authoring Tools for LiveOps Dashboard Architect.
"""

import os
from looker_sdk import init40, api_settings

LOOKER_INSTANCE_URI = os.getenv("LOOKER_INSTANCE_URI", "https://3417a175-fe20-4370-974f-2f2b535340ab.looker.app")
LOOKER_CLIENT_ID = os.getenv("LOOKER_CLIENT_ID", "DgcB4DCwGPbrczp4cmcN")
LOOKER_CLIENT_SECRET = os.getenv("LOOKER_CLIENT_SECRET", "5dzbFDwdZ4Cd7n8V44XcbYGN")

# Ensure environment variables are populated for all Looker SDK callers
os.environ["LOOKERSDK_BASE_URL"] = os.getenv("LOOKERSDK_BASE_URL") or LOOKER_INSTANCE_URI
os.environ["LOOKERSDK_CLIENT_ID"] = os.getenv("LOOKERSDK_CLIENT_ID") or LOOKER_CLIENT_ID
os.environ["LOOKERSDK_CLIENT_SECRET"] = os.getenv("LOOKERSDK_CLIENT_SECRET") or LOOKER_CLIENT_SECRET
os.environ["LOOKER_INSTANCE_URI"] = LOOKER_INSTANCE_URI
os.environ["LOOKER_CLIENT_ID"] = LOOKER_CLIENT_ID
os.environ["LOOKER_CLIENT_SECRET"] = LOOKER_CLIENT_SECRET

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
