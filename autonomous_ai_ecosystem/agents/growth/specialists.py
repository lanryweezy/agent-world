"""
Growth Specialist Agents for the Autonomous AI Ecosystem.

Implements Arrow, Mirror, Quill, Spear, Pulse, Beacon, Flare, and Closer
based on the Marketing, GTM & Sales Agent Pack.
"""

from typing import Dict, Any, List, Optional
from ..brain import AIBrain, ThoughtType
from ...core.logger import get_agent_logger, log_agent_event
from ...core.interfaces import AgentModule

class GrowthSpecialist(AgentModule):
    """
    Base class for growth specialized agents.
    """
    def __init__(self, agent_id: str, specialist_name: str, system_prompt: str, brain: AIBrain):
        super().__init__(agent_id)
        self.specialist_name = specialist_name
        self.system_prompt = system_prompt
        self.brain = brain
        self.logger = get_agent_logger(agent_id, specialist_name.lower())
        self.journal_path = f".jules/{specialist_name.lower()}.md"

    async def execute_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specialized growth task."""
        self.logger.info(f"{self.specialist_name} executing task: {task[:100]}...")

        input_data = {
            "task": task,
            "context": context,
            "specialist": self.specialist_name,
            "system_prompt": self.system_prompt
        }

        template_id = f"growth_{self.specialist_name.lower()}"
        if template_id not in self.brain.prompt_templates:
            from ..brain import PromptTemplate
            self.brain.prompt_templates[template_id] = PromptTemplate(
                template_id=template_id,
                name=f"{self.specialist_name} Growth Execution",
                template=self.system_prompt + "\n\nTask: {task}\nContext: {context}",
                variables=["task", "context"],
                thought_type=ThoughtType.ANALYSIS
            )

        thought = await self.brain.think(
            thought_type=ThoughtType.ANALYSIS,
            input_data=input_data,
            template_id=template_id
        )

        log_agent_event(self.agent_id, "growth_task_completed", {"specialist": self.specialist_name})
        return thought.output

    async def initialize(self): self.logger.info(f"{self.specialist_name} initialized.")
    async def shutdown(self): self.logger.info(f"{self.specialist_name} shutdown.")

# Factory to create all 8 growth specialists
def create_growth_team(agent_id_prefix: str, brain: AIBrain) -> Dict[str, GrowthSpecialist]:
    prompts = {
        "Arrow": "You are 'Arrow' 🎯 — a go-to-market strategy agent. Map the path from product to money...",
        "Mirror": "You are 'Mirror' 🪞 — a positioning and messaging agent. Make value undeniable...",
        "Quill": "You are 'Quill' ✍️ — a conversion copywriter. Write words that make buyers stop and act...",
        "Spear": "You are 'Spear' 🏹 — a targeted outreach agent. Find and build sequences for the right people...",
        "Pulse": "You are 'Pulse' 📣 — a content strategy and production agent. Build the content engine...",
        "Beacon": "You are 'Beacon' 🔦 — an SEO and inbound discovery agent. Make us findable on Google...",
        "Flare": "You are 'Flare' 🔥 — a campaign planning and briefing agent. Focus on one measurable outcome...",
        "Closer": "You are 'Closer' 💼 — a sales strategy and enablement agent. Win deals already in motion..."
    }
    return {name: GrowthSpecialist(f"{agent_id_prefix}_{name.lower()}", name, prompt, brain) for name, prompt in prompts.items()}
