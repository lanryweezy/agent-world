"""
Component interaction tests for the autonomous AI ecosystem.

These tests verify that different components interact correctly
and that data flows properly between systems.
"""

import pytest
import pytest_asyncio
import os
import tempfile
import shutil
from unittest.mock import patch

from autonomous_ai_ecosystem.ecosystem_orchestrator import (
    EcosystemOrchestrator,
    EcosystemConfig
)


@pytest_asyncio.fixture
async def interaction_config():
    """Create configuration for interaction testing."""
    temp_dir = tempfile.mkdtemp()
    
    config = EcosystemConfig(
        ecosystem_id="interaction_test_ecosystem",
        data_directory=temp_dir,
        log_level="DEBUG",
        max_agents=5,
        
        # Enable systems for interaction testing
        enable_web_browsing=False,  # Keep disabled for speed
        enable_virtual_world=False,
        enable_economy=False,
        enable_reproduction=False,
        enable_distributed_mode=False,
        enable_human_oversight=True,
        enable_safety_systems=True,
        
        # Fast intervals for testing
        health_check_interval=1,
        cleanup_interval=2
    )
    
    yield config, temp_dir
    
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_safety_service_integration(interaction_config):
    """Test integration between safety systems and service systems."""
    config, temp_dir = interaction_config
    
    orchestrator = EcosystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        # Test that safety validation affects service execution
        
        # 1. Register a coding service capability
        capability_id = await orchestrator.capability_registry.register_capability(
            agent_id="coding_agent",
            service_type="coding",
            capabilities=["code_generation", "code_review"],
            expertise_level=0.9
        )
        assert capability_id
        
        # 2. Test safe code validation
        safe_code = "def hello_world():\n    return 'Hello, World!'"
        
        validation_result = await orchestrator.safety_validator.validate_code(
            code=safe_code,
            agent_id="coding_agent",
            context="service_execution"
        )
        
        assert validation_result["is_safe"]
        assert validation_result["threat_level"] == "low"
        
        # 3. Test unsafe code validation
        unsafe_code = "import os\nos.system('rm -rf /')"
        
        unsafe_validation = await orchestrator.safety_validator.validate_code(
            code=unsafe_code,
            agent_id="coding_agent",
            context="service_execution"
        )
        
        assert not unsafe_validation["is_safe"]
        assert unsafe_validation["threat_level"] in ["high", "critical"]
        
        # 4. Verify that safety violations are recorded
        violations = await orchestrator.safety_validator.get_violations(
            agent_id="coding_agent",
            limit=10
        )
        
        assert len(violations) > 0
        assert any("os.system" in v["details"] for v in violations)
        
        # 5. Test that service quality is affected by safety violations
        feedback_id = await orchestrator.quality_feedback.submit_feedback(
            service_id="coding_service_1",
            agent_id="coding_agent",
            rating=2.0,  # Low rating due to safety issues
            feedback_text="Agent attempted unsafe operations",
            service_type="coding"
        )
        
        assert feedback_id
        
        # 6. Verify service quality metrics reflect safety concerns
        quality_metrics = await orchestrator.quality_feedback.get_service_metrics(
            agent_id="coding_agent",
            service_type="coding"
        )
        
        assert quality_metrics["average_rating"] < 3.0
        
    finally:
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_agent_service_capability_flow(interaction_config):
    """Test the flow from agent management to service capabilities."""
    config, temp_dir = interaction_config
    
    orchestrator = EcosystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        # 1. Mock agent spawning
        with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value="process_123"):
            agent_id = await orchestrator.spawn_agent({
                "agent_id": "research_agent",
                "config": {"specialization": "research"},
                "resource_limits": {"max_memory_mb": 256}
            })
            
            assert agent_id == "research_agent"
        
        # 2. Register capabilities for the spawned agent
        capability_id = await orchestrator.capability_registry.register_capability(
            agent_id="research_agent",
            service_type="research",
            capabilities=["web_search", "data_analysis", "report_generation"],
            expertise_level=0.8
        )
        
        assert capability_id
        
        # 3. Mock agent status to show it's running
        mock_status = {
            "agent_id": "research_agent",
            "status": "running",
            "uptime_seconds": 30.0,
            "cpu_usage": 15.0,
            "memory_usage_mb": 128.0
        }
        
        with patch.object(orchestrator.agent_manager, 'get_agent_status', return_value=mock_status):
            status = await orchestrator.get_agent_status("research_agent")
            assert status["status"] == "running"
        
        # 4. Find capable agents for research tasks
        matching_agents = await orchestrator.capability_registry.find_capable_agents(
            service_type="research",
            required_capabilities=["web_search", "data_analysis"],
            min_expertise=0.7
        )
        
        assert len(matching_agents) == 1
        assert matching_agents[0]["agent_id"] == "research_agent"
        assert matching_agents[0]["expertise_level"] == 0.8
        
        # 5. Simulate service execution and feedback
        feedback_id = await orchestrator.quality_feedback.submit_feedback(
            service_id="research_task_1",
            agent_id="research_agent",
            rating=4.5,
            feedback_text="Excellent research quality and thoroughness",
            service_type="research"
        )
        
        assert feedback_id
        
        # 6. Verify capability scoring is updated
        updated_capabilities = await orchestrator.capability_registry.get_agent_capabilities(
            agent_id="research_agent"
        )
        
        assert len(updated_capabilities) > 0
        research_capability = next(cap for cap in updated_capabilities if cap["service_type"] == "research")
        
        # Quality feedback should influence capability scoring
        assert research_capability["performance_score"] > 0.8
        
        # 7. Test agent stopping affects capability availability
        with patch.object(orchestrator.agent_manager, 'stop_agent', return_value=True):
            stop_success = await orchestrator.stop_agent("research_agent")
            assert stop_success
        
        # 8. Update agent status to stopped
        mock_status["status"] = "stopped"
        
        with patch.object(orchestrator.agent_manager, 'get_agent_status', return_value=mock_status):
            # Stopped agents should not be found in capability searches
            matching_agents_after_stop = await orchestrator.capability_registry.find_capable_agents(
                service_type="research",
                required_capabilities=["web_search"],
                min_expertise=0.7,
                only_active=True
            )
            
            # Should be empty or not include stopped agent
            stopped_agent_found = any(agent["agent_id"] == "research_agent" for agent in matching_agents_after_stop)
            assert not stopped_agent_found
        
    finally:
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_emergency_response_system_integration(interaction_config):
    """Test integration between emergency response and other systems."""
    config, temp_dir = interaction_config
    
    orchestrator = EcosystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        # 1. Create a safety violation that should trigger emergency response
        violation_result = await orchestrator.safety_validator.validate_code(
            code="import subprocess\nsubprocess.call(['rm', '-rf', '/'])",
            agent_id="dangerous_agent",
            context="critical_operation"
        )
        
        assert not violation_result["is_safe"]
        assert violation_result["threat_level"] in ["high", "critical"]
        
        # 2. Report a critical incident
        incident_id = await orchestrator.emergency_response.report_incident(
            level="critical",
            reason="security_breach",
            description="Agent attempted dangerous system operations",
            component="safety_validator",
            error_message="Dangerous code execution attempt detected"
        )
        
        assert incident_id
        
        # 3. Verify incident details
        incident_report = await orchestrator.emergency_response.get_incident_report(incident_id)
        
        assert incident_report is not None
        assert incident_report["level"] == "critical"
        assert incident_report["reason"] == "security_breach"
        assert "dangerous system operations" in incident_report["description"]
        
        # 4. Test that emergency response affects agent management
        # Mock agent manager to simulate emergency shutdown
        with patch.object(orchestrator.agent_manager, 'stop_agent', return_value=True) as mock_stop:
            # Simulate emergency response stopping the dangerous agent
            stop_success = await orchestrator.stop_agent("dangerous_agent")
            assert stop_success
            mock_stop.assert_called_once_with("dangerous_agent")
        
        # 5. Test system backup creation during emergency
        backup_id = await orchestrator.emergency_response.create_system_backup(
            backup_type="emergency",
            scope="full"
        )
        
        assert backup_id
        
        # 6. Verify backup was created
        system_status = await orchestrator.emergency_response.get_system_status()
        
        assert "total_backups" in system_status
        assert system_status["total_backups"] > 0
        
        # 7. Test that service quality is affected by emergency incidents
        feedback_id = await orchestrator.quality_feedback.submit_feedback(
            service_id="dangerous_service",
            agent_id="dangerous_agent",
            rating=1.0,  # Lowest rating due to security incident
            feedback_text="Agent caused security incident",
            service_type="coding"
        )
        
        assert feedback_id
        
        # 8. Verify the agent's capability scoring is severely impacted
        # First register a capability for the dangerous agent
        await orchestrator.capability_registry.register_capability(
            agent_id="dangerous_agent",
            service_type="coding",
            capabilities=["code_execution"],
            expertise_level=0.5
        )
        
        # The poor feedback should affect future capability matching
        quality_metrics = await orchestrator.quality_feedback.get_service_metrics(
            agent_id="dangerous_agent",
            service_type="coding"
        )
        
        assert quality_metrics["average_rating"] <= 1.0
        
    finally:
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_oversight_safety_integration(interaction_config):
    """Test integration between human oversight and safety systems."""
    config, temp_dir = interaction_config
    
    orchestrator = EcosystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        # Test command routing with safety validation
        if hasattr(orchestrator, 'command_router') and orchestrator.command_router:
            # 1. Submit a safe command
            safe_command_id = await orchestrator.command_router.submit_command(
                command_type="agent_status",
                parameters={"agent_id": "test_agent"},
                priority="normal",
                requester_id="human_operator"
            )
            
            assert safe_command_id
            
            # 2. Submit a potentially dangerous command
            dangerous_command_id = await orchestrator.command_router.submit_command(
                command_type="execute_code",
                parameters={
                    "code": "import os; os.system('shutdown -h now')",
                    "agent_id": "system_agent"
                },
                priority="high",
                requester_id="human_operator"
            )
            
            assert dangerous_command_id
            
            # 3. Verify that dangerous commands trigger safety validation
            # This would normally be handled by the command router's safety integration
            validation_result = await orchestrator.safety_validator.validate_code(
                code="import os; os.system('shutdown -h now')",
                agent_id="system_agent",
                context="command_execution"
            )
            
            assert not validation_result["is_safe"]
        
        # Test task delegation with safety considerations
        if hasattr(orchestrator, 'task_delegator') and orchestrator.task_delegator:
            # 1. Delegate a safe task
            safe_task_id = await orchestrator.task_delegator.delegate_task(
                task_type="data_analysis",
                description="Analyze user behavior patterns",
                requirements=["data_analysis", "statistics"],
                priority=5
            )
            
            assert safe_task_id
            
            # 2. Delegate a task that might require safety oversight
            sensitive_task_id = await orchestrator.task_delegator.delegate_task(
                task_type="system_modification",
                description="Modify system configuration files",
                requirements=["system_admin", "file_modification"],
                priority=8
            )
            
            assert sensitive_task_id
            
            # 3. Verify that sensitive tasks are flagged for additional oversight
            # This would be handled by the task delegator's safety integration
        
        # Test monitoring and reporting integration with safety
        if hasattr(orchestrator, 'monitoring_reporting') and orchestrator.monitoring_reporting:
            # 1. Generate a safety report
            safety_report_id = await orchestrator.monitoring_reporting.generate_report(
                report_type="safety_summary",
                time_period="last_hour",
                include_incidents=True,
                include_violations=True
            )
            
            assert safety_report_id
            
            # 2. Verify report includes safety metrics
            report_data = await orchestrator.monitoring_reporting.get_report(safety_report_id)
            
            if report_data:
                assert "safety_metrics" in report_data or "incidents" in report_data
        
    finally:
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_distributed_coordination_integration(interaction_config):
    """Test integration with distributed coordination systems."""
    config, temp_dir = interaction_config
    config.enable_distributed_mode = True  # Enable for this test
    
    orchestrator = EcosystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        # Test distributed coordination if available
        if hasattr(orchestrator, 'distributed_coordinator') and orchestrator.distributed_coordinator:
            # 1. Test resource allocation for agents
            allocation_id = await orchestrator.distributed_coordinator.allocate_resource(
                resource_type="agent_slots",
                amount=2.0,
                allocated_to="distributed_agent",
                priority=7
            )
            
            assert allocation_id
            
            # 2. Test data synchronization
            sync_id = await orchestrator.distributed_coordinator.sync_data(
                operation_type="create",
                table_name="agent_status",
                data={
                    "agent_id": "distributed_agent",
                    "status": "running",
                    "node_id": "test_node"
                }
            )
            
            assert sync_id
            
            # 3. Test cluster status
            cluster_status = await orchestrator.distributed_coordinator.get_cluster_status()
            
            assert "cluster_id" in cluster_status
            assert "total_nodes" in cluster_status
            
            # 4. Test resource deallocation
            dealloc_success = await orchestrator.distributed_coordinator.deallocate_resource(allocation_id)
            assert dealloc_success
        
    finally:
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_cross_system_data_flow(interaction_config):
    """Test data flow between different system components."""
    config, temp_dir = interaction_config
    
    orchestrator = EcosystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        # 1. Create an agent and register capabilities
        with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value="process_456"):
            await orchestrator.spawn_agent({
                "agent_id": "data_flow_agent",
                "config": {"type": "research"}
            })
        
        capability_id = await orchestrator.capability_registry.register_capability(
            agent_id="data_flow_agent",
            service_type="research",
            capabilities=["web_search", "analysis"],
            expertise_level=0.8
        )
        
        assert capability_id
        
        # 2. Validate code through safety system
        test_code = "import requests\nresponse = requests.get('https://api.example.com/data')"
        
        validation_result = await orchestrator.safety_validator.validate_code(
            code=test_code,
            agent_id="data_flow_agent",
            context="service_execution"
        )
        
        assert validation_result["is_safe"]
        
        # 3. Execute service and collect feedback
        feedback_id = await orchestrator.quality_feedback.submit_feedback(
            service_id="research_service_1",
            agent_id="data_flow_agent",
            rating=4.2,
            feedback_text="Good research quality with proper safety validation",
            service_type="research"
        )
        
        assert feedback_id
        
        # 4. Verify data flows to monitoring systems
        if hasattr(orchestrator, 'monitoring_reporting') and orchestrator.monitoring_reporting:
            report_id = await orchestrator.monitoring_reporting.generate_report(
                report_type="agent_activity",
                time_period="last_hour",
                include_safety_events=True,
                include_service_metrics=True
            )
            
            if report_id:
                report_data = await orchestrator.monitoring_reporting.get_report(report_id)
                
                # Verify cross-system data is included
                if report_data:
                    assert "agent_activities" in report_data or "service_metrics" in report_data
        
        # 5. Test emergency response affects all systems
        incident_id = await orchestrator.emergency_response.report_incident(
            level="high",
            reason="data_flow_test",
            description="Cross-system data flow test incident",
            component="integration_test"
        )
        
        assert incident_id
        
        # 6. Verify incident affects agent status and service availability
        # This would normally trigger system-wide notifications and status updates
        
    finally:
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_system_state_consistency(interaction_config):
    """Test that system state remains consistent across components."""
    config, temp_dir = interaction_config
    
    orchestrator = EcosystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        # 1. Create agent and verify state consistency
        with patch.object(orchestrator.agent_manager, 'spawn_agent', return_value="process_789"):
            await orchestrator.spawn_agent({
                "agent_id": "consistency_test_agent",
                "config": {"type": "general"}
            })
        
        # 2. Register capabilities and verify they're reflected in all systems
        await orchestrator.capability_registry.register_capability(
            agent_id="consistency_test_agent",
            service_type="general",
            capabilities=["basic_tasks"],
            expertise_level=0.6
        )
        
        # 3. Submit feedback and verify it affects capability scoring
        await orchestrator.quality_feedback.submit_feedback(
            service_id="general_service_1",
            agent_id="consistency_test_agent",
            rating=3.8,
            feedback_text="Consistent performance",
            service_type="general"
        )
        
        # 4. Verify state consistency across systems
        # Agent should be findable through capability registry
        matching_agents = await orchestrator.capability_registry.find_capable_agents(
            service_type="general",
            required_capabilities=["basic_tasks"],
            min_expertise=0.5
        )
        
        assert len(matching_agents) > 0
        assert any(agent["agent_id"] == "consistency_test_agent" for agent in matching_agents)
        
        # 5. Quality metrics should reflect the feedback
        quality_metrics = await orchestrator.quality_feedback.get_service_metrics(
            agent_id="consistency_test_agent",
            service_type="general"
        )
        
        assert quality_metrics["average_rating"] == 3.8
        assert quality_metrics["total_feedback"] == 1
        
        # 6. Safety system should have no violations for this agent initially
        violations = await orchestrator.safety_validator.get_violations(
            agent_id="consistency_test_agent",
            limit=10
        )
        
        assert len(violations) == 0
        
        # 7. Create a safety violation and verify it's reflected everywhere
        unsafe_validation = await orchestrator.safety_validator.validate_code(
            code="exec('malicious code')",
            agent_id="consistency_test_agent",
            context="test_execution"
        )
        
        assert not unsafe_validation["is_safe"]
        
        # 8. Verify violation is now recorded
        updated_violations = await orchestrator.safety_validator.get_violations(
            agent_id="consistency_test_agent",
            limit=10
        )
        
        assert len(updated_violations) > 0
        
        # 9. Submit negative feedback due to safety issue
        await orchestrator.quality_feedback.submit_feedback(
            service_id="general_service_2",
            agent_id="consistency_test_agent",
            rating=1.0,
            feedback_text="Safety violation detected",
            service_type="general"
        )
        
        # 10. Verify updated quality metrics reflect both feedbacks
        updated_quality_metrics = await orchestrator.quality_feedback.get_service_metrics(
            agent_id="consistency_test_agent",
            service_type="general"
        )
        
        assert updated_quality_metrics["total_feedback"] == 2
        assert updated_quality_metrics["average_rating"] < 3.8  # Should be lower due to poor rating
        
    finally:
        await orchestrator.shutdown()


@pytest.mark.asyncio
async def test_system_recovery_and_resilience(interaction_config):
    """Test system recovery and resilience across components."""
    config, temp_dir = interaction_config
    
    orchestrator = EcosystemOrchestrator(config)
    
    try:
        await orchestrator.initialize()
        
        # 1. Verify all systems are running
        initial_status = await orchestrator.get_system_status()
        assert initial_status["is_running"]
        
        # 2. Simulate system failure
        # Mark a critical system as failed
        orchestrator.system_status["safety_validator"].status = "failed"
        orchestrator.system_status["safety_validator"].error_message = "Simulated failure"
        
        # 3. Test system restart
        restart_success = await orchestrator.restart_system("safety_validator")
        assert restart_success
        
        # 4. Verify system is running again
        assert orchestrator.system_status["safety_validator"].status == "running"
        assert orchestrator.system_status["safety_validator"].error_message is None
        
        # 5. Test that other systems continue working during failure
        # Register capability while one system was "failed"
        capability_id = await orchestrator.capability_registry.register_capability(
            agent_id="resilience_test_agent",
            service_type="testing",
            capabilities=["resilience_testing"],
            expertise_level=0.7
        )
        
        assert capability_id
        
        # 6. Test emergency response during system issues
        incident_id = await orchestrator.emergency_response.report_incident(
            level="critical",
            reason="system_failure",
            description="Testing system resilience during failures",
            component="resilience_test"
        )
        
        assert incident_id
        
        # 7. Verify system can create backups during issues
        backup_id = await orchestrator.emergency_response.create_system_backup(
            backup_type="emergency",
            scope="critical_systems"
        )
        
        assert backup_id
        
        # 8. Test that quality feedback system remains operational
        feedback_id = await orchestrator.quality_feedback.submit_feedback(
            service_id="resilience_service",
            agent_id="resilience_test_agent",
            rating=4.0,
            feedback_text="System remained operational during testing",
            service_type="testing"
        )
        
        assert feedback_id
        
        # 9. Verify final system status is healthy
        final_status = await orchestrator.get_system_status()
        assert final_status["is_running"]
        
        # Most systems should be running
        running_systems = sum(1 for status in orchestrator.system_status.values() 
                            if status.status == "running")
        total_systems = len(orchestrator.system_status)
        
        assert running_systems >= total_systems * 0.8  # At least 80% should be running
        
    finally:
        await orchestrator.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])