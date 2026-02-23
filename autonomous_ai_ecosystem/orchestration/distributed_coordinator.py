"""
Distributed system coordination and state synchronization.

This module implements distributed database management, system-wide state
synchronization, load balancing, and resource allocation systems.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import sqlite3
import threading

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class NodeRole(Enum):
    """Roles that nodes can have in the distributed system."""
    COORDINATOR = "coordinator"
    WORKER = "worker"
    BACKUP = "backup"
    OBSERVER = "observer"


class NodeStatus(Enum):
    """Status of nodes in the distributed system."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    JOINING = "joining"
    LEAVING = "leaving"
    FAILED = "failed"
    RECOVERING = "recovering"


class SyncStatus(Enum):
    """Status of synchronization operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class ResourceType(Enum):
    """Types of resources that can be allocated."""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    AGENT_SLOTS = "agent_slots"
    CUSTOM = "custom"


@dataclass
class DistributedNode:
    """Represents a node in the distributed system."""
    node_id: str
    host: str
    port: int
    
    # Node properties
    role: NodeRole = NodeRole.WORKER
    status: NodeStatus = NodeStatus.INACTIVE
    
    # Capabilities
    max_agents: int = 10
    max_cpu_percent: float = 80.0
    max_memory_mb: int = 2048
    
    # Current state
    current_agents: int = 0
    current_cpu_percent: float = 0.0
    current_memory_mb: float = 0.0
    
    # Health and connectivity
    last_heartbeat: Optional[datetime] = None
    heartbeat_interval: int = 30
    response_time_ms: float = 0.0
    
    # Synchronization
    last_sync: Optional[datetime] = None
    sync_version: int = 0
    
    # Metadata
    joined_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_load_score(self) -> float:
        """Calculate load score for load balancing."""
        cpu_load = self.current_cpu_percent / 100.0
        memory_load = self.current_memory_mb / self.max_memory_mb
        agent_load = self.current_agents / self.max_agents
        
        # Weighted average
        return (cpu_load * 0.4 + memory_load * 0.3 + agent_load * 0.3)
    
    def can_accept_agent(self) -> bool:
        """Check if node can accept a new agent."""
        return (self.status == NodeStatus.ACTIVE and
                self.current_agents < self.max_agents and
                self.current_cpu_percent < self.max_cpu_percent and
                self.current_memory_mb < self.max_memory_mb)
    
    def is_healthy(self) -> bool:
        """Check if node is healthy based on heartbeat."""
        if not self.last_heartbeat:
            return False
        
        timeout = timedelta(seconds=self.heartbeat_interval * 3)
        return datetime.now() - self.last_heartbeat < timeout


@dataclass
class SyncOperation:
    """Represents a synchronization operation."""
    operation_id: str
    operation_type: str  # create, update, delete
    table_name: str
    
    # Operation data
    data: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Synchronization metadata
    source_node: str = ""
    target_nodes: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    version: int = 0
    
    # Status tracking
    status: SyncStatus = SyncStatus.PENDING
    completed_nodes: Set[str] = field(default_factory=set)
    failed_nodes: Set[str] = field(default_factory=set)
    
    # Conflict resolution
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    resolution_strategy: str = "latest_wins"
    
    def is_complete(self) -> bool:
        """Check if synchronization is complete."""
        return len(self.completed_nodes) == len(self.target_nodes)
    
    def has_conflicts(self) -> bool:
        """Check if there are unresolved conflicts."""
        return len(self.conflicts) > 0


@dataclass
class ResourceAllocation:
    """Represents a resource allocation."""
    allocation_id: str
    resource_type: ResourceType
    amount: float
    
    # Allocation details
    allocated_to: str  # agent_id or service_id
    allocated_by: str  # node_id
    
    # Constraints
    priority: int = 5  # 1-10, 10 being highest
    duration_seconds: Optional[int] = None
    
    # Status
    active: bool = True
    allocated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # Usage tracking
    actual_usage: float = 0.0
    peak_usage: float = 0.0
    
    def is_expired(self) -> bool:
        """Check if allocation has expired."""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False
    
    def get_utilization(self) -> float:
        """Get resource utilization ratio."""
        if self.amount > 0:
            return self.actual_usage / self.amount
        return 0.0


class DistributedCoordinator(AgentModule):
    """
    Distributed system coordination and state synchronization.
    
    Provides distributed database management, system-wide state synchronization,
    load balancing, and resource allocation capabilities.
    """
    
    def __init__(self, agent_id: str = "distributed_coordinator", node_id: Optional[str] = None):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "distributed_coordinator")
        
        # Node identification
        self.node_id = node_id or f"node_{uuid.uuid4().hex[:8]}"
        
        # Core data structures
        self.nodes: Dict[str, DistributedNode] = {}
        self.sync_operations: Dict[str, SyncOperation] = {}
        self.resource_allocations: Dict[str, ResourceAllocation] = {}
        
        # Database connections
        self.local_db: Optional[sqlite3.Connection] = None
        self.db_lock = threading.Lock()
        
        # Coordination state
        self.is_coordinator = False
        self.coordinator_node_id: Optional[str] = None
        self.election_in_progress = False
        
        # Synchronization
        self.sync_queue: asyncio.Queue = asyncio.Queue()
        self.sync_task: Optional[asyncio.Task] = None
        
        # Load balancing
        self.load_balancer_task: Optional[asyncio.Task] = None
        self.rebalance_threshold = 0.3  # Trigger rebalancing when load difference > 30%
        
        # Configuration
        self.config = {
            "database_file": "distributed_state.db",
            "heartbeat_interval": 30,
            "sync_interval": 10,
            "election_timeout": 15,
            "max_sync_retries": 3,
            "load_balance_interval": 60,
            "resource_cleanup_interval": 300,
            "enable_auto_failover": True,
            "enable_load_balancing": True,
            "consensus_threshold": 0.5  # Majority required for decisions
        }
        
        # Statistics
        self.stats = {
            "total_nodes": 0,
            "active_nodes": 0,
            "total_sync_operations": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "conflicts_resolved": 0,
            "load_balance_operations": 0,
            "resource_allocations": 0,
            "coordinator_elections": 0,
            "average_sync_time": 0.0,
            "nodes_by_role": {role.value: 0 for role in NodeRole},
            "nodes_by_status": {status.value: 0 for status in NodeStatus}
        }
        
        # Counters
        self.operation_counter = 0
        self.allocation_counter = 0
        
        self.logger.info(f"Distributed coordinator initialized (Node: {self.node_id})")
    
    async def initialize(self) -> None:
        """Initialize the distributed coordinator."""
        try:
            # Initialize local database
            await self._initialize_database()
            
            # Register this node
            await self._register_self()
            
            # Start background tasks
            self.sync_task = asyncio.create_task(self._sync_loop())
            
            if self.config["enable_load_balancing"]:
                self.load_balancer_task = asyncio.create_task(self._load_balancer_loop())
            
            asyncio.create_task(self._heartbeat_loop())
            asyncio.create_task(self._cleanup_loop())
            
            # Start coordinator election if no coordinator exists
            await self._check_coordinator_status()
            
            self.logger.info("Distributed coordinator initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize distributed coordinator: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the distributed coordinator."""
        try:
            # Cancel background tasks
            if self.sync_task:
                self.sync_task.cancel()
                try:
                    await self.sync_task
                except asyncio.CancelledError:
                    pass
            
            if self.load_balancer_task:
                self.load_balancer_task.cancel()
                try:
                    await self.load_balancer_task
                except asyncio.CancelledError:
                    pass
            
            # Update node status
            await self._update_node_status(self.node_id, NodeStatus.LEAVING)
            
            # Close database connection
            if self.local_db:
                self.local_db.close()
            
            self.logger.info("Distributed coordinator shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during distributed coordinator shutdown: {e}")
    
    async def join_cluster(
        self,
        coordinator_host: str,
        coordinator_port: int,
        node_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Join an existing cluster."""
        try:
            # Create node configuration
            config = node_config or {}
            
            node = DistributedNode(
                node_id=self.node_id,
                host=config.get("host", "localhost"),
                port=config.get("port", 8080),
                role=NodeRole(config.get("role", NodeRole.WORKER.value)),
                max_agents=config.get("max_agents", 10),
                max_cpu_percent=config.get("max_cpu_percent", 80.0),
                max_memory_mb=config.get("max_memory_mb", 2048)
            )
            
            # Update status to joining
            node.status = NodeStatus.JOINING
            node.joined_at = datetime.now()
            
            # Store node information
            self.nodes[self.node_id] = node
            
            # TODO: Implement actual network communication to join cluster
            # For now, simulate successful join
            node.status = NodeStatus.ACTIVE
            
            # Update statistics
            self.stats["total_nodes"] += 1
            self.stats["active_nodes"] += 1
            self.stats["nodes_by_role"][node.role.value] += 1
            self.stats["nodes_by_status"][node.status.value] += 1
            
            log_agent_event(
                self.agent_id,
                "cluster_joined",
                {
                    "node_id": self.node_id,
                    "coordinator_host": coordinator_host,
                    "coordinator_port": coordinator_port,
                    "role": node.role.value
                }
            )
            
            self.logger.info(f"Successfully joined cluster (Coordinator: {coordinator_host}:{coordinator_port})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to join cluster: {e}")
            return False
    
    async def leave_cluster(self) -> bool:
        """Leave the current cluster."""
        try:
            if self.node_id not in self.nodes:
                return True
            
            node = self.nodes[self.node_id]
            node.status = NodeStatus.LEAVING
            
            # If this node is the coordinator, trigger election
            if self.is_coordinator:
                await self._trigger_coordinator_election()
            
            # Migrate any allocated resources
            await self._migrate_resources()
            
            # Update node status
            node.status = NodeStatus.INACTIVE
            
            # Update statistics
            self.stats["active_nodes"] -= 1
            self.stats["nodes_by_status"][NodeStatus.ACTIVE.value] -= 1
            self.stats["nodes_by_status"][NodeStatus.INACTIVE.value] += 1
            
            log_agent_event(
                self.agent_id,
                "cluster_left",
                {"node_id": self.node_id}
            )
            
            self.logger.info("Successfully left cluster")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to leave cluster: {e}")
            return False
    
    async def sync_data(
        self,
        operation_type: str,
        table_name: str,
        data: Dict[str, Any],
        conditions: Optional[Dict[str, Any]] = None,
        target_nodes: Optional[List[str]] = None
    ) -> str:
        """Synchronize data across the distributed system."""
        try:
            # Create sync operation
            self.operation_counter += 1
            operation_id = f"sync_{self.operation_counter}_{datetime.now().timestamp()}"
            
            # Determine target nodes
            if target_nodes is None:
                target_nodes = [
                    node_id for node_id, node in self.nodes.items()
                    if node.status == NodeStatus.ACTIVE and node_id != self.node_id
                ]
            
            sync_op = SyncOperation(
                operation_id=operation_id,
                operation_type=operation_type,
                table_name=table_name,
                data=data,
                conditions=conditions or {},
                source_node=self.node_id,
                target_nodes=target_nodes,
                version=int(time.time() * 1000)  # Timestamp-based versioning
            )
            
            # Store operation
            self.sync_operations[operation_id] = sync_op
            
            # Add to sync queue
            await self.sync_queue.put(sync_op)
            
            # Update statistics
            self.stats["total_sync_operations"] += 1
            
            log_agent_event(
                self.agent_id,
                "sync_operation_created",
                {
                    "operation_id": operation_id,
                    "operation_type": operation_type,
                    "table_name": table_name,
                    "target_nodes": len(target_nodes)
                }
            )
            
            self.logger.info(f"Sync operation created: {operation_id}")
            
            return operation_id
            
        except Exception as e:
            self.logger.error(f"Failed to create sync operation: {e}")
            return ""
    
    async def allocate_resource(
        self,
        resource_type: ResourceType,
        amount: float,
        allocated_to: str,
        priority: int = 5,
        duration_seconds: Optional[int] = None
    ) -> str:
        """Allocate resources to an agent or service."""
        try:
            # Find best node for allocation
            best_node = await self._find_best_node_for_resource(resource_type, amount)
            
            if not best_node:
                self.logger.warning(f"No suitable node found for resource allocation: {resource_type.value}")
                return ""
            
            # Create allocation
            self.allocation_counter += 1
            allocation_id = f"alloc_{self.allocation_counter}_{datetime.now().timestamp()}"
            
            allocation = ResourceAllocation(
                allocation_id=allocation_id,
                resource_type=resource_type,
                amount=amount,
                allocated_to=allocated_to,
                allocated_by=best_node.node_id,
                priority=priority,
                duration_seconds=duration_seconds
            )
            
            # Set expiration if duration specified
            if duration_seconds:
                allocation.expires_at = datetime.now() + timedelta(seconds=duration_seconds)
            
            # Store allocation
            self.resource_allocations[allocation_id] = allocation
            
            # Update node resource usage
            await self._update_node_resource_usage(best_node, resource_type, amount, allocate=True)
            
            # Sync allocation across cluster
            await self.sync_data(
                operation_type="create",
                table_name="resource_allocations",
                data={
                    "allocation_id": allocation_id,
                    "resource_type": resource_type.value,
                    "amount": amount,
                    "allocated_to": allocated_to,
                    "allocated_by": best_node.node_id,
                    "priority": priority,
                    "allocated_at": allocation.allocated_at.isoformat(),
                    "expires_at": allocation.expires_at.isoformat() if allocation.expires_at else None
                }
            )
            
            # Update statistics
            self.stats["resource_allocations"] += 1
            
            log_agent_event(
                allocated_to,
                "resource_allocated",
                {
                    "allocation_id": allocation_id,
                    "resource_type": resource_type.value,
                    "amount": amount,
                    "node_id": best_node.node_id,
                    "priority": priority
                }
            )
            
            self.logger.info(f"Resource allocated: {allocation_id} ({resource_type.value}: {amount})")
            
            return allocation_id
            
        except Exception as e:
            self.logger.error(f"Failed to allocate resource: {e}")
            return ""
    
    async def deallocate_resource(self, allocation_id: str) -> bool:
        """Deallocate a resource."""
        try:
            if allocation_id not in self.resource_allocations:
                return False
            
            allocation = self.resource_allocations[allocation_id]
            
            # Find the node that has the allocation
            node = self.nodes.get(allocation.allocated_by)
            if node:
                await self._update_node_resource_usage(
                    node, allocation.resource_type, allocation.amount, allocate=False
                )
            
            # Mark as inactive
            allocation.active = False
            
            # Sync deallocation across cluster
            await self.sync_data(
                operation_type="update",
                table_name="resource_allocations",
                data={"active": False},
                conditions={"allocation_id": allocation_id}
            )
            
            log_agent_event(
                allocation.allocated_to,
                "resource_deallocated",
                {
                    "allocation_id": allocation_id,
                    "resource_type": allocation.resource_type.value,
                    "amount": allocation.amount
                }
            )
            
            self.logger.info(f"Resource deallocated: {allocation_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deallocate resource: {e}")
            return False
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get comprehensive cluster status."""
        try:
            # Calculate cluster metrics
            active_nodes = [node for node in self.nodes.values() if node.status == NodeStatus.ACTIVE]
            total_agents = sum(node.current_agents for node in active_nodes)
            total_capacity = sum(node.max_agents for node in active_nodes)
            
            avg_cpu = sum(node.current_cpu_percent for node in active_nodes) / len(active_nodes) if active_nodes else 0
            avg_memory = sum(node.current_memory_mb for node in active_nodes) / len(active_nodes) if active_nodes else 0
            
            # Resource allocation summary
            active_allocations = [alloc for alloc in self.resource_allocations.values() if alloc.active]
            resource_summary = {}
            for resource_type in ResourceType:
                allocations = [alloc for alloc in active_allocations if alloc.resource_type == resource_type]
                resource_summary[resource_type.value] = {
                    "total_allocated": sum(alloc.amount for alloc in allocations),
                    "allocation_count": len(allocations),
                    "average_utilization": sum(alloc.get_utilization() for alloc in allocations) / len(allocations) if allocations else 0
                }
            
            return {
                "cluster_id": f"cluster_{self.node_id}",
                "coordinator_node": self.coordinator_node_id,
                "is_coordinator": self.is_coordinator,
                "total_nodes": len(self.nodes),
                "active_nodes": len(active_nodes),
                "total_agents": total_agents,
                "total_capacity": total_capacity,
                "utilization_ratio": total_agents / total_capacity if total_capacity > 0 else 0,
                "average_cpu_percent": avg_cpu,
                "average_memory_mb": avg_memory,
                "active_sync_operations": len([op for op in self.sync_operations.values() if op.status == SyncStatus.IN_PROGRESS]),
                "resource_allocations": len(active_allocations),
                "resource_summary": resource_summary,
                "statistics": self.stats,
                "nodes": [
                    {
                        "node_id": node.node_id,
                        "host": node.host,
                        "port": node.port,
                        "role": node.role.value,
                        "status": node.status.value,
                        "current_agents": node.current_agents,
                        "max_agents": node.max_agents,
                        "load_score": node.get_load_score(),
                        "is_healthy": node.is_healthy(),
                        "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None
                    }
                    for node in self.nodes.values()
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cluster status: {e}")
            return {}
    
    async def trigger_load_balancing(self) -> bool:
        """Manually trigger load balancing across the cluster."""
        try:
            return await self._perform_load_balancing()
        except Exception as e:
            self.logger.error(f"Failed to trigger load balancing: {e}")
            return False
    
    async def _initialize_database(self) -> None:
        """Initialize the local database."""
        try:
            self.local_db = sqlite3.connect(
                self.config["database_file"],
                check_same_thread=False
            )
            
            # Create tables
            with self.db_lock:
                cursor = self.local_db.cursor()
                
                # Nodes table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS nodes (
                        node_id TEXT PRIMARY KEY,
                        host TEXT NOT NULL,
                        port INTEGER NOT NULL,
                        role TEXT NOT NULL,
                        status TEXT NOT NULL,
                        max_agents INTEGER,
                        max_cpu_percent REAL,
                        max_memory_mb REAL,
                        current_agents INTEGER DEFAULT 0,
                        current_cpu_percent REAL DEFAULT 0,
                        current_memory_mb REAL DEFAULT 0,
                        last_heartbeat TEXT,
                        joined_at TEXT,
                        metadata TEXT,
                        sync_version INTEGER DEFAULT 0
                    )
                """)
                
                # Resource allocations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS resource_allocations (
                        allocation_id TEXT PRIMARY KEY,
                        resource_type TEXT NOT NULL,
                        amount REAL NOT NULL,
                        allocated_to TEXT NOT NULL,
                        allocated_by TEXT NOT NULL,
                        priority INTEGER DEFAULT 5,
                        active BOOLEAN DEFAULT 1,
                        allocated_at TEXT NOT NULL,
                        expires_at TEXT,
                        actual_usage REAL DEFAULT 0,
                        peak_usage REAL DEFAULT 0
                    )
                """)
                
                # Sync operations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sync_operations (
                        operation_id TEXT PRIMARY KEY,
                        operation_type TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        data TEXT NOT NULL,
                        conditions TEXT,
                        source_node TEXT NOT NULL,
                        target_nodes TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        version INTEGER NOT NULL,
                        status TEXT DEFAULT 'pending',
                        completed_nodes TEXT DEFAULT '[]',
                        failed_nodes TEXT DEFAULT '[]'
                    )
                """)
                
                self.local_db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _register_self(self) -> None:
        """Register this node in the cluster."""
        try:
            node = DistributedNode(
                node_id=self.node_id,
                host="localhost",  # TODO: Get actual host
                port=8080,  # TODO: Get actual port
                role=NodeRole.WORKER,
                status=NodeStatus.ACTIVE,
                joined_at=datetime.now()
            )
            
            self.nodes[self.node_id] = node
            
            # Store in database
            with self.db_lock:
                cursor = self.local_db.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO nodes 
                    (node_id, host, port, role, status, max_agents, max_cpu_percent, max_memory_mb, joined_at, sync_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node.node_id, node.host, node.port, node.role.value, node.status.value,
                    node.max_agents, node.max_cpu_percent, node.max_memory_mb,
                    node.joined_at.isoformat(), node.sync_version
                ))
                self.local_db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to register self: {e}")
            raise
    
    async def _check_coordinator_status(self) -> None:
        """Check if there's a coordinator and elect one if needed."""
        try:
            # Look for existing coordinator
            coordinator_nodes = [
                node for node in self.nodes.values()
                if node.role == NodeRole.COORDINATOR and node.status == NodeStatus.ACTIVE
            ]
            
            if coordinator_nodes:
                # Use the first active coordinator found
                self.coordinator_node_id = coordinator_nodes[0].node_id
                self.is_coordinator = (self.coordinator_node_id == self.node_id)
            else:
                # No coordinator found, trigger election
                await self._trigger_coordinator_election()
            
        except Exception as e:
            self.logger.error(f"Failed to check coordinator status: {e}")
    
    async def _trigger_coordinator_election(self) -> None:
        """Trigger coordinator election process."""
        try:
            if self.election_in_progress:
                return
            
            self.election_in_progress = True
            self.stats["coordinator_elections"] += 1
            
            # Simple election: node with lowest ID becomes coordinator
            active_nodes = [
                node for node in self.nodes.values()
                if node.status == NodeStatus.ACTIVE
            ]
            
            if not active_nodes:
                self.election_in_progress = False
                return
            
            # Sort by node_id and select first
            active_nodes.sort(key=lambda n: n.node_id)
            new_coordinator = active_nodes[0]
            
            # Update coordinator
            if new_coordinator.node_id == self.node_id:
                # This node becomes coordinator
                self.is_coordinator = True
                self.coordinator_node_id = self.node_id
                new_coordinator.role = NodeRole.COORDINATOR
                
                log_agent_event(
                    self.agent_id,
                    "coordinator_elected",
                    {"node_id": self.node_id}
                )
                
                self.logger.info(f"Elected as coordinator: {self.node_id}")
            else:
                # Another node is coordinator
                self.is_coordinator = False
                self.coordinator_node_id = new_coordinator.node_id
                
                self.logger.info(f"New coordinator elected: {new_coordinator.node_id}")
            
            self.election_in_progress = False
            
        except Exception as e:
            self.logger.error(f"Failed to trigger coordinator election: {e}")
            self.election_in_progress = False
    
    async def _sync_loop(self) -> None:
        """Main synchronization loop."""
        while True:
            try:
                # Wait for sync operation
                sync_op = await asyncio.wait_for(self.sync_queue.get(), timeout=1.0)
                
                # Process sync operation
                await self._process_sync_operation(sync_op)
                
            except asyncio.TimeoutError:
                # Check for pending operations
                await self._check_pending_operations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in sync loop: {e}")
    
    async def _process_sync_operation(self, sync_op: SyncOperation) -> None:
        """Process a synchronization operation."""
        try:
            sync_op.status = SyncStatus.IN_PROGRESS
            start_time = time.time()
            
            # Apply operation locally first
            await self._apply_sync_operation_locally(sync_op)
            
            # TODO: Send to target nodes (implement network communication)
            # For now, simulate successful sync to all nodes
            sync_op.completed_nodes = set(sync_op.target_nodes)
            sync_op.status = SyncStatus.COMPLETED
            
            # Update statistics
            sync_time = time.time() - start_time
            self.stats["successful_syncs"] += 1
            
            if self.stats["average_sync_time"] == 0:
                self.stats["average_sync_time"] = sync_time
            else:
                self.stats["average_sync_time"] = (
                    (self.stats["average_sync_time"] * (self.stats["successful_syncs"] - 1) + sync_time) /
                    self.stats["successful_syncs"]
                )
            
            log_agent_event(
                self.agent_id,
                "sync_operation_completed",
                {
                    "operation_id": sync_op.operation_id,
                    "sync_time": sync_time,
                    "target_nodes": len(sync_op.target_nodes)
                }
            )
            
        except Exception as e:
            sync_op.status = SyncStatus.FAILED
            self.stats["failed_syncs"] += 1
            self.logger.error(f"Failed to process sync operation {sync_op.operation_id}: {e}")
    
    async def _apply_sync_operation_locally(self, sync_op: SyncOperation) -> None:
        """Apply sync operation to local database."""
        try:
            with self.db_lock:
                cursor = self.local_db.cursor()
                
                if sync_op.operation_type == "create":
                    # Insert data
                    columns = list(sync_op.data.keys())
                    values = list(sync_op.data.values())
                    placeholders = ",".join(["?" for _ in columns])
                    
                    query = f"INSERT OR REPLACE INTO {sync_op.table_name} ({','.join(columns)}) VALUES ({placeholders})"
                    cursor.execute(query, values)
                
                elif sync_op.operation_type == "update":
                    # Update data
                    set_clause = ",".join([f"{key}=?" for key in sync_op.data.keys()])
                    values = list(sync_op.data.values())
                    
                    query = f"UPDATE {sync_op.table_name} SET {set_clause}"
                    
                    if sync_op.conditions:
                        where_clause = " AND ".join([f"{key}=?" for key in sync_op.conditions.keys()])
                        query += f" WHERE {where_clause}"
                        values.extend(list(sync_op.conditions.values()))
                    
                    cursor.execute(query, values)
                
                elif sync_op.operation_type == "delete":
                    # Delete data
                    query = f"DELETE FROM {sync_op.table_name}"
                    values = []
                    
                    if sync_op.conditions:
                        where_clause = " AND ".join([f"{key}=?" for key in sync_op.conditions.keys()])
                        query += f" WHERE {where_clause}"
                        values = list(sync_op.conditions.values())
                    
                    cursor.execute(query, values)
                
                self.local_db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to apply sync operation locally: {e}")
            raise
    
    async def _check_pending_operations(self) -> None:
        """Check for pending sync operations that need retry."""
        try:
            current_time = datetime.now()
            
            for sync_op in list(self.sync_operations.values()):
                if sync_op.status == SyncStatus.PENDING:
                    # Check if operation is too old
                    age_seconds = (current_time - sync_op.timestamp).total_seconds()
                    if age_seconds > 60:  # 1 minute timeout
                        sync_op.status = SyncStatus.FAILED
                        self.stats["failed_syncs"] += 1
                        
                        self.logger.warning(f"Sync operation timed out: {sync_op.operation_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to check pending operations: {e}")
    
    async def _load_balancer_loop(self) -> None:
        """Main load balancing loop."""
        while True:
            try:
                await asyncio.sleep(self.config["load_balance_interval"])
                
                if self.is_coordinator:
                    await self._perform_load_balancing()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in load balancer loop: {e}")
    
    async def _perform_load_balancing(self) -> bool:
        """Perform load balancing across nodes."""
        try:
            active_nodes = [node for node in self.nodes.values() if node.status == NodeStatus.ACTIVE]
            
            if len(active_nodes) < 2:
                return True  # No balancing needed with less than 2 nodes
            
            # Calculate load scores
            load_scores = [(node, node.get_load_score()) for node in active_nodes]
            load_scores.sort(key=lambda x: x[1])  # Sort by load score
            
            # Check if rebalancing is needed
            min_load = load_scores[0][1]
            max_load = load_scores[-1][1]
            
            if max_load - min_load < self.rebalance_threshold:
                return True  # No rebalancing needed
            
            # Find agents to migrate from high-load to low-load nodes
            high_load_node = load_scores[-1][0]
            low_load_node = load_scores[0][0]
            
            # TODO: Implement actual agent migration
            # For now, just log the recommendation
            self.logger.info(f"Load balancing recommended: migrate agents from {high_load_node.node_id} to {low_load_node.node_id}")
            
            self.stats["load_balance_operations"] += 1
            
            log_agent_event(
                self.agent_id,
                "load_balancing_performed",
                {
                    "high_load_node": high_load_node.node_id,
                    "low_load_node": low_load_node.node_id,
                    "load_difference": max_load - min_load
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to perform load balancing: {e}")
            return False
    
    async def _heartbeat_loop(self) -> None:
        """Send heartbeats and monitor node health."""
        while True:
            try:
                await asyncio.sleep(self.config["heartbeat_interval"])
                
                # Update own heartbeat
                if self.node_id in self.nodes:
                    self.nodes[self.node_id].last_heartbeat = datetime.now()
                
                # Check health of other nodes
                await self._check_node_health()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
    
    async def _check_node_health(self) -> None:
        """Check health of all nodes."""
        try:
            for node_id, node in list(self.nodes.items()):
                if node_id == self.node_id:
                    continue  # Skip self
                
                if not node.is_healthy() and node.status == NodeStatus.ACTIVE:
                    # Node appears to be unhealthy
                    node.status = NodeStatus.FAILED
                    
                    # Update statistics
                    self.stats["active_nodes"] -= 1
                    self.stats["nodes_by_status"][NodeStatus.ACTIVE.value] -= 1
                    self.stats["nodes_by_status"][NodeStatus.FAILED.value] += 1
                    
                    log_agent_event(
                        self.agent_id,
                        "node_failed",
                        {"node_id": node_id}
                    )
                    
                    self.logger.warning(f"Node marked as failed: {node_id}")
                    
                    # If failed node was coordinator, trigger election
                    if node_id == self.coordinator_node_id:
                        await self._trigger_coordinator_election()
            
        except Exception as e:
            self.logger.error(f"Failed to check node health: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Clean up expired resources and old operations."""
        while True:
            try:
                await asyncio.sleep(self.config["resource_cleanup_interval"])
                
                # Clean up expired resource allocations
                current_time = datetime.now()
                expired_allocations = [
                    alloc_id for alloc_id, alloc in self.resource_allocations.items()
                    if alloc.is_expired()
                ]
                
                for alloc_id in expired_allocations:
                    await self.deallocate_resource(alloc_id)
                
                # Clean up old sync operations
                old_operations = [
                    op_id for op_id, op in self.sync_operations.items()
                    if (current_time - op.timestamp).total_seconds() > 3600  # 1 hour
                ]
                
                for op_id in old_operations:
                    del self.sync_operations[op_id]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    async def _find_best_node_for_resource(
        self,
        resource_type: ResourceType,
        amount: float
    ) -> Optional[DistributedNode]:
        """Find the best node for resource allocation."""
        try:
            # Get nodes that can accept the resource
            suitable_nodes = [
                node for node in self.nodes.values()
                if node.status == NodeStatus.ACTIVE and node.can_accept_agent()
            ]
            
            if not suitable_nodes:
                return None
            
            # Sort by load score (prefer less loaded nodes)
            suitable_nodes.sort(key=lambda n: n.get_load_score())
            
            return suitable_nodes[0]
            
        except Exception as e:
            self.logger.error(f"Failed to find best node for resource: {e}")
            return None
    
    async def _update_node_resource_usage(
        self,
        node: DistributedNode,
        resource_type: ResourceType,
        amount: float,
        allocate: bool = True
    ) -> None:
        """Update node resource usage."""
        try:
            multiplier = 1 if allocate else -1
            
            if resource_type == ResourceType.AGENT_SLOTS:
                node.current_agents += int(amount * multiplier)
            elif resource_type == ResourceType.MEMORY:
                node.current_memory_mb += amount * multiplier
            # Add other resource types as needed
            
        except Exception as e:
            self.logger.error(f"Failed to update node resource usage: {e}")
    
    async def _migrate_resources(self) -> None:
        """Migrate resources from this node to other nodes."""
        try:
            # Find allocations on this node
            node_allocations = [
                alloc for alloc in self.resource_allocations.values()
                if alloc.allocated_by == self.node_id and alloc.active
            ]
            
            for allocation in node_allocations:
                # Find alternative node
                new_node = await self._find_best_node_for_resource(
                    allocation.resource_type,
                    allocation.amount
                )
                
                if new_node:
                    # Update allocation
                    allocation.allocated_by = new_node.node_id
                    
                    # Sync the change
                    await self.sync_data(
                        operation_type="update",
                        table_name="resource_allocations",
                        data={"allocated_by": new_node.node_id},
                        conditions={"allocation_id": allocation.allocation_id}
                    )
                    
                    self.logger.info(f"Migrated resource allocation {allocation.allocation_id} to {new_node.node_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to migrate resources: {e}")
    
    async def _update_node_status(self, node_id: str, status: NodeStatus) -> None:
        """Update node status."""
        try:
            if node_id in self.nodes:
                old_status = self.nodes[node_id].status
                self.nodes[node_id].status = status
                
                # Update statistics
                self.stats["nodes_by_status"][old_status.value] -= 1
                self.stats["nodes_by_status"][status.value] += 1
                
                # Sync status change
                await self.sync_data(
                    operation_type="update",
                    table_name="nodes",
                    data={"status": status.value},
                    conditions={"node_id": node_id}
                )
            
        except Exception as e:
            self.logger.error(f"Failed to update node status: {e}")