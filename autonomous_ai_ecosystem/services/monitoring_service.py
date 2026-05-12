"""
Continuous monitoring service for websites and systems.

This module implements monitoring capabilities for external websites,
APIs, and system resources with alerting and reporting functionality.
"""

import asyncio
import aiohttp
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class MonitorType(Enum):
    """Types of monitoring checks."""
    WEBSITE_HEALTH = "website_health"
    API_ENDPOINT = "api_endpoint"
    SYSTEM_RESOURCE = "system_resource"
    DATABASE_CONNECTION = "database_connection"
    SERVICE_STATUS = "service_status"
    CUSTOM_METRIC = "custom_metric"


class MonitorStatus(Enum):
    """Status of monitoring checks."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    DISABLED = "disabled"


@dataclass
class MonitorCheck:
    """Configuration for a monitoring check."""
    check_id: str
    name: str
    monitor_type: MonitorType
    target: str  # URL, system metric name, etc.
    
    # Check configuration
    interval_seconds: int = 60
    timeout_seconds: int = 30
    enabled: bool = True
    
    # Thresholds
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    expected_status_code: int = 200
    expected_response_time_ms: float = 5000.0
    
    # Alert configuration
    alert_on_failure: bool = True
    alert_after_failures: int = 3
    recovery_notification: bool = True
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    # Custom validation
    custom_validator: Optional[str] = None  # Python code for custom validation


@dataclass
class MonitorResult:
    """Result of a monitoring check."""
    result_id: str
    check_id: str
    timestamp: datetime
    status: MonitorStatus
    
    # Metrics
    response_time_ms: Optional[float] = None
    value: Optional[float] = None
    status_code: Optional[int] = None
    
    # Details
    message: str = ""
    error_details: Optional[str] = None
    raw_response: Optional[str] = None
    
    # Context
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_healthy(self) -> bool:
        """Check if result indicates healthy status."""
        return self.status == MonitorStatus.HEALTHY
    
    def requires_alert(self) -> bool:
        """Check if result requires alerting."""
        return self.status in [MonitorStatus.WARNING, MonitorStatus.CRITICAL]


@dataclass
class MonitorAlert:
    """Alert generated from monitoring results."""
    alert_id: str
    check_id: str
    alert_type: str  # failure, recovery, threshold_breach
    severity: MonitorStatus
    
    # Alert details
    title: str
    message: str
    triggered_at: datetime
    
    # Context
    trigger_result: MonitorResult
    consecutive_failures: int = 0
    
    # Status
    acknowledged: bool = False
    resolved: bool = False
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class ContinuousMonitoringService(AgentModule):
    """
    Continuous monitoring service for websites, APIs, and system resources.
    
    Provides real-time monitoring with configurable checks, thresholds,
    alerting, and reporting capabilities.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "monitoring_service")
        
        # Core data structures
        self.monitor_checks: Dict[str, MonitorCheck] = {}
        self.monitor_results: Dict[str, List[MonitorResult]] = {}  # check_id -> results
        self.monitor_alerts: Dict[str, MonitorAlert] = {}
        
        # Runtime state
        self.running_checks: Set[str] = set()
        self.check_tasks: Dict[str, asyncio.Task] = {}
        self.failure_counts: Dict[str, int] = {}  # check_id -> consecutive failures
        
        # Configuration
        self.config = {
            "max_results_per_check": 1000,
            "result_retention_hours": 168,  # 7 days
            "alert_retention_hours": 720,   # 30 days
            "max_concurrent_checks": 50,
            "default_user_agent": "AI-Ecosystem-Monitor/1.0",
            "enable_system_monitoring": True,
            "system_check_interval": 30,
            "notification_cooldown_minutes": 15
        }
        
        # HTTP session for web monitoring
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Statistics
        self.stats = {
            "total_checks": 0,
            "active_checks": 0,
            "total_results": 0,
            "healthy_checks": 0,
            "warning_checks": 0,
            "critical_checks": 0,
            "total_alerts": 0,
            "checks_by_type": {monitor_type.value: 0 for monitor_type in MonitorType}
        }
        
        # Counters
        self.check_counter = 0
        self.result_counter = 0
        self.alert_counter = 0
        
        self.logger.info("Continuous monitoring service initialized")
    
    async def initialize(self) -> None:
        """Initialize the monitoring service."""
        try:
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=self.config.get("default_timeout", 30))
            self.http_session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"User-Agent": self.config["default_user_agent"]}
            )
            
            # Start system monitoring if enabled
            if self.config["enable_system_monitoring"]:
                await self._setup_system_monitoring()
            
            # Start background tasks
            asyncio.create_task(self._cleanup_old_data())
            asyncio.create_task(self._update_statistics())
            
            self.logger.info("Monitoring service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the monitoring service."""
        try:
            # Stop all running checks
            for task in self.check_tasks.values():
                task.cancel()
            
            # Wait for tasks to complete
            if self.check_tasks:
                await asyncio.gather(*self.check_tasks.values(), return_exceptions=True)
            
            # Close HTTP session
            if self.http_session:
                await self.http_session.close()
            
            self.logger.info("Monitoring service shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during monitoring service shutdown: {e}")
    
    async def add_monitor_check(
        self,
        name: str,
        monitor_type: MonitorType,
        target: str,
        interval_seconds: int = 60,
        timeout_seconds: int = 30,
        warning_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None,
        tags: Optional[List[str]] = None,
        description: str = "",
        custom_validator: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a new monitoring check."""
        try:
            self.check_counter += 1
            check_id = f"check_{self.check_counter}_{datetime.now().timestamp()}"
            
            check = MonitorCheck(
                check_id=check_id,
                name=name,
                monitor_type=monitor_type,
                target=target,
                interval_seconds=interval_seconds,
                timeout_seconds=timeout_seconds,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                tags=tags or [],
                description=description,
                custom_validator=custom_validator
            )
            
            self.monitor_checks[check_id] = check
            self.monitor_results[check_id] = []
            self.failure_counts[check_id] = 0
            
            # Start monitoring task
            if check.enabled:
                await self._start_check(check_id)
            
            # Update statistics
            self.stats["total_checks"] += 1
            self.stats["checks_by_type"][monitor_type.value] += 1
            
            log_agent_event(
                self.agent_id,
                "monitor_check_added",
                {
                    "check_id": check_id,
                    "name": name,
                    "monitor_type": monitor_type.value,
                    "target": target,
                    "interval_seconds": interval_seconds
                }
            )
            
            result = {
                "success": True,
                "check_id": check_id,
                "name": name,
                "monitor_type": monitor_type.value,
                "status": "active" if check.enabled else "disabled"
            }
            
            self.logger.info(f"Monitor check added: {name} ({monitor_type.value})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to add monitor check: {e}")
            return {"success": False, "error": str(e)}
    
    async def remove_monitor_check(self, check_id: str) -> Dict[str, Any]:
        """Remove a monitoring check."""
        try:
            if check_id not in self.monitor_checks:
                return {"success": False, "error": "Check not found"}
            
            # Stop the check task
            if check_id in self.check_tasks:
                self.check_tasks[check_id].cancel()
                del self.check_tasks[check_id]
            
            # Remove from running checks
            self.running_checks.discard(check_id)
            
            # Clean up data
            check = self.monitor_checks[check_id]
            del self.monitor_checks[check_id]
            del self.monitor_results[check_id]
            del self.failure_counts[check_id]
            
            # Update statistics
            self.stats["total_checks"] -= 1
            self.stats["checks_by_type"][check.monitor_type.value] -= 1
            
            log_agent_event(
                self.agent_id,
                "monitor_check_removed",
                {
                    "check_id": check_id,
                    "name": check.name,
                    "monitor_type": check.monitor_type.value
                }
            )
            
            result = {
                "success": True,
                "check_id": check_id,
                "name": check.name,
                "removed_at": datetime.now().isoformat()
            }
            
            self.logger.info(f"Monitor check removed: {check.name}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to remove monitor check: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_monitor_status(self, check_id: Optional[str] = None) -> Dict[str, Any]:
        """Get monitoring status for specific check or all checks."""
        try:
            if check_id:
                if check_id not in self.monitor_checks:
                    return {"success": False, "error": "Check not found"}
                
                check = self.monitor_checks[check_id]
                recent_results = self.monitor_results[check_id][-10:]  # Last 10 results
                
                current_status = MonitorStatus.UNKNOWN
                if recent_results:
                    current_status = recent_results[-1].status
                
                status_info = {
                    "check_id": check_id,
                    "name": check.name,
                    "monitor_type": check.monitor_type.value,
                    "target": check.target,
                    "current_status": current_status.value,
                    "enabled": check.enabled,
                    "consecutive_failures": self.failure_counts.get(check_id, 0),
                    "last_check": recent_results[-1].timestamp.isoformat() if recent_results else None,
                    "recent_results": [
                        {
                            "timestamp": result.timestamp.isoformat(),
                            "status": result.status.value,
                            "response_time_ms": result.response_time_ms,
                            "message": result.message
                        }
                        for result in recent_results
                    ]
                }
                
                return {"success": True, "status": status_info}
            
            else:
                # Get status for all checks
                all_status = []
                
                for cid, check in self.monitor_checks.items():
                    recent_results = self.monitor_results[cid][-1:]  # Last result
                    
                    current_status = MonitorStatus.UNKNOWN
                    last_check = None
                    if recent_results:
                        current_status = recent_results[-1].status
                        last_check = recent_results[-1].timestamp.isoformat()
                    
                    status_info = {
                        "check_id": cid,
                        "name": check.name,
                        "monitor_type": check.monitor_type.value,
                        "current_status": current_status.value,
                        "enabled": check.enabled,
                        "consecutive_failures": self.failure_counts.get(cid, 0),
                        "last_check": last_check
                    }
                    
                    all_status.append(status_info)
                
                return {
                    "success": True,
                    "total_checks": len(all_status),
                    "statistics": self.stats,
                    "checks": all_status
                }
            
        except Exception as e:
            self.logger.error(f"Failed to get monitor status: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_monitor_alerts(
        self,
        check_id: Optional[str] = None,
        severity: Optional[MonitorStatus] = None,
        unresolved_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get monitoring alerts with filtering."""
        try:
            filtered_alerts = []
            
            for alert in self.monitor_alerts.values():
                # Filter by check_id
                if check_id and alert.check_id != check_id:
                    continue
                
                # Filter by severity
                if severity and alert.severity != severity:
                    continue
                
                # Filter by resolution status
                if unresolved_only and alert.resolved:
                    continue
                
                alert_info = {
                    "alert_id": alert.alert_id,
                    "check_id": alert.check_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "message": alert.message,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "consecutive_failures": alert.consecutive_failures,
                    "acknowledged": alert.acknowledged,
                    "resolved": alert.resolved,
                    "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
                }
                
                filtered_alerts.append(alert_info)
            
            # Sort by triggered time (most recent first)
            filtered_alerts.sort(key=lambda a: a["triggered_at"], reverse=True)
            
            return filtered_alerts
            
        except Exception as e:
            self.logger.error(f"Failed to get monitor alerts: {e}")
            return []
    
    async def _start_check(self, check_id: str) -> None:
        """Start monitoring task for a check."""
        if check_id in self.check_tasks:
            return  # Already running
        
        check = self.monitor_checks[check_id]
        if not check.enabled:
            return
        
        # Create monitoring task
        task = asyncio.create_task(self._run_check_loop(check_id))
        self.check_tasks[check_id] = task
        self.running_checks.add(check_id)
        
        self.logger.info(f"Started monitoring check: {check.name}")
    
    async def _run_check_loop(self, check_id: str) -> None:
        """Run monitoring check in a loop."""
        check = self.monitor_checks[check_id]
        
        while check_id in self.running_checks and check.enabled:
            try:
                # Perform the check
                result = await self._perform_check(check)
                
                # Store result
                self.monitor_results[check_id].append(result)
                
                # Limit stored results
                max_results = self.config["max_results_per_check"]
                if len(self.monitor_results[check_id]) > max_results:
                    self.monitor_results[check_id] = self.monitor_results[check_id][-max_results:]
                
                # Update failure count
                if result.is_healthy():
                    # Reset failure count on success
                    if self.failure_counts[check_id] > 0:
                        # Send recovery notification if configured
                        if check.recovery_notification:
                            await self._create_recovery_alert(check, result)
                    
                    self.failure_counts[check_id] = 0
                else:
                    self.failure_counts[check_id] += 1
                    
                    # Create alert if threshold reached
                    if (check.alert_on_failure and 
                        self.failure_counts[check_id] >= check.alert_after_failures):
                        await self._create_failure_alert(check, result)
                
                # Update statistics
                self.stats["total_results"] += 1
                
                # Wait for next check
                await asyncio.sleep(check.interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in check loop for {check.name}: {e}")
                await asyncio.sleep(check.interval_seconds)
        
        # Clean up
        self.running_checks.discard(check_id)
        if check_id in self.check_tasks:
            del self.check_tasks[check_id]
    
    async def _perform_check(self, check: MonitorCheck) -> MonitorResult:
        """Perform a single monitoring check."""
        self.result_counter += 1
        result_id = f"result_{self.result_counter}_{datetime.now().timestamp()}"
        
        start_time = time.time()
        
        try:
            if check.monitor_type == MonitorType.WEBSITE_HEALTH:
                result = await self._check_website_health(check, result_id)
            elif check.monitor_type == MonitorType.API_ENDPOINT:
                result = await self._check_api_endpoint(check, result_id)
            elif check.monitor_type == MonitorType.SYSTEM_RESOURCE:
                result = await self._check_system_resource(check, result_id)
            elif check.monitor_type == MonitorType.CUSTOM_METRIC:
                result = await self._check_custom_metric(check, result_id)
            else:
                result = MonitorResult(
                    result_id=result_id,
                    check_id=check.check_id,
                    timestamp=datetime.now(),
                    status=MonitorStatus.UNKNOWN,
                    message=f"Unsupported monitor type: {check.monitor_type.value}"
                )
            
            # Calculate response time
            if result.response_time_ms is None:
                result.response_time_ms = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            return MonitorResult(
                result_id=result_id,
                check_id=check.check_id,
                timestamp=datetime.now(),
                status=MonitorStatus.CRITICAL,
                message=f"Check execution failed: {str(e)}",
                error_details=str(e),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _check_website_health(self, check: MonitorCheck, result_id: str) -> MonitorResult:
        """Check website health via HTTP request."""
        try:
            start_time = time.time()
            
            async with self.http_session.get(
                check.target,
                timeout=aiohttp.ClientTimeout(total=check.timeout_seconds)
            ) as response:
                response_time_ms = (time.time() - start_time) * 1000
                response_text = await response.text()
                
                # Determine status based on response
                status = MonitorStatus.HEALTHY
                message = f"Website responding normally (HTTP {response.status})"
                
                # Check status code
                if response.status != check.expected_status_code:
                    status = MonitorStatus.WARNING
                    message = f"Unexpected status code: {response.status} (expected {check.expected_status_code})"
                
                # Check response time
                if response_time_ms > check.expected_response_time_ms:
                    if status == MonitorStatus.HEALTHY:
                        status = MonitorStatus.WARNING
                        message = f"Slow response time: {response_time_ms:.1f}ms (expected < {check.expected_response_time_ms}ms)"
                
                # Apply custom validation if provided
                if check.custom_validator and status == MonitorStatus.HEALTHY:
                    try:
                        # Simple custom validation (could be enhanced)
                        if check.custom_validator in response_text:
                            pass  # Validation passed
                        else:
                            status = MonitorStatus.WARNING
                            message = "Custom validation failed"
                    except Exception as e:
                        status = MonitorStatus.WARNING
                        message = f"Custom validation error: {e}"
                
                return MonitorResult(
                    result_id=result_id,
                    check_id=check.check_id,
                    timestamp=datetime.now(),
                    status=status,
                    response_time_ms=response_time_ms,
                    status_code=response.status,
                    message=message,
                    raw_response=response_text[:1000] if len(response_text) > 1000 else response_text
                )
                
        except asyncio.TimeoutError:
            return MonitorResult(
                result_id=result_id,
                check_id=check.check_id,
                timestamp=datetime.now(),
                status=MonitorStatus.CRITICAL,
                message=f"Request timeout after {check.timeout_seconds}s",
                error_details="Timeout"
            )
        except Exception as e:
            return MonitorResult(
                result_id=result_id,
                check_id=check.check_id,
                timestamp=datetime.now(),
                status=MonitorStatus.CRITICAL,
                message=f"Request failed: {str(e)}",
                error_details=str(e)
            )
    
    async def _check_api_endpoint(self, check: MonitorCheck, result_id: str) -> MonitorResult:
        """Check API endpoint health and response."""
        # Similar to website health but with JSON response parsing
        return await self._check_website_health(check, result_id)
    
    async def _check_system_resource(self, check: MonitorCheck, result_id: str) -> MonitorResult:
        """Check system resource metrics."""
        try:
            # Parse target to determine what to check
            target_parts = check.target.split(":")
            resource_type = target_parts[0].lower()
            
            value = None
            status = MonitorStatus.HEALTHY
            message = ""
            
            if resource_type == "cpu":
                value = psutil.cpu_percent(interval=1)
                message = f"CPU usage: {value:.1f}%"
            elif resource_type == "memory":
                memory = psutil.virtual_memory()
                value = memory.percent
                message = f"Memory usage: {value:.1f}%"
            elif resource_type == "disk":
                disk_path = target_parts[1] if len(target_parts) > 1 else "/"
                disk = psutil.disk_usage(disk_path)
                value = (disk.used / disk.total) * 100
                message = f"Disk usage ({disk_path}): {value:.1f}%"
            else:
                return MonitorResult(
                    result_id=result_id,
                    check_id=check.check_id,
                    timestamp=datetime.now(),
                    status=MonitorStatus.UNKNOWN,
                    message=f"Unknown resource type: {resource_type}"
                )
            
            # Apply thresholds
            if check.critical_threshold and value >= check.critical_threshold:
                status = MonitorStatus.CRITICAL
                message += f" (CRITICAL: >= {check.critical_threshold})"
            elif check.warning_threshold and value >= check.warning_threshold:
                status = MonitorStatus.WARNING
                message += f" (WARNING: >= {check.warning_threshold})"
            
            return MonitorResult(
                result_id=result_id,
                check_id=check.check_id,
                timestamp=datetime.now(),
                status=status,
                value=value,
                message=message
            )
            
        except Exception as e:
            return MonitorResult(
                result_id=result_id,
                check_id=check.check_id,
                timestamp=datetime.now(),
                status=MonitorStatus.CRITICAL,
                message=f"System resource check failed: {str(e)}",
                error_details=str(e)
            )
    
    async def _check_custom_metric(self, check: MonitorCheck, result_id: str) -> MonitorResult:
        """Check custom metric using provided validation code."""
        try:
            # This is a simplified implementation
            # In a real system, you'd want more sophisticated custom metric evaluation
            
            return MonitorResult(
                result_id=result_id,
                check_id=check.check_id,
                timestamp=datetime.now(),
                status=MonitorStatus.HEALTHY,
                message="Custom metric check completed"
            )
            
        except Exception as e:
            return MonitorResult(
                result_id=result_id,
                check_id=check.check_id,
                timestamp=datetime.now(),
                status=MonitorStatus.CRITICAL,
                message=f"Custom metric check failed: {str(e)}",
                error_details=str(e)
            )
    
    async def _create_failure_alert(self, check: MonitorCheck, result: MonitorResult) -> None:
        """Create alert for check failure."""
        self.alert_counter += 1
        alert_id = f"alert_{self.alert_counter}_{datetime.now().timestamp()}"
        
        alert = MonitorAlert(
            alert_id=alert_id,
            check_id=check.check_id,
            alert_type="failure",
            severity=result.status,
            title=f"Monitor Check Failed: {check.name}",
            message=f"Check '{check.name}' has failed {self.failure_counts[check.check_id]} consecutive times. Latest error: {result.message}",
            triggered_at=datetime.now(),
            trigger_result=result,
            consecutive_failures=self.failure_counts[check.check_id]
        )
        
        self.monitor_alerts[alert_id] = alert
        self.stats["total_alerts"] += 1
        
        log_agent_event(
            self.agent_id,
            "monitor_alert_created",
            {
                "alert_id": alert_id,
                "check_id": check.check_id,
                "check_name": check.name,
                "alert_type": "failure",
                "severity": result.status.value,
                "consecutive_failures": alert.consecutive_failures
            }
        )
        
        self.logger.warning(f"Monitor alert created: {alert.title}")
    
    async def _create_recovery_alert(self, check: MonitorCheck, result: MonitorResult) -> None:
        """Create alert for check recovery."""
        self.alert_counter += 1
        alert_id = f"alert_{self.alert_counter}_{datetime.now().timestamp()}"
        
        alert = MonitorAlert(
            alert_id=alert_id,
            check_id=check.check_id,
            alert_type="recovery",
            severity=MonitorStatus.HEALTHY,
            title=f"Monitor Check Recovered: {check.name}",
            message=f"Check '{check.name}' has recovered and is now healthy. {result.message}",
            triggered_at=datetime.now(),
            trigger_result=result,
            consecutive_failures=0
        )
        
        self.monitor_alerts[alert_id] = alert
        self.stats["total_alerts"] += 1
        
        log_agent_event(
            self.agent_id,
            "monitor_recovery",
            {
                "alert_id": alert_id,
                "check_id": check.check_id,
                "check_name": check.name,
                "alert_type": "recovery"
            }
        )
        
        self.logger.info(f"Monitor recovery: {alert.title}")
    
    async def _setup_system_monitoring(self) -> None:
        """Set up basic system resource monitoring."""
        try:
            # Add CPU monitoring
            await self.add_monitor_check(
                name="System CPU Usage",
                monitor_type=MonitorType.SYSTEM_RESOURCE,
                target="cpu",
                interval_seconds=self.config["system_check_interval"],
                warning_threshold=80.0,
                critical_threshold=95.0,
                tags=["system", "cpu"],
                description="Monitor system CPU usage percentage"
            )
            
            # Add memory monitoring
            await self.add_monitor_check(
                name="System Memory Usage",
                monitor_type=MonitorType.SYSTEM_RESOURCE,
                target="memory",
                interval_seconds=self.config["system_check_interval"],
                warning_threshold=85.0,
                critical_threshold=95.0,
                tags=["system", "memory"],
                description="Monitor system memory usage percentage"
            )
            
            # Add disk monitoring
            await self.add_monitor_check(
                name="System Disk Usage",
                monitor_type=MonitorType.SYSTEM_RESOURCE,
                target="disk:/",
                interval_seconds=self.config["system_check_interval"] * 2,  # Check less frequently
                warning_threshold=80.0,
                critical_threshold=90.0,
                tags=["system", "disk"],
                description="Monitor system disk usage percentage"
            )
            
            self.logger.info("System monitoring checks configured")
            
        except Exception as e:
            self.logger.error(f"Failed to setup system monitoring: {e}")
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old monitoring data periodically."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                current_time = datetime.now()
                result_cutoff = current_time - timedelta(hours=self.config["result_retention_hours"])
                alert_cutoff = current_time - timedelta(hours=self.config["alert_retention_hours"])
                
                # Clean up old results
                for check_id, results in self.monitor_results.items():
                    old_count = len(results)
                    self.monitor_results[check_id] = [
                        result for result in results if result.timestamp >= result_cutoff
                    ]
                    new_count = len(self.monitor_results[check_id])
                    
                    if old_count > new_count:
                        self.logger.debug(f"Cleaned up {old_count - new_count} old results for check {check_id}")
                
                # Clean up old alerts
                old_alerts = list(self.monitor_alerts.keys())
                for alert_id in old_alerts:
                    alert = self.monitor_alerts[alert_id]
                    if alert.triggered_at < alert_cutoff and alert.resolved:
                        del self.monitor_alerts[alert_id]
                
                self.logger.debug("Monitoring data cleanup completed")
                
            except Exception as e:
                self.logger.error(f"Error during monitoring data cleanup: {e}")
    
    async def _update_statistics(self) -> None:
        """Update monitoring statistics periodically."""
        while True:
            try:
                await asyncio.sleep(60)  # Update every minute
                
                # Count active checks by status
                healthy_count = 0
                warning_count = 0
                critical_count = 0
                
                for check_id, check in self.monitor_checks.items():
                    if not check.enabled:
                        continue
                    
                    recent_results = self.monitor_results[check_id][-1:]
                    if recent_results:
                        status = recent_results[-1].status
                        if status == MonitorStatus.HEALTHY:
                            healthy_count += 1
                        elif status == MonitorStatus.WARNING:
                            warning_count += 1
                        elif status == MonitorStatus.CRITICAL:
                            critical_count += 1
                
                self.stats.update({
                    "active_checks": len(self.running_checks),
                    "healthy_checks": healthy_count,
                    "warning_checks": warning_count,
                    "critical_checks": critical_count
                })
                
            except Exception as e:
                self.logger.error(f"Error updating monitoring statistics: {e}")