"""
ReflectionEngine for meta-cognitive abilities.

This module allows an agent to reflect on its own performance to generate
actionable insights for self-improvement, inspired by the MetaAgent paper.
"""

import asyncio
from typing import Dict, Any, Optional, List

from ..core.interfaces import AgentModule, Memory
from ..agents.memory import MemorySystem
from ..agents.brain import AIBrain


class ReflectionEngine(AgentModule):
    """
    A module for an agent to perform self-reflection and verified reflection.
    """

    def __init__(self, agent_id: str, brain: AIBrain, memory: MemorySystem):
        """
        Initializes the ReflectionEngine.

        Args:
            agent_id: The ID of the agent.
            brain: The AI brain for generating reflective insights.
            memory: The memory system to store and retrieve experiences.
        """
        super().__init__(agent_id)
        self.brain = brain
        self.memory = memory

    async def initialize(self) -> None:
        """Initializes the reflection engine."""
        # No complex initialization required for this module yet.
        pass

    async def shutdown(self) -> None:
        """Shuts down the reflection engine."""
        # No resources to release.
        pass

    async def self_reflect(self, task: Dict[str, Any], outcome: Dict[str, Any]) -> Optional[str]:
        """
        Performs self-reflection on a task without ground truth.
        The agent reviews its own reasoning and actions to find potential flaws or
        areas for improvement.

        Args:
            task: A dictionary describing the completed task.
            outcome: A dictionary describing the outcome of the task.

        Returns:
            A string containing the distilled experience, or None if no significant
            insight was gained.
        """
        prompt = f"""
        I am an autonomous AI agent. I have just completed a task and need to reflect on my performance.
        This is a self-reflection, meaning I do not have a ground-truth answer to compare against.
        I must critically evaluate my own process.

        Task Description: {task.get('description', 'N/A')}
        My Actions: {outcome.get('actions_taken', [])}
        My Reasoning: {outcome.get('reasoning_trace', 'N/A')}
        Final Result: {outcome.get('result', 'N/A')}

        Based on this, please answer the following questions:
        1.  Did I have any moments of uncertainty in my reasoning?
        2.  Could my actions have been more efficient?
        3.  Did I miss any potential edge cases or alternative approaches?
        4.  What is the single most important lesson I can learn from this experience?

        Distill this into a concise, generalizable principle or strategy for future tasks.
        Format the output as a single paragraph of "experience".
        Example: "When researching a topic with multiple facets, it's crucial to synthesize information from at least three different sources to avoid bias."
        """

        experience_text = await self.brain.generate_text(prompt, max_tokens=200)

        if experience_text:
            await self._store_experience(experience_text, "self_reflection")
            return experience_text

        return None

    async def verified_reflect(
        self, task: Dict[str, Any], outcome: Dict[str, Any], ground_truth: Any
    ) -> Optional[str]:
        """
        Performs verified reflection by comparing the outcome to a ground truth.
        This helps the agent learn from both successes and failures.

        Args:
            task: A dictionary describing the completed task.
            outcome: A dictionary describing the outcome of the task.
            ground_truth: The correct or desired outcome.

        Returns:
            A string containing the distilled experience, or None if no significant
            insight was gained.
        """
        is_success = outcome.get("result") == ground_truth

        prompt = f"""
        I am an autonomous AI agent. I have just completed a task and have access to the ground-truth answer.
        I need to reflect on my performance.

        Task Description: {task.get('description', 'N/A')}
        My Result: {outcome.get('result', 'N/A')}
        Ground Truth: {ground_truth}
        Success: {'Yes' if is_success else 'No'}

        My Reasoning: {outcome.get('reasoning_trace', 'N/A')}

        Analyze the entire process.
        If I succeeded, what was the key to my success? What strategy should I always use in similar situations?
        If I failed, what was the root cause of my failure? What specific cognitive bias or reasoning flaw led me astray?

        Distill this into a concise, generalizable principle or strategy for future tasks.
        Format the output as a single paragraph of "experience".
        Example: "For multi-step calculation problems, always double-check each intermediate result before proceeding, as a small error can cascade."
        """

        experience_text = await self.brain.generate_text(prompt, max_tokens=200)

        if experience_text:
            await self._store_experience(experience_text, "verified_reflection", is_success=is_success)
            return experience_text

        return None

    async def _store_experience(self, experience_text: str, reflection_type: str, is_success: bool = True) -> None:
        """
        Stores a distilled experience in the agent's memory.
        """
        from datetime import datetime
        import uuid

        tags = ["experience", reflection_type]
        if not is_success:
            tags.append("failure")

        experience_memory = Memory(
            memory_id=f"mem-exp-{uuid.uuid4()}",
            content=experience_text,
            memory_type="procedural", # Experiences become procedural knowledge
            importance=0.8 if is_success else 0.9, # Failures are very important to remember
            timestamp=datetime.now(),
            agent_id=self.agent_id,
            tags=tags,
        )
        await self.memory.store_memory(experience_memory)
