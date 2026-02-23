"""
Real-time monitoring interface and visualization components.

This module provides real-time visualization of agent activities,
relationships, and system metrics with interactive controls.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class VisualizationType(Enum):
    """Types of visualizations available."""
    NETWORK_GRAPH = "network_graph"
    TIMELINE = "timeline"
    METRICS_CHART = "metrics_chart"
    HEATMAP = "heatmap"
    TREE_VIEW = "tree_view"
    FLOW_DIAGRAM = "flow_diagram"


@dataclass
class VisualizationComponent:
    """Represents a visualization component."""
    component_id: str
    title: str
    visualization_type: VisualizationType
    
    # Configuration
    width: int = 800
    height: int = 600
    refresh_interval: int = 5  # seconds
    
    # Data source
    data_source: str = ""
    filters: Dict[str, Any] = field(default_factory=dict)
    
    # Display options
    show_legend: bool = True
    show_toolbar: bool = True
    interactive: bool = True
    
    # Styling
    theme: str = "dark"
    color_scheme: List[str] = field(default_factory=lambda: ["#007bff", "#28a745", "#ffc107", "#dc3545"])
    
    # State
    last_updated: Optional[datetime] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringAlert:
    """Represents a monitoring alert."""
    alert_id: str
    title: str
    message: str
    severity: str  # info, warning, error, critical
    
    # Context
    source: str = ""
    agent_id: Optional[str] = None
    system_component: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # Status
    acknowledged: bool = False
    resolved: bool = False
    
    # Actions
    suggested_actions: List[str] = field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if alert has expired."""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False


class MonitoringInterface(AgentModule):
    """
    Real-time monitoring interface with visualization components.
    
    Provides interactive visualization of agent activities, relationships,
    and system metrics with real-time updates and controls.
    """
    
    def __init__(self, orchestrator, agent_id: str = "monitoring_interface"):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "monitoring_ui")
        
        self.orchestrator = orchestrator
        
        # Visualization components
        self.components: Dict[str, VisualizationComponent] = {}
        self.alerts: Dict[str, MonitoringAlert] = {}
        
        # Data collectors
        self.data_collectors: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self.config = {
            "update_interval": 5,
            "max_data_points": 1000,
            "alert_retention_hours": 24,
            "enable_real_time": True,
            "max_alerts": 100
        }
        
        # Monitoring data
        self.monitoring_data = {
            "agent_network": {
                "nodes": [],
                "edges": [],
                "last_updated": None
            },
            "system_metrics": {
                "timestamps": [],
                "cpu_usage": [],
                "memory_usage": [],
                "network_traffic": [],
                "agent_count": [],
                "task_count": []
            },
            "agent_activities": [],
            "communication_flows": [],
            "performance_metrics": {}
        }
        
        # Statistics
        self.stats = {
            "total_components": 0,
            "active_alerts": 0,
            "data_updates": 0,
            "visualization_renders": 0
        }
        
        # Counters
        self.component_counter = 0
        self.alert_counter = 0
        
        self.logger.info("Monitoring interface initialized")
    
    async def initialize(self) -> None:
        """Initialize the monitoring interface."""
        try:
            # Create default visualization components
            await self._create_default_components()
            
            # Start data collection tasks
            await self._start_data_collectors()
            
            # Start background tasks
            asyncio.create_task(self._monitoring_loop())
            asyncio.create_task(self._alert_cleanup_loop())
            
            self.logger.info("Monitoring interface initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring interface: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the monitoring interface."""
        try:
            # Cancel data collectors
            for task in self.data_collectors.values():
                task.cancel()
            
            # Wait for tasks to complete
            if self.data_collectors:
                await asyncio.gather(*self.data_collectors.values(), return_exceptions=True)
            
            self.logger.info("Monitoring interface shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during monitoring interface shutdown: {e}")
    
    async def create_component(
        self,
        title: str,
        visualization_type: VisualizationType,
        data_source: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new visualization component."""
        try:
            self.component_counter += 1
            component_id = f"comp_{self.component_counter}_{datetime.now().timestamp()}"
            
            component = VisualizationComponent(
                component_id=component_id,
                title=title,
                visualization_type=visualization_type,
                data_source=data_source
            )
            
            # Apply configuration
            if config:
                for key, value in config.items():
                    if hasattr(component, key):
                        setattr(component, key, value)
            
            # Store component
            self.components[component_id] = component
            
            # Start data collection for this component
            await self._start_component_data_collection(component)
            
            # Update statistics
            self.stats["total_components"] += 1
            
            log_agent_event(
                self.agent_id,
                "visualization_component_created",
                {
                    "component_id": component_id,
                    "title": title,
                    "type": visualization_type.value,
                    "data_source": data_source
                }
            )
            
            self.logger.info(f"Visualization component created: {title}")
            
            return component_id
            
        except Exception as e:
            self.logger.error(f"Failed to create visualization component: {e}")
            return ""
    
    async def update_component_data(self, component_id: str, data: Dict[str, Any]) -> bool:
        """Update data for a visualization component."""
        try:
            if component_id not in self.components:
                return False
            
            component = self.components[component_id]
            component.data = data
            component.last_updated = datetime.now()
            
            self.stats["data_updates"] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update component data: {e}")
            return False
    
    async def create_alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
        source: str = "",
        agent_id: Optional[str] = None,
        expires_in_minutes: Optional[int] = None,
        suggested_actions: Optional[List[str]] = None
    ) -> str:
        """Create a monitoring alert."""
        try:
            self.alert_counter += 1
            alert_id = f"alert_{self.alert_counter}_{datetime.now().timestamp()}"
            
            alert = MonitoringAlert(
                alert_id=alert_id,
                title=title,
                message=message,
                severity=severity,
                source=source,
                agent_id=agent_id,
                suggested_actions=suggested_actions or []
            )
            
            # Set expiration if specified
            if expires_in_minutes:
                alert.expires_at = datetime.now() + timedelta(minutes=expires_in_minutes)
            
            # Store alert
            self.alerts[alert_id] = alert
            
            # Limit number of alerts
            if len(self.alerts) > self.config["max_alerts"]:
                # Remove oldest alerts
                oldest_alerts = sorted(
                    self.alerts.items(),
                    key=lambda x: x[1].created_at
                )
                for old_alert_id, _ in oldest_alerts[:-self.config["max_alerts"]]:
                    del self.alerts[old_alert_id]
            
            # Update statistics
            self.stats["active_alerts"] = len([
                alert for alert in self.alerts.values()
                if not alert.resolved and not alert.is_expired()
            ])
            
            log_agent_event(
                agent_id or self.agent_id,
                "monitoring_alert_created",
                {
                    "alert_id": alert_id,
                    "title": title,
                    "severity": severity,
                    "source": source
                }
            )
            
            self.logger.info(f"Monitoring alert created: {title} ({severity})")
            
            return alert_id
            
        except Exception as e:
            self.logger.error(f"Failed to create alert: {e}")
            return ""
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        try:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            alert.acknowledged = True
            
            log_agent_event(
                alert.agent_id or self.agent_id,
                "alert_acknowledged",
                {"alert_id": alert_id}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        try:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            alert.resolved = True
            
            # Update statistics
            self.stats["active_alerts"] = len([
                alert for alert in self.alerts.values()
                if not alert.resolved and not alert.is_expired()
            ])
            
            log_agent_event(
                alert.agent_id or self.agent_id,
                "alert_resolved",
                {"alert_id": alert_id}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resolve alert: {e}")
            return False
    
    async def get_monitoring_data(self) -> Dict[str, Any]:
        """Get current monitoring data."""
        try:
            return {
                "components": {
                    comp_id: {
                        "title": comp.title,
                        "type": comp.visualization_type.value,
                        "data": comp.data,
                        "last_updated": comp.last_updated.isoformat() if comp.last_updated else None,
                        "config": {
                            "width": comp.width,
                            "height": comp.height,
                            "theme": comp.theme,
                            "interactive": comp.interactive
                        }
                    }
                    for comp_id, comp in self.components.items()
                },
                "alerts": {
                    alert_id: {
                        "title": alert.title,
                        "message": alert.message,
                        "severity": alert.severity,
                        "source": alert.source,
                        "agent_id": alert.agent_id,
                        "created_at": alert.created_at.isoformat(),
                        "acknowledged": alert.acknowledged,
                        "resolved": alert.resolved,
                        "suggested_actions": alert.suggested_actions
                    }
                    for alert_id, alert in self.alerts.items()
                    if not alert.is_expired()
                },
                "monitoring_data": self.monitoring_data,
                "statistics": self.stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get monitoring data: {e}")
            return {}
    
    async def _create_default_components(self) -> None:
        """Create default visualization components."""
        try:
            # Agent network graph
            await self.create_component(
                title="Agent Network",
                visualization_type=VisualizationType.NETWORK_GRAPH,
                data_source="agent_network",
                config={
                    "width": 800,
                    "height": 600,
                    "interactive": True
                }
            )
            
            # System metrics chart
            await self.create_component(
                title="System Metrics",
                visualization_type=VisualizationType.METRICS_CHART,
                data_source="system_metrics",
                config={
                    "width": 800,
                    "height": 400,
                    "show_legend": True
                }
            )
            
            # Agent activity timeline
            await self.create_component(
                title="Agent Activities",
                visualization_type=VisualizationType.TIMELINE,
                data_source="agent_activities",
                config={
                    "width": 1000,
                    "height": 300
                }
            )
            
            # Communication flow diagram
            await self.create_component(
                title="Communication Flows",
                visualization_type=VisualizationType.FLOW_DIAGRAM,
                data_source="communication_flows",
                config={
                    "width": 600,
                    "height": 500
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create default components: {e}")
    
    async def _start_data_collectors(self) -> None:
        """Start data collection tasks."""
        try:
            # Agent network data collector
            self.data_collectors["agent_network"] = asyncio.create_task(
                self._collect_agent_network_data()
            )
            
            # System metrics data collector
            self.data_collectors["system_metrics"] = asyncio.create_task(
                self._collect_system_metrics_data()
            )
            
            # Agent activities data collector
            self.data_collectors["agent_activities"] = asyncio.create_task(
                self._collect_agent_activities_data()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to start data collectors: {e}")
    
    async def _start_component_data_collection(self, component: VisualizationComponent) -> None:
        """Start data collection for a specific component."""
        try:
            # This would start a task to collect data for the specific component
            # Implementation depends on the data source and visualization type
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to start component data collection: {e}")
    
    async def _collect_agent_network_data(self) -> None:
        """Collect agent network data."""
        while True:
            try:
                await asyncio.sleep(self.config["update_interval"])
                
                # Get agent statuses
                if self.orchestrator.agent_manager:
                    agents = await self.orchestrator.agent_manager.get_all_agents_status()
                    
                    # Create network nodes
                    nodes = []
                    for agent in agents:
                        nodes.append({
                            "id": agent["agent_id"],
                            "label": agent["agent_id"],
                            "status": agent["status"],
                            "uptime": agent.get("uptime_seconds", 0),
                            "cpu_usage": agent.get("cpu_usage", 0),
                            "memory_usage": agent.get("memory_usage_mb", 0)
                        })
                    
                    # Create network edges (simplified - would need actual communication data)
                    edges = []
                    
                    # Update monitoring data
                    self.monitoring_data["agent_network"] = {
                        "nodes": nodes,
                        "edges": edges,
                        "last_updated": datetime.now().isoformat()
                    }
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error collecting agent network data: {e}")
    
    async def _collect_system_metrics_data(self) -> None:
        """Collect system metrics data."""
        while True:
            try:
                await asyncio.sleep(self.config["update_interval"])
                
                # Get system status
                if self.orchestrator:
                    status = await self.orchestrator.get_system_status()
                    
                    current_time = datetime.now()
                    
                    # Add data points
                    self.monitoring_data["system_metrics"]["timestamps"].append(
                        current_time.isoformat()
                    )
                    
                    # Add sample metrics (would be real data in production)
                    self.monitoring_data["system_metrics"]["cpu_usage"].append(
                        status.get("statistics", {}).get("running_systems", 0) * 10
                    )
                    
                    self.monitoring_data["system_metrics"]["memory_usage"].append(
                        status.get("statistics", {}).get("total_systems", 0) * 5
                    )
                    
                    self.monitoring_data["system_metrics"]["agent_count"].append(
                        status.get("statistics", {}).get("total_agents", 0)
                    )
                    
                    # Keep only recent data
                    max_points = self.config["max_data_points"]
                    for key in self.monitoring_data["system_metrics"]:
                        if len(self.monitoring_data["system_metrics"][key]) > max_points:
                            self.monitoring_data["system_metrics"][key] = \
                                self.monitoring_data["system_metrics"][key][-max_points:]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error collecting system metrics data: {e}")
    
    async def _collect_agent_activities_data(self) -> None:
        """Collect agent activities data."""
        while True:
            try:
                await asyncio.sleep(self.config["update_interval"])
                
                # Add sample activity (would be real activity data in production)
                activity = {
                    "timestamp": datetime.now().isoformat(),
                    "agent_id": "sample_agent",
                    "activity": "status_update",
                    "details": "Agent status updated"
                }
                
                self.monitoring_data["agent_activities"].append(activity)
                
                # Keep only recent activities
                max_activities = 100
                if len(self.monitoring_data["agent_activities"]) > max_activities:
                    self.monitoring_data["agent_activities"] = \
                        self.monitoring_data["agent_activities"][-max_activities:]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error collecting agent activities data: {e}")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.config["update_interval"])
                
                # Update component data
                for component in self.components.values():
                    if component.data_source in self.monitoring_data:
                        await self.update_component_data(
                            component.component_id,
                            self.monitoring_data[component.data_source]
                        )
                
                self.stats["visualization_renders"] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
    
    async def _alert_cleanup_loop(self) -> None:
        """Clean up expired and old alerts."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                current_time = datetime.now()
                expired_alerts = []
                
                for alert_id, alert in self.alerts.items():
                    # Remove expired alerts
                    if alert.is_expired():
                        expired_alerts.append(alert_id)
                    # Remove old resolved alerts
                    elif (alert.resolved and 
                          (current_time - alert.created_at).total_seconds() > 
                          self.config["alert_retention_hours"] * 3600):
                        expired_alerts.append(alert_id)
                
                # Remove expired alerts
                for alert_id in expired_alerts:
                    del self.alerts[alert_id]
                
                # Update statistics
                self.stats["active_alerts"] = len([
                    alert for alert in self.alerts.values()
                    if not alert.resolved and not alert.is_expired()
                ])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in alert cleanup loop: {e}")