"""
Authentication Token Manager for Google Cloud and Looker APIs.
"""

from google.auth import default
from google.auth.transport.requests import Request as gRequest

class AuthTokenManager:
    def __init__(self):
        self._credentials = None
        self.SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

    def get_credentials(self):
        if self._credentials is None:
            self._credentials, _ = default(scopes=self.SCOPES)
        
        try:
            if not self._credentials.valid:
                self._credentials.refresh(gRequest())
        except Exception as e:
            self._credentials, _ = default(scopes=self.SCOPES)
            if not self._credentials.valid:
                self._credentials.refresh(gRequest())
              
        return self._credentials

    def get_auth_token(self) -> str:
        return self.get_credentials().token

auth_manager = AuthTokenManager()
