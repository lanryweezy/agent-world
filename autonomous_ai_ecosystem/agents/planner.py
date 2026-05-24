"""
Research Planner agent for the ASI-EVOLVE framework.

Inspired by "LoongFlow," this agent generates a strategic blueprint or plan
before the Researcher designs the code modification.
"""

from typing import Dict, Any, List
from .brain import AIBrain, ThoughtType
from ..core.logger import get_agent_logger

class ResearchPlanner:
    """
    Expert Research Strategist. Analyzes the task and history to build a
    logical blueprint for the upcoming design phase.
    """

    def __init__(self, agent_id: str, brain: AIBrain):
        self.agent_id = agent_id
        self.brain = brain
        self.logger = get_agent_logger(agent_id, "research_planner")

    async def generate_plan(
        self,
        task_description: str,
        cognition_context: List[Dict[str, Any]],
        historical_experience: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a strategic plan for the research task.
        """
        self.logger.info("Generating research plan blueprint...")

        input_data = {
            "task_description": task_description,
            "cognition_context": cognition_context,
            "historical_experience": historical_experience
        }

        template_id = "research_planning"
        if template_id not in self.brain.prompt_templates:
            from .brain import PromptTemplate
            self.brain.prompt_templates[template_id] = PromptTemplate(
                template_id=template_id,
                name="Autonomous Research Planning",
                template="""
You are an expert Research Director. Your goal is to create a strategic blueprint for improving the system.

Task Description:
{task_description}

Cognition Context (Prior Knowledge):
{cognition_context}

Historical Experience (Past Lessons):
{historical_experience}

Please provide a structured research plan:
1. "strategic_objective": The high-level goal of this iteration.
2. "proposed_approach": A logical description of the changes to be made.
3. "hypothesized_outcome": What do you expect to happen when this is executed?
4. "key_constraints": Technical or logical constraints to keep in mind.

Format your response as JSON.
""",
                variables=["task_description", "cognition_context", "historical_experience"],
                thought_type=ThoughtType.PLANNING,
                max_tokens=1500,
                temperature=0.6
            )

        thought = await self.brain.think(
            thought_type=ThoughtType.PLANNING,
            input_data=input_data,
            template_id=template_id
        )

        plan = thought.output
        self.logger.info(f"Research plan generated: {plan.get('strategic_objective')}")

        return plan
