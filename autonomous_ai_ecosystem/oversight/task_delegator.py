"""
Task delegation and coordination system for the autonomous AI ecosystem.

This module implements task breakdown, multi-agent collaboration coordination,
progress tracking, and status reporting for complex human tasks.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .command_router import HumanCommandRouter, HumanCommand, CommandPriority


class TaskType(Enum):
    """Types of tasks that can be delegated."""
    RESEARCH = "research"
    DEVELOPMENT = "development"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    PROBLEM_SOLVING = "problem_solving"
    COORDINATION = "coordination"
    MONITORING = "monitoring"
    COMMUNICATION = "communication"
    PLANNING = "planning"
    EXECUTION = "execution"


class TaskStatus(Enum):
    """Status of delegated tasks."""
    CREATED = "created"
    PLANNING = "planning"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Priority levels for tasks."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class TaskDependency:
    """Represents a dependency between tasks."""
    dependent_task_id: str
    prerequisite_task_id: str
    dependency_type: str = "finish_to_start"  # finish_to_start, start_to_start, etc.
    lag_hours: float = 0.0  # Delay after prerequisite completion


@dataclass
class TaskAssignment:
    """Represents assignment of a task to an agent."""
    assignment_id: str
    task_id: str
    agent_id: str
    role: str  # primary, collaborator, reviewer, observer
    
    # Assignment details
    assigned_at: datetime = field(default_factory=datetime.now)
    estimated_hours: float = 1.0
    actual_hours: float = 0.0
    
    # Progress tracking
    progress_percentage: float = 0.0
    status_updates: List[str] = field(default_factory=list)
    
    # Performance
    quality_score: float = 0.0
    efficiency_score: float = 0.0
    
    def add_status_update(self, update: str) -> None:
        """Add a status update."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_updates.append(f"[{timestamp}] {update}")
        
        if len(self.status_updates) > 20:
            self.status_updates = self.status_updates[-20:]


@dataclass
class TaskProgress:
    """Tracks progress of a task."""
    task_id: str
    overall_progress: float = 0.0
    
    # Milestone tracking
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    completed_milestones: int = 0
    
    # Time tracking
    estimated_duration: float = 0.0  # hours
    actual_duration: float = 0.0
    time_remaining: float = 0.0
    
    # Quality metrics
    quality_checks: List[Dict[str, Any]] = field(default_factory=list)
    average_quality: float = 0.0
    
    # Collaboration metrics
    agent_contributions: Dict[str, float] = field(default_factory=dict)  # agent_id -> contribution %
    communication_events: int = 0
    
    # Blockers and issues
    blockers: List[Dict[str, Any]] = field(default_factory=list)
    resolved_issues: int = 0
    
    def add_milestone(self, name: str, description: str, target_date: datetime) -> None:
        """Add a milestone to track."""
        milestone = {
            "id": f"milestone_{len(self.milestones)}",
            "name": name,
            "description": description,
            "target_date": target_date.isoformat(),
            "completed": False,
            "completed_date": None
        }
        self.milestones.append(milestone)
    
    def complete_milestone(self, milestone_id: str) -> bool:
        """Mark a milestone as completed."""
        for milestone in self.milestones:
            if milestone["id"] == milestone_id:
                milestone["completed"] = True
                milestone["completed_date"] = datetime.now().isoformat()
                self.completed_milestones += 1
                return True
        return False


@dataclass
class HumanTask:
    """Represents a complex task from a human that needs delegation."""
    task_id: str
    human_id: str
    command_id: Optional[str]  # Reference to original human command
    
    # Task definition
    title: str
    description: str
    task_type: TaskType
    priority: TaskPriority
    
    # Requirements and constraints
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    
    # Task breakdown
    subtasks: List[str] = field(default_factory=list)  # subtask_ids
    dependencies: List[TaskDependency] = field(default_factory=list)
    
    # Assignment and coordination
    status: TaskStatus = TaskStatus.CREATED
    assignments: Dict[str, TaskAssignment] = field(default_factory=dict)  # assignment_id -> assignment
    coordinator_agent_id: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    # Progress tracking
    progress: TaskProgress = field(default_factory=lambda: TaskProgress(""))
    
    # Resources and budget
    estimated_agent_hours: float = 0.0
    actual_agent_hours: float = 0.0
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    
    # Results and feedback
    deliverables: List[Dict[str, Any]] = field(default_factory=list)
    human_feedback: str = ""
    human_satisfaction: Optional[int] = None  # 1-5 rating
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize progress tracking with task ID."""
        self.progress.task_id = self.task_id
    
    def get_duration(self) -> float:
        """Get task duration in hours."""
        if not self.actual_start:
            return 0.0
        
        end_time = self.actual_end or datetime.now()
        return (end_time - self.actual_start).total_seconds() / 3600.0
    
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.deadline or self.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return False
        return datetime.now() > self.deadline
    
    def get_assigned_agents(self) -> List[str]:
        """Get list of assigned agent IDs."""
        return [assignment.agent_id for assignment in self.assignments.values()]
    
    def get_primary_agent(self) -> Optional[str]:
        """Get the primary assigned agent."""
        for assignment in self.assignments.values():
            if assignment.role == "primary":
                return assignment.agent_id
        return None


class TaskDelegator(AgentModule):
    """
    Task delegation and coordination system for autonomous AI agents.
    
    Breaks down complex human tasks into manageable subtasks, coordinates
    multi-agent collaboration, and tracks progress and status.
    """
    
    def __init__(self, agent_id: str, command_router: HumanCommandRouter):
        super().__init__(agent_id)
        self.command_router = command_router
        self.logger = get_agent_logger(agent_id, "task_delegator")
        
        # Core data structures
        self.tasks: Dict[str, HumanTask] = {}
        self.subtasks: Dict[str, HumanTask] = {}  # Subtasks are also HumanTask objects
        self.task_queue = asyncio.Queue()
        
        # Task breakdown templates
        self.task_templates = {
            TaskType.RESEARCH: {
                "typical_subtasks": ["literature_review", "data_collection", "analysis", "report_writing"],
                "estimated_hours": 8.0,
                "required_skills": ["research", "analysis", "communication"]
            },
            TaskType.DEVELOPMENT: {
                "typical_subtasks": ["requirements_analysis", "design", "implementation", "testing", "documentation"],
                "estimated_hours": 16.0,
                "required_skills": ["programming", "problem_solving", "testing"]
            },
            TaskType.ANALYSIS: {
                "typical_subtasks": ["data_preparation", "analysis", "visualization", "interpretation", "reporting"],
                "estimated_hours": 6.0,
                "required_skills": ["analysis", "research", "communication"]
            },
            TaskType.CREATIVE: {
                "typical_subtasks": ["brainstorming", "concept_development", "creation", "review", "refinement"],
                "estimated_hours": 10.0,
                "required_skills": ["creative", "communication", "problem_solving"]
            }
        }
        
        # System configuration
        self.config = {
            "max_concurrent_tasks": 20,
            "max_subtasks_per_task": 10,
            "default_task_timeout_hours": 48.0,
            "coordination_check_interval_minutes": 15.0,
            "progress_update_interval_minutes": 30.0,
            "auto_escalation_hours": 8.0,
            "quality_threshold": 0.7,
            "max_agents_per_task": 5
        }
        
        # Statistics
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "average_completion_time": 0.0,
            "average_satisfaction": 0.0,
            "tasks_by_type": {task_type.value: 0 for task_type in TaskType},
            "collaboration_efficiency": 0.0,
            "resource_utilization": 0.0
        }
        
        # Counters
        self.task_counter = 0
        self.assignment_counter = 0
        
        self.logger.info("Task delegator initialized")
    
    async def initialize(self) -> None:
        """Initialize the task delegator."""
        try:
            # Start background processes
            asyncio.create_task(self._task_processor())
            asyncio.create_task(self._coordination_monitor())
            asyncio.create_task(self._progress_tracker())
            
            self.logger.info("Task delegator initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize task delegator: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the task delegator."""
        try:
            # Complete pending tasks
            while not self.task_queue.empty():
                await asyncio.sleep(0.1)
            
            # Save task state
            await self._save_task_state()
            
            self.logger.info("Task delegator shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during task delegator shutdown: {e}")
    
    async def create_task_from_command(
        self,
        command: HumanCommand,
        task_type: TaskType,
        requirements: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        success_criteria: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a delegated task from a human command."""
        try:
            # Check system capacity
            if len(self.tasks) >= self.config["max_concurrent_tasks"]:
                return {"success": False, "error": "System at maximum task capacity"}
            
            # Create task
            self.task_counter += 1
            task_id = f"task_{self.task_counter}_{datetime.now().timestamp()}"
            
            # Map command priority to task priority
            priority_mapping = {
                CommandPriority.LOW: TaskPriority.LOW,
                CommandPriority.NORMAL: TaskPriority.NORMAL,
                CommandPriority.HIGH: TaskPriority.HIGH,
                CommandPriority.URGENT: TaskPriority.URGENT,
                CommandPriority.EMERGENCY: TaskPriority.CRITICAL
            }
            
            task = HumanTask(
                task_id=task_id,
                human_id=command.human_id,
                command_id=command.command_id,
                title=command.title,
                description=command.description,
                task_type=task_type,
                priority=priority_mapping.get(command.priority, TaskPriority.NORMAL),
                requirements=requirements or command.requirements,
                constraints=constraints or [],
                success_criteria=success_criteria or [],
                deadline=command.deadline
            )
            
            # Store task
            self.tasks[task_id] = task
            
            # Queue for processing
            await self.task_queue.put(task_id)
            
            # Update statistics
            self.stats["total_tasks"] += 1
            self.stats["tasks_by_type"][task_type.value] += 1
            
            log_agent_event(
                self.agent_id,
                "task_created_from_command",
                {
                    "task_id": task_id,
                    "command_id": command.command_id,
                    "human_id": command.human_id,
                    "task_type": task_type.value,
                    "priority": task.priority.value
                }
            )
            
            result = {
                "success": True,
                "task_id": task_id,
                "status": task.status.value,
                "estimated_duration": await self._estimate_task_duration(task),
                "deadline": task.deadline.isoformat() if task.deadline else None
            }
            
            self.logger.info(f"Task created from command: {task.title}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create task from command: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_standalone_task(
        self,
        human_id: str,
        title: str,
        description: str,
        task_type: TaskType,
        priority: TaskPriority = TaskPriority.NORMAL,
        requirements: Optional[List[str]] = None,
        deadline: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create a standalone delegated task."""
        try:
            if len(self.tasks) >= self.config["max_concurrent_tasks"]:
                return {"success": False, "error": "System at maximum task capacity"}
            
            self.task_counter += 1
            task_id = f"task_{self.task_counter}_{datetime.now().timestamp()}"
            
            task = HumanTask(
                task_id=task_id,
                human_id=human_id,
                title=title,
                description=description,
                task_type=task_type,
                priority=priority,
                requirements=requirements or [],
                deadline=deadline
            )
            
            self.tasks[task_id] = task
            await self.task_queue.put(task_id)
            
            self.stats["total_tasks"] += 1
            self.stats["tasks_by_type"][task_type.value] += 1
            
            log_agent_event(
                self.agent_id,
                "standalone_task_created",
                {
                    "task_id": task_id,
                    "human_id": human_id,
                    "task_type": task_type.value,
                    "priority": priority.value
                }
            )
            
            result = {
                "success": True,
                "task_id": task_id,
                "status": task.status.value,
                "estimated_duration": await self._estimate_task_duration(task)
            }
            
            self.logger.info(f"Standalone task created: {title}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create standalone task: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get detailed status of a task."""
        try:
            if task_id not in self.tasks:
                return {"error": "Task not found"}
            
            task = self.tasks[task_id]
            
            # Get subtask information
            subtask_info = []
            for subtask_id in task.subtasks:
                if subtask_id in self.subtasks:
                    subtask = self.subtasks[subtask_id]
                    subtask_info.append({
                        "subtask_id": subtask.task_id,
                        "title": subtask.title,
                        "status": subtask.status.value,
                        "progress": subtask.progress.overall_progress,
                        "assigned_agents": subtask.get_assigned_agents()
                    })
            
            # Get assignment information
            assignment_info = []
            for assignment in task.assignments.values():
                assignment_info.append({
                    "assignment_id": assignment.assignment_id,
                    "agent_id": assignment.agent_id,
                    "role": assignment.role,
                    "progress": assignment.progress_percentage,
                    "estimated_hours": assignment.estimated_hours,
                    "actual_hours": assignment.actual_hours
                })
            
            # Get milestone information
            milestone_info = []
            for milestone in task.progress.milestones:
                milestone_info.append({
                    "id": milestone["id"],
                    "name": milestone["name"],
                    "completed": milestone["completed"],
                    "target_date": milestone["target_date"],
                    "completed_date": milestone.get("completed_date")
                })
            
            return {
                "task_id": task.task_id,
                "title": task.title,
                "description": task.description,
                "task_type": task.task_type.value,
                "priority": task.priority.value,
                "status": task.status.value,
                "progress": task.progress.overall_progress,
                "created_at": task.created_at.isoformat(),
                "planned_start": task.planned_start.isoformat() if task.planned_start else None,
                "planned_end": task.planned_end.isoformat() if task.planned_end else None,
                "actual_start": task.actual_start.isoformat() if task.actual_start else None,
                "actual_end": task.actual_end.isoformat() if task.actual_end else None,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "duration_hours": task.get_duration(),
                "is_overdue": task.is_overdue(),
                "coordinator_agent": task.coordinator_agent_id,
                "assignments": assignment_info,
                "subtasks": subtask_info,
                "milestones": milestone_info,
                "estimated_hours": task.estimated_agent_hours,
                "actual_hours": task.actual_agent_hours,
                "blockers": task.progress.blockers,
                "human_satisfaction": task.human_satisfaction,
                "human_feedback": task.human_feedback
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get task status: {e}")
            return {"error": str(e)}
    
    async def assign_agent_to_task(
        self,
        task_id: str,
        agent_id: str,
        role: str = "collaborator",
        estimated_hours: float = 1.0
    ) -> Dict[str, Any]:
        """Assign an agent to a task."""
        try:
            if task_id not in self.tasks:
                return {"success": False, "error": "Task not found"}
            
            task = self.tasks[task_id]
            
            # Check if agent is already assigned
            for assignment in task.assignments.values():
                if assignment.agent_id == agent_id:
                    return {"success": False, "error": "Agent already assigned to this task"}
            
            # Check agent limits
            if len(task.assignments) >= self.config["max_agents_per_task"]:
                return {"success": False, "error": "Maximum agents per task exceeded"}
            
            # Create assignment
            self.assignment_counter += 1
            assignment_id = f"assign_{self.assignment_counter}_{datetime.now().timestamp()}"
            
            assignment = TaskAssignment(
                assignment_id=assignment_id,
                task_id=task_id,
                agent_id=agent_id,
                role=role,
                estimated_hours=estimated_hours
            )
            
            task.assignments[assignment_id] = assignment
            
            # Set coordinator if this is the first primary agent
            if role == "primary" and not task.coordinator_agent_id:
                task.coordinator_agent_id = agent_id
            
            # Update task status if needed
            if task.status == TaskStatus.CREATED:
                task.status = TaskStatus.ASSIGNED
            
            assignment.add_status_update(f"Assigned to task as {role}")
            
            log_agent_event(
                self.agent_id,
                "agent_assigned_to_task",
                {
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "role": role,
                    "assignment_id": assignment_id
                }
            )
            
            result = {
                "success": True,
                "assignment_id": assignment_id,
                "role": role,
                "estimated_hours": estimated_hours
            }
            
            self.logger.info(f"Agent {agent_id} assigned to task {task_id} as {role}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to assign agent to task: {e}")
            return {"success": False, "error": str(e)}
   
    async def update_task_progress(
        self,
        task_id: str,
        agent_id: str,
        progress_percentage: float,
        status_update: str = "",
        quality_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update progress on a task."""
        try:
            if task_id not in self.tasks:
                return {"success": False, "error": "Task not found"}
            
            task = self.tasks[task_id]
            
            # Find agent's assignment
            agent_assignment = None
            for assignment in task.assignments.values():
                if assignment.agent_id == agent_id:
                    agent_assignment = assignment
                    break
            
            if not agent_assignment:
                return {"success": False, "error": "Agent not assigned to this task"}
            
            # Update assignment progress
            agent_assignment.progress_percentage = max(0.0, min(100.0, progress_percentage))
            
            if status_update:
                agent_assignment.add_status_update(status_update)
            
            if quality_score is not None:
                agent_assignment.quality_score = max(0.0, min(1.0, quality_score))
            
            # Calculate overall task progress
            await self._calculate_overall_progress(task)
            
            # Update task status based on progress
            if task.progress.overall_progress >= 100.0 and task.status == TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.REVIEW
                task.actual_end = datetime.now()
            elif task.progress.overall_progress > 0.0 and task.status == TaskStatus.ASSIGNED:
                task.status = TaskStatus.IN_PROGRESS
                task.actual_start = datetime.now()
            
            log_agent_event(
                self.agent_id,
                "task_progress_updated",
                {
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "progress": progress_percentage,
                    "overall_progress": task.progress.overall_progress
                }
            )
            
            result = {
                "success": True,
                "agent_progress": agent_assignment.progress_percentage,
                "overall_progress": task.progress.overall_progress,
                "task_status": task.status.value
            }
            
            self.logger.info(f"Task progress updated: {task_id} - {task.progress.overall_progress:.1f}%")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to update task progress: {e}")
            return {"success": False, "error": str(e)}
    
    async def complete_task(
        self,
        task_id: str,
        deliverables: List[Dict[str, Any]],
        completion_notes: str = ""
    ) -> Dict[str, Any]:
        """Mark a task as completed."""
        try:
            if task_id not in self.tasks:
                return {"success": False, "error": "Task not found"}
            
            task = self.tasks[task_id]
            
            if task.status not in [TaskStatus.IN_PROGRESS, TaskStatus.REVIEW]:
                return {"success": False, "error": f"Task not ready for completion (status: {task.status.value})"}
            
            # Complete the task
            task.status = TaskStatus.COMPLETED
            task.actual_end = datetime.now()
            task.progress.overall_progress = 100.0
            task.deliverables = deliverables
            
            # Calculate actual hours
            task.actual_agent_hours = sum(assignment.actual_hours for assignment in task.assignments.values())
            
            # Update all assignments to completed
            for assignment in task.assignments.values():
                assignment.progress_percentage = 100.0
                assignment.add_status_update("Task completed")
            
            # Complete all subtasks
            for subtask_id in task.subtasks:
                if subtask_id in self.subtasks:
                    subtask = self.subtasks[subtask_id]
                    if subtask.status != TaskStatus.COMPLETED:
                        subtask.status = TaskStatus.COMPLETED
                        subtask.progress.overall_progress = 100.0
            
            # Update statistics
            self.stats["completed_tasks"] += 1
            
            # Calculate average completion time
            duration = task.get_duration()
            current_avg = self.stats["average_completion_time"]
            completed_count = self.stats["completed_tasks"]
            self.stats["average_completion_time"] = ((current_avg * (completed_count - 1)) + duration) / completed_count
            
            # Update command status if linked
            if task.command_id:
                await self.command_router.submit_command_response(
                    agent_id=task.coordinator_agent_id or "system",
                    command_id=task.command_id,
                    response_type="completion",
                    content=f"Task completed successfully. {completion_notes}",
                    confidence_level=1.0
                )
            
            log_agent_event(
                self.agent_id,
                "task_completed",
                {
                    "task_id": task_id,
                    "duration_hours": duration,
                    "deliverables_count": len(deliverables),
                    "agents_involved": len(task.assignments)
                }
            )
            
            result = {
                "success": True,
                "status": task.status.value,
                "duration_hours": duration,
                "deliverables_count": len(deliverables),
                "agents_involved": len(task.assignments)
            }
            
            self.logger.info(f"Task completed: {task.title} in {duration:.1f} hours")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to complete task: {e}")
            return {"success": False, "error": str(e)}
    
    async def add_task_blocker(
        self,
        task_id: str,
        blocker_description: str,
        blocker_type: str = "dependency",
        severity: str = "medium"
    ) -> Dict[str, Any]:
        """Add a blocker to a task."""
        try:
            if task_id not in self.tasks:
                return {"success": False, "error": "Task not found"}
            
            task = self.tasks[task_id]
            
            blocker = {
                "id": f"blocker_{len(task.progress.blockers)}",
                "description": blocker_description,
                "type": blocker_type,
                "severity": severity,
                "created_at": datetime.now().isoformat(),
                "resolved": False,
                "resolved_at": None
            }
            
            task.progress.blockers.append(blocker)
            
            # Update task status if not already blocked
            if task.status == TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.BLOCKED
            
            log_agent_event(
                self.agent_id,
                "task_blocker_added",
                {
                    "task_id": task_id,
                    "blocker_type": blocker_type,
                    "severity": severity
                }
            )
            
            result = {
                "success": True,
                "blocker_id": blocker["id"],
                "task_status": task.status.value
            }
            
            self.logger.info(f"Blocker added to task {task_id}: {blocker_description}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to add task blocker: {e}")
            return {"success": False, "error": str(e)}
    
    async def resolve_task_blocker(
        self,
        task_id: str,
        blocker_id: str,
        resolution_notes: str = ""
    ) -> Dict[str, Any]:
        """Resolve a task blocker."""
        try:
            if task_id not in self.tasks:
                return {"success": False, "error": "Task not found"}
            
            task = self.tasks[task_id]
            
            # Find and resolve blocker
            blocker_found = False
            for blocker in task.progress.blockers:
                if blocker["id"] == blocker_id:
                    blocker["resolved"] = True
                    blocker["resolved_at"] = datetime.now().isoformat()
                    blocker["resolution_notes"] = resolution_notes
                    task.progress.resolved_issues += 1
                    blocker_found = True
                    break
            
            if not blocker_found:
                return {"success": False, "error": "Blocker not found"}
            
            # Check if all blockers are resolved
            unresolved_blockers = [b for b in task.progress.blockers if not b["resolved"]]
            
            if not unresolved_blockers and task.status == TaskStatus.BLOCKED:
                task.status = TaskStatus.IN_PROGRESS
            
            log_agent_event(
                self.agent_id,
                "task_blocker_resolved",
                {
                    "task_id": task_id,
                    "blocker_id": blocker_id,
                    "remaining_blockers": len(unresolved_blockers)
                }
            )
            
            result = {
                "success": True,
                "task_status": task.status.value,
                "remaining_blockers": len(unresolved_blockers)
            }
            
            self.logger.info(f"Blocker resolved for task {task_id}: {blocker_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to resolve task blocker: {e}")
            return {"success": False, "error": str(e)}
    
    def get_human_tasks(self, human_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks, optionally filtered by human ID."""
        try:
            tasks = []
            
            for task in self.tasks.values():
                if human_id and task.human_id != human_id:
                    continue
                
                task_info = {
                    "task_id": task.task_id,
                    "title": task.title,
                    "task_type": task.task_type.value,
                    "priority": task.priority.value,
                    "status": task.status.value,
                    "progress": task.progress.overall_progress,
                    "created_at": task.created_at.isoformat(),
                    "deadline": task.deadline.isoformat() if task.deadline else None,
                    "assigned_agents": task.get_assigned_agents(),
                    "coordinator": task.coordinator_agent_id,
                    "subtasks_count": len(task.subtasks),
                    "is_overdue": task.is_overdue(),
                    "human_satisfaction": task.human_satisfaction
                }
                
                tasks.append(task_info)
            
            # Sort by creation time (most recent first)
            tasks.sort(key=lambda t: t["created_at"], reverse=True)
            
            return tasks
            
        except Exception as e:
            self.logger.error(f"Failed to get human tasks: {e}")
            return []
    
    def get_agent_tasks(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get tasks assigned to a specific agent."""
        try:
            agent_tasks = []
            
            for task in self.tasks.values():
                # Check if agent is assigned to this task
                agent_assignment = None
                for assignment in task.assignments.values():
                    if assignment.agent_id == agent_id:
                        agent_assignment = assignment
                        break
                
                if agent_assignment:
                    task_info = {
                        "task_id": task.task_id,
                        "title": task.title,
                        "task_type": task.task_type.value,
                        "status": task.status.value,
                        "progress": task.progress.overall_progress,
                        "agent_role": agent_assignment.role,
                        "agent_progress": agent_assignment.progress_percentage,
                        "estimated_hours": agent_assignment.estimated_hours,
                        "actual_hours": agent_assignment.actual_hours,
                        "assigned_at": agent_assignment.assigned_at.isoformat(),
                        "deadline": task.deadline.isoformat() if task.deadline else None,
                        "is_overdue": task.is_overdue()
                    }
                    
                    agent_tasks.append(task_info)
            
            # Sort by assignment time (most recent first)
            agent_tasks.sort(key=lambda t: t["assigned_at"], reverse=True)
            
            return agent_tasks
            
        except Exception as e:
            self.logger.error(f"Failed to get agent tasks: {e}")
            return []
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get task delegation statistics."""
        try:
            # Calculate additional metrics
            active_tasks = len([t for t in self.tasks.values() 
                              if t.status in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]])
            
            blocked_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.BLOCKED])
            overdue_tasks = len([t for t in self.tasks.values() if t.is_overdue()])
            
            # Calculate success rate
            success_rate = 0.0
            if self.stats["total_tasks"] > 0:
                success_rate = (self.stats["completed_tasks"] / self.stats["total_tasks"]) * 100.0
            
            # Calculate collaboration metrics
            total_assignments = sum(len(task.assignments) for task in self.tasks.values())
            avg_agents_per_task = total_assignments / max(1, len(self.tasks))
            
            # Calculate resource utilization
            total_estimated_hours = sum(task.estimated_agent_hours for task in self.tasks.values())
            total_actual_hours = sum(task.actual_agent_hours for task in self.tasks.values())
            resource_efficiency = (total_actual_hours / max(1, total_estimated_hours)) * 100.0
            
            # Status breakdown
            status_breakdown = {}
            for status in TaskStatus:
                status_breakdown[status.value] = len([t for t in self.tasks.values() if t.status == status])
            
            return {
                "total_tasks": self.stats["total_tasks"],
                "completed_tasks": self.stats["completed_tasks"],
                "failed_tasks": self.stats["failed_tasks"],
                "active_tasks": active_tasks,
                "blocked_tasks": blocked_tasks,
                "overdue_tasks": overdue_tasks,
                "success_rate_percent": success_rate,
                "average_completion_time_hours": self.stats["average_completion_time"],
                "average_satisfaction": self.stats["average_satisfaction"],
                "tasks_by_type": self.stats["tasks_by_type"],
                "status_breakdown": status_breakdown,
                "average_agents_per_task": avg_agents_per_task,
                "resource_efficiency_percent": resource_efficiency,
                "total_assignments": total_assignments,
                "total_subtasks": len(self.subtasks)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get task statistics: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _estimate_task_duration(self, task: HumanTask) -> float:
        """Estimate task duration in hours."""
        try:
            # Get base estimate from template
            template = self.task_templates.get(task.task_type, {"estimated_hours": 4.0})
            base_hours = template["estimated_hours"]
            
            # Adjust based on priority
            priority_multipliers = {
                TaskPriority.LOW: 1.2,
                TaskPriority.NORMAL: 1.0,
                TaskPriority.HIGH: 0.8,
                TaskPriority.URGENT: 0.6,
                TaskPriority.CRITICAL: 0.4
            }
            
            priority_multiplier = priority_multipliers.get(task.priority, 1.0)
            
            # Adjust based on complexity (number of requirements)
            complexity_multiplier = 1.0 + (len(task.requirements) * 0.1)
            
            estimated_hours = base_hours * priority_multiplier * complexity_multiplier
            
            return max(1.0, estimated_hours)
            
        except Exception as e:
            self.logger.error(f"Error estimating task duration: {e}")
            return 4.0
    
    async def _break_down_task(self, task: HumanTask) -> List[str]:
        """Break down a task into subtasks."""
        try:
            template = self.task_templates.get(task.task_type, {"typical_subtasks": []})
            typical_subtasks = template["typical_subtasks"]
            
            subtask_ids = []
            
            for i, subtask_name in enumerate(typical_subtasks):
                if len(subtask_ids) >= self.config["max_subtasks_per_task"]:
                    break
                
                # Create subtask
                subtask_id = f"{task.task_id}_sub_{i}"
                
                subtask = HumanTask(
                    task_id=subtask_id,
                    human_id=task.human_id,
                    title=f"{task.title} - {subtask_name.replace('_', ' ').title()}",
                    description=f"Subtask: {subtask_name.replace('_', ' ')}",
                    task_type=task.task_type,
                    priority=task.priority
                )
                
                # Set parent task reference
                subtask.metadata["parent_task_id"] = task.task_id
                
                self.subtasks[subtask_id] = subtask
                subtask_ids.append(subtask_id)
            
            return subtask_ids
            
        except Exception as e:
            self.logger.error(f"Error breaking down task: {e}")
            return []
    
    async def _calculate_overall_progress(self, task: HumanTask) -> None:
        """Calculate overall task progress based on assignments and subtasks."""
        try:
            total_progress = 0.0
            weight_sum = 0.0
            
            # Weight by assignment hours
            for assignment in task.assignments.values():
                weight = assignment.estimated_hours
                total_progress += assignment.progress_percentage * weight
                weight_sum += weight
            
            # Include subtask progress
            for subtask_id in task.subtasks:
                if subtask_id in self.subtasks:
                    subtask = self.subtasks[subtask_id]
                    weight = subtask.estimated_agent_hours or 1.0
                    total_progress += subtask.progress.overall_progress * weight
                    weight_sum += weight
            
            if weight_sum > 0:
                task.progress.overall_progress = total_progress / weight_sum
            else:
                # Fallback to simple average
                all_progress = [a.progress_percentage for a in task.assignments.values()]
                if all_progress:
                    task.progress.overall_progress = sum(all_progress) / len(all_progress)
            
            # Update time estimates
            if task.progress.overall_progress > 0:
                elapsed_time = task.get_duration()
                if elapsed_time > 0:
                    estimated_total = elapsed_time / (task.progress.overall_progress / 100.0)
                    task.progress.time_remaining = max(0, estimated_total - elapsed_time)
            
        except Exception as e:
            self.logger.error(f"Error calculating overall progress: {e}")
    
    async def _task_processor(self) -> None:
        """Background task to process new tasks."""
        while True:
            try:
                # Get task from queue
                task_id = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                if task_id not in self.tasks:
                    continue
                
                task = self.tasks[task_id]
                
                # Process the task
                await self._process_new_task(task)
                
                self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in task processor: {e}")
                await asyncio.sleep(1)
    
    async def _process_new_task(self, task: HumanTask) -> None:
        """Process a newly created task."""
        try:
            task.status = TaskStatus.PLANNING
            
            # Estimate duration
            task.estimated_agent_hours = await self._estimate_task_duration(task)
            
            # Break down into subtasks if complex
            if task.estimated_agent_hours > 8.0:  # Complex task
                subtask_ids = await self._break_down_task(task)
                task.subtasks = subtask_ids
            
            # Set up milestones
            await self._create_task_milestones(task)
            
            # Try to find and assign suitable agents
            await self._auto_assign_agents(task)
            
            log_agent_event(
                self.agent_id,
                "task_processed",
                {
                    "task_id": task.task_id,
                    "estimated_hours": task.estimated_agent_hours,
                    "subtasks_created": len(task.subtasks),
                    "status": task.status.value
                }
            )
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            self.stats["failed_tasks"] += 1
            self.logger.error(f"Error processing task {task.task_id}: {e}")
    
    async def _create_task_milestones(self, task: HumanTask) -> None:
        """Create milestones for a task."""
        try:
            if task.deadline:
                # Create milestones based on task type
                if task.task_type == TaskType.DEVELOPMENT:
                    milestones = [
                        ("Requirements Complete", 0.2),
                        ("Design Complete", 0.4),
                        ("Implementation Complete", 0.8),
                        ("Testing Complete", 0.95)
                    ]
                elif task.task_type == TaskType.RESEARCH:
                    milestones = [
                        ("Data Collection Complete", 0.3),
                        ("Analysis Complete", 0.7),
                        ("Report Draft Complete", 0.9)
                    ]
                else:
                    milestones = [
                        ("Planning Complete", 0.25),
                        ("Execution Halfway", 0.5),
                        ("Review Ready", 0.9)
                    ]
                
                # Calculate milestone dates
                total_duration = (task.deadline - task.created_at).total_seconds() / 3600.0
                
                for milestone_name, progress_ratio in milestones:
                    milestone_date = task.created_at + timedelta(hours=total_duration * progress_ratio)
                    task.progress.add_milestone(milestone_name, f"Milestone at {progress_ratio*100}% progress", milestone_date)
            
        except Exception as e:
            self.logger.error(f"Error creating task milestones: {e}")
    
    async def _auto_assign_agents(self, task: HumanTask) -> None:
        """Automatically assign suitable agents to a task."""
        try:
            # Get available expert agents from command router
            expert_agents = self.command_router.get_expert_agents()
            
            # Filter by task type requirements
            template = self.task_templates.get(task.task_type, {"required_skills": []})
            required_skills = template["required_skills"]
            
            suitable_agents = []
            for agent_info in expert_agents:
                if not agent_info["is_available"]:
                    continue
                
                # Check if agent has required skills
                agent_domains = [domain.lower() for domain in agent_info["expertise_domains"]]
                skill_match = any(skill in agent_domains for skill in required_skills)
                
                if skill_match:
                    suitable_agents.append(agent_info)
            
            # Assign primary agent (best match)
            if suitable_agents:
                # Sort by overall score
                suitable_agents.sort(key=lambda a: a["overall_score"], reverse=True)
                primary_agent = suitable_agents[0]
                
                await self.assign_agent_to_task(
                    task.task_id,
                    primary_agent["agent_id"],
                    role="primary",
                    estimated_hours=task.estimated_agent_hours
                )
                
                # Assign collaborators for complex tasks
                if task.estimated_agent_hours > 12.0 and len(suitable_agents) > 1:
                    for agent_info in suitable_agents[1:2]:  # Up to 1 collaborator
                        await self.assign_agent_to_task(
                            task.task_id,
                            agent_info["agent_id"],
                            role="collaborator",
                            estimated_hours=task.estimated_agent_hours * 0.3
                        )
            
        except Exception as e:
            self.logger.error(f"Error auto-assigning agents: {e}")
    
    async def _coordination_monitor(self) -> None:
        """Background task to monitor task coordination."""
        while True:
            try:
                await asyncio.sleep(self.config["coordination_check_interval_minutes"] * 60)
                
                for task in self.tasks.values():
                    if task.status in [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]:
                        # Check for coordination issues
                        await self._check_coordination_issues(task)
                
            except Exception as e:
                self.logger.error(f"Error in coordination monitor: {e}")
                await asyncio.sleep(60)
    
    async def _check_coordination_issues(self, task: HumanTask) -> None:
        """Check for coordination issues in a task."""
        try:
            # Check for stalled progress
            if len(task.assignments) > 1:
                progress_values = [a.progress_percentage for a in task.assignments.values()]
                if progress_values:
                    progress_variance = max(progress_values) - min(progress_values)
                    
                    # High variance might indicate coordination issues
                    if progress_variance > 30.0:
                        await self.add_task_blocker(
                            task.task_id,
                            "High progress variance between agents - possible coordination issue",
                            "coordination",
                            "medium"
                        )
            
            # Check for overdue milestones
            current_time = datetime.now()
            for milestone in task.progress.milestones:
                if not milestone["completed"]:
                    target_date = datetime.fromisoformat(milestone["target_date"])
                    if current_time > target_date:
                        await self.add_task_blocker(
                            task.task_id,
                            f"Milestone '{milestone['name']}' is overdue",
                            "milestone",
                            "high"
                        )
            
        except Exception as e:
            self.logger.error(f"Error checking coordination issues: {e}")
    
    async def _progress_tracker(self) -> None:
        """Background task to track progress and update statistics."""
        while True:
            try:
                await asyncio.sleep(self.config["progress_update_interval_minutes"] * 60)
                
                # Update task progress and statistics
                for task in self.tasks.values():
                    if task.status == TaskStatus.IN_PROGRESS:
                        # Update actual hours
                        task.actual_agent_hours = sum(a.actual_hours for a in task.assignments.values())
                        
                        # Check for escalation
                        if task.get_duration() > self.config["auto_escalation_hours"]:
                            if task.progress.overall_progress < 50.0:
                                # Task is taking too long with little progress
                                await self.add_task_blocker(
                                    task.task_id,
                                    "Task progress slower than expected - may need escalation",
                                    "performance",
                                    "high"
                                )
                
            except Exception as e:
                self.logger.error(f"Error in progress tracker: {e}")
                await asyncio.sleep(300)
    
    async def _save_task_state(self) -> None:
        """Save task state to persistent storage."""
        try:
            # In a real implementation, this would save to database
            self.logger.info(f"Saved task state: {len(self.tasks)} tasks, {len(self.subtasks)} subtasks")
        except Exception as e:
            self.logger.error(f"Error saving task state: {e}")