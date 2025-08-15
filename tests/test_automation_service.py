"""
Unit tests for the workflow automation service.

Tests workflow creation, execution, and task management.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.services.automation_service import (
    WorkflowAutomationService,
    WorkflowStatus,
    TaskType,
    TriggerType,
    AutomationTask,
    AutomationWorkflow,
    WorkflowExecution,
    WorkflowTrigger
)


class TestWorkflowAutomationService:
    """Test cases for the workflow automation service."""
    
    @pytest.fixture
    def automation_service(self):
        """Create an automation service instance for testing."""
        service = WorkflowAutomationService("test_agent")
        return service
    
    @pytest.fixture
    async def initialized_service(self, automation_service):
        """Create and initialize an automation service."""
        await automation_service.initialize()
        yield automation_service
        await automation_service.shutdown()
    
    def test_service_initialization(self, automation_service):
        """Test automation service initialization."""
        assert automation_service.agent_id == "test_agent"
        assert len(automation_service.workflows) == 0
        assert len(automation_service.executions) == 0
        assert len(automation_service.active_executions) == 0
        assert automation_service.stats["total_workflows"] == 0
        assert automation_service.stats["total_executions"] == 0
    
    @pytest.mark.asyncio
    async def test_create_simple_workflow(self, initialized_service):
        """Test creating a simple workflow."""
        tasks = [
            {
                "task_id": "task1",
                "name": "Test Task",
                "task_type": "command",
                "parameters": {"command": "echo 'Hello World'"},
                "description": "Simple echo command"
            }
        ]
        
        result = await initialized_service.create_workflow(
            name="Simple Workflow",
            description="A simple test workflow",
            tasks=tasks
        )
        
        assert result["success"] is True
        assert "workflow_id" in result
        assert result["name"] == "Simple Workflow"
        assert result["task_count"] == 1
        assert result["trigger_count"] == 0
        
        # Verify workflow was created
        workflow_id = result["workflow_id"]
        assert workflow_id in initialized_service.workflows
        
        workflow = initialized_service.workflows[workflow_id]
        assert workflow.name == "Simple Workflow"
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].name == "Test Task"
        assert workflow.tasks[0].task_type == TaskType.COMMAND
    
    @pytest.mark.asyncio
    async def test_create_workflow_with_triggers(self, initialized_service):
        """Test creating a workflow with triggers."""
        tasks = [
            {
                "name": "Scheduled Task",
                "task_type": "notification",
                "parameters": {"message": "Scheduled notification"}
            }
        ]
        
        triggers = [
            {
                "trigger_type": "scheduled",
                "schedule": "0 9 * * *",  # Daily at 9 AM
                "description": "Daily morning trigger"
            }
        ]
        
        result = await initialized_service.create_workflow(
            name="Scheduled Workflow",
            description="A workflow with scheduled trigger",
            tasks=tasks,
            triggers=triggers
        )
        
        assert result["success"] is True
        assert result["trigger_count"] == 1
        
        workflow_id = result["workflow_id"]
        workflow = initialized_service.workflows[workflow_id]
        assert len(workflow.triggers) == 1
        assert workflow.triggers[0].trigger_type == TriggerType.SCHEDULED
        assert workflow.triggers[0].schedule == "0 9 * * *"
    
    @pytest.mark.asyncio
    async def test_create_workflow_with_dependencies(self, initialized_service):
        """Test creating a workflow with task dependencies."""
        tasks = [
            {
                "task_id": "task1",
                "name": "First Task",
                "task_type": "command",
                "parameters": {"command": "echo 'First'"}
            },
            {
                "task_id": "task2",
                "name": "Second Task",
                "task_type": "command",
                "parameters": {"command": "echo 'Second'"},
                "depends_on": ["task1"]
            },
            {
                "task_id": "task3",
                "name": "Third Task",
                "task_type": "command",
                "parameters": {"command": "echo 'Third'"},
                "depends_on": ["task1", "task2"]
            }
        ]
        
        result = await initialized_service.create_workflow(
            name="Dependency Workflow",
            description="A workflow with task dependencies",
            tasks=tasks
        )
        
        assert result["success"] is True
        
        workflow_id = result["workflow_id"]
        workflow = initialized_service.workflows[workflow_id]
        
        # Verify dependencies
        task_dict = {task.task_id: task for task in workflow.tasks}
        assert len(task_dict["task1"].depends_on) == 0
        assert "task1" in task_dict["task2"].depends_on
        assert "task1" in task_dict["task3"].depends_on
        assert "task2" in task_dict["task3"].depends_on
    
    @pytest.mark.asyncio
    async def test_execute_workflow_manual(self, initialized_service):
        """Test manual workflow execution."""
        # Create a simple workflow
        tasks = [
            {
                "name": "Manual Test Task",
                "task_type": "delay",
                "parameters": {"delay_seconds": 0.1}
            }
        ]
        
        create_result = await initialized_service.create_workflow(
            name="Manual Test Workflow",
            description="Test manual execution",
            tasks=tasks
        )
        
        workflow_id = create_result["workflow_id"]
        
        # Execute the workflow
        exec_result = await initialized_service.execute_workflow(workflow_id)
        
        assert exec_result["success"] is True
        assert "execution_id" in exec_result
        assert exec_result["workflow_id"] == workflow_id
        assert exec_result["status"] == "pending"
        
        # Wait a bit for execution to start
        await asyncio.sleep(0.2)
        
        # Check execution status
        execution_id = exec_result["execution_id"]
        details_result = await initialized_service.get_execution_details(execution_id)
        
        assert details_result["success"] is True
        execution_details = details_result["execution"]
        assert execution_details["execution_id"] == execution_id
        assert execution_details["workflow_id"] == workflow_id
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_workflow(self, initialized_service):
        """Test executing a non-existent workflow."""
        result = await initialized_service.execute_workflow("nonexistent_workflow")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_get_workflow_status(self, initialized_service):
        """Test getting workflow status."""
        # Create a workflow
        tasks = [
            {
                "name": "Status Test Task",
                "task_type": "notification",
                "parameters": {"message": "Status test"}
            }
        ]
        
        create_result = await initialized_service.create_workflow(
            name="Status Test Workflow",
            description="Test status retrieval",
            tasks=tasks
        )
        
        workflow_id = create_result["workflow_id"]
        
        # Get status
        status_result = await initialized_service.get_workflow_status(workflow_id)
        
        assert status_result["success"] is True
        status_info = status_result["status"]
        assert status_info["workflow_id"] == workflow_id
        assert status_info["name"] == "Status Test Workflow"
        assert status_info["enabled"] is True
        assert status_info["task_count"] == 1
        assert status_info["execution_count"] == 0
        assert status_info["active_executions"] == 0
    
    @pytest.mark.asyncio
    async def test_get_status_nonexistent_workflow(self, initialized_service):
        """Test getting status for non-existent workflow."""
        result = await initialized_service.get_workflow_status("nonexistent_workflow")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_get_execution_details_nonexistent(self, initialized_service):
        """Test getting details for non-existent execution."""
        result = await initialized_service.get_execution_details("nonexistent_execution")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self, initialized_service):
        """Test cancelling a workflow execution."""
        # Create a workflow with a long-running task
        tasks = [
            {
                "name": "Long Task",
                "task_type": "delay",
                "parameters": {"delay_seconds": 10}  # Long delay
            }
        ]
        
        create_result = await initialized_service.create_workflow(
            name="Cancellation Test",
            description="Test execution cancellation",
            tasks=tasks
        )
        
        workflow_id = create_result["workflow_id"]
        
        # Start execution
        exec_result = await initialized_service.execute_workflow(workflow_id)
        execution_id = exec_result["execution_id"]
        
        # Wait a bit for execution to start
        await asyncio.sleep(0.1)
        
        # Cancel execution
        cancel_result = await initialized_service.cancel_execution(execution_id)
        
        assert cancel_result["success"] is True
        assert cancel_result["execution_id"] == execution_id
        assert cancel_result["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_execution(self, initialized_service):
        """Test cancelling a non-existent execution."""
        result = await initialized_service.cancel_execution("nonexistent_execution")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_command_task_execution(self, automation_service):
        """Test command task execution."""
        task = AutomationTask(
            task_id="test_command",
            name="Test Command",
            task_type=TaskType.COMMAND,
            parameters={"command": "echo 'test output'"}
        )
        
        execution = WorkflowExecution(
            execution_id="test_exec",
            workflow_id="test_workflow"
        )
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            # Mock successful command execution
            mock_process = Mock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = asyncio.coroutine(
                lambda: (b'test output\n', b'')
            )()
            mock_subprocess.return_value = mock_process
            
            result = await automation_service._execute_command_task(task, execution)
            
            assert result["success"] is True
            assert result["return_code"] == 0
            assert "test output" in result["stdout"]
            assert result["command"] == "echo 'test output'"
    
    @pytest.mark.asyncio
    async def test_command_task_failure(self, automation_service):
        """Test command task failure handling."""
        task = AutomationTask(
            task_id="test_command_fail",
            name="Test Command Fail",
            task_type=TaskType.COMMAND,
            parameters={"command": "false"}  # Command that always fails
        )
        
        execution = WorkflowExecution(
            execution_id="test_exec",
            workflow_id="test_workflow"
        )
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            # Mock failed command execution
            mock_process = Mock()
            mock_process.returncode = 1
            mock_process.communicate.return_value = asyncio.coroutine(
                lambda: (b'', b'command failed\n')
            )()
            mock_subprocess.return_value = mock_process
            
            result = await automation_service._execute_command_task(task, execution)
            
            assert result["success"] is False
            assert result["return_code"] == 1
            assert "command failed" in result["stderr"]
    
    @pytest.mark.asyncio
    async def test_delay_task_execution(self, automation_service):
        """Test delay task execution."""
        task = AutomationTask(
            task_id="test_delay",
            name="Test Delay",
            task_type=TaskType.DELAY,
            parameters={"delay_seconds": 0.1}
        )
        
        execution = WorkflowExecution(
            execution_id="test_exec",
            workflow_id="test_workflow"
        )
        
        start_time = datetime.now()
        result = await automation_service._execute_delay_task(task, execution)
        end_time = datetime.now()
        
        assert result["success"] is True
        assert "Delayed for 0.1 seconds" in result["message"]
        
        # Verify actual delay occurred
        duration = (end_time - start_time).total_seconds()
        assert duration >= 0.1
    
    @pytest.mark.asyncio
    async def test_notification_task_execution(self, automation_service):
        """Test notification task execution."""
        task = AutomationTask(
            task_id="test_notification",
            name="Test Notification",
            task_type=TaskType.NOTIFICATION,
            parameters={
                "message": "Test notification message",
                "recipient": "test@example.com"
            }
        )
        
        execution = WorkflowExecution(
            execution_id="test_exec",
            workflow_id="test_workflow"
        )
        
        result = await automation_service._execute_notification_task(task, execution)
        
        assert result["success"] is True
        assert "Notification sent" in result["message"]
        
        # Verify notification was logged
        assert len(execution.logs) > 0
        assert "NOTIFICATION" in execution.logs[-1]
        assert "Test notification message" in execution.logs[-1]
    
    @pytest.mark.asyncio
    async def test_conditional_task_execution(self, automation_service):
        """Test conditional task execution."""
        task = AutomationTask(
            task_id="test_conditional",
            name="Test Conditional",
            task_type=TaskType.CONDITIONAL,
            parameters={"condition": "true"}
        )
        
        execution = WorkflowExecution(
            execution_id="test_exec",
            workflow_id="test_workflow"
        )
        
        result = await automation_service._execute_conditional_task(task, execution)
        
        assert result["success"] is True
        assert result["condition_result"] is True
        assert result["output"] is True
    
    @pytest.mark.asyncio
    async def test_file_operation_task_write(self, automation_service, tmp_path):
        """Test file operation task for writing."""
        test_file = tmp_path / "test_file.txt"
        
        task = AutomationTask(
            task_id="test_file_write",
            name="Test File Write",
            task_type=TaskType.FILE_OPERATION,
            parameters={
                "operation": "write",
                "file_path": str(test_file),
                "content": "Test file content"
            }
        )
        
        execution = WorkflowExecution(
            execution_id="test_exec",
            workflow_id="test_workflow"
        )
        
        result = await automation_service._execute_file_operation_task(task, execution)
        
        assert result["success"] is True
        assert "File written" in result["message"]
        assert test_file.exists()
        assert test_file.read_text() == "Test file content"
    
    @pytest.mark.asyncio
    async def test_file_operation_task_read(self, automation_service, tmp_path):
        """Test file operation task for reading."""
        test_file = tmp_path / "test_read_file.txt"
        test_file.write_text("Content to read")
        
        task = AutomationTask(
            task_id="test_file_read",
            name="Test File Read",
            task_type=TaskType.FILE_OPERATION,
            parameters={
                "operation": "read",
                "file_path": str(test_file)
            }
        )
        
        execution = WorkflowExecution(
            execution_id="test_exec",
            workflow_id="test_workflow"
        )
        
        result = await automation_service._execute_file_operation_task(task, execution)
        
        assert result["success"] is True
        assert result["output"] == "Content to read"
    
    @pytest.mark.asyncio
    async def test_variable_substitution(self, automation_service):
        """Test variable substitution in tasks."""
        variables = {
            "name": "John",
            "age": "30",
            "city": "New York"
        }
        
        text = "Hello $name, you are $age years old and live in $city"
        result = automation_service._substitute_variables(text, variables)
        
        expected = "Hello John, you are 30 years old and live in New York"
        assert result == expected
    
    def test_condition_evaluation(self, automation_service):
        """Test condition evaluation."""
        variables = {"x": "10", "y": "20", "status": "active"}
        
        # Test equality
        assert automation_service._evaluate_condition("$x == 10", variables) is True
        assert automation_service._evaluate_condition("$x == 20", variables) is False
        
        # Test inequality
        assert automation_service._evaluate_condition("$x != 20", variables) is True
        assert automation_service._evaluate_condition("$x != 10", variables) is False
        
        # Test boolean values
        assert automation_service._evaluate_condition("true", variables) is True
        assert automation_service._evaluate_condition("false", variables) is False
        assert automation_service._evaluate_condition("yes", variables) is True
        assert automation_service._evaluate_condition("no", variables) is False
    
    def test_task_dependency_graph(self, automation_service):
        """Test task dependency graph building."""
        tasks = [
            AutomationTask(task_id="task1", name="Task 1", task_type=TaskType.COMMAND),
            AutomationTask(task_id="task2", name="Task 2", task_type=TaskType.COMMAND, depends_on=["task1"]),
            AutomationTask(task_id="task3", name="Task 3", task_type=TaskType.COMMAND, depends_on=["task1", "task2"])
        ]
        
        graph = automation_service._build_task_dependency_graph(tasks)
        
        assert graph["task1"] == []
        assert graph["task2"] == ["task1"]
        assert graph["task3"] == ["task1", "task2"]
    
    def test_workflow_duration_estimation(self, automation_service):
        """Test workflow duration estimation."""
        workflow = AutomationWorkflow(
            workflow_id="test_workflow",
            name="Test Workflow",
            description="Test",
            tasks=[
                AutomationTask(task_id="task1", name="Task 1", task_type=TaskType.COMMAND, timeout_seconds=60),
                AutomationTask(task_id="task2", name="Task 2", task_type=TaskType.COMMAND, timeout_seconds=120)
            ]
        )
        
        estimated_duration = automation_service._estimate_workflow_duration(workflow)
        
        # Should be 50% of total timeout (60 + 120) * 0.5 = 90
        assert estimated_duration == 90.0
    
    def test_automation_task_dataclass(self):
        """Test AutomationTask dataclass functionality."""
        task = AutomationTask(
            task_id="test_task",
            name="Test Task",
            task_type=TaskType.COMMAND,
            parameters={"command": "echo test"},
            timeout_seconds=300,
            retry_count=2,
            depends_on=["other_task"],
            condition="$status == active",
            description="Test task description",
            tags=["test", "command"]
        )
        
        assert task.task_id == "test_task"
        assert task.name == "Test Task"
        assert task.task_type == TaskType.COMMAND
        assert task.parameters["command"] == "echo test"
        assert task.timeout_seconds == 300
        assert task.retry_count == 2
        assert "other_task" in task.depends_on
        assert task.condition == "$status == active"
        assert task.run_on_failure is False
        assert task.continue_on_error is False
        assert task.capture_output is True
    
    def test_workflow_execution_dataclass(self):
        """Test WorkflowExecution dataclass functionality."""
        execution = WorkflowExecution(
            execution_id="test_exec",
            workflow_id="test_workflow"
        )
        
        assert execution.execution_id == "test_exec"
        assert execution.workflow_id == "test_workflow"
        assert execution.status == WorkflowStatus.PENDING
        assert execution.started_at is None
        assert execution.completed_at is None
        assert len(execution.task_results) == 0
        assert len(execution.completed_tasks) == 0
        assert len(execution.failed_tasks) == 0
        assert len(execution.logs) == 0
        
        # Test log addition
        execution.add_log("Test log message")
        assert len(execution.logs) == 1
        assert "Test log message" in execution.logs[0]
        
        # Test duration calculation
        assert execution.get_duration_seconds() is None
        
        execution.started_at = datetime.now()
        duration = execution.get_duration_seconds()
        assert duration is not None
        assert duration >= 0
    
    def test_workflow_status_enum(self):
        """Test WorkflowStatus enum values."""
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELLED.value == "cancelled"
        assert WorkflowStatus.PAUSED.value == "paused"
    
    def test_task_type_enum(self):
        """Test TaskType enum values."""
        assert TaskType.COMMAND.value == "command"
        assert TaskType.HTTP_REQUEST.value == "http_request"
        assert TaskType.FILE_OPERATION.value == "file_operation"
        assert TaskType.DATA_PROCESSING.value == "data_processing"
        assert TaskType.NOTIFICATION.value == "notification"
        assert TaskType.CONDITIONAL.value == "conditional"
        assert TaskType.LOOP.value == "loop"
        assert TaskType.DELAY.value == "delay"
        assert TaskType.CUSTOM_FUNCTION.value == "custom_function"
    
    def test_trigger_type_enum(self):
        """Test TriggerType enum values."""
        assert TriggerType.MANUAL.value == "manual"
        assert TriggerType.SCHEDULED.value == "scheduled"
        assert TriggerType.EVENT_DRIVEN.value == "event_driven"
        assert TriggerType.FILE_WATCH.value == "file_watch"
        assert TriggerType.API_WEBHOOK.value == "api_webhook"
        assert TriggerType.CONDITION_MET.value == "condition_met"
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, initialized_service):
        """Test that statistics are properly tracked."""
        initial_stats = initialized_service.stats.copy()
        
        # Create a workflow
        tasks = [
            {
                "name": "Stats Task",
                "task_type": "notification",
                "parameters": {"message": "Stats test"}
            }
        ]
        
        await initialized_service.create_workflow(
            name="Stats Workflow",
            description="Test statistics",
            tasks=tasks
        )
        
        # Verify statistics updated
        assert initialized_service.stats["total_workflows"] == initial_stats["total_workflows"] + 1
        assert initialized_service.stats["tasks_by_type"]["notification"] == initial_stats["tasks_by_type"]["notification"] + 1
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_limit(self, initialized_service):
        """Test concurrent execution limits."""
        # Create a workflow
        tasks = [
            {
                "name": "Concurrent Test",
                "task_type": "delay",
                "parameters": {"delay_seconds": 1}
            }
        ]
        
        create_result = await initialized_service.create_workflow(
            name="Concurrent Test Workflow",
            description="Test concurrent limits",
            tasks=tasks
        )
        
        workflow_id = create_result["workflow_id"]
        workflow = initialized_service.workflows[workflow_id]
        
        # Set low concurrent execution limit
        workflow.max_concurrent_executions = 1
        
        # Start first execution
        exec1_result = await initialized_service.execute_workflow(workflow_id)
        assert exec1_result["success"] is True
        
        # Try to start second execution (should be rejected)
        exec2_result = await initialized_service.execute_workflow(workflow_id)
        assert exec2_result["success"] is False
        assert "concurrent" in exec2_result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__])