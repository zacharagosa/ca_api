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
        (Legacy method - use cookieless methods for new implementations)
        """
        import agent
        
        body = models40.EmbedSsoParams(
            target_url=target_url,
            session_length=3600,
            force_logout_login=True,
            external_user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            permissions=["access_data", "see_looks", "see_user_dashboards", "see_lookml_dashboards", "explore"],
            models=[agent.LOOKML_MODEL],
            group_ids=[],
            external_group_id="",
            user_attributes={"locale": "en_US"}
        )

        try:
            response = self.sdk.create_sso_embed_url(body=body)
            return response.url
        except Exception as e:
            print(f"SDK Embed Error: {e}")
            if "RemoteDisconnected" in str(e) or "Connection refused" in str(e):
                print("HINT: check if LOOKERSDK_BASE_URL needs port 19999 or /api/4.0 suffix.")
            raise e

    def acquire_cookieless_session(self, user_id, first_name="Guest", last_name="User", 
                                    session_reference_token=None, embed_domain=None):
        """
        Acquire a cookieless embed session for an embed user.
        
        This creates an embed user on-the-fly without requiring an internal Looker license.
        Returns tokens needed to initialize the embed iframe.
        
        Args:
            user_id: Unique identifier for the embed user (e.g., email)
            first_name: User's first name
            last_name: User's last name
            session_reference_token: Optional existing session token to rejoin
            embed_domain: Optional embed domain (required if not in Looker allowlist)
        
        Returns:
            dict with authentication_token, navigation_token, api_token, and TTLs
        """
        try:
            # Build the embed user definition
            embed_user = {
                "external_user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "permissions": [
                    "access_data",
                    "see_looks", 
                    "see_user_dashboards",
                    "see_lookml_dashboards",
                    "explore"
                ],
                "models": [self.lookml_model],
                "group_ids": [],
                "user_attributes": {"locale": "en_US"}
            }
            
            # Add session reference token if rejoining existing session
            if session_reference_token:
                embed_user["session_reference_token"] = session_reference_token
            
            # Add embed domain if provided (for dynamic domain registration)
            if embed_domain:
                embed_user["embed_domain"] = embed_domain
            
            # Call the Looker API to acquire cookieless session
            response = self.sdk.acquire_embed_cookieless_session(body=embed_user)
            
            return {
                "authentication_token": response.authentication_token,
                "authentication_token_ttl": response.authentication_token_ttl,
                "navigation_token": response.navigation_token,
                "navigation_token_ttl": response.navigation_token_ttl,
                "api_token": response.api_token,
                "api_token_ttl": response.api_token_ttl,
                "session_reference_token": response.session_reference_token,
                "session_reference_token_ttl": response.session_reference_token_ttl,
            }
            
        except Exception as e:
            print(f"Cookieless Session Error: {e}")
            raise e

    def generate_embed_tokens(self, session_reference_token, api_token=None, navigation_token=None):
        """
        Generate new tokens for an existing cookieless embed session.
        
        Called periodically by the embed SDK to refresh tokens before they expire.
        
        Args:
            session_reference_token: The session reference token from acquire_cookieless_session
            api_token: Current API token (optional)
            navigation_token: Current navigation token (optional)
        
        Returns:
            dict with refreshed tokens and TTLs
        """
        if not session_reference_token:
            # Session expired
            return {"session_reference_token_ttl": 0}
        
        try:
            response = self.sdk.generate_tokens_for_cookieless_session(body={
                "session_reference_token": session_reference_token,
                "api_token": api_token or "",
                "navigation_token": navigation_token or ""
            })
            
            return {
                "api_token": response.api_token,
                "api_token_ttl": response.api_token_ttl,
                "navigation_token": response.navigation_token,
                "navigation_token_ttl": response.navigation_token_ttl,
                "session_reference_token_ttl": response.session_reference_token_ttl,
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"Token Generation Error: {e}")
            
            # Handle invalid tokens by expiring session
            if "Invalid input tokens" in error_msg:
                return {"session_reference_token_ttl": 0}
            
            raise e

