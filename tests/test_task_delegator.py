"""
Tests for the task delegation and coordination system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from autonomous_ai_ecosystem.oversight.task_delegator import (
    TaskDelegator,
    HumanTask,
    TaskAssignment,
    TaskProgress,
    TaskDependency,
    TaskType,
    TaskStatus,
    TaskPriority
)
from autonomous_ai_ecosystem.oversight.command_router import (
    HumanCommandRouter,
    HumanCommand,
    CommandType,
    CommandPriority
)


class TestTaskDependency:
    """Test the TaskDependency class."""
    
    def test_dependency_creation(self):
        """Test creating a task dependency."""
        dependency = TaskDependency(
            dependent_task_id="task_2",
            prerequisite_task_id="task_1",
            dependency_type="finish_to_start",
            lag_hours=2.0
        )
        
        assert dependency.dependent_task_id == "task_2"
        assert dependency.prerequisite_task_id == "task_1"
        assert dependency.dependency_type == "finish_to_start"
        assert dependency.lag_hours == 2.0


class TestTaskAssignment:
    """Test the TaskAssignment class."""
    
    def test_assignment_creation(self):
        """Test creating a task assignment."""
        assignment = TaskAssignment(
            assignment_id="assign_1",
            task_id="task_1",
            agent_id="agent_1",
            role="primary",
            estimated_hours=8.0
        )
        
        assert assignment.assignment_id == "assign_1"
        assert assignment.task_id == "task_1"
        assert assignment.agent_id == "agent_1"
        assert assignment.role == "primary"
        assert assignment.estimated_hours == 8.0
        assert assignment.progress_percentage == 0.0
    
    def test_status_updates(self):
        """Test adding status updates to assignment."""
        assignment = TaskAssignment(
            assignment_id="assign_1",
            task_id="task_1",
            agent_id="agent_1",
            role="primary"
        )
        
        assignment.add_status_update("Started working on task")
        assignment.add_status_update("Made good progress")
        
        assert len(assignment.status_updates) == 2
        assert "Started working" in assignment.status_updates[0]
        assert "Made good progress" in assignment.status_updates[1]
        
        # Test status update limit
        for i in range(25):
            assignment.add_status_update(f"Update {i}")
        
        assert len(assignment.status_updates) == 20  # Should be limited


class TestTaskProgress:
    """Test the TaskProgress class."""
    
    def test_progress_creation(self):
        """Test creating task progress."""
        progress = TaskProgress(task_id="task_1")
        
        assert progress.task_id == "task_1"
        assert progress.overall_progress == 0.0
        assert progress.completed_milestones == 0
        assert len(progress.milestones) == 0
        assert len(progress.blockers) == 0
    
    def test_milestone_management(self):
        """Test milestone management."""
        progress = TaskProgress(task_id="task_1")
        
        # Add milestone
        target_date = datetime.now() + timedelta(days=1)
        progress.add_milestone("Design Complete", "Complete the design phase", target_date)
        
        assert len(progress.milestones) == 1
        milestone = progress.milestones[0]
        assert milestone["name"] == "Design Complete"
        assert milestone["completed"] is False
        
        # Complete milestone
        milestone_id = milestone["id"]
        result = progress.complete_milestone(milestone_id)
        
        assert result is True
        assert milestone["completed"] is True
        assert progress.completed_milestones == 1
        
        # Try to complete non-existent milestone
        result = progress.complete_milestone("nonexistent")
        assert result is False


class TestHumanTask:
    """Test the HumanTask class."""
    
    def test_task_creation(self):
        """Test creating a human task."""
        task = HumanTask(
            task_id="task_1",
            human_id="human_1",
            title="Test Task",
            description="A test task for the system",
            task_type=TaskType.DEVELOPMENT,
            priority=TaskPriority.HIGH
        )
        
        assert task.task_id == "task_1"
        assert task.human_id == "human_1"
        assert task.title == "Test Task"
        assert task.task_type == TaskType.DEVELOPMENT
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.CREATED
        assert task.progress.task_id == "task_1"  # Should be initialized
    
    def test_duration_calculation(self):
        """Test task duration calculation."""
        task = HumanTask(
            task_id="task_1",
            human_id="human_1",
            title="Test Task",
            description="Test task",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.NORMAL
        )
        
        # No start time
        assert task.get_duration() == 0.0
        
        # With start time
        task.actual_start = datetime.now() - timedelta(hours=3)
        duration = task.get_duration()
        assert 2.9 < duration < 3.1  # Approximately 3 hours
        
        # With end time
        task.actual_end = datetime.now() - timedelta(hours=1)
        duration = task.get_duration()
        assert 1.9 < duration < 2.1  # Approximately 2 hours
    
    def test_overdue_check(self):
        """Test overdue checking."""
        task = HumanTask(
            task_id="task_1",
            human_id="human_1",
            title="Test Task",
            description="Test task",
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.NORMAL,
            deadline=datetime.now() - timedelta(hours=1)  # Past deadline
        )
        
        assert task.is_overdue() is True
        
        # Future deadline
        task.deadline = datetime.now() + timedelta(hours=1)
        assert task.is_overdue() is False
        
        # Completed task should not be overdue
        task.deadline = datetime.now() - timedelta(hours=1)
        task.status = TaskStatus.COMPLETED
        assert task.is_overdue() is False
    
    def test_agent_management(self):
        """Test agent assignment management."""
        task = HumanTask(
            task_id="task_1",
            human_id="human_1",
            title="Test Task",
            description="Test task",
            task_type=TaskType.CREATIVE,
            priority=TaskPriority.NORMAL
        )
        
        # Add assignments
        assignment1 = TaskAssignment("assign_1", "task_1", "agent_1", "primary")
        assignment2 = TaskAssignment("assign_2", "task_1", "agent_2", "collaborator")
        
        task.assignments["assign_1"] = assignment1
        task.assignments["assign_2"] = assignment2
        
        # Test get assigned agents
        assigned_agents = task.get_assigned_agents()
        assert len(assigned_agents) == 2
        assert "agent_1" in assigned_agents
        assert "agent_2" in assigned_agents
        
        # Test get primary agent
        primary_agent = task.get_primary_agent()
        assert primary_agent == "agent_1"


class TestTaskDelegator:
    """Test the TaskDelegator class."""
    
    @pytest.fixture
    async def task_delegator(self):
        """Create a test task delegator."""
        # Create mock command router
        command_router = Mock(spec=HumanCommandRouter)
        command_router.get_expert_agents = Mock(return_value=[
            {
                "agent_id": "expert_1",
                "name": "Expert Agent 1",
                "expertise_domains": ["programming", "problem_solving"],
                "is_available": True,
                "overall_score": 0.9
            },
            {
                "agent_id": "expert_2",
                "name": "Expert Agent 2",
                "expertise_domains": ["research", "analysis"],
                "is_available": True,
                "overall_score": 0.8
            }
        ])
        command_router.submit_command_response = AsyncMock(return_value={"success": True})
        
        delegator = TaskDelegator("test_delegator", command_router)
        await delegator.initialize()
        return delegator
    
    @pytest.mark.asyncio
    async def test_delegator_initialization(self):
        """Test task delegator initialization."""
        command_router = Mock(spec=HumanCommandRouter)
        delegator = TaskDelegator("test_delegator", command_router)
        await delegator.initialize()
        
        assert len(delegator.tasks) == 0
        assert len(delegator.subtasks) == 0
        assert delegator.stats["total_tasks"] == 0
        
        await delegator.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_task_from_command(self, task_delegator):
        """Test creating a task from a human command."""
        # Create mock command
        command = HumanCommand(
            command_id="cmd_1",
            human_id="human_1",
            command_type=CommandType.TASK,
            priority=CommandPriority.HIGH,
            title="Develop New Feature",
            description="Develop a new feature for the application",
            requirements=["requirement_1", "requirement_2"]
        )
        
        result = await task_delegator.create_task_from_command(
            command=command,
            task_type=TaskType.DEVELOPMENT,
            success_criteria=["Feature works correctly", "Tests pass"]
        )
        
        assert result["success"] is True
        assert "task_id" in result
        assert result["status"] == TaskStatus.CREATED.value
        
        # Check task was stored
        task_id = result["task_id"]
        assert task_id in task_delegator.tasks
        
        task = task_delegator.tasks[task_id]
        assert task.title == "Develop New Feature"
        assert task.task_type == TaskType.DEVELOPMENT
        assert task.priority == TaskPriority.HIGH  # Mapped from command priority
        assert len(task.requirements) == 2
        assert len(task.success_criteria) == 2
    
    @pytest.mark.asyncio
    async def test_create_standalone_task(self, task_delegator):
        """Test creating a standalone task."""
        deadline = datetime.now() + timedelta(days=2)
        
        result = await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Research Market Trends",
            description="Conduct research on current market trends",
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.NORMAL,
            requirements=["Access to market data", "Analysis tools"],
            deadline=deadline
        )
        
        assert result["success"] is True
        assert "task_id" in result
        
        task_id = result["task_id"]
        task = task_delegator.tasks[task_id]
        assert task.title == "Research Market Trends"
        assert task.task_type == TaskType.RESEARCH
        assert task.deadline == deadline
        assert len(task.requirements) == 2
    
    @pytest.mark.asyncio
    async def test_get_task_status(self, task_delegator):
        """Test getting task status."""
        # Create a task first
        result = await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Test Task",
            description="A test task",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.NORMAL
        )
        task_id = result["task_id"]
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Get status
        status = await task_delegator.get_task_status(task_id)
        
        assert "task_id" in status
        assert status["task_id"] == task_id
        assert status["title"] == "Test Task"
        assert status["task_type"] == TaskType.ANALYSIS.value
        assert "progress" in status
        assert "assignments" in status
        assert "subtasks" in status
        assert "milestones" in status
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_task_status(self, task_delegator):
        """Test getting status of nonexistent task."""
        status = await task_delegator.get_task_status("nonexistent")
        
        assert "error" in status
    
    @pytest.mark.asyncio
    async def test_assign_agent_to_task(self, task_delegator):
        """Test assigning an agent to a task."""
        # Create a task
        result = await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Test Task",
            description="A test task",
            task_type=TaskType.DEVELOPMENT,
            priority=TaskPriority.NORMAL
        )
        task_id = result["task_id"]
        
        # Assign agent
        assign_result = await task_delegator.assign_agent_to_task(
            task_id=task_id,
            agent_id="agent_1",
            role="primary",
            estimated_hours=8.0
        )
        
        assert assign_result["success"] is True
        assert "assignment_id" in assign_result
        assert assign_result["role"] == "primary"
        
        # Check assignment was stored
        task = task_delegator.tasks[task_id]
        assert len(task.assignments) == 1
        
        assignment = list(task.assignments.values())[0]
        assert assignment.agent_id == "agent_1"
        assert assignment.role == "primary"
        assert assignment.estimated_hours == 8.0
        
        # Check coordinator was set
        assert task.coordinator_agent_id == "agent_1"
    
    @pytest.mark.asyncio
    async def test_assign_duplicate_agent(self, task_delegator):
        """Test assigning the same agent twice to a task."""
        # Create task and assign agent
        result = await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Test Task",
            description="Test task",
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.NORMAL
        )
        task_id = result["task_id"]
        
        await task_delegator.assign_agent_to_task(task_id, "agent_1", "primary")
        
        # Try to assign same agent again
        assign_result = await task_delegator.assign_agent_to_task(task_id, "agent_1", "collaborator")
        
        assert assign_result["success"] is False
        assert "already assigned" in assign_result["error"]
    
    @pytest.mark.asyncio
    async def test_update_task_progress(self, task_delegator):
        """Test updating task progress."""
        # Create task and assign agent
        result = await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Test Task",
            description="Test task",
            task_type=TaskType.CREATIVE,
            priority=TaskPriority.NORMAL
        )
        task_id = result["task_id"]
        
        await task_delegator.assign_agent_to_task(task_id, "agent_1", "primary")
        
        # Update progress
        progress_result = await task_delegator.update_task_progress(
            task_id=task_id,
            agent_id="agent_1",
            progress_percentage=50.0,
            status_update="Halfway through the task",
            quality_score=0.8
        )
        
        assert progress_result["success"] is True
        assert progress_result["agent_progress"] == 50.0
        assert progress_result["overall_progress"] == 50.0
        
        # Check task status changed
        task = task_delegator.tasks[task_id]
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.actual_start is not None
        
        # Check assignment was updated
        assignment = list(task.assignments.values())[0]
        assert assignment.progress_percentage == 50.0
        assert assignment.quality_score == 0.8
        assert len(assignment.status_updates) > 0
    
    @pytest.mark.asyncio
    async def test_update_progress_unauthorized(self, task_delegator):
        """Test updating progress from unauthorized agent."""
        # Create task
        result = await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Test Task",
            description="Test task",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.NORMAL
        )
        task_id = result["task_id"]
        
        # Try to update progress without assignment
        progress_result = await task_delegator.update_task_progress(
            task_id=task_id,
            agent_id="unauthorized_agent",
            progress_percentage=25.0
        )
        
        assert progress_result["success"] is False
        assert "not assigned" in progress_result["error"]
    
    @pytest.mark.asyncio
    async def test_complete_task(self, task_delegator):
        """Test completing a task."""
        # Create task, assign agent, and start progress
        result = await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Test Task",
            description="Test task",
            task_type=TaskType.PLANNING,
            priority=TaskPriority.NORMAL
        )
        task_id = result["task_id"]
        
        await task_delegator.assign_agent_to_task(task_id, "agent_1", "primary")
        await task_delegator.update_task_progress(task_id, "agent_1", 90.0)
        
        # Complete task
        deliverables = [
            {"type": "document", "name": "Project Plan", "description": "Detailed project plan"}
        ]
        
        complete_result = await task_delegator.complete_task(
            task_id=task_id,
            deliverables=deliverables,
            completion_notes="Task completed successfully"
        )
        
        assert complete_result["success"] is True
        assert complete_result["status"] == TaskStatus.COMPLETED.value
        assert complete_result["deliverables_count"] == 1
        
        # Check task was updated
        task = task_delegator.tasks[task_id]
        assert task.status == TaskStatus.COMPLETED
        assert task.actual_end is not None
        assert task.progress.overall_progress == 100.0
        assert len(task.deliverables) == 1
    
    @pytest.mark.asyncio
    async def test_add_task_blocker(self, task_delegator):
        """Test adding a blocker to a task."""
        # Create task
        result = await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Test Task",
            description="Test task",
            task_type=TaskType.DEVELOPMENT,
            priority=TaskPriority.NORMAL
        )
        task_id = result["task_id"]
        
        # Add blocker
        blocker_result = await task_delegator.add_task_blocker(
            task_id=task_id,
            blocker_description="Waiting for external API access",
            blocker_type="dependency",
            severity="high"
        )
        
        assert blocker_result["success"] is True
        assert "blocker_id" in blocker_result
        assert blocker_result["task_status"] == TaskStatus.BLOCKED.value
        
        # Check blocker was added
        task = task_delegator.tasks[task_id]
        assert len(task.progress.blockers) == 1
        
        blocker = task.progress.blockers[0]
        assert blocker["description"] == "Waiting for external API access"
        assert blocker["type"] == "dependency"
        assert blocker["severity"] == "high"
        assert blocker["resolved"] is False
    
    @pytest.mark.asyncio
    async def test_resolve_task_blocker(self, task_delegator):
        """Test resolving a task blocker."""
        # Create task and add blocker
        result = await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Test Task",
            description="Test task",
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.NORMAL
        )
        task_id = result["task_id"]
        
        blocker_result = await task_delegator.add_task_blocker(
            task_id=task_id,
            blocker_description="Missing data source",
            blocker_type="resource"
        )
        blocker_id = blocker_result["blocker_id"]
        
        # Resolve blocker
        resolve_result = await task_delegator.resolve_task_blocker(
            task_id=task_id,
            blocker_id=blocker_id,
            resolution_notes="Data source has been provided"
        )
        
        assert resolve_result["success"] is True
        assert resolve_result["task_status"] == TaskStatus.IN_PROGRESS.value
        assert resolve_result["remaining_blockers"] == 0
        
        # Check blocker was resolved
        task = task_delegator.tasks[task_id]
        blocker = task.progress.blockers[0]
        assert blocker["resolved"] is True
        assert blocker["resolution_notes"] == "Data source has been provided"
        assert task.progress.resolved_issues == 1
    
    def test_get_human_tasks(self, task_delegator):
        """Test getting human tasks."""
        # This test needs to be run after delegator initialization
        asyncio.run(self._test_get_human_tasks_async(task_delegator))
    
    async def _test_get_human_tasks_async(self, task_delegator):
        """Async helper for human tasks test."""
        # Create some tasks
        await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Task 1",
            description="First task",
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.HIGH
        )
        
        await task_delegator.create_standalone_task(
            human_id="human_2",
            title="Task 2",
            description="Second task",
            task_type=TaskType.DEVELOPMENT,
            priority=TaskPriority.NORMAL
        )
        
        # Get all tasks
        all_tasks = task_delegator.get_human_tasks()
        assert len(all_tasks) >= 2
        
        # Get tasks by human
        human1_tasks = task_delegator.get_human_tasks(human_id="human_1")
        assert len(human1_tasks) >= 1
        assert human1_tasks[0]["title"] == "Task 1"
    
    def test_get_agent_tasks(self, task_delegator):
        """Test getting agent tasks."""
        asyncio.run(self._test_get_agent_tasks_async(task_delegator))
    
    async def _test_get_agent_tasks_async(self, task_delegator):
        """Async helper for agent tasks test."""
        # Create task and assign agent
        result = await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Agent Task",
            description="Task for agent",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.NORMAL
        )
        task_id = result["task_id"]
        
        await task_delegator.assign_agent_to_task(task_id, "agent_1", "primary")
        
        # Get agent tasks
        agent_tasks = task_delegator.get_agent_tasks("agent_1")
        
        assert len(agent_tasks) >= 1
        task_info = agent_tasks[0]
        assert task_info["title"] == "Agent Task"
        assert task_info["agent_role"] == "primary"
    
    def test_get_task_statistics(self, task_delegator):
        """Test getting task statistics."""
        asyncio.run(self._test_get_task_statistics_async(task_delegator))
    
    async def _test_get_task_statistics_async(self, task_delegator):
        """Async helper for task statistics test."""
        # Create some tasks to generate statistics
        await task_delegator.create_standalone_task(
            human_id="human_1",
            title="Task 1",
            description="First task",
            task_type=TaskType.RESEARCH,
            priority=TaskPriority.NORMAL
        )
        
        await task_delegator.create_standalone_task(
            human_id="human_2",
            title="Task 2",
            description="Second task",
            task_type=TaskType.DEVELOPMENT,
            priority=TaskPriority.HIGH
        )
        
        # Get statistics
        stats = task_delegator.get_task_statistics()
        
        assert "total_tasks" in stats
        assert "completed_tasks" in stats
        assert "active_tasks" in stats
        assert "success_rate_percent" in stats
        assert "tasks_by_type" in stats
        assert "status_breakdown" in stats
        assert "average_agents_per_task" in stats
        
        assert stats["total_tasks"] >= 2


if __name__ == "__main__":
    pytest.main([__file__])