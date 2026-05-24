"""
End-to-End integration test for the Autonomous AI Research Factory.

Simulates a complete breakthrough lifecycle:
1. Research Task Submission via DiscoveryAPI
2. PES Planning (ResearchPlanner)
3. Design (Researcher/CodeModifier)
4. Peer Review Consensus (Reviewer/Planner)
5. Safe Experimentation (Engineer/Sandbox) with Anti-Fabrication Checks
6. Distillation (Analyzer)
7. Skill Export & Serving (HarnessAPI)
8. Commercialization Pipeline (GrowthOrchestrator)
9. Automated Reporting (ResearchJournal)
10. Meta-Optimization (MetaOptimizer)
"""

import pytest
import os
import shutil
import asyncio
from unittest.mock import MagicMock, AsyncMock
from autonomous_ai_ecosystem.learning.evolution_orchestrator import EvolutionOrchestrator
from autonomous_ai_ecosystem.communication.harness_api import HarnessAPI
from autonomous_ai_ecosystem.learning.growth_orchestrator import GrowthOrchestrator
from autonomous_ai_ecosystem.learning.meta_optimizer import MetaOptimizer
from autonomous_ai_ecosystem.agents.code_modifier import CodeModifier
from autonomous_ai_ecosystem.agents.sandbox import CodeSandbox, ExecutionResult, ExecutionStatus
from autonomous_ai_ecosystem.agents.analyzer import StructuredAnalyzer
from autonomous_ai_ecosystem.agents.reviewer import CritiqueReviewer
from autonomous_ai_ecosystem.agents.planner import ResearchPlanner
from autonomous_ai_ecosystem.agents.technical.specialists import create_technical_team
from autonomous_ai_ecosystem.agents.growth.specialists import create_growth_team
from autonomous_ai_ecosystem.knowledge.cognition_base import CognitionBase
from autonomous_ai_ecosystem.oversight.journal import ResearchJournal
from autonomous_ai_ecosystem.ui.discovery_api import DiscoveryAPI
from autonomous_ai_ecosystem.ui.evolution_dashboard import EvolutionDashboard

@pytest.mark.asyncio
async def test_full_factory_lifecycle():
    # Setup
    if os.path.exists("skills"): shutil.rmtree("skills")
    os.makedirs("skills")
    if os.path.exists("data/evolution"): shutil.rmtree("data/evolution")
    os.makedirs("data/evolution")

    # 1. Initialize Components
    brain = MagicMock()
    # Mock brain.think to handle different templates
    async def mock_think(thought_type, input_data, template_id=None, **kwargs):
        mock_output = {"confidence": 0.9}
        if template_id == "experimental_analysis":
             mock_output.update({"analysis": "Good result", "lessons_learned": ["lesson 1"], "insights": ["insight 1"]})
        elif template_id == "code_design":
             mock_output.update({"motivation": "better code", "proposed_code": "def handle(i): pass", "modification_type": "add_function"})
        elif template_id == "code_review":
             mock_output.update({"score": 0.9, "should_proceed": True, "critique": "safe"})
        elif template_id == "research_planning":
             mock_output.update({"strategic_objective": "win", "proposed_approach": "science"})
        elif "growth" in (template_id or ""):
             mock_output.update({"gtm_plan": "sell it", "copy": "buy it"})
        elif template_id == "meta_optimization":
             mock_output.update({"template_updates": {"test": "better"}, "rationale": "improved"})
        elif template_id == "idea_proposal":
             mock_output.update({"proposal": "new idea"})
        elif template_id == "idea_consensus":
             mock_output.update({"consensus": "best idea"})

        thought = MagicMock()
        thought.output = mock_output
        thought.confidence = 0.9
        return thought

    brain.think = mock_think
    brain.prompt_templates = {}

    # Infrastructure
    cognition_base = MagicMock()
    cognition_base.initialize = AsyncMock()
    cognition_base.retrieve_relevant = AsyncMock(return_value=[])
    cognition_base.save_data = AsyncMock()
    cognition_base.add_knowledge = AsyncMock()

    code_analyzer = MagicMock()
    code_analyzer.assess_modification_risk = AsyncMock(return_value={"risk_level": "safe", "should_allow": True})
    code_modifier = CodeModifier("test_researcher", code_analyzer, brain)
    sandbox = MagicMock()
    sandbox.execute_code = AsyncMock(return_value=ExecutionResult(
        execution_id="test_exec_1",
        status=ExecutionStatus.SUCCESS,
        stdout="Test output"
    ))

    analyzer = StructuredAnalyzer("test_analyzer", brain)
    reviewer = CritiqueReviewer("test_reviewer", brain)
    planner = ResearchPlanner("test_planner", brain)
    journal = ResearchJournal("test_journal", storage_path="autonomous_ai_ecosystem/oversight/reports")

    # Teams
    growth_team = create_growth_team("growth", brain)
    growth_orch = GrowthOrchestrator("test_growth_orch", growth_team)

    # 2. Initialize Evolution Orchestrator
    orch = EvolutionOrchestrator(
        "test_factory_orch", planner, code_modifier, sandbox, analyzer, reviewer, cognition_base
    )
    await orch.initialize()

    # 3. Discovery API
    api = DiscoveryAPI("test_api", orch)

    # 4. Meta-Optimizer
    meta_opt = MetaOptimizer("test_meta", brain, orch)

    # --- EXECUTE LIFECYCLE ---

    # A. Submit Task
    task_id = await api.submit_research_request("Improve sequence modeling", "brain.py")
    assert task_id.startswith("ext_task_")

    # B. Run Evolution Round
    # Simulating the trigger that usually comes from a background task
    node = await orch._execute_evolution_round("brain.py", "Improve sequence modeling and evolve a service")
    assert node is not None
    assert node.score > 0.5

    # C. Verify Skill Export
    assert os.path.exists("skills/evolved_service_1/handler.py")

    # D. Verify Reporting
    report_path = await journal.publish_report("Sequence Evolution", orch.database, node)
    assert os.path.exists(report_path)
    assert os.path.exists(report_path.replace(".md", ".jsonld"))

    # E. Run Growth Pipeline
    launch_result = await growth_orch.launch_capability(
        "Evolved Attention", "O(N) Attention model", {"accuracy": 0.95}
    )
    assert "gtm_plan" in launch_result
    assert "Evolved Attention" in growth_orch.commercial_history

    # F. Meta-Optimization
    # Add dummy history to trigger meta-opt
    for _ in range(5): orch.database.append(node)
    await meta_opt.run_meta_optimization()
    assert len(meta_opt.optimization_history) == 1

    # G. Verify UI Data
    dashboard_data = await EvolutionDashboard("test_db", orch, growth_orch).get_dashboard_data()
    assert dashboard_data["total_rounds"] >= 1
    assert "Evolved Attention" in dashboard_data["growth_pipeline"]

    # Cleanup
    shutil.rmtree("skills")
    shutil.rmtree("data/evolution")
    shutil.rmtree("autonomous_ai_ecosystem/oversight/reports")
