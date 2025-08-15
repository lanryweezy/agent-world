"""
Unit tests for the ecosystem dashboard and monitoring UI.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.ui.dashboard import (
    EcosystemDashboard,
    DashboardConfig
)

from autonomous_ai_ecosystem.ui.monitoring_ui import (
    MonitoringInterface,
    VisualizationComponent,
    VisualizationType,
    MonitoringAlert
)


@pytest_asyncio.fixture
async def mock_orchestrator():
    """Create mock orchestrator for testing."""
    orchestrator = Mock()
    orchestrator.get_system_status = AsyncMock(return_value={
        "ecosystem_id": "test_ecosystem",
        "is_running": True,
        "statistics": {
            "total_systems": 5,
            "running_systems": 4,
            "failed_systems": 1,
            "total_agents": 3
        },
        "systems": {
            "test_system": {
                "status": "running",
                "initialized_at": datetime.now().isoformat()
            }
        }
    })
    
    # Mock agent manager
    orchestrator.agent_manager = Mock()
    orchestrator.agent_manager.get_all_agents_status = AsyncMock(return_value=[
        {
            "agent_id": "test_agent_1",
            "status": "running",
            "uptime_seconds": 123.45,
            "cpu_usage": 25.0,
            "memory_usage_mb": 128.0
        },
        {
            "agent_id": "test_agent_2", 
            "status": "sleeping",
            "uptime_seconds": 67.89,
            "cpu_usage": 5.0,
            "memory_usage_mb": 64.0
        }
    ])
    orchestrator.agent_manager.restart_agent = AsyncMock(return_value=True)
    
    # Mock emergency response
    orchestrator.emergency_response = Mock()
    orchestrator.emergency_response.trigger_emergency_shutdown = AsyncMock(return_value="incident_123")
    
    orchestrator.stop_agent = AsyncMock(return_value=True)
    orchestrator.restart_system = AsyncMock(return_value=True)
    
    return orchestrator


@pytest.mark.asyncio
async def test_dashboard_config_defaults():
    """Test dashboard configuration defaults."""
    config = DashboardConfig()
    
    assert config.host == "localhost"
    assert config.port == 8080
    assert config.title == "Autonomous AI Ecosystem Dashboard"
    assert config.enable_real_time_updates
    assert config.enable_agent_controls
    assert config.enable_system_controls
    assert config.enable_emergency_controls
    assert config.status_update_interval == 5
    assert config.theme == "dark"


@pytest.mark.asyncio
async def test_dashboard_config_customization():
    """Test dashboard configuration customization."""
    config = DashboardConfig(
        host="0.0.0.0",
        port=9090,
        title="Custom Dashboard",
        enable_agent_controls=False,
        theme="light"
    )
    
    assert config.host == "0.0.0.0"
    assert config.port == 9090
    assert config.title == "Custom Dashboard"
    assert not config.enable_agent_controls
    assert config.theme == "light"


@pytest.mark.asyncio
async def test_dashboard_creation_without_fastapi():
    """Test dashboard creation when FastAPI is not available."""
    with patch('autonomous_ai_ecosystem.ui.dashboard.FASTAPI_AVAILABLE', False):
        with pytest.raises(ImportError, match="FastAPI is required"):
            EcosystemDashboard(Mock())


@pytest.mark.asyncio
@patch('autonomous_ai_ecosystem.ui.dashboard.FASTAPI_AVAILABLE', True)
async def test_dashboard_creation_with_fastapi(mock_orchestrator):
    """Test dashboard creation when FastAPI is available."""
    config = DashboardConfig(port=8081)
    
    with patch('autonomous_ai_ecosystem.ui.dashboard.FastAPI'):
        dashboard = EcosystemDashboard(mock_orchestrator, config)
        
        assert dashboard.orchestrator == mock_orchestrator
        assert dashboard.config.port == 8081
        assert len(dashboard.websocket_connections) == 0
        assert dashboard.dashboard_data is not None


@pytest.mark.asyncio
async def test_visualization_component_creation():
    """Test visualization component creation."""
    component = VisualizationComponent(
        component_id="test_comp_1",
        title="Test Component",
        visualization_type=VisualizationType.NETWORK_GRAPH,
        width=800,
        height=600
    )
    
    assert component.component_id == "test_comp_1"
    assert component.title == "Test Component"
    assert component.visualization_type == VisualizationType.NETWORK_GRAPH
    assert component.width == 800
    assert component.height == 600
    assert component.refresh_interval == 5
    assert component.show_legend
    assert component.interactive
    assert component.theme == "dark"


@pytest.mark.asyncio
async def test_monitoring_alert_creation():
    """Test monitoring alert creation."""
    alert = MonitoringAlert(
        alert_id="test_alert_1",
        title="Test Alert",
        message="This is a test alert",
        severity="warning",
        source="test_system",
        agent_id="test_agent"
    )
    
    assert alert.alert_id == "test_alert_1"
    assert alert.title == "Test Alert"
    assert alert.message == "This is a test alert"
    assert alert.severity == "warning"
    assert alert.source == "test_system"
    assert alert.agent_id == "test_agent"
    assert not alert.acknowledged
    assert not alert.resolved
    assert not alert.is_expired()


@pytest.mark.asyncio
async def test_monitoring_alert_expiration():
    """Test monitoring alert expiration."""
    alert = MonitoringAlert(
        alert_id="test_alert_exp",
        title="Expiring Alert",
        message="This alert will expire",
        severity="info"
    )
    
    # Not expired initially
    assert not alert.is_expired()
    
    # Set expiration in the past
    alert.expires_at = datetime.now() - timedelta(minutes=5)
    assert alert.is_expired()


@pytest.mark.asyncio
async def test_monitoring_interface_initialization(mock_orchestrator):
    """Test monitoring interface initialization."""
    interface = MonitoringInterface(mock_orchestrator)
    
    assert interface.orchestrator == mock_orchestrator
    assert len(interface.components) == 0
    assert len(interface.alerts) == 0
    assert interface.stats["total_components"] == 0
    assert interface.stats["active_alerts"] == 0


@pytest.mark.asyncio
async def test_monitoring_interface_component_creation(mock_orchestrator):
    """Test creating visualization components."""
    interface = MonitoringInterface(mock_orchestrator)
    
    component_id = await interface.create_component(
        title="Test Network Graph",
        visualization_type=VisualizationType.NETWORK_GRAPH,
        data_source="agent_network",
        config={"width": 1000, "height": 800}
    )
    
    assert component_id
    assert component_id in interface.components
    
    component = interface.components[component_id]
    assert component.title == "Test Network Graph"
    assert component.visualization_type == VisualizationType.NETWORK_GRAPH
    assert component.data_source == "agent_network"
    assert component.width == 1000
    assert component.height == 800
    
    assert interface.stats["total_components"] == 1


@pytest.mark.asyncio
async def test_monitoring_interface_component_data_update(mock_orchestrator):
    """Test updating component data."""
    interface = MonitoringInterface(mock_orchestrator)
    
    # Create component
    component_id = await interface.create_component(
        title="Test Chart",
        visualization_type=VisualizationType.METRICS_CHART,
        data_source="system_metrics"
    )
    
    # Update data
    test_data = {
        "timestamps": ["2023-01-01T10:00:00"],
        "values": [42.5]
    }
    
    success = await interface.update_component_data(component_id, test_data)
    
    assert success
    
    component = interface.components[component_id]
    assert component.data == test_data
    assert component.last_updated is not None
    assert interface.stats["data_updates"] == 1


@pytest.mark.asyncio
async def test_monitoring_interface_component_data_update_nonexistent(mock_orchestrator):
    """Test updating data for non-existent component."""
    interface = MonitoringInterface(mock_orchestrator)
    
    success = await interface.update_component_data("nonexistent", {"data": "test"})
    
    assert not success


@pytest.mark.asyncio
async def test_monitoring_interface_alert_creation(mock_orchestrator):
    """Test creating monitoring alerts."""
    interface = MonitoringInterface(mock_orchestrator)
    
    alert_id = await interface.create_alert(
        title="Test Alert",
        message="This is a test alert",
        severity="warning",
        source="test_system",
        agent_id="test_agent",
        expires_in_minutes=30,
        suggested_actions=["Check logs", "Restart service"]
    )
    
    assert alert_id
    assert alert_id in interface.alerts
    
    alert = interface.alerts[alert_id]
    assert alert.title == "Test Alert"
    assert alert.message == "This is a test alert"
    assert alert.severity == "warning"
    assert alert.source == "test_system"
    assert alert.agent_id == "test_agent"
    assert alert.expires_at is not None
    assert "Check logs" in alert.suggested_actions
    assert "Restart service" in alert.suggested_actions
    
    assert interface.stats["active_alerts"] == 1


@pytest.mark.asyncio
async def test_monitoring_interface_alert_acknowledgment(mock_orchestrator):
    """Test acknowledging alerts."""
    interface = MonitoringInterface(mock_orchestrator)
    
    # Create alert
    alert_id = await interface.create_alert(
        title="Test Alert",
        message="Test message",
        severity="info"
    )
    
    # Acknowledge alert
    success = await interface.acknowledge_alert(alert_id)
    
    assert success
    
    alert = interface.alerts[alert_id]
    assert alert.acknowledged


@pytest.mark.asyncio
async def test_monitoring_interface_alert_acknowledgment_nonexistent(mock_orchestrator):
    """Test acknowledging non-existent alert."""
    interface = MonitoringInterface(mock_orchestrator)
    
    success = await interface.acknowledge_alert("nonexistent")
    
    assert not success


@pytest.mark.asyncio
async def test_monitoring_interface_alert_resolution(mock_orchestrator):
    """Test resolving alerts."""
    interface = MonitoringInterface(mock_orchestrator)
    
    # Create alert
    alert_id = await interface.create_alert(
        title="Test Alert",
        message="Test message",
        severity="error"
    )
    
    assert interface.stats["active_alerts"] == 1
    
    # Resolve alert
    success = await interface.resolve_alert(alert_id)
    
    assert success
    
    alert = interface.alerts[alert_id]
    assert alert.resolved
    assert interface.stats["active_alerts"] == 0


@pytest.mark.asyncio
async def test_monitoring_interface_alert_resolution_nonexistent(mock_orchestrator):
    """Test resolving non-existent alert."""
    interface = MonitoringInterface(mock_orchestrator)
    
    success = await interface.resolve_alert("nonexistent")
    
    assert not success


@pytest.mark.asyncio
async def test_monitoring_interface_alert_limit(mock_orchestrator):
    """Test alert limit enforcement."""
    interface = MonitoringInterface(mock_orchestrator)
    interface.config["max_alerts"] = 3
    
    # Create alerts beyond limit
    alert_ids = []
    for i in range(5):
        alert_id = await interface.create_alert(
            title=f"Alert {i}",
            message=f"Message {i}",
            severity="info"
        )
        alert_ids.append(alert_id)
    
    # Should only keep the most recent alerts
    assert len(interface.alerts) == 3
    
    # First two alerts should be removed
    assert alert_ids[0] not in interface.alerts
    assert alert_ids[1] not in interface.alerts
    
    # Last three alerts should remain
    assert alert_ids[2] in interface.alerts
    assert alert_ids[3] in interface.alerts
    assert alert_ids[4] in interface.alerts


@pytest.mark.asyncio
async def test_monitoring_interface_get_monitoring_data(mock_orchestrator):
    """Test getting monitoring data."""
    interface = MonitoringInterface(mock_orchestrator)
    
    # Create component and alert
    component_id = await interface.create_component(
        title="Test Component",
        visualization_type=VisualizationType.TIMELINE,
        data_source="test_data"
    )
    
    alert_id = await interface.create_alert(
        title="Test Alert",
        message="Test message",
        severity="info"
    )
    
    # Get monitoring data
    data = await interface.get_monitoring_data()
    
    assert "components" in data
    assert "alerts" in data
    assert "monitoring_data" in data
    assert "statistics" in data
    
    # Check component data
    assert component_id in data["components"]
    component_data = data["components"][component_id]
    assert component_data["title"] == "Test Component"
    assert component_data["type"] == "timeline"
    
    # Check alert data
    assert alert_id in data["alerts"]
    alert_data = data["alerts"][alert_id]
    assert alert_data["title"] == "Test Alert"
    assert alert_data["severity"] == "info"
    
    # Check statistics
    stats = data["statistics"]
    assert stats["total_components"] == 1
    assert stats["active_alerts"] == 1


@pytest.mark.asyncio
async def test_monitoring_interface_data_collection_tasks(mock_orchestrator):
    """Test that data collection tasks are started."""
    interface = MonitoringInterface(mock_orchestrator)
    
    # Mock the data collection methods
    with patch.object(interface, '_collect_agent_network_data') as mock_network, \
         patch.object(interface, '_collect_system_metrics_data') as mock_metrics, \
         patch.object(interface, '_collect_agent_activities_data') as mock_activities:
        
        await interface._start_data_collectors()
        
        # Check that data collectors were created
        assert "agent_network" in interface.data_collectors
        assert "system_metrics" in interface.data_collectors
        assert "agent_activities" in interface.data_collectors
        
        # Check that tasks are running
        assert not interface.data_collectors["agent_network"].done()
        assert not interface.data_collectors["system_metrics"].done()
        assert not interface.data_collectors["agent_activities"].done()
        
        # Cancel tasks for cleanup
        for task in interface.data_collectors.values():
            task.cancel()


@pytest.mark.asyncio
async def test_visualization_types():
    """Test visualization type enumeration."""
    assert VisualizationType.NETWORK_GRAPH.value == "network_graph"
    assert VisualizationType.TIMELINE.value == "timeline"
    assert VisualizationType.METRICS_CHART.value == "metrics_chart"
    assert VisualizationType.HEATMAP.value == "heatmap"
    assert VisualizationType.TREE_VIEW.value == "tree_view"
    assert VisualizationType.FLOW_DIAGRAM.value == "flow_diagram"


if __name__ == "__main__":
    pytest.main([__file__])