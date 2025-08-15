"""
Unit tests for agent process management and lifecycle orchestration.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from autonomous_ai_ecosystem.orchestration.agent_manager import (
    AgentManager,
    AgentProcess,
    AgentStatus,
    ProcessState,
    LifecycleEvent,
    LifecycleEventRecord
)


@pytest_asyncio.fixture
async def agent_manager():
    """Create agent manager for testing."""
    manager = AgentManager("test_agent_manager")
    
    # Use temporary directory for agent instances
    temp_dir = tempfile.mkdtemp()
    manager.config["default_working_dir"] = temp_dir
    manager.config["max_agents"] = 5
    manager.config["health_check_interval"] = 1  # Fast for testing
    manager.config["lifecycle_check_interval"] = 1
    
    await manager.initialize()
    
    yield manager
    
    await manager.shutdown()
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_agent_manager_initialization(agent_manager):
    """Test agent manager initialization."""
    assert agent_manager.agent_id == "test_agent_manager"
    assert agent_manager.monitoring_task is not None
    assert agent_manager.lifecycle_task is not None
    assert os.path.exists(agent_manager.config["default_working_dir"])
    assert len(agent_manager.agents) == 0


@pytest.mark.asyncio
async def test_agent_process_creation():
    """Test agent process data structure."""
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process_1",
        executable_path="python",
        working_directory="/tmp/test",
        max_memory_mb=512,
        max_cpu_percent=25.0
    )
    
    assert agent_process.agent_id == "test_agent"
    assert agent_process.process_id == "test_process_1"
    assert agent_process.status == AgentStatus.INITIALIZING
    assert agent_process.process_state == ProcessState.STARTING
    assert agent_process.max_memory_mb == 512
    assert agent_process.max_cpu_percent == 25.0
    assert agent_process.restart_count == 0
    assert not agent_process.modification_in_progress


@pytest.mark.asyncio
async def test_agent_process_uptime():
    """Test agent process uptime calculation."""
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process_1"
    )
    
    # No spawn time set
    assert agent_process.get_uptime() == 0.0
    
    # Set spawn time
    agent_process.spawn_time = datetime.now() - timedelta(seconds=10)
    uptime = agent_process.get_uptime()
    assert uptime >= 10.0
    assert uptime < 11.0  # Should be close to 10 seconds


@pytest.mark.asyncio
async def test_agent_sleep_wake_logic():
    """Test agent sleep/wake logic."""
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process_1",
        status=AgentStatus.RUNNING
    )
    
    # No sleep schedule
    assert not agent_process.should_sleep()
    assert not agent_process.should_wake()
    
    # Set sleep schedule with idle timeout
    agent_process.sleep_schedule = {"idle_sleep_minutes": 5}
    agent_process.last_activity = datetime.now() - timedelta(minutes=6)
    
    assert agent_process.should_sleep()
    
    # Put to sleep
    agent_process.status = AgentStatus.SLEEPING
    agent_process.sleep_start_time = datetime.now() - timedelta(hours=9)
    agent_process.sleep_schedule["sleep_duration_hours"] = 8
    
    assert agent_process.should_wake()


@pytest.mark.asyncio
@patch('subprocess.Popen')
@patch('psutil.Process')
async def test_spawn_agent_success(mock_psutil_process, mock_popen, agent_manager):
    """Test successful agent spawning."""
    # Mock subprocess
    mock_process = Mock()
    mock_process.pid = 12345
    mock_popen.return_value = mock_process
    
    # Mock psutil process
    mock_psutil = Mock()
    mock_psutil.is_running.return_value = True
    mock_psutil_process.return_value = mock_psutil
    
    # Spawn agent
    process_id = await agent_manager.spawn_agent(
        agent_id="test_agent_1",
        config={"test": "config"},
        environment={"TEST_VAR": "test_value"},
        resource_limits={"max_memory_mb": 512}
    )
    
    assert process_id
    assert "test_agent_1" in agent_manager.agents
    
    agent_process = agent_manager.agents["test_agent_1"]
    assert agent_process.agent_id == "test_agent_1"
    assert agent_process.process_id == process_id
    assert agent_process.pid == 12345
    assert agent_process.status == AgentStatus.RUNNING
    assert agent_process.max_memory_mb == 512
    assert "TEST_VAR" in agent_process.environment_vars
    
    # Check statistics
    assert agent_manager.stats["total_agents_spawned"] == 1
    assert agent_manager.stats["active_agents"] == 1


@pytest.mark.asyncio
async def test_spawn_agent_duplicate(agent_manager):
    """Test spawning duplicate agent."""
    # Create mock agent
    agent_process = AgentProcess(
        agent_id="existing_agent",
        process_id="existing_process"
    )
    agent_manager.agents["existing_agent"] = agent_process
    
    # Try to spawn duplicate
    process_id = await agent_manager.spawn_agent("existing_agent")
    
    assert not process_id  # Should fail
    assert agent_manager.stats["total_agents_spawned"] == 0


@pytest.mark.asyncio
async def test_spawn_agent_max_limit(agent_manager):
    """Test agent spawning with max limit."""
    # Set low limit
    agent_manager.config["max_agents"] = 1
    
    # Add one agent
    agent_process = AgentProcess(
        agent_id="existing_agent",
        process_id="existing_process"
    )
    agent_manager.agents["existing_agent"] = agent_process
    
    # Try to spawn another
    process_id = await agent_manager.spawn_agent("new_agent")
    
    assert not process_id  # Should fail due to limit


@pytest.mark.asyncio
async def test_stop_agent(agent_manager):
    """Test agent stopping."""
    # Create mock agent with mock process
    mock_process = Mock()
    mock_process.terminate = Mock()
    mock_process.wait = Mock(return_value=0)
    
    mock_psutil = Mock()
    mock_psutil.terminate = Mock()
    mock_psutil.wait = Mock()
    
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.RUNNING
    )
    agent_process.process = mock_process
    agent_process.psutil_process = mock_psutil
    
    agent_manager.agents["test_agent"] = agent_process
    agent_manager.stats["active_agents"] = 1
    
    # Stop agent
    success = await agent_manager.stop_agent("test_agent", graceful=True)
    
    assert success
    assert agent_process.status == AgentStatus.STOPPED
    assert agent_manager.stats["active_agents"] == 0


@pytest.mark.asyncio
async def test_stop_nonexistent_agent(agent_manager):
    """Test stopping non-existent agent."""
    success = await agent_manager.stop_agent("nonexistent_agent")
    assert not success


@pytest.mark.asyncio
async def test_restart_agent(agent_manager):
    """Test agent restarting."""
    # Create mock agent
    mock_process = Mock()
    mock_psutil = Mock()
    mock_psutil.terminate = Mock()
    mock_psutil.wait = Mock()
    
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.RUNNING
    )
    agent_process.process = mock_process
    agent_process.psutil_process = mock_psutil
    
    agent_manager.agents["test_agent"] = agent_process
    
    # Mock the start process method
    with patch.object(agent_manager, '_start_agent_process', return_value=True):
        success = await agent_manager.restart_agent("test_agent")
    
    assert success
    assert agent_process.restart_count == 1
    assert agent_process.status == AgentStatus.RUNNING
    assert agent_manager.stats["total_restarts"] == 1


@pytest.mark.asyncio
async def test_sleep_agent(agent_manager):
    """Test putting agent to sleep."""
    # Create mock agent
    mock_psutil = Mock()
    mock_psutil.suspend = Mock()
    
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.RUNNING
    )
    agent_process.psutil_process = mock_psutil
    
    agent_manager.agents["test_agent"] = agent_process
    agent_manager.stats["active_agents"] = 1
    
    # Sleep agent
    success = await agent_manager.sleep_agent("test_agent", duration_hours=2.0)
    
    assert success
    assert agent_process.status == AgentStatus.SLEEPING
    assert agent_process.sleep_start_time is not None
    assert agent_process.wake_time is not None
    assert agent_process.process_state == ProcessState.SUSPENDED
    assert agent_manager.stats["active_agents"] == 0
    assert agent_manager.stats["sleeping_agents"] == 1
    
    mock_psutil.suspend.assert_called_once()


@pytest.mark.asyncio
async def test_wake_agent(agent_manager):
    """Test waking up agent."""
    # Create mock sleeping agent
    mock_psutil = Mock()
    mock_psutil.resume = Mock()
    
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.SLEEPING
    )
    agent_process.psutil_process = mock_psutil
    agent_process.sleep_start_time = datetime.now() - timedelta(hours=1)
    
    agent_manager.agents["test_agent"] = agent_process
    agent_manager.stats["sleeping_agents"] = 1
    
    # Wake agent
    success = await agent_manager.wake_agent("test_agent")
    
    assert success
    assert agent_process.status == AgentStatus.RUNNING
    assert agent_process.sleep_start_time is None
    assert agent_process.wake_time is None
    assert agent_process.process_state == ProcessState.ACTIVE
    assert agent_manager.stats["sleeping_agents"] == 0
    assert agent_manager.stats["active_agents"] == 1
    
    mock_psutil.resume.assert_called_once()


@pytest.mark.asyncio
async def test_prepare_for_modification(agent_manager):
    """Test preparing agent for modification."""
    # Create mock agent
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.RUNNING,
        working_directory=agent_manager.config["default_working_dir"]
    )
    
    mock_psutil = Mock()
    mock_psutil.is_running.return_value = True
    mock_psutil.suspend = Mock()
    agent_process.psutil_process = mock_psutil
    
    agent_manager.agents["test_agent"] = agent_process
    
    # Mock backup creation
    with patch.object(agent_manager, '_create_agent_backup', return_value="/tmp/backup"):
        success = await agent_manager.prepare_for_modification("test_agent")
    
    assert success
    assert agent_process.status == AgentStatus.MODIFYING
    assert agent_process.modification_in_progress
    assert agent_process.modification_backup_path == "/tmp/backup"
    assert agent_process.process_state == ProcessState.SUSPENDED
    assert agent_manager.stats["total_modifications"] == 1
    
    mock_psutil.suspend.assert_called_once()


@pytest.mark.asyncio
async def test_complete_modification_success(agent_manager):
    """Test completing successful modification."""
    # Create mock agent in modification state
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.MODIFYING
    )
    agent_process.modification_in_progress = True
    agent_process.modification_backup_path = "/tmp/backup"
    
    agent_manager.agents["test_agent"] = agent_process
    
    # Mock methods
    with patch.object(agent_manager, '_force_terminate', return_value=True), \
         patch.object(agent_manager, '_start_agent_process', return_value=True):
        
        success = await agent_manager.complete_modification("test_agent", success=True)
    
    assert success
    assert agent_process.status == AgentStatus.RUNNING
    assert not agent_process.modification_in_progress
    assert agent_process.modification_backup_path is None


@pytest.mark.asyncio
async def test_complete_modification_failure(agent_manager):
    """Test completing failed modification."""
    # Create mock agent in modification state
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.MODIFYING
    )
    agent_process.modification_in_progress = True
    agent_process.modification_backup_path = "/tmp/backup"
    
    agent_manager.agents["test_agent"] = agent_process
    
    # Mock rollback
    with patch.object(agent_manager, '_rollback_modification') as mock_rollback:
        success = await agent_manager.complete_modification("test_agent", success=False)
    
    assert success
    mock_rollback.assert_called_once_with(agent_process)


@pytest.mark.asyncio
async def test_get_agent_status(agent_manager):
    """Test getting agent status."""
    # Create mock agent
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.RUNNING
    )
    agent_process.spawn_time = datetime.now() - timedelta(minutes=5)
    agent_process.last_health_check = datetime.now() - timedelta(seconds=30)
    agent_process.cpu_usage = 25.5
    agent_process.memory_usage_mb = 128.0
    agent_process.restart_count = 2
    
    agent_manager.agents["test_agent"] = agent_process
    
    # Mock resource update
    with patch.object(agent_manager, '_update_resource_usage'):
        status = await agent_manager.get_agent_status("test_agent")
    
    assert status is not None
    assert status["agent_id"] == "test_agent"
    assert status["process_id"] == "test_process"
    assert status["status"] == AgentStatus.RUNNING.value
    assert status["restart_count"] == 2
    assert status["cpu_usage"] == 25.5
    assert status["memory_usage_mb"] == 128.0
    assert "uptime_seconds" in status
    assert "spawn_time" in status


@pytest.mark.asyncio
async def test_get_nonexistent_agent_status(agent_manager):
    """Test getting status of non-existent agent."""
    status = await agent_manager.get_agent_status("nonexistent_agent")
    assert status is None


@pytest.mark.asyncio
async def test_get_all_agents_status(agent_manager):
    """Test getting status of all agents."""
    # Create multiple mock agents
    for i in range(3):
        agent_process = AgentProcess(
            agent_id=f"test_agent_{i}",
            process_id=f"test_process_{i}",
            status=AgentStatus.RUNNING
        )
        agent_manager.agents[f"test_agent_{i}"] = agent_process
    
    # Mock resource update
    with patch.object(agent_manager, '_update_resource_usage'):
        statuses = await agent_manager.get_all_agents_status()
    
    assert len(statuses) == 3
    assert all("agent_id" in status for status in statuses)
    assert all("status" in status for status in statuses)


@pytest.mark.asyncio
async def test_stop_all_agents(agent_manager):
    """Test stopping all agents."""
    # Create multiple mock agents
    for i in range(3):
        agent_process = AgentProcess(
            agent_id=f"test_agent_{i}",
            process_id=f"test_process_{i}",
            status=AgentStatus.RUNNING
        )
        agent_manager.agents[f"test_agent_{i}"] = agent_process
    
    # Mock stop_agent method
    with patch.object(agent_manager, 'stop_agent', return_value=True) as mock_stop:
        await agent_manager.stop_all_agents()
    
    # Should have called stop_agent for each agent
    assert mock_stop.call_count == 3


@pytest.mark.asyncio
async def test_lifecycle_event_recording(agent_manager):
    """Test lifecycle event recording."""
    # Create mock agent
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process"
    )
    agent_process.cpu_usage = 15.0
    agent_process.memory_usage_mb = 64.0
    
    agent_manager.agents["test_agent"] = agent_process
    
    # Record event
    await agent_manager._record_lifecycle_event(
        agent_id="test_agent",
        event_type=LifecycleEvent.START,
        description="Agent started successfully",
        previous_status=AgentStatus.INITIALIZING,
        new_status=AgentStatus.RUNNING,
        metadata={"test": "data"}
    )
    
    # Check event was recorded
    assert len(agent_manager.lifecycle_events) == 1
    
    event = list(agent_manager.lifecycle_events.values())[0]
    assert event.agent_id == "test_agent"
    assert event.event_type == LifecycleEvent.START
    assert event.description == "Agent started successfully"
    assert event.previous_status == AgentStatus.INITIALIZING
    assert event.new_status == AgentStatus.RUNNING
    assert event.cpu_usage == 15.0
    assert event.memory_usage == 64.0
    assert event.metadata["test"] == "data"
    assert event.success
    
    # Check statistics
    assert agent_manager.stats["lifecycle_events"][LifecycleEvent.START.value] == 1


@pytest.mark.asyncio
async def test_health_check_success(agent_manager):
    """Test successful health check."""
    # Create mock agent
    mock_psutil = Mock()
    mock_psutil.is_running.return_value = True
    mock_psutil.cpu_percent.return_value = 20.0
    mock_psutil.memory_info.return_value = Mock(rss=128 * 1024 * 1024)  # 128MB
    
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.RUNNING
    )
    agent_process.psutil_process = mock_psutil
    agent_process.health_check_failures = 2  # Had previous failures
    
    # Perform health check
    await agent_manager._perform_health_check(agent_process)
    
    # Check results
    assert agent_process.last_health_check is not None
    assert agent_process.health_check_failures == 0  # Reset on success
    assert agent_process.cpu_usage == 20.0
    assert agent_process.memory_usage_mb == 128.0


@pytest.mark.asyncio
async def test_health_check_dead_process(agent_manager):
    """Test health check with dead process."""
    # Create mock agent with dead process
    mock_psutil = Mock()
    mock_psutil.is_running.return_value = False
    
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.RUNNING
    )
    agent_process.psutil_process = mock_psutil
    agent_process.max_health_failures = 2
    agent_process.health_check_failures = 1
    
    agent_manager.agents["test_agent"] = agent_process
    
    # Mock handle_dead_process
    with patch.object(agent_manager, '_handle_dead_process') as mock_handle:
        await agent_manager._perform_health_check(agent_process)
    
    # Should increment failure count
    assert agent_process.health_check_failures == 2
    
    # Should handle dead process when max failures reached
    mock_handle.assert_called_once_with(agent_process)


@pytest.mark.asyncio
async def test_handle_dead_process(agent_manager):
    """Test handling dead process."""
    # Create mock agent
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process",
        status=AgentStatus.RUNNING
    )
    
    agent_manager.agents["test_agent"] = agent_process
    agent_manager.stats["active_agents"] = 1
    agent_manager.config["auto_restart_failed"] = True
    
    # Mock restart_agent
    with patch.object(agent_manager, 'restart_agent', return_value=True) as mock_restart:
        await agent_manager._handle_dead_process(agent_process)
    
    # Check status changed
    assert agent_process.status == AgentStatus.FAILED
    
    # Check statistics updated
    assert agent_manager.stats["active_agents"] == 0
    assert agent_manager.stats["failed_agents"] == 1
    
    # Should attempt restart
    mock_restart.assert_called_once_with("test_agent")


@pytest.mark.asyncio
async def test_shutdown_handler_registration(agent_manager):
    """Test shutdown handler registration."""
    mock_handler = Mock()
    
    agent_manager.register_shutdown_handler(mock_handler)
    
    assert mock_handler in agent_manager.shutdown_handlers


@pytest.mark.asyncio
async def test_resource_usage_update(agent_manager):
    """Test resource usage update."""
    # Create mock agent with psutil process
    mock_memory_info = Mock()
    mock_memory_info.rss = 256 * 1024 * 1024  # 256MB
    
    mock_psutil = Mock()
    mock_psutil.is_running.return_value = True
    mock_psutil.cpu_percent.return_value = 35.5
    mock_psutil.memory_info.return_value = mock_memory_info
    
    agent_process = AgentProcess(
        agent_id="test_agent",
        process_id="test_process"
    )
    agent_process.psutil_process = mock_psutil
    agent_process.spawn_time = datetime.now() - timedelta(minutes=10)
    
    # Update resource usage
    await agent_manager._update_resource_usage(agent_process)
    
    # Check updated values
    assert agent_process.cpu_usage == 35.5
    assert agent_process.memory_usage_mb == 256.0
    assert agent_process.uptime_seconds > 0


if __name__ == "__main__":
    pytest.main([__file__])