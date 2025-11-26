from vertexai.preview import reasoning_engines
import vertexai
from agent_debug import app

PROJECT_ID = "aragosalooker"
LOCATION = "us-central1"

# Initialize Vertex AI for deployment
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket="gs://ca_api",
)

print("Deploying debug agent to Agent Engine...")

remote_app = reasoning_engines.ReasoningEngine.create(
    reasoning_engine=app,
    requirements=[
        "google-cloud-aiplatform[adk,agent_engines]",
        "google-cloud-geminidataanalytics",
        "google-auth",
    ],
)

print(f"Agent deployed successfully.")
print(f"Resource Name: {remote_app.resource_name}")
