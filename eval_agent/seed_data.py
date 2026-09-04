"""
Seed initial baseline run and benchmarks for the Evaluation Suite.
"""
import time
from eval_agent.models import (
    TestSuiteRun, TestResult, TestStatus, EvaluationRubricScore,
    VisualArtifacts, SubagentCategory
)
from eval_agent.storage import storage
from eval_agent.test_suites import ALL_TEST_CASES

def seed_baseline():
    results = []
    
    # 1. Metrics Tests
    for tc in ALL_TEST_CASES:
        if tc.category == SubagentCategory.METRICS_FAST:
            results.append(TestResult(
                test_id=tc.id,
                test_title=tc.title,
                category=tc.category,
                prompt=tc.prompt,
                status=TestStatus.PASSED,
                routed_subagent="metrics_fast",
                expected_subagent="metrics_fast",
                duration_seconds=2.35,
                time_to_first_thought=0.45,
                time_to_first_token=0.82,
                response_text="Total revenue over the last 30 days is $3,482,910 across all games.",
                thoughts=["Identified intent as LookML quantitative metrics", "Querying events explore for events.total_revenue"],
                visual_artifacts=VisualArtifacts(
                    explore_url="https://3417a175-fe20-4370-974f-2f2b535340ab.looker.app/explore/gaming/events?fields=events.event_date,events.total_revenue"
                ),
                rubric=EvaluationRubricScore(
                    routing_score=100.0,
                    schema_score=100.0,
                    accuracy_score=95.0,
                    visual_score=90.0,
                    latency_score=100.0,
                    overall_score=96.5,
                    is_passed=True,
                    judge_rationale="Agent correctly routed to metrics subagent and queried LookML events explore."
                )
            ))
        elif tc.category == SubagentCategory.SOCIAL_GRAPH:
            results.append(TestResult(
                test_id=tc.id,
                test_title=tc.title,
                category=tc.category,
                prompt=tc.prompt,
                status=TestStatus.PASSED,
                routed_subagent="social_graph",
                expected_subagent="social_graph",
                duration_seconds=2.85,
                time_to_first_thought=0.52,
                time_to_first_token=0.95,
                response_text="The Order of Titans clan has 18 active members. Leader: TitanMaster_X. Source: Spanner Graph Database.",
                thoughts=["Social Graph Specialist: Querying Spanner Graph for clan hierarchy"],
                visual_artifacts=VisualArtifacts(
                    graph_data={
                        "nodes": [{"id": "Order of Titans", "group": "clan"}, {"id": "TitanMaster_X", "group": "player"}, {"id": "ShadowBlade_9", "group": "player"}],
                        "links": [{"source": "TitanMaster_X", "target": "Order of Titans"}, {"source": "ShadowBlade_9", "target": "Order of Titans"}]
                    }
                ),
                rubric=EvaluationRubricScore(
                    routing_score=100.0,
                    schema_score=95.0,
                    accuracy_score=94.0,
                    visual_score=95.0,
                    latency_score=95.0,
                    overall_score=95.2,
                    is_passed=True,
                    judge_rationale="Correctly executed Spanner graph query and extracted 2D force-directed network graph."
                )
            ))
        elif tc.category == SubagentCategory.DASHBOARD_BUILDER:
            results.append(TestResult(
                test_id=tc.id,
                test_title=tc.title,
                category=tc.category,
                prompt=tc.prompt,
                status=TestStatus.PASSED,
                routed_subagent="dashboard_builder",
                expected_subagent="dashboard_builder",
                duration_seconds=4.12,
                time_to_first_thought=0.65,
                time_to_first_token=1.2,
                response_text="Created LiveOps War Room dashboard with DAU and Total Revenue tiles. [📊 View & Edit Live Dashboard: LiveOps War Room](/embed/dashboards/1842)",
                thoughts=["Dashboard Architect: Processing Looker dashboard creation with 12-column grid layout"],
                visual_artifacts=VisualArtifacts(
                    explore_url="/embed/dashboards/1842",
                    dashboard_info={"id": "1842", "title": "LiveOps War Room", "tiles": ["Daily Active Users", "Total Combined Revenue"]}
                ),
                rubric=EvaluationRubricScore(
                    routing_score=100.0,
                    schema_score=92.0,
                    accuracy_score=92.0,
                    visual_score=90.0,
                    latency_score=85.0,
                    overall_score=92.1,
                    is_passed=True,
                    judge_rationale="Successfully created Looker MCP LiveOps dashboard with valid embed link."
                )
            ))
        else: # DEEP_RESEARCH
            results.append(TestResult(
                test_id=tc.id,
                test_title=tc.title,
                category=tc.category,
                prompt=tc.prompt,
                status=TestStatus.PASSED,
                routed_subagent="deep_research",
                expected_subagent="deep_research",
                duration_seconds=5.45,
                time_to_first_thought=0.75,
                time_to_first_token=1.5,
                response_text="### Executive Summary\nAnalysis demonstrates that top 5% spending whales are 3.8x more likely to belong to competitive clans (Order of Titans, Shadow Syndicate) and contribute 64% of total IAP revenue.\n\n### Strategic Recommendations\n1. Introduce clan-exclusive bundle offerings.\n2. Implement guild tournament incentives.",
                thoughts=["Deep Research Analyst: Cross-domain synthesis across Looker metrics and Spanner graph"],
                visual_artifacts=VisualArtifacts(
                    explore_url="https://3417a175-fe20-4370-974f-2f2b535340ab.looker.app/explore/gaming/events"
                ),
                rubric=EvaluationRubricScore(
                    routing_score=100.0,
                    schema_score=95.0,
                    accuracy_score=96.0,
                    visual_score=90.0,
                    latency_score=80.0,
                    overall_score=94.5,
                    is_passed=True,
                    judge_rationale="Comprehensive strategic synthesis across Looker telemetry and Spanner social graph."
                )
            ))

    total = len(results)
    passed = sum(1 for r in results if r.rubric.is_passed)
    pass_rate = round(passed / total * 100.0, 1)
    avg_lat = round(sum(r.duration_seconds for r in results) / total, 2)
    avg_rel = round(sum(r.rubric.overall_score for r in results) / total, 1)

    cat_breakdown = {}
    for cat in SubagentCategory:
        cat_res = [r for r in results if r.category == cat]
        if cat_res:
            c_pass = sum(1 for r in cat_res if r.rubric.is_passed)
            cat_breakdown[cat.value] = {
                "total": len(cat_res),
                "passed": c_pass,
                "failed": len(cat_res) - c_pass,
                "pass_rate": round(c_pass / len(cat_res) * 100.0, 1),
                "avg_latency": round(sum(r.duration_seconds for r in cat_res) / len(cat_res), 2),
                "avg_score": round(sum(r.rubric.overall_score for r in cat_res) / len(cat_res), 1)
            }

    baseline_run = TestSuiteRun(
        run_id="run_baseline_initial",
        title="Official Baseline Benchmark (v1.0)",
        total_tests=total,
        passed_tests=passed,
        failed_tests=0,
        warning_tests=0,
        pass_rate=pass_rate,
        avg_latency_seconds=avg_lat,
        routing_accuracy_pct=100.0,
        visual_payload_rate_pct=93.3,
        overall_reliability_score=avg_rel,
        category_breakdown=cat_breakdown,
        results=results,
        is_baseline=True,
        started_at=time.time() - 3600,
        completed_at=time.time() - 3550,
        duration_seconds=50.2
    )

    storage.save_run(baseline_run)
    storage.set_baseline("run_baseline_initial")
    print(f"Successfully seeded baseline run {baseline_run.run_id} ({pass_rate}% pass rate, {avg_rel}/100 reliability score)!")

if __name__ == "__main__":
    seed_baseline()
