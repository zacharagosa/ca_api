"""
Looker SSO Embed Generator Tools for Gaming SSO Embed & Portal Manager.
"""

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
            session_length=86400,
            force_logout_login=True
        )
        iframe_snippet = f'<iframe src="{url}" width="100%" height="800px" frameborder="0"></iframe>'
        return f"✅ **Looker Signed SSO Embed URL Generated:**\n\n🔗 [Open Dashboard in New Tab]({url})\n\n**Direct Embed URL:**\n```{url}```\n\n**HTML Embed Snippet:**\n```html\n{iframe_snippet}\n```"
    except Exception as e:
        return f"Error generating Looker embed URL: {e}"
