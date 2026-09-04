import requests
import json
import time
import uuid

BASE_URL = "http://127.0.0.1:8080"

def send_chat_prompt(session_id, prompt, agent_type="deep"):
    url = f"{BASE_URL}/chat"
    payload = {
        "message": prompt,
        "agent_type": agent_type,
        "deep_analysis": True,
        "session_id": session_id,
        "user_id": "test_user_dashboard_eval",
        "force_refresh": True
    }
    
    print(f"\n=======================================================")
    print(f"PROMPT [{agent_type}]: {prompt}")
    print(f"SESSION ID: {session_id}")
    print(f"=======================================================")
    
    t0 = time.time()
    resp = requests.post(url, json=payload, stream=True, timeout=120)
    
    thoughts = []
    text_chunks = []
    side_events = []
    
    for line in resp.iter_lines():
        if not line:
            continue
        decoded = line.decode('utf-8')
        if decoded.startswith("THOUGHT: "):
            thought_text = decoded[len("THOUGHT: "):]
            thoughts.append(thought_text)
            print(f"[THOUGHT] {thought_text}")
        elif decoded.startswith("DATA: "):
            data_json_str = decoded[len("DATA: "):]
            try:
                data_obj = json.loads(data_json_str)
                side_events.append(data_obj)
                print(f"[DATA EVENT] Type: {data_obj.get('type')}")
                if data_obj.get('type') == 'json_dashboard_created':
                    dash = data_obj.get('dashboard', {})
                    print(f"  -> Dashboard ID: {dash.get('looker_id')}, Title: '{dash.get('title')}', Tiles: {dash.get('tiles_count')}, Filters: {len(dash.get('filters', []))}")
            except Exception as e:
                print(f"[DATA EVENT ERROR] {e} on {data_json_str[:100]}")
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
        elif decoded.startswith("ERROR: "):
            print(f"[SERVER ERROR] {decoded}")

    elapsed = time.time() - t0
    final_text = "".join(text_chunks).strip()
    
    print(f"\n--- FINAL AGENT RESPONSE ({elapsed:.2f}s) ---")
    print(final_text[:1000] + ("..." if len(final_text) > 1000 else ""))
    print("---------------------------------------------")
    
    return {
        "elapsed": elapsed,
        "thoughts": thoughts,
        "side_events": side_events,
        "final_text": final_text
    }

def run_all_tests():
    session_id = f"eval_session_{uuid.uuid4().hex[:8]}"
    results = {}
    
    # Test 1: Initial Dashboard Creation
    p1 = "Build a new LiveOps War Room dashboard for Season 4 with 3 tiles: Daily Active Users over the last 30 days, Total Revenue by Game, and Session Counts, with interactive filters for Date Range and Game Title."
    results["1_create_dashboard"] = send_chat_prompt(session_id, p1)
    
    time.sleep(2)
    
    # Test 2: Iterative Addition - New Tiles
    p2 = "Add a new tile showing D1 Retention Rate and D7 Retention Rate over time to this dashboard."
    results["2_add_retention_tile"] = send_chat_prompt(session_id, p2)
    
    time.sleep(2)
    
    # Test 3: Iterative Addition - Single-value KPI & New Filter
    p3 = "Add a single-value KPI tile for Total IAP Revenue, and add a Country filter to the dashboard."
    results["3_add_kpi_and_filter"] = send_chat_prompt(session_id, p3)
    
    time.sleep(2)
    
    # Test 4: Iterative Modification - Delete tile & Rename
    p4 = "Remove the Session Counts tile and rename the dashboard to 'Season 4 LiveOps Command Center'."
    results["4_delete_tile_and_rename"] = send_chat_prompt(session_id, p4)
    
    time.sleep(2)
    
    # Test 5: In-place Tile Modification - Modify timeframe
    p5 = "Change the timeframe of the Daily Active Users tile to 90 days."
    results["5_modify_tile_timeframe"] = send_chat_prompt(session_id, p5)
    
    time.sleep(2)

    # Test 6: Layout / Pixel request (Unsupported capability boundary)
    p6 = "Resize the Daily Active Users tile to 500x300 pixels and move it to column 3."
    results["6_unsupported_layout"] = send_chat_prompt(session_id, p6)
    
    time.sleep(2)
    
    # Test 7: Explicit Brand New Dashboard (Separate session/request)
    p7 = "Create a brand new separate dashboard titled 'Whale Monetization Deep Dive' tracking total revenue and top purchasing countries."
    results["7_new_separate_dashboard"] = send_chat_prompt(session_id, p7)

    print("\n\n=======================================================")
    print("ALL TESTS COMPLETED. SUMMARY OF RESULTS:")
    print("=======================================================")
    for key, res in results.items():
        dash_events = [e for e in res["side_events"] if e.get("type") == "json_dashboard_created"]
        print(f"\nTest '{key}':")
        print(f"  Duration: {res['elapsed']:.2f}s")
        print(f"  Thoughts count: {len(res['thoughts'])}")
        print(f"  Dashboard events: {len(dash_events)}")
        if dash_events:
            d = dash_events[0].get("dashboard", {})
            print(f"  Dashboard Info -> ID: {d.get('looker_id')}, Title: {d.get('title')}, Tiles: {d.get('tiles_count')}")

if __name__ == "__main__":
    run_all_tests()

