"""
Tests for the human command routing system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from autonomous_ai_ecosystem.oversight.command_router import (
    HumanCommandRouter,
    HumanCommand,
    ExpertAgent,
    CommandResponse,
    CommandType,
    CommandStatus,
    CommandPriority
)


class TestExpertAgent:
    """Test the ExpertAgent class."""
    
    def test_expert_agent_creation(self):
        """Test creating an expert agent."""
        agent = ExpertAgent(
            agent_id="agent_1",
            name="Test Expert",
            expertise_domains=["programming", "problem_solving"],
            status_score=0.85
        )
        
        assert agent.agent_id == "agent_1"
        assert agent.name == "Test Expert"
        assert "programming" in agent.expertise_domains
        assert agent.status_score == 0.85
        assert agent.availability is True
        assert agent.success_rate == 1.0
        assert agent.current_workload == 0
    
    def test_availability_check(self):
        """Test agent availability checking."""
        agent = ExpertAgent(
            agent_id="agent_1",
            name="Test Expert",
            expertise_domains=["programming"],
            status_score=0.8,
            max_concurrent_commands=2
        )
        
        # Should be available initially
        assert agent.is_available() is True
        
        # Add workload
        agent.current_workload = 1
        assert agent.is_available() is True
        
        # At capacity
        agent.current_workload = 2
        assert agent.is_available() is False
        
        # Unavailable
        agent.current_workload = 0
        agent.availability = False
        assert agent.is_available() is False
    
    def test_expertise_score(self):
        """Test expertise score calculation."""
        agent = ExpertAgent(
            agent_id="agent_1",
            name="Test Expert",
            expertise_domains=["programming", "research"],
            status_score=0.8,
            success_rate=0.9
        )
        
        # Domain expertise
        programming_score = agent.get_expertise_score("programming")
        assert programming_score == 0.8 * 0.9  # status_score * success_rate
        
        # Non-expertise domain
        creative_score = agent.get_expertise_score("creative")
        assert creative_score == 0.0
    
    def test_overall_score(self):
        """Test overall score calculation."""
        agent = ExpertAgent(
            agent_id="agent_1",
            name="Test Expert",
            expertise_domains=["programming"],
            status_score=0.8,
            success_rate=0.9,
            satisfaction_rating=4.0,
            max_concurrent_commands=3,
            current_workload=1
        )
        
        overall_score = agent.get_overall_score()
        
        # Should be positive and account for various factors
        assert overall_score > 0
        assert overall_score < 2.0  # Reasonable upper bound
        
        # Higher workload should reduce score
        agent.current_workload = 2
        higher_workload_score = agent.get_overall_score()
        assert higher_workload_score < overall_score


class TestHumanCommand:
    """Test the HumanCommand class."""
    
    def test_command_creation(self):
        """Test creating a human command."""
        command = HumanCommand(
            command_id="cmd_1",
            human_id="human_1",
            command_type=CommandType.TASK,
            priority=CommandPriority.HIGH,
            title="Test Task",
            description="A test task for the system"
        )
        
        assert command.command_id == "cmd_1"
        assert command.human_id == "human_1"
        assert command.command_type == CommandType.TASK
        assert command.priority == CommandPriority.HIGH
        assert command.title == "Test Task"
        assert command.status == CommandStatus.RECEIVED
        assert command.progress_percentage == 0.0
    
    def test_status_updates(self):
        """Test adding status updates."""
        command = HumanCommand(
            command_id="cmd_1",
            human_id="human_1",
            command_type=CommandType.QUERY,
            priority=CommandPriority.NORMAL,
            title="Test Query",
            description="Test query"
        )
        
        command.add_status_update("Processing started")
        command.add_status_update("Analysis complete")
        
        assert len(command.status_updates) == 2
        assert "Processing started" in command.status_updates[0]
        assert "Analysis complete" in command.status_updates[1]
        
        # Test status update limit
        for i in range(55):
            command.add_status_update(f"Update {i}")
        
        assert len(command.status_updates) == 50  # Should be limited
    
    def test_duration_calculation(self):
        """Test command duration calculation."""
        command = HumanCommand(
            command_id="cmd_1",
            human_id="human_1",
            command_type=CommandType.TASK,
            priority=CommandPriority.NORMAL,
            title="Test Task",
            description="Test task"
        )
        
        # No start time
        assert command.get_duration() == 0.0
        
        # With start time
        command.started_at = datetime.now() - timedelta(hours=2)
        duration = command.get_duration()
        assert 1.9 < duration < 2.1  # Approximately 2 hours
        
        # With completion time
        command.completed_at = datetime.now() - timedelta(hours=1)
        duration = command.get_duration()
        assert 0.9 < duration < 1.1  # Approximately 1 hour
    
    def test_overdue_check(self):
        """Test overdue checking."""
        command = HumanCommand(
            command_id="cmd_1",
            human_id="human_1",
            command_type=CommandType.TASK,
            priority=CommandPriority.NORMAL,
            title="Test Task",
            description="Test task",
            deadline=datetime.now() - timedelta(hours=1)  # Past deadline
        )
        
        assert command.is_overdue() is True
        
        # Future deadline
        command.deadline = datetime.now() + timedelta(hours=1)
        assert command.is_overdue() is False
        
        # Completed command should not be overdue
        command.deadline = datetime.now() - timedelta(hours=1)
        command.status = CommandStatus.COMPLETED
        assert command.is_overdue() is False


class TestCommandResponse:
    """Test the CommandResponse class."""
    
    def test_response_creation(self):
        """Test creating a command response."""
        response = CommandResponse(
            response_id="resp_1",
            command_id="cmd_1",
            agent_id="agent_1",
            response_type="status_update",
            content="Work in progress"
        )
        
        assert response.response_id == "resp_1"
        assert response.command_id == "cmd_1"
        assert response.agent_id == "agent_1"
        assert response.response_type == "status_update"
        assert response.content == "Work in progress"
        assert response.confidence_level == 1.0
        assert response.requires_human_review is False


class TestHumanCommandRouter:
    """Test the HumanCommandRouter class."""
    
    @pytest.fixture
    async def command_router(self):
        """Create a test command router."""
        router = HumanCommandRouter("test_router")
        await router.initialize()
        return router
    
    @pytest.mark.asyncio
    async def test_router_initialization(self):
        """Test command router initialization."""
        router = HumanCommandRouter("test_router")
        await router.initialize()
        
        assert len(router.commands) == 0
        assert len(router.expert_agents) > 0  # Should have default experts
        assert router.stats["total_commands"] == 0
        
        await router.shutdown()
    
    @pytest.mark.asyncio
    async def test_register_expert_agent(self, command_router):
        """Test registering an expert agent."""
        result = command_router.register_expert_agent(
            agent_id="test_expert",
            name="Test Expert Agent",
            expertise_domains=["testing", "quality_assurance"],
            status_score=0.9
        )
        
        assert result["success"] is True
        assert result["agent_id"] == "test_expert"
        assert "testing" in result["expertise_domains"]
        
        # Check agent was stored
        assert "test_expert" in command_router.expert_agents
        agent = command_router.expert_agents["test_expert"]
        assert agent.name == "Test Expert Agent"
        assert agent.status_score == 0.9
    
    @pytest.mark.asyncio
    async def test_submit_human_command(self, command_router):
        """Test submitting a human command."""
        result = await command_router.submit_human_command(
            human_id="human_1",
            command_type=CommandType.TASK,
            title="Test Task",
            description="Please complete this test task",
            priority=CommandPriority.HIGH,
            requirements=["requirement_1", "requirement_2"]
        )
        
        assert result["success"] is True
        assert "command_id" in result
        assert result["status"] == CommandStatus.RECEIVED.value
        assert "expert_domain" in result
        assert "estimated_response_time" in result
        
        # Check command was stored
        command_id = result["command_id"]
        assert command_id in command_router.commands
        
        command = command_router.commands[command_id]
        assert command.title == "Test Task"
        assert command.human_id == "human_1"
        assert command.priority == CommandPriority.HIGH
        assert len(command.requirements) == 2
    
    @pytest.mark.asyncio
    async def test_submit_emergency_command(self, command_router):
        """Test submitting an emergency command."""
        result = await command_router.submit_human_command(
            human_id="human_1",
            command_type=CommandType.EMERGENCY,
            title="System Emergency",
            description="Critical system issue needs immediate attention",
            priority=CommandPriority.EMERGENCY
        )
        
        assert result["success"] is True
        
        command_id = result["command_id"]
        command = command_router.commands[command_id]
        
        # Emergency commands should have short deadlines
        assert command.deadline is not None
        time_to_deadline = (command.deadline - command.created_at).total_seconds() / 3600.0
        assert time_to_deadline <= 1.0  # Should be 1 hour or less
    
    @pytest.mark.asyncio
    async def test_get_command_status(self, command_router):
        """Test getting command status."""
        # Submit a command first
        submit_result = await command_router.submit_human_command(
            human_id="human_1",
            command_type=CommandType.QUERY,
            title="Test Query",
            description="What is the status of the system?"
        )
        command_id = submit_result["command_id"]
        
        # Wait a moment for processing
        await asyncio.sleep(0.1)
        
        # Get status
        status = await command_router.get_command_status(command_id)
        
        assert "command_id" in status
        assert status["command_id"] == command_id
        assert status["title"] == "Test Query"
        assert "status" in status
        assert "progress_percentage" in status
        assert "created_at" in status
        assert "expert_domain" in status
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_command_status(self, command_router):
        """Test getting status of nonexistent command."""
        status = await command_router.get_command_status("nonexistent")
        
        assert "error" in status
    
    @pytest.mark.asyncio
    async def test_submit_command_response(self, command_router):
        """Test submitting a command response."""
        # Submit a command and wait for assignment
        submit_result = await command_router.submit_human_command(
            human_id="human_1",
            command_type=CommandType.TASK,
            title="Test Task",
            description="Complete this task"
        )
        command_id = submit_result["command_id"]
        
        # Wait for processing and assignment
        await asyncio.sleep(0.2)
        
        command = command_router.commands[command_id]
        if command.assigned_agent_id:
            # Submit response
            response_result = await command_router.submit_command_response(
                agent_id=command.assigned_agent_id,
                command_id=command_id,
                response_type="status_update",
                content="Working on the task",
                confidence_level=0.8
            )
            
            assert response_result["success"] is True
            assert "response_id" in response_result
            
            # Check response was stored
            assert command_id in command_router.command_responses
            responses = command_router.command_responses[command_id]
            assert len(responses) >= 1
            
            latest_response = responses[-1]
            assert latest_response.content == "Working on the task"
            assert latest_response.confidence_level == 0.8
    
    @pytest.mark.asyncio
    async def test_submit_response_unauthorized(self, command_router):
        """Test submitting response from unauthorized agent."""
        # Submit a command
        submit_result = await command_router.submit_human_command(
            human_id="human_1",
            command_type=CommandType.TASK,
            title="Test Task",
            description="Complete this task"
        )
        command_id = submit_result["command_id"]
        
        # Try to submit response from unauthorized agent
        response_result = await command_router.submit_command_response(
            agent_id="unauthorized_agent",
            command_id=command_id,
            response_type="status_update",
            content="Unauthorized response"
        )
        
        assert response_result["success"] is False
        assert "not assigned" in response_result["error"]
    
    @pytest.mark.asyncio
    async def test_submit_human_feedback(self, command_router):
        """Test submitting human feedback."""
        # Submit and complete a command
        submit_result = await command_router.submit_human_command(
            human_id="human_1",
            command_type=CommandType.QUERY,
            title="Test Query",
            description="Simple query"
        )
        command_id = submit_result["command_id"]
        
        # Wait for assignment and simulate completion
        await asyncio.sleep(0.2)
        command = command_router.commands[command_id]
        command.status = CommandStatus.COMPLETED
        
        # Submit feedback
        feedback_result = await command_router.submit_human_feedback(
            human_id="human_1",
            command_id=command_id,
            satisfaction_rating=4,
            feedback="Good response, very helpful"
        )
        
        assert feedback_result["success"] is True
        assert feedback_result["satisfaction_rating"] == 4
        
        # Check feedback was stored
        assert command.human_satisfaction == 4
        assert command.human_feedback == "Good response, very helpful"
    
    @pytest.mark.asyncio
    async def test_submit_feedback_unauthorized(self, command_router):
        """Test submitting feedback from unauthorized human."""
        # Submit a command
        submit_result = await command_router.submit_human_command(
            human_id="human_1",
            command_type=CommandType.QUERY,
            title="Test Query",
            description="Simple query"
        )
        command_id = submit_result["command_id"]
        
        # Try to submit feedback from different human
        feedback_result = await command_router.submit_human_feedback(
            human_id="different_human",
            command_id=command_id,
            satisfaction_rating=3,
            feedback="Unauthorized feedback"
        )
        
        assert feedback_result["success"] is False
        assert "Not authorized" in feedback_result["error"]
    
    def test_get_expert_agents(self, command_router):
        """Test getting expert agents."""
        # This test needs to be run after router initialization
        asyncio.run(self._test_get_expert_agents_async(command_router))
    
    async def _test_get_expert_agents_async(self, command_router):
        """Async helper for expert agents test."""
        # Get all experts
        all_experts = command_router.get_expert_agents()
        
        assert len(all_experts) > 0
        for expert in all_experts:
            assert "agent_id" in expert
            assert "name" in expert
            assert "expertise_domains" in expert
            assert "status_score" in expert
            assert "is_available" in expert
        
        # Get experts by domain
        programming_experts = command_router.get_expert_agents(domain="programming")
        
        # Should have at least one programming expert
        assert len(programming_experts) > 0
        for expert in programming_experts:
            assert "programming" in expert["expertise_domains"]
    
    def test_get_human_commands(self, command_router):
        """Test getting human commands."""
        asyncio.run(self._test_get_human_commands_async(command_router))
    
    async def _test_get_human_commands_async(self, command_router):
        """Async helper for human commands test."""
        # Submit some commands
        await command_router.submit_human_command(
            human_id="human_1",
            command_type=CommandType.TASK,
            title="Task 1",
            description="First task"
        )
        
        await command_router.submit_human_command(
            human_id="human_2",
            command_type=CommandType.QUERY,
            title="Query 1",
            description="First query"
        )
        
        # Get all commands
        all_commands = command_router.get_human_commands()
        assert len(all_commands) >= 2
        
        # Get commands by human
        human1_commands = command_router.get_human_commands(human_id="human_1")
        assert len(human1_commands) >= 1
        assert human1_commands[0]["title"] == "Task 1"
    
    def test_get_command_statistics(self, command_router):
        """Test getting command statistics."""
        asyncio.run(self._test_get_command_statistics_async(command_router))
    
    async def _test_get_command_statistics_async(self, command_router):
        """Async helper for command statistics test."""
        # Submit some commands to generate statistics
        await command_router.submit_human_command(
            human_id="human_1",
            command_type=CommandType.TASK,
            title="Task 1",
            description="First task"
        )
        
        await command_router.submit_human_command(
            human_id="human_2",
            command_type=CommandType.QUERY,
            title="Query 1",
            description="First query"
        )
        
        # Get statistics
        stats = command_router.get_command_statistics()
        
        assert "total_commands" in stats
        assert "completed_commands" in stats
        assert "active_commands" in stats
        assert "success_rate_percent" in stats
        assert "commands_by_type" in stats
        assert "commands_by_priority" in stats
        assert "total_expert_agents" in stats
        assert "available_experts" in stats
        
        assert stats["total_commands"] >= 2
        assert stats["total_expert_agents"] > 0


if __name__ == "__main__":
    pytest.main([__file__])