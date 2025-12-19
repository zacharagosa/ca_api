from vertexai.preview import reasoning_engines
from agent import app, PROJECT_ID, LOCATION

# Vertex AI is initialized in agent.py

print("Deploying agent to Agent Engine...")

remote_app = reasoning_engines.ReasoningEngine.create(
    reasoning_engine=app,
    requirements=[
        "google-cloud-aiplatform>=1.38.0",
        "google-adk",
        "google-cloud-geminidataanalytics",
    ],
    extra_packages=[
        "./agent.py",
    ],
    display_name="CA_API",
)

print(f"Agent deployed successfully.")
print(f"Resource Name: {remote_app.resource_name}")
print(f"Operation Name: {remote_app.operation_name}")
