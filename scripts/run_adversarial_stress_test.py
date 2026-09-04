#!/usr/bin/env python3
"""
Adversarial Stress Test Suite against metrics_fast and deep_research agents.
Runs multiple rounds of single-turn and multi-turn adversarial queries
to uncover failure modes, misroutings, schema errors, and contextual breakdowns.
"""
import os
import sys
import time
import json
import uuid
import requests

# Ensure project root is in sys.path
sys.path.insert(0, '/usr/local/google/home/aragosa/ca_api')

from eval_agent.models import (
    TestCase, SubagentCategory, TestDifficulty, ExpectedArtifacts,
    PersonaType, VisualArtifacts
)
from eval_agent.evaluator import evaluator
from eval_agent.storage import storage

BASE_URL = "http://127.0.0.1:8080"

# 1. Adversarial Test Cases for metrics_fast & deep_research
ADVERSARIAL_CASES = [
    # --- METRICS_FAST ADVERSARIAL CASES ---
    {
        "category": SubagentCategory.METRICS_FAST,
        "title": "MF-ADV-01: Ambiguous Game Name & Conflicting Timeframes",
        "description": "Uses informal abbreviation 'Farm' & 'BR', with conflicting timeframe 'yesterday vs last 30d'.",
        "prompt": "Compare total revenue for Farm and Battle Royale yesterday vs last 30 days for iOS players in US and JP as a bar chart",
        "expected_subagent": "metrics_fast",
        "expected_artifacts": ExpectedArtifacts(
            table_required=True,
            chart_required=True,
            must_contain_keywords=["Lookerwood Farm", "Lookup Battle Royale", "US"]
        )
    },
    {
        "category": SubagentCategory.METRICS_FAST,
        "title": "MF-ADV-02: Non-Existent Dimension & Metric Hallucination Trap",
        "description": "Requests non-existent dimensions (player_ping, server_load) mixed with valid LookML revenue metrics.",
        "prompt": "Show me server ping latency and total revenue by country for the last 7 days",
        "expected_subagent": "metrics_fast",
        "expected_artifacts": ExpectedArtifacts(
            table_required=False,
            must_contain_keywords=["revenue"]
        )
    },
    {
        "category": SubagentCategory.METRICS_FAST,
        "title": "MF-ADV-03: Triple Measure Ratio with Ambiguous Visual Type",
        "description": "Requests ratio of IAP to Ad revenue per active user (ARPU vs ARPPU) with custom breakdown.",
        "prompt": "What is the ratio of IAP revenue to total ad revenue per spender (ARPPU) by device platform over the last 90 days?",
        "expected_subagent": "metrics_fast",
        "expected_artifacts": ExpectedArtifacts(
            table_required=True,
            link_required=True,
            must_contain_keywords=["iOS", "Android", "ARPPU"]
        )
    },
    {
        "category": SubagentCategory.METRICS_FAST,
        "title": "MF-ADV-04: Misspelled Explore Measure ('sesssions' vs 'sessions')",
        "description": "Tests handling of session count measure with irregular schema naming ('number_of_sesssions').",
        "prompt": "Calculate average sessions per user and D7 retention rate for Lookup Battle Royale over the last 14 days",
        "expected_subagent": "metrics_fast",
        "expected_artifacts": ExpectedArtifacts(
            table_required=True,
            must_contain_keywords=["Lookup Battle Royale", "retention"]
        )
    },

    # --- DEEP_RESEARCH ADVERSARIAL CASES ---
    {
        "category": SubagentCategory.DEEP_RESEARCH,
        "title": "DR-ADV-01: Cross-Domain Whale Spending with Implicit Clan Name",
        "description": "Tests cross-domain synthesis where whale spending in Looker must be matched with Spanner clan members without explicit keywords.",
        "prompt": "Investigate why our highest spending players have lower 7-day retention than casual players, and check if their guild leadership roles are contributing.",
        "expected_subagent": "deep_research",
        "expected_artifacts": ExpectedArtifacts(
            table_required=True,
            must_contain_keywords=["Executive Summary", "retention", "clan", "revenue"]
        )
    },
    {
        "category": SubagentCategory.DEEP_RESEARCH,
        "title": "DR-ADV-02: Multi-Hop Non-Existent Clan + Real Metrics Correlation",
        "description": "Combines a non-existent clan name with valid Looker revenue metrics to test hallucination resistance.",
        "prompt": "Analyze the revenue impact and friendship density of the PhoenixReborn clan in Lookup Battle Royale over the last 30 days.",
        "expected_subagent": "deep_research",
        "expected_artifacts": ExpectedArtifacts(
            table_required=False,
            must_contain_keywords=["PhoenixReborn", "Lookup Battle Royale"]
        )
    },
    {
        "category": SubagentCategory.DEEP_RESEARCH,
        "title": "DR-ADV-03: Strategic Root Cause on Ad Revenue vs Social Isolation",
        "description": "Asks for deep strategic correlation between ad-monetized player retention and player-to-player friendship count.",
        "prompt": "Perform a root-cause investigation on whether players with zero in-game friends generate higher ad revenue in Lookerwood Farm, and provide 3 strategic recommendations.",
        "expected_subagent": "deep_research",
        "expected_artifacts": ExpectedArtifacts(
            table_required=True,
            must_contain_keywords=["Executive Summary", "Lookerwood Farm", "Recommendations"]
        )
    },
    {
        "category": SubagentCategory.DEEP_RESEARCH,
        "title": "DR-ADV-04: Subagent Boundary Ambiguity (Looks like Metrics, requires Deep Research)",
        "description": "Prompt starts like a pure quantitative question but ends with cross-domain clan hierarchy investigation.",
        "prompt": "Give me total revenue for the last 30 days, and analyze how much of that came from officers and leaders in the Order of Titans clan.",
        "expected_subagent": "deep_research",
        "expected_artifacts": ExpectedArtifacts(
            table_required=True,
            must_contain_keywords=["Order of Titans", "revenue", "Leader", "Officer"]
        )
    }
]

# 2. Multi-Turn Adversarial Dialogues
ADVERSARIAL_DIALOGUES = [
    {
        "name": "Metrics Analyst Multi-Turn Contextual Stress Test",
        "target_category": SubagentCategory.METRICS_FAST,
        "turns": [
            {
                "turn": 1,
                "prompt": "What was total revenue by game over last 30 days?",
                "expected_subagent": "metrics_fast"
            },
            {
                "turn": 2,
                "prompt": "Now filter that down to just iOS users in Japan and show daily active users instead of revenue",
                "expected_subagent": "metrics_fast"
            },
            {
                "turn": 3,
                "prompt": "What about for the other platform in Germany?",
                "expected_subagent": "metrics_fast"
            },
            {
                "turn": 4,
                "prompt": "Plot the daily trend for both as a combo chart",
                "expected_subagent": "metrics_fast"
            }
        ]
    },
    {
        "name": "Deep Research Multi-Turn Context Shift Stress Test",
        "target_category": SubagentCategory.DEEP_RESEARCH,
        "turns": [
            {
                "turn": 1,
                "prompt": "Analyze the relationship between top spending whales, their clan memberships, and overall revenue trends.",
                "expected_subagent": "deep_research"
            },
            {
                "turn": 2,
                "prompt": "Which specific players in the Order of Titans were the biggest contributors to that IAP spike?",
                "expected_subagent": "deep_research"
            },
            {
                "turn": 3,
                "prompt": "Are their in-game friends also high spenders? Check their friendship network.",
                "expected_subagent": "deep_research"
            }
        ]
    }
]

def run_single_adversarial_test(test_info, session_id=None):
    if not session_id:
        session_id = f"adv_sess_{uuid.uuid4().hex[:8]}"

    prompt = test_info["prompt"]
    exp_sub = test_info["expected_subagent"]
    
    payload = {
        "message": prompt,
        "session_id": session_id,
        "user_id": "adversarial_tester",
        "agent_type": "auto",
        "force_refresh": True
    }

    t0 = time.time()
    thoughts = []
    text_chunks = []
    side_events = []
    routed_subagent = "unknown"
    visual_artifacts = VisualArtifacts()
    raw_error = None

    try:
        resp = requests.post(f"{BASE_URL}/chat", json=payload, stream=True, timeout=90)
        if resp.status_code != 200:
            raw_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        else:
            for line in resp.iter_lines():
                if not line:
                    continue
                decoded = line.decode('utf-8')
                if decoded.startswith("THOUGHT: "):
                    th = decoded[len("THOUGHT: "):].strip()
                    if th: thoughts.append(th)
                elif decoded.startswith("DATA: "):
                    data_str = decoded[len("DATA: "):].strip()
                    try:
                        data_obj = json.loads(data_str)
                        side_events.append(data_obj)
                        dtype = data_obj.get("type")
                        if dtype == "subagent_routed":
                            routed_subagent = data_obj.get("subagent") or data_obj.get("name") or "unknown"
                        elif dtype == "json_table":
                            visual_artifacts.table_data = data_obj.get("data")
                        elif dtype == "json_chart":
                            visual_artifacts.chart_config = data_obj.get("config")
                        elif dtype == "json_graph":
                            visual_artifacts.graph_data = data_obj.get("graphData")
                        elif dtype == "json_link":
                            visual_artifacts.explore_url = data_obj.get("url")
                        elif dtype == "json_dashboard_created":
                            visual_artifacts.dashboard_info = data_obj.get("dashboard")
                        else:
                            text_chunks.append(data_str)
                    except Exception:
                        text_chunks.append(data_str)
                elif decoded.startswith("data: "):
                    c = decoded[len("data: "):].strip()
                    try:
                        c_obj = json.loads(c)
                        if isinstance(c_obj, dict):
                            if "text" in c_obj: text_chunks.append(c_obj["text"])
                            elif "content" in c_obj and "parts" in c_obj["content"]:
                                for p in c_obj["content"]["parts"]:
                                    if "text" in p: text_chunks.append(p["text"])
                    except Exception:
                        text_chunks.append(c)
    except Exception as e:
        raw_error = str(e)

    duration = round(time.time() - t0, 2)
    response_text = "".join(text_chunks).strip()

    # Fallback routing check
    if routed_subagent == "unknown":
        thought_blob = " ".join(thoughts).lower()
        if "metrics analyst" in thought_blob or "looker metrics" in thought_blob:
            routed_subagent = "metrics_fast"
        elif "social graph" in thought_blob:
            routed_subagent = "social_graph"
        elif "dashboard architect" in thought_blob:
            routed_subagent = "dashboard_builder"
        elif "deep research" in thought_blob:
            routed_subagent = "deep_research"

    tc_obj = TestCase(
        category=test_info["category"],
        title=test_info["title"],
        description=test_info.get("description", ""),
        difficulty=TestDifficulty.ADVERSARIAL,
        prompt=prompt,
        expected_subagent=exp_sub,
        expected_artifacts=test_info.get("expected_artifacts", ExpectedArtifacts())
    )

    rubric = evaluator.evaluate_response(
        test_case=tc_obj,
        response_text=response_text,
        routed_subagent=routed_subagent,
        thoughts=thoughts,
        visual_artifacts=visual_artifacts,
        duration_seconds=duration,
        raw_error=raw_error
    )

    return {
        "title": test_info["title"],
        "category": test_info["category"].value,
        "prompt": prompt,
        "expected_subagent": exp_sub.value if hasattr(exp_sub, 'value') else str(exp_sub),
        "routed_subagent": routed_subagent,
        "is_passed": rubric.is_passed,
        "overall_score": rubric.overall_score,
        "routing_score": rubric.routing_score,
        "schema_score": rubric.schema_score,
        "accuracy_score": rubric.accuracy_score,
        "visual_score": rubric.visual_score,
        "duration_seconds": duration,
        "judge_rationale": rubric.judge_rationale,
        "issues_detected": rubric.issues_detected,
        "suggestions": rubric.suggestions,
        "has_table": visual_artifacts.table_data is not None,
        "has_chart": visual_artifacts.chart_config is not None,
        "has_graph": visual_artifacts.graph_data is not None,
        "has_link": visual_artifacts.explore_url is not None,
        "response_preview": response_text[:300] + "..." if len(response_text) > 300 else response_text,
        "thoughts_count": len(thoughts)
    }

def main():
    print("=" * 80)
    print("🚀 EXECUTING ADVERSARIAL STRESS TEST SUITE AGAINST LIVE AGENT (8080)")
    print("Targeting: metrics_fast & deep_research subagents")
    print("=" * 80)

    results = []

    # 1. Run Single-Turn Adversarial Cases
    print("\n--- PHASE 1: Single-Turn Adversarial Queries ---")
    for i, tc in enumerate(ADVERSARIAL_CASES, 1):
        print(f"\n[{i}/{len(ADVERSARIAL_CASES)}] Running: {tc['title']}")
        print(f"  Prompt: \"{tc['prompt']}\"")
        res = run_single_adversarial_test(tc)
        results.append(res)
        
        status_sym = "✅ PASSED" if res["is_passed"] else "❌ FAILED"
        print(f"  Result: {status_sym} (Score: {res['overall_score']}/100, Routing: {res['routed_subagent']} [{res['routing_score']} pts], Duration: {res['duration_seconds']}s)")
        if res["issues_detected"]:
            print(f"  ⚠️ Issues: {', '.join(res['issues_detected'])}")
        time.sleep(1)

    # 2. Run Multi-Turn Adversarial Dialogues
    print("\n\n--- PHASE 2: Multi-Turn Contextual Stress Tests ---")
    for d in ADVERSARIAL_DIALOGUES:
        session_id = f"adv_dialogue_{uuid.uuid4().hex[:8]}"
        print(f"\n🎬 Dialogue: {d['name']} (Session: {session_id})")
        for turn in d["turns"]:
            t_num = turn["turn"]
            prompt = turn["prompt"]
            print(f"\n  [Turn {t_num}] \"{prompt}\"")
            turn_info = {
                "title": f"{d['name']} - Turn {t_num}",
                "category": d["target_category"],
                "prompt": prompt,
                "expected_subagent": turn["expected_subagent"]
            }
            t_res = run_single_adversarial_test(turn_info, session_id=session_id)
            results.append(t_res)
            
            status_sym = "✅ PASSED" if t_res["is_passed"] else "❌ FAILED"
            print(f"  Result: {status_sym} (Score: {t_res['overall_score']}/100, Routed: {t_res['routed_subagent']}, Duration: {t_res['duration_seconds']}s)")
            if t_res["issues_detected"]:
                print(f"  ⚠️ Issues: {', '.join(t_res['issues_detected'])}")
            time.sleep(1)

    # 3. Save full raw report
    output_path = "/usr/local/google/home/aragosa/ca_api/eval_data/adversarial_stress_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n\n{'=' * 80}")
    print(f"🏁 COMPLETED ADVERSARIAL STRESS TEST. Results saved to: {output_path}")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    main()
