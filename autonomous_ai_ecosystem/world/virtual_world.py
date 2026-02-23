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


class VirtualWorld(AgentModule):
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