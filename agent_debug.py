from google.cloud import geminidataanalytics
from google.adk.agents import Agent
from vertexai.preview import reasoning_engines
import vertexai

def echo(text: str):
    return text

agent = Agent(
    model="gemini-2.5-flash-lite",
    name="DebugAgent",
    instruction="Debug agent",
    tools=[echo],
)

app = reasoning_engines.AdkApp(
    agent=agent,
    enable_tracing=True,
)
