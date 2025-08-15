"""
Unit tests for the monitoring and reporting system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.oversight.monitoring_reporting import (
    MonitoringReportingSystem,
    MonitoredEvent,
    Alert,
    Report,
    EventSeverity,
    EventCategory,
    AlertType
)


class TestMonitoringReportingSystem:
    """Test cases for MonitoringReportingSystem."""
    
    @pytest.fixture
    async def monitoring_system(self):
        """Create a monitoring system for testing."""
        system = MonitoringReportingSystem("test_monitor")
        await system.initialize()
        yield system
        await system.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test monitoring system initialization."""
        system = MonitoringReportingSystem("test_monitor")
        
        assert system.agent_id == "test_monitor"
        assert system.events == {}
        assert system.alerts == {}
        assert system.reports == {}
        assert len(system.event_processors) > 0
        assert len(system.alert_rules) > 0
        
        await system.initialize()
        assert len(system.background_tasks) > 0
        
        await system.shutdown()
    
    @pytest.mark.asyncio
    async def test_log_event(self, monitoring_system):
        """Test event logging functionality."""
        # Log a test event
        event_id = await monitoring_system.log_event(
            agent_id="test_agent",
            event_type="test_event",
            category=EventCategory.AGENT_LIFECYCLE,
            severity=EventSeverity.INFO,
            description="Test event description",
            data={"key": "value"},
            context={"context_key": "context_value"}
        )
        
        # Verify event was logged
        assert event_id != ""
        assert event_id in monitoring_system.events
        
        event = monitoring_system.events[event_id]
        assert event.agent_id == "test_agent"
        assert event.event_type == "test_event"
        assert event.category == EventCategory.AGENT_LIFECYCLE
        assert event.severity == EventSeverity.INFO
        assert event.description == "Test event description"
        assert event.data == {"key": "value"}
        assert event.context == {"context_key": "context_value"}
        
        # Verify statistics updated
        assert monitoring_system.stats["total_events"] == 1
        assert monitoring_system.stats["events_by_category"][EventCategory.AGENT_LIFECYCLE.value] == 1
        assert monitoring_system.stats["events_by_severity"][EventSeverity.INFO.value] == 1
    
    @pytest.mark.asyncio
    async def test_log_intervention_event(self, monitoring_system):
        """Test logging events that require intervention."""
        event_id = await monitoring_system.log_event(
            agent_id="test_agent",
            event_type="critical_error",
            category=EventCategory.ERROR,
            severity=EventSeverity.CRITICAL,
            description="Critical error occurred",
            requires_intervention=True,
            intervention_reason="System instability detected"
        )
        
        # Verify event was logged with intervention flag
        event = monitoring_system.events[event_id]
        assert event.requires_intervention is True
        assert event.intervention_reason == "System instability detected"
        
        # Verify intervention request statistics
        assert monitoring_system.stats["intervention_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_generate_alert(self, monitoring_system):
        """Test alert generation."""
        alert_id = await monitoring_system.generate_alert(
            alert_type=AlertType.IMMEDIATE,
            severity=EventSeverity.WARNING,
            title="Test Alert",
            message="This is a test alert",
            triggering_events=["event_1", "event_2"]
        )
        
        # Verify alert was generated
        assert alert_id != ""
        assert alert_id in monitoring_system.alerts
        assert alert_id in monitoring_system.active_alerts
        
        alert = monitoring_system.alerts[alert_id]
        assert alert.alert_type == AlertType.IMMEDIATE
        assert alert.severity == EventSeverity.WARNING
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test alert"
        assert alert.triggering_events == ["event_1", "event_2"]
        assert alert.acknowledged is False
        assert alert.resolved is False
        
        # Verify statistics updated
        assert monitoring_system.stats["total_alerts"] == 1
        assert monitoring_system.stats["active_alerts_count"] == 1
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, monitoring_system):
        """Test alert acknowledgment."""
        # Generate an alert
        alert_id = await monitoring_system.generate_alert(
            alert_type=AlertType.IMMEDIATE,
            severity=EventSeverity.WARNING,
            title="Test Alert",
            message="Test message"
        )
        
        # Acknowledge the alert
        result = await monitoring_system.acknowledge_alert(alert_id, "test_operator")
        
        assert result is True
        
        alert = monitoring_system.alerts[alert_id]
        assert alert.acknowledged is True
        assert alert.acknowledged_at is not None
        assert "Acknowledged by test_operator" in alert.actions_taken
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, monitoring_system):
        """Test alert resolution."""
        # Generate an alert
        alert_id = await monitoring_system.generate_alert(
            alert_type=AlertType.IMMEDIATE,
            severity=EventSeverity.WARNING,
            title="Test Alert",
            message="Test message"
        )
        
        # Resolve the alert
        result = await monitoring_system.resolve_alert(
            alert_id, 
            "Issue resolved", 
            "test_operator"
        )
        
        assert result is True
        
        alert = monitoring_system.alerts[alert_id]
        assert alert.resolved is True
        assert alert.resolved_at is not None
        assert "Resolved by test_operator: Issue resolved" in alert.actions_taken
        assert alert_id not in monitoring_system.active_alerts
        assert monitoring_system.stats["active_alerts_count"] == 0
    
    @pytest.mark.asyncio
    async def test_generate_report(self, monitoring_system):
        """Test report generation."""
        # Add some test events
        await monitoring_system.log_event(
            agent_id="test_agent",
            event_type="test_event_1",
            category=EventCategory.AGENT_LIFECYCLE,
            severity=EventSeverity.INFO,
            description="Test event 1"
        )
        
        await monitoring_system.log_event(
            agent_id="test_agent",
            event_type="test_event_2",
            category=EventCategory.COMMUNICATION,
            severity=EventSeverity.WARNING,
            description="Test event 2"
        )
        
        # Generate an alert
        await monitoring_system.generate_alert(
            alert_type=AlertType.IMMEDIATE,
            severity=EventSeverity.WARNING,
            title="Test Alert",
            message="Test alert message"
        )
        
        # Generate report
        report_id = await monitoring_system.generate_report(
            report_type="test_report",
            title="Test Report",
            recipients=["test@example.com"]
        )
        
        # Verify report was generated
        assert report_id != ""
        assert report_id in monitoring_system.reports
        
        report = monitoring_system.reports[report_id]
        assert report.report_type == "test_report"
        assert report.title == "Test Report"
        assert report.recipients == ["test@example.com"]
        assert len(report.events_included) == 2
        assert len(report.alerts_included) == 1
        assert report.content != ""
        
        # Verify statistics updated
        assert monitoring_system.stats["reports_generated"] == 1
    
    @pytest.mark.asyncio
    async def test_get_system_status(self, monitoring_system):
        """Test system status retrieval."""
        # Add some test data
        await monitoring_system.log_event(
            agent_id="test_agent",
            event_type="test_event",
            category=EventCategory.AGENT_LIFECYCLE,
            severity=EventSeverity.INFO,
            description="Test event"
        )
        
        await monitoring_system.generate_alert(
            alert_type=AlertType.IMMEDIATE,
            severity=EventSeverity.WARNING,
            title="Test Alert",
            message="Test message"
        )
        
        # Get system status
        status = await monitoring_system.get_system_status()
        
        # Verify status information
        assert "system_uptime_hours" in status
        assert status["total_events"] == 1
        assert status["active_alerts_count"] == 1
        assert len(status["active_alerts"]) == 1
        assert status["events_by_category"][EventCategory.AGENT_LIFECYCLE.value] == 1
        assert status["events_by_severity"][EventSeverity.INFO.value] == 1
        assert status["intervention_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_event_processing_agent_lifecycle(self, monitoring_system):
        """Test processing of agent lifecycle events."""
        # Log a critical agent lifecycle event
        event_id = await monitoring_system.log_event(
            agent_id="test_agent",
            event_type="agent_destroyed",
            category=EventCategory.AGENT_LIFECYCLE,
            severity=EventSeverity.CRITICAL,
            description="Agent unexpectedly destroyed"
        )
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Check if alert was generated
        lifecycle_alerts = [
            alert for alert in monitoring_system.alerts.values()
            if "Agent Lifecycle Issue" in alert.title
        ]
        
        assert len(lifecycle_alerts) > 0
        alert = lifecycle_alerts[0]
        assert alert.severity == EventSeverity.CRITICAL
        assert event_id in alert.triggering_events
    
    @pytest.mark.asyncio
    async def test_event_processing_security(self, monitoring_system):
        """Test processing of security events."""
        # Log a security event
        event_id = await monitoring_system.log_event(
            agent_id="test_agent",
            event_type="unauthorized_access",
            category=EventCategory.SECURITY,
            severity=EventSeverity.WARNING,
            description="Unauthorized access attempt detected"
        )
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Check if security alert was generated
        security_alerts = [
            alert for alert in monitoring_system.alerts.values()
            if "Security Alert" in alert.title
        ]
        
        assert len(security_alerts) > 0
        alert = security_alerts[0]
        assert alert.severity >= EventSeverity.WARNING
        assert event_id in alert.triggering_events
    
    @pytest.mark.asyncio
    async def test_event_processing_code_modification(self, monitoring_system):
        """Test processing of unsafe code modification events."""
        # Log an unsafe code modification event
        event_id = await monitoring_system.log_event(
            agent_id="test_agent",
            event_type="unsafe_code_modification",
            category=EventCategory.CODE_MODIFICATION,
            severity=EventSeverity.CRITICAL,
            description="Agent attempted to modify system files"
        )
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Check if critical alert was generated
        code_alerts = [
            alert for alert in monitoring_system.alerts.values()
            if "Unsafe Code Modification" in alert.title
        ]
        
        assert len(code_alerts) > 0
        alert = code_alerts[0]
        assert alert.severity == EventSeverity.CRITICAL
        assert event_id in alert.triggering_events
        
        # Check if event was marked for intervention
        event = monitoring_system.events[event_id]
        assert event.requires_intervention is True
        assert event.intervention_reason == "Unsafe code modification detected"
    
    @pytest.mark.asyncio
    async def test_alert_rule_error_rate(self, monitoring_system):
        """Test alert rule for high error rate."""
        # Mock high error rate
        with patch.object(monitoring_system, '_calculate_error_rate', return_value=0.15):
            # Trigger alert rule check
            for rule in monitoring_system.alert_rules:
                if rule["name"] == "High Error Rate":
                    if rule["condition"]():
                        await monitoring_system.generate_alert(
                            alert_type=rule["alert_type"],
                            severity=rule["severity"],
                            title=rule["name"],
                            message=rule["message"]
                        )
                        break
            
            # Check if alert was generated
            error_rate_alerts = [
                alert for alert in monitoring_system.alerts.values()
                if "High Error Rate" in alert.title
            ]
            
            assert len(error_rate_alerts) > 0
            alert = error_rate_alerts[0]
            assert alert.alert_type == AlertType.THRESHOLD_BREACH
            assert alert.severity == EventSeverity.WARNING
    
    @pytest.mark.asyncio
    async def test_alert_rule_security_incidents(self, monitoring_system):
        """Test alert rule for multiple security incidents."""
        # Mock high security incident count
        with patch.object(monitoring_system, '_count_recent_security_incidents', return_value=6):
            # Trigger alert rule check
            for rule in monitoring_system.alert_rules:
                if rule["name"] == "Security Incidents":
                    if rule["condition"]():
                        await monitoring_system.generate_alert(
                            alert_type=rule["alert_type"],
                            severity=rule["severity"],
                            title=rule["name"],
                            message=rule["message"]
                        )
                        break
            
            # Check if alert was generated
            security_alerts = [
                alert for alert in monitoring_system.alerts.values()
                if "Security Incidents" in alert.title
            ]
            
            assert len(security_alerts) > 0
            alert = security_alerts[0]
            assert alert.alert_type == AlertType.PATTERN_DETECTED
            assert alert.severity == EventSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_intervention_handling(self, monitoring_system):
        """Test handling of intervention requests."""
        # Log an event requiring intervention
        event_id = await monitoring_system.log_event(
            agent_id="test_agent",
            event_type="system_compromise",
            category=EventCategory.SECURITY,
            severity=EventSeverity.EMERGENCY,
            description="System compromise detected",
            requires_intervention=True,
            intervention_reason="Immediate human intervention required"
        )
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check if intervention alert was generated
        intervention_alerts = [
            alert for alert in monitoring_system.alerts.values()
            if alert.alert_type == AlertType.INTERVENTION_REQUIRED
        ]
        
        assert len(intervention_alerts) > 0
        alert = intervention_alerts[0]
        assert alert.severity == EventSeverity.CRITICAL
        assert "Human Intervention Required" in alert.title
        assert event_id in alert.triggering_events
        
        # Check if intervention report was generated
        intervention_reports = [
            report for report in monitoring_system.reports.values()
            if report.report_type == "intervention_request"
        ]
        
        assert len(intervention_reports) > 0
    
    def test_monitored_event_to_dict(self):
        """Test MonitoredEvent serialization."""
        event = MonitoredEvent(
            event_id="test_event_1",
            timestamp=datetime.now(),
            agent_id="test_agent",
            event_type="test_event",
            category=EventCategory.AGENT_LIFECYCLE,
            severity=EventSeverity.INFO,
            description="Test event",
            data={"key": "value"},
            context={"context_key": "context_value"},
            requires_intervention=True,
            intervention_reason="Test intervention"
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_id"] == "test_event_1"
        assert event_dict["agent_id"] == "test_agent"
        assert event_dict["event_type"] == "test_event"
        assert event_dict["category"] == EventCategory.AGENT_LIFECYCLE.value
        assert event_dict["severity"] == EventSeverity.INFO.value
        assert event_dict["description"] == "Test event"
        assert event_dict["data"] == {"key": "value"}
        assert event_dict["context"] == {"context_key": "context_value"}
        assert event_dict["requires_intervention"] is True
        assert event_dict["intervention_reason"] == "Test intervention"
    
    def test_alert_to_dict(self):
        """Test Alert serialization."""
        alert = Alert(
            alert_id="test_alert_1",
            alert_type=AlertType.IMMEDIATE,
            severity=EventSeverity.WARNING,
            title="Test Alert",
            message="Test alert message",
            triggering_events=["event_1", "event_2"],
            acknowledged=True,
            resolved=False
        )
        alert.acknowledged_at = datetime.now()
        alert.actions_taken = ["Action 1", "Action 2"]
        
        alert_dict = alert.to_dict()
        
        assert alert_dict["alert_id"] == "test_alert_1"
        assert alert_dict["alert_type"] == AlertType.IMMEDIATE.value
        assert alert_dict["severity"] == EventSeverity.WARNING.value
        assert alert_dict["title"] == "Test Alert"
        assert alert_dict["message"] == "Test alert message"
        assert alert_dict["triggering_events"] == ["event_1", "event_2"]
        assert alert_dict["acknowledged"] is True
        assert alert_dict["resolved"] is False
        assert alert_dict["actions_taken"] == ["Action 1", "Action 2"]
    
    def test_report_to_dict(self):
        """Test Report serialization."""
        report = Report(
            report_id="test_report_1",
            report_type="daily_summary",
            title="Daily Report",
            content="Report content",
            events_included=["event_1", "event_2"],
            alerts_included=["alert_1"],
            delivered=True
        )
        
        report_dict = report.to_dict()
        
        assert report_dict["report_id"] == "test_report_1"
        assert report_dict["report_type"] == "daily_summary"
        assert report_dict["title"] == "Daily Report"
        assert report_dict["content"] == "Report content"
        assert report_dict["events_included"] == 2
        assert report_dict["alerts_included"] == 1
        assert report_dict["delivered"] is True
    
    @pytest.mark.asyncio
    async def test_error_handling_log_event(self, monitoring_system):
        """Test error handling in log_event method."""
        # Test with invalid parameters
        with patch.object(monitoring_system, 'event_queue') as mock_queue:
            mock_queue.put.side_effect = Exception("Queue error")
            
            event_id = await monitoring_system.log_event(
                agent_id="test_agent",
                event_type="test_event",
                category=EventCategory.AGENT_LIFECYCLE,
                severity=EventSeverity.INFO,
                description="Test event"
            )
            
            # Should return empty string on error
            assert event_id == ""
    
    @pytest.mark.asyncio
    async def test_error_handling_generate_alert(self, monitoring_system):
        """Test error handling in generate_alert method."""
        # Mock an error in alert generation
        with patch.object(monitoring_system.alerts, '__setitem__', side_effect=Exception("Storage error")):
            alert_id = await monitoring_system.generate_alert(
                alert_type=AlertType.IMMEDIATE,
                severity=EventSeverity.WARNING,
                title="Test Alert",
                message="Test message"
            )
            
            # Should return empty string on error
            assert alert_id == ""
    
    @pytest.mark.asyncio
    async def test_error_handling_generate_report(self, monitoring_system):
        """Test error handling in generate_report method."""
        # Mock an error in report generation
        with patch.object(monitoring_system, '_generate_report_content', side_effect=Exception("Content error")):
            report_id = await monitoring_system.generate_report(
                report_type="test_report",
                title="Test Report"
            )
            
            # Should return empty string on error
            assert report_id == ""
    
    @pytest.mark.asyncio
    async def test_helper_methods(self, monitoring_system):
        """Test helper methods for alert rule conditions."""
        # Add some test events
        now = datetime.now()
        
        # Add error events
        for i in range(3):
            await monitoring_system.log_event(
                agent_id=f"agent_{i}",
                event_type="error_event",
                category=EventCategory.ERROR,
                severity=EventSeverity.ERROR,
                description=f"Error event {i}"
            )
        
        # Add communication events
        for i in range(2):
            await monitoring_system.log_event(
                agent_id="test_agent",
                event_type="communication_failed",
                category=EventCategory.COMMUNICATION,
                severity=EventSeverity.WARNING,
                description=f"Communication failure {i}"
            )
        
        # Add security events
        await monitoring_system.log_event(
            agent_id="test_agent",
            event_type="security_breach",
            category=EventCategory.SECURITY,
            severity=EventSeverity.CRITICAL,
            description="Security breach detected"
        )
        
        # Test helper methods
        error_rate = monitoring_system._calculate_error_rate()
        assert error_rate > 0
        
        comm_failure_rate = monitoring_system._calculate_communication_failure_rate()
        assert comm_failure_rate > 0
        
        security_incidents = monitoring_system._count_recent_security_incidents()
        assert security_incidents == 1
        
        comm_failures = monitoring_system._count_recent_communication_failures("test_agent")
        assert comm_failures == 2
        
        learning_stagnation = monitoring_system._detect_learning_stagnation()
        assert learning_stagnation is True  # No learning events added


if __name__ == "__main__":
    pytest.main([__file__])