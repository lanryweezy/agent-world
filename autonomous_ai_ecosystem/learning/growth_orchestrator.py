"""
Growth Orchestrator for the Autonomous AI Ecosystem.

Coordinates the GTM pipeline for successfully evolved capabilities,
connecting Arrow, Mirror, Quill, Flare, and Closer.
"""

from typing import Dict, Any, List
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from ..agents.growth.specialists import GrowthSpecialist

class GrowthOrchestrator(AgentModule):
    """
    Orchestrates the commercialization journey of an evolved asset.
    Pipeline: GTM Plan (Arrow) -> Positioning (Mirror) -> Copy (Quill) -> Campaign (Flare) -> Sales (Closer).
    """

    def __init__(self, agent_id: str, growth_team: Dict[str, GrowthSpecialist]):
        super().__init__(agent_id)
        self.team = growth_team
        self.logger = get_agent_logger(agent_id, "growth_orchestrator")
        self.commercial_history = {}

    async def initialize(self):
        self.logger.info("Growth Orchestrator initialized.")

    async def launch_capability(self, name: str, description: str, metrics: Dict[str, Any]):
        """Execute the full GTM pipeline for a new breakthrough."""
        self.logger.info(f"Launching growth pipeline for breakthrough: {name}")

        context = {"name": name, "description": description, "metrics": metrics}

        # 1. ARROW: Strategic GTM Plan
        gtm_plan = await self.team["Arrow"].execute_task(f"Create GTM plan for {name}", context)

        # 2. MIRROR: Positioning Brief
        pos_brief = await self.team["Mirror"].execute_task(f"Position {name}", {**context, "gtm": gtm_plan})

        # 3. QUILL: Core Sales Copy
        copy = await self.team["Quill"].execute_task(f"Write landing page and ad copy for {name}", {**context, "positioning": pos_brief})

        # 4. FLARE: Brief Campaign
        campaign = await self.team["Flare"].execute_task(f"Design launch campaign for {name}", {**context, "copy": copy})

        # 5. CLOSER: Prep Discovery Guide
        sales_guide = await self.team["Closer"].execute_task(f"Create discovery call guide for {name}", {**context, "campaign": campaign})

        self.commercial_history[name] = {
            "gtm_plan": gtm_plan,
            "positioning": pos_brief,
            "copy": copy,
            "campaign": campaign,
            "sales_guide": sales_guide
        }

        log_agent_event(self.agent_id, "capability_launched_commercially", {"name": name})
        self.logger.info(f"Growth pipeline completed for {name}.")
        return self.commercial_history[name]

    async def shutdown(self):
        self.logger.info("Growth Orchestrator shutdown.")
