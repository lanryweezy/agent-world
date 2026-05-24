"""
Consensus module for system-level changes in the ASI-EVOLVE framework.

Ensures that modifications to the core evolution orchestrator or other
critical system components require agreement from multiple specialized agents.
"""

from typing import Dict, Any, List
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from ..agents.reviewer import CritiqueReviewer
from ..agents.planner import ResearchPlanner

class MultiAgentConsensus(AgentModule):
    """
    Manages the consensus process between specialized agents for
    high-impact system modifications.
    """

    def __init__(self, agent_id: str, reviewer: CritiqueReviewer, planner: ResearchPlanner):
        super().__init__(agent_id)
        self.reviewer = reviewer
        self.planner = planner
        self.logger = get_agent_logger(agent_id, "consensus_module")

    async def evaluate_system_change(self, proposal: Dict[str, Any]) -> bool:
        """
        Evaluate a proposed system-level change through multi-agent consensus.
        """
        self.logger.info(f"Evaluating system change consensus for: {proposal.get('target_element')}")

        # 1. Reviewer's Assessment
        review = await self.reviewer.review_design(
            proposed_code=proposal.get("proposed_code", ""),
            motivation=proposal.get("motivation", ""),
            task_description="High-Impact System Modification"
        )

        # 2. Planner's Assessment
        # (Conceptual: use the brain to check if the approach aligns with strategic goals)
        plan_check = await self.planner.brain.think(
            thought_type=self.planner.brain.ThoughtType.ANALYSIS,
            input_data={
                "proposal": proposal,
                "review": review
            },
            template_id="consensus_strategic_alignment"
        )

        is_aligned = plan_check.output.get("is_strategically_aligned", False)
        is_safe = review.get("should_proceed", False)

        consensus_reached = is_aligned and is_safe

        log_agent_event(
            self.agent_id,
            "consensus_evaluation_completed",
            {"consensus_reached": consensus_reached, "safe": is_safe, "aligned": is_aligned}
        )

        if consensus_reached:
            self.logger.info("Consensus REACHED for system change.")
        else:
            self.logger.warning("Consensus FAILED for system change.")

        return consensus_reached

    async def initialize(self):
        """Initialize the consensus module."""
        self.logger.info("Multi-Agent Consensus Module initialized.")

    async def shutdown(self):
        """Shutdown the consensus module."""
        self.logger.info("Consensus Module shutdown.")
