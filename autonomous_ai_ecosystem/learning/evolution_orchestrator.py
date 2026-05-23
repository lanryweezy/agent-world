"""
Evolution Orchestrator for the ASI-EVOLVE framework.

Coordinates the Learn-Design-Experiment-Analyze cycle to achieve
continuous autonomous self-improvement of the AI ecosystem.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from ..agents.code_modifier import CodeModifier
from ..agents.sandbox import CodeSandbox
from ..agents.analyzer import StructuredAnalyzer
from ..knowledge.cognition_base import CognitionBase

class EvolutionOrchestrator(AgentModule):
    """
    Orchestrates the end-to-end evolution loop.
    """

    def __init__(
        self,
        agent_id: str,
        code_modifier: CodeModifier,
        sandbox: CodeSandbox,
        analyzer: StructuredAnalyzer,
        cognition_base: CognitionBase
    ):
        super().__init__(agent_id)
        self.code_modifier = code_modifier
        self.sandbox = sandbox
        self.analyzer = analyzer
        self.cognition_base = cognition_base
        self.logger = get_agent_logger(agent_id, "evolution_orchestrator")

        self.is_evolving = False
        self.evolution_rounds = 0
        self.historical_experience = []

    async def initialize(self):
        """Initialize the evolution orchestrator."""
        self.logger.info("Initializing Evolution Orchestrator...")
        self.analyzer.register_template()
        await self.cognition_base.initialize()

    async def start_evolution(self, target_file: str, task_description: str, max_rounds: int = 5):
        """Start the evolution loop."""
        self.is_evolving = True
        self.logger.info(f"Starting evolution loop for {target_file}...")

        for r in range(max_rounds):
            if not self.is_evolving:
                break

            self.evolution_rounds += 1
            self.logger.info(f"--- Evolution Round {self.evolution_rounds} ---")

            # 1. LEARN: Retrieve relevant cognition
            cognition = await self.cognition_base.retrieve_relevant(task_description)

            # 2. DESIGN: Propose a modification
            design_result = await self.code_modifier.design_modification(
                target_file=target_file,
                task_description=task_description,
                cognition_context=cognition,
                historical_experience=self.historical_experience
            )

            # 3. EXPERIMENT: Test in sandbox
            test_results = await self.sandbox.execute_code(
                code=design_result["proposed_code"],
                # In a real scenario, we'd provide test cases here
            )

            # 4. ANALYZE: Distill insights
            analysis = await self.analyzer.analyze_experiment(
                program_code=design_result["proposed_code"],
                execution_result=test_results.__dict__,
                context={"round": self.evolution_rounds, "task": task_description}
            )

            # Record experience for next rounds
            experience_node = {
                "round": self.evolution_rounds,
                "motivation": design_result["motivation"],
                "status": test_results.status.value,
                "analysis": analysis["analysis"],
                "lessons": analysis["lessons_learned"]
            }
            self.historical_experience.append(experience_node)

            # Apply if successful and safe
            if test_results.status.value == "success" and analysis["confidence"] > 0.7:
                self.logger.info(f"Round {self.evolution_rounds} SUCCESS. Applying modification.")
                await self.code_modifier.apply_modification(design_result["modification_id"])
            else:
                self.logger.warning(f"Round {self.evolution_rounds} failed or low confidence. Skipping application.")

            log_agent_event(
                self.agent_id,
                "evolution_round_completed",
                {
                    "round": self.evolution_rounds,
                    "status": test_results.status.value,
                    "confidence": analysis["confidence"]
                }
            )

        self.is_evolving = False
        self.logger.info("Evolution loop finished.")

    async def stop_evolution(self):
        """Stop the evolution loop."""
        self.is_evolving = False
        self.logger.info("Evolution loop stop requested.")

    async def shutdown(self):
        """Shutdown the evolution orchestrator."""
        await self.stop_evolution()
        await self.cognition_base.save_data()
        self.logger.info("Evolution Orchestrator shutdown.")
