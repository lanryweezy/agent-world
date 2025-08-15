"""
Automation service for workflow creation and execution.

This module implements workflow automation capabilities including
task scheduling, workflow orchestration, and automated process execution.
"""

import asyncio
import json
import subprocess
import shlex
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import cron_descriptor

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class WorkflowStatus(Enum):
    """Status of workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskType(Enum):
    """Types of automation tasks."""
    COMMAND = "command"
    HTTP_REQUEST = "http_request"
    FILE_OPERATION = "file_operation"
    DATA_PROCESSING = "data_processing"
    NOTIFICATION = "notification"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    DELAY = "delay"
    CUSTOM_FUNCTION = "custom_function"


class TriggerType(Enum):
    """Types of workflow triggers."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"
    FILE_WATCH = "file_watch"
    API_WEBHOOK = "api_webhook"
    CONDITION_MET = "condition_met"


@dataclass
class AutomationTask:
    """Individual task within a workflow."""
    task_id: str
    name: str
    task_type: TaskType
    
    # Task configuration
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    retry_count: int = 0
    retry_delay_seconds: int = 5
    
    # Dependencies and flow control
    depends_on: List[str] = field(default_factory=list)  # task_ids
    run_on_failure: bool = False
    continue_on_error: bool = False
    
    # Conditions
    condition: Optional[str] = None  # Python expression
    
    # Output handling
    capture_output: bool = True
    output_variable: Optional[str] = None
    
    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class WorkflowTrigger:
    """Trigger configuration for workflows."""
    trigger_id: str
    trigger_type: TriggerType
    
    # Trigger configuration
    schedule: Optional[str] = None  # Cron expression
    event_pattern: Optional[str] = None
    file_path: Optional[str] = None
    webhook_endpoint: Optional[str] = None
    condition: Optional[str] = None
    
    # Trigger state
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    # Metadata
    description: str = ""


@dataclass
class AutomationWorkflow:
    """Complete automation workflow definition."""
    workflow_id: str
    name: str
    description: str
    
    # Workflow structure
    tasks: List[AutomationTask] = field(default_factory=list)
    triggers: List[WorkflowTrigger] = field(default_factory=list)
    
    # Configuration
    max_concurrent_executions: int = 1
    timeout_minutes: int = 60
    retry_failed_tasks: bool = True
    
    # Variables and context
    variables: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    
    # State
    enabled: bool = True
    execution_count: int = 0
    last_execution: Optional[datetime] = None
    last_status: Optional[WorkflowStatus] = None


@dataclass
class WorkflowExecution:
    """Runtime execution instance of a workflow."""
    execution_id: str
    workflow_id: str
    
    # Execution state
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Task execution tracking
    task_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # task_id -> result
    current_task: Optional[str] = None
    completed_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    
    # Runtime context
    variables: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    
    # Trigger information
    triggered_by: Optional[str] = None
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def add_log(self, message: str) -> None:
        """Add log entry to execution."""
        timestamp = datetime.now().isoformat()
        self.logs.append(f"[{timestamp}] {message}")
    
    def get_duration_seconds(self) -> Optional[float]:
        """Get execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None


class WorkflowAutomationService(AgentModule):
    """
    Workflow automation service for creating and executing automated processes.
    
    Provides workflow definition, scheduling, execution, and monitoring
    capabilities for complex automation scenarios.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "automation_service")
        
        # Core data structures
        self.workflows: Dict[str, AutomationWorkflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.active_executions: Dict[str, asyncio.Task] = {}  # execution_id -> task
        
        # Scheduling and triggers
        self.scheduled_workflows: Dict[str, asyncio.Task] = {}  # workflow_id -> scheduler task
        self.trigger_handlers: Dict[TriggerType, Callable] = {}
        
        # Configuration
        self.config = {
            "max_concurrent_workflows": 10,
            "max_execution_history": 1000,
            "execution_retention_days": 30,
            "default_task_timeout": 300,
            "max_workflow_duration_hours": 24,
            "enable_file_watching": True,
            "enable_webhooks": True,
            "webhook_port": 8080
        }
        
        # Statistics
        self.stats = {
            "total_workflows": 0,
            "active_workflows": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "executions_by_status": {status.value: 0 for status in WorkflowStatus},
            "tasks_by_type": {task_type.value: 0 for task_type in TaskType}
        }
        
        # Counters
        self.workflow_counter = 0
        self.execution_counter = 0
        
        # Built-in task handlers
        self.task_handlers = {
            TaskType.COMMAND: self._execute_command_task,
            TaskType.HTTP_REQUEST: self._execute_http_request_task,
            TaskType.FILE_OPERATION: self._execute_file_operation_task,
            TaskType.DATA_PROCESSING: self._execute_data_processing_task,
            TaskType.NOTIFICATION: self._execute_notification_task,
            TaskType.CONDITIONAL: self._execute_conditional_task,
            TaskType.LOOP: self._execute_loop_task,
            TaskType.DELAY: self._execute_delay_task,
            TaskType.CUSTOM_FUNCTION: self._execute_custom_function_task
        }
        
        self.logger.info("Workflow automation service initialized")
    
    async def initialize(self) -> None:
        """Initialize the automation service."""
        try:
            # Start background tasks
            asyncio.create_task(self._execution_monitor())
            asyncio.create_task(self._cleanup_old_executions())
            asyncio.create_task(self._update_statistics())
            
            # Initialize trigger handlers
            self._setup_trigger_handlers()
            
            # Start webhook server if enabled
            if self.config["enable_webhooks"]:
                asyncio.create_task(self._start_webhook_server())
            
            self.logger.info("Automation service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize automation service: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the automation service."""
        try:
            # Cancel all active executions
            for execution_task in self.active_executions.values():
                execution_task.cancel()
            
            # Wait for executions to complete
            if self.active_executions:
                await asyncio.gather(*self.active_executions.values(), return_exceptions=True)
            
            # Stop scheduled workflows
            for scheduler_task in self.scheduled_workflows.values():
                scheduler_task.cancel()
            
            self.logger.info("Automation service shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during automation service shutdown: {e}")
    
    async def create_workflow(
        self,
        name: str,
        description: str,
        tasks: List[Dict[str, Any]],
        triggers: Optional[List[Dict[str, Any]]] = None,
        variables: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new automation workflow."""
        try:
            self.workflow_counter += 1
            workflow_id = f"workflow_{self.workflow_counter}_{datetime.now().timestamp()}"
            
            # Parse tasks
            workflow_tasks = []
            for task_data in tasks:
                task = AutomationTask(
                    task_id=task_data.get("task_id", f"task_{len(workflow_tasks) + 1}"),
                    name=task_data["name"],
                    task_type=TaskType(task_data["task_type"]),
                    parameters=task_data.get("parameters", {}),
                    timeout_seconds=task_data.get("timeout_seconds", self.config["default_task_timeout"]),
                    retry_count=task_data.get("retry_count", 0),
                    depends_on=task_data.get("depends_on", []),
                    condition=task_data.get("condition"),
                    description=task_data.get("description", "")
                )
                workflow_tasks.append(task)
            
            # Parse triggers
            workflow_triggers = []
            if triggers:
                for trigger_data in triggers:
                    trigger = WorkflowTrigger(
                        trigger_id=trigger_data.get("trigger_id", f"trigger_{len(workflow_triggers) + 1}"),
                        trigger_type=TriggerType(trigger_data["trigger_type"]),
                        schedule=trigger_data.get("schedule"),
                        event_pattern=trigger_data.get("event_pattern"),
                        condition=trigger_data.get("condition"),
                        description=trigger_data.get("description", "")
                    )
                    workflow_triggers.append(trigger)
            
            # Create workflow
            workflow = AutomationWorkflow(
                workflow_id=workflow_id,
                name=name,
                description=description,
                tasks=workflow_tasks,
                triggers=workflow_triggers,
                variables=variables or {},
                tags=tags or [],
                created_by=self.agent_id
            )
            
            self.workflows[workflow_id] = workflow
            
            # Set up triggers
            if workflow_triggers:
                await self._setup_workflow_triggers(workflow_id)
            
            # Update statistics
            self.stats["total_workflows"] += 1
            for task in workflow_tasks:
                self.stats["tasks_by_type"][task.task_type.value] += 1
            
            log_agent_event(
                self.agent_id,
                "workflow_created",
                {
                    "workflow_id": workflow_id,
                    "name": name,
                    "task_count": len(workflow_tasks),
                    "trigger_count": len(workflow_triggers)
                }
            )
            
            result = {
                "success": True,
                "workflow_id": workflow_id,
                "name": name,
                "task_count": len(workflow_tasks),
                "trigger_count": len(workflow_triggers),
                "status": "active" if workflow.enabled else "disabled"
            }
            
            self.logger.info(f"Workflow created: {name} ({workflow_id})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create workflow: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_data: Optional[Dict[str, Any]] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a workflow manually or via trigger."""
        try:
            if workflow_id not in self.workflows:
                return {"success": False, "error": "Workflow not found"}
            
            workflow = self.workflows[workflow_id]
            
            if not workflow.enabled:
                return {"success": False, "error": "Workflow is disabled"}
            
            # Check concurrent execution limit
            active_count = sum(1 for exec_id, execution in self.executions.items() 
                             if execution.workflow_id == workflow_id and 
                             execution.status == WorkflowStatus.RUNNING)
            
            if active_count >= workflow.max_concurrent_executions:
                return {"success": False, "error": "Maximum concurrent executions reached"}
            
            # Create execution instance
            self.execution_counter += 1
            execution_id = f"exec_{self.execution_counter}_{datetime.now().timestamp()}"
            
            execution = WorkflowExecution(
                execution_id=execution_id,
                workflow_id=workflow_id,
                variables={**workflow.variables, **(variables or {})},
                trigger_data=trigger_data or {}
            )
            
            self.executions[execution_id] = execution
            
            # Start execution task
            execution_task = asyncio.create_task(self._run_workflow_execution(execution_id))
            self.active_executions[execution_id] = execution_task
            
            # Update statistics
            self.stats["total_executions"] += 1
            self.stats["executions_by_status"][WorkflowStatus.PENDING.value] += 1
            
            log_agent_event(
                self.agent_id,
                "workflow_execution_started",
                {
                    "execution_id": execution_id,
                    "workflow_id": workflow_id,
                    "workflow_name": workflow.name
                }
            )
            
            result = {
                "success": True,
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "workflow_name": workflow.name,
                "status": execution.status.value,
                "estimated_duration": self._estimate_workflow_duration(workflow)
            }
            
            self.logger.info(f"Workflow execution started: {workflow.name} ({execution_id})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute workflow: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get status of a specific workflow."""
        try:
            if workflow_id not in self.workflows:
                return {"success": False, "error": "Workflow not found"}
            
            workflow = self.workflows[workflow_id]
            
            # Get recent executions
            recent_executions = [
                execution for execution in self.executions.values()
                if execution.workflow_id == workflow_id
            ]
            recent_executions.sort(key=lambda e: e.started_at or datetime.min, reverse=True)
            recent_executions = recent_executions[:10]  # Last 10 executions
            
            # Count active executions
            active_executions = sum(1 for execution in recent_executions 
                                  if execution.status == WorkflowStatus.RUNNING)
            
            # Calculate success rate
            completed_executions = [e for e in recent_executions 
                                  if e.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]]
            success_rate = 0.0
            if completed_executions:
                successful = sum(1 for e in completed_executions if e.status == WorkflowStatus.COMPLETED)
                success_rate = successful / len(completed_executions)
            
            status_info = {
                "workflow_id": workflow_id,
                "name": workflow.name,
                "description": workflow.description,
                "enabled": workflow.enabled,
                "task_count": len(workflow.tasks),
                "trigger_count": len(workflow.triggers),
                "execution_count": workflow.execution_count,
                "active_executions": active_executions,
                "last_execution": workflow.last_execution.isoformat() if workflow.last_execution else None,
                "last_status": workflow.last_status.value if workflow.last_status else None,
                "success_rate": success_rate,
                "recent_executions": [
                    {
                        "execution_id": execution.execution_id,
                        "status": execution.status.value,
                        "started_at": execution.started_at.isoformat() if execution.started_at else None,
                        "duration_seconds": execution.get_duration_seconds(),
                        "completed_tasks": len(execution.completed_tasks),
                        "failed_tasks": len(execution.failed_tasks)
                    }
                    for execution in recent_executions
                ]
            }
            
            return {"success": True, "status": status_info}
            
        except Exception as e:
            self.logger.error(f"Failed to get workflow status: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_execution_details(self, execution_id: str) -> Dict[str, Any]:
        """Get detailed information about a workflow execution."""
        try:
            if execution_id not in self.executions:
                return {"success": False, "error": "Execution not found"}
            
            execution = self.executions[execution_id]
            workflow = self.workflows[execution.workflow_id]
            
            execution_details = {
                "execution_id": execution_id,
                "workflow_id": execution.workflow_id,
                "workflow_name": workflow.name,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "duration_seconds": execution.get_duration_seconds(),
                "current_task": execution.current_task,
                "completed_tasks": execution.completed_tasks,
                "failed_tasks": execution.failed_tasks,
                "variables": execution.variables,
                "logs": execution.logs[-50:],  # Last 50 log entries
                "task_results": execution.task_results,
                "error_message": execution.error_message,
                "retry_count": execution.retry_count,
                "triggered_by": execution.triggered_by,
                "trigger_data": execution.trigger_data
            }
            
            return {"success": True, "execution": execution_details}
            
        except Exception as e:
            self.logger.error(f"Failed to get execution details: {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """Cancel a running workflow execution."""
        try:
            if execution_id not in self.executions:
                return {"success": False, "error": "Execution not found"}
            
            execution = self.executions[execution_id]
            
            if execution.status != WorkflowStatus.RUNNING:
                return {"success": False, "error": "Execution is not running"}
            
            # Cancel the execution task
            if execution_id in self.active_executions:
                self.active_executions[execution_id].cancel()
                del self.active_executions[execution_id]
            
            # Update execution status
            execution.status = WorkflowStatus.CANCELLED
            execution.completed_at = datetime.now()
            execution.add_log("Execution cancelled by user request")
            
            log_agent_event(
                self.agent_id,
                "workflow_execution_cancelled",
                {
                    "execution_id": execution_id,
                    "workflow_id": execution.workflow_id
                }
            )
            
            result = {
                "success": True,
                "execution_id": execution_id,
                "status": execution.status.value,
                "cancelled_at": execution.completed_at.isoformat()
            }
            
            self.logger.info(f"Workflow execution cancelled: {execution_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to cancel execution: {e}")
            return {"success": False, "error": str(e)}
    
    async def _run_workflow_execution(self, execution_id: str) -> None:
        """Run a complete workflow execution."""
        execution = self.executions[execution_id]
        workflow = self.workflows[execution.workflow_id]
        
        try:
            execution.status = WorkflowStatus.RUNNING
            execution.started_at = datetime.now()
            execution.add_log(f"Starting workflow execution: {workflow.name}")
            
            # Build task dependency graph
            task_graph = self._build_task_dependency_graph(workflow.tasks)
            
            # Execute tasks in dependency order
            completed_tasks = set()
            
            while len(completed_tasks) < len(workflow.tasks):
                # Find tasks that can be executed (dependencies satisfied)
                ready_tasks = []
                for task in workflow.tasks:
                    if (task.task_id not in completed_tasks and 
                        all(dep in completed_tasks for dep in task.depends_on)):
                        ready_tasks.append(task)
                
                if not ready_tasks:
                    # Check for circular dependencies or other issues
                    remaining_tasks = [t for t in workflow.tasks if t.task_id not in completed_tasks]
                    execution.add_log(f"No ready tasks found. Remaining: {[t.name for t in remaining_tasks]}")
                    break
                
                # Execute ready tasks (could be parallelized in the future)
                for task in ready_tasks:
                    execution.current_task = task.task_id
                    execution.add_log(f"Executing task: {task.name}")
                    
                    # Check task condition
                    if task.condition and not self._evaluate_condition(task.condition, execution.variables):
                        execution.add_log(f"Task condition not met, skipping: {task.name}")
                        completed_tasks.add(task.task_id)
                        continue
                    
                    # Execute the task
                    task_result = await self._execute_task(task, execution)
                    execution.task_results[task.task_id] = task_result
                    
                    if task_result["success"]:
                        execution.add_log(f"Task completed successfully: {task.name}")
                        execution.completed_tasks.append(task.task_id)
                        completed_tasks.add(task.task_id)
                        
                        # Store output variable if specified
                        if task.output_variable and "output" in task_result:
                            execution.variables[task.output_variable] = task_result["output"]
                    
                    else:
                        execution.add_log(f"Task failed: {task.name} - {task_result.get('error', 'Unknown error')}")
                        execution.failed_tasks.append(task.task_id)
                        
                        if not task.continue_on_error:
                            execution.add_log("Stopping workflow due to task failure")
                            raise Exception(f"Task failed: {task.name}")
                        
                        completed_tasks.add(task.task_id)  # Mark as completed even if failed
            
            # Workflow completed successfully
            execution.status = WorkflowStatus.COMPLETED
            execution.add_log("Workflow execution completed successfully")
            self.stats["successful_executions"] += 1
            
        except asyncio.CancelledError:
            execution.status = WorkflowStatus.CANCELLED
            execution.add_log("Workflow execution was cancelled")
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.add_log(f"Workflow execution failed: {str(e)}")
            self.stats["failed_executions"] += 1
        
        finally:
            execution.completed_at = datetime.now()
            execution.current_task = None
            
            # Update workflow statistics
            workflow.execution_count += 1
            workflow.last_execution = execution.completed_at
            workflow.last_status = execution.status
            
            # Clean up active execution
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
            
            # Update statistics
            self.stats["executions_by_status"][execution.status.value] += 1
            
            log_agent_event(
                self.agent_id,
                "workflow_execution_completed",
                {
                    "execution_id": execution_id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status.value,
                    "duration_seconds": execution.get_duration_seconds(),
                    "completed_tasks": len(execution.completed_tasks),
                    "failed_tasks": len(execution.failed_tasks)
                }
            )
            
            self.logger.info(f"Workflow execution {execution.status.value}: {execution_id}")
    
    async def _execute_task(self, task: AutomationTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a single automation task."""
        try:
            # Get task handler
            if task.task_type not in self.task_handlers:
                return {"success": False, "error": f"Unsupported task type: {task.task_type.value}"}
            
            handler = self.task_handlers[task.task_type]
            
            # Execute with timeout and retry logic
            for attempt in range(task.retry_count + 1):
                try:
                    result = await asyncio.wait_for(
                        handler(task, execution),
                        timeout=task.timeout_seconds
                    )
                    
                    if result["success"] or attempt == task.retry_count:
                        return result
                    
                    # Wait before retry
                    if attempt < task.retry_count:
                        execution.add_log(f"Task attempt {attempt + 1} failed, retrying in {task.retry_delay_seconds}s")
                        await asyncio.sleep(task.retry_delay_seconds)
                
                except asyncio.TimeoutError:
                    if attempt == task.retry_count:
                        return {"success": False, "error": f"Task timeout after {task.timeout_seconds}s"}
                    
                    execution.add_log(f"Task attempt {attempt + 1} timed out, retrying")
                    await asyncio.sleep(task.retry_delay_seconds)
            
            return {"success": False, "error": "All retry attempts failed"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_command_task(self, task: AutomationTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a command line task."""
        try:
            command = task.parameters.get("command", "")
            if not command:
                return {"success": False, "error": "No command specified"}
            
            # Substitute variables in command
            command = self._substitute_variables(command, execution.variables)
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=task.parameters.get("working_directory")
            )
            
            stdout, stderr = await process.communicate()
            
            result = {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "command": command
            }
            
            if task.capture_output:
                result["output"] = result["stdout"]
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_http_request_task(self, task: AutomationTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute an HTTP request task."""
        try:
            import aiohttp
            
            url = task.parameters.get("url", "")
            method = task.parameters.get("method", "GET").upper()
            headers = task.parameters.get("headers", {})
            data = task.parameters.get("data")
            
            if not url:
                return {"success": False, "error": "No URL specified"}
            
            # Substitute variables
            url = self._substitute_variables(url, execution.variables)
            
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, json=data) as response:
                    response_text = await response.text()
                    
                    result = {
                        "success": 200 <= response.status < 400,
                        "status_code": response.status,
                        "response_text": response_text,
                        "headers": dict(response.headers)
                    }
                    
                    if task.capture_output:
                        result["output"] = response_text
                    
                    return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_file_operation_task(self, task: AutomationTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a file operation task."""
        try:
            operation = task.parameters.get("operation", "")
            file_path = task.parameters.get("file_path", "")
            
            if not operation or not file_path:
                return {"success": False, "error": "Missing operation or file_path"}
            
            # Substitute variables
            file_path = self._substitute_variables(file_path, execution.variables)
            
            if operation == "read":
                with open(file_path, 'r') as f:
                    content = f.read()
                return {"success": True, "output": content}
            
            elif operation == "write":
                content = task.parameters.get("content", "")
                content = self._substitute_variables(content, execution.variables)
                with open(file_path, 'w') as f:
                    f.write(content)
                return {"success": True, "message": f"File written: {file_path}"}
            
            elif operation == "delete":
                import os
                os.remove(file_path)
                return {"success": True, "message": f"File deleted: {file_path}"}
            
            else:
                return {"success": False, "error": f"Unsupported file operation: {operation}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_data_processing_task(self, task: AutomationTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a data processing task."""
        try:
            operation = task.parameters.get("operation", "")
            data_source = task.parameters.get("data_source", "")
            
            # This is a simplified implementation
            # In a real system, you'd have more sophisticated data processing
            
            if operation == "transform":
                # Simple data transformation example
                input_data = execution.variables.get(data_source, {})
                # Apply transformation logic here
                output_data = input_data  # Placeholder
                
                return {"success": True, "output": output_data}
            
            else:
                return {"success": False, "error": f"Unsupported data operation: {operation}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_notification_task(self, task: AutomationTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a notification task."""
        try:
            message = task.parameters.get("message", "")
            recipient = task.parameters.get("recipient", "")
            
            # Substitute variables
            message = self._substitute_variables(message, execution.variables)
            
            # Log the notification (in a real system, you'd send actual notifications)
            execution.add_log(f"NOTIFICATION to {recipient}: {message}")
            
            return {"success": True, "message": "Notification sent"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_conditional_task(self, task: AutomationTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a conditional task."""
        try:
            condition = task.parameters.get("condition", "")
            
            if not condition:
                return {"success": False, "error": "No condition specified"}
            
            # Evaluate condition
            result = self._evaluate_condition(condition, execution.variables)
            
            return {"success": True, "output": result, "condition_result": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_loop_task(self, task: AutomationTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a loop task."""
        try:
            # This is a simplified implementation
            # In a real system, you'd have more sophisticated loop handling
            
            iterations = task.parameters.get("iterations", 1)
            loop_variable = task.parameters.get("loop_variable", "i")
            
            results = []
            for i in range(iterations):
                execution.variables[loop_variable] = i
                # Execute loop body (would need to be defined)
                results.append(f"Loop iteration {i}")
            
            return {"success": True, "output": results}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_delay_task(self, task: AutomationTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a delay task."""
        try:
            delay_seconds = task.parameters.get("delay_seconds", 1)
            
            execution.add_log(f"Delaying for {delay_seconds} seconds")
            await asyncio.sleep(delay_seconds)
            
            return {"success": True, "message": f"Delayed for {delay_seconds} seconds"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_custom_function_task(self, task: AutomationTask, execution: WorkflowExecution) -> Dict[str, Any]:
        """Execute a custom function task."""
        try:
            # This would execute custom Python code
            # For security reasons, this is a placeholder implementation
            
            function_name = task.parameters.get("function_name", "")
            
            return {"success": True, "message": f"Custom function executed: {function_name}"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _build_task_dependency_graph(self, tasks: List[AutomationTask]) -> Dict[str, List[str]]:
        """Build task dependency graph."""
        graph = {}
        for task in tasks:
            graph[task.task_id] = task.depends_on
        return graph
    
    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Evaluate a condition expression safely."""
        try:
            # This is a simplified implementation
            # In a real system, you'd want more sophisticated and secure expression evaluation
            
            # Replace variable references
            for var_name, var_value in variables.items():
                condition = condition.replace(f"${var_name}", str(var_value))
            
            # Simple condition evaluation (very basic)
            if "==" in condition:
                left, right = condition.split("==", 1)
                return left.strip() == right.strip()
            elif "!=" in condition:
                left, right = condition.split("!=", 1)
                return left.strip() != right.strip()
            elif condition.lower() in ["true", "1", "yes"]:
                return True
            elif condition.lower() in ["false", "0", "no"]:
                return False
            
            return bool(condition)
            
        except Exception:
            return False
    
    def _substitute_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """Substitute variables in text."""
        for var_name, var_value in variables.items():
            text = text.replace(f"${var_name}", str(var_value))
        return text
    
    def _estimate_workflow_duration(self, workflow: AutomationWorkflow) -> float:
        """Estimate workflow duration in seconds."""
        # Simple estimation based on task timeouts
        total_timeout = sum(task.timeout_seconds for task in workflow.tasks)
        return total_timeout * 0.5  # Assume 50% of timeout on average
    
    def _setup_trigger_handlers(self) -> None:
        """Set up trigger handlers for different trigger types."""
        # This would set up handlers for different trigger types
        # For now, just a placeholder
        pass
    
    async def _setup_workflow_triggers(self, workflow_id: str) -> None:
        """Set up triggers for a workflow."""
        workflow = self.workflows[workflow_id]
        
        for trigger in workflow.triggers:
            if trigger.trigger_type == TriggerType.SCHEDULED and trigger.schedule:
                # Set up scheduled trigger
                scheduler_task = asyncio.create_task(
                    self._schedule_workflow(workflow_id, trigger.schedule)
                )
                self.scheduled_workflows[workflow_id] = scheduler_task
    
    async def _schedule_workflow(self, workflow_id: str, schedule: str) -> None:
        """Schedule workflow execution based on cron expression."""
        # This is a simplified implementation
        # In a real system, you'd use a proper cron scheduler
        
        while workflow_id in self.workflows:
            try:
                # For now, just execute every hour (placeholder)
                await asyncio.sleep(3600)
                
                if workflow_id in self.workflows and self.workflows[workflow_id].enabled:
                    await self.execute_workflow(workflow_id, {"triggered_by": "schedule"})
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in scheduled workflow {workflow_id}: {e}")
    
    async def _start_webhook_server(self) -> None:
        """Start webhook server for API triggers."""
        # This would start a web server for webhook endpoints
        # Placeholder implementation
        pass
    
    async def _execution_monitor(self) -> None:
        """Monitor running executions for timeouts and issues."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.now()
                max_duration = timedelta(hours=self.config["max_workflow_duration_hours"])
                
                # Check for timed out executions
                for execution_id, execution in list(self.executions.items()):
                    if (execution.status == WorkflowStatus.RUNNING and 
                        execution.started_at and 
                        current_time - execution.started_at > max_duration):
                        
                        # Cancel timed out execution
                        if execution_id in self.active_executions:
                            self.active_executions[execution_id].cancel()
                        
                        execution.status = WorkflowStatus.FAILED
                        execution.error_message = "Execution timed out"
                        execution.completed_at = current_time
                        execution.add_log("Execution cancelled due to timeout")
                        
                        self.logger.warning(f"Execution timed out: {execution_id}")
                
            except Exception as e:
                self.logger.error(f"Error in execution monitor: {e}")
    
    async def _cleanup_old_executions(self) -> None:
        """Clean up old execution data periodically."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                cutoff_time = datetime.now() - timedelta(days=self.config["execution_retention_days"])
                
                # Remove old executions
                old_executions = [
                    exec_id for exec_id, execution in self.executions.items()
                    if (execution.completed_at and execution.completed_at < cutoff_time)
                ]
                
                for exec_id in old_executions:
                    del self.executions[exec_id]
                
                if old_executions:
                    self.logger.debug(f"Cleaned up {len(old_executions)} old executions")
                
                # Limit total executions
                if len(self.executions) > self.config["max_execution_history"]:
                    # Keep most recent executions
                    sorted_executions = sorted(
                        self.executions.items(),
                        key=lambda x: x[1].started_at or datetime.min,
                        reverse=True
                    )
                    
                    keep_count = self.config["max_execution_history"]
                    for exec_id, _ in sorted_executions[keep_count:]:
                        del self.executions[exec_id]
                
            except Exception as e:
                self.logger.error(f"Error during execution cleanup: {e}")
    
    async def _update_statistics(self) -> None:
        """Update automation service statistics periodically."""
        while True:
            try:
                await asyncio.sleep(300)  # Update every 5 minutes
                
                # Update active workflow count
                self.stats["active_workflows"] = sum(1 for w in self.workflows.values() if w.enabled)
                
                # Calculate average execution time
                completed_executions = [
                    e for e in self.executions.values()
                    if e.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED] and e.get_duration_seconds()
                ]
                
                if completed_executions:
                    total_time = sum(e.get_duration_seconds() for e in completed_executions)
                    self.stats["average_execution_time"] = total_time / len(completed_executions)
                
            except Exception as e:
                self.logger.error(f"Error updating automation statistics: {e}")