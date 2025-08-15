"""
Emergency response and shutdown systems.

This module implements emergency shutdown procedures, system state backup,
recovery mechanisms, and incident logging for critical error situations.
"""

import asyncio
import json
import os
import shutil
import signal
import sys
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import threading
import psutil

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class EmergencyLevel(Enum):
    """Levels of emergency situations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    CATASTROPHIC = "catastrophic"


class ShutdownReason(Enum):
    """Reasons for emergency shutdown."""
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    SECURITY_BREACH = "security_breach"
    SYSTEM_CORRUPTION = "system_corruption"
    INFINITE_LOOP = "infinite_loop"
    MEMORY_LEAK = "memory_leak"
    CRITICAL_ERROR = "critical_error"
    MANUAL_SHUTDOWN = "manual_shutdown"
    SAFETY_VIOLATION = "safety_violation"


class RecoveryStrategy(Enum):
    """Recovery strategies for different emergency types."""
    RESTART_COMPONENT = "restart_component"
    ROLLBACK_STATE = "rollback_state"
    RESTORE_BACKUP = "restore_backup"
    SAFE_MODE = "safe_mode"
    FULL_RESTART = "full_restart"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class EmergencyIncident:
    """Represents an emergency incident."""
    incident_id: str
    level: EmergencyLevel
    reason: ShutdownReason
    
    # Incident details
    description: str
    component: str = ""
    error_message: str = ""
    stack_trace: str = ""
    
    # System state at incident
    system_metrics: Dict[str, Any] = field(default_factory=dict)
    active_agents: List[str] = field(default_factory=list)
    resource_usage: Dict[str, float] = field(default_factory=dict)
    
    # Response actions
    actions_taken: List[str] = field(default_factory=list)
    recovery_strategy: Optional[RecoveryStrategy] = None
    
    # Timeline
    detected_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    response_time_seconds: Optional[float] = None
    
    # Status
    resolved: bool = False
    requires_manual_intervention: bool = False
    
    def add_action(self, action: str) -> None:
        """Add an action taken during incident response."""
        self.actions_taken.append(f"[{datetime.now().isoformat()}] {action}")
    
    def mark_resolved(self) -> None:
        """Mark the incident as resolved."""
        self.resolved = True
        self.resolved_at = datetime.now()
        if self.resolved_at:
            self.response_time_seconds = (self.resolved_at - self.detected_at).total_seconds()


@dataclass
class SystemBackup:
    """Represents a system state backup."""
    backup_id: str
    backup_type: str  # full, incremental, component
    
    # Backup content
    backup_path: str
    components_backed_up: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    checksum: str = ""
    
    # Validation
    verified: bool = False
    verification_date: Optional[datetime] = None
    
    # Retention
    expires_at: Optional[datetime] = None
    auto_delete: bool = True


class EmergencyResponseSystem(AgentModule):
    """
    Emergency response and shutdown system.
    
    Provides emergency shutdown procedures, system state backup and recovery,
    and incident logging for critical error situations.
    """
    
    def __init__(self, agent_id: str = "emergency_response"):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "emergency_response")
        
        # Core data structures
        self.incidents: Dict[str, EmergencyIncident] = {}
        self.backups: Dict[str, SystemBackup] = {}
        self.shutdown_handlers: Dict[str, Callable] = {}
        
        # System monitoring
        self.monitoring_active: bool = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.resource_thresholds = {
            "cpu_percent": 95.0,
            "memory_percent": 90.0,
            "disk_percent": 95.0,
            "open_files": 1000
        }
        
        # Emergency state
        self.emergency_active: bool = False
        self.shutdown_in_progress: bool = False
        self.safe_mode: bool = False
        
        # Configuration
        self.config = {
            "backup_directory": "backups",
            "incident_log_file": "incidents.log",
            "max_backup_age_days": 30,
            "backup_interval_hours": 6,
            "monitoring_interval_seconds": 10,
            "emergency_timeout_seconds": 30,
            "max_incidents_retained": 1000,
            "auto_backup_on_emergency": True,
            "enable_graceful_shutdown": True,
            "shutdown_timeout_seconds": 60
        }
        
        # Statistics
        self.stats = {
            "total_incidents": 0,
            "incidents_by_level": {level.value: 0 for level in EmergencyLevel},
            "incidents_by_reason": {reason.value: 0 for reason in ShutdownReason},
            "total_backups": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "average_response_time": 0.0,
            "system_uptime_seconds": 0.0
        }
        
        # Counters
        self.incident_counter = 0
        self.backup_counter = 0
        
        # System start time
        self.system_start_time = datetime.now()
        
        # Signal handlers
        self._setup_signal_handlers()
        
        self.logger.info("Emergency response system initialized")
    
    async def initialize(self) -> None:
        """Initialize the emergency response system."""
        try:
            # Create backup directory
            os.makedirs(self.config["backup_directory"], exist_ok=True)
            
            # Start monitoring
            await self.start_monitoring()
            
            # Create initial backup
            await self.create_system_backup("initial", "full")
            
            # Start periodic backup task
            asyncio.create_task(self._periodic_backup_task())
            
            # Start cleanup task
            asyncio.create_task(self._cleanup_old_data())
            
            self.logger.info("Emergency response system initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize emergency response system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the emergency response system."""
        try:
            # Stop monitoring
            await self.stop_monitoring()
            
            # Create final backup
            if not self.shutdown_in_progress:
                await self.create_system_backup("shutdown", "full")
            
            self.logger.info("Emergency response system shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during emergency response system shutdown: {e}")
    
    async def trigger_emergency_shutdown(
        self,
        reason: ShutdownReason,
        description: str,
        component: str = "",
        level: EmergencyLevel = EmergencyLevel.HIGH
    ) -> str:
        """Trigger an emergency shutdown of the system."""
        try:
            if self.shutdown_in_progress:
                return "shutdown_already_in_progress"
            
            # Create incident
            incident_id = await self.report_incident(
                level=level,
                reason=reason,
                description=description,
                component=component
            )
            
            incident = self.incidents[incident_id]
            incident.add_action("Emergency shutdown initiated")
            
            self.shutdown_in_progress = True
            self.emergency_active = True
            
            # Create emergency backup if configured
            if self.config["auto_backup_on_emergency"]:
                try:
                    backup_id = await self.create_system_backup("emergency", "full")
                    incident.add_action(f"Emergency backup created: {backup_id}")
                except Exception as e:
                    incident.add_action(f"Emergency backup failed: {e}")
            
            # Execute shutdown sequence
            await self._execute_shutdown_sequence(incident)
            
            log_agent_event(
                self.agent_id,
                "emergency_shutdown_triggered",
                {
                    "incident_id": incident_id,
                    "reason": reason.value,
                    "level": level.value,
                    "component": component
                }
            )
            
            self.logger.critical(f"Emergency shutdown triggered: {description}")
            
            return incident_id
            
        except Exception as e:
            self.logger.error(f"Failed to trigger emergency shutdown: {e}")
            return ""
    
    async def report_incident(
        self,
        level: EmergencyLevel,
        reason: ShutdownReason,
        description: str,
        component: str = "",
        error_message: str = "",
        stack_trace: str = ""
    ) -> str:
        """Report an emergency incident."""
        try:
            # Create incident
            self.incident_counter += 1
            incident_id = f"incident_{self.incident_counter}_{datetime.now().timestamp()}"
            
            # Collect system metrics
            system_metrics = await self._collect_system_metrics()
            
            incident = EmergencyIncident(
                incident_id=incident_id,
                level=level,
                reason=reason,
                description=description,
                component=component,
                error_message=error_message,
                stack_trace=stack_trace,
                system_metrics=system_metrics
            )
            
            # Determine if manual intervention is required
            if level in [EmergencyLevel.CRITICAL, EmergencyLevel.CATASTROPHIC]:
                incident.requires_manual_intervention = True
            
            # Store incident
            self.incidents[incident_id] = incident
            
            # Update statistics
            self.stats["total_incidents"] += 1
            self.stats["incidents_by_level"][level.value] += 1
            self.stats["incidents_by_reason"][reason.value] += 1
            
            # Log incident
            await self._log_incident(incident)
            
            # Trigger automatic response if appropriate
            if level in [EmergencyLevel.HIGH, EmergencyLevel.CRITICAL, EmergencyLevel.CATASTROPHIC]:
                await self._trigger_automatic_response(incident)
            
            log_agent_event(
                self.agent_id,
                "incident_reported",
                {
                    "incident_id": incident_id,
                    "level": level.value,
                    "reason": reason.value,
                    "component": component
                }
            )
            
            self.logger.warning(f"Incident reported: {description} (Level: {level.value})")
            
            return incident_id
            
        except Exception as e:
            self.logger.error(f"Failed to report incident: {e}")
            return ""
    
    async def create_system_backup(
        self,
        backup_type: str = "manual",
        scope: str = "full"
    ) -> str:
        """Create a system state backup."""
        try:
            # Create backup
            self.backup_counter += 1
            backup_id = f"backup_{self.backup_counter}_{datetime.now().timestamp()}"
            
            backup_path = os.path.join(
                self.config["backup_directory"],
                f"{backup_id}_{backup_type}"
            )
            
            # Create backup directory
            os.makedirs(backup_path, exist_ok=True)
            
            components_backed_up = []
            
            # Backup configuration files
            if scope in ["full", "config"]:
                await self._backup_configuration(backup_path)
                components_backed_up.append("configuration")
            
            # Backup agent states
            if scope in ["full", "agents"]:
                await self._backup_agent_states(backup_path)
                components_backed_up.append("agent_states")
            
            # Backup system logs
            if scope in ["full", "logs"]:
                await self._backup_system_logs(backup_path)
                components_backed_up.append("system_logs")
            
            # Backup databases
            if scope in ["full", "data"]:
                await self._backup_databases(backup_path)
                components_backed_up.append("databases")
            
            # Calculate backup size and checksum
            size_bytes = await self._calculate_directory_size(backup_path)
            checksum = await self._calculate_directory_checksum(backup_path)
            
            # Create backup record
            backup = SystemBackup(
                backup_id=backup_id,
                backup_type=backup_type,
                backup_path=backup_path,
                components_backed_up=components_backed_up,
                size_bytes=size_bytes,
                checksum=checksum,
                expires_at=datetime.now() + timedelta(days=self.config["max_backup_age_days"])
            )
            
            # Store backup record
            self.backups[backup_id] = backup
            
            # Update statistics
            self.stats["total_backups"] += 1
            
            log_agent_event(
                self.agent_id,
                "backup_created",
                {
                    "backup_id": backup_id,
                    "backup_type": backup_type,
                    "scope": scope,
                    "size_bytes": size_bytes,
                    "components": components_backed_up
                }
            )
            
            self.logger.info(f"System backup created: {backup_id} ({scope})")
            
            return backup_id
            
        except Exception as e:
            self.logger.error(f"Failed to create system backup: {e}")
            return ""
    
    async def restore_from_backup(
        self,
        backup_id: str,
        components: Optional[List[str]] = None
    ) -> bool:
        """Restore system from a backup."""
        try:
            if backup_id not in self.backups:
                self.logger.error(f"Backup not found: {backup_id}")
                return False
            
            backup = self.backups[backup_id]
            
            # Verify backup integrity
            if not await self._verify_backup(backup):
                self.logger.error(f"Backup verification failed: {backup_id}")
                return False
            
            # Determine components to restore
            restore_components = components or backup.components_backed_up
            
            # Create pre-restore backup
            pre_restore_backup = await self.create_system_backup("pre_restore", "full")
            
            try:
                # Restore components
                for component in restore_components:
                    if component in backup.components_backed_up:
                        await self._restore_component(backup, component)
                
                self.stats["successful_recoveries"] += 1
                
                log_agent_event(
                    self.agent_id,
                    "backup_restored",
                    {
                        "backup_id": backup_id,
                        "components": restore_components,
                        "pre_restore_backup": pre_restore_backup
                    }
                )
                
                self.logger.info(f"System restored from backup: {backup_id}")
                
                return True
                
            except Exception as e:
                # Restore failed, try to rollback
                self.logger.error(f"Restore failed, attempting rollback: {e}")
                
                if pre_restore_backup:
                    await self.restore_from_backup(pre_restore_backup)
                
                self.stats["failed_recoveries"] += 1
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {e}")
            self.stats["failed_recoveries"] += 1
            return False
    
    async def start_monitoring(self) -> None:
        """Start system monitoring for emergency conditions."""
        try:
            if self.monitoring_active:
                return
            
            self.monitoring_active = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            self.logger.info("Emergency monitoring started")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
    
    async def stop_monitoring(self) -> None:
        """Stop system monitoring."""
        try:
            self.monitoring_active = False
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                self.monitoring_task = None
            
            self.logger.info("Emergency monitoring stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
    
    async def get_incident_report(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed incident report."""
        try:
            if incident_id not in self.incidents:
                return None
            
            incident = self.incidents[incident_id]
            
            return {
                "incident_id": incident_id,
                "level": incident.level.value,
                "reason": incident.reason.value,
                "description": incident.description,
                "component": incident.component,
                "error_message": incident.error_message,
                "detected_at": incident.detected_at.isoformat(),
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "response_time_seconds": incident.response_time_seconds,
                "resolved": incident.resolved,
                "requires_manual_intervention": incident.requires_manual_intervention,
                "actions_taken": incident.actions_taken,
                "recovery_strategy": incident.recovery_strategy.value if incident.recovery_strategy else None,
                "system_metrics": incident.system_metrics,
                "active_agents": incident.active_agents,
                "resource_usage": incident.resource_usage
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get incident report: {e}")
            return None
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and health."""
        try:
            current_metrics = await self._collect_system_metrics()
            
            # Calculate uptime
            uptime_seconds = (datetime.now() - self.system_start_time).total_seconds()
            self.stats["system_uptime_seconds"] = uptime_seconds
            
            # Get recent incidents
            recent_incidents = [
                incident for incident in self.incidents.values()
                if (datetime.now() - incident.detected_at).days <= 1
            ]
            
            return {
                "emergency_active": self.emergency_active,
                "shutdown_in_progress": self.shutdown_in_progress,
                "safe_mode": self.safe_mode,
                "monitoring_active": self.monitoring_active,
                "system_uptime_seconds": uptime_seconds,
                "current_metrics": current_metrics,
                "recent_incidents": len(recent_incidents),
                "total_backups": len(self.backups),
                "statistics": self.stats,
                "resource_thresholds": self.resource_thresholds
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return {}
    
    def register_shutdown_handler(self, name: str, handler: Callable) -> None:
        """Register a shutdown handler for graceful component shutdown."""
        self.shutdown_handlers[name] = handler
        self.logger.info(f"Shutdown handler registered: {name}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for emergency shutdown."""
        try:
            # Handle SIGTERM and SIGINT
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            # Handle SIGUSR1 for emergency shutdown (Unix only)
            if hasattr(signal, 'SIGUSR1'):
                signal.signal(signal.SIGUSR1, self._emergency_signal_handler)
                
        except Exception as e:
            self.logger.warning(f"Failed to setup signal handlers: {e}")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
        
        # Create a task to handle shutdown
        asyncio.create_task(self.trigger_emergency_shutdown(
            reason=ShutdownReason.MANUAL_SHUTDOWN,
            description=f"Received signal {signum}",
            level=EmergencyLevel.MEDIUM
        ))
    
    def _emergency_signal_handler(self, signum: int, frame) -> None:
        """Handle emergency shutdown signals."""
        self.logger.critical(f"Received emergency signal {signum}, initiating immediate shutdown")
        
        # Create a task to handle emergency shutdown
        asyncio.create_task(self.trigger_emergency_shutdown(
            reason=ShutdownReason.MANUAL_SHUTDOWN,
            description=f"Emergency signal {signum}",
            level=EmergencyLevel.CRITICAL
        ))
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for detecting emergency conditions."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                metrics = await self._collect_system_metrics()
                
                # Check for emergency conditions
                await self._check_emergency_conditions(metrics)
                
                # Wait for next check
                await asyncio.sleep(self.config["monitoring_interval_seconds"])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.config["monitoring_interval_seconds"])
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics."""
        try:
            # CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Process information
            process = psutil.Process()
            process_info = {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "open_files": len(process.open_files()),
                "threads": process.num_threads()
            }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / 1024 / 1024,
                "disk_percent": (disk.used / disk.total) * 100,
                "disk_free_mb": disk.free / 1024 / 1024,
                "process": process_info,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
            return {}
    
    async def _check_emergency_conditions(self, metrics: Dict[str, Any]) -> None:
        """Check for emergency conditions in system metrics."""
        try:
            # Check CPU usage
            if metrics.get("cpu_percent", 0) > self.resource_thresholds["cpu_percent"]:
                await self.report_incident(
                    level=EmergencyLevel.HIGH,
                    reason=ShutdownReason.RESOURCE_EXHAUSTION,
                    description=f"High CPU usage: {metrics['cpu_percent']:.1f}%",
                    component="system_monitor"
                )
            
            # Check memory usage
            if metrics.get("memory_percent", 0) > self.resource_thresholds["memory_percent"]:
                await self.report_incident(
                    level=EmergencyLevel.HIGH,
                    reason=ShutdownReason.MEMORY_LEAK,
                    description=f"High memory usage: {metrics['memory_percent']:.1f}%",
                    component="system_monitor"
                )
            
            # Check disk usage
            if metrics.get("disk_percent", 0) > self.resource_thresholds["disk_percent"]:
                await self.report_incident(
                    level=EmergencyLevel.MEDIUM,
                    reason=ShutdownReason.RESOURCE_EXHAUSTION,
                    description=f"High disk usage: {metrics['disk_percent']:.1f}%",
                    component="system_monitor"
                )
            
            # Check open files
            process_info = metrics.get("process", {})
            if process_info.get("open_files", 0) > self.resource_thresholds["open_files"]:
                await self.report_incident(
                    level=EmergencyLevel.MEDIUM,
                    reason=ShutdownReason.RESOURCE_EXHAUSTION,
                    description=f"Too many open files: {process_info['open_files']}",
                    component="system_monitor"
                )
            
        except Exception as e:
            self.logger.error(f"Failed to check emergency conditions: {e}")
    
    async def _trigger_automatic_response(self, incident: EmergencyIncident) -> None:
        """Trigger automatic response to an incident."""
        try:
            # Determine recovery strategy
            strategy = self._determine_recovery_strategy(incident)
            incident.recovery_strategy = strategy
            incident.add_action(f"Recovery strategy determined: {strategy.value}")
            
            # Execute recovery strategy
            if strategy == RecoveryStrategy.RESTART_COMPONENT:
                await self._restart_component(incident)
            elif strategy == RecoveryStrategy.ROLLBACK_STATE:
                await self._rollback_state(incident)
            elif strategy == RecoveryStrategy.RESTORE_BACKUP:
                await self._restore_latest_backup(incident)
            elif strategy == RecoveryStrategy.SAFE_MODE:
                await self._enter_safe_mode(incident)
            elif strategy == RecoveryStrategy.FULL_RESTART:
                await self._full_system_restart(incident)
            elif strategy == RecoveryStrategy.MANUAL_INTERVENTION:
                incident.requires_manual_intervention = True
                incident.add_action("Manual intervention required")
            
        except Exception as e:
            incident.add_action(f"Automatic response failed: {e}")
            self.logger.error(f"Failed to trigger automatic response: {e}")
    
    def _determine_recovery_strategy(self, incident: EmergencyIncident) -> RecoveryStrategy:
        """Determine the appropriate recovery strategy for an incident."""
        # Strategy based on incident level and reason
        if incident.level == EmergencyLevel.CATASTROPHIC:
            return RecoveryStrategy.MANUAL_INTERVENTION
        elif incident.level == EmergencyLevel.CRITICAL:
            if incident.reason in [ShutdownReason.SECURITY_BREACH, ShutdownReason.SYSTEM_CORRUPTION]:
                return RecoveryStrategy.RESTORE_BACKUP
            else:
                return RecoveryStrategy.FULL_RESTART
        elif incident.level == EmergencyLevel.HIGH:
            if incident.reason == ShutdownReason.MEMORY_LEAK:
                return RecoveryStrategy.RESTART_COMPONENT
            elif incident.reason == ShutdownReason.INFINITE_LOOP:
                return RecoveryStrategy.SAFE_MODE
            else:
                return RecoveryStrategy.ROLLBACK_STATE
        else:
            return RecoveryStrategy.RESTART_COMPONENT
    
    async def _execute_shutdown_sequence(self, incident: EmergencyIncident) -> None:
        """Execute the emergency shutdown sequence."""
        try:
            incident.add_action("Starting shutdown sequence")
            
            # Set timeout for shutdown
            shutdown_timeout = self.config["shutdown_timeout_seconds"]
            
            if self.config["enable_graceful_shutdown"]:
                # Graceful shutdown
                incident.add_action("Attempting graceful shutdown")
                
                # Call registered shutdown handlers
                for name, handler in self.shutdown_handlers.items():
                    try:
                        incident.add_action(f"Calling shutdown handler: {name}")
                        if asyncio.iscoroutinefunction(handler):
                            await asyncio.wait_for(handler(), timeout=10)
                        else:
                            handler()
                    except Exception as e:
                        incident.add_action(f"Shutdown handler {name} failed: {e}")
                
                # Wait a moment for cleanup
                await asyncio.sleep(2)
            
            # Force shutdown if critical
            if incident.level in [EmergencyLevel.CRITICAL, EmergencyLevel.CATASTROPHIC]:
                incident.add_action("Forcing immediate shutdown")
                os._exit(1)
            else:
                incident.add_action("Graceful shutdown completed")
                sys.exit(0)
            
        except Exception as e:
            incident.add_action(f"Shutdown sequence failed: {e}")
            self.logger.error(f"Shutdown sequence failed: {e}")
            # Force exit as last resort
            os._exit(1)
    
    async def _backup_configuration(self, backup_path: str) -> None:
        """Backup configuration files."""
        config_backup_path = os.path.join(backup_path, "config")
        os.makedirs(config_backup_path, exist_ok=True)
        
        # Copy configuration files
        config_files = ["config.json", "settings.json"]
        for config_file in config_files:
            if os.path.exists(config_file):
                shutil.copy2(config_file, config_backup_path)
    
    async def _backup_agent_states(self, backup_path: str) -> None:
        """Backup agent state files."""
        states_backup_path = os.path.join(backup_path, "agent_states")
        os.makedirs(states_backup_path, exist_ok=True)
        
        # Copy agent state directories if they exist
        if os.path.exists("agent_states"):
            shutil.copytree("agent_states", states_backup_path, dirs_exist_ok=True)
    
    async def _backup_system_logs(self, backup_path: str) -> None:
        """Backup system log files."""
        logs_backup_path = os.path.join(backup_path, "logs")
        os.makedirs(logs_backup_path, exist_ok=True)
        
        # Copy log files
        if os.path.exists("logs"):
            shutil.copytree("logs", logs_backup_path, dirs_exist_ok=True)
    
    async def _backup_databases(self, backup_path: str) -> None:
        """Backup database files."""
        db_backup_path = os.path.join(backup_path, "databases")
        os.makedirs(db_backup_path, exist_ok=True)
        
        # Copy database files
        db_extensions = [".db", ".sqlite", ".sqlite3"]
        for file in os.listdir("."):
            if any(file.endswith(ext) for ext in db_extensions):
                shutil.copy2(file, db_backup_path)
    
    async def _calculate_directory_size(self, path: str) -> int:
        """Calculate total size of directory."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
    
    async def _calculate_directory_checksum(self, path: str) -> str:
        """Calculate checksum for directory contents."""
        import hashlib
        
        hash_md5 = hashlib.md5()
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in sorted(filenames):
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    async def _verify_backup(self, backup: SystemBackup) -> bool:
        """Verify backup integrity."""
        try:
            if not os.path.exists(backup.backup_path):
                return False
            
            # Verify checksum
            current_checksum = await self._calculate_directory_checksum(backup.backup_path)
            if current_checksum != backup.checksum:
                return False
            
            backup.verified = True
            backup.verification_date = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Backup verification failed: {e}")
            return False
    
    async def _restore_component(self, backup: SystemBackup, component: str) -> None:
        """Restore a specific component from backup."""
        component_path = os.path.join(backup.backup_path, component)
        
        if component == "configuration":
            # Restore config files
            for file in os.listdir(component_path):
                shutil.copy2(os.path.join(component_path, file), ".")
        elif component == "agent_states":
            # Restore agent states
            if os.path.exists("agent_states"):
                shutil.rmtree("agent_states")
            shutil.copytree(component_path, "agent_states")
        elif component == "databases":
            # Restore database files
            for file in os.listdir(component_path):
                shutil.copy2(os.path.join(component_path, file), ".")
    
    async def _log_incident(self, incident: EmergencyIncident) -> None:
        """Log incident to file."""
        try:
            log_entry = {
                "incident_id": incident.incident_id,
                "timestamp": incident.detected_at.isoformat(),
                "level": incident.level.value,
                "reason": incident.reason.value,
                "description": incident.description,
                "component": incident.component,
                "error_message": incident.error_message,
                "system_metrics": incident.system_metrics
            }
            
            with open(self.config["incident_log_file"], "a") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            self.logger.error(f"Failed to log incident: {e}")
    
    async def _restart_component(self, incident: EmergencyIncident) -> None:
        """Restart a specific component."""
        incident.add_action(f"Restarting component: {incident.component}")
        # Implementation would depend on component architecture
    
    async def _rollback_state(self, incident: EmergencyIncident) -> None:
        """Rollback system state."""
        incident.add_action("Rolling back system state")
        # Find most recent backup and restore
        if self.backups:
            latest_backup_id = max(self.backups.keys(), key=lambda x: self.backups[x].created_at)
            await self.restore_from_backup(latest_backup_id)
    
    async def _restore_latest_backup(self, incident: EmergencyIncident) -> None:
        """Restore from latest backup."""
        incident.add_action("Restoring from latest backup")
        if self.backups:
            latest_backup_id = max(self.backups.keys(), key=lambda x: self.backups[x].created_at)
            await self.restore_from_backup(latest_backup_id)
    
    async def _enter_safe_mode(self, incident: EmergencyIncident) -> None:
        """Enter safe mode."""
        incident.add_action("Entering safe mode")
        self.safe_mode = True
        # Disable non-essential systems
    
    async def _full_system_restart(self, incident: EmergencyIncident) -> None:
        """Perform full system restart."""
        incident.add_action("Performing full system restart")
        await self._execute_shutdown_sequence(incident)
    
    async def _periodic_backup_task(self) -> None:
        """Periodic backup creation task."""
        while True:
            try:
                await asyncio.sleep(self.config["backup_interval_hours"] * 3600)
                await self.create_system_backup("periodic", "incremental")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Periodic backup failed: {e}")
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old incidents and backups."""
        while True:
            try:
                await asyncio.sleep(24 * 3600)  # Daily cleanup
                
                # Clean up old incidents
                cutoff_date = datetime.now() - timedelta(days=30)
                old_incidents = [
                    incident_id for incident_id, incident in self.incidents.items()
                    if incident.detected_at < cutoff_date
                ]
                
                for incident_id in old_incidents:
                    del self.incidents[incident_id]
                
                # Clean up expired backups
                expired_backups = [
                    backup_id for backup_id, backup in self.backups.items()
                    if backup.expires_at and backup.expires_at < datetime.now()
                ]
                
                for backup_id in expired_backups:
                    backup = self.backups[backup_id]
                    if backup.auto_delete and os.path.exists(backup.backup_path):
                        shutil.rmtree(backup.backup_path)
                    del self.backups[backup_id]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup task failed: {e}")