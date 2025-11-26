from agent import app
import inspect

print("Signature of streaming_agent_run_with_events:")
print(inspect.signature(app.streaming_agent_run_with_events))
