"""
Unit tests for the continuous monitoring service.

Tests monitoring capabilities, alerting, and system health checks.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.services.monitoring_service import (
    ContinuousMonitoringService,
    MonitorType,
    MonitorStatus,
    MonitorCheck,
    MonitorResult,
    MonitorAlert
)


class TestContinuousMonitoringService:
    """Test cases for the continuous monitoring service."""
    
    @pytest.fixture
    def monitoring_service(self):
        """Create a monitoring service instance for testing."""
        service = ContinuousMonitoringService("test_agent")
        return service
    
    @pytest.fixture
    async def initialized_service(self, monitoring_service):
        """Create and initialize a monitoring service."""
        await monitoring_service.initialize()
        yield monitoring_service
        await monitoring_service.shutdown()
    
    def test_service_initialization(self, monitoring_service):
        """Test monitoring service initialization."""
        assert monitoring_service.agent_id == "test_agent"
        assert len(monitoring_service.monitor_checks) == 0
        assert len(monitoring_service.monitor_results) == 0
        assert len(monitoring_service.monitor_alerts) == 0
        assert monitoring_service.stats["total_checks"] == 0
    
    @pytest.mark.asyncio
    async def test_add_website_monitor_check(self, initialized_service):
        """Test adding a website monitoring check."""
        result = await initialized_service.add_monitor_check(
            name="Test Website",
            monitor_type=MonitorType.WEBSITE_HEALTH,
            target="https://example.com",
            interval_seconds=60,
            timeout_seconds=30
        )
        
        assert result["success"] is True
        assert "check_id" in result
        assert result["name"] == "Test Website"
        assert result["monitor_type"] == "website_health"
        
        # Verify check was added
        check_id = result["check_id"]
        assert check_id in initialized_service.monitor_checks
        
        check = initialized_service.monitor_checks[check_id]
        assert check.name == "Test Website"
        assert check.monitor_type == MonitorType.WEBSITE_HEALTH
        assert check.target == "https://example.com"
        assert check.enabled is True
    
    @pytest.mark.asyncio
    async def test_add_system_resource_monitor_check(self, initialized_service):
        """Test adding a system resource monitoring check."""
        result = await initialized_service.add_monitor_check(
            name="CPU Usage",
            monitor_type=MonitorType.SYSTEM_RESOURCE,
            target="cpu",
            warning_threshold=80.0,
            critical_threshold=95.0,
            interval_seconds=30
        )
        
        assert result["success"] is True
        check_id = result["check_id"]
        
        check = initialized_service.monitor_checks[check_id]
        assert check.monitor_type == MonitorType.SYSTEM_RESOURCE
        assert check.target == "cpu"
        assert check.warning_threshold == 80.0
        assert check.critical_threshold == 95.0
    
    @pytest.mark.asyncio
    async def test_remove_monitor_check(self, initialized_service):
        """Test removing a monitoring check."""
        # First add a check
        add_result = await initialized_service.add_monitor_check(
            name="Test Check",
            monitor_type=MonitorType.WEBSITE_HEALTH,
            target="https://test.com"
        )
        
        check_id = add_result["check_id"]
        assert check_id in initialized_service.monitor_checks
        
        # Remove the check
        remove_result = await initialized_service.remove_monitor_check(check_id)
        
        assert remove_result["success"] is True
        assert remove_result["check_id"] == check_id
        assert check_id not in initialized_service.monitor_checks
        assert check_id not in initialized_service.monitor_results
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_check(self, initialized_service):
        """Test removing a non-existent monitoring check."""
        result = await initialized_service.remove_monitor_check("nonexistent_id")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_get_monitor_status_single_check(self, initialized_service):
        """Test getting status for a single monitoring check."""
        # Add a check
        add_result = await initialized_service.add_monitor_check(
            name="Status Test",
            monitor_type=MonitorType.WEBSITE_HEALTH,
            target="https://status-test.com"
        )
        
        check_id = add_result["check_id"]
        
        # Get status
        status_result = await initialized_service.get_monitor_status(check_id)
        
        assert status_result["success"] is True
        status_info = status_result["status"]
        assert status_info["check_id"] == check_id
        assert status_info["name"] == "Status Test"
        assert status_info["monitor_type"] == "website_health"
        assert status_info["enabled"] is True
        assert status_info["consecutive_failures"] == 0
    
    @pytest.mark.asyncio
    async def test_get_monitor_status_all_checks(self, initialized_service):
        """Test getting status for all monitoring checks."""
        # Add multiple checks
        await initialized_service.add_monitor_check(
            name="Check 1",
            monitor_type=MonitorType.WEBSITE_HEALTH,
            target="https://check1.com"
        )
        
        await initialized_service.add_monitor_check(
            name="Check 2",
            monitor_type=MonitorType.SYSTEM_RESOURCE,
            target="memory"
        )
        
        # Get all status
        status_result = await initialized_service.get_monitor_status()
        
        assert status_result["success"] is True
        assert status_result["total_checks"] == 2
        assert len(status_result["checks"]) == 2
        
        # Verify statistics
        stats = status_result["statistics"]
        assert stats["total_checks"] == 2
    
    @pytest.mark.asyncio
    async def test_get_status_nonexistent_check(self, initialized_service):
        """Test getting status for a non-existent check."""
        result = await initialized_service.get_monitor_status("nonexistent_id")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    @patch('psutil.cpu_percent')
    async def test_system_resource_check_cpu(self, mock_cpu_percent, monitoring_service):
        """Test system resource monitoring for CPU."""
        mock_cpu_percent.return_value = 75.0
        
        check = MonitorCheck(
            check_id="test_cpu_check",
            name="CPU Test",
            monitor_type=MonitorType.SYSTEM_RESOURCE,
            target="cpu",
            warning_threshold=80.0,
            critical_threshold=95.0
        )
        
        result = await monitoring_service._check_system_resource(check, "test_result")
        
        assert result.status == MonitorStatus.HEALTHY
        assert result.value == 75.0
        assert "CPU usage: 75.0%" in result.message
        mock_cpu_percent.assert_called_once_with(interval=1)
    
    @pytest.mark.asyncio
    @patch('psutil.cpu_percent')
    async def test_system_resource_check_cpu_warning(self, mock_cpu_percent, monitoring_service):
        """Test system resource monitoring with warning threshold."""
        mock_cpu_percent.return_value = 85.0
        
        check = MonitorCheck(
            check_id="test_cpu_check",
            name="CPU Test",
            monitor_type=MonitorType.SYSTEM_RESOURCE,
            target="cpu",
            warning_threshold=80.0,
            critical_threshold=95.0
        )
        
        result = await monitoring_service._check_system_resource(check, "test_result")
        
        assert result.status == MonitorStatus.WARNING
        assert result.value == 85.0
        assert "WARNING" in result.message
    
    @pytest.mark.asyncio
    @patch('psutil.cpu_percent')
    async def test_system_resource_check_cpu_critical(self, mock_cpu_percent, monitoring_service):
        """Test system resource monitoring with critical threshold."""
        mock_cpu_percent.return_value = 98.0
        
        check = MonitorCheck(
            check_id="test_cpu_check",
            name="CPU Test",
            monitor_type=MonitorType.SYSTEM_RESOURCE,
            target="cpu",
            warning_threshold=80.0,
            critical_threshold=95.0
        )
        
        result = await monitoring_service._check_system_resource(check, "test_result")
        
        assert result.status == MonitorStatus.CRITICAL
        assert result.value == 98.0
        assert "CRITICAL" in result.message
    
    @pytest.mark.asyncio
    @patch('psutil.virtual_memory')
    async def test_system_resource_check_memory(self, mock_memory, monitoring_service):
        """Test system resource monitoring for memory."""
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 60.0
        mock_memory.return_value = mock_memory_obj
        
        check = MonitorCheck(
            check_id="test_memory_check",
            name="Memory Test",
            monitor_type=MonitorType.SYSTEM_RESOURCE,
            target="memory",
            warning_threshold=85.0,
            critical_threshold=95.0
        )
        
        result = await monitoring_service._check_system_resource(check, "test_result")
        
        assert result.status == MonitorStatus.HEALTHY
        assert result.value == 60.0
        assert "Memory usage: 60.0%" in result.message
    
    @pytest.mark.asyncio
    async def test_system_resource_check_unknown_type(self, monitoring_service):
        """Test system resource monitoring with unknown resource type."""
        check = MonitorCheck(
            check_id="test_unknown_check",
            name="Unknown Test",
            monitor_type=MonitorType.SYSTEM_RESOURCE,
            target="unknown_resource"
        )
        
        result = await monitoring_service._check_system_resource(check, "test_result")
        
        assert result.status == MonitorStatus.UNKNOWN
        assert "Unknown resource type" in result.message
    
    @pytest.mark.asyncio
    async def test_monitor_result_properties(self):
        """Test MonitorResult properties and methods."""
        result = MonitorResult(
            result_id="test_result",
            check_id="test_check",
            timestamp=datetime.now(),
            status=MonitorStatus.HEALTHY,
            response_time_ms=150.0,
            message="Test successful"
        )
        
        assert result.is_healthy() is True
        assert result.requires_alert() is False
        
        # Test warning status
        result.status = MonitorStatus.WARNING
        assert result.is_healthy() is False
        assert result.requires_alert() is True
        
        # Test critical status
        result.status = MonitorStatus.CRITICAL
        assert result.is_healthy() is False
        assert result.requires_alert() is True
    
    @pytest.mark.asyncio
    async def test_monitor_alert_properties(self):
        """Test MonitorAlert properties and methods."""
        result = MonitorResult(
            result_id="test_result",
            check_id="test_check",
            timestamp=datetime.now(),
            status=MonitorStatus.CRITICAL,
            message="Test failed"
        )
        
        alert = MonitorAlert(
            alert_id="test_alert",
            check_id="test_check",
            alert_type="failure",
            severity=MonitorStatus.CRITICAL,
            title="Test Alert",
            message="Test alert message",
            triggered_at=datetime.now(),
            trigger_result=result,
            consecutive_failures=3
        )
        
        assert alert.acknowledged is False
        assert alert.resolved is False
        assert alert.consecutive_failures == 3
        assert alert.severity == MonitorStatus.CRITICAL
    
    @pytest.mark.asyncio
    async def test_get_monitor_alerts_empty(self, initialized_service):
        """Test getting monitor alerts when none exist."""
        alerts = await initialized_service.get_monitor_alerts()
        
        assert isinstance(alerts, list)
        assert len(alerts) == 0
    
    @pytest.mark.asyncio
    async def test_get_monitor_alerts_with_filtering(self, initialized_service):
        """Test getting monitor alerts with filtering."""
        # Create a mock alert
        alert = MonitorAlert(
            alert_id="test_alert",
            check_id="test_check",
            alert_type="failure",
            severity=MonitorStatus.CRITICAL,
            title="Test Alert",
            message="Test message",
            triggered_at=datetime.now(),
            trigger_result=MonitorResult(
                result_id="test_result",
                check_id="test_check",
                timestamp=datetime.now(),
                status=MonitorStatus.CRITICAL
            )
        )
        
        initialized_service.monitor_alerts["test_alert"] = alert
        
        # Get all alerts
        all_alerts = await initialized_service.get_monitor_alerts(unresolved_only=False)
        assert len(all_alerts) == 1
        assert all_alerts[0]["alert_id"] == "test_alert"
        assert all_alerts[0]["severity"] == "critical"
        
        # Filter by severity
        critical_alerts = await initialized_service.get_monitor_alerts(
            severity=MonitorStatus.CRITICAL,
            unresolved_only=False
        )
        assert len(critical_alerts) == 1
        
        # Filter by different severity (should return empty)
        warning_alerts = await initialized_service.get_monitor_alerts(
            severity=MonitorStatus.WARNING,
            unresolved_only=False
        )
        assert len(warning_alerts) == 0
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, initialized_service):
        """Test that statistics are properly tracked."""
        initial_stats = initialized_service.stats.copy()
        
        # Add some checks
        await initialized_service.add_monitor_check(
            name="Stats Test 1",
            monitor_type=MonitorType.WEBSITE_HEALTH,
            target="https://stats1.com"
        )
        
        await initialized_service.add_monitor_check(
            name="Stats Test 2",
            monitor_type=MonitorType.SYSTEM_RESOURCE,
            target="cpu"
        )
        
        # Verify statistics updated
        assert initialized_service.stats["total_checks"] == initial_stats["total_checks"] + 2
        assert initialized_service.stats["checks_by_type"]["website_health"] == initial_stats["checks_by_type"]["website_health"] + 1
        assert initialized_service.stats["checks_by_type"]["system_resource"] == initial_stats["checks_by_type"]["system_resource"] + 1
    
    @pytest.mark.asyncio
    async def test_concurrent_generation_limit(self, initialized_service):
        """Test that concurrent monitoring respects limits."""
        # This test would be more complex in a real implementation
        # For now, just verify the config exists
        assert "max_concurrent_checks" in initialized_service.config
        assert initialized_service.config["max_concurrent_checks"] > 0
    
    @pytest.mark.asyncio
    async def test_service_shutdown_cleanup(self, monitoring_service):
        """Test that service shutdown properly cleans up resources."""
        await monitoring_service.initialize()
        
        # Add some checks to create tasks
        await monitoring_service.add_monitor_check(
            name="Shutdown Test",
            monitor_type=MonitorType.WEBSITE_HEALTH,
            target="https://shutdown-test.com"
        )
        
        # Verify tasks were created
        assert len(monitoring_service.check_tasks) > 0
        
        # Shutdown and verify cleanup
        await monitoring_service.shutdown()
        
        # After shutdown, HTTP session should be closed
        if monitoring_service.http_session:
            assert monitoring_service.http_session.closed
    
    def test_monitor_check_dataclass(self):
        """Test MonitorCheck dataclass functionality."""
        check = MonitorCheck(
            check_id="test_check",
            name="Test Check",
            monitor_type=MonitorType.WEBSITE_HEALTH,
            target="https://test.com",
            interval_seconds=60,
            timeout_seconds=30,
            warning_threshold=5000.0,
            critical_threshold=10000.0,
            tags=["test", "website"],
            description="Test monitoring check"
        )
        
        assert check.check_id == "test_check"
        assert check.name == "Test Check"
        assert check.monitor_type == MonitorType.WEBSITE_HEALTH
        assert check.target == "https://test.com"
        assert check.enabled is True
        assert check.alert_on_failure is True
        assert check.alert_after_failures == 3
        assert "test" in check.tags
        assert "website" in check.tags
    
    def test_monitor_status_enum(self):
        """Test MonitorStatus enum values."""
        assert MonitorStatus.HEALTHY.value == "healthy"
        assert MonitorStatus.WARNING.value == "warning"
        assert MonitorStatus.CRITICAL.value == "critical"
        assert MonitorStatus.UNKNOWN.value == "unknown"
        assert MonitorStatus.DISABLED.value == "disabled"
    
    def test_monitor_type_enum(self):
        """Test MonitorType enum values."""
        assert MonitorType.WEBSITE_HEALTH.value == "website_health"
        assert MonitorType.API_ENDPOINT.value == "api_endpoint"
        assert MonitorType.SYSTEM_RESOURCE.value == "system_resource"
        assert MonitorType.DATABASE_CONNECTION.value == "database_connection"
        assert MonitorType.SERVICE_STATUS.value == "service_status"
        assert MonitorType.CUSTOM_METRIC.value == "custom_metric"


if __name__ == "__main__":
    pytest.main([__file__])