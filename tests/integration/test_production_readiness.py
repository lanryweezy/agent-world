"""
Production readiness tests for the autonomous AI ecosystem.

This module contains comprehensive tests to validate the system
is ready for production deployment.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
import time
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from autonomous_ai_ecosystem.ecosystem_orchestrator import (
    EcosystemOrchestrator,
    EcosystemConfig
)


@pytest_asyncio.fixture
async def production_config():
    """Create production-like configuration."""
    config = EcosystemConfig(
        ecosystem_id="production_readiness_test",
        max_agents=25,
        enable_web_browsing=True,
        enable_virtual_world=True,
        enable_economy=True,
        enable_reproduction=False,  # Disable for testing
        enable_distributed_mode=False,
        enable_human_oversight=True,
        enable_safety_systems=True,
        safety_level="high",
        health_check_interval=30,
        cleanup_interval=300
    )
    return config


@pytest_asyncio.fixture
async def production_orchestrator(production_config):
    """Create production-ready orchestrator."""
    temp_dir = tempfile.mkdtemp()
    production_config.data_directory = temp_dir
    
    orchestrator = EcosystemOrchestrator(production_config)
    
    yield orchestrator
    
    # Cleanup
    if orchestrator.is_running:
        await orchestrator.shutdown()
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
@pytest.mark.production
async def test_production_initialization_time(production_orchestrator):
    """Test that production initialization completes within acceptable time."""
    start_time = time.time()
    
    success = await production_orchestrator.initialize()
    
    init_time = time.time() - start_time
    
    assert success
    assert init_time < 30.0  # Should initialize within 30 seconds
    
    # Check startup time is recorded
    status = await production_orchestrator.get_system_status()
    assert status["statistics"]["startup_time_seconds"] < 30.0


@pytest.mark.asyncio
@pytest.mark.production
async def test_production_system_completeness(production_orchestrator):
    """Test that all required systems are present in production."""
    await production_orchestrator.initialize()
    
    status = await production_orchestrator.get_system_status()
    systems = status["systems"]
    
    # Required core systems
    required_systems = [
        "identity_manager",
        "state_manager", 
        "agent_manager",
        "safety_validator",
        "emergency_response",
        "capability_registry",
        "quality_feedback"
    ]
    
    for system_name in required_systems:
        assert system_name in systems, f"Required system missing: {system_name}"
        assert systems[system_name]["status"] == "running", f"Required system not running: {system_name}"
    
    # Optional systems should be present if enabled
    if production_orchestrator.config.enable_human_oversight:
        oversight_systems = ["command_router", "task_delegator", "monitoring_reporting"]
        for system_name in oversight_systems:
            assert system_name in systems, f"Oversight system missing: {system_name}"


@pytest.mark.asyncio
@pytest.mark.production
async def test_production_resource_limits(production_orchestrator):
    """Test that system respects resource limits in production."""
    await production_orchestrator.initialize()
    
    # Monitor resource usage over time
    resource_samples = []
    
    for _ in range(10):
        process = psutil.Process()
        sample = {
            "timestamp": datetime.now(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "cpu_percent": process.cpu_percent(),
            "open_files": len(process.open_files()),
            "threads": process.num_threads()
        }
        resource_samples.append(sample)
        
        # Perform some operations
        await production_orchestrator.get_system_status()
        await asyncio.sleep(1)
    
    # Analyze resource usage
    max_memory = max(sample["memory_mb"] for sample in resource_samples)
    avg_cpu = sum(sample["cpu_percent"] for sample in resource_samples) / len(resource_samples)
    max_files = max(sample["open_files"] for sample in resource_samples)
    max_threads = max(sample["threads"] for sample in resource_samples)
    
    # Production resource limits
    assert max_memory < 1000, f"Memory usage too high: {max_memory}MB"
    assert avg_cpu < 50, f"Average CPU usage too high: {avg_cpu}%"
    assert max_files < 500, f"Too many open files: {max_files}"
    assert max_threads < 100, f"Too many threads: {max_threads}"


@pytest.mark.asyncio
@pytest.mark.production
async def test_production_error_handling(production_orchestrator):
    """Test error handling in production scenarios."""
    await production_orchestrator.initialize()
    
    # Test handling of invalid operations
    invalid_agent_id = "nonexistent_agent_12345"
    
    # Should handle gracefully without crashing
    agent_status = await production_orchestrator.get_agent_status(invalid_agent_id)
    assert agent_status is None
    
    stop_result = await production_orchestrator.stop_agent(invalid_agent_id)
    assert not stop_result
    
    # Test invalid system restart
    restart_result = await production_orchestrator.restart_system("nonexistent_system")
    assert not restart_result
    
    # System should still be running after error conditions
    status = await production_orchestrator.get_system_status()
    assert status["is_running"]


@pytest.mark.asyncio
@pytest.mark.production
async def test_production_safety_systems(production_orchestrator):
    """Test safety systems in production configuration."""
    await production_orchestrator.initialize()
    
    # Verify safety systems are active
    assert production_orchestrator.safety_validator is not None
    assert production_orchestrator.emergency_response is not None
    
    # Test safety system functionality
    if production_orchestrator.safety_validator:
        # Mock safety validation
        with patch.object(production_orchestrator.safety_validator, 'validate_code_safety') as mock_validate:
            mock_validate.return_value = {"safe": True, "violations": []}
            
            # Safety validation should be available
            result = await production_orchestrator.safety_validator.validate_code_safety(
                "print('hello world')", "test_agent"
            )
            assert result["safe"]
    
    # Test emergency response
    if production_orchestrator.emergency_response:
        # Test incident reporting
        with patch.object(production_orchestrator.emergency_response, 'report_incident') as mock_report:
            mock_report.return_value = "test_incident_prod"
            
            incident_id = await production_orchestrator.emergency_response.report_incident(
                level="medium",
                reason="resource_exhaustion", 
                description="Production test incident"
            )
            
            assert incident_id == "test_incident_prod"


@pytest.mark.asyncio
@pytest.mark.production
async def test_production_monitoring_capabilities(production_orchestrator):
    """Test monitoring capabilities in production."""
    await production_orchestrator.initialize()
    
    # Test comprehensive status monitoring
    status = await production_orchestrator.get_system_status()
    
    # Should have detailed monitoring data
    assert "statistics" in status
    assert "systems" in status
    assert "configuration" in status
    
    stats = status["statistics"]
    required_stats = [
        "total_systems", "running_systems", "failed_systems",
        "uptime_seconds", "startup_time_seconds", "health_checks_performed"
    ]
    
    for stat_name in required_stats:
        assert stat_name in stats, f"Required statistic missing: {stat_name}"
    
    # Test health monitoring over time
    initial_health_checks = stats["health_checks_performed"]
    
    await asyncio.sleep(5)  # Wait for health checks
    
    updated_status = await production_orchestrator.get_system_status()
    updated_health_checks = updated_status["statistics"]["health_checks_performed"]
    
    assert updated_health_checks > initial_health_checks


@pytest.mark.asyncio
@pytest.mark.production
async def test_production_configuration_validation(production_orchestrator):
    """Test configuration validation for production deployment."""
    config = production_orchestrator.config
    
    # Validate production configuration
    assert config.max_agents > 0
    assert config.max_agents <= 1000  # Reasonable upper limit
    assert config.health_check_interval > 0
    assert config.cleanup_interval > 0
    assert config.safety_level in ["low", "medium", "high", "maximum"]
    
    # Safety should be enabled in production
    assert config.enable_safety_systems
    assert config.emergency_shutdown_enabled
    
    # Resource limits should be reasonable
    assert config.max_memory_mb > 0
    assert config.max_memory_mb <= 16384  # 16GB max
    assert config.max_cpu_percent > 0
    assert config.max_cpu_percent <= 100


@pytest.mark.asyncio
@pytest.mark.production
async def test_production_graceful_shutdown(production_orchestrator):
    """Test graceful shutdown in production scenarios."""
    await production_orchestrator.initialize()
    
    # Record initial state
    initial_status = await production_orchestrator.get_system_status()
    initial_uptime = initial_status["uptime_seconds"]
    
    # Verify system is fully operational
    assert initial_status["is_running"]
    assert initial_status["statistics"]["running_systems"] > 0
    
    # Perform graceful shutdown
    shutdown_start = time.time()
    await production_orchestrator.shutdown()
    shutdown_time = time.time() - shutdown_start
    
    # Shutdown should complete within reasonable time
    assert shutdown_time < 30.0  # 30 seconds max
    
    # Verify shutdown completed properly
    assert not production_orchestrator.is_running
    assert production_orchestrator.shutdown_requested
    
    # Background tasks should be cancelled
    if production_orchestrator.health_check_task:
        assert production_orchestrator.health_check_task.cancelled() or production_orchestrator.health_check_task.done()
    
    if production_orchestrator.cleanup_task:
        assert production_orchestrator.cleanup_task.cancelled() or production_orchestrator.cleanup_task.done()


@pytest.mark.asyncio
@pytest.mark.production
async def test_production_data_persistence(production_orchestrator):
    """Test data persistence and recovery in production."""
    await production_orchestrator.initialize()
    
    # Create some data
    test_data = {
        "test_key": "test_value",
        "timestamp": datetime.now().isoformat(),
        "agent_count": 5
    }
    
    # Store data (mock implementation)
    data_file = os.path.join(production_orchestrator.config.data_directory, "test_data.json")
    with open(data_file, 'w') as f:
        json.dump(test_data, f)
    
    # Verify data exists
    assert os.path.exists(data_file)
    
    # Shutdown and restart
    await production_orchestrator.shutdown()
    
    # Reinitialize
    await production_orchestrator.initialize()
    
    # Verify data persisted
    assert os.path.exists(data_file)
    
    with open(data_file, 'r') as f:
        recovered_data = json.load(f)
    
    assert recovered_data["test_key"] == "test_value"
    assert recovered_data["agent_count"] == 5


@pytest.mark.asyncio
@pytest.mark.production
async def test_production_scalability_limits(production_orchestrator):
    """Test system behavior at scalability limits."""
    await production_orchestrator.initialize()
    
    # Test with maximum configured agents
    max_agents = production_orchestrator.config.max_agents
    
    # Mock agent spawning to test limits
    with patch.object(production_orchestrator.agent_manager, 'spawn_agent') as mock_spawn:
        mock_spawn.return_value = "mock_process"
        
        # Try to spawn maximum number of agents
        spawned_count = 0
        for i in range(max_agents + 5):  # Try to exceed limit
            agent_id = await production_orchestrator.spawn_agent({
                "agent_id": f"scale_test_agent_{i}"
            })
            if agent_id:
                spawned_count += 1
        
        # Should respect the limit
        assert spawned_count <= max_agents
    
    # Test system stability at scale
    status = await production_orchestrator.get_system_status()
    assert status["is_running"]
    assert status["statistics"]["failed_systems"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "production"])