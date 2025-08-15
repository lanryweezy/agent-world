"""
Unit tests for distributed system coordination.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.orchestration.distributed_coordinator import (
    DistributedCoordinator,
    DistributedNode,
    NodeRole,
    NodeStatus,
    SyncOperation,
    SyncStatus,
    ResourceAllocation,
    ResourceType
)


@pytest_asyncio.fixture
async def coordinator():
    """Create distributed coordinator for testing."""
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_distributed.db")
    
    coord = DistributedCoordinator("test_coordinator", "test_node_1")
    coord.config["database_file"] = db_file
    coord.config["heartbeat_interval"] = 1  # Fast for testing
    coord.config["sync_interval"] = 1
    coord.config["load_balance_interval"] = 2
    
    await coord.initialize()
    
    yield coord
    
    await coord.shutdown()
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_coordinator_initialization(coordinator):
    """Test coordinator initialization."""
    assert coordinator.agent_id == "test_coordinator"
    assert coordinator.node_id == "test_node_1"
    assert coordinator.local_db is not None
    assert coordinator.sync_task is not None
    assert coordinator.node_id in coordinator.nodes
    
    # Check self-registration
    self_node = coordinator.nodes[coordinator.node_id]
    assert self_node.node_id == coordinator.node_id
    assert self_node.status == NodeStatus.ACTIVE


@pytest.mark.asyncio
async def test_distributed_node_creation():
    """Test distributed node data structure."""
    node = DistributedNode(
        node_id="test_node",
        host="localhost",
        port=8080,
        role=NodeRole.WORKER,
        max_agents=20,
        max_cpu_percent=75.0,
        max_memory_mb=1024
    )
    
    assert node.node_id == "test_node"
    assert node.host == "localhost"
    assert node.port == 8080
    assert node.role == NodeRole.WORKER
    assert node.status == NodeStatus.INACTIVE
    assert node.max_agents == 20
    assert node.max_cpu_percent == 75.0
    assert node.max_memory_mb == 1024
    assert node.current_agents == 0


@pytest.mark.asyncio
async def test_node_load_calculation():
    """Test node load score calculation."""
    node = DistributedNode(
        node_id="test_node",
        host="localhost",
        port=8080,
        max_agents=10,
        max_cpu_percent=100.0,
        max_memory_mb=1000
    )
    
    # Set current usage
    node.current_agents = 5  # 50% agent load
    node.current_cpu_percent = 60.0  # 60% CPU load
    node.current_memory_mb = 400  # 40% memory load
    
    load_score = node.get_load_score()
    
    # Expected: (0.6 * 0.4) + (0.4 * 0.3) + (0.5 * 0.3) = 0.24 + 0.12 + 0.15 = 0.51
    assert abs(load_score - 0.51) < 0.01


@pytest.mark.asyncio
async def test_node_can_accept_agent():
    """Test node capacity checking."""
    node = DistributedNode(
        node_id="test_node",
        host="localhost",
        port=8080,
        status=NodeStatus.ACTIVE,
        max_agents=10,
        max_cpu_percent=80.0,
        max_memory_mb=1000
    )
    
    # Node should accept agents initially
    assert node.can_accept_agent()
    
    # Fill up agents
    node.current_agents = 10
    assert not node.can_accept_agent()
    
    # Reset agents but max out CPU
    node.current_agents = 5
    node.current_cpu_percent = 85.0
    assert not node.can_accept_agent()
    
    # Reset CPU but max out memory
    node.current_cpu_percent = 50.0
    node.current_memory_mb = 1100
    assert not node.can_accept_agent()


@pytest.mark.asyncio
async def test_node_health_check():
    """Test node health checking."""
    node = DistributedNode(
        node_id="test_node",
        host="localhost",
        port=8080,
        heartbeat_interval=30
    )
    
    # No heartbeat yet
    assert not node.is_healthy()
    
    # Recent heartbeat
    node.last_heartbeat = datetime.now()
    assert node.is_healthy()
    
    # Old heartbeat
    node.last_heartbeat = datetime.now() - timedelta(seconds=100)
    assert not node.is_healthy()


@pytest.mark.asyncio
async def test_join_cluster(coordinator):
    """Test joining a cluster."""
    success = await coordinator.join_cluster(
        coordinator_host="coordinator.example.com",
        coordinator_port=8080,
        node_config={
            "host": "worker.example.com",
            "port": 8081,
            "role": "worker",
            "max_agents": 15
        }
    )
    
    assert success
    
    # Check node was updated
    node = coordinator.nodes[coordinator.node_id]
    assert node.status == NodeStatus.ACTIVE
    assert node.max_agents == 15
    
    # Check statistics
    assert coordinator.stats["total_nodes"] == 1
    assert coordinator.stats["active_nodes"] == 1


@pytest.mark.asyncio
async def test_leave_cluster(coordinator):
    """Test leaving a cluster."""
    # First join
    await coordinator.join_cluster("coordinator.example.com", 8080)
    
    # Then leave
    success = await coordinator.leave_cluster()
    
    assert success
    
    # Check node status
    node = coordinator.nodes[coordinator.node_id]
    assert node.status == NodeStatus.INACTIVE


@pytest.mark.asyncio
async def test_sync_data_creation(coordinator):
    """Test data synchronization creation."""
    operation_id = await coordinator.sync_data(
        operation_type="create",
        table_name="test_table",
        data={"key": "value", "number": 42},
        conditions={"id": "test_id"}
    )
    
    assert operation_id
    assert operation_id in coordinator.sync_operations
    
    sync_op = coordinator.sync_operations[operation_id]
    assert sync_op.operation_type == "create"
    assert sync_op.table_name == "test_table"
    assert sync_op.data["key"] == "value"
    assert sync_op.data["number"] == 42
    assert sync_op.conditions["id"] == "test_id"
    assert sync_op.source_node == coordinator.node_id
    assert sync_op.status == SyncStatus.PENDING
    
    # Check statistics
    assert coordinator.stats["total_sync_operations"] == 1


@pytest.mark.asyncio
async def test_sync_operation_completion():
    """Test sync operation completion tracking."""
    sync_op = SyncOperation(
        operation_id="test_op",
        operation_type="update",
        table_name="test_table",
        target_nodes=["node1", "node2", "node3"]
    )
    
    assert not sync_op.is_complete()
    
    # Add completed nodes
    sync_op.completed_nodes.add("node1")
    sync_op.completed_nodes.add("node2")
    assert not sync_op.is_complete()
    
    # Complete all nodes
    sync_op.completed_nodes.add("node3")
    assert sync_op.is_complete()


@pytest.mark.asyncio
async def test_resource_allocation(coordinator):
    """Test resource allocation."""
    # Add another node to allocate to
    other_node = DistributedNode(
        node_id="other_node",
        host="other.example.com",
        port=8082,
        status=NodeStatus.ACTIVE,
        max_agents=20
    )
    coordinator.nodes["other_node"] = other_node
    
    allocation_id = await coordinator.allocate_resource(
        resource_type=ResourceType.AGENT_SLOTS,
        amount=5.0,
        allocated_to="test_agent",
        priority=8,
        duration_seconds=3600
    )
    
    assert allocation_id
    assert allocation_id in coordinator.resource_allocations
    
    allocation = coordinator.resource_allocations[allocation_id]
    assert allocation.resource_type == ResourceType.AGENT_SLOTS
    assert allocation.amount == 5.0
    assert allocation.allocated_to == "test_agent"
    assert allocation.priority == 8
    assert allocation.active
    assert allocation.expires_at is not None
    
    # Check statistics
    assert coordinator.stats["resource_allocations"] == 1


@pytest.mark.asyncio
async def test_resource_deallocation(coordinator):
    """Test resource deallocation."""
    # Create allocation first
    allocation = ResourceAllocation(
        allocation_id="test_alloc",
        resource_type=ResourceType.MEMORY,
        amount=512.0,
        allocated_to="test_agent",
        allocated_by=coordinator.node_id
    )
    coordinator.resource_allocations["test_alloc"] = allocation
    
    # Deallocate
    success = await coordinator.deallocate_resource("test_alloc")
    
    assert success
    assert not allocation.active


@pytest.mark.asyncio
async def test_resource_allocation_expiration():
    """Test resource allocation expiration."""
    allocation = ResourceAllocation(
        allocation_id="test_alloc",
        resource_type=ResourceType.CPU,
        amount=25.0,
        allocated_to="test_agent",
        allocated_by="test_node"
    )
    
    # Not expired initially
    assert not allocation.is_expired()
    
    # Set expiration in the past
    allocation.expires_at = datetime.now() - timedelta(seconds=10)
    assert allocation.is_expired()


@pytest.mark.asyncio
async def test_resource_utilization():
    """Test resource utilization calculation."""
    allocation = ResourceAllocation(
        allocation_id="test_alloc",
        resource_type=ResourceType.MEMORY,
        amount=1000.0,
        allocated_to="test_agent",
        allocated_by="test_node"
    )
    
    # No usage initially
    assert allocation.get_utilization() == 0.0
    
    # Set actual usage
    allocation.actual_usage = 750.0
    assert allocation.get_utilization() == 0.75
    
    # Zero amount edge case
    allocation.amount = 0.0
    assert allocation.get_utilization() == 0.0


@pytest.mark.asyncio
async def test_coordinator_election(coordinator):
    """Test coordinator election process."""
    # Add multiple nodes
    node2 = DistributedNode(
        node_id="node_2",
        host="node2.example.com",
        port=8082,
        status=NodeStatus.ACTIVE
    )
    node3 = DistributedNode(
        node_id="node_3",
        host="node3.example.com",
        port=8083,
        status=NodeStatus.ACTIVE
    )
    
    coordinator.nodes["node_2"] = node2
    coordinator.nodes["node_3"] = node3
    
    # Trigger election
    await coordinator._trigger_coordinator_election()
    
    # Should elect node with lowest ID (lexicographically)
    # Between "test_node_1", "node_2", "node_3" -> "node_2" should win
    assert coordinator.coordinator_node_id == "node_2"
    assert not coordinator.is_coordinator
    assert coordinator.stats["coordinator_elections"] == 1


@pytest.mark.asyncio
async def test_cluster_status(coordinator):
    """Test cluster status retrieval."""
    # Add some nodes and allocations
    node2 = DistributedNode(
        node_id="node_2",
        host="node2.example.com",
        port=8082,
        status=NodeStatus.ACTIVE,
        current_agents=3,
        max_agents=10,
        current_cpu_percent=45.0,
        current_memory_mb=512.0
    )
    coordinator.nodes["node_2"] = node2
    
    allocation = ResourceAllocation(
        allocation_id="test_alloc",
        resource_type=ResourceType.MEMORY,
        amount=256.0,
        allocated_to="test_agent",
        allocated_by="node_2"
    )
    coordinator.resource_allocations["test_alloc"] = allocation
    
    status = await coordinator.get_cluster_status()
    
    assert "cluster_id" in status
    assert status["total_nodes"] == 2
    assert status["active_nodes"] == 2
    assert status["total_agents"] == 3  # Only node2 has agents
    assert status["total_capacity"] == 20  # 10 + 10
    assert status["resource_allocations"] == 1
    assert "nodes" in status
    assert len(status["nodes"]) == 2


@pytest.mark.asyncio
async def test_load_balancing_trigger(coordinator):
    """Test manual load balancing trigger."""
    # Add nodes with different loads
    high_load_node = DistributedNode(
        node_id="high_load",
        host="high.example.com",
        port=8082,
        status=NodeStatus.ACTIVE,
        current_agents=8,
        max_agents=10,
        current_cpu_percent=80.0,
        current_memory_mb=800.0,
        max_memory_mb=1000.0
    )
    
    low_load_node = DistributedNode(
        node_id="low_load",
        host="low.example.com",
        port=8083,
        status=NodeStatus.ACTIVE,
        current_agents=2,
        max_agents=10,
        current_cpu_percent=20.0,
        current_memory_mb=200.0,
        max_memory_mb=1000.0
    )
    
    coordinator.nodes["high_load"] = high_load_node
    coordinator.nodes["low_load"] = low_load_node
    coordinator.is_coordinator = True  # Make this node coordinator
    
    success = await coordinator.trigger_load_balancing()
    
    assert success
    assert coordinator.stats["load_balance_operations"] >= 1


@pytest.mark.asyncio
async def test_node_health_monitoring(coordinator):
    """Test node health monitoring."""
    # Add a node with old heartbeat
    unhealthy_node = DistributedNode(
        node_id="unhealthy_node",
        host="unhealthy.example.com",
        port=8082,
        status=NodeStatus.ACTIVE,
        heartbeat_interval=30
    )
    unhealthy_node.last_heartbeat = datetime.now() - timedelta(seconds=100)
    
    coordinator.nodes["unhealthy_node"] = unhealthy_node
    coordinator.stats["active_nodes"] = 2  # Self + unhealthy node
    
    # Check node health
    await coordinator._check_node_health()
    
    # Unhealthy node should be marked as failed
    assert unhealthy_node.status == NodeStatus.FAILED
    assert coordinator.stats["active_nodes"] == 1


@pytest.mark.asyncio
async def test_database_operations(coordinator):
    """Test database operations."""
    # Test that database was created and tables exist
    assert coordinator.local_db is not None
    
    cursor = coordinator.local_db.cursor()
    
    # Check that tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "nodes" in tables
    assert "resource_allocations" in tables
    assert "sync_operations" in tables
    
    # Check that self-registration worked
    cursor.execute("SELECT * FROM nodes WHERE node_id = ?", (coordinator.node_id,))
    node_row = cursor.fetchone()
    
    assert node_row is not None
    assert node_row[0] == coordinator.node_id  # node_id is first column


@pytest.mark.asyncio
async def test_sync_operation_local_application(coordinator):
    """Test local application of sync operations."""
    # Create a sync operation
    sync_op = SyncOperation(
        operation_id="test_sync",
        operation_type="create",
        table_name="nodes",
        data={
            "node_id": "new_node",
            "host": "new.example.com",
            "port": 8084,
            "role": "worker",
            "status": "active",
            "max_agents": 15,
            "max_cpu_percent": 75.0,
            "max_memory_mb": 1500.0,
            "current_agents": 0,
            "current_cpu_percent": 0.0,
            "current_memory_mb": 0.0,
            "sync_version": 1
        }
    )
    
    # Apply locally
    await coordinator._apply_sync_operation_locally(sync_op)
    
    # Verify data was inserted
    cursor = coordinator.local_db.cursor()
    cursor.execute("SELECT * FROM nodes WHERE node_id = ?", ("new_node",))
    row = cursor.fetchone()
    
    assert row is not None
    assert row[0] == "new_node"
    assert row[1] == "new.example.com"
    assert row[2] == 8084


@pytest.mark.asyncio
async def test_resource_migration(coordinator):
    """Test resource migration during node departure."""
    # Add target node for migration
    target_node = DistributedNode(
        node_id="target_node",
        host="target.example.com",
        port=8082,
        status=NodeStatus.ACTIVE,
        max_agents=20
    )
    coordinator.nodes["target_node"] = target_node
    
    # Create allocation on current node
    allocation = ResourceAllocation(
        allocation_id="migrate_alloc",
        resource_type=ResourceType.AGENT_SLOTS,
        amount=3.0,
        allocated_to="test_agent",
        allocated_by=coordinator.node_id
    )
    coordinator.resource_allocations["migrate_alloc"] = allocation
    
    # Migrate resources
    await coordinator._migrate_resources()
    
    # Allocation should be moved to target node
    assert allocation.allocated_by == "target_node"


@pytest.mark.asyncio
async def test_best_node_selection(coordinator):
    """Test best node selection for resource allocation."""
    # Add nodes with different loads
    node1 = DistributedNode(
        node_id="node1",
        host="node1.example.com",
        port=8081,
        status=NodeStatus.ACTIVE,
        current_agents=8,
        max_agents=10
    )
    
    node2 = DistributedNode(
        node_id="node2",
        host="node2.example.com",
        port=8082,
        status=NodeStatus.ACTIVE,
        current_agents=3,
        max_agents=10
    )
    
    coordinator.nodes["node1"] = node1
    coordinator.nodes["node2"] = node2
    
    # Find best node
    best_node = await coordinator._find_best_node_for_resource(
        ResourceType.AGENT_SLOTS, 1.0
    )
    
    # Should select node2 (lower load)
    assert best_node is not None
    assert best_node.node_id == "node2"


if __name__ == "__main__":
    pytest.main([__file__])