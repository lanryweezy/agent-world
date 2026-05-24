"""
Meta-Optimization agent for the ASI-EVOLVE framework.

Monitors the effectiveness of the evolution loop and proposes improvements
to the system's own prompt templates and parameters.
"""

from typing import Dict, Any, List
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from ..agents.brain import AIBrain, ThoughtType

class MetaOptimizer(AgentModule):
    """
    Agent that optimizes the Evolution Orchestrator. It acts as a
    "Prompt Engineer" and "Hyperparameter Tuner" for the evolution process.
    """

    def __init__(self, agent_id: str, brain: AIBrain, target_orchestrator: Any):
        super().__init__(agent_id)
        self.brain = brain
        self.target_orchestrator = target_orchestrator
        self.logger = get_agent_logger(agent_id, "meta_optimizer")
        self.optimization_history = []

    async def initialize(self):
        """Initialize the meta-optimizer."""
        self.logger.info("Meta-Optimizer initialized.")

    async def run_meta_optimization(self):
        """
        Analyze recent evolution history and propose system-level improvements.
        """
        self.logger.info("Starting meta-optimization cycle...")

        # Gather performance data from the target orchestrator
        history = self.target_orchestrator.database
        if len(history) < 5:
            self.logger.info("Insufficient history for meta-optimization.")
            return

        performance_data = [
            {"round": node.node_id, "score": node.score, "status": node.execution_result["status"]}
            for node in history[-10:]
        ]

        input_data = {
            "performance_history": performance_data,
            "current_templates": {
                k: v.template for k, v in self.brain.prompt_templates.items()
            }
        }

        template_id = "meta_optimization"
        if template_id not in self.brain.prompt_templates:
            from ..agents.brain import PromptTemplate
            self.brain.prompt_templates[template_id] = PromptTemplate(
                template_id=template_id,
                name="System Meta-Optimization",
                template="""
You are an Expert AI Systems Architect. Analyze the performance of our evolution system:

Performance History:
{performance_history}

Current Prompt Templates:
{current_templates}

Please propose optimizations to improve the success rate and quality of our self-evolution:
1. "template_updates": A dictionary of template_id -> improved_template_string.
2. "parameter_suggestions": Suggested changes to sampling strategy or other parameters.
3. "rationale": Explain why these changes will help.

Format your response as JSON.
""",
                variables=["performance_history", "current_templates"],
                thought_type=ThoughtType.REFLECTION,
                max_tokens=2500,
                temperature=0.4
            )

        thought = await self.brain.think(
            thought_type=ThoughtType.REFLECTION,
            input_data=input_data,
            template_id=template_id
        )

        proposal = thought.output
        self.logger.info(f"Meta-optimization proposal generated. Rationale: {proposal.get('rationale')}")

        # Apply template updates
        updates = proposal.get("template_updates", {})
        for tid, new_template in updates.items():
            if tid in self.brain.prompt_templates:
                self.brain.prompt_templates[tid].template = new_template
                self.logger.info(f"Updated prompt template: {tid}")

        self.optimization_history.append(proposal)

        log_agent_event(
            self.agent_id,
            "meta_optimization_applied",
            {"updates_count": len(updates), "rationale": proposal.get("rationale")}
        )

    async def propose_orchestrator_improvement(self, orchestrator_file: str, code_modifier: Any) -> Dict[str, Any]:
        """
        Analyze the EvolutionOrchestrator code and propose functional improvements.
        (Self-Architecture improvement)
        """
        self.logger.info(f"Analyzing {orchestrator_file} for architectural improvements...")

        with open(orchestrator_file, "r") as f:
            current_code = f.read()

        input_data = {
            "current_code": current_code,
            "performance_history": self.optimization_history[-5:] if self.optimization_history else "No history yet."
        }

        template_id = "architectural_optimization"
        if template_id not in self.brain.prompt_templates:
            from ..agents.brain import PromptTemplate
            self.brain.prompt_templates[template_id] = PromptTemplate(
                template_id=template_id,
                name="System Architectural Optimization",
                template="""
You are a Lead AI System Architect. Review the core evolution orchestrator code:

Current Code:
{current_code}

Performance Context:
{performance_history}

Please propose a functional improvement to the orchestrator's logic:
1. "motivation": Why is this change needed?
2. "proposed_code": The complete improved code for the orchestrator.
3. "target_element": The specific class or method being improved.

Format your response as JSON.
""",
                variables=["current_code", "performance_history"],
                thought_type=ThoughtType.PLANNING,
                max_tokens=4000,
                temperature=0.3
            )

        thought = await self.brain.think(
            thought_type=ThoughtType.PLANNING,
            input_data=input_data,
            template_id=template_id
        )

        proposal = thought.output
        self.logger.info(f"Architectural improvement proposed: {proposal.get('motivation')}")

        # In a real scenario, this would be passed to the consensus module before application
        return proposal

    async def shutdown(self):
        """Shutdown the meta-optimizer."""
        self.logger.info("Meta-Optimizer shutdown.")
