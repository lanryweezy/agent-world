"""
Agent process management and lifecycle orchestration.

This module implements agent spawning, monitoring, termination,
sleep/wake cycle orchestration, and health monitoring.
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class AgentStatus(Enum):
    """Status of an agent process."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    SLEEPING = "sleeping"
    MODIFYING = "modifying"
    RESTARTING = "restarting"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ProcessState(Enum):
    """State of the underlying process."""
    STARTING = "starting"
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    ZOMBIE = "zombie"


class LifecycleEvent(Enum):
    """Types of lifecycle events."""
    SPAWN = "spawn"
    START = "start"
    SLEEP = "sleep"
    WAKE = "wake"
    MODIFY = "modify"
    RESTART = "restart"
    STOP = "stop"
    CRASH = "crash"
    HEALTH_CHECK = "health_check"


@dataclass
class AgentProcess:
    """Represents a managed agent process."""
    agent_id: str
    process_id: str
    
    # Process information
    pid: Optional[int] = None
    process: Optional[subprocess.Popen] = None
    psutil_process: Optional[psutil.Process] = None
    
    # Status and state
    status: AgentStatus = AgentStatus.INITIALIZING
    process_state: ProcessState = ProcessState.STARTING
    
    # Configuration
    executable_path: str = ""
    working_directory: str = ""
    environment_vars: Dict[str, str] = field(default_factory=dict)
    command_args: List[str] = field(default_factory=list)
    
    # Resource limits
    max_memory_mb: int = 1024
    max_cpu_percent: float = 50.0
    max_runtime_hours: int = 24
    
    # Lifecycle tracking
    spawn_time: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    restart_count: int = 0
    
    # Sleep/wake cycle
    sleep_schedule: Optional[Dict[str, Any]] = None
    sleep_start_time: Optional[datetime] = None
    wake_time: Optional[datetime] = None
    
    # Health monitoring
    health_check_interval: int = 30  # seconds
    health_check_failures: int = 0
    max_health_failures: int = 3
    
    # Performance metrics
    cpu_usage: float = 0.0
    memory_usage_mb: float = 0.0
    uptime_seconds: float = 0.0
    
    # Modification tracking
    modification_in_progress: bool = False
    modification_backup_path: Optional[str] = None
    
    def is_alive(self) -> bool:
        """Check if the process is alive."""
        if self.psutil_process:
            try:
                return self.psutil_process.is_running()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
        return False
    
    def get_uptime(self) -> float:
        """Get process uptime in seconds."""
        if self.spawn_time:
            return (datetime.now() - self.spawn_time).total_seconds()
        return 0.0
    
    def should_sleep(self) -> bool:
        """Check if agent should enter sleep mode."""
        if not self.sleep_schedule:
            return False
        
        current_time = datetime.now()
        
        # Check if it's sleep time based on schedule
        if "sleep_hour" in self.sleep_schedule:
            sleep_hour = self.sleep_schedule["sleep_hour"]
            if current_time.hour == sleep_hour and self.status == AgentStatus.RUNNING:
                return True
        
        # Check if agent has been idle too long
        if "idle_sleep_minutes" in self.sleep_schedule and self.last_activity:
            idle_minutes = (current_time - self.last_activity).total_seconds() / 60
            if idle_minutes > self.sleep_schedule["idle_sleep_minutes"]:
                return True
        
        return False
    
    def should_wake(self) -> bool:
        """Check if agent should wake up."""
        if self.status != AgentStatus.SLEEPING:
            return False
        
        current_time = datetime.now()
        
        # Check scheduled wake time
        if self.wake_time and current_time >= self.wake_time:
            return True
        
        # Check if sleep duration exceeded
        if self.sleep_start_time and self.sleep_schedule:
            sleep_duration_hours = self.sleep_schedule.get("sleep_duration_hours", 8)
            if (current_time - self.sleep_start_time).total_seconds() > sleep_duration_hours * 3600:
                return True
        
        return False


@dataclass
class LifecycleEventRecord:
    """Record of a lifecycle event."""
    event_id: str
    agent_id: str
    event_type: LifecycleEvent
    timestamp: datetime
    
    # Event details
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    previous_status: Optional[AgentStatus] = None
    new_status: Optional[AgentStatus] = None
    
    # Performance data
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    
    # Success/failure
    success: bool = True
    error_message: Optional[str] = None


class AgentManager(AgentModule):
    """
    Agent process management and lifecycle orchestration system.
    
    Provides agent spawning, monitoring, termination, sleep/wake cycles,
    and health monitoring capabilities.
    """
    
    def __init__(self, agent_id: str = "agent_manager"):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "agent_manager")
        
        # Core data structures
        self.agents: Dict[str, AgentProcess] = {}
        self.lifecycle_events: Dict[str, LifecycleEventRecord] = {}
        
        # Management tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.lifecycle_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.config = {
            "agent_executable": "python",
            "agent_script": "agent_runner.py",
            "default_working_dir": "agent_instances",
            "health_check_interval": 30,
            "lifecycle_check_interval": 60,
            "max_agents": 100,
            "auto_restart_failed": True,
            "enable_sleep_wake": True,
            "modification_timeout": 300,
            "shutdown_timeout": 30,
            "resource_monitoring": True
        }
        
        # Statistics
        self.stats = {
            "total_agents_spawned": 0,
            "active_agents": 0,
            "sleeping_agents": 0,
            "failed_agents": 0,
            "total_restarts": 0,
            "total_modifications": 0,
            "average_uptime_hours": 0.0,
            "agents_by_status": {status.value: 0 for status in AgentStatus},
            "lifecycle_events": {event.value: 0 for event in LifecycleEvent}
        }
        
        # Counters
        self.process_counter = 0
        self.event_counter = 0
        
        # Shutdown handlers
        self.shutdown_handlers: List[Callable] = []
        
        self.logger.info("Agent manager initialized")
    
    async def initialize(self) -> None:
        """Initialize the agent manager."""
        try:
            # Create working directory
            os.makedirs(self.config["default_working_dir"], exist_ok=True)
            
            # Start monitoring tasks
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.lifecycle_task = asyncio.create_task(self._lifecycle_loop())
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            self.logger.info("Agent manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize agent manager: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the agent manager."""
        try:
            # Stop all agents gracefully
            await self.stop_all_agents()
            
            # Cancel monitoring tasks
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            if self.lifecycle_task:
                self.lifecycle_task.cancel()
                try:
                    await self.lifecycle_task
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("Agent manager shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during agent manager shutdown: {e}")
    
    async def spawn_agent(
        self,
        agent_id: str,
        config: Optional[Dict[str, Any]] = None,
        environment: Optional[Dict[str, str]] = None,
        resource_limits: Optional[Dict[str, Any]] = None
    ) -> str:
        """Spawn a new agent process."""
        try:
            if len(self.agents) >= self.config["max_agents"]:
                raise Exception(f"Maximum agent limit reached: {self.config['max_agents']}")
            
            if agent_id in self.agents:
                raise Exception(f"Agent already exists: {agent_id}")
            
            # Create process ID
            self.process_counter += 1
            process_id = f"proc_{self.process_counter}_{datetime.now().timestamp()}"
            
            # Setup agent configuration
            agent_config = config or {}
            working_dir = os.path.join(
                self.config["default_working_dir"],
                agent_id
            )
            os.makedirs(working_dir, exist_ok=True)
            
            # Create agent process record
            agent_process = AgentProcess(
                agent_id=agent_id,
                process_id=process_id,
                executable_path=self.config["agent_executable"],
                working_directory=working_dir,
                environment_vars=environment or {},
                command_args=[self.config["agent_script"], agent_id],
                spawn_time=datetime.now()
            )
            
            # Apply resource limits
            if resource_limits:
                agent_process.max_memory_mb = resource_limits.get("max_memory_mb", 1024)
                agent_process.max_cpu_percent = resource_limits.get("max_cpu_percent", 50.0)
                agent_process.max_runtime_hours = resource_limits.get("max_runtime_hours", 24)
            
            # Setup sleep schedule if provided
            if "sleep_schedule" in agent_config:
                agent_process.sleep_schedule = agent_config["sleep_schedule"]
            
            # Start the process
            await self._start_agent_process(agent_process)
            
            # Store agent
            self.agents[agent_id] = agent_process
            
            # Record lifecycle event
            await self._record_lifecycle_event(
                agent_id=agent_id,
                event_type=LifecycleEvent.SPAWN,
                description=f"Agent spawned with process ID {process_id}",
                new_status=agent_process.status
            )
            
            # Update statistics
            self.stats["total_agents_spawned"] += 1
            self.stats["active_agents"] += 1
            self.stats["agents_by_status"][agent_process.status.value] += 1
            
            log_agent_event(
                agent_id,
                "agent_spawned",
                {
                    "process_id": process_id,
                    "pid": agent_process.pid,
                    "working_directory": working_dir
                }
            )
            
            self.logger.info(f"Agent spawned: {agent_id} (PID: {agent_process.pid})")
            
            return process_id
            
        except Exception as e:
            self.logger.error(f"Failed to spawn agent {agent_id}: {e}")
            return ""
    
    async def stop_agent(self, agent_id: str, graceful: bool = True) -> bool:
        """Stop an agent process."""
        try:
            if agent_id not in self.agents:
                return False
            
            agent_process = self.agents[agent_id]
            previous_status = agent_process.status
            agent_process.status = AgentStatus.STOPPING
            
            # Record lifecycle event
            await self._record_lifecycle_event(
                agent_id=agent_id,
                event_type=LifecycleEvent.STOP,
                description="Agent stop requested",
                previous_status=previous_status,
                new_status=agent_process.status
            )
            
            success = False
            
            if graceful:
                # Try graceful shutdown first
                success = await self._graceful_shutdown(agent_process)
            
            if not success:
                # Force termination
                success = await self._force_terminate(agent_process)
            
            if success:
                agent_process.status = AgentStatus.STOPPED
                self.stats["active_agents"] -= 1
                self.stats["agents_by_status"][AgentStatus.STOPPED.value] += 1
                
                log_agent_event(
                    agent_id,
                    "agent_stopped",
                    {
                        "process_id": agent_process.process_id,
                        "graceful": graceful,
                        "uptime_seconds": agent_process.get_uptime()
                    }
                )
                
                self.logger.info(f"Agent stopped: {agent_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to stop agent {agent_id}: {e}")
            return False
    
    async def restart_agent(self, agent_id: str) -> bool:
        """Restart an agent process."""
        try:
            if agent_id not in self.agents:
                return False
            
            agent_process = self.agents[agent_id]
            previous_status = agent_process.status
            agent_process.status = AgentStatus.RESTARTING
            
            # Record lifecycle event
            await self._record_lifecycle_event(
                agent_id=agent_id,
                event_type=LifecycleEvent.RESTART,
                description="Agent restart initiated",
                previous_status=previous_status,
                new_status=agent_process.status
            )
            
            # Stop current process
            await self._force_terminate(agent_process)
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Start new process
            success = await self._start_agent_process(agent_process)
            
            if success:
                agent_process.restart_count += 1
                agent_process.status = AgentStatus.RUNNING
                self.stats["total_restarts"] += 1
                
                log_agent_event(
                    agent_id,
                    "agent_restarted",
                    {
                        "process_id": agent_process.process_id,
                        "restart_count": agent_process.restart_count,
                        "new_pid": agent_process.pid
                    }
                )
                
                self.logger.info(f"Agent restarted: {agent_id} (restart #{agent_process.restart_count})")
            else:
                agent_process.status = AgentStatus.FAILED
                self.stats["failed_agents"] += 1
                
                self.logger.error(f"Failed to restart agent: {agent_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to restart agent {agent_id}: {e}")
            return False
    
    async def sleep_agent(self, agent_id: str, duration_hours: Optional[float] = None) -> bool:
        """Put an agent to sleep."""
        try:
            if agent_id not in self.agents:
                return False
            
            agent_process = self.agents[agent_id]
            
            if agent_process.status != AgentStatus.RUNNING:
                return False
            
            previous_status = agent_process.status
            agent_process.status = AgentStatus.SLEEPING
            agent_process.sleep_start_time = datetime.now()
            
            # Set wake time if duration specified
            if duration_hours:
                agent_process.wake_time = datetime.now() + timedelta(hours=duration_hours)
            
            # Suspend the process
            if agent_process.psutil_process:
                try:
                    agent_process.psutil_process.suspend()
                    agent_process.process_state = ProcessState.SUSPENDED
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    self.logger.warning(f"Could not suspend process for {agent_id}: {e}")
            
            # Record lifecycle event
            await self._record_lifecycle_event(
                agent_id=agent_id,
                event_type=LifecycleEvent.SLEEP,
                description=f"Agent put to sleep for {duration_hours or 'indefinite'} hours",
                previous_status=previous_status,
                new_status=agent_process.status
            )
            
            # Update statistics
            self.stats["active_agents"] -= 1
            self.stats["sleeping_agents"] += 1
            
            log_agent_event(
                agent_id,
                "agent_sleep",
                {
                    "process_id": agent_process.process_id,
                    "duration_hours": duration_hours,
                    "wake_time": agent_process.wake_time.isoformat() if agent_process.wake_time else None
                }
            )
            
            self.logger.info(f"Agent put to sleep: {agent_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to sleep agent {agent_id}: {e}")
            return False
    
    async def wake_agent(self, agent_id: str) -> bool:
        """Wake up a sleeping agent."""
        try:
            if agent_id not in self.agents:
                return False
            
            agent_process = self.agents[agent_id]
            
            if agent_process.status != AgentStatus.SLEEPING:
                return False
            
            previous_status = agent_process.status
            
            # Resume the process
            if agent_process.psutil_process:
                try:
                    agent_process.psutil_process.resume()
                    agent_process.process_state = ProcessState.ACTIVE
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    self.logger.warning(f"Could not resume process for {agent_id}: {e}")
                    # Process might have died, try restarting
                    return await self.restart_agent(agent_id)
            
            agent_process.status = AgentStatus.RUNNING
            agent_process.sleep_start_time = None
            agent_process.wake_time = None
            agent_process.last_activity = datetime.now()
            
            # Record lifecycle event
            await self._record_lifecycle_event(
                agent_id=agent_id,
                event_type=LifecycleEvent.WAKE,
                description="Agent woken up",
                previous_status=previous_status,
                new_status=agent_process.status
            )
            
            # Update statistics
            self.stats["sleeping_agents"] -= 1
            self.stats["active_agents"] += 1
            
            log_agent_event(
                agent_id,
                "agent_wake",
                {
                    "process_id": agent_process.process_id,
                    "sleep_duration_seconds": (datetime.now() - agent_process.sleep_start_time).total_seconds() if agent_process.sleep_start_time else 0
                }
            )
            
            self.logger.info(f"Agent woken up: {agent_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to wake agent {agent_id}: {e}")
            return False
    
    async def prepare_for_modification(self, agent_id: str) -> bool:
        """Prepare agent for code modification."""
        try:
            if agent_id not in self.agents:
                return False
            
            agent_process = self.agents[agent_id]
            
            if agent_process.modification_in_progress:
                return False
            
            previous_status = agent_process.status
            agent_process.status = AgentStatus.MODIFYING
            agent_process.modification_in_progress = True
            
            # Create backup of current state
            backup_path = await self._create_agent_backup(agent_process)
            agent_process.modification_backup_path = backup_path
            
            # Put agent to sleep for modification
            if agent_process.psutil_process and agent_process.psutil_process.is_running():
                try:
                    agent_process.psutil_process.suspend()
                    agent_process.process_state = ProcessState.SUSPENDED
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Record lifecycle event
            await self._record_lifecycle_event(
                agent_id=agent_id,
                event_type=LifecycleEvent.MODIFY,
                description="Agent prepared for modification",
                previous_status=previous_status,
                new_status=agent_process.status,
                metadata={"backup_path": backup_path}
            )
            
            self.stats["total_modifications"] += 1
            
            log_agent_event(
                agent_id,
                "agent_modification_prepared",
                {
                    "process_id": agent_process.process_id,
                    "backup_path": backup_path
                }
            )
            
            self.logger.info(f"Agent prepared for modification: {agent_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to prepare agent for modification {agent_id}: {e}")
            return False
    
    async def complete_modification(self, agent_id: str, success: bool = True) -> bool:
        """Complete agent modification and resume operation."""
        try:
            if agent_id not in self.agents:
                return False
            
            agent_process = self.agents[agent_id]
            
            if not agent_process.modification_in_progress:
                return False
            
            if success:
                # Modification successful, restart agent with new code
                await self._force_terminate(agent_process)
                await asyncio.sleep(1)
                
                restart_success = await self._start_agent_process(agent_process)
                
                if restart_success:
                    agent_process.status = AgentStatus.RUNNING
                    agent_process.modification_in_progress = False
                    agent_process.modification_backup_path = None
                    
                    self.logger.info(f"Agent modification completed successfully: {agent_id}")
                else:
                    # Restart failed, rollback
                    await self._rollback_modification(agent_process)
                    return False
            else:
                # Modification failed, rollback
                await self._rollback_modification(agent_process)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to complete modification for agent {agent_id}: {e}")
            return False
    
    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of an agent."""
        try:
            if agent_id not in self.agents:
                return None
            
            agent_process = self.agents[agent_id]
            
            # Update resource usage
            await self._update_resource_usage(agent_process)
            
            return {
                "agent_id": agent_id,
                "process_id": agent_process.process_id,
                "pid": agent_process.pid,
                "status": agent_process.status.value,
                "process_state": agent_process.process_state.value,
                "uptime_seconds": agent_process.get_uptime(),
                "spawn_time": agent_process.spawn_time.isoformat() if agent_process.spawn_time else None,
                "last_health_check": agent_process.last_health_check.isoformat() if agent_process.last_health_check else None,
                "last_activity": agent_process.last_activity.isoformat() if agent_process.last_activity else None,
                "restart_count": agent_process.restart_count,
                "health_check_failures": agent_process.health_check_failures,
                "cpu_usage": agent_process.cpu_usage,
                "memory_usage_mb": agent_process.memory_usage_mb,
                "is_alive": agent_process.is_alive(),
                "modification_in_progress": agent_process.modification_in_progress,
                "sleep_schedule": agent_process.sleep_schedule,
                "sleep_start_time": agent_process.sleep_start_time.isoformat() if agent_process.sleep_start_time else None,
                "wake_time": agent_process.wake_time.isoformat() if agent_process.wake_time else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get agent status for {agent_id}: {e}")
            return None
    
    async def get_all_agents_status(self) -> List[Dict[str, Any]]:
        """Get status of all managed agents."""
        try:
            statuses = []
            
            for agent_id in self.agents:
                status = await self.get_agent_status(agent_id)
                if status:
                    statuses.append(status)
            
            return statuses
            
        except Exception as e:
            self.logger.error(f"Failed to get all agents status: {e}")
            return []
    
    async def stop_all_agents(self) -> None:
        """Stop all managed agents."""
        try:
            stop_tasks = []
            
            for agent_id in list(self.agents.keys()):
                task = asyncio.create_task(self.stop_agent(agent_id, graceful=True))
                stop_tasks.append(task)
            
            if stop_tasks:
                await asyncio.gather(*stop_tasks, return_exceptions=True)
            
            self.logger.info("All agents stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop all agents: {e}")
    
    def register_shutdown_handler(self, handler: Callable) -> None:
        """Register a shutdown handler."""
        self.shutdown_handlers.append(handler)
    
    async def _start_agent_process(self, agent_process: AgentProcess) -> bool:
        """Start the actual agent process."""
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(agent_process.environment_vars)
            
            # Prepare command
            cmd = [agent_process.executable_path] + agent_process.command_args
            
            # Start process
            process = subprocess.Popen(
                cmd,
                cwd=agent_process.working_directory,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            
            agent_process.process = process
            agent_process.pid = process.pid
            
            # Create psutil process for monitoring
            try:
                agent_process.psutil_process = psutil.Process(process.pid)
                agent_process.process_state = ProcessState.ACTIVE
            except psutil.NoSuchProcess:
                self.logger.warning(f"Could not create psutil process for {agent_process.agent_id}")
            
            agent_process.status = AgentStatus.RUNNING
            agent_process.spawn_time = datetime.now()
            agent_process.last_activity = datetime.now()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start agent process: {e}")
            agent_process.status = AgentStatus.FAILED
            return False
    
    async def _graceful_shutdown(self, agent_process: AgentProcess) -> bool:
        """Attempt graceful shutdown of agent process."""
        try:
            if not agent_process.process:
                return True
            
            # Send SIGTERM (or equivalent on Windows)
            if sys.platform == "win32":
                agent_process.process.terminate()
            else:
                agent_process.process.send_signal(signal.SIGTERM)
            
            # Wait for graceful shutdown
            try:
                agent_process.process.wait(timeout=self.config["shutdown_timeout"])
                return True
            except subprocess.TimeoutExpired:
                return False
            
        except Exception as e:
            self.logger.error(f"Graceful shutdown failed: {e}")
            return False
    
    async def _force_terminate(self, agent_process: AgentProcess) -> bool:
        """Force terminate agent process."""
        try:
            if agent_process.psutil_process:
                try:
                    agent_process.psutil_process.terminate()
                    agent_process.psutil_process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    agent_process.psutil_process.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if agent_process.process:
                try:
                    agent_process.process.kill()
                    agent_process.process.wait()
                except (subprocess.TimeoutExpired, ProcessLookupError):
                    pass
            
            agent_process.process_state = ProcessState.TERMINATED
            
            return True
            
        except Exception as e:
            self.logger.error(f"Force terminate failed: {e}")
            return False
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for agent health checks."""
        while True:
            try:
                await asyncio.sleep(self.config["health_check_interval"])
                
                for agent_id, agent_process in list(self.agents.items()):
                    await self._perform_health_check(agent_process)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
    
    async def _lifecycle_loop(self) -> None:
        """Main lifecycle management loop."""
        while True:
            try:
                await asyncio.sleep(self.config["lifecycle_check_interval"])
                
                for agent_id, agent_process in list(self.agents.items()):
                    await self._check_lifecycle_events(agent_process)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in lifecycle loop: {e}")
    
    async def _perform_health_check(self, agent_process: AgentProcess) -> None:
        """Perform health check on an agent."""
        try:
            agent_process.last_health_check = datetime.now()
            
            # Check if process is alive
            if not agent_process.is_alive():
                agent_process.health_check_failures += 1
                
                if agent_process.health_check_failures >= agent_process.max_health_failures:
                    # Process is dead, handle accordingly
                    await self._handle_dead_process(agent_process)
                return
            
            # Update resource usage
            await self._update_resource_usage(agent_process)
            
            # Check resource limits
            if agent_process.memory_usage_mb > agent_process.max_memory_mb:
                self.logger.warning(f"Agent {agent_process.agent_id} exceeding memory limit")
                
                await self._record_lifecycle_event(
                    agent_id=agent_process.agent_id,
                    event_type=LifecycleEvent.HEALTH_CHECK,
                    description=f"Memory usage exceeded limit: {agent_process.memory_usage_mb}MB",
                    success=False
                )
            
            if agent_process.cpu_usage > agent_process.max_cpu_percent:
                self.logger.warning(f"Agent {agent_process.agent_id} exceeding CPU limit")
            
            # Reset failure count on successful check
            agent_process.health_check_failures = 0
            
        except Exception as e:
            self.logger.error(f"Health check failed for {agent_process.agent_id}: {e}")
            agent_process.health_check_failures += 1
    
    async def _check_lifecycle_events(self, agent_process: AgentProcess) -> None:
        """Check for lifecycle events (sleep/wake, etc.)."""
        try:
            if self.config["enable_sleep_wake"]:
                # Check if agent should sleep
                if agent_process.should_sleep():
                    await self.sleep_agent(agent_process.agent_id)
                
                # Check if agent should wake
                elif agent_process.should_wake():
                    await self.wake_agent(agent_process.agent_id)
            
        except Exception as e:
            self.logger.error(f"Lifecycle check failed for {agent_process.agent_id}: {e}")
    
    async def _handle_dead_process(self, agent_process: AgentProcess) -> None:
        """Handle a dead agent process."""
        try:
            previous_status = agent_process.status
            agent_process.status = AgentStatus.FAILED
            
            await self._record_lifecycle_event(
                agent_id=agent_process.agent_id,
                event_type=LifecycleEvent.CRASH,
                description="Agent process died unexpectedly",
                previous_status=previous_status,
                new_status=agent_process.status,
                success=False
            )
            
            # Update statistics
            if previous_status == AgentStatus.RUNNING:
                self.stats["active_agents"] -= 1
            elif previous_status == AgentStatus.SLEEPING:
                self.stats["sleeping_agents"] -= 1
            
            self.stats["failed_agents"] += 1
            
            # Auto-restart if configured
            if self.config["auto_restart_failed"]:
                self.logger.info(f"Auto-restarting failed agent: {agent_process.agent_id}")
                await self.restart_agent(agent_process.agent_id)
            
        except Exception as e:
            self.logger.error(f"Failed to handle dead process for {agent_process.agent_id}: {e}")
    
    async def _update_resource_usage(self, agent_process: AgentProcess) -> None:
        """Update resource usage metrics for an agent."""
        try:
            if agent_process.psutil_process and agent_process.psutil_process.is_running():
                agent_process.cpu_usage = agent_process.psutil_process.cpu_percent()
                memory_info = agent_process.psutil_process.memory_info()
                agent_process.memory_usage_mb = memory_info.rss / 1024 / 1024
                agent_process.uptime_seconds = agent_process.get_uptime()
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        except Exception as e:
            self.logger.error(f"Failed to update resource usage for {agent_process.agent_id}: {e}")
    
    async def _create_agent_backup(self, agent_process: AgentProcess) -> str:
        """Create backup of agent state before modification."""
        try:
            import shutil
            
            backup_dir = os.path.join(
                agent_process.working_directory,
                "backups",
                f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            os.makedirs(backup_dir, exist_ok=True)
            
            # Copy agent files
            source_dir = agent_process.working_directory
            for item in os.listdir(source_dir):
                if item != "backups":  # Don't backup the backup directory
                    source_path = os.path.join(source_dir, item)
                    dest_path = os.path.join(backup_dir, item)
                    
                    if os.path.isdir(source_path):
                        shutil.copytree(source_path, dest_path)
                    else:
                        shutil.copy2(source_path, dest_path)
            
            return backup_dir
            
        except Exception as e:
            self.logger.error(f"Failed to create agent backup: {e}")
            return ""
    
    async def _rollback_modification(self, agent_process: AgentProcess) -> None:
        """Rollback agent modification using backup."""
        try:
            if not agent_process.modification_backup_path:
                return
            
            # Stop current process
            await self._force_terminate(agent_process)
            
            # Restore from backup
            import shutil
            
            backup_dir = agent_process.modification_backup_path
            target_dir = agent_process.working_directory
            
            # Remove current files (except backups)
            for item in os.listdir(target_dir):
                if item != "backups":
                    item_path = os.path.join(target_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
            
            # Restore from backup
            for item in os.listdir(backup_dir):
                source_path = os.path.join(backup_dir, item)
                dest_path = os.path.join(target_dir, item)
                
                if os.path.isdir(source_path):
                    shutil.copytree(source_path, dest_path)
                else:
                    shutil.copy2(source_path, dest_path)
            
            # Restart agent
            await self._start_agent_process(agent_process)
            
            agent_process.status = AgentStatus.RUNNING
            agent_process.modification_in_progress = False
            agent_process.modification_backup_path = None
            
            self.logger.info(f"Agent modification rolled back: {agent_process.agent_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to rollback modification for {agent_process.agent_id}: {e}")
    
    async def _record_lifecycle_event(
        self,
        agent_id: str,
        event_type: LifecycleEvent,
        description: str,
        previous_status: Optional[AgentStatus] = None,
        new_status: Optional[AgentStatus] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """Record a lifecycle event."""
        try:
            self.event_counter += 1
            event_id = f"event_{self.event_counter}_{datetime.now().timestamp()}"
            
            # Get current resource usage if agent exists
            cpu_usage = None
            memory_usage = None
            
            if agent_id in self.agents:
                agent_process = self.agents[agent_id]
                cpu_usage = agent_process.cpu_usage
                memory_usage = agent_process.memory_usage_mb
            
            event = LifecycleEventRecord(
                event_id=event_id,
                agent_id=agent_id,
                event_type=event_type,
                timestamp=datetime.now(),
                description=description,
                metadata=metadata or {},
                previous_status=previous_status,
                new_status=new_status,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                success=success,
                error_message=error_message
            )
            
            self.lifecycle_events[event_id] = event
            
            # Update statistics
            self.stats["lifecycle_events"][event_type.value] += 1
            
            # Log event
            log_agent_event(
                agent_id,
                f"lifecycle_{event_type.value}",
                {
                    "event_id": event_id,
                    "description": description,
                    "success": success,
                    "metadata": metadata or {}
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to record lifecycle event: {e}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        try:
            def signal_handler(signum, frame):
                self.logger.info(f"Received signal {signum}, shutting down agents")
                
                # Call shutdown handlers
                for handler in self.shutdown_handlers:
                    try:
                        handler()
                    except Exception as e:
                        self.logger.error(f"Shutdown handler failed: {e}")
                
                # Create task to stop all agents
                asyncio.create_task(self.stop_all_agents())
            
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            
        except Exception as e:
            self.logger.warning(f"Failed to setup signal handlers: {e}")