import requests
import json
import time

BASE_URL = "http://127.0.0.1:8080"

test_cases = [
    {
        "id": "tc1_weekly_revenue_chart",
        "prompt": "what's the total revenue by week break down by game and show as a line chart",
        "expected_subagent": "metrics_fast"
    },
    {
        "id": "tc2_dau_trend",
        "prompt": "what is daily active users over the last 30 days",
        "expected_subagent": "metrics_fast"
    },
    {
        "id": "tc3_iap_vs_ad_country",
        "prompt": "compare total iap revenue and total ad revenue by country over the last 30 days",
        "expected_subagent": "metrics_fast"
    },
    {
        "id": "tc4_revenue_by_game_bar",
        "prompt": "show total revenue by game for the last 90 days as a bar chart",
        "expected_subagent": "metrics_fast"
    },
    {
        "id": "tc5_top_country_users",
        "prompt": "which country had the highest number of users in the last 7 days",
        "expected_subagent": "metrics_fast"
    }
]

print("=" * 70)
print("=== RUNNING METRICS ANALYST TEST SUITE ===")
print("=" * 70)

results = []

for tc in test_cases:
    session_id = f"test_metrics_sess_{tc['id']}"
    print(f"\n[TEST {tc['id']}] Prompt: \"{tc['prompt']}\"")
    t0 = time.time()
    
    resp = requests.post(
        f"{BASE_URL}/chat",
        json={
            "message": tc["prompt"],
            "session_id": session_id,
            "agent_type": "auto",
            "force_refresh": True
        },
        stream=True,
        timeout=120
    )
    
    routed_subagent = "unknown"
    has_table = False
    has_chart = False
    has_link = False
    text_chunks = []
    thoughts = []
    
    for line in resp.iter_lines():
        if not line:
            continue
        decoded = line.decode('utf-8')
        if decoded.startswith("THOUGHT: "):
            thoughts.append(decoded[9:])
        elif decoded.startswith("DATA: "):
            try:
                data_obj = json.loads(decoded[6:])
                dtype = data_obj.get("type")
                if dtype == "subagent_routed":
                    routed_subagent = data_obj.get("subagent")
                elif dtype == "json_table":
                    has_table = True
                elif dtype == "json_chart":
                    has_chart = True
                elif dtype == "json_link":
                    has_link = True
            except Exception:
                pass
        elif decoded.startswith("DATA: "):
            text_chunks.append(decoded[6:])
        elif decoded.startswith("data: "):
            content = decoded[6:]
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
    passed_routing = (routed_subagent == tc["expected_subagent"])
    status = "✅ PASS" if passed_routing else "❌ FAIL"
    
    print(f"  Result: {status} | Routed Subagent: {routed_subagent} | Elapsed: {elapsed:.2f}s")
    print(f"  Payloads: Table={has_table}, Chart/Link={has_chart or has_link}, Thoughts={len(thoughts)}")
    
    results.append({
        "id": tc["id"],
        "prompt": tc["prompt"],
        "expected": tc["expected_subagent"],
        "actual": routed_subagent,
        "elapsed": elapsed,
        "has_table": has_table,
        "passed": passed_routing
    })

print("\n" + "=" * 70)
print("=== METRICS ANALYST TEST SUITE REPORT ===")
print("=" * 70)
print(f"{'Test ID':<25} | {'Expected':<14} | {'Actual':<14} | {'Time (s)':<10} | {'Status'}")
print("-" * 70)
for r in results:
    st = "PASS" if r["passed"] else "FAIL"
    print(f"{r['id']:<25} | {r['expected']:<14} | {r['actual']:<14} | {r['elapsed']:>8.2f}s | {st}")
print("=" * 70)
