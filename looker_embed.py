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
        
        base_uri = (
            self.looker_uri 
            or os.getenv("LOOKER_INSTANCE_URI") 
            or os.getenv("LOOKERSDK_BASE_URL") 
            or getattr(agent, "LOOKER_INSTANCE_URI", "") 
            or "https://3417a175-fe20-4370-974f-2f2b535340ab.looker.app"
        ).rstrip('/')
        
        # Clean & normalize path
        if not target_url or target_url == "embedded_explore":
            path = f"/embed/explore/{agent.LOOKML_MODEL or 'gaming'}/{agent.EXPLORE or 'events'}"
        elif "/login/embed/" in target_url:
            parsed = urllib.parse.urlparse(target_url)
            path = parsed.path.replace("/login/embed", "")
            if parsed.query:
                # Retain non-auth query params
                query_params = urllib.parse.parse_qs(parsed.query)
                clean_query = {k: v for k, v in query_params.items() if k not in ['signature', 'nonce', 'time', 'session_length', 'external_user_id', 'permissions', 'models']}
                if clean_query:
                    path = f"{path}?{urllib.parse.urlencode(clean_query, doseq=True)}"
        elif target_url.startswith("http"):
            parsed = urllib.parse.urlparse(target_url)
            path = parsed.path
            if parsed.query:
                path = f"{path}?{parsed.query}"
        elif not target_url.startswith("/"):
            if target_url.isdigit() or target_url.startswith("custom_"):
                dash_id = target_url.replace("custom_", "")
                path = f"/embed/dashboards/{dash_id}"
            else:
                path = f"/{target_url}"
        else:
            path = target_url
        
        full_target_url = f"{base_uri}{path}"
        
        # Force Looker theme if not already present
        if "theme=" not in full_target_url:
            separator = "&" if "?" in full_target_url else "?"
            full_target_url = f"{full_target_url}{separator}theme=Looker"
        
        print(f"=== Generating SSO Embed URL ===")
        print(f"  Full Target URL: {full_target_url}")
        print(f"  User ID: {user_id}")
        print(f"  Name: {first_name} {last_name}")
        
        # Dynamically grant access to all available models on instance
        try:
            available_models = [m.name for m in self.sdk.all_lookml_models() if m.name]
        except Exception:
            available_models = [agent.LOOKML_MODEL or "gaming", "thelook", "ga4", "panera_digital_analytics"]
            
        permissions = [
            "access_data",
            "see_looks",
            "see_user_dashboards",
            "see_lookml_dashboards",
            "explore",
            "save_content",
            "embed_save_shared_space",
            "embed_browse_spaces",
            "see_drill_overlay",
            "schedule_look_emails",
            "download_without_limit"
        ]
        
        body = models40.EmbedSsoParams(
            target_url=full_target_url,
            session_length=86400,
            force_logout_login=True,
            external_user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            permissions=permissions,
            models=available_models,
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
            raise e
