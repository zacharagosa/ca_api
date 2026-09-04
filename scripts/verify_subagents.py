import requests
import json
import time

BASE_URL = "http://127.0.0.1:8080"

test_prompts = [
    ("METRICS_FAST", "What was total revenue by game over the last 30 days?"),
    ("SOCIAL_GRAPH", "Who are the members of the DragonSlayers clan?"),
    ("DASHBOARD_BUILDER", "Build a new LiveOps War Room dashboard with DAU and Total Revenue tiles.")
]

session_id = "test_subagent_sess_1"

for cat, prompt in test_prompts:
    print(f"\n==================== TEST [{cat}]: {prompt} ====================")
    t0 = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/chat",
            json={"message": prompt, "session_id": session_id, "agent_type": "auto", "force_refresh": True},
            stream=True,
            timeout=120
        )
        print(f"Status Code: {resp.status_code}")
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode('utf-8')
            if decoded.startswith("THOUGHT:"):
                print(f"  [THOUGHT] {decoded[9:120]}")
            elif decoded.startswith("DATA:"):
                data_str = decoded[6:]
                try:
                    d = json.loads(data_str)
                    print(f"  [DATA EVENT] Type: {d.get('type')}, Subagent: {d.get('subagent') or d.get('name')}")
                except Exception:
                    print(f"  [DATA CHUNK] {data_str[:120]}")
        print(f"Finished in {time.time() - t0:.2f}s")
    except Exception as e:
        print(f"Error: {e}")
