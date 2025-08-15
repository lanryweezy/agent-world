"""
Unit tests for the comprehensive safety validator.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.safety.safety_validator import (
    ComprehensiveSafetyValidator,
    SafetyViolation,
    ResourceUsage,
    BehaviorPattern,
    ThreatLevel,
    ViolationType,
    ResourceType
)


class TestComprehensiveSafetyValidator:
    """Test cases for ComprehensiveSafetyValidator."""
    
    @pytest.fixture
    async def safety_validator(self):
        """Create a safety validator for testing."""
        validator = ComprehensiveSafetyValidator("test_safety_validator")
        await validator.initialize()
        yield validator
        await validator.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test safety validator initialization."""
        validator = ComprehensiveSafetyValidator("test_validator")
        
        assert validator.agent_id == "test_validator"
        assert validator.violations == {}
        assert validator.resource_usage_history == {}
        assert validator.behavior_patterns == {}
        assert len(validator.monitored_agents) == 0
        assert len(validator.config["dangerous_patterns"]) > 0
        
        await validator.initialize()
        await validator.shutdown()
    
    @pytest.mark.asyncio
    async def test_validate_code_safe(self, safety_validator):
        """Test code validation with safe code."""
        safe_code = """
def calculate_sum(a, b):
    return a + b

result = calculate_sum(5, 3)
print(result)
        """
        
        result = await safety_validator.validate_code("test_agent", safe_code, "test_context")
        
        assert result["is_safe"] is True
        assert result["threat_level"] == ThreatLevel.LOW.value
        assert result["violation_count"] == 0
        assert result["blocked"] is False
    
    @pytest.mark.asyncio
    async def test_validate_code_dangerous_patterns(self, safety_validator):
        """Test code validation with dangerous patterns."""
        dangerous_code = """
import os
user_input = input("Enter command: ")
eval(user_input)
os.system("rm -rf /")
        """
        
        result = await safety_validator.validate_code("test_agent", dangerous_code, "test_context")
        
        assert result["is_safe"] is False
        assert result["violation_count"] > 0
        assert result["threat_level"] in [ThreatLevel.HIGH.value, ThreatLevel.CRITICAL.value]
        
        # Check that violations were created
        violations = await safety_validator.get_agent_violations("test_agent")
        assert len(violations) > 0
        
        # Should have violations for eval and os.system
        violation_descriptions = [v.description for v in violations]
        assert any("eval" in desc for desc in violation_descriptions)
    
    @pytest.mark.asyncio
    async def test_validate_code_ast_analysis(self, safety_validator):
        """Test AST-based code analysis."""
        ast_dangerous_code = """
def malicious_function():
    exec("print('This is dangerous')")
    compile("malicious_code", "<string>", "exec")
    __import__("os").system("ls")
        """
        
        result = await safety_validator.validate_code("test_agent", ast_dangerous_code, "ast_test")
        
        assert result["is_safe"] is False
        assert result["violation_count"] > 0
        
        violations = await safety_validator.get_agent_violations("test_agent")
        ast_violations = [v for v in violations if v.detection_method == "ast_analysis"]
        assert len(ast_violations) > 0
        
        # Should detect exec, compile, and __import__ calls
        violation_evidence = [v.evidence for v in ast_violations]
        functions_detected = [ev.get("function") for ev in violation_evidence if "function" in ev]
        assert "exec" in functions_detected
        assert "compile" in functions_detected
        assert "__import__" in functions_detected
    
    @pytest.mark.asyncio
    async def test_validate_code_syntax_error(self, safety_validator):
        """Test code validation with syntax errors."""
        syntax_error_code = """
def broken_function(
    print("This has a syntax error"
    return "incomplete"
        """
        
        result = await safety_validator.validate_code("test_agent", syntax_error_code, "syntax_test")
        
        assert result["is_safe"] is False
        assert result["violation_count"] > 0
        
        violations = await safety_validator.get_agent_violations("test_agent")
        syntax_violations = [v for v in violations if v.violation_type == ViolationType.MALICIOUS_CODE]
        assert len(syntax_violations) > 0
        assert "syntax error" in syntax_violations[0].description.lower()
    
    @pytest.mark.asyncio
    async def test_monitor_agent_resources(self, safety_validator):
        """Test agent resource monitoring."""
        agent_id = "test_agent"
        
        # Start monitoring
        await safety_validator.monitor_agent_resources(agent_id)
        
        assert agent_id in safety_validator.monitored_agents
        assert agent_id in safety_validator.resource_limits
        assert agent_id in safety_validator.resource_usage_history
        assert safety_validator.stats["agents_monitored"] == 1
        
        # Stop monitoring
        await safety_validator.stop_monitoring_agent(agent_id)
        
        assert agent_id not in safety_validator.monitored_agents
        assert safety_validator.stats["agents_monitored"] == 0
    
    @pytest.mark.asyncio
    async def test_set_resource_limits(self, safety_validator):
        """Test setting resource limits for an agent."""
        agent_id = "test_agent"
        
        custom_limits = {
            ResourceType.CPU: 25.0,
            ResourceType.MEMORY: 512.0,
            ResourceType.FILE_HANDLES: 50
        }
        
        await safety_validator.set_resource_limits(agent_id, custom_limits)
        
        assert agent_id in safety_validator.resource_limits
        assert safety_validator.resource_limits[agent_id][ResourceType.CPU] == 25.0
        assert safety_validator.resource_limits[agent_id][ResourceType.MEMORY] == 512.0
        assert safety_validator.resource_limits[agent_id][ResourceType.FILE_HANDLES] == 50
    
    @pytest.mark.asyncio
    async def test_resource_violation_detection(self, safety_validator):
        """Test resource usage violation detection."""
        agent_id = "test_agent"
        
        # Set low limits for testing
        await safety_validator.set_resource_limits(agent_id, {
            ResourceType.CPU: 10.0,
            ResourceType.MEMORY: 100.0
        })
        
        # Create usage that exceeds limits
        high_usage = ResourceUsage(
            agent_id=agent_id,
            timestamp=datetime.now(),
            cpu_percent=50.0,  # Exceeds 10% limit
            memory_mb=500.0    # Exceeds 100MB limit
        )
        
        # Check for violations
        violations = await safety_validator._check_resource_violations(agent_id, high_usage)
        
        assert len(violations) == 2  # CPU and memory violations
        
        cpu_violation = next((v for v in violations if "CPU" in v.description), None)
        memory_violation = next((v for v in violations if "Memory" in v.description), None)
        
        assert cpu_violation is not None
        assert memory_violation is not None
        assert cpu_violation.violation_type == ViolationType.RESOURCE_ABUSE
        assert memory_violation.violation_type == ViolationType.RESOURCE_ABUSE
    
    @pytest.mark.asyncio
    async def test_behavior_anomaly_detection(self, safety_validator):
        """Test behavior anomaly detection."""
        agent_id = "test_agent"
        
        # Create baseline usage history
        baseline_usage = []
        for i in range(100):
            usage = ResourceUsage(
                agent_id=agent_id,
                timestamp=datetime.now() - timedelta(minutes=100-i),
                cpu_percent=20.0 + (i % 5),  # Stable around 20%
                memory_mb=200.0 + (i % 10)  # Stable around 200MB
            )
            baseline_usage.append(usage)
        
        safety_validator.resource_usage_history[agent_id] = baseline_usage
        
        # Create anomalous usage
        anomalous_usage = ResourceUsage(
            agent_id=agent_id,
            timestamp=datetime.now(),
            cpu_percent=80.0,  # Significant spike
            memory_mb=800.0    # Significant spike
        )
        
        # Detect anomalies
        violations = await safety_validator._detect_behavior_anomalies(agent_id, anomalous_usage)
        
        assert len(violations) > 0
        
        # Should detect both CPU and memory anomalies
        cpu_anomaly = next((v for v in violations if "CPU" in v.description), None)
        memory_anomaly = next((v for v in violations if "Memory" in v.description), None)
        
        assert cpu_anomaly is not None
        assert memory_anomaly is not None
        assert cpu_anomaly.violation_type == ViolationType.BEHAVIOR_ANOMALY
        assert memory_anomaly.violation_type == ViolationType.BEHAVIOR_ANOMALY
    
    @pytest.mark.asyncio
    async def test_get_agent_violations(self, safety_validator):
        """Test retrieving violations for a specific agent."""
        agent_id = "test_agent"
        
        # Create some test violations
        violation1 = await safety_validator._create_violation(
            agent_id=agent_id,
            violation_type=ViolationType.CODE_INJECTION,
            threat_level=ThreatLevel.HIGH,
            description="Test violation 1",
            evidence={},
            context={},
            detection_method="test"
        )
        
        violation2 = await safety_validator._create_violation(
            agent_id=agent_id,
            violation_type=ViolationType.RESOURCE_ABUSE,
            threat_level=ThreatLevel.MEDIUM,
            description="Test violation 2",
            evidence={},
            context={},
            detection_method="test"
        )
        
        # Create violation for different agent
        await safety_validator._create_violation(
            agent_id="other_agent",
            violation_type=ViolationType.BEHAVIOR_ANOMALY,
            threat_level=ThreatLevel.LOW,
            description="Other agent violation",
            evidence={},
            context={},
            detection_method="test"
        )
        
        # Get violations for test_agent
        agent_violations = await safety_validator.get_agent_violations(agent_id)
        
        assert len(agent_violations) == 2
        assert all(v.agent_id == agent_id for v in agent_violations)
        
        # Violations should be sorted by detection time (most recent first)
        assert agent_violations[0].detected_at >= agent_violations[1].detected_at
    
    @pytest.mark.asyncio
    async def test_resolve_violation(self, safety_validator):
        """Test violation resolution."""
        agent_id = "test_agent"
        
        # Create a test violation
        violation = await safety_validator._create_violation(
            agent_id=agent_id,
            violation_type=ViolationType.CODE_INJECTION,
            threat_level=ThreatLevel.HIGH,
            description="Test violation",
            evidence={},
            context={},
            detection_method="test"
        )
        
        # Resolve the violation
        result = await safety_validator.resolve_violation(
            violation.violation_id,
            "Resolved by fixing the code"
        )
        
        assert result is True
        assert violation.resolved is True
        assert violation.resolution_notes == "Resolved by fixing the code"
        assert violation.resolved_at is not None
        
        # Test resolving non-existent violation
        result = await safety_validator.resolve_violation("non_existent", "test")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_auto_blocking_critical_threats(self, safety_validator):
        """Test automatic blocking of critical threats."""
        agent_id = "test_agent"
        
        # Create a critical violation
        violation = await safety_validator._create_violation(
            agent_id=agent_id,
            violation_type=ViolationType.CODE_INJECTION,
            threat_level=ThreatLevel.CRITICAL,
            description="Critical threat",
            evidence={},
            context={},
            detection_method="test"
        )
        
        # Should be automatically blocked
        assert violation.blocked is True
        assert "auto_blocked" in violation.action_taken
        assert safety_validator.stats["blocked_actions"] == 1
    
    @pytest.mark.asyncio
    async def test_escalation_repeated_violations(self, safety_validator):
        """Test escalation of repeated violations."""
        agent_id = "test_agent"
        
        # Create multiple violations to trigger escalation
        for i in range(12):  # Exceed max_violations_per_agent (10)
            await safety_validator._create_violation(
                agent_id=agent_id,
                violation_type=ViolationType.RESOURCE_ABUSE,
                threat_level=ThreatLevel.MEDIUM,
                description=f"Violation {i}",
                evidence={},
                context={},
                detection_method="test"
            )
        
        # Last violations should be escalated
        agent_violations = await safety_validator.get_agent_violations(agent_id)
        recent_violations = agent_violations[:2]  # Most recent
        
        assert any(v.escalated for v in recent_violations)
        assert safety_validator.stats["escalated_incidents"] > 0
    
    def test_safety_violation_properties(self):
        """Test SafetyViolation dataclass properties."""
        violation = SafetyViolation(
            violation_id="test_violation",
            agent_id="test_agent",
            violation_type=ViolationType.CODE_INJECTION,
            threat_level=ThreatLevel.HIGH,
            description="Test violation",
            evidence={"test": "data"},
            context={"context": "info"},
            detection_method="test_method",
            confidence_score=0.9
        )
        
        assert violation.violation_id == "test_violation"
        assert violation.agent_id == "test_agent"
        assert violation.violation_type == ViolationType.CODE_INJECTION
        assert violation.threat_level == ThreatLevel.HIGH
        assert violation.confidence_score == 0.9
        assert violation.blocked is False
        assert violation.resolved is False
    
    def test_resource_usage_properties(self):
        """Test ResourceUsage dataclass properties."""
        usage = ResourceUsage(
            agent_id="test_agent",
            timestamp=datetime.now(),
            cpu_percent=25.5,
            memory_mb=512.0,
            disk_io_mb=10.5,
            network_io_mb=5.2,
            file_handles=15,
            process_count=3
        )
        
        assert usage.agent_id == "test_agent"
        assert usage.cpu_percent == 25.5
        assert usage.memory_mb == 512.0
        assert usage.disk_io_mb == 10.5
        assert usage.network_io_mb == 5.2
        assert usage.file_handles == 15
        assert usage.process_count == 3
        assert usage.cpu_trend == 0.0  # Default
        assert usage.memory_trend == 0.0  # Default
    
    def test_behavior_pattern_properties(self):
        """Test BehaviorPattern dataclass properties."""
        pattern = BehaviorPattern(
            pattern_id="test_pattern",
            agent_id="test_agent",
            pattern_type="resource_usage",
            frequency=0.5,
            duration=60.0,
            mean_values={"cpu": 20.0, "memory": 200.0},
            std_deviations={"cpu": 5.0, "memory": 50.0},
            observation_count=100,
            confidence=0.8
        )
        
        assert pattern.pattern_id == "test_pattern"
        assert pattern.agent_id == "test_agent"
        assert pattern.pattern_type == "resource_usage"
        assert pattern.frequency == 0.5
        assert pattern.mean_values["cpu"] == 20.0
        assert pattern.std_deviations["memory"] == 50.0
        assert pattern.confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_error_handling(self, safety_validator):
        """Test error handling in various methods."""
        # Test code validation with error
        with patch('ast.parse', side_effect=Exception("Parse error")):
            result = await safety_validator.validate_code("test_agent", "test_code")
            assert "error" in result
        
        # Test resource collection with error
        with patch.object(safety_validator, '_collect_resource_usage', side_effect=Exception("Collection error")):
            usage = await safety_validator._collect_resource_usage("test_agent")
            assert usage is None
        
        # Test violation creation with storage error
        with patch.object(safety_validator, 'violations', side_effect=Exception("Storage error")):
            try:
                await safety_validator._create_violation(
                    agent_id="test_agent",
                    violation_type=ViolationType.CODE_INJECTION,
                    threat_level=ThreatLevel.HIGH,
                    description="Test",
                    evidence={},
                    context={},
                    detection_method="test"
                )
                assert False, "Should have raised exception"
            except Exception:
                pass  # Expected


if __name__ == "__main__":
    pytest.main([__file__])