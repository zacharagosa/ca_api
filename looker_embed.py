import looker_sdk
import os
import urllib.parse
from looker_sdk import models40

class LookerEmbedManager:
    def __init__(self):
        # Import agent config - this has the dataset-specific Looker settings
        import agent
        
        # Set SDK env vars from agent config (loaded from dataset YAML)
        looker_uri = agent.LOOKER_INSTANCE_URI
        client_id = agent.LOOKER_CLIENT_ID
        client_secret = agent.LOOKER_CLIENT_SECRET
        
        if looker_uri:
            os.environ["LOOKERSDK_BASE_URL"] = looker_uri
        if client_id:
            os.environ["LOOKERSDK_CLIENT_ID"] = client_id
        if client_secret:
            os.environ["LOOKERSDK_CLIENT_SECRET"] = client_secret
             
        # Log config (masking secret)
        print(f"Looker SDK Init: Base URL={os.getenv('LOOKERSDK_BASE_URL')}, ID={os.getenv('LOOKERSDK_CLIENT_ID')}")
        
        # Store the model for embed user permissions
        self.lookml_model = agent.LOOKML_MODEL
        self.looker_uri = looker_uri
             
        self.sdk = looker_sdk.init40()

    def generate_signed_url(self, target_url, user_id, first_name="Gaming", last_name="Analyst"):
        """
        Uses the Looker API to generate a Signed Embed URL.
        """
        import agent
        
        print(f"=== Generating SSO Embed URL ===")
        print(f"  Target URL: {target_url}")
        print(f"  User ID: {user_id}")
        print(f"  Name: {first_name} {last_name}")
        print(f"  LookML Model: {agent.LOOKML_MODEL}")
        print(f"  Looker Instance: {self.looker_uri}")
        
        # Force Looker theme if not already present
        if "theme=" not in target_url:
            separator = "&" if "?" in target_url else "?"
            target_url = f"{target_url}{separator}theme=Looker"
            print(f"  Updated Target URL with Theme: {target_url}")
        
        body = models40.EmbedSsoParams(
            target_url=target_url,
            session_length=3600,
            force_logout_login=True,
            external_user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            permissions=["access_data", "see_looks", "see_user_dashboards", "see_lookml_dashboards", "explore"],
            models=list(set([agent.LOOKML_MODEL, "gaming", "snowplow"])),
            group_ids=[],
            external_group_id="",
            user_attributes={"locale": "en_US"}
        )
        
        print(f"  Permissions: {body.permissions}")
        print(f"  Models: {body.models}")

        try:
            response = self.sdk.create_sso_embed_url(body=body)
            print(f"  ✅ Generated URL successfully (length: {len(response.url)})")
            print(f"  URL Preview: {response.url[:150]}...")
            return response.url
        except Exception as e:
            print(f"  ❌ SDK Embed Error: {e}")
            if "RemoteDisconnected" in str(e) or "Connection refused" in str(e):
                print("  HINT: check if LOOKERSDK_BASE_URL needs port 19999 or /api/4.0 suffix.")
            if "not enabled" in str(e).lower() or "sso" in str(e).lower():
                print("  HINT: Embed SSO Authentication must be enabled in Looker Admin > Platform > Embed")
            raise e
