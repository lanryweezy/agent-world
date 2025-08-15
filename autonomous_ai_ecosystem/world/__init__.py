"""
Virtual world module for autonomous AI ecosystem.

This module provides the virtual environment where agents can interact,
move around, perform activities, and gather resources. It also includes
collaborative construction mechanics for world building.
"""

from .virtual_world import (
    VirtualWorld,
    Location,
    LocationType,
    Resource,
    ResourceType,
    ActivityType,
    Coordinates,
    AgentPosition,
    WorldEvent
)

from .construction import (
    CollaborativeConstruction,
    ConstructionProject,
    ProjectType,
    ProjectStatus,
    ContributionType,
    ConflictType,
    ResourceRequirement,
    ProjectContribution,
    ConstructionConflict
)

__all__ = [
    "VirtualWorld",
    "Location",
    "LocationType", 
    "Resource",
    "ResourceType",
    "ActivityType",
    "Coordinates",
    "AgentPosition",
    "WorldEvent",
    "CollaborativeConstruction",
    "ConstructionProject",
    "ProjectType",
    "ProjectStatus",
    "ContributionType",
    "ConflictType",
    "ResourceRequirement",
    "ProjectContribution",
    "ConstructionConflict"
]