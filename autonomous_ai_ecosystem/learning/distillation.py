"""
Cross-Agent Knowledge Distillation for the ASI-EVOLVE framework.

Enables agents and islands to package their high-quality experiences into
compact 'Teacher Nodes' that other agents can learn from.
"""

from typing import List, Dict, Any, Optional
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from ..agents.brain import AIBrain, ThoughtType

class ResearchDistiller(AgentModule):
    """
    Distills high-scoring evolution nodes into generalized principles
    (Teacher Nodes) for cross-agent knowledge sharing.
    """

    def __init__(self, agent_id: str, brain: AIBrain):
        super().__init__(agent_id)
        self.brain = brain
        self.logger = get_agent_logger(agent_id, "research_distiller")
        self.teacher_nodes = []

    async def initialize(self):
        """Initialize the distiller."""
        self.logger.info("Research Distiller initialized.")

    async def distill_best_practices(self, successful_nodes: List[Any]) -> Dict[str, Any]:
        """
        Distill a set of successful trials into a compact 'Teacher Node'.
        """
        if not successful_nodes:
            return {}

        self.logger.info(f"Distilling {len(successful_nodes)} nodes into generalized knowledge...")

        input_data = {
            "successful_trials": [
                {"motivation": n.motivation, "lessons": n.analysis.get("lessons_learned", [])}
                for n in successful_nodes[:5]
            ]
        }

        template_id = "knowledge_distillation"
        if template_id not in self.brain.prompt_templates:
            from ..agents.brain import PromptTemplate
            self.brain.prompt_templates[template_id] = PromptTemplate(
                template_id=template_id,
                name="Research Knowledge Distillation",
                template="""
You are an expert Research Mentor. Analyze these successful evolution trials:

Successful Trials:
{successful_trials}

Please distill these specific successes into a generalized 'Teacher Node':
1. "core_principle": The single most important generalized principle discovered.
2. "best_practices": A list of 3-5 concrete best practices derived from these trials.
3. "applicability": Where else in the ecosystem could this knowledge be applied?
4. "metadata": tags for retrieval.

Format your response as JSON.
""",
                variables=["successful_trials"],
                thought_type=ThoughtType.ANALYSIS,
                max_tokens=1500,
                temperature=0.3
            )

        thought = await self.brain.think(
            thought_type=ThoughtType.ANALYSIS,
            input_data=input_data,
            template_id=template_id
        )

        teacher_node = thought.output
        self.teacher_nodes.append(teacher_node)

        log_agent_event(
            self.agent_id,
            "knowledge_distilled",
            {"principle": teacher_node.get("core_principle")}
        )

        return teacher_node

    async def shutdown(self):
        """Shutdown the distiller."""
        self.logger.info("Research Distiller shutdown.")
