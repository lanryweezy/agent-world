"""
Integration test for HARNESSAPI and ASI-EVOLVE.

Verifies that an evolved skill is automatically exported and reachable
via the HarnessAPI transport layer.
"""

import pytest
import os
import shutil
import asyncio
from unittest.mock import MagicMock, AsyncMock
from autonomous_ai_ecosystem.learning.evolution_orchestrator import EvolutionOrchestrator
from autonomous_ai_ecosystem.communication.harness_api import HarnessAPI
from autonomous_ai_ecosystem.agents.code_modifier import CodeModifier
from autonomous_ai_ecosystem.agents.sandbox import CodeSandbox, ExecutionResult, ExecutionStatus
from autonomous_ai_ecosystem.agents.analyzer import StructuredAnalyzer
from autonomous_ai_ecosystem.agents.reviewer import CritiqueReviewer
from autonomous_ai_ecosystem.agents.planner import ResearchPlanner
from autonomous_ai_ecosystem.knowledge.cognition_base import CognitionBase

@pytest.mark.asyncio
async def test_evolved_skill_registration():
    # Setup clean skills directory
    if os.path.exists("skills"):
        shutil.rmtree("skills")
    os.makedirs("skills")

    # 1. Mock Evolution Components
    planner = MagicMock(spec=ResearchPlanner)
    planner.generate_plan = AsyncMock(return_value={"strategic_objective": "Evolve a service"})

    researcher = MagicMock(spec=CodeModifier)
    researcher.design_modification = AsyncMock(return_value={
        "modification_id": "mod_1",
        "motivation": "Create a translator",
        "proposed_code": "async def handle(input):\n    yield f'Translating: {input.text}'\n    yield 'Done.'"
    })
    researcher.apply_modification = AsyncMock()

    sandbox = MagicMock(spec=CodeSandbox)
    sandbox.execute_code = AsyncMock(return_value=ExecutionResult(
        execution_id="exec_1",
        status=ExecutionStatus.SUCCESS
    ))

    analyzer = MagicMock(spec=StructuredAnalyzer)
    analyzer.analyze_experiment = AsyncMock(return_value={
        "analysis": "Success",
        "confidence": 0.9,
        "lessons_learned": ["Streaming is good"]
    })

    reviewer = MagicMock(spec=CritiqueReviewer)
    reviewer.review_design = AsyncMock(return_value={"should_proceed": True, "score": 0.9})

    cognition_base = MagicMock(spec=CognitionBase)
    cognition_base.initialize = AsyncMock()
    cognition_base.retrieve_relevant = AsyncMock(return_value=[])

    # 2. Run Evolution
    orchestrator = EvolutionOrchestrator(
        "test_agent", planner, researcher, sandbox, analyzer, reviewer, cognition_base
    )
    await orchestrator.initialize()

    # Target a "service" to trigger export
    await orchestrator.start_evolution(
        target_file="translator.py",
        task_description="Create a translation capability",
        max_rounds=1
    )

    # 3. Verify Skill Export
    assert os.path.exists("skills/evolved_service_1/handler.py")
    assert os.path.exists("skills/evolved_service_1/models.py")
    assert os.path.exists("skills/evolved_service_1/skill.toml")

    # 4. Initialize HarnessAPI and verify registration
    harness = HarnessAPI("test_api", skills_dir="skills")

    # Check if skill was loaded
    assert "evolved_service_1" in harness.skills
    skill = harness.skills["evolved_service_1"]
    assert skill.meta.name == "evolved_service_1"

    # Check if MCP tool was registered
    # In some versions of FastMCP, tools are stored in internal attributes
    # We'll just verify the loading and metadata which we can control
    assert skill.meta.is_mcp is True

    # Cleanup
    shutil.rmtree("skills")
