"""
Large-scale simulation tests for the autonomous AI ecosystem.

These tests simulate realistic scenarios with multiple agents
and verify emergent behaviors and system scalability.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import tempfile
import shutil
import time
import random
from unittest.mock import patch
from typing import List, Dict, Any

from autonomous_ai_ecosystem.ecosystem_orchestrator import (
    EcosystemOrchestrator,
    EcosystemConfig
)


@pytest_asyncio.fixture
async def simulation_config():
    """Create configuration for large-scale simulation testing."""
    temp_dir = tempfile.mkdtemp()
    
    config = EcosystemConfig(
        ecosystem_id="simulation_test_ecosystem",
        data_directory=temp_dir,
        log_level="WARNING",  # Reduce logging for performance
        max_agents=50,
        
        # Enable systems for realistic simulation
        enable_web_browsing=False,  # Keep disabled for speed
        enable_virtual_world=True,
        enable_economy=True,
        enable_reproduction=True,
        enable_distributed_mode=True,
        enable_human_oversight=True,
        enable_safety_systems=True,
        
        # Reasonable intervals for simulation
        health_check_interval=2,
        cleanup_interval=5
    )
    
    yield config, temp_dir
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


class SimulationMetrics:
    """Helper class to collect and analyze simulation metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.agent_spawns = 0
        self.agent_deaths = 0
        self.service_executions = 0
        self.safety_violations = 0
        self.emergency_incidents = 0
        self.economic_transactions = 0
        self.social_interactions = 0
        self.reproduction_events = 0
        self.world_modifications = 0
        
        self.agent_lifespans = []
        self.service_ratings = []
        self.system_errors = []
        
    def record_agent_spawn(self, agent_id: str):
        """Record agent spawning event."""
        self.agent_spawns += 1
        
    def record_agent_death(self, agent_id: str, lifespan_seconds: float):
        """Record agent death event."""
        self.agent_deaths += 1
        self.agent_lifespans.append(lifespan_seconds)
        
    def record_service_execution(self, rating: float):
        """Record service execution and rating."""
        self.service_executions += 1
        self.service_ratings.append(rating)
        
    def record_safety_violation(self, severity: str):
        """Record safety violation."""
        self.safety_violations += 1
        
    def record_emergency_incident(self, level: str):
        """Record emergency incident."""
        self.emergency_incidents += 1
        
    def record_economic_transaction(self, amount: float):
        """Record economic transaction."""
        self.economic_transactions += 1
        
    def record_social_interaction(self, interaction_type: str):
        """Record social interaction."""
        self.social_interactions += 1
        
    def record_reproduction_event(self, parent_ids: List[str]):
        """Record reproduction event."""
        self.reproduction_events += 1
        
    def record_world_modification(self, modification_type: str):
        """Record world modification."""
        self.world_modifications += 1
        
    def record_system_error(self, error_type: str, details: str):
        """Record system error."""
        self.system_errors.append({
            "type": error_type,
            "details": details,
            "timestamp": time.time()
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Get simulation summary metrics."""
        duration = time.time() - self.start_time
        
        return {
            "duration_seconds": duration,
            "agent_spawns": self.agent_spawns,
            "agent_deaths": self.agent_deaths,
            "net_agent_growth": self.agent_spawns - self.agent_deaths,
            "service_executions": self.service_executions,
            "average_service_rating": sum(self.service_ratings) / len(self.service_ratings) if self.service_ratings else 0,
            "safety_violations": self.safety_violations,
            "emergency_incidents": self.emergency_incidents,
            "economic_transactions": self.economic_transactions,
            "social_interactions": self.social_interactions,
            "reproduction_events": self.reproduction_events,
            "world_modifications": self.world_modifications,
            "average_agent_lifespan": sum(self.agent_lifespans) / len(self.agent_lifespans) if self.agent_lifespans else 0,
            "system_errors": len(self.system_errors),
            "events_per_second": (
                self.agent_spawns + self.service_executions + self.social_interactions + 
                self.economic_transactions + self.reproduction_events + self.world_modifications
            ) / duration if duration > 0 else 0
        }


@pytest.mark.asyncio
async def test_multi_agent_ecosystem_simulation(simulation_config):
    """Test large-scale multi-agent ecosystem simulation."""
    config, temp_dir = simulation_config
    
    orchestrator = EcosystemOrchestrator(config)
    metrics = SimulationMetrics()
    
    try:
        await orchestrator.initialize()
        
        # Simulate spawning multiple agents with different specializations
        agent_types = ["research", "coding", "creative", "analysis", "monitoring"]
        spawned_agents = []
        
        # Phase 1: Initial agent population
        for i in range(10):
            agent_type = random.choice(agent_types)
            agent_id = f"sim_agent_{i}_{agent_type}"
            
            with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value=f"process_{i}"):
                spawned_agent_id = await orchestrator.spawn_agent({
                    "agent_id": agent_id,
                    "config": {
                        "specialization": agent_type,
                        "personality_traits": {
                            "curiosity": random.uniform(0.3, 1.0),
                            "sociability": random.uniform(0.2, 0.9),
                            "creativity": random.uniform(0.1, 0.8)
                        }
                    },
                    "resource_limits": {"max_memory_mb": random.randint(128, 512)}
                })
                
                spawned_agents.append(spawned_agent_id)
                metrics.record_agent_spawn(spawned_agent_id)
        
        # Register capabilities for spawned agents
        for agent_id in spawned_agents:
            agent_type = agent_id.split("_")[2]
            
            if agent_type == "research":
                capabilities = ["web_search", "data_analysis", "report_generation"]
            elif agent_type == "coding":
                capabilities = ["code_generation", "debugging", "code_review"]
            elif agent_type == "creative":
                capabilities = ["content_creation", "design", "storytelling"]
            elif agent_type == "analysis":
                capabilities = ["data_analysis", "statistics", "visualization"]
            else:  # monitoring
                capabilities = ["system_monitoring", "alerting", "performance_analysis"]
            
            capability_id = await orchestrator.capability_registry.register_capability(
                agent_id=agent_id,
                service_type=agent_type,
                capabilities=capabilities,
                expertise_level=random.uniform(0.5, 0.9)
            )
            
            assert capability_id
        
        # Phase 2: Simulate service interactions
        for _ in range(30):
            # Random service requests
            service_type = random.choice(agent_types)
            
            # Find capable agents
            matching_agents = await orchestrator.capability_registry.find_capable_agents(
                service_type=service_type,
                required_capabilities=[],
                min_expertise=0.4
            )
            
            if matching_agents:
                selected_agent = random.choice(matching_agents)
                
                # Simulate service execution with random outcome
                rating = random.uniform(2.0, 5.0)
                
                await orchestrator.quality_feedback.submit_feedback(
                    service_id=f"sim_service_{_}",
                    agent_id=selected_agent["agent_id"],
                    rating=rating,
                    feedback_text=f"Simulated service execution {_}",
                    service_type=service_type
                )
                
                metrics.record_service_execution(rating)
                
                # Occasionally simulate safety violations
                if random.random() < 0.1:  # 10% chance
                    violation_result = await orchestrator.safety_validator.validate_code(
                        code="import os; os.listdir('/')",  # Mild violation
                        agent_id=selected_agent["agent_id"],
                        context="service_execution"
                    )
                    
                    if not violation_result["is_safe"]:
                        metrics.record_safety_violation(violation_result["threat_level"])
        
        # Phase 3: Simulate economic transactions (if economy is enabled)
        if hasattr(orchestrator, 'marketplace') and orchestrator.marketplace:
            for _ in range(15):
                buyer_agent = random.choice(spawned_agents)
                seller_agent = random.choice([a for a in spawned_agents if a != buyer_agent])
                
                # Simulate service purchase
                transaction_id = await orchestrator.marketplace.create_transaction(
                    buyer_id=buyer_agent,
                    seller_id=seller_agent,
                    service_type=random.choice(agent_types),
                    amount=random.uniform(10.0, 100.0),
                    description=f"Simulated transaction {_}"
                )
                
                if transaction_id:
                    metrics.record_economic_transaction(random.uniform(10.0, 100.0))
        
        # Phase 4: Simulate social interactions and reproduction
        for _ in range(20):
            agent1 = random.choice(spawned_agents)
            agent2 = random.choice([a for a in spawned_agents if a != agent1])
            
            # Simulate social interaction
            metrics.record_social_interaction("collaboration")
            
            # Occasionally simulate reproduction (if enabled)
            if random.random() < 0.2 and hasattr(orchestrator, 'reproduction_manager'):  # 20% chance
                # Mock reproduction attempt
                compatibility_score = random.uniform(0.3, 0.9)
                
                if compatibility_score > 0.6:
                    # Simulate successful reproduction
                    child_id = f"child_{agent1}_{agent2}_{_}"
                    
                    with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value=f"child_process_{_}"):
                        child_agent_id = await orchestrator.spawn_agent({
                            "agent_id": child_id,
                            "config": {
                                "parents": [agent1, agent2],
                                "inherited_traits": True
                            }
                        })
                        
                        spawned_agents.append(child_agent_id)
                        metrics.record_agent_spawn(child_agent_id)
                        metrics.record_reproduction_event([agent1, agent2])
        
        # Phase 5: Simulate world building (if virtual world is enabled)
        if hasattr(orchestrator, 'virtual_world') and orchestrator.virtual_world:
            for _ in range(10):
                builder_agent = random.choice(spawned_agents)
                
                # Simulate world modification
                modification_id = await orchestrator.virtual_world.create_location(
                    name=f"sim_location_{_}",
                    coordinates=(random.uniform(-100, 100), random.uniform(-100, 100)),
                    created_by=builder_agent,
                    resources={"energy": random.randint(50, 200)}
                )
                
                if modification_id:
                    metrics.record_world_modification("location_creation")
        
        # Phase 6: Simulate some system stress and failures
        for _ in range(5):
            # Simulate emergency incidents
            incident_id = await orchestrator.emergency_response.report_incident(
                level=random.choice(["low", "medium", "high"]),
                reason="simulation_stress",
                description=f"Simulated stress incident {_}",
                component="simulation_test"
            )
            
            if incident_id:
                metrics.record_emergency_incident("simulation")
        
        # Let the simulation run for a bit
        await asyncio.sleep(5)
        
        # Phase 7: Analyze results
        summary = metrics.get_summary()
        
        # Verify simulation produced realistic results
        assert summary["agent_spawns"] >= 10, "Should have spawned initial agents"
        assert summary["service_executions"] >= 20, "Should have executed services"
        assert summary["events_per_second"] > 0, "Should have activity throughout simulation"
        
        # System should remain stable
        system_status = await orchestrator.get_system_status()
        assert system_status["is_running"], "System should remain running during simulation"
        
        # Print simulation results
        print("\nSimulation Results:")
        print(f"  Duration: {summary['duration_seconds']:.1f}s")
        print(f"  Agents spawned: {summary['agent_spawns']}")
        print(f"  Service executions: {summary['service_executions']}")
        print(f"  Average service rating: {summary['average_service_rating']:.2f}")
        print(f"  Safety violations: {summary['safety_violations']}")
        print(f"  Emergency incidents: {summary['emergency_incidents']}")
        print(f"  Economic transactions: {summary['economic_transactions']}")
        print(f"  Social interactions: {summary['social_interactions']}")
        print(f"  Reproduction events: {summary['reproduction_events']}")
        print(f"  World modifications: {summary['world_modifications']}")
        print(f"  Events per second: {summary['events_per_second']:.2f}")
        print(f"  System errors: {summary['system_errors']}")
        
        # Verify no excessive system errors
        assert summary["system_errors"] < 5, f"Too many system errors: {summary['system_errors']}"
        
    finally:
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_emergent_behavior_simulation(simulation_config):
    """Test simulation of emergent behaviors in agent ecosystem."""
    config, temp_dir = simulation_config
    config.max_agents = 20  # Smaller scale for focused testing
    
    orchestrator = EcosystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        # Create agents with different personality profiles
        personality_profiles = [
            {"curiosity": 0.9, "sociability": 0.8, "creativity": 0.7},  # Explorer
            {"curiosity": 0.3, "sociability": 0.9, "creativity": 0.4},  # Social
            {"curiosity": 0.7, "sociability": 0.3, "creativity": 0.9},  # Creative
            {"curiosity": 0.5, "sociability": 0.5, "creativity": 0.5},  # Balanced
        ]
        
        agents_by_type = {}
        
        for i, profile in enumerate(personality_profiles * 3):  # 12 agents total
            agent_id = f"emergent_agent_{i}"
            agent_type = ["explorer", "social", "creative", "balanced"][i % 4]
            
            with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value=f"emergent_process_{i}"):
                spawned_agent_id = await orchestrator.spawn_agent({
                    "agent_id": agent_id,
                    "config": {
                        "personality_traits": profile,
                        "agent_type": agent_type
                    }
                })
                
                if agent_type not in agents_by_type:
                    agents_by_type[agent_type] = []
                agents_by_type[agent_type].append(spawned_agent_id)
        
        # Register different capabilities based on personality
        for agent_type, agent_list in agents_by_type.items():
            for agent_id in agent_list:
                if agent_type == "explorer":
                    capabilities = ["research", "exploration", "discovery"]
                elif agent_type == "social":
                    capabilities = ["communication", "coordination", "mediation"]
                elif agent_type == "creative":
                    capabilities = ["content_creation", "problem_solving", "innovation"]
                else:  # balanced
                    capabilities = ["general_tasks", "adaptation", "support"]
                
                await orchestrator.capability_registry.register_capability(
                    agent_id=agent_id,
                    service_type=agent_type,
                    capabilities=capabilities,
                    expertise_level=random.uniform(0.6, 0.9)
                )
        
        # Simulate interactions that should lead to emergent behaviors
        interaction_patterns = {}
        
        # Phase 1: Random interactions to establish baseline
        for _ in range(50):
            agent1 = random.choice(list(agents_by_type.values())[0] + 
                                 list(agents_by_type.values())[1] + 
                                 list(agents_by_type.values())[2] + 
                                 list(agents_by_type.values())[3])
            agent2 = random.choice([a for agents in agents_by_type.values() for a in agents if a != agent1])
            
            # Record interaction pattern
            pair = tuple(sorted([agent1, agent2]))
            interaction_patterns[pair] = interaction_patterns.get(pair, 0) + 1
            
            # Simulate service request between agents
            service_type = random.choice(["explorer", "social", "creative", "balanced"])
            
            matching_agents = await orchestrator.capability_registry.find_capable_agents(
                service_type=service_type,
                required_capabilities=[],
                min_expertise=0.5
            )
            
            if matching_agents:
                selected_agent = random.choice(matching_agents)
                
                await orchestrator.quality_feedback.submit_feedback(
                    service_id=f"emergent_service_{_}",
                    agent_id=selected_agent["agent_id"],
                    rating=random.uniform(3.0, 5.0),
                    feedback_text="Emergent behavior simulation",
                    service_type=service_type
                )
        
        # Phase 2: Analyze emergent patterns
        # Check if certain agent types tend to work together more
        explorer_interactions = sum(1 for (a1, a2), count in interaction_patterns.items() 
                                  if any(a1.endswith(f"_{i}") or a2.endswith(f"_{i}") 
                                        for i in [0, 4, 8]))  # Explorer agents
        
        social_interactions = sum(1 for (a1, a2), count in interaction_patterns.items() 
                                if any(a1.endswith(f"_{i}") or a2.endswith(f"_{i}") 
                                      for i in [1, 5, 9]))  # Social agents
        
        # Phase 3: Test specialization emergence
        # Agents should develop preferences for certain types of work
        service_preferences = {}
        
        for agent_type, agent_list in agents_by_type.items():
            for agent_id in agent_list:
                quality_metrics = await orchestrator.quality_feedback.get_service_metrics(
                    agent_id=agent_id,
                    service_type=agent_type
                )
                
                service_preferences[agent_id] = quality_metrics.get("average_rating", 0)
        
        # Phase 4: Test collaborative behavior emergence
        # Simulate complex tasks requiring multiple agents
        for _ in range(10):
            # Create a "complex task" requiring multiple specializations
            required_types = random.sample(["explorer", "social", "creative", "balanced"], 2)
            
            task_agents = []
            for req_type in required_types:
                matching_agents = await orchestrator.capability_registry.find_capable_agents(
                    service_type=req_type,
                    required_capabilities=[],
                    min_expertise=0.6
                )
                
                if matching_agents:
                    task_agents.append(random.choice(matching_agents)["agent_id"])
            
            # Simulate collaborative task execution
            if len(task_agents) >= 2:
                for agent_id in task_agents:
                    await orchestrator.quality_feedback.submit_feedback(
                        service_id=f"collaborative_task_{_}",
                        agent_id=agent_id,
                        rating=random.uniform(3.5, 5.0),  # Collaborative tasks tend to be rated higher
                        feedback_text="Collaborative task execution",
                        service_type="collaboration"
                    )
        
        # Let the system run to allow patterns to emerge
        await asyncio.sleep(3)
        
        # Analyze emergent behaviors
        system_status = await orchestrator.get_system_status()
        assert system_status["is_running"]
        
        # Verify that different agent types show different interaction patterns
        assert len(interaction_patterns) > 10, "Should have diverse interaction patterns"
        
        # Verify that agents develop service preferences
        preference_variance = max(service_preferences.values()) - min(service_preferences.values()) if service_preferences else 0
        assert preference_variance > 0.5, "Agents should develop different service preferences"
        
        print("\nEmergent Behavior Analysis:")
        print(f"  Unique interaction pairs: {len(interaction_patterns)}")
        print(f"  Explorer-involved interactions: {explorer_interactions}")
        print(f"  Social-involved interactions: {social_interactions}")
        print(f"  Service preference variance: {preference_variance:.2f}")
        print(f"  Agent types: {list(agents_by_type.keys())}")
        print(f"  Agents per type: {[len(agents) for agents in agents_by_type.values()]}")
        
    finally:
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_system_scalability_limits(simulation_config):
    """Test system behavior at scalability limits."""
    config, temp_dir = simulation_config
    config.max_agents = 100  # Test higher limits
    
    orchestrator = EcosystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        # Test gradual scaling
        scale_levels = [10, 25, 50, 75]
        performance_metrics = {}
        
        for scale in scale_levels:
            start_time = time.time()
            
            # Spawn agents up to current scale level
            current_agents = []
            for i in range(scale):
                agent_id = f"scale_agent_{i}"
                
                with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value=f"scale_process_{i}"):
                    spawned_agent_id = await orchestrator.spawn_agent({
                        "agent_id": agent_id,
                        "config": {"scale_test": True}
                    })
                    
                    current_agents.append(spawned_agent_id)
                
                # Register capabilities
                await orchestrator.capability_registry.register_capability(
                    agent_id=agent_id,
                    service_type="general",
                    capabilities=["basic_tasks"],
                    expertise_level=0.7
                )
            
            # Test system responsiveness at this scale
            response_times = []
            for _ in range(10):
                start_response = time.time()
                status = await orchestrator.get_system_status()
                response_time = time.time() - start_response
                response_times.append(response_time)
                
                assert status["is_running"], f"System should remain responsive at scale {scale}"
            
            # Test service discovery performance
            discovery_times = []
            for _ in range(5):
                start_discovery = time.time()
                matching_agents = await orchestrator.capability_registry.find_capable_agents(
                    service_type="general",
                    required_capabilities=["basic_tasks"],
                    min_expertise=0.5
                )
                discovery_time = time.time() - start_discovery
                discovery_times.append(discovery_time)
                
                assert len(matching_agents) == scale, f"Should find all {scale} agents"
            
            scale_time = time.time() - start_time
            
            performance_metrics[scale] = {
                "setup_time": scale_time,
                "avg_response_time": sum(response_times) / len(response_times),
                "max_response_time": max(response_times),
                "avg_discovery_time": sum(discovery_times) / len(discovery_times),
                "max_discovery_time": max(discovery_times)
            }
            
            print(f"Scale {scale} agents:")
            print(f"  Setup time: {scale_time:.2f}s")
            print(f"  Avg response time: {performance_metrics[scale]['avg_response_time']*1000:.1f}ms")
            print(f"  Avg discovery time: {performance_metrics[scale]['avg_discovery_time']*1000:.1f}ms")
        
        # Analyze scalability trends
        response_time_growth = (
            performance_metrics[75]["avg_response_time"] / 
            performance_metrics[10]["avg_response_time"]
        )
        
        discovery_time_growth = (
            performance_metrics[75]["avg_discovery_time"] / 
            performance_metrics[10]["avg_discovery_time"]
        )
        
        # Performance should not degrade exponentially
        assert response_time_growth < 10, f"Response time growth too high: {response_time_growth:.2f}x"
        assert discovery_time_growth < 20, f"Discovery time growth too high: {discovery_time_growth:.2f}x"
        
        # System should remain responsive even at high scale
        assert performance_metrics[75]["max_response_time"] < 2.0, "Max response time should be < 2s"
        assert performance_metrics[75]["max_discovery_time"] < 5.0, "Max discovery time should be < 5s"
        
        print("\nScalability Analysis:")
        print(f"  Response time growth (10→75 agents): {response_time_growth:.2f}x")
        print(f"  Discovery time growth (10→75 agents): {discovery_time_growth:.2f}x")
        
    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])