"""
Integration tests for the ecosystem orchestrator.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.ecosystem_orchestrator import (
    EcosystemOrchestrator,
    EcosystemConfig,
    SystemStatus
)


@pytest_asyncio.fixture
async def test_config():
    """Create test configuration."""
    config = EcosystemConfig(
        ecosystem_id="test_ecosystem",
        log_level="DEBUG",
        max_agents=5,
        enable_web_browsing=False,  # Disable to speed up tests
        enable_virtual_world=False,
        enable_economy=False,
        enable_reproduction=False,
        enable_distributed_mode=False,
        enable_human_oversight=True,
        enable_safety_systems=True,
        health_check_interval=1,  # Fast for testing
        cleanup_interval=2
    )
    return config


@pytest_asyncio.fixture
async def orchestrator(test_config):
    """Create ecosystem orchestrator for testing."""
    temp_dir = tempfile.mkdtemp()
    test_config.data_directory = temp_dir
    
    orch = EcosystemOrchestrator(test_config)
    
    yield orch
    
    # Cleanup
    if orch.is_running:
        await orch.shutdown()
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_orchestrator_creation(test_config):
    """Test orchestrator creation."""
    orchestrator = EcosystemOrchestrator(test_config)
    
    assert orchestrator.config.ecosystem_id == "test_ecosystem"
    assert orchestrator.config.max_agents == 5
    assert not orchestrator.is_running
    assert orchestrator.startup_time is None
    assert len(orchestrator.systems) == 0


@pytest.mark.asyncio
async def test_ecosystem_initialization(orchestrator):
    """Test full ecosystem initialization."""
    success = await orchestrator.initialize()
    
    assert success
    assert orchestrator.is_running
    assert orchestrator.startup_time is not None
    assert len(orchestrator.systems) > 0
    
    # Check that core systems are initialized
    assert "identity_manager" in orchestrator.systems
    assert "state_manager" in orchestrator.systems
    assert "message_router" in orchestrator.systems
    
    # Check that safety systems are initialized
    assert "safety_validator" in orchestrator.systems
    assert "emergency_response" in orchestrator.systems
    
    # Check that orchestration systems are initialized
    assert "agent_manager" in orchestrator.systems
    
    # Check that service systems are initialized
    assert "capability_registry" in orchestrator.systems
    assert "quality_feedback" in orchestrator.systems
    
    # Check system statuses
    for name, status in orchestrator.system_status.items():
        assert status.status in ["running", "initializing"]
        if status.status == "running":
            assert status.initialized_at is not None


@pytest.mark.asyncio
async def test_ecosystem_shutdown(orchestrator):
    """Test ecosystem shutdown."""
    # Initialize first
    await orchestrator.initialize()
    assert orchestrator.is_running
    
    # Shutdown
    await orchestrator.shutdown()
    
    assert not orchestrator.is_running
    assert orchestrator.shutdown_requested
    
    # Check that systems are stopped
    for status in orchestrator.system_status.values():
        assert status.status in ["stopped", "failed"]


@pytest.mark.asyncio
async def test_system_status_retrieval(orchestrator):
    """Test system status retrieval."""
    await orchestrator.initialize()
    
    status = await orchestrator.get_system_status()
    
    assert "ecosystem_id" in status
    assert status["ecosystem_id"] == "test_ecosystem"
    assert status["is_running"]
    assert "startup_time" in status
    assert "uptime_seconds" in status
    assert "statistics" in status
    assert "configuration" in status
    assert "systems" in status
    
    # Check statistics
    stats = status["statistics"]
    assert "total_systems" in stats
    assert "running_systems" in stats
    assert "failed_systems" in stats
    assert stats["total_systems"] > 0
    
    # Check configuration
    config = status["configuration"]
    assert config["max_agents"] == 5
    assert not config["enable_web_browsing"]
    assert config["enable_safety_systems"]
    
    # Check systems
    systems = status["systems"]
    assert len(systems) > 0
    for system_name, system_status in systems.items():
        assert "status" in system_status
        assert system_status["status"] in ["running", "initializing", "failed", "stopped"]


@pytest.mark.asyncio
async def test_system_restart(orchestrator):
    """Test system restart functionality."""
    await orchestrator.initialize()
    
    # Get a system to restart
    system_name = "identity_manager"
    assert system_name in orchestrator.systems
    
    # Restart the system
    success = await orchestrator.restart_system(system_name)
    
    assert success
    assert orchestrator.stats["system_restarts"] == 1
    
    # System should still be running
    assert system_name in orchestrator.systems
    assert orchestrator.system_status[system_name].status == "running"


@pytest.mark.asyncio
async def test_restart_nonexistent_system(orchestrator):
    """Test restarting non-existent system."""
    await orchestrator.initialize()
    
    success = await orchestrator.restart_system("nonexistent_system")
    
    assert not success
    assert orchestrator.stats["system_restarts"] == 0


@pytest.mark.asyncio
async def test_agent_spawning(orchestrator):
    """Test agent spawning through orchestrator."""
    await orchestrator.initialize()
    
    agent_config = {
        "agent_id": "test_agent_1",
        "config": {"test": "value"},
        "environment": {"TEST_VAR": "test"},
        "resource_limits": {"max_memory_mb": 256}
    }
    
    # Mock the agent manager spawn method
    with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value="process_123"):
        agent_id = await orchestrator.spawn_agent(agent_config)
    
    assert agent_id == "test_agent_1"


@pytest.mark.asyncio
async def test_agent_spawning_failure(orchestrator):
    """Test agent spawning failure."""
    await orchestrator.initialize()
    
    agent_config = {"agent_id": "test_agent_fail"}
    
    # Mock the agent manager to return empty string (failure)
    with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value=""):
        agent_id = await orchestrator.spawn_agent(agent_config)
    
    assert agent_id == ""


@pytest.mark.asyncio
async def test_agent_stopping(orchestrator):
    """Test agent stopping through orchestrator."""
    await orchestrator.initialize()
    
    # Mock the agent manager stop method
    with patch.object(orchestrator.agent_manager, 'stop_agent', return_value=True):
        success = await orchestrator.stop_agent("test_agent")
    
    assert success


@pytest.mark.asyncio
async def test_agent_status_retrieval(orchestrator):
    """Test agent status retrieval through orchestrator."""
    await orchestrator.initialize()
    
    mock_status = {
        "agent_id": "test_agent",
        "status": "running",
        "uptime_seconds": 123.45
    }
    
    # Mock the agent manager get_agent_status method
    with patch.object(orchestrator.agent_manager, 'get_agent_status', return_value=mock_status):
        status = await orchestrator.get_agent_status("test_agent")
    
    assert status == mock_status


@pytest.mark.asyncio
async def test_health_check_loop(orchestrator):
    """Test health check loop functionality."""
    await orchestrator.initialize()
    
    # Let health check run a few times
    await asyncio.sleep(2.5)  # Should run at least 2 health checks
    
    assert orchestrator.stats["health_checks_performed"] >= 2
    
    # Check that health check times are updated
    for status in orchestrator.system_status.values():
        if status.status == "running":
            assert status.last_health_check is not None


@pytest.mark.asyncio
async def test_system_status_object():
    """Test SystemStatus data structure."""
    status = SystemStatus(
        name="test_system",
        status="running",
        initialized_at=datetime.now(),
        metadata={"key": "value"}
    )
    
    assert status.name == "test_system"
    assert status.status == "running"
    assert status.initialized_at is not None
    assert status.metadata["key"] == "value"
    assert status.error_message is None


@pytest.mark.asyncio
async def test_ecosystem_config_defaults():
    """Test ecosystem configuration defaults."""
    config = EcosystemConfig()
    
    assert config.log_level == "INFO"
    assert config.enable_web_browsing
    assert config.enable_virtual_world
    assert config.enable_economy
    assert config.enable_reproduction
    assert not config.enable_distributed_mode
    assert config.enable_human_oversight
    assert config.enable_safety_systems
    assert config.max_agents == 50
    assert config.safety_level == "high"
    assert config.emergency_shutdown_enabled


@pytest.mark.asyncio
async def test_ecosystem_config_customization():
    """Test ecosystem configuration customization."""
    config = EcosystemConfig(
        ecosystem_id="custom_ecosystem",
        max_agents=100,
        enable_web_browsing=False,
        safety_level="maximum"
    )
    
    assert config.ecosystem_id == "custom_ecosystem"
    assert config.max_agents == 100
    assert not config.enable_web_browsing
    assert config.safety_level == "maximum"


@pytest.mark.asyncio
async def test_enabled_features_detection(test_config):
    """Test enabled features detection."""
    orchestrator = EcosystemOrchestrator(test_config)
    
    features = orchestrator._get_enabled_features()
    
    assert "human_oversight" in features
    assert "safety_systems" in features
    assert "web_browsing" not in features  # Disabled in test config
    assert "virtual_world" not in features  # Disabled in test config


@pytest.mark.asyncio
async def test_uptime_calculation(orchestrator):
    """Test uptime calculation."""
    # No startup time initially
    assert orchestrator._get_uptime_seconds() == 0.0
    
    # Initialize and check uptime
    await orchestrator.initialize()
    
    # Wait a bit
    await asyncio.sleep(0.1)
    
    uptime = orchestrator._get_uptime_seconds()
    assert uptime > 0.0
    assert uptime < 1.0  # Should be less than 1 second


@pytest.mark.asyncio
async def test_emergency_shutdown(orchestrator):
    """Test emergency shutdown functionality."""
    await orchestrator.initialize()
    
    # Mock emergency response system
    with patch.object(orchestrator.emergency_response, 'trigger_emergency_shutdown') as mock_emergency:
        await orchestrator._emergency_shutdown()
        mock_emergency.assert_called_once()


@pytest.mark.asyncio
async def test_system_initialization_failure():
    """Test handling of system initialization failure."""
    config = EcosystemConfig(enable_safety_systems=True)
    orchestrator = EcosystemOrchestrator(config)
    
    # Mock a system initialization to fail
    with patch.object(orchestrator, '_initialize_core_systems', side_effect=Exception("Test failure")):
        success = await orchestrator.initialize()
    
    assert not success
    assert not orchestrator.is_running


@pytest.mark.asyncio
async def test_signal_handler_setup(test_config):
    """Test signal handler setup."""
    orchestrator = EcosystemOrchestrator(test_config)
    
    # This should not raise an exception
    orchestrator._setup_signal_handlers()


@pytest.mark.asyncio
async def test_background_task_cancellation(orchestrator):
    """Test that background tasks are properly cancelled on shutdown."""
    await orchestrator.initialize()
    
    # Check that background tasks are running
    assert orchestrator.health_check_task is not None
    assert orchestrator.cleanup_task is not None
    assert not orchestrator.health_check_task.done()
    assert not orchestrator.cleanup_task.done()
    
    # Shutdown
    await orchestrator.shutdown()
    
    # Tasks should be cancelled
    assert orchestrator.health_check_task.cancelled() or orchestrator.health_check_task.done()
    assert orchestrator.cleanup_task.cancelled() or orchestrator.cleanup_task.done()


@pytest.mark.asyncio
async def test_system_health_check_with_status_method(orchestrator):
    """Test system health check when system has get_status method."""
    await orchestrator.initialize()
    
    # Mock a system with get_status method
    mock_system = Mock()
    mock_system.get_status = AsyncMock(return_value={"health": "good", "load": 0.5})
    
    orchestrator.systems["mock_system"] = mock_system
    orchestrator.system_status["mock_system"] = SystemStatus("mock_system", "running")
    
    # Perform health check
    await orchestrator._check_system_health("mock_system", mock_system)
    
    # Check that status was called and metadata updated
    mock_system.get_status.assert_called_once()
    assert "health" in orchestrator.system_status["mock_system"].metadata
    assert orchestrator.system_status["mock_system"].metadata["health"] == "good"


@pytest.mark.asyncio
async def test_system_health_check_failure(orchestrator):
    """Test system health check failure handling."""
    await orchestrator.initialize()
    
    # Mock a system that raises an exception during health check
    mock_system = Mock()
    mock_system.get_status = AsyncMock(side_effect=Exception("Health check failed"))
    
    orchestrator.systems["failing_system"] = mock_system
    orchestrator.system_status["failing_system"] = SystemStatus("failing_system", "running")
    
    # Perform health check
    await orchestrator._check_system_health("failing_system", mock_system)
    
    # System should be marked as failed
    assert orchestrator.system_status["failing_system"].status == "failed"
    assert "Health check failed" in orchestrator.system_status["failing_system"].error_message


@pytest.mark.asyncio
async def test_configuration_file_loading():
    """Test configuration loading from file."""
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, "test_config.json")
    
    try:
        # Create test config file
        test_config_data = {
            "ecosystem_id": "file_loaded_ecosystem",
            "max_agents": 25,
            "enable_web_browsing": False,
            "safety_level": "maximum"
        }
        
        with open(config_file, 'w') as f:
            json.dump(test_config_data, f)
        
        # Test loading (this would be done in main function)
        config = EcosystemConfig()
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        assert config.ecosystem_id == "file_loaded_ecosystem"
        assert config.max_agents == 25
        assert not config.enable_web_browsing
        assert config.safety_level == "maximum"
        
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__])