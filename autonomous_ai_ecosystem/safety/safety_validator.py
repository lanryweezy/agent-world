"""
Comprehensive safety validation system.

This module implements code injection detection and prevention,
resource usage monitoring and limiting, and behavior anomaly detection.
"""

import asyncio
import ast
import re
import psutil
try:
    import resource
except ImportError:
    resource = None  # Not available on Windows
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import hashlib

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class ThreatLevel(Enum):
    """Threat levels for security issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ViolationType(Enum):
    """Types of safety violations."""
    CODE_INJECTION = "code_injection"
    RESOURCE_ABUSE = "resource_abuse"
    BEHAVIOR_ANOMALY = "behavior_anomaly"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MALICIOUS_CODE = "malicious_code"
    SYSTEM_MANIPULATION = "system_manipulation"
    DATA_EXFILTRATION = "data_exfiltration"


class ResourceType(Enum):
    """Types of system resources to monitor."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    FILE_HANDLES = "file_handles"
    PROCESSES = "processes"


@dataclass
class SafetyViolation:
    """Represents a detected safety violation."""
    violation_id: str
    agent_id: str
    violation_type: ViolationType
    threat_level: ThreatLevel
    
    # Violation details
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Detection information
    detected_at: datetime = field(default_factory=datetime.now)
    detection_method: str = ""
    confidence_score: float = 0.0
    
    # Response information
    action_taken: str = ""
    blocked: bool = False
    escalated: bool = False
    
    # Resolution
    resolved: bool = False
    resolution_notes: str = ""
    resolved_at: Optional[datetime] = None


@dataclass
class ResourceUsage:
    """Represents current resource usage for an agent."""
    agent_id: str
    timestamp: datetime
    
    # Resource metrics
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_io_mb: float = 0.0
    network_io_mb: float = 0.0
    file_handles: int = 0
    process_count: int = 0
    
    # Calculated metrics
    cpu_trend: float = 0.0  # Rate of change
    memory_trend: float = 0.0
    anomaly_score: float = 0.0


@dataclass
class BehaviorPattern:
    """Represents a behavior pattern for anomaly detection."""
    pattern_id: str
    agent_id: str
    pattern_type: str
    
    # Pattern characteristics
    frequency: float = 0.0
    duration: float = 0.0
    resource_signature: Dict[str, float] = field(default_factory=dict)
    
    # Statistical measures
    mean_values: Dict[str, float] = field(default_factory=dict)
    std_deviations: Dict[str, float] = field(default_factory=dict)
    
    # Pattern metadata
    first_observed: datetime = field(default_factory=datetime.now)
    last_observed: datetime = field(default_factory=datetime.now)
    observation_count: int = 0
    confidence: float = 0.0


class ComprehensiveSafetyValidator(AgentModule):
    """
    Comprehensive safety validation system.
    
    Provides code injection detection, resource monitoring,
    and behavior anomaly detection for agent safety.
    """
    
    def __init__(self, agent_id: str = "safety_validator"):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "safety_validator")
        
        # Core data structures
        self.violations: Dict[str, SafetyViolation] = {}
        self.resource_usage_history: Dict[str, List[ResourceUsage]] = {}
        self.behavior_patterns: Dict[str, BehaviorPattern] = {}
        
        # Active monitoring
        self.monitored_agents: Set[str] = set()
        self.resource_limits: Dict[str, Dict[ResourceType, float]] = {}
        
        # Configuration
        self.config = {
            "resource_monitoring_interval": 5,  # seconds
            "resource_history_limit": 1000,
            "anomaly_detection_window": 100,  # number of samples
            "violation_retention_days": 30,
            "auto_block_critical_threats": True,
            "escalate_repeated_violations": True,
            "max_violations_per_agent": 10,
            
            # Resource limits (per agent)
            "default_resource_limits": {
                ResourceType.CPU: 50.0,  # percent
                ResourceType.MEMORY: 1024.0,  # MB
                ResourceType.DISK: 100.0,  # MB/s
                ResourceType.NETWORK: 50.0,  # MB/s
                ResourceType.FILE_HANDLES: 100,
                ResourceType.PROCESSES: 5
            },
            
            # Code injection patterns
            "dangerous_patterns": [
                r'eval\s*\(',
                r'exec\s*\(',
                r'__import__\s*\(',
                r'compile\s*\(',
                r'open\s*\([^)]*["\']w["\']',
                r'subprocess\.',
                r'os\.system',
                r'os\.popen',
                r'pickle\.loads',
                r'marshal\.loads'
            ],
            
            # Anomaly detection thresholds
            "anomaly_thresholds": {
                "cpu_spike": 3.0,  # standard deviations
                "memory_spike": 3.0,
                "unusual_pattern": 2.5,
                "resource_abuse": 2.0
            }
        }
        
        # Statistics
        self.stats = {
            "total_violations": 0,
            "violations_by_type": {vtype.value: 0 for vtype in ViolationType},
            "violations_by_threat": {threat.value: 0 for threat in ThreatLevel},
            "blocked_actions": 0,
            "escalated_incidents": 0,
            "agents_monitored": 0,
            "anomalies_detected": 0
        }
        
        # Counters
        self.violation_counter = 0
        self.pattern_counter = 0
        
        self.logger.info("Comprehensive safety validator initialized")
    
    async def initialize(self) -> None:
        """Initialize the safety validator."""
        try:
            # Start monitoring tasks
            asyncio.create_task(self._resource_monitoring_loop())
            asyncio.create_task(self._anomaly_detection_loop())
            asyncio.create_task(self._cleanup_old_data())
            
            self.logger.info("Safety validator initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize safety validator: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the safety validator."""
        try:
            self.logger.info("Safety validator shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during safety validator shutdown: {e}")
    
    async def validate_code(self, agent_id: str, code: str, context: str = "") -> Dict[str, Any]:
        """Validate code for security issues and injection attempts."""
        try:
            violations = []
            
            # Check for dangerous patterns
            for pattern in self.config["dangerous_patterns"]:
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for match in matches:
                    violation = await self._create_violation(
                        agent_id=agent_id,
                        violation_type=ViolationType.CODE_INJECTION,
                        threat_level=ThreatLevel.HIGH,
                        description=f"Dangerous code pattern detected: {pattern}",
                        evidence={
                            "pattern": pattern,
                            "match": match.group(),
                            "position": match.span(),
                            "code_snippet": code[max(0, match.start()-50):match.end()+50]
                        },
                        context={"validation_context": context},
                        detection_method="pattern_matching"
                    )
                    violations.append(violation)
            
            # AST-based analysis
            try:
                tree = ast.parse(code)
                ast_violations = await self._analyze_ast(agent_id, tree, code, context)
                violations.extend(ast_violations)
            except SyntaxError as e:
                # Syntax errors might indicate obfuscated malicious code
                violation = await self._create_violation(
                    agent_id=agent_id,
                    violation_type=ViolationType.MALICIOUS_CODE,
                    threat_level=ThreatLevel.MEDIUM,
                    description=f"Syntax error in code (possible obfuscation): {str(e)}",
                    evidence={"syntax_error": str(e), "line": e.lineno},
                    context={"validation_context": context},
                    detection_method="syntax_analysis"
                )
                violations.append(violation)
            
            # Determine overall safety
            is_safe = len(violations) == 0
            max_threat = ThreatLevel.LOW
            
            if violations:
                threat_levels = [v.threat_level for v in violations]
                threat_order = [ThreatLevel.LOW, ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL, ThreatLevel.EMERGENCY]
                max_threat = max(threat_levels, key=lambda t: threat_order.index(t))
            
            result = {
                "is_safe": is_safe,
                "threat_level": max_threat.value,
                "violations": [v.violation_id for v in violations],
                "violation_count": len(violations),
                "blocked": max_threat in [ThreatLevel.CRITICAL, ThreatLevel.EMERGENCY] and self.config["auto_block_critical_threats"]
            }
            
            # Log validation result
            log_agent_event(
                agent_id,
                "code_validation_completed",
                {
                    "is_safe": is_safe,
                    "threat_level": max_threat.value,
                    "violation_count": len(violations),
                    "context": context
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to validate code: {e}")
            return {"is_safe": False, "error": str(e)}
    
    async def monitor_agent_resources(self, agent_id: str) -> None:
        """Start monitoring resources for a specific agent."""
        try:
            self.monitored_agents.add(agent_id)
            
            # Set default resource limits if not already set
            if agent_id not in self.resource_limits:
                self.resource_limits[agent_id] = self.config["default_resource_limits"].copy()
            
            # Initialize resource usage history
            if agent_id not in self.resource_usage_history:
                self.resource_usage_history[agent_id] = []
            
            self.stats["agents_monitored"] = len(self.monitored_agents)
            
            log_agent_event(
                agent_id,
                "resource_monitoring_started",
                {"limits": self.resource_limits[agent_id]}
            )
            
            self.logger.info(f"Started resource monitoring for agent {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to start resource monitoring: {e}")
    
    async def stop_monitoring_agent(self, agent_id: str) -> None:
        """Stop monitoring resources for a specific agent."""
        try:
            self.monitored_agents.discard(agent_id)
            self.stats["agents_monitored"] = len(self.monitored_agents)
            
            log_agent_event(agent_id, "resource_monitoring_stopped", {})
            
            self.logger.info(f"Stopped resource monitoring for agent {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to stop resource monitoring: {e}")
    
    async def set_resource_limits(self, agent_id: str, limits: Dict[ResourceType, float]) -> None:
        """Set resource limits for a specific agent."""
        try:
            if agent_id not in self.resource_limits:
                self.resource_limits[agent_id] = self.config["default_resource_limits"].copy()
            
            self.resource_limits[agent_id].update(limits)
            
            log_agent_event(
                agent_id,
                "resource_limits_updated",
                {"new_limits": limits}
            )
            
            self.logger.info(f"Updated resource limits for agent {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to set resource limits: {e}")
    
    async def get_agent_violations(self, agent_id: str, limit: int = 50) -> List[SafetyViolation]:
        """Get safety violations for a specific agent."""
        try:
            agent_violations = [
                violation for violation in self.violations.values()
                if violation.agent_id == agent_id
            ]
            
            # Sort by detection time (most recent first)
            agent_violations.sort(key=lambda v: v.detected_at, reverse=True)
            
            return agent_violations[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get agent violations: {e}")
            return []
    
    async def resolve_violation(self, violation_id: str, resolution_notes: str = "") -> bool:
        """Mark a violation as resolved."""
        try:
            if violation_id not in self.violations:
                return False
            
            violation = self.violations[violation_id]
            violation.resolved = True
            violation.resolution_notes = resolution_notes
            violation.resolved_at = datetime.now()
            
            log_agent_event(
                violation.agent_id,
                "violation_resolved",
                {
                    "violation_id": violation_id,
                    "violation_type": violation.violation_type.value,
                    "resolution_notes": resolution_notes
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resolve violation: {e}")
            return False
    
    async def _create_violation(
        self,
        agent_id: str,
        violation_type: ViolationType,
        threat_level: ThreatLevel,
        description: str,
        evidence: Dict[str, Any],
        context: Dict[str, Any],
        detection_method: str,
        confidence_score: float = 1.0
    ) -> SafetyViolation:
        """Create and store a safety violation."""
        try:
            self.violation_counter += 1
            violation_id = f"violation_{self.violation_counter}_{datetime.now().timestamp()}"
            
            violation = SafetyViolation(
                violation_id=violation_id,
                agent_id=agent_id,
                violation_type=violation_type,
                threat_level=threat_level,
                description=description,
                evidence=evidence,
                context=context,
                detection_method=detection_method,
                confidence_score=confidence_score
            )
            
            # Auto-block critical threats
            if (threat_level in [ThreatLevel.CRITICAL, ThreatLevel.EMERGENCY] and 
                self.config["auto_block_critical_threats"]):
                violation.blocked = True
                violation.action_taken = "auto_blocked"
                self.stats["blocked_actions"] += 1
            
            # Check for escalation
            agent_violations = await self.get_agent_violations(agent_id, limit=10)
            if (len(agent_violations) >= self.config["max_violations_per_agent"] and 
                self.config["escalate_repeated_violations"]):
                violation.escalated = True
                violation.action_taken += " escalated"
                self.stats["escalated_incidents"] += 1
            
            # Store violation
            self.violations[violation_id] = violation
            
            # Update statistics
            self.stats["total_violations"] += 1
            self.stats["violations_by_type"][violation_type.value] += 1
            self.stats["violations_by_threat"][threat_level.value] += 1
            
            log_agent_event(
                agent_id,
                "safety_violation_detected",
                {
                    "violation_id": violation_id,
                    "violation_type": violation_type.value,
                    "threat_level": threat_level.value,
                    "blocked": violation.blocked,
                    "escalated": violation.escalated
                }
            )
            
            self.logger.warning(f"Safety violation detected: {violation_id} for agent {agent_id}")
            
            return violation
            
        except Exception as e:
            self.logger.error(f"Failed to create violation: {e}")
            raise
    
    async def _analyze_ast(self, agent_id: str, tree: ast.AST, code: str, context: str) -> List[SafetyViolation]:
        """Analyze AST for security issues."""
        violations = []
        
        try:
            for node in ast.walk(tree):
                # Check for dangerous function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        if func_name in ['eval', 'exec', 'compile', '__import__']:
                            violation = await self._create_violation(
                                agent_id=agent_id,
                                violation_type=ViolationType.CODE_INJECTION,
                                threat_level=ThreatLevel.CRITICAL,
                                description=f"Dangerous function call: {func_name}",
                                evidence={"function": func_name, "line": node.lineno},
                                context={"validation_context": context},
                                detection_method="ast_analysis"
                            )
                            violations.append(violation)
                
                # Check for file operations
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == 'open':
                        # Check if opening files for writing
                        if len(node.args) > 1:
                            mode_arg = node.args[1]
                            if isinstance(mode_arg, ast.Str) and 'w' in mode_arg.s:
                                violation = await self._create_violation(
                                    agent_id=agent_id,
                                    violation_type=ViolationType.SYSTEM_MANIPULATION,
                                    threat_level=ThreatLevel.MEDIUM,
                                    description="File write operation detected",
                                    evidence={"operation": "file_write", "line": node.lineno},
                                    context={"validation_context": context},
                                    detection_method="ast_analysis"
                                )
                                violations.append(violation)
                
                # Check for attribute access to dangerous modules
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        if node.value.id in ['os', 'sys', 'subprocess']:
                            violation = await self._create_violation(
                                agent_id=agent_id,
                                violation_type=ViolationType.SYSTEM_MANIPULATION,
                                threat_level=ThreatLevel.HIGH,
                                description=f"System module access: {node.value.id}.{node.attr}",
                                evidence={"module": node.value.id, "attribute": node.attr, "line": node.lineno},
                                context={"validation_context": context},
                                detection_method="ast_analysis"
                            )
                            violations.append(violation)
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Failed to analyze AST: {e}")
            return []
    
    async def _collect_resource_usage(self, agent_id: str) -> Optional[ResourceUsage]:
        """Collect current resource usage for an agent."""
        try:
            # In a real implementation, you would track per-agent resource usage
            # For now, we'll simulate with system-wide metrics
            
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            net_io = psutil.net_io_counters()
            
            usage = ResourceUsage(
                agent_id=agent_id,
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_mb=memory.used / (1024 * 1024),
                disk_io_mb=(disk_io.read_bytes + disk_io.write_bytes) / (1024 * 1024) if disk_io else 0,
                network_io_mb=(net_io.bytes_sent + net_io.bytes_recv) / (1024 * 1024) if net_io else 0,
                file_handles=len(psutil.Process().open_files()) if hasattr(psutil.Process(), 'open_files') else 0,
                process_count=len(psutil.pids())
            )
            
            # Calculate trends if we have history
            history = self.resource_usage_history.get(agent_id, [])
            if len(history) > 1:
                prev_usage = history[-1]
                time_diff = (usage.timestamp - prev_usage.timestamp).total_seconds()
                if time_diff > 0:
                    usage.cpu_trend = (usage.cpu_percent - prev_usage.cpu_percent) / time_diff
                    usage.memory_trend = (usage.memory_mb - prev_usage.memory_mb) / time_diff
            
            return usage
            
        except Exception as e:
            self.logger.error(f"Failed to collect resource usage: {e}")
            return None
    
    async def _check_resource_violations(self, agent_id: str, usage: ResourceUsage) -> List[SafetyViolation]:
        """Check for resource usage violations."""
        violations = []
        
        try:
            limits = self.resource_limits.get(agent_id, self.config["default_resource_limits"])
            
            # Check CPU usage
            if usage.cpu_percent > limits[ResourceType.CPU]:
                violation = await self._create_violation(
                    agent_id=agent_id,
                    violation_type=ViolationType.RESOURCE_ABUSE,
                    threat_level=ThreatLevel.MEDIUM,
                    description=f"CPU usage exceeded limit: {usage.cpu_percent:.1f}% > {limits[ResourceType.CPU]}%",
                    evidence={"current_usage": usage.cpu_percent, "limit": limits[ResourceType.CPU], "resource": "cpu"},
                    context={"timestamp": usage.timestamp.isoformat()},
                    detection_method="resource_monitoring"
                )
                violations.append(violation)
            
            # Check memory usage
            if usage.memory_mb > limits[ResourceType.MEMORY]:
                violation = await self._create_violation(
                    agent_id=agent_id,
                    violation_type=ViolationType.RESOURCE_ABUSE,
                    threat_level=ThreatLevel.MEDIUM,
                    description=f"Memory usage exceeded limit: {usage.memory_mb:.1f}MB > {limits[ResourceType.MEMORY]}MB",
                    evidence={"current_usage": usage.memory_mb, "limit": limits[ResourceType.MEMORY], "resource": "memory"},
                    context={"timestamp": usage.timestamp.isoformat()},
                    detection_method="resource_monitoring"
                )
                violations.append(violation)
            
            # Check file handles
            if usage.file_handles > limits[ResourceType.FILE_HANDLES]:
                violation = await self._create_violation(
                    agent_id=agent_id,
                    violation_type=ViolationType.RESOURCE_ABUSE,
                    threat_level=ThreatLevel.HIGH,
                    description=f"File handles exceeded limit: {usage.file_handles} > {limits[ResourceType.FILE_HANDLES]}",
                    evidence={"current_usage": usage.file_handles, "limit": limits[ResourceType.FILE_HANDLES], "resource": "file_handles"},
                    context={"timestamp": usage.timestamp.isoformat()},
                    detection_method="resource_monitoring"
                )
                violations.append(violation)
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Failed to check resource violations: {e}")
            return []
    
    async def _detect_behavior_anomalies(self, agent_id: str, usage: ResourceUsage) -> List[SafetyViolation]:
        """Detect behavioral anomalies in resource usage patterns."""
        violations = []
        
        try:
            history = self.resource_usage_history.get(agent_id, [])
            if len(history) < self.config["anomaly_detection_window"]:
                return violations  # Not enough data for anomaly detection
            
            # Calculate statistical measures for recent history
            recent_history = history[-self.config["anomaly_detection_window"]:]
            
            # CPU anomaly detection
            cpu_values = [h.cpu_percent for h in recent_history]
            cpu_mean = sum(cpu_values) / len(cpu_values)
            cpu_std = (sum((x - cpu_mean) ** 2 for x in cpu_values) / len(cpu_values)) ** 0.5
            
            if cpu_std > 0 and abs(usage.cpu_percent - cpu_mean) > self.config["anomaly_thresholds"]["cpu_spike"] * cpu_std:
                violation = await self._create_violation(
                    agent_id=agent_id,
                    violation_type=ViolationType.BEHAVIOR_ANOMALY,
                    threat_level=ThreatLevel.MEDIUM,
                    description=f"CPU usage anomaly detected: {usage.cpu_percent:.1f}% (mean: {cpu_mean:.1f}%, std: {cpu_std:.1f}%)",
                    evidence={
                        "current_value": usage.cpu_percent,
                        "mean": cpu_mean,
                        "std_dev": cpu_std,
                        "z_score": (usage.cpu_percent - cpu_mean) / cpu_std,
                        "resource": "cpu"
                    },
                    context={"timestamp": usage.timestamp.isoformat()},
                    detection_method="statistical_anomaly"
                )
                violations.append(violation)
            
            # Memory anomaly detection
            memory_values = [h.memory_mb for h in recent_history]
            memory_mean = sum(memory_values) / len(memory_values)
            memory_std = (sum((x - memory_mean) ** 2 for x in memory_values) / len(memory_values)) ** 0.5
            
            if memory_std > 0 and abs(usage.memory_mb - memory_mean) > self.config["anomaly_thresholds"]["memory_spike"] * memory_std:
                violation = await self._create_violation(
                    agent_id=agent_id,
                    violation_type=ViolationType.BEHAVIOR_ANOMALY,
                    threat_level=ThreatLevel.MEDIUM,
                    description=f"Memory usage anomaly detected: {usage.memory_mb:.1f}MB (mean: {memory_mean:.1f}MB, std: {memory_std:.1f}MB)",
                    evidence={
                        "current_value": usage.memory_mb,
                        "mean": memory_mean,
                        "std_dev": memory_std,
                        "z_score": (usage.memory_mb - memory_mean) / memory_std,
                        "resource": "memory"
                    },
                    context={"timestamp": usage.timestamp.isoformat()},
                    detection_method="statistical_anomaly"
                )
                violations.append(violation)
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Failed to detect behavior anomalies: {e}")
            return []
    
    async def _resource_monitoring_loop(self) -> None:
        """Main resource monitoring loop."""
        while True:
            try:
                for agent_id in list(self.monitored_agents):
                    # Collect resource usage
                    usage = await self._collect_resource_usage(agent_id)
                    if not usage:
                        continue
                    
                    # Store usage history
                    if agent_id not in self.resource_usage_history:
                        self.resource_usage_history[agent_id] = []
                    
                    self.resource_usage_history[agent_id].append(usage)
                    
                    # Limit history size
                    if len(self.resource_usage_history[agent_id]) > self.config["resource_history_limit"]:
                        self.resource_usage_history[agent_id] = self.resource_usage_history[agent_id][-self.config["resource_history_limit"]:]
                    
                    # Check for violations
                    resource_violations = await self._check_resource_violations(agent_id, usage)
                    
                    # Check for anomalies
                    anomaly_violations = await self._detect_behavior_anomalies(agent_id, usage)
                    
                    if anomaly_violations:
                        self.stats["anomalies_detected"] += len(anomaly_violations)
                
                # Sleep until next monitoring cycle
                await asyncio.sleep(self.config["resource_monitoring_interval"])
                
            except Exception as e:
                self.logger.error(f"Error in resource monitoring loop: {e}")
                await asyncio.sleep(self.config["resource_monitoring_interval"])
    
    async def _anomaly_detection_loop(self) -> None:
        """Dedicated anomaly detection loop."""
        while True:
            try:
                # Update behavior patterns for all monitored agents
                for agent_id in list(self.monitored_agents):
                    await self._update_behavior_patterns(agent_id)
                
                # Sleep for 1 minute
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in anomaly detection loop: {e}")
                await asyncio.sleep(60)
    
    async def _update_behavior_patterns(self, agent_id: str) -> None:
        """Update behavior patterns for an agent."""
        try:
            history = self.resource_usage_history.get(agent_id, [])
            if len(history) < 10:  # Need minimum data
                return
            
            # Analyze recent patterns (simplified implementation)
            recent_history = history[-50:]  # Last 50 samples
            
            # Calculate pattern characteristics
            cpu_values = [h.cpu_percent for h in recent_history]
            memory_values = [h.memory_mb for h in recent_history]
            
            pattern_id = f"pattern_{agent_id}_{datetime.now().timestamp()}"
            
            pattern = BehaviorPattern(
                pattern_id=pattern_id,
                agent_id=agent_id,
                pattern_type="resource_usage",
                frequency=len(recent_history) / (recent_history[-1].timestamp - recent_history[0].timestamp).total_seconds(),
                mean_values={
                    "cpu": sum(cpu_values) / len(cpu_values),
                    "memory": sum(memory_values) / len(memory_values)
                },
                std_deviations={
                    "cpu": (sum((x - sum(cpu_values) / len(cpu_values)) ** 2 for x in cpu_values) / len(cpu_values)) ** 0.5,
                    "memory": (sum((x - sum(memory_values) / len(memory_values)) ** 2 for x in memory_values) / len(memory_values)) ** 0.5
                },
                observation_count=len(recent_history),
                confidence=min(1.0, len(recent_history) / 100.0)
            )
            
            self.behavior_patterns[pattern_id] = pattern
            
        except Exception as e:
            self.logger.error(f"Failed to update behavior patterns: {e}")
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old violations and resource usage data."""
        while True:
            try:
                cutoff_date = datetime.now() - timedelta(days=self.config["violation_retention_days"])
                
                # Clean up old violations
                old_violations = [
                    v_id for v_id, violation in self.violations.items()
                    if violation.detected_at < cutoff_date and violation.resolved
                ]
                
                for v_id in old_violations:
                    del self.violations[v_id]
                
                # Clean up old resource usage data
                for agent_id in list(self.resource_usage_history.keys()):
                    history = self.resource_usage_history[agent_id]
                    recent_history = [
                        usage for usage in history
                        if usage.timestamp > cutoff_date
                    ]
                    self.resource_usage_history[agent_id] = recent_history
                
                if old_violations:
                    self.logger.info(f"Cleaned up {len(old_violations)} old violations")
                
                # Sleep for 24 hours
                await asyncio.sleep(86400)
                
            except Exception as e:
                self.logger.error(f"Error in cleanup: {e}")
                await asyncio.sleep(86400)