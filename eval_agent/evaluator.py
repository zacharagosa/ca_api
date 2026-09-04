"""
Core Evaluation Engine, Persona Simulator, and LLM-as-Judge for the Gaming Analytics Agent.
"""
import os
import json
import time
import re
from typing import List, Dict, Any, Optional
from eval_agent.models import (
    TestCase, SubagentCategory, PersonaType, EvaluationRubricScore,
    VisualArtifacts, TestResult, TestStatus, SimulationTurnResult,
    DynamicSimulationResult
)

# Persona Definitions & Behavioral Prompts
PERSONA_PROMPTS = {
    PersonaType.EXECUTIVE_VP: {
        "name": "Sarah Chen (Executive VP of Games)",
        "role_desc": "Senior Gaming Executive focused on high-level ROI, cross-game comparisons, retention curves, and monetization health (IAP vs Ads).",
        "style": "Direct, business-focused, asks about revenue, DAU, and high-impact strategic comparisons."
    },
    PersonaType.LIVEOPS_PM: {
        "name": "Alex Rivera (LiveOps Product Manager)",
        "role_desc": "LiveOps PM overseeing daily events, war rooms, custom Looker dashboards, KPI alerts, and ARPPU optimization.",
        "style": "Wants dashboards created, specific tile timeframes (30d vs 90d), country filters, and granular monetization breakdowns."
    },
    PersonaType.GUILD_MASTER: {
        "name": "Elena Rostova (Community & Guild Director)",
        "role_desc": "Community Manager focused on clan dynamics, social networks, player friendships, leadership rosters, and guild wars.",
        "style": "Asks about clan rosters (Order of Titans, Shadow Syndicate, DragonSlayers), clan leaders, officer account levels, and friendship graphs."
    },
    PersonaType.QA_ADVERSARY: {
        "name": "Marcus Vance (Adversarial QA & Stress Tester)",
        "role_desc": "Lead QA Engineer actively testing edge cases, boundary filters, subtle multi-turn context switches, and schema hallucination traps.",
        "style": "Uses informal phrasing, complex multi-part queries, sudden contextual followups, and subtle edge cases."
    },
    PersonaType.DATA_ANALYST: {
        "name": "David Kim (Senior Gaming Data Analyst)",
        "role_desc": "Quantitative data analyst diving deep into LookML metrics, time-series line charts, platform splits (iOS vs Android), and D1/D7 retention.",
        "style": "Asks precise analytical questions, requests bar and line charts, and verifies underlying data tables."
    }
}

class EvaluationEngine:
    """
    Evaluates response quality, schema grounding, routing accuracy,
    and visual artifact generation using both deterministic heuristics and Gemini LLM Judge.
    """
    def __init__(self):
        self.model_name = os.getenv("EVAL_JUDGE_MODEL", "gemini-3.5-flash")
        self._init_vertex()

    def _init_vertex(self):
        try:
            import agent
            agent.init_vertex_ai()
        except Exception as e:
            print(f"DEBUG: Could not init Vertex AI via agent module: {e}")

    def _get_judge_model(self):
        try:
            self._init_vertex()
            from vertexai.generative_models import GenerativeModel
            return GenerativeModel(self.model_name)
        except Exception as e:
            print(f"DEBUG: Could not initialize Vertex AI Judge model: {e}")
            return None

    def evaluate_response(
        self,
        test_case: TestCase,
        response_text: str,
        routed_subagent: str,
        thoughts: List[str],
        visual_artifacts: VisualArtifacts,
        duration_seconds: float,
        raw_error: Optional[str] = None
    ) -> EvaluationRubricScore:
        """
        Runs comprehensive rubric evaluation for a test execution.
        """
        issues = []
        suggestions = []
        
        # 1. Routing Score (30% weight)
        expected_sub = test_case.expected_subagent.value
        actual_sub = routed_subagent
        
        # Normalize subagent names if needed
        if actual_sub == "Metrics Analyst" or actual_sub == "metrics":
            actual_sub = "metrics_fast"
        elif actual_sub == "Social Graph Specialist" or actual_sub == "social":
            actual_sub = "social_graph"
        elif actual_sub == "Dashboard Architect" or actual_sub == "dashboard":
            actual_sub = "dashboard_builder"
        elif actual_sub == "Deep Research Analyst" or actual_sub == "deep":
            actual_sub = "deep_research"
            
        routing_score = 100.0 if actual_sub == expected_sub else 0.0
        if routing_score == 0.0:
            issues.append(f"Subagent routing mismatch: expected '{expected_sub}', but routed to '{actual_sub}'.")
            suggestions.append(f"Refine router keyword heuristics in classify_subagent_route for category '{expected_sub}'.")

        # 2. Schema & Error Heuristics (25% weight)
        schema_score = 100.0
        if raw_error:
            schema_score = 0.0
            issues.append(f"Execution error encountered: {raw_error}")
        else:
            # Check for raw unparsed JSON leak in output text
            if "DATA_PAYLOAD_JSON" in response_text or '{"type":' in response_text and '"query_details"' in response_text:
                schema_score -= 40.0
                issues.append("Raw JSON metadata or query_details leaked into user-facing response text.")
                suggestions.append("Ensure server.py filter_raw_json_from_text properly scrubs internal payloads.")
            
            # Check for required keywords
            req_keywords = test_case.expected_artifacts.must_contain_keywords
            missing_kw = [kw for kw in req_keywords if kw.lower() not in response_text.lower() and not any(kw.lower() in t.lower() for t in thoughts)]
            if missing_kw:
                schema_score -= (len(missing_kw) * 15.0)
                issues.append(f"Missing expected domain keywords: {', '.join(missing_kw)}.")

        schema_score = max(0.0, min(100.0, schema_score))

        # 3. Visual Artifacts Score (15% weight)
        visual_score = 100.0
        exp_art = test_case.expected_artifacts
        
        if exp_art.table_required and not visual_artifacts.table_data:
            visual_score -= 40.0
            issues.append("Expected a structured data table (json_table), but none was emitted.")
        if exp_art.chart_required and not visual_artifacts.chart_config:
            visual_score -= 40.0
            issues.append("Expected an interactive chart visualization (json_chart), but none was emitted.")
        if exp_art.graph_required and not visual_artifacts.graph_data:
            visual_score -= 40.0
            issues.append("Expected a 2D network graph payload (json_graph), but none was emitted.")
        if exp_art.link_required and not (visual_artifacts.explore_url or "/embed/dashboards/" in response_text or "/explore/" in response_text):
            visual_score -= 20.0
            issues.append("Expected a Looker explore or dashboard embed link, but none was found.")
            
        visual_score = max(0.0, min(100.0, visual_score))

        # 4. Latency Score (5% weight)
        latency_score = 100.0
        if duration_seconds > 45.0:
            latency_score = 40.0
            issues.append(f"High latency warning: took {duration_seconds:.1f}s (>45s).")
        elif duration_seconds > 20.0:
            latency_score = 75.0

        # 5. Semantic Accuracy & Intent Fulfillment (LLM Judge - 25% weight)
        accuracy_score = 85.0
        judge_rationale = "Deterministic evaluation applied."
        
        # Try running LLM-as-judge if available
        judge_result = self._run_llm_judge(
            test_case=test_case,
            response_text=response_text,
            routed_subagent=actual_sub,
            thoughts=thoughts,
            visual_artifacts=visual_artifacts
        )
        if judge_result:
            accuracy_score = judge_result.get("accuracy_score", 85.0)
            judge_rationale = judge_result.get("judge_rationale", judge_rationale)
            judge_issues = judge_result.get("issues_detected", [])
            for j_iss in judge_issues:
                if j_iss not in issues:
                    issues.append(j_iss)
            judge_suggs = judge_result.get("suggestions", [])
            for j_sug in judge_suggs:
                if j_sug not in suggestions:
                    suggestions.append(j_sug)

        # Composite Weighted Score
        overall = (
            (routing_score * 0.30) +
            (schema_score * 0.25) +
            (accuracy_score * 0.25) +
            (visual_score * 0.15) +
            (latency_score * 0.05)
        )
        
        is_passed = (overall >= 75.0) and (routing_score >= 80.0) and (raw_error is None)

        return EvaluationRubricScore(
            routing_score=round(routing_score, 1),
            schema_score=round(schema_score, 1),
            accuracy_score=round(accuracy_score, 1),
            visual_score=round(visual_score, 1),
            latency_score=round(latency_score, 1),
            overall_score=round(overall, 1),
            is_passed=is_passed,
            judge_rationale=judge_rationale,
            issues_detected=issues,
            suggestions=suggestions
        )

    def _run_llm_judge(
        self,
        test_case: TestCase,
        response_text: str,
        routed_subagent: str,
        thoughts: List[str],
        visual_artifacts: VisualArtifacts
    ) -> Optional[Dict[str, Any]]:
        """Invokes Gemini as an impartial evaluator judge."""
        model = self._get_judge_model()
        if not model:
            return None

        prompt = f"""
You are the Chief AI Quality Assurance Judge for a Multi-Agent Gaming Analytics platform.
Evaluate the response of the gaming analytics agent against the user prompt and testing criteria.

### USER PROMPT:
"{test_case.prompt}"

### TARGET CATEGORY & EXPECTED SUBAGENT:
Category: {test_case.category.value}
Expected Subagent: {test_case.expected_subagent.value}
Actual Routed Subagent: {routed_subagent}

### AGENT REASONING THOUGHTS:
{json.dumps(thoughts[-5:] if len(thoughts) > 5 else thoughts, indent=2)}

### AGENT FINAL TEXT RESPONSE:
\"\"\"{response_text[:3000]}\"\"\"

### VISUAL ARTIFACTS EMITTED:
- Table Emitted: {visual_artifacts.table_data is not None}
- Chart Emitted: {visual_artifacts.chart_config is not None}
- Graph Emitted: {visual_artifacts.graph_data is not None}
- Explore Link Emitted: {visual_artifacts.explore_url is not None}

### EVALUATION INSTRUCTIONS:
1. Rate the accuracy and completeness of the answer (0 to 100).
2. Check if the numbers, tables, clan names, or dashboard descriptions directly address the user prompt without hallucinations.
3. Check if formatting is clear, professional, and well-structured.
4. Output your evaluation strictly as a valid JSON object without markdown formatting.

Format:
{{
  "accuracy_score": 92.5,
  "judge_rationale": "Clear explanation of why this score was awarded...",
  "issues_detected": ["Specific omission or flaw 1", ...],
  "suggestions": ["Actionable improvement 1", ...]
}}
"""
        try:
            res = model.generate_content(prompt)
            raw_text = res.text.strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()
            return json.loads(raw_text)
        except Exception as e:
            print(f"DEBUG: LLM Judge evaluation failed: {e}")
            return None

    def generate_persona_prompt(
        self,
        persona: PersonaType,
        target_category: SubagentCategory,
        turn_index: int,
        history: List[Dict[str, str]]
    ) -> str:
        """
        Dynamically generates a realistic user query for a given persona and target conversation category.
        """
        persona_info = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS[PersonaType.DATA_ANALYST])
        
        # Turn 1 fallback presets if LLM fails or is fast
        if turn_index == 1 and not history:
            category_defaults = {
                SubagentCategory.METRICS_FAST: "What was total revenue, DAU, and Day 1 retention by game title over the last 30 days?",
                SubagentCategory.SOCIAL_GRAPH: "Who are the members of the Order of Titans clan, and who holds the leader role?",
                SubagentCategory.DASHBOARD_BUILDER: "Build a new LiveOps War Room dashboard with DAU and Total Revenue tiles.",
                SubagentCategory.DEEP_RESEARCH: "Analyze the relationship between top spending whales, their clan memberships, and overall revenue trends."
            }
            default_prompt = category_defaults.get(target_category, "Show total revenue by game over the last 30 days.")
            
        model = self._get_judge_model()
        if not model:
            if turn_index == 1:
                return default_prompt
            elif turn_index == 2:
                return "Break down those numbers by country and device platform."
            else:
                return "Can you show this as a chart for our executive review?"

        prompt_instructions = f"""
You are roleplaying as: {persona_info['name']}
Role: {persona_info['role_desc']}
Style: {persona_info['style']}

Task: Generate the next natural-language question in a multi-turn conversation with a Gaming Analytics AI.
Conversation Category: {target_category.value}
Current Turn: {turn_index}

### CONVERSATION HISTORY SO FAR:
{json.dumps(history, indent=2)}

### INSTRUCTIONS:
- If this is Turn 1, ask a strong, detailed question fitting your persona and category.
- If this is Turn 2+, ask an intelligent contextual follow-up that references specific numbers, clan names, tiles, or trends mentioned in the previous AI response.
- Keep it natural, realistic, and focused on gaming analytics (Looker metrics, Spanner clans/social graph, Looker dashboards, or deep strategic synthesis).
- Return ONLY the query string, without quotes or additional commentary.
"""
        try:
            res = model.generate_content(prompt_instructions)
            query = res.text.strip().strip('"').strip("'")
            return query if query else "What was total revenue over the last 30 days?"
        except Exception as e:
            print(f"DEBUG: Persona prompt generation error: {e}")
            if turn_index == 1:
                return "What was total revenue by game over the last 30 days?"
            return "Break down these findings by country and show as a bar chart."

    def generate_ai_test_cases(
        self,
        category: SubagentCategory,
        difficulty: str,
        user_intent: str,
        count: int = 3
    ) -> List[TestCase]:
        """
        Generates brand new test cases on the fly using Gemini.
        """
        model = self._get_judge_model()
        if not model:
            return []

        prompt = f"""
You are an expert QA Engineer designing test cases for a Multi-Agent Gaming Analytics platform.
Generate {count} distinct test cases based on the user's intent.

Category: {category.value}
Difficulty: {difficulty}
User Goal: {user_intent}

Available Schemas:
1. LookML Metrics: events.total_revenue, events.total_iap_revenue, events.total_ad_revenue, events.number_of_users, events.number_of_sesssions, events.d1_retention_rate, events.average_revenue_per_user, events.game_name ('Lookup Battle Royale', 'Lookerwood Farm'), events.country, events.device_platform.
2. Spanner Graph: Players (player_id, gamertag, region, account_level), Clans (clan_id, clan_name), ClanMemberships (role: Leader, Officer, Member), Friendships (initiator_id, acceptor_id).
3. Dashboard Builder: create_looker_dashboard, edit_looker_dashboard, tiles, filters.
4. Deep Research: Cross-domain multi-hop correlating telemetry with social networks.

Return a JSON list of test case objects strictly following this format:
[
  {{
    "title": "Short descriptive title",
    "description": "What this test verifies",
    "prompt": "Exact user question to test",
    "difficulty": "{difficulty}",
    "expected_subagent": "{category.value}",
    "table_required": true,
    "chart_required": false,
    "graph_required": false,
    "link_required": true,
    "dashboard_required": false,
    "must_contain_keywords": ["keyword1", "keyword2"],
    "tags": ["tag1", "tag2"]
  }}
]
Return ONLY the raw JSON array.
"""
        try:
            res = model.generate_content(prompt)
            raw_text = res.text.strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()
                
            raw_list = json.loads(raw_text)
            test_cases = []
            for item in raw_list:
                tc = TestCase(
                    category=category,
                    title=item.get("title", "AI Generated Test"),
                    description=item.get("description", ""),
                    difficulty=difficulty,
                    prompt=item.get("prompt", ""),
                    expected_subagent=category,
                    expected_artifacts={
                        "table_required": item.get("table_required", False),
                        "chart_required": item.get("chart_required", False),
                        "graph_required": item.get("graph_required", False),
                        "link_required": item.get("link_required", False),
                        "dashboard_required": item.get("dashboard_required", False),
                        "must_contain_keywords": item.get("must_contain_keywords", [])
                    },
                    tags=item.get("tags", ["ai_generated"])
                )
                test_cases.append(tc)
            return test_cases
        except Exception as e:
            print(f"DEBUG: Failed to generate AI test cases: {e}")
            return []

evaluator = EvaluationEngine()
