import looker_sdk
import os
import urllib.parse
from looker_sdk import models40

class LookerEmbedManager:
    def __init__(self):
        # Configure the SDK using existing environment variables or defaults
        # The SDK looks for LOOKERSDK_BASE_URL, LOOKERSDK_CLIENT_ID, LOOKERSDK_CLIENT_SECRET
        # We might need to map our vars if they differ
        
        # Mapping standard env vars to SDK expected env vars if not already set
        if not os.getenv("LOOKERSDK_BASE_URL") and os.getenv("LOOKER_INSTANCE_URI"):
            uri = os.getenv("LOOKER_INSTANCE_URI")
            # Heuristic: If valid URL and no port/api path, warn or try to adjust?
            # For now, just set it and log.
            os.environ["LOOKERSDK_BASE_URL"] = uri
            print(f"LookerEmbedManager: Defaulting LOOKERSDK_BASE_URL to {uri}")
            
        if not os.getenv("LOOKERSDK_CLIENT_ID") and os.getenv("LOOKER_CLIENT_ID"):
            os.environ["LOOKERSDK_CLIENT_ID"] = os.getenv("LOOKER_CLIENT_ID")
        if not os.getenv("LOOKERSDK_CLIENT_SECRET") and os.getenv("LOOKER_CLIENT_SECRET"):
             os.environ["LOOKERSDK_CLIENT_SECRET"] = os.getenv("LOOKER_CLIENT_SECRET")
             
        # Log config (masking secret)
        print(f"Looker SDK Init: Base URL={os.getenv('LOOKERSDK_BASE_URL')}, ID={os.getenv('LOOKERSDK_CLIENT_ID')}")
             
        self.sdk = looker_sdk.init40()

    def generate_signed_url(self, target_url, user_id, first_name="Gaming", last_name="Analyst"):
        """
        Uses the Looker API to generate a Signed Embed URL.
        """
        # Ensure target_url is fully qualified if possible, though SDK might handle relative if base is clean.
        # But create_sso_embed_url typically wants the full Embed URI.
        
        body = models40.EmbedSsoParams(
            target_url=target_url,
            session_length=3600,
            force_logout_login=True,
            external_user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            permissions=["access_data", "see_looks", "see_user_dashboards", "see_lookml_dashboards", "explore"],
            models=[os.getenv("LOOKML_MODEL", "gaming")],
            group_ids=[],
            external_group_id="",
            user_attributes={"locale": "en_US"}
        )

        try:
            response = self.sdk.create_sso_embed_url(body=body)
            return response.url
        except Exception as e:
            print(f"SDK Embed Error: {e}")
            # Detect common misconfig
            if "RemoteDisconnected" in str(e) or "Connection refused" in str(e):
                print("HINT: check if LOOKERSDK_BASE_URL needs port 19999 or /api/4.0 suffix.")
            raise e
