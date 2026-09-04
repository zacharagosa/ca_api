import requests
import json
import time
import uuid

BASE_URL = "http://127.0.0.1:8080"

BENCHMARK_PROMPTS = [
    {
        "category": "METRICS_FAST",
        "id": "metrics_1",
        "prompt": "What was total revenue by game over the last 30 days?",
        "expected_domain": "Looker Metrics (events.total_revenue, events.game_name)"
    },
    {
        "category": "METRICS_FAST",
        "id": "metrics_2",
        "prompt": "Show daily active users trend over the last 7 days.",
        "expected_domain": "Looker Metrics (events.number_of_users, events.event_date)"
    },
    {
        "category": "SOCIAL_GRAPH",
        "id": "social_1",
        "prompt": "Who are the members of the DragonSlayers clan?",
        "expected_domain": "Spanner Graph (Clan, Players, Memberships)"
    },
    {
        "category": "SOCIAL_GRAPH",
        "id": "social_2",
        "prompt": "Show the friendship network and connections for player DragonSlayer_Ace.",
        "expected_domain": "Spanner Graph (Friendships, Graph Visualization)"
    },
    {
        "category": "DASHBOARD_BUILDER",
        "id": "dash_1",
        "prompt": "Build a new LiveOps War Room dashboard with DAU and Total Revenue tiles.",
        "expected_domain": "Looker MCP (create_looker_dashboard, Dashboard ID)"
    },
    {
        "category": "DASHBOARD_BUILDER",
        "id": "dash_2",
        "prompt": "Add a Country filter and a single-value KPI for Total IAP Revenue to this dashboard.",
        "expected_domain": "Looker MCP (edit_looker_dashboard, ResultMakerFilterables)"
    },
    {
        "category": "DEEP_RESEARCH",
        "id": "deep_1",
        "prompt": "Analyze the relationship between top spending whales, their clan memberships, and overall revenue trends.",
        "expected_domain": "Multi-Hop Reasoning (Looker Metrics + Spanner Graph)"
    }
]

def run_prompt(prompt_info, session_id):
    url = f"{BASE_URL}/chat"
    payload = {
        "message": prompt_info["prompt"],
        "session_id": session_id,
        "user_id": "routing_benchmark_user",
        "agent_type": "auto",
        "force_refresh": True
    }
    
    t0 = time.time()
    resp = requests.post(url, json=payload, stream=True, timeout=120)
    
    thoughts = []
    text_chunks = []
    side_events = []
    routed_subagent = "unknown"
    
    for line in resp.iter_lines():
        if not line:
            continue
        decoded = line.decode('utf-8')
        if decoded.startswith("THOUGHT: "):
            thoughts.append(decoded[len("THOUGHT: "):])
        elif decoded.startswith("DATA: "):
            try:
                data_obj = json.loads(decoded[len("DATA: "):])
                side_events.append(data_obj)
                if data_obj.get("type") == "subagent_routed":
                    routed_subagent = data_obj.get("subagent") or data_obj.get("name")
            except Exception:
                pass
        elif decoded.startswith("data: "):
            content = decoded[len("data: "):]
            try:
                chunk_obj = json.loads(content)
                if isinstance(chunk_obj, dict):
                    if "text" in chunk_obj:
                        text_chunks.append(chunk_obj["text"])
                    elif "content" in chunk_obj and "parts" in chunk_obj["content"]:
                        for p in chunk_obj["content"]["parts"]:
                            if "text" in p:
                                text_chunks.append(p["text"])
            except Exception:
                text_chunks.append(content)

    elapsed = time.time() - t0
    final_text = "".join(text_chunks).strip()
    
    return {
        "prompt_id": prompt_info["id"],
        "category": prompt_info["category"],
        "prompt": prompt_info["prompt"],
        "elapsed": elapsed,
        "routed_subagent": routed_subagent,
        "thoughts": thoughts,
        "side_events": side_events,
        "final_text_sample": final_text[:300]
    }

def run_benchmark():
    session_id = f"bench_sess_{uuid.uuid4().hex[:8]}"
    print(f"=== RUNNING AUTONOMOUS SUBAGENT BENCHMARK (Session: {session_id}) ===")
    
    results = []
    for item in BENCHMARK_PROMPTS:
        print(f"\nRunning [{item['category']}] '{item['prompt']}'...")
        res = run_prompt(item, session_id)
        print(f"  -> Routed: {res['routed_subagent']} | Elapsed: {res['elapsed']:.2f}s | Thoughts: {len(res['thoughts'])} | Side Events: {len(res['side_events'])}")
        results.append(res)
        time.sleep(1)
        
    print("\n\n================ BENCHMARK REPORT ================")
    for r in results:
        print(f"[{r['category']}] {r['prompt_id']}: Routed: {r['routed_subagent']:<18} | {r['elapsed']:.2f}s | Events: {len(r['side_events'])} | Thoughts: {len(r['thoughts'])}")
    print("==================================================")
    
    # Save after results to file
    with open("scripts/benchmark_after.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved benchmark results to scripts/benchmark_after.json")

    # If baseline exists, print SxS comparison
    try:
        with open("scripts/benchmark_baseline.json", "r") as f:
            baseline = json.load(f)
        base_map = {b["prompt_id"]: b for b in baseline}
        
        print("\n\n=============== BEFORE vs AFTER SxS COMPARISON ===============")
        print(f"{'Prompt ID':<12} | {'Category':<18} | {'Baseline (s)':<12} | {'Subagent (s)':<12} | {'Delta':<10} | {'Subagent Routed'}")
        print("-" * 88)
        for r in results:
            pid = r["prompt_id"]
            base = base_map.get(pid, {})
            b_time = base.get("elapsed", 0.0)
            a_time = r["elapsed"]
            diff = a_time - b_time
            sign = "+" if diff > 0 else ""
            print(f"{pid:<12} | {r['category']:<18} | {b_time:>10.2f}s | {a_time:>10.2f}s | {sign}{diff:>7.2f}s | {r['routed_subagent']}")
        print("==============================================================")
    except Exception as e:
        print(f"Could not compute SxS comparison: {e}")

if __name__ == "__main__":
    run_benchmark()
