import requests
import json
import time
import uuid

BASE_URL = "http://127.0.0.1:8080"

dialogues = [
    {
        "name": "MetricsAnalyst Multi-Turn Follow-up Suite",
        "turns": [
            {
                "turn": 1,
                "prompt": "What was total revenue by game over last 30d?",
                "expected_subagent": "metrics_fast",
                "must_contain": ["Lookerwood Farm", "Lookup Battle Royale"]
            },
            {
                "turn": 2,
                "prompt": "Events Number of Users - what was that for the same games over that period?",
                "expected_subagent": "metrics_fast",
                "must_contain": ["users", "Lookerwood Farm", "Lookup Battle Royale"]
            },
            {
                "turn": 3,
                "prompt": "Break it down by country as well",
                "expected_subagent": "metrics_fast",
                "must_contain": ["country"]
            },
            {
                "turn": 4,
                "prompt": "Show as a bar chart",
                "expected_subagent": "metrics_fast",
                "must_contain": []
            }
        ]
    },
    {
        "name": "SocialGraph Specialist Multi-Turn Follow-up Suite",
        "turns": [
            {
                "turn": 1,
                "prompt": "Who are the members of the Order of Titans clan?",
                "expected_subagent": "social_graph",
                "must_contain": ["Order of Titans"]
            },
            {
                "turn": 2,
                "prompt": "Who is the leader and who are the officers?",
                "expected_subagent": "social_graph",
                "must_contain": ["Leader", "Officer"]
            },
            {
                "turn": 3,
                "prompt": "Show their friendships and social connections",
                "expected_subagent": "social_graph",
                "must_contain": ["friend"]
            }
        ]
    }
]

print("=" * 80)
print("=== RUNNING MULTI-TURN CONTEXTUAL FOLLOW-UP BENCHMARK ===")
print("=" * 80)

all_results = []

for d in dialogues:
    session_id = f"followup_sess_{uuid.uuid4().hex[:8]}"
    print(f"\n\n========================================================")
    print(f"🎬 DIALOGUE: {d['name']} (Session ID: {session_id})")
    print(f"========================================================")
    
    for turn_info in d["turns"]:
        t_num = turn_info["turn"]
        prompt = turn_info["prompt"]
        exp_sub = turn_info["expected_subagent"]
        
        print(f"\n--- Turn {t_num}: \"{prompt}\" ---")
        t0 = time.time()
        
        resp = requests.post(
            f"{BASE_URL}/chat",
            json={
                "message": prompt,
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
        has_graph = False
        text_chunks = []
        
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode('utf-8')
            if decoded.startswith("DATA: "):
                try:
                    data_obj = json.loads(decoded[6:])
                    dtype = data_obj.get("type")
                    if dtype == "subagent_routed":
                        routed_subagent = data_obj.get("subagent")
                    elif dtype == "json_table":
                        has_table = True
                    elif dtype == "json_chart":
                        has_chart = True
                    elif dtype == "json_graph":
                        has_graph = True
                except Exception:
                    # It's a text chunk!
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
            elif not decoded.startswith("THOUGHT: ") and not decoded.startswith("event: "):
                text_chunks.append(decoded)
                    
        elapsed = time.time() - t0
        full_text = "".join(text_chunks).strip()
        
        # Check if expected context/keywords are in the response
        context_check = True
        missing_kw = []
        for kw in turn_info["must_contain"]:
            if kw.lower() not in full_text.lower():
                context_check = False
                missing_kw.append(kw)
                
        routing_pass = (routed_subagent == exp_sub)
        overall_pass = routing_pass and (context_check or len(turn_info["must_contain"]) == 0)
        
        status = "✅ PASS" if overall_pass else "❌ FAIL"
        print(f"  Result: {status} | Routed: {routed_subagent} | Elapsed: {elapsed:.2f}s")
        print(f"  Artifacts: Table={has_table}, Chart={has_chart}, Graph={has_graph}")
        print(f"  Text Sample: {full_text[:160]}...")
        if missing_kw:
            print(f"  ⚠️ Warning: Response did not include expected keywords: {missing_kw}")
            
        all_results.append({
            "dialogue": d["name"],
            "turn": t_num,
            "prompt": prompt,
            "routed": routed_subagent,
            "elapsed": elapsed,
            "passed": overall_pass
        })
        time.sleep(2)

print("\n\n" + "=" * 80)
print("=== MULTI-TURN FOLLOW-UP EVALUATION REPORT ===")
print("=" * 80)
print(f"{'Dialogue':<25} | {'Turn':<5} | {'Subagent':<14} | {'Time (s)':<10} | {'Status'}")
print("-" * 80)
for r in all_results:
    st = "PASS" if r["passed"] else "FAIL"
    print(f"{r['dialogue'][:25]:<25} | {r['turn']:<5} | {r['routed']:<14} | {r['elapsed']:>8.2f}s | {st}")
print("=" * 80)
