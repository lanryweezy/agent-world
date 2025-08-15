"""
Ecosystem stress testing for the autonomous AI ecosystem.

These tests push the system to its limits and verify
robustness under extreme conditions.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
import time
import random
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any
import psutil

from autonomous_ai_ecosystem.ecosystem_orchestrator import (
    EcosystemOrchestrator,
    EcosystemConfig
)


@pytest_asyncio.fixture
async def stress_config():
    """Create configuration for stress testing."""
    temp_dir = tempfile.mkdtemp()
    
    config = EcosystemConfig(
        ecosystem_id="stress_test_ecosystem",
        data_directory=temp_dir,
        log_level="ERROR",  # Minimal logging for performance
        max_agents=200,  # High limit for stress testing
        
        # Enable all systems for comprehensive stress testing
        enable_web_browsing=False,  # Keep disabled for safety
        enable_virtual_world=True,
        enable_economy=True,
        enable_reproduction=True,
        enable_distributed_mode=True,
        enable_human_oversight=True,
        enable_safety_systems=True,
        
        # Aggressive intervals for stress testing
        health_check_interval=0.5,
        cleanup_interval=1
    )
    
    yield config, temp_dir
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


class StressTestMonitor:
    """Monitor system resources and performance during stress tests."""
    
    def __init__(self):
        self.start_time = time.time()
        self.process = psutil.Process()
        self.monitoring = False
        self.samples = []
        self.errors = []
        
    def start_monitoring(self):
        """Start resource monitoring."""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1)
            
    def _monitor_loop(self):
        """Monitor system resources in background thread."""
        while self.monitoring:
            try:
                sample = {
                    "timestamp": time.time(),
                    "cpu_percent": self.process.cpu_percent(),
                    "memory_mb": self.process.memory_info().rss / 1024 / 1024,
                    "open_files": len(self.process.open_files()),
                    "threads": self.process.num_threads()
                }
                self.samples.append(sample)
                time.sleep(0.1)
            except Exception as e:
                self.errors.append(f"Monitoring error: {e}")
                
    def record_error(self, error_type: str, details: str):
        """Record an error during stress testing."""
        self.errors.append({
            "type": error_type,
            "details": details,
            "timestamp": time.time()
        })
        
    def get_peak_usage(self) -> Dict[str, Any]:
        """Get peak resource usage during monitoring."""
        if not self.samples:
            return {}
            
        return {
            "peak_cpu_percent": max(s["cpu_percent"] for s in self.samples),
            "peak_memory_mb": max(s["memory_mb"] for s in self.samples),
            "peak_open_files": max(s["open_files"] for s in self.samples),
            "peak_threads": max(s["threads"] for s in self.samples),
            "avg_cpu_percent": sum(s["cpu_percent"] for s in self.samples) / len(self.samples),
            "avg_memory_mb": sum(s["memory_mb"] for s in self.samples) / len(self.samples),
            "total_samples": len(self.samples),
            "total_errors": len(self.errors),
            "duration_seconds": time.time() - self.start_time
        }


@pytest.mark.asyncio
async def test_concurrent_operation_stress(stress_config):
    """Test system under extreme concurrent operation load."""
    config, temp_dir = stress_config
    
    orchestrator = EcosystemOrchestrator(config)
    monitor = StressTestMonitor()
    
    try:
        await orchestrator.initialize()
        monitor.start_monitoring()
        
        # Create a large number of concurrent operations
        concurrent_tasks = []
        
        # Spawn many agents concurrently
        agent_spawn_tasks = []
        for i in range(50):
            async def spawn_agent(agent_num):
                try:
                    with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value=f"stress_process_{agent_num}"):
                        agent_id = await orchestrator.spawn_agent({
                            "agent_id": f"stress_agent_{agent_num}",
                            "config": {"stress_test": True}
                        })
                        return agent_id
                except Exception as e:
                    monitor.record_error("agent_spawn", str(e))
                    return None
            
            agent_spawn_tasks.append(spawn_agent(i))
        
        # Execute agent spawning concurrently
        spawned_agents = await asyncio.gather(*agent_spawn_tasks, return_exceptions=True)
        successful_spawns = [a for a in spawned_agents if a and not isinstance(a, Exception)]
        
        assert len(successful_spawns) >= 40, f"Should successfully spawn most agents, got {len(successful_spawns)}"
        
        # Register capabilities concurrently
        capability_tasks = []
        for agent_id in successful_spawns[:30]:  # Use subset to avoid overwhelming
            async def register_capability(aid):
                try:
                    capability_id = await orchestrator.capability_registry.register_capability(
                        agent_id=aid,
                        service_type="stress_test",
                        capabilities=["concurrent_operations"],
                        expertise_level=random.uniform(0.5, 0.9)
                    )
                    return capability_id
                except Exception as e:
                    monitor.record_error("capability_registration", str(e))
                    return None
            
            capability_tasks.append(register_capability(agent_id))
        
        capability_results = await asyncio.gather(*capability_tasks, return_exceptions=True)
        successful_capabilities = [c for c in capability_results if c and not isinstance(c, Exception)]
        
        assert len(successful_capabilities) >= 25, f"Should register most capabilities, got {len(successful_capabilities)}"
        
        # Perform many concurrent service operations
        service_tasks = []
        for i in range(100):
            async def service_operation(op_num):
                try:
                    # System status check
                    status = await orchestrator.get_system_status()
                    
                    # Safety validation
                    validation = await orchestrator.safety_validator.validate_code(
                        code=f"print('Stress test operation {op_num}')",
                        agent_id=f"stress_agent_{op_num % len(successful_spawns)}",
                        context="stress_test"
                    )
                    
                    # Service discovery
                    agents = await orchestrator.capability_registry.find_capable_agents(
                        service_type="stress_test",
                        required_capabilities=[],
                        min_expertise=0.4
                    )
                    
                    # Quality feedback
                    if agents:
                        feedback_id = await orchestrator.quality_feedback.submit_feedback(
                            service_id=f"stress_service_{op_num}",
                            agent_id=agents[0]["agent_id"],
                            rating=random.uniform(3.0, 5.0),
                            feedback_text=f"Stress test feedback {op_num}",
                            service_type="stress_test"
                        )
                        return feedback_id
                    
                    return "no_agents"
                except Exception as e:
                    monitor.record_error("service_operation", str(e))
                    return None
            
            service_tasks.append(service_operation(i))
        
        # Execute all service operations concurrently
        service_results = await asyncio.gather(*service_tasks, return_exceptions=True)
        successful_services = [s for s in service_results if s and not isinstance(s, Exception)]
        
        assert len(successful_services) >= 80, f"Should complete most service operations, got {len(successful_services)}"
        
        # Test emergency response under load
        incident_tasks = []
        for i in range(20):
            async def report_incident(incident_num):
                try:
                    incident_id = await orchestrator.emergency_response.report_incident(
                        level=random.choice(["low", "medium", "high"]),
                        reason="stress_test",
                        description=f"Concurrent stress test incident {incident_num}",
                        component="stress_test"
                    )
                    return incident_id
                except Exception as e:
                    monitor.record_error("incident_report", str(e))
                    return None
            
            incident_tasks.append(report_incident(i))
        
        incident_results = await asyncio.gather(*incident_tasks, return_exceptions=True)
        successful_incidents = [i for i in incident_results if i and not isinstance(i, Exception)]
        
        assert len(successful_incidents) >= 15, f"Should handle most incident reports, got {len(successful_incidents)}"
        
        # Verify system remains responsive
        final_status = await orchestrator.get_system_status()
        assert final_status["is_running"], "System should remain running after concurrent stress"
        
        # Check resource usage
        monitor.stop_monitoring()
        peak_usage = monitor.get_peak_usage()
        
        print(f"\nConcurrent Operation Stress Results:")
        print(f"  Successful agent spawns: {len(successful_spawns)}/50")
        print(f"  Successful capability registrations: {len(successful_capabilities)}/30")
        print(f"  Successful service operations: {len(successful_services)}/100")
        print(f"  Successful incident reports: {len(successful_incidents)}/20")
        print(f"  Peak CPU usage: {peak_usage.get('peak_cpu_percent', 0):.1f}%")
        print(f"  Peak memory usage: {peak_usage.get('peak_memory_mb', 0):.1f}MB")
        print(f"  Peak open files: {peak_usage.get('peak_open_files', 0)}")
        print(f"  Total errors: {peak_usage.get('total_errors', 0)}")
        
        # Resource usage should be reasonable
        assert peak_usage.get("peak_memory_mb", 0) < 2000, "Memory usage should be < 2GB"
        assert peak_usage.get("total_errors", 0) < 10, "Should have minimal errors"
        
    finally:
        monitor.stop_monitoring()
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_memory_leak_stress(stress_config):
    """Test for memory leaks under sustained load."""
    config, temp_dir = stress_config
    
    orchestrator = EcosystemOrchestrator(config)
    monitor = StressTestMonitor()
    
    try:
        await orchestrator.initialize()
        monitor.start_monitoring()
        
        # Run sustained operations to detect memory leaks
        iterations = 20
        memory_samples = []
        
        for iteration in range(iterations):
            iteration_start_memory = monitor.process.memory_info().rss / 1024 / 1024
            
            # Perform a cycle of operations
            agents_created = []
            
            # Create agents
            for i in range(10):
                agent_id = f"leak_test_agent_{iteration}_{i}"
                
                with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value=f"leak_process_{iteration}_{i}"):
                    spawned_agent_id = await orchestrator.spawn_agent({
                        "agent_id": agent_id,
                        "config": {"leak_test": True}
                    })
                    agents_created.append(spawned_agent_id)
            
            # Register and use capabilities
            for agent_id in agents_created:
                capability_id = await orchestrator.capability_registry.register_capability(
                    agent_id=agent_id,
                    service_type="leak_test",
                    capabilities=["memory_operations"],
                    expertise_level=0.7
                )
                
                # Perform operations
                for _ in range(5):
                    await orchestrator.get_system_status()
                    
                    validation = await orchestrator.safety_validator.validate_code(
                        code="x = list(range(100))",
                        agent_id=agent_id,
                        context="leak_test"
                    )
                    
                    feedback_id = await orchestrator.quality_feedback.submit_feedback(
                        service_id=f"leak_service_{iteration}_{_}",
                        agent_id=agent_id,
                        rating=4.0,
                        feedback_text="Memory leak test",
                        service_type="leak_test"
                    )
            
            # "Stop" agents (simulate cleanup)
            for agent_id in agents_created:
                with patch.object(orchestrator.agent_manager, 'stop_agent', return_value=True):
                    await orchestrator.stop_agent(agent_id)
            
            # Force cleanup
            await asyncio.sleep(0.5)  # Allow cleanup to run
            
            iteration_end_memory = monitor.process.memory_info().rss / 1024 / 1024
            memory_samples.append({
                "iteration": iteration,
                "start_memory": iteration_start_memory,
                "end_memory": iteration_end_memory,
                "memory_delta": iteration_end_memory - iteration_start_memory
            })
            
            print(f"Iteration {iteration}: {iteration_start_memory:.1f}MB → {iteration_end_memory:.1f}MB (Δ{iteration_end_memory - iteration_start_memory:+.1f}MB)")
        
        # Analyze memory usage trends
        initial_memory = memory_samples[0]["start_memory"]
        final_memory = memory_samples[-1]["end_memory"]
        total_growth = final_memory - initial_memory
        
        # Calculate trend
        memory_trend = sum(sample["memory_delta"] for sample in memory_samples[-5:]) / 5  # Average of last 5 iterations
        
        monitor.stop_monitoring()
        peak_usage = monitor.get_peak_usage()
        
        print(f"\nMemory Leak Stress Results:")
        print(f"  Initial memory: {initial_memory:.1f}MB")
        print(f"  Final memory: {final_memory:.1f}MB")
        print(f"  Total growth: {total_growth:+.1f}MB")
        print(f"  Recent trend: {memory_trend:+.1f}MB/iteration")
        print(f"  Peak memory: {peak_usage.get('peak_memory_mb', 0):.1f}MB")
        
        # Memory growth should be minimal
        assert total_growth < 200, f"Total memory growth should be < 200MB, was {total_growth:.1f}MB"
        assert memory_trend < 5, f"Memory trend should be < 5MB/iteration, was {memory_trend:.1f}MB"
        
        # System should remain responsive
        final_status = await orchestrator.get_system_status()
        assert final_status["is_running"], "System should remain running after memory stress"
        
    finally:
        monitor.stop_monitoring()
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_failure_recovery_stress(stress_config):
    """Test system recovery under repeated failures."""
    config, temp_dir = stress_config
    
    orchestrator = EcosystemOrchestrator(config)
    monitor = StressTestMonitor()
    
    try:
        await orchestrator.initialize()
        monitor.start_monitoring()
        
        # Create baseline agents
        baseline_agents = []
        for i in range(20):
            agent_id = f"recovery_agent_{i}"
            
            with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value=f"recovery_process_{i}"):
                spawned_agent_id = await orchestrator.spawn_agent({
                    "agent_id": agent_id,
                    "config": {"recovery_test": True}
                })
                baseline_agents.append(spawned_agent_id)
                
                # Register capabilities
                capability_id = await orchestrator.capability_registry.register_capability(
                    agent_id=agent_id,
                    service_type="recovery_test",
                    capabilities=["failure_recovery"],
                    expertise_level=0.8
                )
        
        recovery_cycles = 10
        successful_recoveries = 0
        
        for cycle in range(recovery_cycles):
            print(f"Recovery cycle {cycle + 1}/{recovery_cycles}")
            
            # Simulate system failures
            failed_systems = random.sample(
                ["safety_validator", "capability_registry", "quality_feedback"], 
                random.randint(1, 2)
            )
            
            for system_name in failed_systems:
                # Mark system as failed
                if system_name in orchestrator.system_status:
                    orchestrator.system_status[system_name].status = "failed"
                    orchestrator.system_status[system_name].error_message = f"Stress test failure {cycle}"
            
            # Try to continue operations during failure
            try:
                status = await orchestrator.get_system_status()
                assert not status["is_running"] or len(failed_systems) == 0, "System should detect failures"
            except Exception as e:
                monitor.record_error("status_during_failure", str(e))
            
            # Attempt recovery
            recovery_success = True
            for system_name in failed_systems:
                try:
                    restart_success = await orchestrator.restart_system(system_name)
                    if not restart_success:
                        recovery_success = False
                        monitor.record_error("system_restart", f"Failed to restart {system_name}")
                except Exception as e:
                    recovery_success = False
                    monitor.record_error("system_restart", f"Exception restarting {system_name}: {e}")
            
            if recovery_success:
                successful_recoveries += 1
                
                # Verify system is operational after recovery
                try:
                    status = await orchestrator.get_system_status()
                    assert status["is_running"], "System should be running after recovery"
                    
                    # Test basic operations
                    matching_agents = await orchestrator.capability_registry.find_capable_agents(
                        service_type="recovery_test",
                        required_capabilities=[],
                        min_expertise=0.5
                    )
                    
                    assert len(matching_agents) > 0, "Should find agents after recovery"
                    
                    # Test safety validation
                    validation = await orchestrator.safety_validator.validate_code(
                        code="print('Recovery test')",
                        agent_id=baseline_agents[0],
                        context="recovery_test"
                    )
                    
                    assert validation["is_safe"], "Safety validation should work after recovery"
                    
                except Exception as e:
                    monitor.record_error("post_recovery_test", str(e))
                    successful_recoveries -= 1
            
            # Brief pause between cycles
            await asyncio.sleep(0.5)
        
        # Report incidents for all failures
        for cycle in range(recovery_cycles):
            incident_id = await orchestrator.emergency_response.report_incident(
                level="high",
                reason="stress_test_failure",
                description=f"Failure recovery stress test cycle {cycle}",
                component="stress_test"
            )
        
        monitor.stop_monitoring()
        peak_usage = monitor.get_peak_usage()
        
        print(f"\nFailure Recovery Stress Results:")
        print(f"  Recovery cycles: {recovery_cycles}")
        print(f"  Successful recoveries: {successful_recoveries}")
        print(f"  Recovery success rate: {successful_recoveries/recovery_cycles*100:.1f}%")
        print(f"  Total errors: {peak_usage.get('total_errors', 0)}")
        print(f"  Peak memory: {peak_usage.get('peak_memory_mb', 0):.1f}MB")
        
        # Should recover from most failures
        assert successful_recoveries >= recovery_cycles * 0.8, f"Should recover from at least 80% of failures, got {successful_recoveries}/{recovery_cycles}"
        
        # System should be running at the end
        final_status = await orchestrator.get_system_status()
        assert final_status["is_running"], "System should be running after recovery stress"
        
    finally:
        monitor.stop_monitoring()
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_long_running_stability(stress_config):
    """Test system stability over extended runtime."""
    config, temp_dir = stress_config
    
    orchestrator = EcosystemOrchestrator(config)
    monitor = StressTestMonitor()
    
    try:
        await orchestrator.initialize()
        monitor.start_monitoring()
        
        # Create persistent agents
        persistent_agents = []
        for i in range(15):
            agent_id = f"stable_agent_{i}"
            
            with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value=f"stable_process_{i}"):
                spawned_agent_id = await orchestrator.spawn_agent({
                    "agent_id": agent_id,
                    "config": {"stability_test": True}
                })
                persistent_agents.append(spawned_agent_id)
                
                capability_id = await orchestrator.capability_registry.register_capability(
                    agent_id=agent_id,
                    service_type="stability",
                    capabilities=["long_running_operations"],
                    expertise_level=0.7
                )
        
        # Run continuous operations for extended period
        runtime_seconds = 30  # Reduced for test efficiency
        operation_count = 0
        error_count = 0
        
        start_time = time.time()
        
        while time.time() - start_time < runtime_seconds:
            try:
                # Rotate through different operations
                operation_type = operation_count % 4
                
                if operation_type == 0:
                    # System status check
                    status = await orchestrator.get_system_status()
                    assert status["is_running"]
                    
                elif operation_type == 1:
                    # Service discovery
                    agents = await orchestrator.capability_registry.find_capable_agents(
                        service_type="stability",
                        required_capabilities=[],
                        min_expertise=0.5
                    )
                    assert len(agents) == len(persistent_agents)
                    
                elif operation_type == 2:
                    # Safety validation
                    agent_id = random.choice(persistent_agents)
                    validation = await orchestrator.safety_validator.validate_code(
                        code=f"result = {random.randint(1, 100)} * 2",
                        agent_id=agent_id,
                        context="stability_test"
                    )
                    assert validation["is_safe"]
                    
                else:
                    # Quality feedback
                    agent_id = random.choice(persistent_agents)
                    feedback_id = await orchestrator.quality_feedback.submit_feedback(
                        service_id=f"stability_service_{operation_count}",
                        agent_id=agent_id,
                        rating=random.uniform(3.5, 5.0),
                        feedback_text=f"Stability test operation {operation_count}",
                        service_type="stability"
                    )
                    assert feedback_id
                
                operation_count += 1
                
                # Brief pause to avoid overwhelming
                await asyncio.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                monitor.record_error("stability_operation", str(e))
                
                # Don't fail immediately on errors, but track them
                if error_count > operation_count * 0.1:  # More than 10% error rate
                    break
        
        actual_runtime = time.time() - start_time
        
        monitor.stop_monitoring()
        peak_usage = monitor.get_peak_usage()
        
        print(f"\nLong-Running Stability Results:")
        print(f"  Runtime: {actual_runtime:.1f}s")
        print(f"  Operations completed: {operation_count}")
        print(f"  Operations per second: {operation_count/actual_runtime:.1f}")
        print(f"  Error count: {error_count}")
        print(f"  Error rate: {error_count/operation_count*100:.1f}%")
        print(f"  Peak memory: {peak_usage.get('peak_memory_mb', 0):.1f}MB")
        print(f"  Average memory: {peak_usage.get('avg_memory_mb', 0):.1f}MB")
        print(f"  Peak CPU: {peak_usage.get('peak_cpu_percent', 0):.1f}%")
        
        # Verify stability metrics
        assert operation_count > runtime_seconds * 5, f"Should complete at least 5 ops/sec, got {operation_count/actual_runtime:.1f}"
        assert error_count < operation_count * 0.05, f"Error rate should be < 5%, got {error_count/operation_count*100:.1f}%"
        
        # System should still be responsive
        final_status = await orchestrator.get_system_status()
        assert final_status["is_running"], "System should remain running after stability test"
        
        # Memory usage should be stable
        memory_growth = peak_usage.get("peak_memory_mb", 0) - peak_usage.get("avg_memory_mb", 0)
        assert memory_growth < 100, f"Memory growth should be < 100MB, was {memory_growth:.1f}MB"
        
    finally:
        monitor.stop_monitoring()
        await orchestrator.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])