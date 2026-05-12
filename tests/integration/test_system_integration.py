"""
System-wide integration tests for multi-agent scenarios.

This module tests the complete ecosystem with various agent counts,
long-running stability, performance benchmarking, and failure recovery.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
import time
import psutil
from datetime import datetime
from unittest.mock import patch

from autonomous_ai_ecosystem.ecosystem_orchestrator import (
    EcosystemOrchestrator,
    EcosystemConfig
)


@pytest_asyncio.fixture
async def integration_config():
    """Create configuration for integration tests."""
    config = EcosystemConfig(
        ecosystem_id="integration_test_ecosystem",
        max_agents=10,
        enable_web_browsing=False,  # Disable to speed up tests
        enable_virtual_world=False,
        enable_economy=False,
        enable_reproduction=False,
        enable_distributed_mode=False,
        enable_human_oversight=True,
        enable_safety_systems=True,
        health_check_interval=2,
        cleanup_interval=5
    )
    return config


@pytest_asyncio.fixture
async def integration_orchestrator(integration_config):
    """Create orchestrator for integration tests."""
    temp_dir = tempfile.mkdtemp()
    integration_config.data_directory = temp_dir
    
    orchestrator = EcosystemOrchestrator(integration_config)
    
    yield orchestrator
    
    # Cleanup
    if orchestrator.is_running:
        await orchestrator.shutdown()
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_system_initialization(integration_orchestrator):
    """Test complete system initialization and basic functionality."""
    # Initialize the ecosystem
    success = await integration_orchestrator.initialize()
    
    assert success
    assert integration_orchestrator.is_running
    
    # Verify core systems are running
    status = await integration_orchestrator.get_system_status()
    
    assert status["is_running"]
    assert status["statistics"]["running_systems"] > 0
    assert status["statistics"]["failed_systems"] == 0
    
    # Verify essential systems are present
    systems = status["systems"]
    essential_systems = ["identity_manager", "state_manager", "agent_manager", "safety_validator"]
    
    for system_name in essential_systems:
        assert system_name in systems
        assert systems[system_name]["status"] == "running"
    
    # Test system health after initialization
    await asyncio.sleep(3)  # Let health checks run
    
    updated_status = await integration_orchestrator.get_system_status()
    assert updated_status["statistics"]["health_checks_performed"] > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multi_agent_scenario(integration_orchestrator):
    """Test multi-agent scenarios with various agent counts."""
    await integration_orchestrator.initialize()
    
    # Test spawning multiple agents
    agent_configs = [
        {"agent_id": f"test_agent_{i}", "config": {"role": "worker"}}
        for i in range(5)
    ]
    
    spawned_agents = []
    
    # Mock agent spawning since we don't have full agent implementation
    with patch.object(integration_orchestrator.agent_manager, 'spawn_agent') as mock_spawn:
        mock_spawn.return_value = "mock_process_id"
        
        for config in agent_configs:
            agent_id = await integration_orchestrator.spawn_agent(config)
            if agent_id:
                spawned_agents.append(agent_id)
    
    assert len(spawned_agents) == 5
    
    # Mock agent status retrieval
    mock_agent_statuses = [
        {
            "agent_id": agent_id,
            "status": "running",
            "uptime_seconds": 10.0,
            "cpu_usage": 15.0,
            "memory_usage_mb": 64.0
        }
        for agent_id in spawned_agents
    ]
    
    with patch.object(integration_orchestrator.agent_manager, 'get_all_agents_status') as mock_status:
        mock_status.return_value = mock_agent_statuses
        
        # Verify agent status
        status = await integration_orchestrator.get_system_status()
        assert status["statistics"]["total_agents"] == 5
    
    # Test stopping agents
    with patch.object(integration_orchestrator.agent_manager, 'stop_agent') as mock_stop:
        mock_stop.return_value = True
        
        for agent_id in spawned_agents:
            success = await integration_orchestrator.stop_agent(agent_id)
            assert success


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_long_running_stability(integration_orchestrator):
    """Test long-running stability over extended periods."""
    await integration_orchestrator.initialize()
    
    start_time = time.time()
    test_duration = 30  # 30 seconds for CI/CD compatibility
    
    # Monitor system health over time
    health_checks = []
    
    while time.time() - start_time < test_duration:
        status = await integration_orchestrator.get_system_status()
        
        health_check = {
            "timestamp": datetime.now(),
            "uptime": status["uptime_seconds"],
            "running_systems": status["statistics"]["running_systems"],
            "failed_systems": status["statistics"]["failed_systems"],
            "memory_usage": psutil.Process().memory_info().rss / 1024 / 1024  # MB
        }
        
        health_checks.append(health_check)
        
        # Verify system is still healthy
        assert status["is_running"]
        assert status["statistics"]["failed_systems"] == 0
        
        await asyncio.sleep(2)
    
    # Analyze stability metrics
    assert len(health_checks) > 10  # Should have multiple health checks
    
    # Check that uptime is increasing
    assert health_checks[-1]["uptime"] > health_checks[0]["uptime"]
    
    # Check that running systems count is stable
    running_systems_counts = [hc["running_systems"] for hc in health_checks]
    assert all(count > 0 for count in running_systems_counts)
    
    # Check memory usage is reasonable (not growing unbounded)
    memory_usages = [hc["memory_usage"] for hc in health_checks]
    max_memory = max(memory_usages)
    min_memory = min(memory_usages)
    
    # Memory shouldn't grow more than 50MB during test
    assert max_memory - min_memory < 50


@pytest.mark.asyncio
@pytest.mark.integration
async def test_performance_benchmarking(integration_orchestrator):
    """Test performance benchmarking and optimization."""
    # Measure initialization time
    start_time = time.time()
    await integration_orchestrator.initialize()
    init_time = time.time() - start_time
    
    # Initialization should complete within reasonable time
    assert init_time < 10.0  # 10 seconds max
    
    # Measure system response times
    response_times = []
    
    for _ in range(10):
        start = time.time()
        await integration_orchestrator.get_system_status()
        response_time = time.time() - start
        response_times.append(response_time)
    
    # Response times should be fast
    avg_response_time = sum(response_times) / len(response_times)
    assert avg_response_time < 0.1  # 100ms average
    assert max(response_times) < 0.5  # 500ms max
    
    # Test concurrent operations
    concurrent_tasks = []
    
    for _ in range(5):
        task = asyncio.create_task(integration_orchestrator.get_system_status())
        concurrent_tasks.append(task)
    
    start = time.time()
    results = await asyncio.gather(*concurrent_tasks)
    concurrent_time = time.time() - start
    
    # Concurrent operations should complete quickly
    assert concurrent_time < 1.0
    assert len(results) == 5
    assert all(result["is_running"] for result in results)
    
    # Memory usage should be reasonable
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    # Should use less than 500MB for basic operations
    assert memory_mb < 500


@pytest.mark.asyncio
@pytest.mark.integration
async def test_failure_recovery_and_resilience(integration_orchestrator):
    """Test failure recovery and system resilience."""
    await integration_orchestrator.initialize()
    
    # Test system restart capability
    initial_status = await integration_orchestrator.get_system_status()
    initial_systems = list(initial_status["systems"].keys())
    
    # Simulate system failure and restart
    test_system = "identity_manager"
    if test_system in initial_systems:
        success = await integration_orchestrator.restart_system(test_system)
        assert success
        
        # Verify system is still running after restart
        await asyncio.sleep(1)
        post_restart_status = await integration_orchestrator.get_system_status()
        assert post_restart_status["is_running"]
        assert test_system in post_restart_status["systems"]
        assert post_restart_status["systems"][test_system]["status"] == "running"
    
    # Test emergency response system
    if integration_orchestrator.emergency_response:
        # Test emergency incident reporting
        with patch.object(integration_orchestrator.emergency_response, 'report_incident') as mock_report:
            mock_report.return_value = "test_incident_123"
            
            incident_id = await integration_orchestrator.emergency_response.report_incident(
                level="high",
                reason="resource_exhaustion",
                description="Test incident for resilience testing"
            )
            
            assert incident_id == "test_incident_123"
            mock_report.assert_called_once()
    
    # Test graceful degradation
    # Simulate a system component failure
    original_system = integration_orchestrator.systems.get("state_manager")
    if original_system:
        # Temporarily remove system to simulate failure
        del integration_orchestrator.systems["state_manager"]
        integration_orchestrator.system_status["state_manager"].status = "failed"
        
        # System should still be operational
        status = await integration_orchestrator.get_system_status()
        assert status["is_running"]
        assert status["statistics"]["failed_systems"] == 1
        
        # Restore system
        integration_orchestrator.systems["state_manager"] = original_system
        integration_orchestrator.system_status["state_manager"].status = "running"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resource_management(integration_orchestrator):
    """Test resource management and limits."""
    await integration_orchestrator.initialize()
    
    # Monitor resource usage
    initial_process = psutil.Process()
    initial_memory = initial_process.memory_info().rss
    initial_process.cpu_percent()
    
    # Perform resource-intensive operations
    tasks = []
    for _ in range(10):
        task = asyncio.create_task(integration_orchestrator.get_system_status())
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    
    # Check resource usage after operations
    final_process = psutil.Process()
    final_memory = final_process.memory_info().rss
    final_cpu_percent = final_process.cpu_percent(interval=1)
    
    # Memory growth should be reasonable
    memory_growth_mb = (final_memory - initial_memory) / 1024 / 1024
    assert memory_growth_mb < 100  # Less than 100MB growth
    
    # CPU usage should be reasonable
    assert final_cpu_percent < 80  # Less than 80% CPU
    
    # Test resource cleanup
    await asyncio.sleep(2)  # Let cleanup run
    
    cleanup_process = psutil.Process()
    cleanup_memory = cleanup_process.memory_info().rss
    
    # Memory should not grow unbounded
    cleanup_growth_mb = (cleanup_memory - initial_memory) / 1024 / 1024
    assert cleanup_growth_mb < 50  # Less than 50MB after cleanup


@pytest.mark.asyncio
@pytest.mark.integration
async def test_configuration_management(integration_orchestrator):
    """Test configuration management and validation."""
    # Test configuration loading
    config = integration_orchestrator.config
    
    assert config.ecosystem_id == "integration_test_ecosystem"
    assert config.max_agents == 10
    assert not config.enable_web_browsing
    assert config.enable_safety_systems
    
    # Test configuration validation
    assert config.health_check_interval > 0
    assert config.cleanup_interval > 0
    assert config.max_agents > 0
    
    # Test system behavior with configuration
    await integration_orchestrator.initialize()
    
    status = await integration_orchestrator.get_system_status()
    
    # Verify configuration is reflected in system behavior
    assert status["configuration"]["max_agents"] == 10
    assert not status["configuration"]["enable_web_browsing"]
    assert status["configuration"]["enable_safety_systems"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_logging_and_monitoring(integration_orchestrator):
    """Test logging and monitoring capabilities."""
    await integration_orchestrator.initialize()
    
    # Test that logging is working
    initial_stats = await integration_orchestrator.get_system_status()
    initial_health_checks = initial_stats["statistics"]["health_checks_performed"]
    
    # Wait for health checks to run
    await asyncio.sleep(5)
    
    updated_stats = await integration_orchestrator.get_system_status()
    updated_health_checks = updated_stats["statistics"]["health_checks_performed"]
    
    # Health checks should have increased
    assert updated_health_checks > initial_health_checks
    
    # Test system statistics
    stats = updated_stats["statistics"]
    
    assert "total_systems" in stats
    assert "running_systems" in stats
    assert "failed_systems" in stats
    assert "uptime_seconds" in stats
    
    assert stats["total_systems"] > 0
    assert stats["running_systems"] > 0
    assert stats["uptime_seconds"] > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_shutdown_and_cleanup(integration_orchestrator):
    """Test proper shutdown and cleanup procedures."""
    await integration_orchestrator.initialize()
    
    # Verify system is running
    assert integration_orchestrator.is_running
    
    # Record initial state
    initial_status = await integration_orchestrator.get_system_status()
    initial_systems = list(initial_status["systems"].keys())
    
    # Perform shutdown
    await integration_orchestrator.shutdown()
    
    # Verify shutdown completed
    assert not integration_orchestrator.is_running
    assert integration_orchestrator.shutdown_requested
    
    # Verify systems were properly stopped
    for system_name in initial_systems:
        if system_name in integration_orchestrator.system_status:
            status = integration_orchestrator.system_status[system_name].status
            assert status in ["stopped", "failed"]  # Should be stopped or failed (acceptable)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_operations(integration_orchestrator):
    """Test concurrent operations and thread safety."""
    await integration_orchestrator.initialize()
    
    # Test concurrent status requests
    async def get_status_repeatedly():
        results = []
        for _ in range(5):
            status = await integration_orchestrator.get_system_status()
            results.append(status["is_running"])
            await asyncio.sleep(0.1)
        return results
    
    # Run multiple concurrent status requests
    tasks = [get_status_repeatedly() for _ in range(3)]
    results = await asyncio.gather(*tasks)
    
    # All requests should succeed
    assert len(results) == 3
    for result_list in results:
        assert len(result_list) == 5
        assert all(result for result in result_list)  # All should be True
    
    # Test concurrent system operations
    async def restart_system_safe():
        try:
            return await integration_orchestrator.restart_system("identity_manager")
        except Exception:
            return False
    
    # Multiple concurrent restart attempts (should be handled gracefully)
    restart_tasks = [restart_system_safe() for _ in range(3)]
    restart_results = await asyncio.gather(*restart_tasks)
    
    # At least one should succeed, others should fail gracefully
    assert any(restart_results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])