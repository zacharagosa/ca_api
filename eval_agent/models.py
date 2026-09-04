"""
Data models and schemas for the Gaming Analytics Agent Testing & Evaluation Suite.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
import time
import uuid

class SubagentCategory(str, Enum):
    METRICS_FAST = "metrics_fast"
    SOCIAL_GRAPH = "social_graph"
    DASHBOARD_BUILDER = "dashboard_builder"
    DEEP_RESEARCH = "deep_research"

class TestDifficulty(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ADVERSARIAL = "adversarial"

class TestStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"

class PersonaType(str, Enum):
    EXECUTIVE_VP = "executive_vp"
    LIVEOPS_PM = "liveops_pm"
    GUILD_MASTER = "guild_master"
    QA_ADVERSARY = "qa_adversary"
    DATA_ANALYST = "data_analyst"

class ExpectedArtifacts(BaseModel):
    table_required: bool = False
    chart_required: bool = False
    graph_required: bool = False
    link_required: bool = False
    dashboard_required: bool = False
    must_contain_keywords: List[str] = Field(default_factory=list)
    forbidden_keywords: List[str] = Field(default_factory=list)

class TestCase(BaseModel):
    id: str = Field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:8]}")
    category: SubagentCategory
    title: str
    description: str
    difficulty: TestDifficulty = TestDifficulty.BASIC
    prompt: str
    expected_subagent: SubagentCategory
    expected_artifacts: ExpectedArtifacts = Field(default_factory=ExpectedArtifacts)
    tags: List[str] = Field(default_factory=list)
    timeout_seconds: int = 120

class MultiTurnTurn(BaseModel):
    turn: int
    prompt: str
    expected_subagent: SubagentCategory
    expected_keywords: List[str] = Field(default_factory=list)
    expected_artifacts: ExpectedArtifacts = Field(default_factory=ExpectedArtifacts)

class MultiTurnDialogueCase(BaseModel):
    id: str = Field(default_factory=lambda: f"dialogue_{uuid.uuid4().hex[:8]}")
    title: str
    category: SubagentCategory
    persona: PersonaType = PersonaType.DATA_ANALYST
    description: str
    turns: List[MultiTurnTurn]

class EvaluationRubricScore(BaseModel):
    routing_score: float = 100.0       # 0 or 100 (Correct subagent)
    schema_score: float = 100.0        # 0-100 (Proper dimensions/measures/tables)
    accuracy_score: float = 100.0      # 0-100 (Semantic accuracy & intent fulfillment)
    visual_score: float = 100.0        # 0-100 (Tables/Charts/Graphs presence & format)
    latency_score: float = 100.0       # 0-100 (Time within threshold)
    overall_score: float = 100.0       # Composite weighted score
    is_passed: bool = True
    judge_rationale: str = ""
    issues_detected: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

class VisualArtifacts(BaseModel):
    table_data: Optional[Dict[str, Any]] = None
    chart_config: Optional[Dict[str, Any]] = None
    graph_data: Optional[Dict[str, Any]] = None
    explore_url: Optional[str] = None
    dashboard_info: Optional[Dict[str, Any]] = None

class TestResult(BaseModel):
    test_id: str
    test_title: str
    category: SubagentCategory
    prompt: str
    status: TestStatus = TestStatus.IDLE
    routed_subagent: str = "unknown"
    expected_subagent: str = "unknown"
    duration_seconds: float = 0.0
    time_to_first_thought: float = 0.0
    time_to_first_token: float = 0.0
    response_text: str = ""
    thoughts: List[str] = Field(default_factory=list)
    side_events: List[Dict[str, Any]] = Field(default_factory=list)
    visual_artifacts: VisualArtifacts = Field(default_factory=VisualArtifacts)
    rubric: EvaluationRubricScore = Field(default_factory=EvaluationRubricScore)
    raw_error: Optional[str] = None
    executed_at: float = Field(default_factory=time.time)

class SimulationTurnResult(BaseModel):
    turn: int
    user_prompt: str
    agent_response: str
    routed_subagent: str
    thoughts: List[str] = Field(default_factory=list)
    visual_artifacts: VisualArtifacts = Field(default_factory=VisualArtifacts)
    rubric: EvaluationRubricScore = Field(default_factory=EvaluationRubricScore)
    duration_seconds: float = 0.0

class DynamicSimulationResult(BaseModel):
    simulation_id: str = Field(default_factory=lambda: f"sim_{uuid.uuid4().hex[:8]}")
    persona: PersonaType
    persona_name: str
    target_category: SubagentCategory
    total_turns: int
    turns: List[SimulationTurnResult] = Field(default_factory=list)
    overall_coherence_score: float = 100.0
    overall_accuracy_score: float = 100.0
    overall_routing_precision: float = 100.0
    final_assessment: str = ""
    duration_seconds: float = 0.0
    executed_at: float = Field(default_factory=time.time)

class TestSuiteRun(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    title: str = "Full Test Suite Run"
    trigger_source: str = "manual"
    dataset_name: str = "events"
    model_name: str = "gemini-3.5-flash"
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    warning_tests: int = 0
    pass_rate: float = 0.0
    avg_latency_seconds: float = 0.0
    routing_accuracy_pct: float = 0.0
    visual_payload_rate_pct: float = 0.0
    overall_reliability_score: float = 0.0
    category_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    results: List[TestResult] = Field(default_factory=list)
    is_baseline: bool = False
    started_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_seconds: float = 0.0

class BenchmarkComparison(BaseModel):
    current_run_id: str
    baseline_run_id: str
    pass_rate_delta: float = 0.0
    latency_delta_seconds: float = 0.0
    reliability_delta: float = 0.0
    routing_accuracy_delta: float = 0.0
    regressions: List[Dict[str, Any]] = Field(default_factory=list)
    improvements: List[Dict[str, Any]] = Field(default_factory=list)
    category_deltas: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    executive_summary: str = ""
