"""
Autonomous Tester agent for the ASI-EVOLVE framework.

Autonomously generates unit tests and performance benchmarks for
successfully evolved code modules.
"""

from typing import Dict, Any, List
from .brain import AIBrain, ThoughtType
from ..core.logger import get_agent_logger, log_agent_event

class AutonomousTester:
    """
    Expert QA and Performance Engineer. Generates tests and benchmarks
    to validate and quantify the quality of evolved code.
    """

    def __init__(self, agent_id: str, brain: AIBrain):
        self.agent_id = agent_id
        self.brain = brain
        self.logger = get_agent_logger(agent_id, "autonomous_tester")

    async def generate_benchmark_suite(self, code: str, task_description: str) -> str:
        """
        Generate a Python test/benchmark suite for the given code.
        """
        self.logger.info("Generating autonomous benchmark suite...")

        input_data = {
            "code": code,
            "task_description": task_description
        }

        template_id = "test_generation"
        if template_id not in self.brain.prompt_templates:
            from .brain import PromptTemplate
            self.brain.prompt_templates[template_id] = PromptTemplate(
                template_id=template_id,
                name="Autonomous Test Generation",
                template="""
You are a Lead Software Test Engineer. Generate a comprehensive unit test and performance benchmark suite for the following code:

Task: {task_description}

Code:
{code}

Please provide:
1. Complete Python code using 'pytest' and 'timeit'.
2. Test cases for edge cases and typical usage.
3. A benchmark function that measures execution time and resource usage.

Format your response as a complete, runnable Python script.
""",
                variables=["task_description", "code"],
                thought_type=ThoughtType.PLANNING,
                max_tokens=3000,
                temperature=0.4
            )

        thought = await self.brain.think(
            thought_type=ThoughtType.PLANNING,
            input_data=input_data,
            template_id=template_id
        )

        test_code = thought.output.get("response", "# Test code generation failed.")
        if "```python" in test_code:
             test_code = test_code.split("```python")[1].split("```")[0]

        log_agent_event(self.agent_id, "benchmark_suite_generated", {"task": task_description})
        return test_code
