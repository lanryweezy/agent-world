"""
Monitoring and reporting system for the autonomous AI ecosystem.

This module implements comprehensive activity logging, automated report
generation, and alert systems for human oversight and intervention.
"""

import asyncio
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ActivityType(Enum):
    """Types of activities to monitor."""
    AGENT_COMMUNICATION = "agent_communication"
    TASK_EXECUTION = "task_execution"
    LEARNING_ACTIVITY = "learning_activity"
    REPRODUCTION_EVENT = "reproduction_event"
    ECONOMIC_TRANSACTION = "economic_transaction"
    WORLD_INTERACTION = "world_interaction"
    HUMAN_INTERACTION = "human_interaction"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"
    PERFORMANCE_METRIC = "performance_metric"


class ReportType(Enum):
    """Types of reports that can be generated."""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_OVERVIEW = "weekly_overview"
    PERFORMANCE_REPORT = "performance_report"
    INCIDENT_REPORT = "incident_report"
    AGENT_ACTIVITY = "agent_activity"
    SYSTEM_HEALTH = "system_health"
    ECONOMIC_SUMMARY = "economic_summary"
    LEARNING_PROGRESS = "learning_progress"


@dataclass
class ActivityLog:
    """Represents a logged activity in the system."""
    log_id: str
    activity_type: ActivityType
    agent_id: str
    
    # Activity details
    title: str
    description: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Timing and context
    timestamp: datetime = field(default_factory=datetime.now)
    duration: Optional[float] = None  # Duration in seconds
    location: Optional[str] = None
    
    # Categorization
    tags: List[str] = field(default_factory=list)
    severity: AlertLevel = AlertLevel.INFO
    
    # Relationships
    related_agents: List[str] = field(default_factory=list)
    parent_activity_id: Optional[str] = None
    child_activity_ids: List[str] = field(default_factory=list)
    
    # Metrics
    success: bool = True
    performance_score: float = 1.0
    resource_usage: Dict[str, float] = field(default_factory=dict)


@dataclass
class SystemAlert:
    """Represents a system alert requiring attention."""
    alert_id: str
    alert_level: AlertLevel
    title: str
    description: str
    
    # Alert context
    source_component: str
    affected_agents: List[str] = field(default_factory=list)
    related_activities: List[str] = field(default_factory=list)  # activity_log_ids
    
    # Status and resolution
    status: str = "open"  # open, acknowledged, investigating, resolved, dismissed
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Human interaction
    acknowledged_by: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: str = ""
    
    # Alert data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_age_hours(self) -> float:
        """Get alert age in hours."""
        return (datetime.now() - self.created_at).total_seconds() / 3600.0
    
    def is_stale(self, stale_threshold_hours: float = 24.0) -> bool:
        """Check if alert is stale."""
        return self.get_age_hours() > stale_threshold_hours and self.status == "open"


@dataclass
class PerformanceMetrics:
    """System performance metrics."""
    metric_id: str
    component: str
    metric_name: str
    value: float
    unit: str
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    collection_interval: float = 60.0  # seconds
    
    # Thresholds
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    
    # Historical data
    historical_values: List[Tuple[datetime, float]] = field(default_factory=list)
    
    def add_historical_value(self, value: float, timestamp: Optional[datetime] = None) -> None:
        """Add a historical value."""
        ts = timestamp or datetime.now()
        self.historical_values.append((ts, value))
        
        # Limit historical data (keep last 1000 points)
        if len(self.historical_values) > 1000:
            self.historical_values = self.historical_values[-1000:]
    
    def get_trend(self, hours_back: float = 24.0) -> str:
        """Get trend direction over specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        recent_values = [value for ts, value in self.historical_values if ts >= cutoff_time]
        
        if len(recent_values) < 2:
            return "insufficient_data"
        
        # Simple trend calculation
        first_half = recent_values[:len(recent_values)//2]
        second_half = recent_values[len(recent_values)//2:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        if avg_second > avg_first * 1.1:
            return "increasing"
        elif avg_second < avg_first * 0.9:
            return "decreasing"
        else:
            return "stable"


@dataclass
class InterventionRequest:
    """Request for human intervention."""
    request_id: str
    requesting_agent_id: str
    intervention_type: str  # guidance, decision, approval, emergency
    
    # Request details
    title: str
    description: str
    urgency: AlertLevel
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    status: str = "pending"  # pending, reviewed, approved, denied, escalated
    created_at: datetime = field(default_factory=datetime.now)
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None
    
    # Response
    human_response: str = ""
    approved: bool = False
    
    def get_age_hours(self) -> float:
        """Get request age in hours."""
        return (datetime.now() - self.created_at).total_seconds() / 3600.0


class OversightMonitor(AgentModule):
    """
    Comprehensive monitoring and reporting system for autonomous AI oversight.
    
    Provides activity logging, automated report generation, alert systems,
    and intervention request handling for human oversight.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "oversight_monitor")
        
        # Core data structures
        self.activity_logs: Dict[str, ActivityLog] = {}
        self.system_alerts: Dict[str, SystemAlert] = {}
        self.performance_metrics: Dict[str, PerformanceMetrics] = {}
        self.intervention_requests: Dict[str, InterventionRequest] = {}
        
        # Monitoring configuration
        self.config = {
            "log_retention_days": 30,
            "alert_retention_days": 90,
            "performance_retention_days": 7,
            "report_generation_interval_hours": 24,
            "alert_check_interval_minutes": 5,
            "performance_collection_interval_seconds": 60,
            "auto_alert_thresholds": {
                "error_rate": 0.05,  # 5% error rate triggers alert
                "response_time": 10.0,  # 10 second response time
                "memory_usage": 0.9,  # 90% memory usage
                "agent_failure_rate": 0.1  # 10% agent failure rate
            },
            "critical_alert_escalation_minutes": 30,
            "max_logs_per_hour": 10000
        }
        
        # Report templates
        self.report_templates = {
            ReportType.DAILY_SUMMARY: {
                "sections": ["system_overview", "agent_activity", "alerts", "performance"],
                "metrics": ["total_activities", "error_count", "performance_summary"]
            },
            ReportType.SYSTEM_HEALTH: {
                "sections": ["system_status", "resource_usage", "error_analysis", "recommendations"],
                "metrics": ["uptime", "error_rate", "resource_utilization", "agent_health"]
            },
            ReportType.PERFORMANCE_REPORT: {
                "sections": ["performance_overview", "trends", "bottlenecks", "optimization_suggestions"],
                "metrics": ["response_times", "throughput", "resource_efficiency", "quality_scores"]
            }
        }
        
        # Statistics
        self.stats = {
            "total_logs": 0,
            "total_alerts": 0,
            "total_reports": 0,
            "critical_alerts": 0,
            "intervention_requests": 0,
            "logs_by_type": {activity_type.value: 0 for activity_type in ActivityType},
            "alerts_by_level": {level.value: 0 for level in AlertLevel}
        }
        
        # Counters
        self.log_counter = 0
        self.alert_counter = 0
        self.report_counter = 0
        self.intervention_counter = 0
        
        # Background tasks
        self.log_queue = asyncio.Queue()
        self.alert_queue = asyncio.Queue()
        
        self.logger.info("Oversight monitor initialized")
    
    async def initialize(self) -> None:
        """Initialize the monitoring system."""
        try:
            # Start background processes
            asyncio.create_task(self._log_processor())
            asyncio.create_task(self._alert_processor())
            asyncio.create_task(self._performance_collector())
            asyncio.create_task(self._report_generator())
            asyncio.create_task(self._cleanup_processor())
            
            # Initialize performance metrics
            await self._initialize_performance_metrics()
            
            self.logger.info("Oversight monitor initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize oversight monitor: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the monitoring system."""
        try:
            # Process remaining logs and alerts
            while not self.log_queue.empty() or not self.alert_queue.empty():
                await asyncio.sleep(0.1)
            
            # Generate final report
            await self._generate_shutdown_report()
            
            # Save monitoring state
            await self._save_monitoring_state()
            
            self.logger.info("Oversight monitor shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during oversight monitor shutdown: {e}")
    
    async def log_activity(
        self,
        activity_type: ActivityType,
        agent_id: str,
        title: str,
        description: str,
        data: Optional[Dict[str, Any]] = None,
        severity: AlertLevel = AlertLevel.INFO,
        duration: Optional[float] = None,
        related_agents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Log an activity in the system."""
        try:
            # Check rate limiting
            current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
            recent_logs = [log for log in self.activity_logs.values() 
                          if log.timestamp >= current_hour and log.timestamp < current_hour + timedelta(hours=1)]
            
            if len(recent_logs) >= self.config["max_logs_per_hour"]:
                return {"success": False, "error": "Rate limit exceeded"}
            
            # Create activity log
            self.log_counter += 1
            log_id = f"log_{self.log_counter}_{datetime.now().timestamp()}"
            
            activity_log = ActivityLog(
                log_id=log_id,
                activity_type=activity_type,
                agent_id=agent_id,
                title=title,
                description=description,
                data=data or {},
                severity=severity,
                duration=duration,
                related_agents=related_agents or []
            )
            
            # Queue for processing
            await self.log_queue.put(log_id)
            self.activity_logs[log_id] = activity_log
            
            # Update statistics
            self.stats["total_logs"] += 1
            self.stats["logs_by_type"][activity_type.value] += 1
            
            # Create alert if severity is high
            if severity in [AlertLevel.ERROR, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                await self._create_alert_from_activity(activity_log)
            
            result = {
                "success": True,
                "log_id": log_id,
                "severity": severity.value,
                "alert_created": severity in [AlertLevel.ERROR, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to log activity: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_alert(
        self,
        alert_level: AlertLevel,
        title: str,
        description: str,
        source_component: str,
        affected_agents: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a system alert."""
        try:
            self.alert_counter += 1
            alert_id = f"alert_{self.alert_counter}_{datetime.now().timestamp()}"
            
            alert = SystemAlert(
                alert_id=alert_id,
                alert_level=alert_level,
                title=title,
                description=description,
                source_component=source_component,
                affected_agents=affected_agents or [],
                metadata=metadata or {}
            )
            
            self.system_alerts[alert_id] = alert
            
            # Queue for processing
            await self.alert_queue.put(alert_id)
            
            # Update statistics
            self.stats["total_alerts"] += 1
            self.stats["alerts_by_level"][alert_level.value] += 1
            
            if alert_level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                self.stats["critical_alerts"] += 1
            
            log_agent_event(
                self.agent_id,
                "alert_created",
                {
                    "alert_id": alert_id,
                    "alert_level": alert_level.value,
                    "title": title,
                    "source_component": source_component
                }
            )
            
            result = {
                "success": True,
                "alert_id": alert_id,
                "alert_level": alert_level.value,
                "requires_immediate_attention": alert_level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
            }
            
            self.logger.info(f"Alert created: {title} ({alert_level.value})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create alert: {e}")
            return {"success": False, "error": str(e)}
    
    async def request_human_intervention(
        self,
        requesting_agent_id: str,
        intervention_type: str,
        title: str,
        description: str,
        urgency: AlertLevel = AlertLevel.WARNING,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Request human intervention."""
        try:
            self.intervention_counter += 1
            request_id = f"intervention_{self.intervention_counter}_{datetime.now().timestamp()}"
            
            request = InterventionRequest(
                request_id=request_id,
                requesting_agent_id=requesting_agent_id,
                intervention_type=intervention_type,
                title=title,
                description=description,
                urgency=urgency,
                context=context or {}
            )
            
            self.intervention_requests[request_id] = request
            
            # Create corresponding alert
            await self.create_alert(
                alert_level=urgency,
                title=f"Intervention Request: {title}",
                description=f"Agent {requesting_agent_id} requests {intervention_type}: {description}",
                source_component="intervention_system",
                affected_agents=[requesting_agent_id],
                metadata={"intervention_request_id": request_id}
            )
            
            # Update statistics
            self.stats["intervention_requests"] += 1
            
            log_agent_event(
                self.agent_id,
                "intervention_requested",
                {
                    "request_id": request_id,
                    "requesting_agent": requesting_agent_id,
                    "intervention_type": intervention_type,
                    "urgency": urgency.value
                }
            )
            
            result = {
                "success": True,
                "request_id": request_id,
                "status": request.status,
                "urgency": urgency.value,
                "estimated_response_time": await self._estimate_intervention_response_time(urgency)
            }
            
            self.logger.info(f"Intervention requested: {title} by {requesting_agent_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to request intervention: {e}")
            return {"success": False, "error": str(e)}
    
    async def generate_report(
        self,
        report_type: ReportType,
        time_range_hours: float = 24.0,
        include_details: bool = True
    ) -> Dict[str, Any]:
        """Generate a system report."""
        try:
            self.report_counter += 1
            report_id = f"report_{self.report_counter}_{datetime.now().timestamp()}"
            
            cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
            
            # Get data for report
            recent_logs = [log for log in self.activity_logs.values() if log.timestamp >= cutoff_time]
            recent_alerts = [alert for alert in self.system_alerts.values() if alert.created_at >= cutoff_time]
            
            # Generate report based on type
            if report_type == ReportType.DAILY_SUMMARY:
                report_content = await self._generate_daily_summary(recent_logs, recent_alerts, time_range_hours)
            elif report_type == ReportType.SYSTEM_HEALTH:
                report_content = await self._generate_system_health_report(recent_logs, recent_alerts)
            elif report_type == ReportType.PERFORMANCE_REPORT:
                report_content = await self._generate_performance_report(time_range_hours)
            elif report_type == ReportType.INCIDENT_REPORT:
                report_content = await self._generate_incident_report(recent_alerts)
            else:
                report_content = await self._generate_generic_report(recent_logs, recent_alerts, report_type)
            
            # Add report metadata
            report = {
                "report_id": report_id,
                "report_type": report_type.value,
                "generated_at": datetime.now().isoformat(),
                "time_range_hours": time_range_hours,
                "data_points": len(recent_logs),
                "alerts_included": len(recent_alerts),
                "content": report_content
            }
            
            # Update statistics
            self.stats["total_reports"] += 1
            
            log_agent_event(
                self.agent_id,
                "report_generated",
                {
                    "report_id": report_id,
                    "report_type": report_type.value,
                    "time_range_hours": time_range_hours,
                    "data_points": len(recent_logs)
                }
            )
            
            self.logger.info(f"Report generated: {report_type.value} ({report_id})")
            
            return {"success": True, "report": report}
            
        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")
            return {"success": False, "error": str(e)}
    
    def get_recent_activities(
        self,
        hours_back: float = 24.0,
        activity_type: Optional[ActivityType] = None,
        agent_id: Optional[str] = None,
        severity: Optional[AlertLevel] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent activities with filtering."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            # Filter activities
            filtered_logs = []
            for log in self.activity_logs.values():
                if log.timestamp < cutoff_time:
                    continue
                
                if activity_type and log.activity_type != activity_type:
                    continue
                
                if agent_id and log.agent_id != agent_id:
                    continue
                
                if severity and log.severity != severity:
                    continue
                
                filtered_logs.append(log)
            
            # Sort by timestamp (most recent first)
            filtered_logs.sort(key=lambda l: l.timestamp, reverse=True)
            
            # Format for output
            activities = []
            for log in filtered_logs[:limit]:
                activity = {
                    "log_id": log.log_id,
                    "activity_type": log.activity_type.value,
                    "agent_id": log.agent_id,
                    "title": log.title,
                    "description": log.description,
                    "timestamp": log.timestamp.isoformat(),
                    "severity": log.severity.value,
                    "success": log.success,
                    "performance_score": log.performance_score,
                    "duration": log.duration,
                    "related_agents": log.related_agents,
                    "tags": log.tags
                }
                
                activities.append(activity)
            
            return activities
            
        except Exception as e:
            self.logger.error(f"Failed to get recent activities: {e}")
            return []
    
    def get_active_alerts(self, alert_level: Optional[AlertLevel] = None) -> List[Dict[str, Any]]:
        """Get active system alerts."""
        try:
            active_alerts = []
            
            for alert in self.system_alerts.values():
                if alert.status not in ["open", "acknowledged", "investigating"]:
                    continue
                
                if alert_level and alert.alert_level != alert_level:
                    continue
                
                alert_info = {
                    "alert_id": alert.alert_id,
                    "alert_level": alert.alert_level.value,
                    "title": alert.title,
                    "description": alert.description,
                    "source_component": alert.source_component,
                    "status": alert.status,
                    "created_at": alert.created_at.isoformat(),
                    "age_hours": alert.get_age_hours(),
                    "affected_agents": alert.affected_agents,
                    "acknowledged_by": alert.acknowledged_by,
                    "assigned_to": alert.assigned_to,
                    "is_stale": alert.is_stale()
                }
                
                active_alerts.append(alert_info)
            
            # Sort by alert level and creation time
            level_priority = {
                AlertLevel.EMERGENCY: 5,
                AlertLevel.CRITICAL: 4,
                AlertLevel.ERROR: 3,
                AlertLevel.WARNING: 2,
                AlertLevel.INFO: 1
            }
            
            active_alerts.sort(
                key=lambda a: (level_priority.get(AlertLevel(a["alert_level"]), 0), a["created_at"]),
                reverse=True
            )
            
            return active_alerts
            
        except Exception as e:
            self.logger.error(f"Failed to get active alerts: {e}")
            return []"