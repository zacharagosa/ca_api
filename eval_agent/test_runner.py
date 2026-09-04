"""
Execution Runner for Test Suites, Single Tests, and Dynamic Persona Dialogues.
"""
import os
import time
import json
import uuid
import requests
from typing import List, Dict, Any, Generator, Optional
from eval_agent.models import (
    TestCase, TestResult, TestStatus, TestSuiteRun, VisualArtifacts,
    SubagentCategory, PersonaType, DynamicSimulationResult, SimulationTurnResult
)
from eval_agent.evaluator import evaluator, PERSONA_PROMPTS
from eval_agent.storage import storage
from eval_agent.test_suites import ALL_TEST_CASES, get_test_case_by_id

DEFAULT_AGENT_ENDPOINT = os.getenv("AGENT_BACKEND_URL", "http://127.0.0.1:8080/chat")

class TestRunner:
    def __init__(self, backend_url: str = DEFAULT_AGENT_ENDPOINT):
        self.backend_url = backend_url

    def run_single_test_streaming(
        self,
        test_case: TestCase,
        session_id: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, TestResult]:
        """
        Executes a single test case against the Gaming Analytics Agent and yields real-time progress events.
        """
        if not session_id:
            session_id = f"eval_sess_{test_case.id}_{uuid.uuid4().hex[:6]}"

        t0 = time.time()
        time_to_first_thought = 0.0
        time_to_first_token = 0.0
        
        routed_subagent = "unknown"
        thoughts: List[str] = []
        text_chunks: List[str] = []
        side_events: List[Dict[str, Any]] = []
        
        visual_artifacts = VisualArtifacts()
        raw_error = None

        yield {
            "type": "test_started",
            "test_id": test_case.id,
            "title": test_case.title,
            "category": test_case.category.value,
            "prompt": test_case.prompt,
            "session_id": session_id
        }

        payload = {
            "message": test_case.prompt,
            "session_id": session_id,
            "user_id": "eval_test_runner",
            "agent_type": "auto",
            "force_refresh": True
        }

        try:
            resp = requests.post(
                self.backend_url,
                json=payload,
                stream=True,
                timeout=test_case.timeout_seconds
            )
            
            if resp.status_code != 200:
                raw_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                yield {"type": "error", "message": raw_error}
            else:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    decoded = line.decode('utf-8')
                    current_time = time.time() - t0

                    # 1. Thought Stream
                    if decoded.startswith("THOUGHT: "):
                        thought_content = decoded[len("THOUGHT: "):].strip()
                        if thought_content:
                            if time_to_first_thought == 0.0:
                                time_to_first_thought = current_time
                            thoughts.append(thought_content)
                            yield {
                                "type": "thought",
                                "test_id": test_case.id,
                                "content": thought_content,
                                "elapsed": round(current_time, 2)
                            }

                    # 2. Side-channel / Data Stream
                    elif decoded.startswith("DATA: "):
                        data_str = decoded[len("DATA: "):].strip()
                        try:
                            data_obj = json.loads(data_str)
                            side_events.append(data_obj)
                            dtype = data_obj.get("type")

                            if dtype == "subagent_routed":
                                routed_subagent = data_obj.get("subagent") or data_obj.get("name") or "unknown"
                                yield {
                                    "type": "subagent_routed",
                                    "test_id": test_case.id,
                                    "subagent": routed_subagent,
                                    "name": data_obj.get("name"),
                                    "icon": data_obj.get("icon"),
                                    "description": data_obj.get("description")
                                }
                            elif dtype == "json_table":
                                visual_artifacts.table_data = data_obj.get("data")
                                yield {
                                    "type": "artifact_table",
                                    "test_id": test_case.id,
                                    "data": data_obj.get("data")
                                }
                            elif dtype == "json_chart":
                                visual_artifacts.chart_config = data_obj.get("config")
                                yield {
                                    "type": "artifact_chart",
                                    "test_id": test_case.id,
                                    "config": data_obj.get("config")
                                }
                            elif dtype == "json_graph":
                                visual_artifacts.graph_data = data_obj.get("graphData")
                                yield {
                                    "type": "artifact_graph",
                                    "test_id": test_case.id,
                                    "graphData": data_obj.get("graphData")
                                }
                            elif dtype == "json_link":
                                visual_artifacts.explore_url = data_obj.get("url")
                                yield {
                                    "type": "artifact_link",
                                    "test_id": test_case.id,
                                    "url": data_obj.get("url")
                                }
                            elif dtype == "json_dashboard_created":
                                visual_artifacts.dashboard_info = data_obj.get("dashboard")
                                yield {
                                    "type": "artifact_dashboard",
                                    "test_id": test_case.id,
                                    "dashboard": data_obj.get("dashboard")
                                }
                            else:
                                # Generic text or other payload
                                if time_to_first_token == 0.0:
                                    time_to_first_token = current_time
                                text_chunks.append(data_str)
                                yield {
                                    "type": "chunk",
                                    "test_id": test_case.id,
                                    "text": data_str
                                }
                        except Exception:
                            # Not a JSON blob, treat as pure text
                            if time_to_first_token == 0.0:
                                time_to_first_token = current_time
                            text_chunks.append(data_str)
                            yield {
                                "type": "chunk",
                                "test_id": test_case.id,
                                "text": data_str
                            }

                    # 3. Legacy data: chunk stream
                    elif decoded.startswith("data: "):
                        content = decoded[len("data: "):].strip()
                        if time_to_first_token == 0.0:
                            time_to_first_token = current_time
                        try:
                            chunk_obj = json.loads(content)
                            if isinstance(chunk_obj, dict):
                                if "text" in chunk_obj:
                                    txt = chunk_obj["text"]
                                    text_chunks.append(txt)
                                    yield {"type": "chunk", "test_id": test_case.id, "text": txt}
                                elif "content" in chunk_obj and "parts" in chunk_obj["content"]:
                                    for p in chunk_obj["content"]["parts"]:
                                        if "text" in p:
                                            txt = p["text"]
                                            text_chunks.append(txt)
                                            yield {"type": "chunk", "test_id": test_case.id, "text": txt}
                        except Exception:
                            text_chunks.append(content)
                            yield {"type": "chunk", "test_id": test_case.id, "text": content}

        except Exception as e:
            raw_error = str(e)
            yield {"type": "error", "message": raw_error}

        duration = time.time() - t0
        full_response_text = "".join(text_chunks).strip()

        # Fallback routing inference from thoughts or prompt classifier if needed
        if routed_subagent == "unknown":
            thought_blob = " ".join(thoughts).lower()
            if "metrics analyst" in thought_blob or "looker metrics" in thought_blob:
                routed_subagent = "metrics_fast"
            elif "social graph" in thought_blob or "spanner graph" in thought_blob:
                routed_subagent = "social_graph"
            elif "dashboard architect" in thought_blob or "dashboard builder" in thought_blob:
                routed_subagent = "dashboard_builder"
            elif "deep research" in thought_blob:
                routed_subagent = "deep_research"
            else:
                try:
                    import agent
                    classified = agent.classify_subagent_route(test_case.prompt)
                    routed_subagent = classified.get("subagent", "metrics_fast")
                except Exception:
                    routed_subagent = "metrics_fast"

        # Run Rubric and LLM Judge Evaluation
        rubric = evaluator.evaluate_response(
            test_case=test_case,
            response_text=full_response_text,
            routed_subagent=routed_subagent,
            thoughts=thoughts,
            visual_artifacts=visual_artifacts,
            duration_seconds=duration,
            raw_error=raw_error
        )

        test_status = TestStatus.PASSED if rubric.is_passed else TestStatus.FAILED
        if raw_error:
            test_status = TestStatus.ERROR

        result = TestResult(
            test_id=test_case.id,
            test_title=test_case.title,
            category=test_case.category,
            prompt=test_case.prompt,
            status=test_status,
            routed_subagent=routed_subagent,
            expected_subagent=test_case.expected_subagent.value,
            duration_seconds=round(duration, 2),
            time_to_first_thought=round(time_to_first_thought, 2),
            time_to_first_token=round(time_to_first_token, 2),
            response_text=full_response_text,
            thoughts=thoughts,
            side_events=side_events,
            visual_artifacts=visual_artifacts,
            rubric=rubric,
            raw_error=raw_error
        )

        yield {
            "type": "test_completed",
            "test_id": test_case.id,
            "status": result.status.value,
            "result": result.model_dump()
        }

        return result

    def run_suite_streaming(
        self,
        test_cases: List[TestCase],
        run_title: str = "Test Suite Run"
    ) -> Generator[Dict[str, Any], None, TestSuiteRun]:
        """
        Executes a full list of test cases in sequence and yields live progress.
        """
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        t_start = time.time()
        
        yield {
            "type": "suite_started",
            "run_id": run_id,
            "title": run_title,
            "total_tests": len(test_cases)
        }

        results: List[TestResult] = []
        for i, tc in enumerate(test_cases):
            yield {
                "type": "suite_progress",
                "run_id": run_id,
                "current_index": i + 1,
                "total_tests": len(test_cases),
                "current_test_id": tc.id,
                "current_test_title": tc.title
            }
            
            # Execute test stream
            gen = self.run_single_test_streaming(tc)
            res = None
            try:
                while True:
                    event = next(gen)
                    yield event
            except StopIteration as e:
                res = e.value
                
            if res:
                results.append(res)

        total_duration = time.time() - t_start
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.rubric.is_passed)
        failed_tests = sum(1 for r in results if not r.rubric.is_passed and r.status != TestStatus.ERROR)
        error_tests = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        pass_rate = round((passed_tests / total_tests * 100.0) if total_tests > 0 else 0.0, 1)
        avg_latency = round((sum(r.duration_seconds for r in results) / total_tests) if total_tests > 0 else 0.0, 2)
        routing_matches = sum(1 for r in results if r.rubric.routing_score >= 80.0)
        routing_accuracy = round((routing_matches / total_tests * 100.0) if total_tests > 0 else 0.0, 1)
        
        has_payloads = sum(1 for r in results if (
            r.visual_artifacts.table_data or 
            r.visual_artifacts.chart_config or 
            r.visual_artifacts.graph_data or 
            r.visual_artifacts.explore_url or 
            r.visual_artifacts.dashboard_info
        ))
        visual_payload_rate = round((has_payloads / total_tests * 100.0) if total_tests > 0 else 0.0, 1)
        
        avg_reliability = round((sum(r.rubric.overall_score for r in results) / total_tests) if total_tests > 0 else 0.0, 1)

        # Category Breakdown
        category_breakdown = {}
        for cat in SubagentCategory:
            cat_results = [r for r in results if r.category == cat]
            if cat_results:
                c_passed = sum(1 for r in cat_results if r.rubric.is_passed)
                category_breakdown[cat.value] = {
                    "total": len(cat_results),
                    "passed": c_passed,
                    "failed": len(cat_results) - c_passed,
                    "pass_rate": round(c_passed / len(cat_results) * 100.0, 1),
                    "avg_latency": round(sum(r.duration_seconds for r in cat_results) / len(cat_results), 2),
                    "avg_score": round(sum(r.rubric.overall_score for r in cat_results) / len(cat_results), 1)
                }

        suite_run = TestSuiteRun(
            run_id=run_id,
            title=run_title,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            warning_tests=error_tests,
            pass_rate=pass_rate,
            avg_latency_seconds=avg_latency,
            routing_accuracy_pct=routing_accuracy,
            visual_payload_rate_pct=visual_payload_rate,
            overall_reliability_score=avg_reliability,
            category_breakdown=category_breakdown,
            results=results,
            started_at=t_start,
            completed_at=time.time(),
            duration_seconds=round(total_duration, 2)
        )

        # Persist run
        storage.save_run(suite_run)

        yield {
            "type": "suite_completed",
            "run": suite_run.model_dump()
        }

        return suite_run

    def simulate_dynamic_dialogue_streaming(
        self,
        persona: PersonaType,
        target_category: SubagentCategory,
        total_turns: int = 3
    ) -> Generator[Dict[str, Any], None, DynamicSimulationResult]:
        """
        Autonomously runs a multi-turn conversation where the Testing Agent plays a synthetic persona
        and generates context-aware follow-up questions dynamically based on the Gaming Analytics Agent's prior answers.
        """
        sim_id = f"sim_{uuid.uuid4().hex[:8]}"
        session_id = f"sim_sess_{sim_id}"
        persona_meta = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS[PersonaType.DATA_ANALYST])
        
        t0 = time.time()
        yield {
            "type": "simulation_started",
            "simulation_id": sim_id,
            "persona": persona.value,
            "persona_name": persona_meta["name"],
            "target_category": target_category.value,
            "total_turns": total_turns
        }

        conversation_history: List[Dict[str, str]] = []
        turn_results: List[SimulationTurnResult] = []

        for turn_idx in range(1, total_turns + 1):
            yield {
                "type": "simulation_turn_started",
                "turn": turn_idx,
                "total_turns": total_turns
            }

            # 1. Tester Agent generates persona prompt
            user_prompt = evaluator.generate_persona_prompt(
                persona=persona,
                target_category=target_category,
                turn_index=turn_idx,
                history=conversation_history
            )

            yield {
                "type": "persona_query_generated",
                "turn": turn_idx,
                "persona": persona.value,
                "persona_name": persona_meta["name"],
                "prompt": user_prompt
            }

            # 2. Build ad-hoc TestCase for this turn
            turn_test_case = TestCase(
                id=f"{sim_id}_turn_{turn_idx}",
                category=target_category,
                title=f"Turn {turn_idx}: {user_prompt[:40]}...",
                description=f"Multi-turn dynamic simulation turn {turn_idx} for persona {persona.value}",
                prompt=user_prompt,
                expected_subagent=target_category,
                expected_artifacts={
                    "table_required": False,
                    "chart_required": False,
                    "graph_required": (target_category == SubagentCategory.SOCIAL_GRAPH),
                    "link_required": False,
                    "dashboard_required": (target_category == SubagentCategory.DASHBOARD_BUILDER)
                }
            )

            # 3. Stream query to Gaming Analytics Agent
            turn_gen = self.run_single_test_streaming(turn_test_case, session_id=session_id)
            turn_test_res = None
            try:
                while True:
                    evt = next(turn_gen)
                    evt["simulation_turn"] = turn_idx
                    yield evt
            except StopIteration as e:
                turn_test_res = e.value

            if turn_test_res:
                turn_sim = SimulationTurnResult(
                    turn=turn_idx,
                    user_prompt=user_prompt,
                    agent_response=turn_test_res.response_text,
                    routed_subagent=turn_test_res.routed_subagent,
                    thoughts=turn_test_res.thoughts,
                    visual_artifacts=turn_test_res.visual_artifacts,
                    rubric=turn_test_res.rubric,
                    duration_seconds=turn_test_res.duration_seconds
                )
                turn_results.append(turn_sim)

                # Record in history for subsequent turns
                conversation_history.append({"role": "user", "content": user_prompt})
                conversation_history.append({"role": "model", "content": turn_test_res.response_text})

                yield {
                    "type": "simulation_turn_completed",
                    "turn": turn_idx,
                    "turn_result": turn_sim.model_dump()
                }

        total_sim_duration = time.time() - t0
        avg_coherence = round(sum(tr.rubric.overall_score for tr in turn_results) / len(turn_results), 1) if turn_results else 0.0
        avg_accuracy = round(sum(tr.rubric.accuracy_score for tr in turn_results) / len(turn_results), 1) if turn_results else 0.0
        routing_correct = sum(1 for tr in turn_results if tr.rubric.routing_score >= 80.0)
        routing_precision = round((routing_correct / len(turn_results) * 100.0), 1) if turn_results else 0.0

        assessment = f"Dynamic Dialogue with {persona_meta['name']} across {len(turn_results)} turns completed with {avg_coherence}/100 composite score."

        sim_result = DynamicSimulationResult(
            simulation_id=sim_id,
            persona=persona,
            persona_name=persona_meta["name"],
            target_category=target_category,
            total_turns=len(turn_results),
            turns=turn_results,
            overall_coherence_score=avg_coherence,
            overall_accuracy_score=avg_accuracy,
            overall_routing_precision=routing_precision,
            final_assessment=assessment,
            duration_seconds=round(total_sim_duration, 2),
            executed_at=time.time()
        )

        storage.save_simulation(sim_result)

        yield {
            "type": "simulation_completed",
            "simulation": sim_result.model_dump()
        }

        return sim_result

test_runner = TestRunner()
