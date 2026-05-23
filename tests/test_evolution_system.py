"""
Test for the ASI-EVOLVE framework integration.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from autonomous_ai_ecosystem.learning.evolution_orchestrator import EvolutionOrchestrator
from autonomous_ai_ecosystem.agents.code_modifier import CodeModifier
from autonomous_ai_ecosystem.agents.sandbox import CodeSandbox, ExecutionResult, ExecutionStatus
from autonomous_ai_ecosystem.agents.analyzer import StructuredAnalyzer
from autonomous_ai_ecosystem.knowledge.cognition_base import CognitionBase
from autonomous_ai_ecosystem.agents.brain import ThoughtProcess, ThoughtType

@pytest.mark.asyncio
async def test_evolution_cycle():
    # Mock components
    code_modifier = MagicMock(spec=CodeModifier)
    code_modifier.design_modification = AsyncMock(return_value={
        "modification_id": "test_mod_1",
        "motivation": "Test motivation",
        "proposed_code": "def new_func(): pass",
        "confidence": 0.9
    })
    code_modifier.apply_modification = AsyncMock()

    sandbox = MagicMock(spec=CodeSandbox)
    sandbox.execute_code = AsyncMock(return_value=ExecutionResult(
        execution_id="test_exec_1",
        status=ExecutionStatus.SUCCESS,
        stdout="Test output"
    ))

    analyzer = MagicMock(spec=StructuredAnalyzer)
    analyzer.analyze_experiment = AsyncMock(return_value={
        "analysis": "Test analysis",
        "insights": ["Insight 1"],
        "lessons_learned": ["Lesson 1"],
        "suggested_next_steps": ["Step 1"],
        "confidence": 0.9
    })

    cognition_base = MagicMock(spec=CognitionBase)
    cognition_base.initialize = AsyncMock()
    cognition_base.retrieve_relevant = AsyncMock(return_value=[{"content": "Prior knowledge"}])

    orchestrator = EvolutionOrchestrator(
        "test_evolve",
        code_modifier,
        sandbox,
        analyzer,
        cognition_base
    )

    await orchestrator.initialize()

    # Run one round of evolution
    await orchestrator.start_evolution(
        target_file="test_file.py",
        task_description="Improve performance",
        max_rounds=1
    )

    # Verify calls
    cognition_base.retrieve_relevant.assert_called_once()
    code_modifier.design_modification.assert_called_once()
    sandbox.execute_code.assert_called_once()
    analyzer.analyze_experiment.assert_called_once()
    code_modifier.apply_modification.assert_called_once_with("test_mod_1")

    assert orchestrator.evolution_rounds == 1
    assert len(orchestrator.historical_experience) == 1
