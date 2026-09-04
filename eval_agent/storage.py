"""
Persistence and Historical Regression Tracking for the Evaluation Suite.
"""
import os
import json
import time
from typing import List, Dict, Any, Optional
from eval_agent.models import TestSuiteRun, BenchmarkComparison, DynamicSimulationResult, TestCase

STORAGE_DIR = "/usr/local/google/home/aragosa/ca_api/eval_data"
RUNS_FILE = os.path.join(STORAGE_DIR, "runs.json")
BASELINE_FILE = os.path.join(STORAGE_DIR, "baseline.json")
SIMULATIONS_FILE = os.path.join(STORAGE_DIR, "simulations.json")
CUSTOM_TESTS_FILE = os.path.join(STORAGE_DIR, "custom_tests.json")

class EvaluationStorage:
    def __init__(self):
        os.makedirs(STORAGE_DIR, exist_ok=True)
        self._ensure_files()

    def _ensure_files(self):
        for path in [RUNS_FILE, SIMULATIONS_FILE, CUSTOM_TESTS_FILE]:
            if not os.path.exists(path):
                with open(path, "w") as f:
                    json.dump([], f)

    def save_run(self, run: TestSuiteRun):
        runs = self.list_runs()
        # Prepend latest run
        runs.insert(0, run.model_dump())
        # Keep latest 50 runs
        runs = runs[:50]
        with open(RUNS_FILE, "w") as f:
            json.dump(runs, f, indent=2)

        # If marked as baseline, update baseline.json
        if run.is_baseline:
            self.set_baseline(run.run_id)

    def list_runs(self) -> List[Dict[str, Any]]:
        try:
            with open(RUNS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def get_run(self, run_id: str) -> Optional[TestSuiteRun]:
        runs = self.list_runs()
        for r in runs:
            if r.get("run_id") == run_id:
                return TestSuiteRun(**r)
        return None

    def set_baseline(self, run_id: str) -> bool:
        run = self.get_run(run_id)
        if not run:
            return False
        with open(BASELINE_FILE, "w") as f:
            json.dump(run.model_dump(), f, indent=2)
            
        # Update runs.json is_baseline flags
        runs = self.list_runs()
        for r in runs:
            r["is_baseline"] = (r.get("run_id") == run_id)
        with open(RUNS_FILE, "w") as f:
            json.dump(runs, f, indent=2)
        return True

    def get_baseline(self) -> Optional[TestSuiteRun]:
        if not os.path.exists(BASELINE_FILE):
            # If no baseline file, use the oldest or first run
            runs = self.list_runs()
            if runs:
                return TestSuiteRun(**runs[-1])
            return None
        try:
            with open(BASELINE_FILE, "r") as f:
                data = json.load(f)
                return TestSuiteRun(**data)
        except Exception:
            return None

    def compare_to_baseline(self, current_run_id: str) -> Optional[BenchmarkComparison]:
        current_run = self.get_run(current_run_id)
        if not current_run:
            return None
            
        baseline_run = self.get_baseline()
        if not baseline_run:
            # Baseline is current itself
            baseline_run = current_run

        pass_rate_delta = current_run.pass_rate - baseline_run.pass_rate
        latency_delta = current_run.avg_latency_seconds - baseline_run.avg_latency_seconds
        rel_delta = current_run.overall_reliability_score - baseline_run.overall_reliability_score
        routing_delta = current_run.routing_accuracy_pct - baseline_run.routing_accuracy_pct

        # Map baseline test statuses
        baseline_map = {r.test_id: r for r in baseline_run.results}
        regressions = []
        improvements = []

        for curr_res in current_run.results:
            base_res = baseline_map.get(curr_res.test_id)
            if base_res:
                if base_res.rubric.is_passed and not curr_res.rubric.is_passed:
                    regressions.append({
                        "test_id": curr_res.test_id,
                        "title": curr_res.test_title,
                        "category": curr_res.category.value,
                        "previous_score": base_res.rubric.overall_score,
                        "current_score": curr_res.rubric.overall_score,
                        "issues": curr_res.rubric.issues_detected
                    })
                elif not base_res.rubric.is_passed and curr_res.rubric.is_passed:
                    improvements.append({
                        "test_id": curr_res.test_id,
                        "title": curr_res.test_title,
                        "category": curr_res.category.value,
                        "previous_score": base_res.rubric.overall_score,
                        "current_score": curr_res.rubric.overall_score
                    })

        # Category level deltas
        category_deltas = {}
        for cat, cat_data in current_run.category_breakdown.items():
            base_cat = baseline_run.category_breakdown.get(cat, {})
            category_deltas[cat] = {
                "current_pass_rate": cat_data.get("pass_rate", 0),
                "baseline_pass_rate": base_cat.get("pass_rate", 0),
                "pass_rate_delta": round(cat_data.get("pass_rate", 0) - base_cat.get("pass_rate", 0), 1),
                "current_latency": cat_data.get("avg_latency", 0),
                "baseline_latency": base_cat.get("avg_latency", 0),
                "latency_delta": round(cat_data.get("avg_latency", 0) - base_cat.get("avg_latency", 0), 2)
            }

        summary = f"Run {current_run.run_id[:8]} vs Baseline {baseline_run.run_id[:8]}: "
        if pass_rate_delta > 0:
            summary += f"Pass rate improved by +{pass_rate_delta:.1f}%. "
        elif pass_rate_delta < 0:
            summary += f"Pass rate degraded by {pass_rate_delta:.1f}%. "
        else:
            summary += "Pass rate remained unchanged. "

        if regressions:
            summary += f"⚠️ {len(regressions)} regressions detected! "
        if improvements:
            summary += f"✅ {len(improvements)} test fixes verified."

        return BenchmarkComparison(
            current_run_id=current_run.run_id,
            baseline_run_id=baseline_run.run_id,
            pass_rate_delta=round(pass_rate_delta, 1),
            latency_delta_seconds=round(latency_delta, 2),
            reliability_delta=round(rel_delta, 1),
            routing_accuracy_delta=round(routing_delta, 1),
            regressions=regressions,
            improvements=improvements,
            category_deltas=category_deltas,
            executive_summary=summary
        )

    def save_simulation(self, sim: DynamicSimulationResult):
        sims = self.list_simulations()
        sims.insert(0, sim.model_dump())
        sims = sims[:30]
        with open(SIMULATIONS_FILE, "w") as f:
            json.dump(sims, f, indent=2)

    def list_simulations(self) -> List[Dict[str, Any]]:
        try:
            with open(SIMULATIONS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def save_custom_tests(self, test_cases: List[TestCase]):
        existing = self.list_custom_tests()
        for tc in test_cases:
            existing.append(tc.model_dump())
        with open(CUSTOM_TESTS_FILE, "w") as f:
            json.dump(existing, f, indent=2)

    def list_custom_tests(self) -> List[Dict[str, Any]]:
        try:
            with open(CUSTOM_TESTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []

storage = EvaluationStorage()
