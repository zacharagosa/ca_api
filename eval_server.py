"""
FastAPI Server for Gaming Analytics Testing & Evaluation Engine.
Runs on port 8085.
"""
import os
import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from eval_agent.models import (
    SubagentCategory, TestDifficulty, PersonaType, TestCase,
    ExpectedArtifacts
)
from eval_agent.test_suites import (
    ALL_TEST_CASES, METRICS_TEST_CASES, SOCIAL_GRAPH_TEST_CASES,
    DASHBOARD_TEST_CASES, DEEP_RESEARCH_TEST_CASES, MULTI_TURN_DIALOGUES,
    get_test_case_by_id
)
from eval_agent.evaluator import evaluator, PERSONA_PROMPTS
from eval_agent.test_runner import test_runner
from eval_agent.storage import storage

app = FastAPI(
    title="Argus AI - Gaming Agent QA & Evaluation Server",
    version="1.0.0",
    description="Dedicated testing and evaluation harness for Multi-Agent Gaming Analytics."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Request Payloads
# -----------------------------------------------------------------------------
class RunSingleTestRequest(BaseModel):
    test_id: Optional[str] = None
    custom_test: Optional[TestCase] = None
    session_id: Optional[str] = None

class RunSuiteRequest(BaseModel):
    category: Optional[str] = "ALL"  # "ALL", "metrics_fast", "social_graph", "dashboard_builder", "deep_research"
    test_ids: Optional[List[str]] = None
    title: Optional[str] = "Suite Execution"

class SimulateDialogueRequest(BaseModel):
    persona: PersonaType = PersonaType.DATA_ANALYST
    target_category: SubagentCategory = SubagentCategory.METRICS_FAST
    total_turns: int = 3

class GenerateTestsRequest(BaseModel):
    category: SubagentCategory
    difficulty: str = "intermediate"
    intent: str
    count: int = 3

# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    """Checks connection to Gaming Analytics backend (port 8080) and dependencies."""
    import requests
    backend_status = "offline"
    backend_latency_ms = None
    try:
        t0 = time.time()
        r = requests.get("http://127.0.0.1:8080/", timeout=3)
        backend_latency_ms = round((time.time() - t0) * 1000, 1)
        if r.status_code in [200, 404]:
            backend_status = "online"
    except Exception:
        backend_status = "offline"

    return {
        "status": "healthy",
        "eval_server_port": 8085,
        "gaming_backend": {
            "status": backend_status,
            "url": "http://127.0.0.1:8080",
            "latency_ms": backend_latency_ms
        },
        "dataset": os.getenv("DATASET_NAME", "events"),
        "timestamp": time.time()
    }

@app.get("/api/categories")
def get_categories():
    """Returns the four core conversation types with schema definitions and capabilities."""
    return [
        {
            "id": SubagentCategory.METRICS_FAST.value,
            "name": "Looker Quantitative Metrics",
            "subagent": "metrics_fast",
            "icon": "Zap",
            "badge": "Looker LookML",
            "description": "Quantitative event metrics, DAU, revenue, retention, ARPU, sessions, game comparisons, and time-series trends using Looker.",
            "supported_artifacts": ["Vega-Lite Charts", "Data Tables", "Looker Explore Links"],
            "schema_summary": "events explore in gaming model (total_revenue, total_iap_revenue, total_ad_revenue, number_of_users, d1_retention_rate, average_revenue_per_user, etc.)"
        },
        {
            "id": SubagentCategory.SOCIAL_GRAPH.value,
            "name": "Spanner Social Graph & Clans",
            "subagent": "social_graph",
            "icon": "Share2",
            "badge": "Spanner Graph",
            "description": "Clans, Guilds, Friend networks, Player-to-player relationships, Social Graph, and Trading using Spanner Graph.",
            "supported_artifacts": ["2D Force-Directed Graphs", "Clan Hierarchy Tables", "Source Citations"],
            "schema_summary": "Players, Clans, ClanMemberships (roles: Leader, Officer, Member), Friendships, Inventory, Items"
        },
        {
            "id": SubagentCategory.DASHBOARD_BUILDER.value,
            "name": "Looker LiveOps Dashboard Architect",
            "subagent": "dashboard_builder",
            "icon": "LayoutDashboard",
            "badge": "Looker MCP",
            "description": "Building new Looker dashboards, adding tiles, modifying tile timeframes/fields, removing tiles, adding/removing dashboard filters, or LiveOps War Rooms.",
            "supported_artifacts": ["12-Column Grid Dashboards", "Embed Links", "KPI Cards", "Dashboard Filters"],
            "schema_summary": "create_looker_dashboard, edit_looker_dashboard, LiveOps war rooms, automatic tile layouts"
        },
        {
            "id": SubagentCategory.DEEP_RESEARCH.value,
            "name": "Strategic Deep Research Analyst",
            "subagent": "deep_research",
            "icon": "Brain",
            "badge": "Multi-Hop Cross-Domain",
            "description": "Cross-domain investigations requiring both Looker metrics and Spanner social data (e.g. whale spending patterns correlated with clan dynamics or root cause analysis).",
            "supported_artifacts": ["Executive Summaries", "Cross-Domain Tables", "Correlation Graphs", "Actionable Recommendations"],
            "schema_summary": "Multi-hop query pipeline combining Looker get_insights + Spanner query_spanner + Strategic Synthesis"
        }
    ]

@app.get("/api/personas")
def get_personas():
    """Returns available testing personas for dynamic multi-turn conversation simulations."""
    result = []
    for p_type, meta in PERSONA_PROMPTS.items():
        result.append({
            "id": p_type.value,
            "name": meta["name"],
            "role_desc": meta["role_desc"],
            "style": meta["style"]
        })
    return result

@app.get("/api/test-suites")
def get_test_suites():
    """Returns catalog of preset test cases and multi-turn dialogues."""
    custom = storage.list_custom_tests()
    return {
        "all_tests": [tc.model_dump() for tc in ALL_TEST_CASES] + custom,
        "metrics_tests": [tc.model_dump() for tc in METRICS_TEST_CASES],
        "social_tests": [tc.model_dump() for tc in SOCIAL_GRAPH_TEST_CASES],
        "dashboard_tests": [tc.model_dump() for tc in DASHBOARD_TEST_CASES],
        "deep_research_tests": [tc.model_dump() for tc in DEEP_RESEARCH_TEST_CASES],
        "multi_turn_dialogues": [d.model_dump() for d in MULTI_TURN_DIALOGUES],
        "custom_tests": custom
    }

@app.post("/api/test-case/run")
async def run_single_test_endpoint(req: RunSingleTestRequest):
    """Executes a single test case with Server-Sent Events (SSE) streaming."""
    tc = None
    if req.custom_test:
        tc = req.custom_test
    elif req.test_id:
        tc = get_test_case_by_id(req.test_id)
        if not tc:
            # Check custom tests
            for c in storage.list_custom_tests():
                if c.get("id") == req.test_id:
                    tc = TestCase(**c)
                    break
    
    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    def event_stream():
        gen = test_runner.run_single_test_streaming(tc, session_id=req.session_id)
        try:
            for event in gen:
                yield f"data: {json.dumps(event)}\n\n"
        except StopIteration:
            pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/api/suite/run")
async def run_suite_endpoint(req: RunSuiteRequest):
    """Executes a suite of test cases with SSE progress streaming."""
    target_tests: List[TestCase] = []
    
    if req.test_ids:
        for tid in req.test_ids:
            tc = get_test_case_by_id(tid)
            if tc:
                target_tests.append(tc)
    elif req.category == "ALL" or not req.category:
        target_tests = list(ALL_TEST_CASES)
    else:
        try:
            cat_enum = SubagentCategory(req.category)
            target_tests = [tc for tc in ALL_TEST_CASES if tc.category == cat_enum]
        except Exception:
            target_tests = list(ALL_TEST_CASES)

    if not target_tests:
        raise HTTPException(status_code=400, detail="No test cases match the selection")

    def event_stream():
        gen = test_runner.run_suite_streaming(target_tests, run_title=req.title or "Test Suite Run")
        try:
            for event in gen:
                yield f"data: {json.dumps(event)}\n\n"
        except StopIteration:
            pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/api/simulate-dialogue")
async def simulate_dialogue_endpoint(req: SimulateDialogueRequest):
    """Runs a dynamic multi-turn conversation simulation with a synthetic persona."""
    def event_stream():
        gen = test_runner.simulate_dynamic_dialogue_streaming(
            persona=req.persona,
            target_category=req.target_category,
            total_turns=req.total_turns
        )
        try:
            for event in gen:
                yield f"data: {json.dumps(event)}\n\n"
        except StopIteration:
            pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/api/generate-test-cases")
def generate_test_cases_endpoint(req: GenerateTestsRequest):
    """Uses the AI Evaluator to generate new test cases dynamically."""
    generated = evaluator.generate_ai_test_cases(
        category=req.category,
        difficulty=req.difficulty,
        user_intent=req.intent,
        count=req.count
    )
    if generated:
        storage.save_custom_tests(generated)
    return {"generated_count": len(generated), "test_cases": [tc.model_dump() for tc in generated]}

@app.get("/api/runs")
def list_runs():
    """Returns execution history and past runs."""
    return storage.list_runs()

@app.get("/api/runs/{run_id}")
def get_run_details(run_id: str):
    """Returns full details of a specific test suite execution."""
    run = storage.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run.model_dump()

@app.post("/api/runs/{run_id}/set-baseline")
def set_baseline_endpoint(run_id: str):
    """Sets the designated run as the baseline for regression tracking."""
    success = storage.set_baseline(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"success": True, "baseline_run_id": run_id}

@app.get("/api/benchmarks/comparison")
def compare_benchmark(run_id: Optional[str] = None):
    """Compares a specific run (or latest run) against the baseline run to identify regressions."""
    if not run_id:
        runs = storage.list_runs()
        if not runs:
            return {"error": "No runs available to compare"}
        run_id = runs[0].get("run_id")
        
    comp = storage.compare_to_baseline(run_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Comparison failed or run not found")
    return comp.model_dump()

@app.get("/api/simulations")
def list_simulations():
    """Returns past dynamic dialogue simulations."""
    return storage.list_simulations()

# Mount frontend static files if built
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "eval_frontend/dist"))
if os.path.exists(frontend_dist):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
