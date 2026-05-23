"""
Discovery API for the Autonomous AI Ecosystem.

Exposes the ecosystem's autonomous research and evolution capabilities
to external users and applications.
"""

from typing import Dict, Any, List, Optional
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from ..learning.evolution_orchestrator import EvolutionOrchestrator

class DiscoveryAPI(AgentModule):
    """
    Public-facing API for interacting with the evolution and discovery systems.
    Allows external users to submit research tasks and retrieve reports.
    """

    def __init__(self, agent_id: str, evolution_orchestrator: EvolutionOrchestrator):
        super().__init__(agent_id)
        self.evolution_orchestrator = evolution_orchestrator
        self.logger = get_agent_logger(agent_id, "discovery_api")
        self.active_tasks = {}

    async def initialize(self):
        """Initialize the API."""
        self.logger.info("Discovery API initialized and ready for external requests.")

    async def submit_research_request(self, task_description: str, target_area: str) -> str:
        """
        Submit a new research/evolution task from an external user.
        """
        task_id = f"ext_task_{len(self.active_tasks)}"
        self.logger.info(f"Received external research request: {task_id} - {target_area}")

        # Start evolution in background (conceptual)
        # In a real system, this would be an async background task
        # await self.evolution_orchestrator.start_evolution(target_file=target_area, task_description=task_description)

        self.active_tasks[task_id] = {
            "status": "queued",
            "task": task_description,
            "area": target_area
        }

        log_agent_event(self.agent_id, "external_task_received", {"task_id": task_id})
        return task_id

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status and result of a submitted task."""
        if task_id not in self.active_tasks:
            return {"error": "Task not found"}
        return self.active_tasks[task_id]

    async def shutdown(self):
        """Shutdown the API."""
        self.logger.info("Discovery API shutdown.")
