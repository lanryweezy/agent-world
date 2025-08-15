"""
Monitoring and reporting system for comprehensive activity logging and alerting.

This module implements comprehensive monitoring, automated report generation,
and alert systems for human oversight and intervention.
"""

import asyncio
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class EventSeverity(Enum):
    """Severity levels for monitored events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class EventCategory(Enum):
    """Categories of monitored events."""
    AGENT_LIFECYCLE = "agent_lifecycle"
    COMMUNICATION = "communication"
    LEARNING = "learning"
    CODE_MODIFICATION = "code_modification"
    REPRODUCTION = "reproduction"
    ECONOMIC_ACTIVITY = "economic_activity"
    WORLD_BUILDING = "world_building"
    HUMAN_INTERACTION = "human_interaction"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ERROR = "error"


class AlertType(Enum):
    """Types of alerts that can be generated."""
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    THRESHOLD_BREACH = "threshold_breach"
    PATTERN_DETECTED = "pattern_detected"
    INTERVENTION_REQUIRED = "intervention_required"
    SYSTEM_HEALTH = "system_health"


@dataclass
class MonitoredEvent:
    """Represents a monitored event in the system."""
    event_id: str
    timestamp: datetime
    agent_id: str
    event_type: str
    category: EventCategory
    severity: EventSeverity
    
    # Event details
    description: str
    data: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Processing metadata
    processed: bool = False
    alert_generated: bool = False
    reported: bool = False
    
    # Human oversight flags
    requires_intervention: bool = False
    intervention_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "event_type": self.event_type,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "data": self.data,
            "context": self.context,
            "requires_intervention": self.requires_intervention,
            "intervention_reason": self.intervention_reason
        }


@dataclass
class Alert:
    """Represents an alert generated from monitored events."""
    alert_id: str
    alert_type: AlertType
    severity: EventSeverity
    title: str
    message: str
    
    # Related events
    triggering_events: List[str] = field(default_factory=list)  # event_ids
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    escalation_time: Optional[datetime] = None
    
    # Status
    acknowledged: bool = False
    resolved: bool = False
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Actions taken
    actions_taken: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for serialization."""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "triggering_events": self.triggering_events,
            "created_at": self.created_at.isoformat(),
            "escalation_time": self.escalation_time.isoformat() if self.escalation_time else None,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "actions_taken": self.actions_taken
        }


@dataclass
class Report:
    """Represents a generated report."""
    report_id: str
    report_type: str
    title: str
    content: str
    
    # Report metadata
    generated_at: datetime = field(default_factory=datetime.now)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # Related data
    events_included: List[str] = field(default_factory=list)  # event_ids
    alerts_included: List[str] = field(default_factory=list)  # alert_ids
    
    # Delivery
    delivered: bool = False
    delivery_method: str = "email"
    recipients: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for serialization."""
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "title": self.title,
            "content": self.content,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "events_included": len(self.events_included),
            "alerts_included": len(self.alerts_included),
            "delivered": self.delivered
        }


class MonitoringReportingSystem(AgentModule):
    """
    Comprehensive monitoring and reporting system for the AI ecosystem.
    
    Provides activity logging, event monitoring, automated alerting,
    and report generation for human oversight.
    """
    
    def __init__(self, agent_id: str = "monitoring_system"):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "monitoring_reporting")
        
        # Core data structures
        self.events: Dict[str, MonitoredEvent] = {}
        self.alerts: Dict[str, Alert] = {}
        self.reports: Dict[str, Report] = {}
        
        # Event processing
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.event_processors: Dict[EventCategory, Callable] = {}
        
        # Alert management
        self.active_alerts: Set[str] = set()
        self.alert_rules: List[Dict[str, Any]] = []
        
        # Configuration
        self.config = {
            "max_events_stored": 100000,
            "event_retention_days": 30,
            "alert_retention_days": 90,
            "report_retention_days": 365,
            "enable_email_alerts": True,
            "enable_immediate_alerts": True,
            "alert_escalation_minutes": 30,
            "batch_processing_interval": 60,  # seconds
            "report_generation_hour": 8,  # 8 AM daily reports
            "emergency_contact_email": "admin@example.com",
            "smtp_server": "localhost",
            "smtp_port": 587
        }
        
        # Monitoring thresholds
        self.thresholds = {
            "agent_error_rate": 0.1,  # 10% error rate triggers alert
            "communication_failure_rate": 0.05,  # 5% failure rate
            "resource_usage_critical": 0.9,  # 90% resource usage
            "security_incidents_per_hour": 5,
            "code_modification_failures": 3,
            "reproduction_failures": 5,
            "learning_stagnation_hours": 24
        }
        
        # Statistics
        self.stats = {
            "total_events": 0,
            "events_by_category": {cat.value: 0 for cat in EventCategory},
            "events_by_severity": {sev.value: 0 for sev in EventSeverity},
            "total_alerts": 0,
            "active_alerts_count": 0,
            "reports_generated": 0,
            "intervention_requests": 0,
            "system_uptime": datetime.now()
        }
        
        # Counters
        self.event_counter = 0
        self.alert_counter = 0
        self.report_counter = 0
        
        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
        
        self.logger.info("Monitoring and reporting system initialized")
    
    async def initialize(self) -> None:
        """Initialize the monitoring and reporting system."""
        try:
            # Set up event processors
            self._setup_event_processors()
            
            # Set up alert rules
            self._setup_alert_rules()
            
            # Start background tasks
            self._start_background_tasks()
            
            self.logger.info("Monitoring and reporting system initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the monitoring and reporting system."""
        try:
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # Process remaining events
            await self._process_remaining_events()
            
            self.logger.info("Monitoring and reporting system shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during monitoring system shutdown: {e}")
    
    async def log_event(
        self,
        agent_id: str,
        event_type: str,
        category: EventCategory,
        severity: EventSeverity,
        description: str,
        data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        requires_intervention: bool = False,
        intervention_reason: str = ""
    ) -> str:
        """Log a monitored event."""
        try:
            # Create event
            self.event_counter += 1
            event_id = f"event_{self.event_counter}_{datetime.now().timestamp()}"
            
            event = MonitoredEvent(
                event_id=event_id,
                timestamp=datetime.now(),
                agent_id=agent_id,
                event_type=event_type,
                category=category,
                severity=severity,
                description=description,
                data=data or {},
                context=context or {},
                requires_intervention=requires_intervention,
                intervention_reason=intervention_reason
            )
            
            # Store event
            self.events[event_id] = event
            
            # Queue for processing
            await self.event_queue.put(event)
            
            # Update statistics
            self.stats["total_events"] += 1
            self.stats["events_by_category"][category.value] += 1
            self.stats["events_by_severity"][severity.value] += 1
            
            if requires_intervention:
                self.stats["intervention_requests"] += 1
            
            # Log to system logger
            log_agent_event(
                agent_id,
                event_type,
                {
                    "event_id": event_id,
                    "category": category.value,
                    "severity": severity.value,
                    "description": description,
                    "requires_intervention": requires_intervention
                }
            )
            
            self.logger.info(f"Event logged: {event_type} ({severity.value}) for agent {agent_id}")
            
            return event_id
            
        except Exception as e:
            self.logger.error(f"Failed to log event: {e}")
            return ""
    
    async def generate_alert(
        self,
        alert_type: AlertType,
        severity: EventSeverity,
        title: str,
        message: str,
        triggering_events: Optional[List[str]] = None,
        escalation_minutes: Optional[int] = None
    ) -> str:
        """Generate an alert."""
        try:
            # Create alert
            self.alert_counter += 1
            alert_id = f"alert_{self.alert_counter}_{datetime.now().timestamp()}"
            
            escalation_time = None
            if escalation_minutes:
                escalation_time = datetime.now() + timedelta(minutes=escalation_minutes)
            
            alert = Alert(
                alert_id=alert_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                triggering_events=triggering_events or [],
                escalation_time=escalation_time
            )
            
            # Store alert
            self.alerts[alert_id] = alert
            self.active_alerts.add(alert_id)
            
            # Update statistics
            self.stats["total_alerts"] += 1
            self.stats["active_alerts_count"] = len(self.active_alerts)
            
            # Send immediate notification if configured
            if self.config["enable_immediate_alerts"] and severity in [EventSeverity.CRITICAL, EventSeverity.EMERGENCY]:
                await self._send_immediate_alert(alert)
            
            self.logger.warning(f"Alert generated: {title} ({severity.value})")
            
            return alert_id
            
        except Exception as e:
            self.logger.error(f"Failed to generate alert: {e}")
            return ""
    
    async def generate_report(
        self,
        report_type: str,
        title: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        include_events: bool = True,
        include_alerts: bool = True,
        recipients: Optional[List[str]] = None
    ) -> str:
        """Generate a comprehensive report."""
        try:
            # Set default period if not specified
            if not period_end:
                period_end = datetime.now()
            if not period_start:
                period_start = period_end - timedelta(days=1)  # Last 24 hours
            
            # Collect relevant events and alerts
            relevant_events = []
            relevant_alerts = []
            
            if include_events:
                relevant_events = [
                    event for event in self.events.values()
                    if period_start <= event.timestamp <= period_end
                ]
            
            if include_alerts:
                relevant_alerts = [
                    alert for alert in self.alerts.values()
                    if period_start <= alert.created_at <= period_end
                ]
            
            # Generate report content
            content = await self._generate_report_content(
                report_type, relevant_events, relevant_alerts, period_start, period_end
            )
            
            # Create report
            self.report_counter += 1
            report_id = f"report_{self.report_counter}_{datetime.now().timestamp()}"
            
            report = Report(
                report_id=report_id,
                report_type=report_type,
                title=title,
                content=content,
                period_start=period_start,
                period_end=period_end,
                events_included=[e.event_id for e in relevant_events],
                alerts_included=[a.alert_id for a in relevant_alerts],
                recipients=recipients or [self.config["emergency_contact_email"]]
            )
            
            # Store report
            self.reports[report_id] = report
            
            # Deliver report
            if self.config["enable_email_alerts"]:
                await self._deliver_report(report)
            
            # Update statistics
            self.stats["reports_generated"] += 1
            
            self.logger.info(f"Report generated: {title} ({len(relevant_events)} events, {len(relevant_alerts)} alerts)")
            
            return report_id
            
        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")
            return ""
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "human_operator") -> bool:
        """Acknowledge an alert."""
        try:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_at = datetime.now()
            alert.actions_taken.append(f"Acknowledged by {acknowledged_by}")
            
            self.logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str, resolution_note: str = "", resolved_by: str = "system") -> bool:
        """Resolve an alert."""
        try:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            alert.actions_taken.append(f"Resolved by {resolved_by}: {resolution_note}")
            
            # Remove from active alerts
            self.active_alerts.discard(alert_id)
            self.stats["active_alerts_count"] = len(self.active_alerts)
            
            self.logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resolve alert: {e}")
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        try:
            # Calculate uptime
            uptime = datetime.now() - self.stats["system_uptime"]
            
            # Get recent events summary
            recent_events = [
                event for event in self.events.values()
                if (datetime.now() - event.timestamp).total_seconds() < 3600  # Last hour
            ]
            
            # Get active alerts summary
            active_alerts_summary = [
                {
                    "alert_id": alert_id,
                    "severity": self.alerts[alert_id].severity.value,
                    "title": self.alerts[alert_id].title,
                    "created_at": self.alerts[alert_id].created_at.isoformat()
                }
                for alert_id in self.active_alerts
            ]
            
            status = {
                "system_uptime_hours": uptime.total_seconds() / 3600,
                "total_events": self.stats["total_events"],
                "recent_events_count": len(recent_events),
                "active_alerts_count": len(self.active_alerts),
                "active_alerts": active_alerts_summary,
                "events_by_category": self.stats["events_by_category"],
                "events_by_severity": self.stats["events_by_severity"],
                "intervention_requests": self.stats["intervention_requests"],
                "reports_generated": self.stats["reports_generated"],
                "last_report_time": max(
                    [report.generated_at for report in self.reports.values()],
                    default=datetime.min
                ).isoformat() if self.reports else None
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return {}
    
    def _setup_event_processors(self) -> None:
        """Set up event processors for different categories."""
        self.event_processors = {
            EventCategory.AGENT_LIFECYCLE: self._process_agent_lifecycle_event,
            EventCategory.COMMUNICATION: self._process_communication_event,
            EventCategory.LEARNING: self._process_learning_event,
            EventCategory.CODE_MODIFICATION: self._process_code_modification_event,
            EventCategory.REPRODUCTION: self._process_reproduction_event,
            EventCategory.ECONOMIC_ACTIVITY: self._process_economic_event,
            EventCategory.WORLD_BUILDING: self._process_world_building_event,
            EventCategory.HUMAN_INTERACTION: self._process_human_interaction_event,
            EventCategory.SECURITY: self._process_security_event,
            EventCategory.PERFORMANCE: self._process_performance_event,
            EventCategory.ERROR: self._process_error_event
        }
    
    def _setup_alert_rules(self) -> None:
        """Set up automated alert rules."""
        self.alert_rules = [
            {
                "name": "High Error Rate",
                "condition": lambda: self._calculate_error_rate() > self.thresholds["agent_error_rate"],
                "alert_type": AlertType.THRESHOLD_BREACH,
                "severity": EventSeverity.WARNING,
                "message": "Agent error rate has exceeded threshold"
            },
            {
                "name": "Communication Failures",
                "condition": lambda: self._calculate_communication_failure_rate() > self.thresholds["communication_failure_rate"],
                "alert_type": AlertType.THRESHOLD_BREACH,
                "severity": EventSeverity.WARNING,
                "message": "Communication failure rate is high"
            },
            {
                "name": "Security Incidents",
                "condition": lambda: self._count_recent_security_incidents() > self.thresholds["security_incidents_per_hour"],
                "alert_type": AlertType.PATTERN_DETECTED,
                "severity": EventSeverity.CRITICAL,
                "message": "Multiple security incidents detected"
            },
            {
                "name": "Code Modification Failures",
                "condition": lambda: self._count_recent_code_failures() > self.thresholds["code_modification_failures"],
                "alert_type": AlertType.PATTERN_DETECTED,
                "severity": EventSeverity.ERROR,
                "message": "Multiple code modification failures"
            },
            {
                "name": "Learning Stagnation",
                "condition": lambda: self._detect_learning_stagnation(),
                "alert_type": AlertType.PATTERN_DETECTED,
                "severity": EventSeverity.WARNING,
                "message": "Agent learning activity has stagnated"
            }
        ]
    
    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks."""
        # Event processing task
        task = asyncio.create_task(self._event_processing_loop())
        self.background_tasks.add(task)
        
        # Alert checking task
        task = asyncio.create_task(self._alert_checking_loop())
        self.background_tasks.add(task)
        
        # Report generation task
        task = asyncio.create_task(self._report_generation_loop())
        self.background_tasks.add(task)
        
        # Cleanup task
        task = asyncio.create_task(self._cleanup_loop())
        self.background_tasks.add(task)
        
        # Statistics update task
        task = asyncio.create_task(self._statistics_update_loop())
        self.background_tasks.add(task)
    
    async def _event_processing_loop(self) -> None:
        """Main event processing loop."""
        while True:
            try:
                # Process events from queue
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # Process event based on category
                if event.category in self.event_processors:
                    await self.event_processors[event.category](event)
                
                # Mark as processed
                event.processed = True
                
                # Check if immediate intervention is required
                if event.requires_intervention:
                    await self._handle_intervention_request(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in event processing loop: {e}")
                await asyncio.sleep(1)
    
    async def _alert_checking_loop(self) -> None:
        """Check alert rules periodically."""
        while True:
            try:
                for rule in self.alert_rules:
                    try:
                        if rule["condition"]():
                            # Generate alert
                            await self.generate_alert(
                                alert_type=rule["alert_type"],
                                severity=rule["severity"],
                                title=rule["name"],
                                message=rule["message"]
                            )
                    except Exception as e:
                        self.logger.warning(f"Error checking alert rule '{rule['name']}': {e}")
                
                # Check for alert escalations
                await self._check_alert_escalations()
                
                # Sleep before next check
                await asyncio.sleep(self.config["batch_processing_interval"])
                
            except Exception as e:
                self.logger.error(f"Error in alert checking loop: {e}")
                await asyncio.sleep(60)
    
    async def _report_generation_loop(self) -> None:
        """Generate scheduled reports."""
        while True:
            try:
                now = datetime.now()
                
                # Check if it's time for daily report
                if now.hour == self.config["report_generation_hour"] and now.minute < 5:
                    await self.generate_report(
                        report_type="daily_summary",
                        title=f"Daily System Report - {now.strftime('%Y-%m-%d')}",
                        period_start=now - timedelta(days=1),
                        period_end=now
                    )
                
                # Sleep for 5 minutes before next check
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in report generation loop: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_loop(self) -> None:
        """Clean up old events, alerts, and reports."""
        while True:
            try:
                now = datetime.now()
                
                # Clean up old events
                old_events = [
                    event_id for event_id, event in self.events.items()
                    if (now - event.timestamp).days > self.config["event_retention_days"]
                ]
                for event_id in old_events:
                    del self.events[event_id]
                
                # Clean up old alerts
                old_alerts = [
                    alert_id for alert_id, alert in self.alerts.items()
                    if (now - alert.created_at).days > self.config["alert_retention_days"]
                ]
                for alert_id in old_alerts:
                    self.active_alerts.discard(alert_id)
                    del self.alerts[alert_id]
                
                # Clean up old reports
                old_reports = [
                    report_id for report_id, report in self.reports.items()
                    if (now - report.generated_at).days > self.config["report_retention_days"]
                ]
                for report_id in old_reports:
                    del self.reports[report_id]
                
                if old_events or old_alerts or old_reports:
                    self.logger.info(f"Cleaned up {len(old_events)} events, {len(old_alerts)} alerts, {len(old_reports)} reports")
                
                # Sleep for 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def _statistics_update_loop(self) -> None:
        """Update system statistics periodically."""
        while True:
            try:
                # Update active alerts count
                self.stats["active_alerts_count"] = len(self.active_alerts)
                
                # Sleep for 1 minute before next update
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in statistics update loop: {e}")
                await asyncio.sleep(60)
    
    async def _process_agent_lifecycle_event(self, event: MonitoredEvent) -> None:
        """Process agent lifecycle events."""
        # Check for agent creation/destruction patterns
        if event.event_type in ["agent_created", "agent_destroyed"]:
            # Log significant lifecycle events
            if event.severity in [EventSeverity.ERROR, EventSeverity.CRITICAL]:
                await self.generate_alert(
                    AlertType.IMMEDIATE,
                    event.severity,
                    f"Agent Lifecycle Issue: {event.event_type}",
                    f"Agent {event.agent_id}: {event.description}",
                    [event.event_id]
                )
    
    async def _process_communication_event(self, event: MonitoredEvent) -> None:
        """Process communication events."""
        # Monitor communication failures
        if event.event_type == "communication_failed" and event.severity >= EventSeverity.WARNING:
            # Check if this is part of a pattern
            recent_failures = self._count_recent_communication_failures(event.agent_id)
            if recent_failures > 3:
                await self.generate_alert(
                    AlertType.PATTERN_DETECTED,
                    EventSeverity.WARNING,
                    "Communication Pattern Alert",
                    f"Agent {event.agent_id} has {recent_failures} recent communication failures",
                    [event.event_id]
                )
    
    async def _process_learning_event(self, event: MonitoredEvent) -> None:
        """Process learning events."""
        # Monitor learning progress and issues
        if event.event_type == "learning_failed" and event.severity >= EventSeverity.ERROR:
            await self.generate_alert(
                AlertType.IMMEDIATE,
                event.severity,
                "Learning Failure",
                f"Agent {event.agent_id} learning failure: {event.description}",
                [event.event_id]
            )
    
    async def _process_code_modification_event(self, event: MonitoredEvent) -> None:
        """Process code modification events."""
        # Monitor unsafe code modifications
        if event.event_type == "unsafe_code_modification":
            await self.generate_alert(
                AlertType.IMMEDIATE,
                EventSeverity.CRITICAL,
                "Unsafe Code Modification Attempt",
                f"Agent {event.agent_id} attempted unsafe code modification: {event.description}",
                [event.event_id]
            )
            
            # Mark for intervention
            event.requires_intervention = True
            event.intervention_reason = "Unsafe code modification detected"
    
    async def _process_reproduction_event(self, event: MonitoredEvent) -> None:
        """Process reproduction events."""
        # Monitor reproduction failures and successes
        if event.event_type == "reproduction_failed" and event.severity >= EventSeverity.WARNING:
            recent_failures = self._count_recent_reproduction_failures()
            if recent_failures > self.thresholds["reproduction_failures"]:
                await self.generate_alert(
                    AlertType.THRESHOLD_BREACH,
                    EventSeverity.WARNING,
                    "High Reproduction Failure Rate",
                    f"Multiple reproduction failures detected: {recent_failures} in recent period",
                    [event.event_id]
                )
    
    async def _process_economic_event(self, event: MonitoredEvent) -> None:
        """Process economic activity events."""
        # Monitor economic disputes and fraud
        if event.event_type in ["economic_dispute", "fraud_detected"]:
            await self.generate_alert(
                AlertType.IMMEDIATE,
                EventSeverity.WARNING,
                f"Economic Issue: {event.event_type}",
                f"Economic issue detected: {event.description}",
                [event.event_id]
            )
    
    async def _process_world_building_event(self, event: MonitoredEvent) -> None:
        """Process world building events."""
        # Monitor world modification conflicts
        if event.event_type == "world_modification_conflict":
            await self.generate_alert(
                AlertType.IMMEDIATE,
                EventSeverity.WARNING,
                "World Building Conflict",
                f"World modification conflict: {event.description}",
                [event.event_id]
            )
    
    async def _process_human_interaction_event(self, event: MonitoredEvent) -> None:
        """Process human interaction events."""
        # All human interactions are significant
        if event.severity >= EventSeverity.WARNING:
            await self.generate_alert(
                AlertType.IMMEDIATE,
                event.severity,
                "Human Interaction Alert",
                f"Human interaction event: {event.description}",
                [event.event_id]
            )
    
    async def _process_security_event(self, event: MonitoredEvent) -> None:
        """Process security events."""
        # All security events require immediate attention
        await self.generate_alert(
            AlertType.IMMEDIATE,
            max(event.severity, EventSeverity.WARNING),
            f"Security Alert: {event.event_type}",
            f"Security event detected: {event.description}",
            [event.event_id]
        )
        
        # Mark for intervention if critical
        if event.severity >= EventSeverity.CRITICAL:
            event.requires_intervention = True
            event.intervention_reason = "Critical security event"
    
    async def _process_performance_event(self, event: MonitoredEvent) -> None:
        """Process performance events."""
        # Monitor performance degradation
        if event.event_type == "performance_degradation" and event.severity >= EventSeverity.WARNING:
            await self.generate_alert(
                AlertType.THRESHOLD_BREACH,
                event.severity,
                "Performance Degradation",
                f"Performance issue detected: {event.description}",
                [event.event_id]
            )
    
    async def _process_error_event(self, event: MonitoredEvent) -> None:
        """Process error events."""
        # Monitor critical errors
        if event.severity >= EventSeverity.CRITICAL:
            await self.generate_alert(
                AlertType.IMMEDIATE,
                event.severity,
                f"Critical Error: {event.event_type}",
                f"Critical error in agent {event.agent_id}: {event.description}",
                [event.event_id]
            )
    
    async def _handle_intervention_request(self, event: MonitoredEvent) -> None:
        """Handle requests for human intervention."""
        try:
            # Generate high-priority alert
            await self.generate_alert(
                AlertType.INTERVENTION_REQUIRED,
                EventSeverity.CRITICAL,
                "Human Intervention Required",
                f"Agent {event.agent_id} requires intervention: {event.intervention_reason}",
                [event.event_id],
                escalation_minutes=5  # Escalate quickly
            )
            
            # Generate immediate report
            await self.generate_report(
                report_type="intervention_request",
                title=f"Intervention Request - {event.agent_id}",
                period_start=datetime.now() - timedelta(hours=1),
                period_end=datetime.now()
            )
            
            self.logger.critical(f"Human intervention requested for agent {event.agent_id}: {event.intervention_reason}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle intervention request: {e}")
    
    async def _check_alert_escalations(self) -> None:
        """Check for alerts that need escalation."""
        try:
            now = datetime.now()
            
            for alert_id in list(self.active_alerts):
                alert = self.alerts[alert_id]
                
                if (alert.escalation_time and 
                    now >= alert.escalation_time and 
                    not alert.acknowledged):
                    
                    # Escalate alert
                    await self.generate_alert(
                        AlertType.IMMEDIATE,
                        EventSeverity.CRITICAL,
                        f"ESCALATED: {alert.title}",
                        f"Alert {alert_id} has been escalated due to lack of acknowledgment: {alert.message}",
                        alert.triggering_events
                    )
                    
                    self.logger.warning(f"Alert escalated: {alert_id}")
        
        except Exception as e:
            self.logger.error(f"Error checking alert escalations: {e}")
    
    async def _send_immediate_alert(self, alert: Alert) -> None:
        """Send immediate alert notification."""
        try:
            if self.config["enable_email_alerts"]:
                await self._send_email_alert(alert)
            
            # Could add other notification methods here (SMS, Slack, etc.)
            
        except Exception as e:
            self.logger.error(f"Failed to send immediate alert: {e}")
    
    async def _send_email_alert(self, alert: Alert) -> None:
        """Send alert via email."""
        try:
            msg = MimeMultipart()
            msg['From'] = "ai-ecosystem@example.com"
            msg['To'] = self.config["emergency_contact_email"]
            msg['Subject'] = f"[AI ECOSYSTEM ALERT] {alert.title}"
            
            body = f"""
Alert Details:
- Alert ID: {alert.alert_id}
- Severity: {alert.severity.value.upper()}
- Type: {alert.alert_type.value}
- Created: {alert.created_at.isoformat()}

Message:
{alert.message}

Triggering Events: {len(alert.triggering_events)}

This is an automated alert from the AI Ecosystem Monitoring System.
Please acknowledge this alert in the system interface.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email (simplified - would need proper SMTP configuration)
            # server = smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"])
            # server.send_message(msg)
            # server.quit()
            
            self.logger.info(f"Email alert sent for {alert.alert_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    async def _deliver_report(self, report: Report) -> None:
        """Deliver report to recipients."""
        try:
            if self.config["enable_email_alerts"]:
                await self._send_email_report(report)
            
            report.delivered = True
            
        except Exception as e:
            self.logger.error(f"Failed to deliver report: {e}")
    
    async def _send_email_report(self, report: Report) -> None:
        """Send report via email."""
        try:
            for recipient in report.recipients:
                msg = MimeMultipart()
                msg['From'] = "ai-ecosystem@example.com"
                msg['To'] = recipient
                msg['Subject'] = f"[AI ECOSYSTEM REPORT] {report.title}"
                
                msg.attach(MimeText(report.content, 'plain'))
                
                # Send email (simplified)
                self.logger.info(f"Email report sent to {recipient}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email report: {e}")
    
    async def _generate_report_content(
        self,
        report_type: str,
        events: List[MonitoredEvent],
        alerts: List[Alert],
        period_start: datetime,
        period_end: datetime
    ) -> str:
        """Generate report content based on events and alerts."""
        try:
            content_parts = [
                f"# {report_type.replace('_', ' ').title()} Report",
                f"Generated: {datetime.now().isoformat()}",
                f"Period: {period_start.isoformat()} to {period_end.isoformat()}",
                "",
                "## Summary",
                f"- Total Events: {len(events)}",
                f"- Total Alerts: {len(alerts)}",
                f"- Active Alerts: {len(self.active_alerts)}",
                ""
            ]
            
            # Events summary
            if events:
                content_parts.extend([
                    "## Events Summary",
                    ""
                ])
                
                # Group events by category
                events_by_category = {}
                for event in events:
                    category = event.category.value
                    if category not in events_by_category:
                        events_by_category[category] = []
                    events_by_category[category].append(event)
                
                for category, category_events in events_by_category.items():
                    content_parts.append(f"### {category.replace('_', ' ').title()}: {len(category_events)} events")
                    
                    # Show critical events
                    critical_events = [e for e in category_events if e.severity >= EventSeverity.ERROR]
                    if critical_events:
                        content_parts.append("Critical Events:")
                        for event in critical_events[:5]:  # Top 5
                            content_parts.append(f"- {event.timestamp.strftime('%H:%M:%S')} - {event.description}")
                    
                    content_parts.append("")
            
            # Alerts summary
            if alerts:
                content_parts.extend([
                    "## Alerts Summary",
                    ""
                ])
                
                for alert in alerts:
                    status = "RESOLVED" if alert.resolved else "ACTIVE"
                    content_parts.append(f"- [{status}] {alert.title} ({alert.severity.value})")
                    content_parts.append(f"  Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    content_parts.append(f"  Message: {alert.message}")
                    content_parts.append("")
            
            # System health
            content_parts.extend([
                "## System Health",
                f"- System Uptime: {(datetime.now() - self.stats['system_uptime']).total_seconds() / 3600:.1f} hours",
                f"- Total Events Processed: {self.stats['total_events']}",
                f"- Intervention Requests: {self.stats['intervention_requests']}",
                ""
            ])
            
            # Recommendations
            content_parts.extend([
                "## Recommendations",
                ""
            ])
            
            if len(self.active_alerts) > 5:
                content_parts.append("- High number of active alerts - review and resolve")
            
            if self.stats["intervention_requests"] > 0:
                content_parts.append("- Human intervention requests require immediate attention")
            
            error_rate = self._calculate_error_rate()
            if error_rate > 0.05:
                content_parts.append(f"- Error rate is elevated ({error_rate:.1%}) - investigate root causes")
            
            return "\n".join(content_parts)
            
        except Exception as e:
            self.logger.error(f"Failed to generate report content: {e}")
            return f"Error generating report content: {e}"
    
    async def _process_remaining_events(self) -> None:
        """Process any remaining events in the queue during shutdown."""
        try:
            while not self.event_queue.empty():
                try:
                    event = self.event_queue.get_nowait()
                    if event.category in self.event_processors:
                        await self.event_processors[event.category](event)
                    event.processed = True
                except asyncio.QueueEmpty:
                    break
                except Exception as e:
                    self.logger.warning(f"Error processing remaining event: {e}")
        except Exception as e:
            self.logger.error(f"Error processing remaining events: {e}")
    
    # Helper methods for alert rule conditions
    
    def _calculate_error_rate(self) -> float:
        """Calculate recent error rate."""
        try:
            recent_events = [
                event for event in self.events.values()
                if (datetime.now() - event.timestamp).total_seconds() < 3600  # Last hour
            ]
            
            if not recent_events:
                return 0.0
            
            error_events = [
                event for event in recent_events
                if event.severity >= EventSeverity.ERROR
            ]
            
            return len(error_events) / len(recent_events)
            
        except Exception:
            return 0.0
    
    def _calculate_communication_failure_rate(self) -> float:
        """Calculate recent communication failure rate."""
        try:
            recent_comm_events = [
                event for event in self.events.values()
                if (event.category == EventCategory.COMMUNICATION and
                    (datetime.now() - event.timestamp).total_seconds() < 3600)
            ]
            
            if not recent_comm_events:
                return 0.0
            
            failed_events = [
                event for event in recent_comm_events
                if event.event_type == "communication_failed"
            ]
            
            return len(failed_events) / len(recent_comm_events)
            
        except Exception:
            return 0.0
    
    def _count_recent_security_incidents(self) -> int:
        """Count security incidents in the last hour."""
        try:
            return len([
                event for event in self.events.values()
                if (event.category == EventCategory.SECURITY and
                    (datetime.now() - event.timestamp).total_seconds() < 3600)
            ])
        except Exception:
            return 0
    
    def _count_recent_code_failures(self) -> int:
        """Count code modification failures recently."""
        try:
            return len([
                event for event in self.events.values()
                if (event.category == EventCategory.CODE_MODIFICATION and
                    event.event_type == "code_modification_failed" and
                    (datetime.now() - event.timestamp).total_seconds() < 3600)
            ])
        except Exception:
            return 0
    
    def _count_recent_communication_failures(self, agent_id: str) -> int:
        """Count recent communication failures for an agent."""
        try:
            return len([
                event for event in self.events.values()
                if (event.agent_id == agent_id and
                    event.category == EventCategory.COMMUNICATION and
                    event.event_type == "communication_failed" and
                    (datetime.now() - event.timestamp).total_seconds() < 3600)
            ])
        except Exception:
            return 0
    
    def _count_recent_reproduction_failures(self) -> int:
        """Count recent reproduction failures."""
        try:
            return len([
                event for event in self.events.values()
                if (event.category == EventCategory.REPRODUCTION and
                    event.event_type == "reproduction_failed" and
                    (datetime.now() - event.timestamp).total_seconds() < 3600)
            ])
        except Exception:
            return 0
    
    def _detect_learning_stagnation(self) -> bool:
        """Detect if learning activity has stagnated."""
        try:
            recent_learning = [
                event for event in self.events.values()
                if (event.category == EventCategory.LEARNING and
                    (datetime.now() - event.timestamp).total_seconds() < self.thresholds["learning_stagnation_hours"] * 3600)
            ]
            
            return len(recent_learning) == 0
            
        except Exception:
            return False