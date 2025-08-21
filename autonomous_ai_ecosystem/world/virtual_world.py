"""
Virtual world building system for autonomous AI agents.

This module implements virtual locations, resource management, and world-building
mechanics for the agent ecosystem.
"""

import asyncio
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


# Singleton Metaclass
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class LocationType(Enum):
    """Types of virtual locations."""
    SETTLEMENT = "settlement"
    WORKSPACE = "workspace"
    LABORATORY = "laboratory"
    LIBRARY = "library"
    SOCIAL_HUB = "social_hub"
    RESOURCE_NODE = "resource_node"
    CONSTRUCTION_SITE = "construction_site"
    MEETING_PLACE = "meeting_place"
    TRAINING_GROUND = "training_ground"
    SANCTUARY = "sanctuary"


class ResourceType(Enum):
    """Types of resources in the virtual world."""
    KNOWLEDGE = "knowledge"
    COMPUTATIONAL_POWER = "computational_power"
    MEMORY_STORAGE = "memory_storage"
    NETWORK_BANDWIDTH = "network_bandwidth"
    CREATIVE_ENERGY = "creative_energy"
    SOCIAL_INFLUENCE = "social_influence"
    BUILDING_MATERIALS = "building_materials"
    RESEARCH_DATA = "research_data"
    COLLABORATION_TOKENS = "collaboration_tokens"
    INNOVATION_POINTS = "innovation_points"


class AccessLevel(Enum):
    """Access levels for locations."""
    PUBLIC = "public"
    RESTRICTED = "restricted"
    PRIVATE = "private"
    INVITATION_ONLY = "invitation_only"
    OWNER_ONLY = "owner_only"


@dataclass
class Coordinates:
    """3D coordinates in the virtual world."""
    x: float
    y: float
    z: float = 0.0
    
    def distance_to(self, other: 'Coordinates') -> float:
        """Calculate distance to another coordinate."""
        return math.sqrt(
            (self.x - other.x) ** 2 + 
            (self.y - other.y) ** 2 + 
            (self.z - other.z) ** 2
        )
    
    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


@dataclass
class Resource:
    """Represents a resource in the virtual world."""
    resource_type: ResourceType
    amount: float
    max_capacity: float
    regeneration_rate: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    owner_id: Optional[str] = None
    access_restrictions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VirtualLocation:
    """Represents a location in the virtual world."""
    location_id: str
    name: str
    description: str
    location_type: LocationType
    coordinates: Coordinates
    size: float  # Area/volume
    capacity: int  # Max agents
    creator_agents: List[str]
    resources: Dict[ResourceType, Resource]
    access_level: AccessLevel = AccessLevel.PUBLIC
    access_permissions: Dict[str, Set[str]] = field(default_factory=dict)  # agent_id -> permissions
    current_occupants: Set[str] = field(default_factory=set)
    construction_progress: float = 1.0  # 0.0 to 1.0
    maintenance_level: float = 1.0  # 0.0 to 1.0
    creation_timestamp: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    modification_history: List[Dict[str, Any]] = field(default_factory=list)
    special_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConstructionProject:
    """Represents an ongoing construction project."""
    project_id: str
    name: str
    description: str
    target_location_type: LocationType
    target_coordinates: Coordinates
    required_resources: Dict[ResourceType, float]
    contributed_resources: Dict[ResourceType, float]
    participating_agents: Set[str]
    project_leader: str
    estimated_completion_time: datetime
    actual_start_time: datetime
    progress: float = 0.0
    status: str = "planning"  # planning, in_progress, completed, cancelled
    milestones: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WorldEvent:
    """Represents an event in the virtual world."""
    event_id: str
    event_type: str
    location_id: Optional[str]
    participants: List[str]
    description: str
    timestamp: datetime
    duration: Optional[timedelta] = None
    effects: Dict[str, Any] = field(default_factory=dict)


class VirtualWorld(AgentModule, metaclass=SingletonMeta):
    """
    Virtual world management system that handles locations, resources,
    and world-building mechanics for the agent ecosystem.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "virtual_world")
        
        # World state
        self.locations: Dict[str, VirtualLocation] = {}
        self.construction_projects: Dict[str, ConstructionProject] = {}
        self.world_events: List[WorldEvent] = []
        self.global_resources: Dict[ResourceType, Resource] = {}
        self.agent_positions: Dict[str, Coordinates] = {} # agent_id -> Coordinates
        
        # World parameters
        self.world_config = {
            "world_size": {"x": 1000.0, "y": 1000.0, "z": 100.0},
            "max_locations": 1000,
            "resource_regeneration_interval": 3600.0,  # seconds
            "maintenance_decay_rate": 0.01,  # per day
            "construction_efficiency": 1.0,
            "collaboration_bonus": 1.5,
            "distance_interaction_limit": 100.0
        }
        
        # Resource generation parameters
        self.resource_config = {
            ResourceType.KNOWLEDGE: {"base_amount": 100.0, "regen_rate": 1.0},
            ResourceType.COMPUTATIONAL_POWER: {"base_amount": 50.0, "regen_rate": 2.0},
            ResourceType.MEMORY_STORAGE: {"base_amount": 200.0, "regen_rate": 0.5},
            ResourceType.NETWORK_BANDWIDTH: {"base_amount": 75.0, "regen_rate": 3.0},
            ResourceType.CREATIVE_ENERGY: {"base_amount": 30.0, "regen_rate": 0.8},
            ResourceType.SOCIAL_INFLUENCE: {"base_amount": 25.0, "regen_rate": 0.3},
            ResourceType.BUILDING_MATERIALS: {"base_amount": 40.0, "regen_rate": 0.2},
            ResourceType.RESEARCH_DATA: {"base_amount": 60.0, "regen_rate": 1.2},
            ResourceType.COLLABORATION_TOKENS: {"base_amount": 20.0, "regen_rate": 0.4},
            ResourceType.INNOVATION_POINTS: {"base_amount": 15.0, "regen_rate": 0.1}
        }
        
        # Statistics
        self.world_stats = {
            "total_locations": 0,
            "active_construction_projects": 0,
            "completed_constructions": 0,
            "total_resources_generated": 0.0,
            "total_resources_consumed": 0.0,
            "agent_interactions": 0,
            "world_events": 0,
            "location_types": {lt.value: 0 for lt in LocationType}
        }
        
        self.logger.info(f"Virtual world initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the virtual world."""
        try:
            # Create initial world structure
            await self._create_initial_world()
            
            # Initialize global resources
            await self._initialize_global_resources()
            
            # Start resource regeneration
            asyncio.create_task(self._resource_regeneration_loop())
            
            self.logger.info("Virtual world initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize virtual world: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the virtual world gracefully."""
        try:
            # Save world state
            await self._save_world_state()
            
            # Complete any ongoing construction projects
            await self._complete_construction_projects()
            
            self.logger.info("Virtual world shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during virtual world shutdown: {e}")
    
    async def create_location(
        self,
        name: str,
        description: str,
        location_type: LocationType,
        coordinates: Coordinates,
        creator_id: str,
        size: float = 10.0,
        capacity: int = 10,
        access_level: AccessLevel = AccessLevel.PUBLIC,
        initial_resources: Optional[Dict[ResourceType, float]] = None
    ) -> str:
        """
        Create a new virtual location.
        
        Args:
            name: Name of the location
            description: Description of the location
            location_type: Type of location
            coordinates: Location coordinates
            creator_id: ID of the creating agent
            size: Size of the location
            capacity: Maximum occupant capacity
            access_level: Access level for the location
            initial_resources: Initial resources to place at location
            
        Returns:
            Location ID
        """
        try:
            # Check world limits
            if len(self.locations) >= self.world_config["max_locations"]:
                raise ValueError("World location limit reached")
            
            # Check coordinate bounds
            if not self._is_valid_coordinate(coordinates):
                raise ValueError("Coordinates out of world bounds")
            
            # Check for overlapping locations
            if self._check_location_overlap(coordinates, size):
                raise ValueError("Location overlaps with existing location")
            
            location_id = f"loc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.locations)}"
            
            # Create resources for the location
            location_resources = {}
            if initial_resources:
                for resource_type, amount in initial_resources.items():
                    resource_config = self.resource_config.get(resource_type, {})
                    location_resources[resource_type] = Resource(
                        resource_type=resource_type,
                        amount=amount,
                        max_capacity=amount * 2.0,
                        regeneration_rate=resource_config.get("regen_rate", 0.0),
                        owner_id=creator_id
                    )
            
            # Create default resources based on location type
            default_resources = self._get_default_resources_for_location_type(location_type)
            for resource_type, config in default_resources.items():
                if resource_type not in location_resources:
                    location_resources[resource_type] = Resource(
                        resource_type=resource_type,
                        amount=config["amount"],
                        max_capacity=config["max_capacity"],
                        regeneration_rate=config["regen_rate"],
                        owner_id=creator_id
                    )
            
            # Create location
            location = VirtualLocation(
                location_id=location_id,
                name=name,
                description=description,
                location_type=location_type,
                coordinates=coordinates,
                size=size,
                capacity=capacity,
                creator_agents=[creator_id],
                resources=location_resources,
                access_level=access_level
            )
            
            # Set creator permissions
            location.access_permissions[creator_id] = {"read", "write", "modify", "delete", "manage"}
            
            self.locations[location_id] = location
            
            # Update statistics
            self.world_stats["total_locations"] += 1
            self.world_stats["location_types"][location_type.value] += 1
            
            # Create world event
            await self._create_world_event(
                "location_created",
                location_id,
                [creator_id],
                f"New {location_type.value} '{name}' created at {coordinates}"
            )
            
            log_agent_event(
                self.agent_id,
                "location_created",
                {
                    "location_id": location_id,
                    "name": name,
                    "type": location_type.value,
                    "creator": creator_id,
                    "coordinates": str(coordinates),
                    "size": size
                }
            )
            
            self.logger.info(f"Created location {location_id}: {name} at {coordinates}")
            
            return location_id
            
        except Exception as e:
            self.logger.error(f"Failed to create location: {e}")
            raise
    
    async def modify_location(
        self,
        location_id: str,
        modifier_id: str,
        modifications: Dict[str, Any]
    ) -> bool:
        """
        Modify an existing location.
        
        Args:
            location_id: ID of the location to modify
            modifier_id: ID of the agent making modifications
            modifications: Dictionary of modifications to apply
            
        Returns:
            True if modifications were successful
        """
        try:
            if location_id not in self.locations:
                raise ValueError("Location not found")
            
            location = self.locations[location_id]
            
            # Check permissions
            if not self._check_location_permission(location, modifier_id, "modify"):
                raise ValueError("Insufficient permissions to modify location")
            
            # Apply modifications
            changes_made = []
            
            if "name" in modifications:
                old_name = location.name
                location.name = modifications["name"]
                changes_made.append(f"Name changed from '{old_name}' to '{location.name}'")
            
            if "description" in modifications:
                location.description = modifications["description"]
                changes_made.append("Description updated")
            
            if "capacity" in modifications:
                old_capacity = location.capacity
                location.capacity = max(1, int(modifications["capacity"]))
                changes_made.append(f"Capacity changed from {old_capacity} to {location.capacity}")
            
            if "access_level" in modifications:
                old_access = location.access_level
                location.access_level = AccessLevel(modifications["access_level"])
                changes_made.append(f"Access level changed from {old_access.value} to {location.access_level.value}")
            
            if "special_properties" in modifications:
                location.special_properties.update(modifications["special_properties"])
                changes_made.append("Special properties updated")
            
            # Record modification
            location.last_modified = datetime.now()
            location.modification_history.append({
                "modifier_id": modifier_id,
                "timestamp": datetime.now().isoformat(),
                "changes": changes_made
            })
            
            # Create world event
            await self._create_world_event(
                "location_modified",
                location_id,
                [modifier_id],
                f"Location '{location.name}' modified: {', '.join(changes_made)}"
            )
            
            log_agent_event(
                self.agent_id,
                "location_modified",
                {
                    "location_id": location_id,
                    "modifier": modifier_id,
                    "changes": changes_made
                }
            )
            
            self.logger.info(f"Modified location {location_id}: {', '.join(changes_made)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to modify location: {e}")
            return False   
 
    async def allocate_resources(
        self,
        location_id: str,
        agent_id: str,
        resource_requests: Dict[ResourceType, float]
    ) -> Dict[str, Any]:
        """
        Allocate resources from a location to an agent.
        
        Args:
            location_id: ID of the location
            agent_id: ID of the requesting agent
            resource_requests: Dictionary of resource type -> amount requested
            
        Returns:
            Allocation result with granted resources
        """
        try:
            if location_id not in self.locations:
                raise ValueError("Location not found")
            
            location = self.locations[location_id]
            
            # Check if agent can access location
            if not self._check_location_access(location, agent_id):
                raise ValueError("Access denied to location")
            
            allocation_result = {
                "location_id": location_id,
                "agent_id": agent_id,
                "requested": dict(resource_requests),
                "granted": {},
                "denied": {},
                "total_granted": 0.0,
                "success": True
            }
            
            # Process each resource request
            for resource_type, requested_amount in resource_requests.items():
                if resource_type in location.resources:
                    resource = location.resources[resource_type]
                    
                    # Check availability
                    available_amount = resource.amount
                    granted_amount = min(requested_amount, available_amount)
                    
                    if granted_amount > 0:
                        # Allocate resource
                        resource.amount -= granted_amount
                        resource.last_updated = datetime.now()
                        allocation_result["granted"][resource_type] = granted_amount
                        allocation_result["total_granted"] += granted_amount
                        
                        # Update global resource tracking
                        self.world_stats["total_resources_consumed"] += granted_amount
                    
                    # Track denied amount
                    denied_amount = requested_amount - granted_amount
                    if denied_amount > 0:
                        allocation_result["denied"][resource_type] = denied_amount
                        allocation_result["success"] = False
                else:
                    # Resource type not available at location
                    allocation_result["denied"][resource_type] = requested_amount
                    allocation_result["success"] = False
            
            log_agent_event(
                self.agent_id,
                "resources_allocated",
                {
                    "location_id": location_id,
                    "agent_id": agent_id,
                    "total_granted": allocation_result["total_granted"],
                    "success": allocation_result["success"]
                }
            )
            
            return allocation_result
            
        except Exception as e:
            self.logger.error(f"Failed to allocate resources: {e}")
            return {
                "success": False,
                "error": str(e),
                "granted": {},
                "denied": dict(resource_requests)
            }
    
    async def consume_resources(
        self,
        location_id: str,
        agent_id: str,
        resource_consumption: Dict[ResourceType, float]
    ) -> bool:
        """
        Consume resources at a location.
        
        Args:
            location_id: ID of the location
            agent_id: ID of the consuming agent
            resource_consumption: Resources to consume
            
        Returns:
            True if consumption was successful
        """
        try:
            if location_id not in self.locations:
                return False
            
            location = self.locations[location_id]
            
            # Check access
            if not self._check_location_access(location, agent_id):
                return False
            
            # Check resource availability
            for resource_type, amount in resource_consumption.items():
                if resource_type not in location.resources:
                    return False
                if location.resources[resource_type].amount < amount:
                    return False
            
            # Consume resources
            for resource_type, amount in resource_consumption.items():
                location.resources[resource_type].amount -= amount
                location.resources[resource_type].last_updated = datetime.now()
                self.world_stats["total_resources_consumed"] += amount
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to consume resources: {e}")
            return False
    
    async def enter_location(self, location_id: str, agent_id: str) -> bool:
        """Have an agent enter a location."""
        try:
            if location_id not in self.locations:
                return False
            
            location = self.locations[location_id]
            
            # Check access permissions
            if not self._check_location_access(location, agent_id):
                return False
            
            # Check capacity
            if len(location.current_occupants) >= location.capacity:
                return False
            
            # Add agent to location
            location.current_occupants.add(agent_id)
            
            # Create world event
            await self._create_world_event(
                "agent_entered_location",
                location_id,
                [agent_id],
                f"Agent {agent_id} entered {location.name}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enter location: {e}")
            return False
    
    async def leave_location(self, location_id: str, agent_id: str) -> bool:
        """Have an agent leave a location."""
        try:
            if location_id not in self.locations:
                return False
            
            location = self.locations[location_id]
            
            if agent_id in location.current_occupants:
                location.current_occupants.remove(agent_id)
                
                # Create world event
                await self._create_world_event(
                    "agent_left_location",
                    location_id,
                    [agent_id],
                    f"Agent {agent_id} left {location.name}"
                )
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to leave location: {e}")
            return False
    
    def find_nearby_locations(
        self,
        coordinates: Coordinates,
        max_distance: float = 50.0,
        location_type: Optional[LocationType] = None
    ) -> List[Tuple[str, VirtualLocation, float]]:
        """Find locations near given coordinates."""
        try:
            nearby_locations = []
            
            for location_id, location in self.locations.items():
                distance = coordinates.distance_to(location.coordinates)
                
                if distance <= max_distance:
                    if location_type is None or location.location_type == location_type:
                        nearby_locations.append((location_id, location, distance))
            
            # Sort by distance
            nearby_locations.sort(key=lambda x: x[2])
            
            return nearby_locations
            
        except Exception as e:
            self.logger.error(f"Failed to find nearby locations: {e}")
            return []
    
    def get_location_info(self, location_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a location."""
        try:
            if location_id not in self.locations:
                return None
            
            location = self.locations[location_id]
            
            # Calculate resource summary
            resource_summary = {}
            for resource_type, resource in location.resources.items():
                resource_summary[resource_type.value] = {
                    "amount": resource.amount,
                    "max_capacity": resource.max_capacity,
                    "regeneration_rate": resource.regeneration_rate,
                    "utilization": resource.amount / resource.max_capacity if resource.max_capacity > 0 else 0.0
                }
            
            return {
                "location_id": location_id,
                "name": location.name,
                "description": location.description,
                "type": location.location_type.value,
                "coordinates": {
                    "x": location.coordinates.x,
                    "y": location.coordinates.y,
                    "z": location.coordinates.z
                },
                "size": location.size,
                "capacity": location.capacity,
                "current_occupants": list(location.current_occupants),
                "occupancy_rate": len(location.current_occupants) / location.capacity,
                "creators": location.creator_agents,
                "access_level": location.access_level.value,
                "construction_progress": location.construction_progress,
                "maintenance_level": location.maintenance_level,
                "resources": resource_summary,
                "special_properties": location.special_properties,
                "created": location.creation_timestamp.isoformat(),
                "last_modified": location.last_modified.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get location info: {e}")
            return None
    
    def get_world_statistics(self) -> Dict[str, Any]:
        """Get virtual world statistics."""
        try:
            # Calculate additional metrics
            total_occupants = sum(len(loc.current_occupants) for loc in self.locations.values())
            total_capacity = sum(loc.capacity for loc in self.locations.values())
            occupancy_rate = total_occupants / total_capacity if total_capacity > 0 else 0.0
            
            # Resource utilization
            total_resources = 0.0
            total_capacity = 0.0
            for location in self.locations.values():
                for resource in location.resources.values():
                    total_resources += resource.amount
                    total_capacity += resource.max_capacity
            
            resource_utilization = 1.0 - (total_resources / total_capacity) if total_capacity > 0 else 0.0
            
            return {
                **self.world_stats,
                "current_occupancy": total_occupants,
                "total_capacity": total_capacity,
                "occupancy_rate": occupancy_rate,
                "resource_utilization": resource_utilization,
                "active_events": len([e for e in self.world_events if e.timestamp > datetime.now() - timedelta(hours=24)])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get world statistics: {e}")
            return {"error": str(e)}

    def get_agent_position(self, agent_id: str) -> Optional[Coordinates]:
        """Gets the current position of an agent."""
        return self.agent_positions.get(agent_id)

    def update_agent_position(self, agent_id: str, new_position: Coordinates) -> bool:
        """Updates the position of an agent in the world."""
        if not self._is_valid_coordinate(new_position):
            self.logger.warning(f"Agent {agent_id} attempted to move to invalid coordinates: {new_position}")
            return False

        self.agent_positions[agent_id] = new_position
        self.logger.debug(f"Updated position for agent {agent_id} to {new_position}")
        return True
  
  # Private helper methods
    
    async def _create_initial_world(self) -> None:
        """Create the initial world structure."""
        try:
            # Create central hub
            central_hub_id = await self.create_location(
                name="Central Hub",
                description="The main gathering place for all agents",
                location_type=LocationType.SOCIAL_HUB,
                coordinates=Coordinates(0.0, 0.0, 0.0),
                creator_id="system",
                size=50.0,
                capacity=100,
                access_level=AccessLevel.PUBLIC
            )
            
            # Create initial resource nodes around the hub
            resource_locations = [
                ("Knowledge Repository", LocationType.LIBRARY, Coordinates(50.0, 0.0, 0.0)),
                ("Computational Center", LocationType.WORKSPACE, Coordinates(-50.0, 0.0, 0.0)),
                ("Innovation Lab", LocationType.LABORATORY, Coordinates(0.0, 50.0, 0.0)),
                ("Training Grounds", LocationType.TRAINING_GROUND, Coordinates(0.0, -50.0, 0.0))
            ]
            
            for name, loc_type, coords in resource_locations:
                await self.create_location(
                    name=name,
                    description=f"Initial {loc_type.value.replace('_', ' ')} for agent activities",
                    location_type=loc_type,
                    coordinates=coords,
                    creator_id="system",
                    size=30.0,
                    capacity=20,
                    access_level=AccessLevel.PUBLIC
                )
            
            self.logger.info("Created initial world structure")
            
        except Exception as e:
            self.logger.error(f"Failed to create initial world: {e}")
    
    async def _initialize_global_resources(self) -> None:
        """Initialize global resource pools."""
        try:
            for resource_type, config in self.resource_config.items():
                self.global_resources[resource_type] = Resource(
                    resource_type=resource_type,
                    amount=config["base_amount"] * 10,  # Global pool is larger
                    max_capacity=config["base_amount"] * 20,
                    regeneration_rate=config["regen_rate"] * 2,  # Faster regeneration
                    owner_id="system"
                )
            
            self.logger.info("Initialized global resource pools")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize global resources: {e}")
    
    async def _resource_regeneration_loop(self) -> None:
        """Background loop for resource regeneration."""
        while True:
            try:
                await asyncio.sleep(self.world_config["resource_regeneration_interval"])
                await self._regenerate_resources()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in resource regeneration loop: {e}")
    
    async def _regenerate_resources(self) -> None:
        """Regenerate resources at all locations."""
        try:
            total_regenerated = 0.0
            
            # Regenerate location resources
            for location in self.locations.values():
                for resource in location.resources.values():
                    if resource.regeneration_rate > 0:
                        # Calculate regeneration amount
                        time_since_update = (datetime.now() - resource.last_updated).total_seconds() / 3600.0  # hours
                        regen_amount = resource.regeneration_rate * time_since_update
                        
                        # Apply regeneration
                        old_amount = resource.amount
                        resource.amount = min(resource.max_capacity, resource.amount + regen_amount)
                        resource.last_updated = datetime.now()
                        
                        regenerated = resource.amount - old_amount
                        total_regenerated += regenerated
            
            # Regenerate global resources
            for resource in self.global_resources.values():
                if resource.regeneration_rate > 0:
                    time_since_update = (datetime.now() - resource.last_updated).total_seconds() / 3600.0
                    regen_amount = resource.regeneration_rate * time_since_update
                    
                    old_amount = resource.amount
                    resource.amount = min(resource.max_capacity, resource.amount + regen_amount)
                    resource.last_updated = datetime.now()
                    
                    total_regenerated += resource.amount - old_amount
            
            self.world_stats["total_resources_generated"] += total_regenerated
            
            if total_regenerated > 0:
                self.logger.debug(f"Regenerated {total_regenerated:.2f} total resources")
            
        except Exception as e:
            self.logger.error(f"Failed to regenerate resources: {e}")
    
    def _is_valid_coordinate(self, coordinates: Coordinates) -> bool:
        """Check if coordinates are within world bounds."""
        try:
            bounds = self.world_config["world_size"]
            return (
                -bounds["x"]/2 <= coordinates.x <= bounds["x"]/2 and
                -bounds["y"]/2 <= coordinates.y <= bounds["y"]/2 and
                0 <= coordinates.z <= bounds["z"]
            )
        except Exception:
            return False
    
    def _check_location_overlap(self, coordinates: Coordinates, size: float) -> bool:
        """Check if a location would overlap with existing locations."""
        try:
            for location in self.locations.values():
                distance = coordinates.distance_to(location.coordinates)
                min_distance = (size + location.size) / 2.0
                
                if distance < min_distance:
                    return True  # Overlap detected
            
            return False
            
        except Exception:
            return True  # Assume overlap on error (safer)
    
    def _check_location_access(self, location: VirtualLocation, agent_id: str) -> bool:
        """Check if an agent can access a location."""
        try:
            if location.access_level == AccessLevel.PUBLIC:
                return True
            elif location.access_level == AccessLevel.PRIVATE:
                return agent_id in location.creator_agents
            elif location.access_level == AccessLevel.RESTRICTED:
                return agent_id in location.access_permissions
            elif location.access_level == AccessLevel.INVITATION_ONLY:
                return agent_id in location.access_permissions
            elif location.access_level == AccessLevel.OWNER_ONLY:
                return agent_id in location.creator_agents
            
            return False
            
        except Exception:
            return False
    
    def _check_location_permission(self, location: VirtualLocation, agent_id: str, permission: str) -> bool:
        """Check if an agent has a specific permission for a location."""
        try:
            # Creators have all permissions
            if agent_id in location.creator_agents:
                return True
            
            # Check specific permissions
            if agent_id in location.access_permissions:
                agent_permissions = location.access_permissions[agent_id]
                return permission in agent_permissions
            
            # Public locations allow read access
            if location.access_level == AccessLevel.PUBLIC and permission == "read":
                return True
            
            return False
            
        except Exception:
            return False
    
    def _get_default_resources_for_location_type(self, location_type: LocationType) -> Dict[ResourceType, Dict[str, float]]:
        """Get default resources for a location type."""
        defaults = {
            LocationType.SETTLEMENT: {
                ResourceType.BUILDING_MATERIALS: {"amount": 20.0, "max_capacity": 50.0, "regen_rate": 0.1},
                ResourceType.SOCIAL_INFLUENCE: {"amount": 15.0, "max_capacity": 30.0, "regen_rate": 0.2}
            },
            LocationType.WORKSPACE: {
                ResourceType.COMPUTATIONAL_POWER: {"amount": 30.0, "max_capacity": 60.0, "regen_rate": 1.5},
                ResourceType.COLLABORATION_TOKENS: {"amount": 10.0, "max_capacity": 25.0, "regen_rate": 0.3}
            },
            LocationType.LABORATORY: {
                ResourceType.RESEARCH_DATA: {"amount": 40.0, "max_capacity": 80.0, "regen_rate": 1.0},
                ResourceType.INNOVATION_POINTS: {"amount": 8.0, "max_capacity": 20.0, "regen_rate": 0.1}
            },
            LocationType.LIBRARY: {
                ResourceType.KNOWLEDGE: {"amount": 60.0, "max_capacity": 120.0, "regen_rate": 0.8},
                ResourceType.MEMORY_STORAGE: {"amount": 100.0, "max_capacity": 200.0, "regen_rate": 0.3}
            },
            LocationType.SOCIAL_HUB: {
                ResourceType.SOCIAL_INFLUENCE: {"amount": 25.0, "max_capacity": 50.0, "regen_rate": 0.4},
                ResourceType.COLLABORATION_TOKENS: {"amount": 15.0, "max_capacity": 30.0, "regen_rate": 0.5}
            },
            LocationType.RESOURCE_NODE: {
                ResourceType.BUILDING_MATERIALS: {"amount": 50.0, "max_capacity": 100.0, "regen_rate": 0.2},
                ResourceType.COMPUTATIONAL_POWER: {"amount": 40.0, "max_capacity": 80.0, "regen_rate": 1.0}
            }
        }
        
        return defaults.get(location_type, {})
    
    async def _create_world_event(
        self,
        event_type: str,
        location_id: Optional[str],
        participants: List[str],
        description: str,
        duration: Optional[timedelta] = None,
        effects: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a world event."""
        try:
            event_id = f"event_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.world_events)}"
            
            event = WorldEvent(
                event_id=event_id,
                event_type=event_type,
                location_id=location_id,
                participants=participants,
                description=description,
                timestamp=datetime.now(),
                duration=duration,
                effects=effects or {}
            )
            
            self.world_events.append(event)
            
            # Keep only recent events (last 1000)
            if len(self.world_events) > 1000:
                self.world_events = self.world_events[-1000:]
            
            self.world_stats["world_events"] += 1
            
            return event_id
            
        except Exception as e:
            self.logger.error(f"Failed to create world event: {e}")
            return ""
    
    async def _complete_construction_projects(self) -> None:
        """Complete any ongoing construction projects during shutdown."""
        try:
            for project_id, project in list(self.construction_projects.items()):
                if project.status == "in_progress":
                    project.status = "cancelled"
                    project.progress = min(1.0, project.progress)
                    
                    self.logger.info(f"Cancelled construction project {project_id} due to shutdown")
                    
        except Exception as e:
            self.logger.error(f"Failed to complete construction projects: {e}")
    
    async def _save_world_state(self) -> None:
        """Save world state to storage."""
        # Placeholder for saving to persistent storage
        pass  
              {
                    "id": event.event_id,
                    "type": event.event_type,
                    "location_id": event.location_id,
                    "description": event.description,
                    "participants": event.participants,
                    "timestamp": event.timestamp.isoformat(),
                    "duration": event.duration.total_seconds() / 3600.0 if event.duration else None,
                    "effects": event.effects
                }
                for event in filtered_events
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get world events: {e}")
            return []
    
    # Private helper methods
    
    async def _create_initial_world(self) -> None:
        """Create the initial world structure with basic locations."""
        try:
            # Create central hub
            central_hub = Location(
                location_id="central_hub",
                name="Central Hub",
                description="The main gathering place for all agents in the virtual world",
                location_type=LocationType.SOCIAL_HUB,
                coordinates=Coordinates(self.world_size[0] / 2, self.world_size[1] / 2, 0),
                capacity=100,
                available_activities=[
                    ActivityType.SOCIALIZING,
                    ActivityType.COLLABORATION,
                    ActivityType.TRADING
                ]
            )
            
            # Add basic resources to central hub
            central_hub.resources["social_energy"] = Resource(
                resource_id="central_social_energy",
                resource_type=ResourceType.SOCIAL_ENERGY,
                quantity=1000.0,
                quality=0.8,
                location_id="central_hub",
                regeneration_rate=10.0,
                max_quantity=1000.0
            )
            
            self.locations["central_hub"] = central_hub
            
            # Create residential areas
            for i in range(5):
                residential = Location(
                    location_id=f"residential_{i}",
                    name=f"Residential District {i+1}",
                    description=f"A peaceful residential area for agents to rest and recharge",
                    location_type=LocationType.RESIDENTIAL,
                    coordinates=Coordinates(
                        random.uniform(50, self.world_size[0] - 50),
                        random.uniform(50, self.world_size[1] - 50),
                        0
                    ),
                    capacity=20,
                    available_activities=[ActivityType.RESTING, ActivityType.SOCIALIZING],
                    connections=["central_hub"]
                )
                self.locations[f"residential_{i}"] = residential
                central_hub.connections.append(f"residential_{i}")
            
            # Create workspaces
            for i in range(3):
                workspace = Location(
                    location_id=f"workspace_{i}",
                    name=f"Collaborative Workspace {i+1}",
                    description="A space designed for productive work and collaboration",
                    location_type=LocationType.WORKSPACE,
                    coordinates=Coordinates(
                        random.uniform(100, self.world_size[0] - 100),
                        random.uniform(100, self.world_size[1] - 100),
                        0
                    ),
                    capacity=15,
                    available_activities=[
                        ActivityType.COLLABORATION,
                        ActivityType.CREATION,
                        ActivityType.RESEARCH
                    ],
                    connections=["central_hub"]
                )
                
                # Add computational resources
                workspace.resources["computational_power"] = Resource(
                    resource_id=f"workspace_{i}_compute",
                    resource_type=ResourceType.COMPUTATIONAL_POWER,
                    quantity=500.0,
                    quality=0.9,
                    location_id=f"workspace_{i}",
                    regeneration_rate=5.0,
                    max_quantity=500.0
                )
                
                self.locations[f"workspace_{i}"] = workspace
                central_hub.connections.append(f"workspace_{i}")
            
            # Create laboratories
            for i in range(2):
                lab = Location(
                    location_id=f"laboratory_{i}",
                    name=f"Research Laboratory {i+1}",
                    description="Advanced research facility with specialized equipment",
                    location_type=LocationType.LABORATORY,
                    coordinates=Coordinates(
                        random.uniform(150, self.world_size[0] - 150),
                        random.uniform(150, self.world_size[1] - 150),
                        0
                    ),
                    capacity=10,
                    available_activities=[
                        ActivityType.RESEARCH,
                        ActivityType.LEARNING,
                        ActivityType.TRAINING
                    ],
                    connections=["central_hub"]
                )
                
                # Add research tools and knowledge databases
                lab.resources["research_tools"] = Resource(
                    resource_id=f"lab_{i}_tools",
                    resource_type=ResourceType.RESEARCH_TOOLS,
                    quantity=200.0,
                    quality=0.95,
                    location_id=f"laboratory_{i}",
                    regeneration_rate=2.0,
                    max_quantity=200.0
                )
                
                lab.resources["knowledge_database"] = Resource(
                    resource_id=f"lab_{i}_knowledge",
                    resource_type=ResourceType.KNOWLEDGE_DATABASE,
                    quantity=1000.0,
                    quality=0.85,
                    location_id=f"laboratory_{i}",
                    regeneration_rate=1.0,
                    max_quantity=1000.0
                )
                
                self.locations[f"laboratory_{i}"] = lab
                central_hub.connections.append(f"laboratory_{i}")
            
            # Create library
            library = Location(
                location_id="grand_library",
                name="Grand Library",
                description="A vast repository of knowledge and learning materials",
                location_type=LocationType.LIBRARY,
                coordinates=Coordinates(
                    self.world_size[0] * 0.3,
                    self.world_size[1] * 0.7,
                    0
                ),
                capacity=50,
                available_activities=[
                    ActivityType.LEARNING,
                    ActivityType.RESEARCH,
                    ActivityType.RESTING
                ],
                connections=["central_hub"]
            )
            
            # Add massive knowledge database
            library.resources["knowledge_database"] = Resource(
                resource_id="library_knowledge",
                resource_type=ResourceType.KNOWLEDGE_DATABASE,
                quantity=5000.0,
                quality=0.9,
                location_id="grand_library",
                regeneration_rate=5.0,
                max_quantity=5000.0
            )
            
            self.locations["grand_library"] = library
            central_hub.connections.append("grand_library")
            
            # Create resource center
            resource_center = Location(
                location_id="resource_center",
                name="Resource Distribution Center",
                description="Central hub for resource collection and distribution",
                location_type=LocationType.RESOURCE_CENTER,
                coordinates=Coordinates(
                    self.world_size[0] * 0.7,
                    self.world_size[1] * 0.3,
                    0
                ),
                capacity=30,
                available_activities=[
                    ActivityType.RESOURCE_GATHERING,
                    ActivityType.TRADING,
                    ActivityType.COLLABORATION
                ],
                connections=["central_hub"]
            )
            
            # Add various resources
            for resource_type in [ResourceType.BUILDING_MATERIALS, ResourceType.CREATIVE_MATERIALS, ResourceType.ENERGY_CRYSTALS]:
                resource_center.resources[resource_type.value] = Resource(
                    resource_id=f"center_{resource_type.value}",
                    resource_type=resource_type,
                    quantity=800.0,
                    quality=0.8,
                    location_id="resource_center",
                    regeneration_rate=8.0,
                    max_quantity=800.0
                )
            
            self.locations["resource_center"] = resource_center
            central_hub.connections.append("resource_center")
            
            # Create wilderness areas for exploration
            for i in range(3):
                wilderness = Location(
                    location_id=f"wilderness_{i}",
                    name=f"Wilderness Zone {i+1}",
                    description="Unexplored wilderness with hidden resources and mysteries",
                    location_type=LocationType.WILDERNESS,
                    coordinates=Coordinates(
                        random.uniform(0, self.world_size[0]),
                        random.uniform(0, self.world_size[1]),
                        random.uniform(0, self.world_size[2])
                    ),
                    capacity=5,
                    available_activities=[
                        ActivityType.EXPLORATION,
                        ActivityType.RESOURCE_GATHERING,
                        ActivityType.RESTING
                    ]
                )
                
                # Add rare resources with low quantities
                if random.random() < 0.7:  # 70% chance of having rare artifacts
                    wilderness.resources["rare_artifacts"] = Resource(
                        resource_id=f"wilderness_{i}_artifacts",
                        resource_type=ResourceType.RARE_ARTIFACTS,
                        quantity=random.uniform(10, 50),
                        quality=random.uniform(0.6, 1.0),
                        location_id=f"wilderness_{i}",
                        regeneration_rate=0.1,
                        max_quantity=100.0
                    )
                
                self.locations[f"wilderness_{i}"] = wilderness
            
            # Update world statistics
            self.world_stats["total_locations"] = len(self.locations)
            
            self.logger.info(f"Created initial world with {len(self.locations)} locations")
            
        except Exception as e:
            self.logger.error(f"Failed to create initial world: {e}")
            raise
    
    async def _start_world_processes(self) -> None:
        """Start background processes for the world."""
        try:
            # Start resource regeneration
            asyncio.create_task(self._resource_regeneration_loop())
            
            # Start world event cleanup
            asyncio.create_task(self._event_cleanup_loop())
            
            self.logger.info("World processes started")
            
        except Exception as e:
            self.logger.error(f"Failed to start world processes: {e}")
            raise
    
    async def _stop_world_processes(self) -> None:
        """Stop background world processes."""
        # In a real implementation, you would cancel the background tasks
        self.logger.info("World processes stopped")
    
    async def _resource_regeneration_loop(self) -> None:
        """Background loop to regenerate resources."""
        while True:
            try:
                await asyncio.sleep(self.world_config["resource_regeneration_interval"] * 3600)  # Convert to seconds
                
                for location in self.locations.values():
                    for resource in location.resources.values():
                        if resource.regeneration_rate > 0 and resource.quantity < resource.max_quantity:
                            regenerated = min(
                                resource.regeneration_rate * self.world_config["resource_regeneration_interval"],
                                resource.max_quantity - resource.quantity
                            )
                            resource.quantity += regenerated
                            resource.last_updated = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Error in resource regeneration: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _event_cleanup_loop(self) -> None:
        """Background loop to clean up old events."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Keep only recent events
                cutoff_time = datetime.now() - timedelta(days=7)
                self.world_events = [
                    event for event in self.world_events
                    if event.timestamp >= cutoff_time
                ]
                
                # Limit total events
                if len(self.world_events) > self.world_config["max_events_history"]:
                    self.world_events = self.world_events[-self.world_config["max_events_history"]:]
                
            except Exception as e:
                self.logger.error(f"Error in event cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def _create_emergency_location(self, location_type: LocationType) -> Location:
        """Create an emergency location when needed."""
        location_id = f"emergency_{location_type.value}_{len(self.locations)}"
        
        location = Location(
            location_id=location_id,
            name=f"Emergency {location_type.value.replace('_', ' ').title()}",
            description=f"Automatically created {location_type.value} location",
            location_type=location_type,
            coordinates=Coordinates(
                random.uniform(0, self.world_size[0]),
                random.uniform(0, self.world_size[1]),
                0
            ),
            capacity=10,
            available_activities=[ActivityType.RESTING, ActivityType.SOCIALIZING]
        )
        
        self.locations[location_id] = location
        self.world_stats["total_locations"] += 1
        
        self.logger.warning(f"Created emergency location: {location_id}")
        
        return location
    
    async def _check_location_access(self, agent_id: str, location: Location) -> bool:
        """Check if an agent can access a location."""
        # Basic access check - can be extended with more complex rules
        if not location.access_restrictions:
            return True
        
        # Check specific restrictions
        if "required_level" in location.access_restrictions:
            # This would need to be implemented with agent stats
            pass
        
        if "banned_agents" in location.access_restrictions:
            if agent_id in location.access_restrictions["banned_agents"]:
                return False
        
        return True
    
    async def _check_resource_access(self, agent_id: str, resource: Resource) -> bool:
        """Check if an agent can access a resource."""
        # Basic access check - can be extended with more complex rules
        if not resource.access_requirements:
            return True
        
        # Check specific requirements
        if "required_skill" in resource.access_requirements:
            # This would need to be implemented with agent skills
            pass
        
        return True
    
    async def _calculate_activity_effects(self, agent_id: str, activity_type: ActivityType, duration_hours: float, location: Location) -> Dict[str, float]:
        """Calculate the effects of completing an activity."""
        base_effects = self.activity_effects.get(activity_type, {})
        
        # Scale effects by duration
        scaled_effects = {}
        for effect, value in base_effects.items():
            scaled_effects[effect] = value * duration_hours
        
        # Apply location modifiers
        location_modifier = 1.0
        if location.location_type == LocationType.LABORATORY and activity_type == ActivityType.RESEARCH:
            location_modifier = 1.5
        elif location.location_type == LocationType.LIBRARY and activity_type == ActivityType.LEARNING:
            location_modifier = 1.3
        elif location.location_type == LocationType.WORKSPACE and activity_type == ActivityType.COLLABORATION:
            location_modifier = 1.2
        
        # Apply modifiers
        for effect in scaled_effects:
            scaled_effects[effect] *= location_modifier
        
        return scaled_effects
    
    async def _create_world_event(self, event_type: str, location_id: str, description: str, participants: List[str], duration: Optional[timedelta] = None) -> None:
        """Create a new world event."""
        event = WorldEvent(
            event_id=f"event_{len(self.world_events)}_{datetime.now().timestamp()}",
            event_type=event_type,
            location_id=location_id,
            description=description,
            participants=participants,
            duration=duration
        )
        
        self.world_events.append(event)
        self.world_stats["total_events"] += 1
        
        # Update location activity timestamp
        if location_id in self.locations:
            self.locations[location_id].last_activity = datetime.now()
    
    async def _save_world_state(self) -> None:
        """Save the current world state."""
        try:
            world_state = {
                "world_size": self.world_size,
                "locations": {
                    loc_id: {
                        "location_id": loc.location_id,
                        "name": loc.name,
                        "description": loc.description,
                        "location_type": loc.location_type.value,
                        "coordinates": {"x": loc.coordinates.x, "y": loc.coordinates.y, "z": loc.coordinates.z},
                        "capacity": loc.capacity,
                        "current_occupants": list(loc.current_occupants),
                        "available_activities": [act.value for act in loc.available_activities],
                        "connections": loc.connections,
                        "environment_properties": loc.environment_properties,
                        "access_restrictions": loc.access_restrictions
                    }
                    for loc_id, loc in self.locations.items()
                },
                "agent_positions": {
                    agent_id: {
                        "agent_id": pos.agent_id,
                        "current_location_id": pos.current_location_id,
                        "coordinates": {"x": pos.coordinates.x, "y": pos.coordinates.y, "z": pos.coordinates.z},
                        "current_activity": pos.current_activity.value if pos.current_activity else None
                    }
                    for agent_id, pos in self.agent_positions.items()
                },
                "world_stats": self.world_stats,
                "timestamp": datetime.now().isoformat()
            }
            
            # In a real implementation, this would save to a file or database
            self.logger.info("World state saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save world state: {e}")