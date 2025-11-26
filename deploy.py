from vertexai.preview import reasoning_engines
import vertexai
from agent import app, PROJECT_ID, LOCATION

# Initialize Vertex AI for deployment
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket="gs://ca_api",
)

print("Deploying agent to Agent Engine...")

remote_app = reasoning_engines.ReasoningEngine.create(
    reasoning_engine=app,
    requirements=[
        "google-cloud-aiplatform[adk,agent_engines]",
        "google-cloud-geminidataanalytics",
    ],
)

print(f"Agent deployed successfully.")
print(f"Resource Name: {remote_app.resource_name}")
print(f"Operation Name: {remote_app.operation_name}")
