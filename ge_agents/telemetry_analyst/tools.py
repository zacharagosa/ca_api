"""
Looker Telemetry Tools for Gaming Telemetry Analyst.
"""

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
