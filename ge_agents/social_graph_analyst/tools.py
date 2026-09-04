"""
Spanner Graph Query Tools for Gaming Clan & Social Graph Intelligence.
"""

import os
from google.cloud import spanner

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "aragosalooker")
SPANNER_INSTANCE = os.getenv("SPANNER_INSTANCE_ID", "gaming-instance")
SPANNER_DATABASE = os.getenv("SPANNER_DATABASE_ID", "gaming-graph")

_spanner_client = None

def _get_spanner_db():
    global _spanner_client
    if _spanner_client is None:
        _spanner_client = spanner.Client(project=GCP_PROJECT_ID)
    instance = _spanner_client.instance(SPANNER_INSTANCE)
    return instance.database(SPANNER_DATABASE)

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
