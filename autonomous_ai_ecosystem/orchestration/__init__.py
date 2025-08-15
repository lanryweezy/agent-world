"""
Orchestration module for agent lifecycle and process management.

This module provides agent spawning, monitoring, termination,
lifecycle orchestration, and distributed system coordination capabilities.
"""

from .agent_manager import (
    AgentManager,
    AgentProcess,
    AgentStatus,
    ProcessState,
    LifecycleEvent
)

from .distributed_coordinator import (
    DistributedCoordinator,
    DistributedNode,
    NodeRole,
    NodeStatus,
    SyncOperation,
    SyncStatus,
    ResourceAllocation,
    ResourceType
)

__all__ = [
    "AgentManager",
    "AgentProcess", 
    "AgentStatus",
    "ProcessState",
    "LifecycleEvent",
    "DistributedCoordinator",
    "DistributedNode",
    "NodeRole",
    "NodeStatus",
    "SyncOperation",
    "SyncStatus",
    "ResourceAllocation",
    "ResourceType"
]