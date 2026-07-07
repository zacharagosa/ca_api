
import os
from google.cloud import geminidataanalytics
from google.auth import default
from google.api_core.exceptions import PermissionDenied, ServiceUnavailable

# Force the project ID as per agent.py logic
PROJECT_ID = "1094200614711"
LOCATION = "global"
# We need valid Looker credentials for a real request
LOOKER_INSTANCE_URI = os.getenv("LOOKER_INSTANCE_URI", "https://3417a175-fe20-4370-974f-2f2b535340ab.looker.app")
LOOKER_CLIENT_ID = os.getenv("LOOKER_CLIENT_ID_EVENTS", "9cR2K4JdGYjZCBCm6HGs")
LOOKER_CLIENT_SECRET = os.getenv("LOOKER_CLIENT_SECRET_EVENTS", "8YP9CWFVhdzxF2dvPsyJhQdR")
LOOKML_MODEL = "gaming"
EXPLORE = "events"

def test_connectivity():
    print(f"Testing connectivity for Project: {PROJECT_ID}, Location: {LOCATION}")
    try:
        creds, project = default()
        print(f"Credentials detected for project: {project}")
        print(f"Service Account/User Email: {getattr(creds, 'service_account_email', 'User Credentials')}")
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return

    client = geminidataanalytics.DataChatServiceClient(credentials=creds)
    
    # Create valid credentials object
    credentials = geminidataanalytics.Credentials(
        oauth=geminidataanalytics.OAuthCredentials(
            secret=geminidataanalytics.OAuthCredentials.SecretBased(
                client_id=LOOKER_CLIENT_ID, client_secret=LOOKER_CLIENT_SECRET
            ),
        )
    )

    looker_explore_reference = geminidataanalytics.LookerExploreReference(
        looker_instance_uri=LOOKER_INSTANCE_URI, lookml_model=LOOKML_MODEL, explore=EXPLORE
    )

    has_looker_credentials = 'credentials' in geminidataanalytics.LookerExploreReferences.pb().DESCRIPTOR.fields_by_name
    if has_looker_credentials:
        looker_refs = geminidataanalytics.LookerExploreReferences(
            explore_references=[looker_explore_reference],
            credentials=credentials
        )
    else:
        looker_refs = geminidataanalytics.LookerExploreReferences(
            explore_references=[looker_explore_reference]
        )
        
    datasource_references = geminidataanalytics.DatasourceReferences(
        looker=looker_refs,
    )
    
    inline_context = geminidataanalytics.Context(
        datasource_references=datasource_references
    )

    try:
        messages = [geminidataanalytics.Message()]
        messages[0].user_message.text = "Hello"
        
        chat_kwargs = {
            'inline_context': inline_context,
            'parent': f"projects/{PROJECT_ID}/locations/{LOCATION}",
            'messages': messages,
        }
        if 'credentials' in geminidataanalytics.ChatRequest.pb().DESCRIPTOR.fields_by_name:
            chat_kwargs['credentials'] = credentials
            
        request = geminidataanalytics.ChatRequest(**chat_kwargs)
        print("Sending Valid ChatRequest...")
        response = client.chat(request=request)
        print("Success! Response received.")
        for item in response:
             print(f"Item: {item}")
        
    except PermissionDenied as e:
        print(f"FAILED: 403 Permission Denied. \n{e}")
        
    except Exception as e:
        print(f"FAILED: Error: {e}")

if __name__ == "__main__":
    test_connectivity()
