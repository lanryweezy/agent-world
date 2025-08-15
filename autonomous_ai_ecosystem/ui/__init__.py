"""
User interface module for the autonomous AI ecosystem.

This module provides web-based dashboard, real-time visualization,
and controls for human intervention and system management.
"""

from .dashboard import (
    EcosystemDashboard,
    DashboardConfig
)

from .monitoring_ui import (
    MonitoringInterface,
    VisualizationComponent
)

__all__ = [
    "EcosystemDashboard",
    "DashboardConfig",
    "MonitoringInterface",
    "VisualizationComponent"
]