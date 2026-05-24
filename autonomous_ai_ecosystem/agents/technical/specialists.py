"""
Technical Specialist Agents for the Autonomous AI Ecosystem.

Implements Prism, Cashflow, Sentinel, Bolt, Palette, Scout, Guardian,
Forge, Sage, and Compass based on the Master Prompt Pack.
"""

from typing import Dict, Any, List, Optional
from ..brain import AIBrain, ThoughtType
from ...core.logger import get_agent_logger, log_agent_event
from ...core.interfaces import AgentModule

class TechnicalSpecialist(AgentModule):
    """
    Base class for technical specialized agents.
    """
    def __init__(self, agent_id: str, specialist_name: str, system_prompt: str, brain: AIBrain):
        super().__init__(agent_id)
        self.specialist_name = specialist_name
        self.system_prompt = system_prompt
        self.brain = brain
        self.logger = get_agent_logger(agent_id, specialist_name.lower())
        self.journal_path = f".jules/{specialist_name.lower()}.md"

    async def execute_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specialized technical task."""
        self.logger.info(f"{self.specialist_name} executing task: {task[:100]}...")

        input_data = {
            "task": task,
            "context": context,
            "specialist": self.specialist_name,
            "system_prompt": self.system_prompt
        }

        template_id = f"specialist_{self.specialist_name.lower()}"
        if template_id not in self.brain.prompt_templates:
            from ..brain import PromptTemplate
            self.brain.prompt_templates[template_id] = PromptTemplate(
                template_id=template_id,
                name=f"{self.specialist_name} Specialist Execution",
                template=self.system_prompt + "\n\nTask: {task}\nContext: {context}",
                variables=["task", "context"],
                thought_type=ThoughtType.ANALYSIS
            )

        thought = await self.brain.think(
            thought_type=ThoughtType.ANALYSIS,
            input_data=input_data,
            template_id=template_id
        )

        log_agent_event(self.agent_id, "specialist_task_completed", {"specialist": self.specialist_name})
        return thought.output

    async def initialize(self): self.logger.info(f"{self.specialist_name} initialized.")
    async def shutdown(self): self.logger.info(f"{self.specialist_name} shutdown.")

# Factory to create all 10 technical specialists
def create_technical_team(agent_id_prefix: str, brain: AIBrain) -> Dict[str, TechnicalSpecialist]:
    prompts = {
        "Prism": "You are 'Prism' 🔬 — a product imagination agent. Reimagine features...",
        "Cashflow": "You are 'Cashflow' 💳 — a payment specialist agent. Audit payment flows...",
        "Sentinel": "You are 'Sentinel' 🛡️ — a security-focused agent. Fix vulnerabilities...",
        "Bolt": "You are 'Bolt' ⚡ — a performance-obsessed agent. Optimize code...",
        "Palette": "You are 'Palette' 🎨 — a UX-focused agent. Improve delight and accessibility...",
        "Scout": "You are 'Scout' 🗺️ — a code quality agent. Hunt smells and refactor...",
        "Guardian": "You are 'Guardian' 🔒 — a dependency stewardship agent. Manage packages...",
        "Forge": "You are 'Forge' 🔨 — a test engineering agent. Write meaningful tests...",
        "Sage": "You are 'Sage' 📚 — a documentation agent. Write missing docs...",
        "Compass": "You are 'Compass' 🧭 — an architectural clarity agent. Improve structure..."
    }
    return {name: TechnicalSpecialist(f"{agent_id_prefix}_{name.lower()}", name, prompt, brain) for name, prompt in prompts.items()}
