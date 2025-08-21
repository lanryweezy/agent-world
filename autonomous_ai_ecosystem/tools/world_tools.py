"""
Tools for interacting with the Virtual World.
"""

from typing import Any, Dict, List

from ..core.interfaces import ToolInterface
from ..world.virtual_world import VirtualWorld
from ..world.construction import ConstructionManager, ProjectType
from ..world.virtual_world import Coordinates, LocationType


class CheckSurroundingsTool(ToolInterface):
    """A tool to check the agent's immediate surroundings."""

    def __init__(self, virtual_world: VirtualWorld):
        self._virtual_world = virtual_world

    @property
    def name(self) -> str:
        return "check_surroundings"

    @property
    def description(self) -> str:
        return "Checks the agent's immediate surroundings in the virtual world to see what locations, resources, or other agents are nearby. Use this to understand your current environment."

    async def execute(self, agent_id: str, radius: float = 20.0) -> List[Dict[str, Any]]:
        """
        Executes the check.

        Args:
            agent_id: The ID of the agent checking its surroundings.
            radius: The radius to check within.

        Returns:
            A list of nearby locations and their details.
        """
        # This requires getting the agent's current position, which is not yet implemented.
        # For now, we will assume a default position or that this will be added later.
        # Let's assume the VirtualWorld can get an agent's position.
        agent_pos = self._virtual_world.get_agent_position(agent_id)
        if not agent_pos:
            return [{"error": f"Could not find position for agent {agent_id}."}]

        nearby_locations = self._virtual_world.find_nearby_locations(agent_pos, max_distance=radius)

        return [
            {
                "location_id": loc.location_id,
                "name": loc.name,
                "type": loc.location_type.value,
                "distance": dist
            }
            for loc_id, loc, dist in nearby_locations
        ]


class MoveTool(ToolInterface):
    """A tool for moving the agent in the world."""

    def __init__(self, virtual_world: VirtualWorld):
        self._virtual_world = virtual_world

    @property
    def name(self) -> str:
        return "move"

    @property
    def description(self) -> str:
        return "Moves the agent one step in a specified direction (north, south, east, west)."

    async def execute(self, agent_id: str, direction: str) -> Dict[str, Any]:
        """
        Executes the move.

        Args:
            agent_id: The ID of the agent moving.
            direction: The direction to move in.

        Returns:
            A dictionary with the result of the move.
        """
        # This logic is also dependent on agent positions being tracked in VirtualWorld
        current_pos = self._virtual_world.get_agent_position(agent_id)
        if not current_pos:
            return {"success": False, "reason": "Agent position unknown."}

        new_pos = Coordinates(current_pos.x, current_pos.y, current_pos.z)
        step_size = 5.0

        if direction.lower() == "north":
            new_pos.y += step_size
        elif direction.lower() == "south":
            new_pos.y -= step_size
        elif direction.lower() == "east":
            new_pos.x += step_size
        elif direction.lower() == "west":
            new_pos.x -= step_size
        else:
            return {"success": False, "reason": "Invalid direction. Use north, south, east, or west."}

        # In a real implementation, you'd check for collisions in the virtual_world
        success = self._virtual_world.update_agent_position(agent_id, new_pos)

        if success:
            return {"success": True, "new_position": str(new_pos)}
        else:
            return {"success": False, "reason": "Move failed, path may be obstructed."}


class StartConstructionProjectTool(ToolInterface):
    """A tool to start a new construction project."""

    def __init__(self, construction_manager: ConstructionManager):
        self._construction_manager = construction_manager

    @property
    def name(self) -> str:
        return "start_construction_project"

    @property
    def description(self) -> str:
        return "Starts a new collaborative construction project for a new location, like a 'workspace' or 'library'."

    async def execute(self, agent_id: str, name: str, description: str, project_type: str, x: float, y: float) -> Dict[str, Any]:
        """
        Executes the project proposal.

        Args:
            agent_id: The ID of the agent proposing the project.
            name: The name of the new location to be built.
            description: A description of the new location.
            project_type: The type of project (e.g., 'NEW_LOCATION').
            x: The x-coordinate for the new location.
            y: The y-coordinate for the new location.

        Returns:
            A dictionary with the result of the proposal.
        """
        try:
            # The ConstructionManager's propose_project seems more detailed.
            # I will adapt to what I expect it to be.
            # This is a good example of where I might need to refactor the existing code
            # to match the needs of the tools.
            proposal_id = await self._construction_manager.propose_project(
                proposer_id=agent_id,
                project_name=name,
                project_description=description,
                project_type=ProjectType[project_type.upper()],
                target_coordinates=Coordinates(x, y),
                # Resource requirements would be determined by a more complex process
                required_resources={}
            )
            return {"success": True, "proposal_id": proposal_id}
        except Exception as e:
            return {"success": False, "error": str(e)}
