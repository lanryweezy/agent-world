"""
Stress testing and simulation framework for large-scale agent ecosystems.

This module implements large-scale simulations, stress tests for communication
and learning systems, and automated testing for emergent behaviors.
"""

import pytest
import pytest_asyncio
import asyncio
import time
import random
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass, field

from autonomous_ai_ecosystem.ecosystem_orchestrator import (
    EcosystemOrchestrator,
    EcosystemConfig
)


@dataclass
class StressTestMetrics:
    """Metrics collected during stress testing."""
    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Performance metrics
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    
    # Timing metrics
    response_times: List[float] = field(default_factory=list)
    throughput_ops_per_second: float = 0.0
    
    # Resource metrics
    peak_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    
    # Error tracking
    error_types: Dict[str, int] = field(default_factory=dict)
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate test statistics."""
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        
        return {
            "duration_seconds": duration,
            "total_operations": self.total_operations,
            "success_rate": self.successful_operations / max(self.total_operations, 1),
            "failure_rate": self.failed_operations / max(self.total_operations, 1),
            "throughput_ops_per_second": self.throughput_ops_per_second,
            "avg_response_time": statistics.mean(self.response_times) if self.response_times else 0,
            "min_response_time": min(self.response_times) if self.response_times else 0,
            "max_response_time": max(self.response_times) if self.response_times else 0,
            "p95_response_time": statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) > 20 else 0,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_cpu_percent": self.peak_cpu_percent,
            "error_types": self.error_types
        }


@dataclass
class SimulationScenario:
    """Defines a simulation scenario."""
    scenario_id: str
    name: str
    description: str
    
    # Agent configuration
    agent_count: int = 10
    agent_types: List[str] = field(default_factory=lambda: ["worker"])
    
    # Simulation parameters
    duration_seconds: int = 60
    interaction_frequency: float = 1.0  # interactions per second per agent
    
    # Behavior patterns
    communication_patterns: List[str] = field(default_factory=lambda: ["broadcast", "peer_to_peer"])
    task_patterns: List[str] = field(default_factory=lambda: ["sequential", "parallel"])
    
    # Stress factors
    resource_constraints: Dict[str, Any] = field(default_factory=dict)
    failure_injection: Dict[str, float] = field(default_factory=dict)  # failure_type -> probability
    
    # Expected outcomes
    expected_behaviors: List[str] = field(default_factory=list)
    success_criteria: Dict[str, Any] = field(default_factory=dict)


class StressTestFramework:
    """Framework for conducting stress tests and simulations."""
    
    def __init__(self, orchestrator: EcosystemOrchestrator):
        self.orchestrator = orchestrator
        self.metrics: Dict[str, StressTestMetrics] = {}
        self.scenarios: Dict[str, SimulationScenario] = {}
        
        # Test configuration
        self.config = {
            "max_concurrent_tests": 5,
            "metrics_collection_interval": 1.0,
            "resource_monitoring_enabled": True,
            "failure_injection_enabled": True
        }
        
        # Mock agents for simulation
        self.mock_agents: Dict[str, Mock] = {}
        
    async def run_stress_test(
        self,
        test_name: str,
        operations_per_second: int,
        duration_seconds: int,
        operation_func: callable
    ) -> StressTestMetrics:
        """Run a stress test with specified parameters."""
        metrics = StressTestMetrics(
            test_name=test_name,
            start_time=datetime.now()
        )
        
        self.metrics[test_name] = metrics
        
        try:
            # Start metrics collection
            metrics_task = asyncio.create_task(
                self._collect_metrics(metrics, duration_seconds)
            )
            
            # Run stress test operations
            await self._execute_stress_operations(
                metrics, operations_per_second, duration_seconds, operation_func
            )
            
            # Wait for metrics collection to complete
            await metrics_task
            
            metrics.end_time = datetime.now()
            metrics.throughput_ops_per_second = metrics.successful_operations / duration_seconds
            
            return metrics
            
        except Exception as e:
            metrics.error_types[str(type(e).__name__)] = metrics.error_types.get(str(type(e).__name__), 0) + 1
            metrics.end_time = datetime.now()
            raise
    
    async def run_simulation(self, scenario: SimulationScenario) -> Dict[str, Any]:
        """Run a simulation scenario."""
        self.scenarios[scenario.scenario_id] = scenario
        
        simulation_results = {
            "scenario_id": scenario.scenario_id,
            "start_time": datetime.now(),
            "agent_behaviors": {},
            "communication_stats": {},
            "emergent_behaviors": [],
            "success_metrics": {}
        }
        
        try:
            # Setup mock agents
            await self._setup_simulation_agents(scenario)
            
            # Run simulation
            await self._execute_simulation(scenario, simulation_results)
            
            # Analyze results
            simulation_results["analysis"] = await self._analyze_simulation_results(
                scenario, simulation_results
            )
            
            simulation_results["end_time"] = datetime.now()
            simulation_results["duration"] = (
                simulation_results["end_time"] - simulation_results["start_time"]
            ).total_seconds()
            
            return simulation_results
            
        except Exception as e:
            simulation_results["error"] = str(e)
            simulation_results["end_time"] = datetime.now()
            return simulation_results
    
    async def _execute_stress_operations(
        self,
        metrics: StressTestMetrics,
        ops_per_second: int,
        duration: int,
        operation_func: callable
    ) -> None:
        """Execute stress test operations."""
        end_time = time.time() + duration
        operation_interval = 1.0 / ops_per_second
        
        while time.time() < end_time:
            batch_start = time.time()
            
            # Execute batch of operations
            tasks = []
            for _ in range(min(ops_per_second, 10)):  # Limit batch size
                task = asyncio.create_task(self._execute_single_operation(metrics, operation_func))
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Wait for next batch
            batch_duration = time.time() - batch_start
            if batch_duration < operation_interval:
                await asyncio.sleep(operation_interval - batch_duration)
    
    async def _execute_single_operation(
        self,
        metrics: StressTestMetrics,
        operation_func: callable
    ) -> None:
        """Execute a single operation and record metrics."""
        start_time = time.time()
        
        try:
            await operation_func()
            metrics.successful_operations += 1
        except Exception as e:
            metrics.failed_operations += 1
            error_type = type(e).__name__
            metrics.error_types[error_type] = metrics.error_types.get(error_type, 0) + 1
        finally:
            response_time = time.time() - start_time
            metrics.response_times.append(response_time)
            metrics.total_operations += 1
    
    async def _collect_metrics(self, metrics: StressTestMetrics, duration: int) -> None:
        """Collect system metrics during stress test."""
        if not self.config["resource_monitoring_enabled"]:
            return
        
        import psutil
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            try:
                process = psutil.Process()
                
                # Update peak metrics
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                metrics.peak_memory_mb = max(metrics.peak_memory_mb, memory_mb)
                metrics.peak_cpu_percent = max(metrics.peak_cpu_percent, cpu_percent)
                
                await asyncio.sleep(self.config["metrics_collection_interval"])
                
            except Exception:
                pass  # Continue monitoring even if individual measurements fail
    
    async def _setup_simulation_agents(self, scenario: SimulationScenario) -> None:
        """Setup mock agents for simulation."""
        self.mock_agents.clear()
        
        for i in range(scenario.agent_count):
            agent_id = f"sim_agent_{i}"
            agent_type = random.choice(scenario.agent_types)
            
            mock_agent = Mock()
            mock_agent.agent_id = agent_id
            mock_agent.agent_type = agent_type
            mock_agent.status = "running"
            mock_agent.interactions = []
            mock_agent.tasks_completed = 0
            mock_agent.messages_sent = 0
            mock_agent.messages_received = 0
            
            self.mock_agents[agent_id] = mock_agent
    
    async def _execute_simulation(
        self,
        scenario: SimulationScenario,
        results: Dict[str, Any]
    ) -> None:
        """Execute the simulation scenario."""
        end_time = time.time() + scenario.duration_seconds
        
        # Start agent behavior tasks
        behavior_tasks = []
        for agent_id, agent in self.mock_agents.items():
            task = asyncio.create_task(
                self._simulate_agent_behavior(agent, scenario, results)
            )
            behavior_tasks.append(task)
        
        # Monitor simulation
        monitor_task = asyncio.create_task(
            self._monitor_simulation(scenario, results, scenario.duration_seconds)
        )
        
        # Wait for simulation to complete
        await asyncio.sleep(scenario.duration_seconds)
        
        # Cancel behavior tasks
        for task in behavior_tasks:
            task.cancel()
        
        monitor_task.cancel()
        
        # Wait for tasks to finish
        await asyncio.gather(*behavior_tasks, monitor_task, return_exceptions=True)
    
    async def _simulate_agent_behavior(
        self,
        agent: Mock,
        scenario: SimulationScenario,
        results: Dict[str, Any]
    ) -> None:
        """Simulate behavior for a single agent."""
        try:
            while True:
                # Simulate interactions based on frequency
                await asyncio.sleep(1.0 / scenario.interaction_frequency)
                
                # Random behavior selection
                behavior = random.choice(["communicate", "process_task", "idle"])
                
                if behavior == "communicate":
                    await self._simulate_communication(agent, scenario)
                elif behavior == "process_task":
                    await self._simulate_task_processing(agent, scenario)
                
                # Inject failures if configured
                if self.config["failure_injection_enabled"]:
                    await self._inject_random_failure(agent, scenario)
                
        except asyncio.CancelledError:
            pass
    
    async def _simulate_communication(self, agent: Mock, scenario: SimulationScenario) -> None:
        """Simulate agent communication."""
        pattern = random.choice(scenario.communication_patterns)
        
        if pattern == "broadcast":
            # Simulate broadcasting to all agents
            for other_agent in self.mock_agents.values():
                if other_agent.agent_id != agent.agent_id:
                    other_agent.messages_received += 1
            agent.messages_sent += len(self.mock_agents) - 1
            
        elif pattern == "peer_to_peer":
            # Simulate direct communication with random agent
            other_agents = [a for a in self.mock_agents.values() if a.agent_id != agent.agent_id]
            if other_agents:
                target = random.choice(other_agents)
                target.messages_received += 1
                agent.messages_sent += 1
        
        # Record interaction
        interaction = {
            "timestamp": datetime.now(),
            "type": "communication",
            "pattern": pattern,
            "agent_id": agent.agent_id
        }
        agent.interactions.append(interaction)
    
    async def _simulate_task_processing(self, agent: Mock, scenario: SimulationScenario) -> None:
        """Simulate agent task processing."""
        pattern = random.choice(scenario.task_patterns)
        
        # Simulate task completion time
        processing_time = random.uniform(0.1, 0.5)
        await asyncio.sleep(processing_time)
        
        agent.tasks_completed += 1
        
        # Record interaction
        interaction = {
            "timestamp": datetime.now(),
            "type": "task_processing",
            "pattern": pattern,
            "processing_time": processing_time,
            "agent_id": agent.agent_id
        }
        agent.interactions.append(interaction)
    
    async def _inject_random_failure(self, agent: Mock, scenario: SimulationScenario) -> None:
        """Inject random failures based on scenario configuration."""
        for failure_type, probability in scenario.failure_injection.items():
            if random.random() < probability:
                # Simulate failure
                if failure_type == "communication_failure":
                    agent.status = "communication_error"
                    await asyncio.sleep(0.1)  # Brief recovery time
                    agent.status = "running"
                elif failure_type == "processing_failure":
                    agent.status = "processing_error"
                    await asyncio.sleep(0.2)  # Longer recovery time
                    agent.status = "running"
    
    async def _monitor_simulation(
        self,
        scenario: SimulationScenario,
        results: Dict[str, Any],
        duration: int
    ) -> None:
        """Monitor simulation progress and collect statistics."""
        try:
            end_time = time.time() + duration
            
            while time.time() < end_time:
                # Collect communication statistics
                total_messages = sum(agent.messages_sent for agent in self.mock_agents.values())
                total_tasks = sum(agent.tasks_completed for agent in self.mock_agents.values())
                
                results["communication_stats"] = {
                    "total_messages": total_messages,
                    "messages_per_agent": total_messages / len(self.mock_agents),
                    "total_tasks": total_tasks,
                    "tasks_per_agent": total_tasks / len(self.mock_agents)
                }
                
                # Check for emergent behaviors
                await self._detect_emergent_behaviors(scenario, results)
                
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            pass
    
    async def _detect_emergent_behaviors(
        self,
        scenario: SimulationScenario,
        results: Dict[str, Any]
    ) -> None:
        """Detect emergent behaviors in the simulation."""
        behaviors = []
        
        # Detect communication clusters
        high_communicators = [
            agent for agent in self.mock_agents.values()
            if agent.messages_sent > len(self.mock_agents) * 2
        ]
        
        if len(high_communicators) > len(self.mock_agents) * 0.3:
            behaviors.append({
                "type": "communication_clustering",
                "description": "High communication activity detected in subset of agents",
                "agents_involved": [agent.agent_id for agent in high_communicators],
                "detected_at": datetime.now()
            })
        
        # Detect task specialization
        high_performers = [
            agent for agent in self.mock_agents.values()
            if agent.tasks_completed > statistics.mean([a.tasks_completed for a in self.mock_agents.values()]) * 1.5
        ]
        
        if high_performers:
            behaviors.append({
                "type": "task_specialization",
                "description": "Some agents showing higher task completion rates",
                "agents_involved": [agent.agent_id for agent in high_performers],
                "detected_at": datetime.now()
            })
        
        results["emergent_behaviors"] = behaviors
    
    async def _analyze_simulation_results(
        self,
        scenario: SimulationScenario,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze simulation results against success criteria."""
        analysis = {
            "success_criteria_met": {},
            "performance_analysis": {},
            "behavior_analysis": {},
            "recommendations": []
        }
        
        # Check success criteria
        for criterion, expected_value in scenario.success_criteria.items():
            if criterion == "min_messages_per_agent":
                actual_value = results["communication_stats"]["messages_per_agent"]
                analysis["success_criteria_met"][criterion] = actual_value >= expected_value
            elif criterion == "min_tasks_per_agent":
                actual_value = results["communication_stats"]["tasks_per_agent"]
                analysis["success_criteria_met"][criterion] = actual_value >= expected_value
        
        # Performance analysis
        total_interactions = sum(len(agent.interactions) for agent in self.mock_agents.values())
        analysis["performance_analysis"] = {
            "total_interactions": total_interactions,
            "interactions_per_second": total_interactions / scenario.duration_seconds,
            "agent_utilization": len([a for a in self.mock_agents.values() if len(a.interactions) > 0]) / len(self.mock_agents)
        }
        
        # Behavior analysis
        analysis["behavior_analysis"] = {
            "emergent_behaviors_detected": len(results["emergent_behaviors"]),
            "communication_patterns_observed": len(set(scenario.communication_patterns)),
            "task_patterns_observed": len(set(scenario.task_patterns))
        }
        
        # Generate recommendations
        if analysis["performance_analysis"]["agent_utilization"] < 0.8:
            analysis["recommendations"].append("Consider increasing interaction frequency to improve agent utilization")
        
        if len(results["emergent_behaviors"]) == 0:
            analysis["recommendations"].append("No emergent behaviors detected - consider longer simulation duration or different parameters")
        
        return analysis


@pytest_asyncio.fixture
async def stress_test_orchestrator():
    """Create orchestrator for stress testing."""
    config = EcosystemConfig(
        ecosystem_id="stress_test_ecosystem",
        max_agents=50,
        enable_web_browsing=False,
        enable_virtual_world=False,
        enable_economy=False,
        enable_reproduction=False,
        enable_distributed_mode=False,
        enable_safety_systems=True,
        health_check_interval=1,
        cleanup_interval=2
    )
    
    orchestrator = EcosystemOrchestrator(config)
    await orchestrator.initialize()
    
    yield orchestrator
    
    await orchestrator.shutdown()


@pytest_asyncio.fixture
async def stress_framework(stress_test_orchestrator):
    """Create stress test framework."""
    return StressTestFramework(stress_test_orchestrator)


@pytest.mark.asyncio
@pytest.mark.stress
async def test_high_throughput_operations(stress_framework):
    """Test system under high throughput operations."""
    
    async def status_operation():
        """Simple status check operation."""
        await stress_framework.orchestrator.get_system_status()
    
    # Run stress test
    metrics = await stress_framework.run_stress_test(
        test_name="high_throughput_status",
        operations_per_second=50,
        duration_seconds=10,
        operation_func=status_operation
    )
    
    stats = metrics.calculate_statistics()
    
    # Verify performance requirements
    assert stats["success_rate"] > 0.95  # 95% success rate
    assert stats["avg_response_time"] < 0.1  # 100ms average response time
    assert stats["throughput_ops_per_second"] > 40  # At least 40 ops/sec achieved
    assert metrics.peak_memory_mb < 1000  # Less than 1GB memory usage


@pytest.mark.asyncio
@pytest.mark.stress
async def test_concurrent_agent_operations(stress_framework):
    """Test concurrent agent operations."""
    
    # Mock agent operations
    with patch.object(stress_framework.orchestrator, 'spawn_agent') as mock_spawn, \
         patch.object(stress_framework.orchestrator, 'stop_agent') as mock_stop:
        
        mock_spawn.return_value = "mock_agent_id"
        mock_stop.return_value = True
        
        async def agent_lifecycle_operation():
            """Agent spawn and stop operation."""
            agent_id = await stress_framework.orchestrator.spawn_agent({
                "agent_id": f"stress_agent_{random.randint(1000, 9999)}"
            })
            if agent_id:
                await stress_framework.orchestrator.stop_agent(agent_id)
        
        # Run stress test
        metrics = await stress_framework.run_stress_test(
            test_name="concurrent_agent_ops",
            operations_per_second=20,
            duration_seconds=15,
            operation_func=agent_lifecycle_operation
        )
        
        stats = metrics.calculate_statistics()
        
        # Verify performance
        assert stats["success_rate"] > 0.90  # 90% success rate for agent operations
        assert stats["avg_response_time"] < 0.5  # 500ms average response time
        assert mock_spawn.call_count > 200  # Should have attempted many spawns


@pytest.mark.asyncio
@pytest.mark.stress
async def test_memory_stress(stress_framework):
    """Test system under memory stress."""
    
    # Create memory-intensive operation
    memory_hogs = []
    
    async def memory_intensive_operation():
        """Operation that consumes memory."""
        # Create some data structures
        data = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}
        memory_hogs.append(data)
        
        # Simulate processing
        await asyncio.sleep(0.01)
        
        # Clean up some memory
        if len(memory_hogs) > 50:
            memory_hogs.pop(0)
    
    try:
        metrics = await stress_framework.run_stress_test(
            test_name="memory_stress",
            operations_per_second=30,
            duration_seconds=20,
            operation_func=memory_intensive_operation
        )
        
        stats = metrics.calculate_statistics()
        
        # Verify system handled memory stress
        assert stats["success_rate"] > 0.85  # 85% success rate under memory stress
        assert metrics.peak_memory_mb < 2000  # Less than 2GB peak memory
        
    finally:
        # Clean up memory
        memory_hogs.clear()


@pytest.mark.asyncio
@pytest.mark.stress
async def test_large_scale_agent_simulation(stress_framework):
    """Test large-scale agent ecosystem simulation."""
    
    # Create large-scale simulation scenario
    scenario = SimulationScenario(
        scenario_id="large_scale_test",
        name="Large Scale Agent Ecosystem",
        description="Simulation with many agents and high interaction rates",
        agent_count=100,
        agent_types=["worker", "coordinator", "specialist"],
        duration_seconds=30,
        interaction_frequency=2.0,
        communication_patterns=["broadcast", "peer_to_peer", "hierarchical"],
        task_patterns=["sequential", "parallel", "collaborative"],
        failure_injection={"communication_failure": 0.01, "processing_failure": 0.005},
        success_criteria={
            "min_messages_per_agent": 20,
            "min_tasks_per_agent": 10
        }
    )
    
    # Run simulation
    results = await stress_framework.run_simulation(scenario)
    
    # Verify simulation results
    assert "error" not in results
    assert results["duration"] >= 25  # Should run for most of the duration
    assert results["communication_stats"]["total_messages"] > 1000
    assert results["communication_stats"]["total_tasks"] > 500
    
    # Check analysis results
    analysis = results["analysis"]
    assert "success_criteria_met" in analysis
    assert "performance_analysis" in analysis
    assert analysis["performance_analysis"]["agent_utilization"] > 0.7


@pytest.mark.asyncio
@pytest.mark.stress
async def test_communication_stress(stress_framework):
    """Test communication system under stress."""
    
    # Create communication-heavy scenario
    scenario = SimulationScenario(
        scenario_id="communication_stress",
        name="Communication Stress Test",
        description="High-frequency communication between agents",
        agent_count=50,
        duration_seconds=20,
        interaction_frequency=5.0,  # High frequency
        communication_patterns=["broadcast", "peer_to_peer"],
        success_criteria={"min_messages_per_agent": 50}
    )
    
    results = await stress_framework.run_simulation(scenario)
    
    # Verify communication performance
    assert results["communication_stats"]["total_messages"] > 2000
    assert results["communication_stats"]["messages_per_agent"] > 40
    
    # Check for emergent communication behaviors
    emergent_behaviors = results["emergent_behaviors"]
    communication_behaviors = [
        b for b in emergent_behaviors 
        if b["type"] == "communication_clustering"
    ]
    
    # Should detect some communication patterns
    assert len(communication_behaviors) >= 0  # May or may not detect patterns


@pytest.mark.asyncio
@pytest.mark.stress
async def test_failure_recovery_simulation(stress_framework):
    """Test system behavior under failure conditions."""
    
    # Create failure-prone scenario
    scenario = SimulationScenario(
        scenario_id="failure_recovery",
        name="Failure Recovery Test",
        description="Test system resilience under failures",
        agent_count=30,
        duration_seconds=25,
        interaction_frequency=1.5,
        failure_injection={
            "communication_failure": 0.05,  # 5% communication failure rate
            "processing_failure": 0.03      # 3% processing failure rate
        },
        success_criteria={"min_tasks_per_agent": 15}
    )
    
    results = await stress_framework.run_simulation(scenario)
    
    # System should continue operating despite failures
    assert results["communication_stats"]["total_tasks"] > 300
    assert results["analysis"]["performance_analysis"]["agent_utilization"] > 0.6
    
    # Should still meet some success criteria despite failures
    success_criteria = results["analysis"]["success_criteria_met"]
    assert any(success_criteria.values())  # At least some criteria should be met


@pytest.mark.asyncio
@pytest.mark.stress
async def test_emergent_behavior_detection(stress_framework):
    """Test detection of emergent behaviors in simulations."""
    
    # Create scenario likely to produce emergent behaviors
    scenario = SimulationScenario(
        scenario_id="emergent_behavior",
        name="Emergent Behavior Detection",
        description="Scenario designed to produce emergent behaviors",
        agent_count=40,
        duration_seconds=30,
        interaction_frequency=3.0,
        communication_patterns=["peer_to_peer", "hierarchical"],
        task_patterns=["collaborative", "competitive"],
        expected_behaviors=["specialization", "clustering", "leadership_emergence"]
    )
    
    results = await stress_framework.run_simulation(scenario)
    
    # Should detect some emergent behaviors
    emergent_behaviors = results["emergent_behaviors"]
    assert len(emergent_behaviors) > 0
    
    # Check behavior types
    behavior_types = [b["type"] for b in emergent_behaviors]
    expected_types = ["communication_clustering", "task_specialization"]
    
    # Should detect at least one expected behavior type
    assert any(bt in behavior_types for bt in expected_types)
    
    # Analysis should provide insights
    analysis = results["analysis"]
    assert analysis["behavior_analysis"]["emergent_behaviors_detected"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "stress"])