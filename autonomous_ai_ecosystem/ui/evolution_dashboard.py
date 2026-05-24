"""
ASI-EVOLVE Dashboard for the Autonomous AI Ecosystem.

Provides a visualization of the evolution progress, MAP-Elites niches,
and research breakthroughs for human oversight.
"""

from typing import Dict, Any, List
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger
from ..learning.evolution_orchestrator import EvolutionOrchestrator

class EvolutionDashboard(AgentModule):
    """
    Visualization and oversight dashboard for the ASI-EVOLVE framework.
    """

    def __init__(self, agent_id: str, orchestrator: EvolutionOrchestrator):
        super().__init__(agent_id)
        self.orchestrator = orchestrator
        self.logger = get_agent_logger(agent_id, "evolution_dashboard")

    async def initialize(self):
        """Initialize the dashboard."""
        self.logger.info("Evolution Dashboard initialized.")

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Compile current evolution data for visualization.
        """
        orch = self.orchestrator

        # Calculate summary statistics
        total_rounds = orch.evolution_rounds
        success_rate = 0.0
        if orch.database:
            success_count = sum(1 for n in orch.database if n.execution_result["status"] == "success")
            success_rate = success_count / len(orch.database)

        # MAP-Elites Grid visualization data
        grid_data = []
        for niche, node in orch.map_elites_archive.items():
            grid_data.append({
                "bin": list(niche),
                "score": node.score,
                "complexity": node.features.get("complexity", 0),
                "insight_density": node.features.get("insight_density", 0)
            })

        # Island status
        island_stats = [len(island) for island in orch.islands]

        # Best discoveries
        top_nodes = sorted(orch.database, key=lambda x: x.score, reverse=True)[:5]
        discoveries = [
            {"id": n.node_id, "score": n.score, "motivation": n.motivation[:100]}
            for n in top_nodes
        ]

        return {
            "orchestrator_id": orch.agent_id,
            "total_rounds": total_rounds,
            "success_rate": success_rate,
            "sampling_strategy": orch.sampling_strategy,
            "map_elites_grid": grid_data,
            "islands_population": island_stats,
            "top_discoveries": discoveries
        }

    async def render_cli_view(self):
        """Render a text-based view of the evolution progress."""
        data = await self.get_dashboard_data()
        print("\n" + "="*50)
        print(f" ASI-EVOLVE PROGRESS DASHBOARD ({data['orchestrator_id']})")
        print("="*50)
        print(f"Total Rounds: {data['total_rounds']} | Success Rate: {data['success_rate']:.2%}")
        print(f"Strategy: {data['sampling_strategy']} | Islands: {data['islands_population']}")
        print("-"*50)
        print("TOP DISCOVERIES:")
        for i, d in enumerate(data['top_discoveries']):
            print(f" {i+1}. [{d['score']:.2f}] {d['motivation']}...")
        print("="*50 + "\n")

    async def shutdown(self):
        """Shutdown the dashboard."""
        self.logger.info("Evolution Dashboard shutdown.")
