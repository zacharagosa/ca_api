from google.adk.agents import Agent
from vertexai.preview import reasoning_engines
import vertexai

PROJECT_ID = "aragosalooker"
LOCATION = "us-central1"

def echo(text: str):
    """Echoes the input text."""
    return text

agent = Agent(
    model="gemini-1.5-flash-001",
    name="EchoAgent",
    instruction="You are an echo agent.",
    tools=[echo],
)

# vertexai.init moved to deploy script

app = reasoning_engines.AdkApp(
    agent=agent,
    enable_tracing=False,
)
