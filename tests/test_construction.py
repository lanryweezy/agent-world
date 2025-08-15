"""
Tests for the collaborative construction system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.world.construction import (
    CollaborativeConstruction,
    ConstructionProject,
    ProjectType,
    ProjectStatus,
    ContributionType,
    ConflictType,
    ResourceRequirement,
    ProjectContribution,
    ConstructionConflict
)
from autonomous_ai_ecosystem.world.virtual_world import (
    VirtualWorld,
    ResourceType,
    Coordinates
)


class TestResourceRequirement:
    """Test the ResourceRequirement class."""
    
    def test_resource_requirement_creation(self):
        """Test creating a resource requirement."""
        req = ResourceRequirement(
            resource_type=ResourceType.COMPUTATIONAL_POWER,
            quantity_needed=100.0,
            quality_threshold=0.8
        )
        
        assert req.resource_type == ResourceType.COMPUTATIONAL_POWER
        assert req.quantity_needed == 100.0
        assert req.quality_threshold == 0.8
        assert req.quantity_contributed == 0.0
        assert not req.is_fulfilled
        assert req.completion_percentage == 0.0
    
    def test_resource_requirement_fulfillment(self):
        """Test resource requirement fulfillment tracking."""
        req = ResourceRequirement(
            resource_type=ResourceType.COMPUTATIONAL_POWER,
            quantity_needed=100.0
        )
        
        # Add partial contribution
        req.quantity_contributed = 50.0
        req.contributors["agent_1"] = 50.0
        
        assert not req.is_fulfilled
        assert req.completion_percentage == 50.0
        
        # Complete the requirement
        req.quantity_contributed = 100.0
        req.contributors["agent_2"] = 50.0
        
        assert req.is_fulfilled
        assert req.completion_percentage == 100.0


class TestConstructionProject:
    """Test the ConstructionProject class."""
    
    def test_project_creation(self):
        """Test creating a construction project."""
        project = ConstructionProject(
            project_id="test_project",
            name="Test Project",
            description="A test construction project",
            project_type=ProjectType.NEW_LOCATION,
            initiator_id="agent_1"
        )
        
        assert project.project_id == "test_project"
        assert project.name == "Test Project"
        assert project.project_type == ProjectType.NEW_LOCATION
        assert project.status == ProjectStatus.PROPOSED
        assert project.progress_percentage == 0.0
        assert len(project.participants) == 0
    
    def test_project_voting(self):
        """Test project voting mechanics."""
        project = ConstructionProject(
            project_id="test_project",
            name="Test Project",
            description="A test project",
            project_type=ProjectType.NEW_LOCATION,
            initiator_id="agent_1"
        )
        
        # Add votes
        project.votes["agent_1"] = True
        project.votes["agent_2"] = True
        project.votes["agent_3"] = False
        
        assert project.get_approval_percentage() == 66.67  # 2/3 * 100
        assert project.is_approved()  # Default threshold is 60%
    
    def test_resource_progress_calculation(self):
        """Test resource progress calculation."""
        project = ConstructionProject(
            project_id="test_project",
            name="Test Project",
            description="A test project",
            project_type=ProjectType.NEW_LOCATION,
            initiator_id="agent_1"
        )
        
        # Add resource requirements
        req1 = ResourceRequirement(ResourceType.COMPUTATIONAL_POWER, 100.0)
        req1.quantity_contributed = 50.0
        
        req2 = ResourceRequirement(ResourceType.BUILDING_MATERIALS, 200.0)
        req2.quantity_contributed = 100.0
        
        project.resource_requirements["req1"] = req1
        project.resource_requirements["req2"] = req2
        
        # Should be (50% + 50%) / 2 = 50%
        assert project.get_total_resource_progress() == 50.0


class TestCollaborativeConstruction:
    """Test the CollaborativeConstruction class."""
    
    @pytest.fixture
    async def construction_system(self):
        """Create a test construction system."""
        # Create mock virtual world
        virtual_world = Mock(spec=VirtualWorld)
        virtual_world.agent_positions = {
            "agent_1": Mock(current_location_id="location_1"),
            "agent_2": Mock(current_location_id="location_2")
        }
        virtual_world.locations = {
            "location_1": Mock(
                coordinates=Coordinates(0, 0, 0),
                resources={"res1": Mock(resource_type=ResourceType.COMPUTATIONAL_POWER, quantity=100.0)}
            ),
            "location_2": Mock(
                coordinates=Coordinates(10, 10, 0),
                resources={}
            )
        }
        virtual_world.world_stats = {"total_locations": 2}
        
        construction = CollaborativeConstruction("test_agent", virtual_world)
        await construction.initialize()
        return construction
    
    @pytest.mark.asyncio
    async def test_propose_project(self, construction_system):
        """Test proposing a new project."""
        result = await construction_system.propose_project(
            initiator_id="agent_1",
            name="Test Building",
            description="A test building project",
            project_type=ProjectType.NEW_LOCATION,
            resource_requirements={
                ResourceType.BUILDING_MATERIALS: (100.0, 0.8)
            }
        )
        
        assert result["success"] is True
        assert "project_id" in result
        assert result["status"] == ProjectStatus.PROPOSED.value
        
        # Check project was stored
        project_id = result["project_id"]
        assert project_id in construction_system.projects
        
        project = construction_system.projects[project_id]
        assert project.name == "Test Building"
        assert project.initiator_id == "agent_1"
        assert "agent_1" in project.participants
    
    @pytest.mark.asyncio
    async def test_vote_on_project(self, construction_system):
        """Test voting on a project."""
        # First propose a project
        result = await construction_system.propose_project(
            initiator_id="agent_1",
            name="Test Building",
            description="A test building project",
            project_type=ProjectType.NEW_LOCATION
        )
        project_id = result["project_id"]
        
        # Vote on the project
        vote_result = await construction_system.vote_on_project("agent_2", project_id, True)
        
        assert vote_result["success"] is True
        assert vote_result["vote_recorded"] is True
        assert vote_result["current_approval"] > 0
        
        # Check project state
        project = construction_system.projects[project_id]
        assert "agent_2" in project.votes
        assert project.votes["agent_2"] is True
        assert "agent_2" in project.participants
    
    @pytest.mark.asyncio
    async def test_vote_on_nonexistent_project(self, construction_system):
        """Test voting on a project that doesn't exist."""
        result = await construction_system.vote_on_project("agent_1", "nonexistent", True)
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_contribute_to_project(self, construction_system):
        """Test contributing to a project."""
        # Propose and approve a project
        result = await construction_system.propose_project(
            initiator_id="agent_1",
            name="Test Building",
            description="A test building project",
            project_type=ProjectType.NEW_LOCATION,
            resource_requirements={
                ResourceType.COMPUTATIONAL_POWER: (50.0, 0.5)
            }
        )
        project_id = result["project_id"]
        
        # Approve the project
        project = construction_system.projects[project_id]
        project.status = ProjectStatus.APPROVED
        
        # Make a contribution
        contrib_result = await construction_system.contribute_to_project(
            agent_id="agent_1",
            project_id=project_id,
            contribution_type=ContributionType.RESOURCES,
            value=25.0,
            description="Contributing computational power",
            resource_type=ResourceType.COMPUTATIONAL_POWER
        )
        
        assert contrib_result["success"] is True
        assert "contribution_id" in contrib_result
        assert contrib_result["project_progress"] >= 0
        
        # Check contribution was recorded
        assert len(project.contributions) == 1
        contribution = project.contributions[0]
        assert contribution.agent_id == "agent_1"
        assert contribution.contribution_type == ContributionType.RESOURCES
        assert contribution.value == 25.0
    
    @pytest.mark.asyncio
    async def test_start_project(self, construction_system):
        """Test starting a project."""
        # Create an approved project with sufficient resources
        result = await construction_system.propose_project(
            initiator_id="agent_1",
            name="Test Building",
            description="A test building project",
            project_type=ProjectType.NEW_LOCATION
        )
        project_id = result["project_id"]
        
        project = construction_system.projects[project_id]
        project.status = ProjectStatus.APPROVED
        project.progress_percentage = 85.0  # Simulate sufficient progress
        
        # Mock resource progress
        with patch.object(project, 'get_total_resource_progress', return_value=85.0):
            start_result = await construction_system.start_project(project_id)
        
        assert start_result["success"] is True
        assert start_result["status"] == ProjectStatus.IN_PROGRESS.value
        assert "project_manager" in start_result
        assert "deadline" in start_result
        
        # Check project state
        assert project.status == ProjectStatus.IN_PROGRESS
        assert project.started_at is not None
        assert project.deadline is not None
    
    @pytest.mark.asyncio
    async def test_start_project_insufficient_resources(self, construction_system):
        """Test starting a project with insufficient resources."""
        result = await construction_system.propose_project(
            initiator_id="agent_1",
            name="Test Building",
            description="A test building project",
            project_type=ProjectType.NEW_LOCATION
        )
        project_id = result["project_id"]
        
        project = construction_system.projects[project_id]
        project.status = ProjectStatus.APPROVED
        
        # Mock insufficient resource progress
        with patch.object(project, 'get_total_resource_progress', return_value=50.0):
            start_result = await construction_system.start_project(project_id)
        
        assert start_result["success"] is False
        assert "Insufficient resources" in start_result["error"]
    
    @pytest.mark.asyncio
    async def test_complete_project(self, construction_system):
        """Test completing a project."""
        # Create a project in progress
        result = await construction_system.propose_project(
            initiator_id="agent_1",
            name="Test Building",
            description="A test building project",
            project_type=ProjectType.NEW_LOCATION
        )
        project_id = result["project_id"]
        
        project = construction_system.projects[project_id]
        project.status = ProjectStatus.IN_PROGRESS
        project.started_at = datetime.now() - timedelta(hours=2)
        
        # Mock the project effects application
        with patch.object(construction_system, '_apply_project_effects', new_callable=AsyncMock) as mock_effects:
            mock_effects.return_value = {"location_id": "new_location"}
            
            complete_result = await construction_system.complete_project(project_id)
        
        assert complete_result["success"] is True
        assert complete_result["status"] == ProjectStatus.COMPLETED.value
        assert complete_result["duration_hours"] > 0
        assert "result" in complete_result
        
        # Check project state
        assert project.status == ProjectStatus.COMPLETED
        assert project.completed_at is not None
        assert project.progress_percentage == 100.0
    
    @pytest.mark.asyncio
    async def test_report_conflict(self, construction_system):
        """Test reporting a conflict."""
        # Create a project with participants
        result = await construction_system.propose_project(
            initiator_id="agent_1",
            name="Test Building",
            description="A test building project",
            project_type=ProjectType.NEW_LOCATION
        )
        project_id = result["project_id"]
        
        project = construction_system.projects[project_id]
        project.participants.add("agent_2")
        
        # Report a conflict
        conflict_result = await construction_system.report_conflict(
            reporter_id="agent_1",
            project_id=project_id,
            conflict_type=ConflictType.DESIGN_DISAGREEMENT,
            description="Disagreement about building design",
            involved_agents=["agent_1", "agent_2"]
        )
        
        assert conflict_result["success"] is True
        assert "conflict_id" in conflict_result
        assert conflict_result["status"] == "open"
        
        # Check conflict was stored
        conflict_id = conflict_result["conflict_id"]
        assert conflict_id in construction_system.conflicts
        assert conflict_id in project.conflicts
        
        conflict = construction_system.conflicts[conflict_id]
        assert conflict.conflict_type == ConflictType.DESIGN_DISAGREEMENT
        assert conflict.project_id == project_id
    
    @pytest.mark.asyncio
    async def test_resolve_conflict(self, construction_system):
        """Test resolving a conflict."""
        # Create a project and conflict
        result = await construction_system.propose_project(
            initiator_id="agent_1",
            name="Test Building",
            description="A test building project",
            project_type=ProjectType.NEW_LOCATION
        )
        project_id = result["project_id"]
        
        project = construction_system.projects[project_id]
        project.participants.add("agent_2")
        
        conflict_result = await construction_system.report_conflict(
            reporter_id="agent_1",
            project_id=project_id,
            conflict_type=ConflictType.DESIGN_DISAGREEMENT,
            description="Disagreement about building design",
            involved_agents=["agent_1", "agent_2"]
        )
        conflict_id = conflict_result["conflict_id"]
        
        # Resolve the conflict
        resolution_result = await construction_system.resolve_conflict(
            conflict_id=conflict_id,
            mediator_id="agent_3",
            resolution="Compromise reached on design elements"
        )
        
        assert resolution_result["success"] is True
        assert resolution_result["status"] == "resolved"
        assert "resolution" in resolution_result
        
        # Check conflict state
        conflict = construction_system.conflicts[conflict_id]
        assert conflict.status == "resolved"
        assert conflict.mediator_id == "agent_3"
        assert conflict.resolved_at is not None
    
    def test_get_project_info(self, construction_system):
        """Test getting project information."""
        # This test needs to be run after construction system initialization
        asyncio.run(self._test_get_project_info_async(construction_system))
    
    async def _test_get_project_info_async(self, construction_system):
        """Async helper for project info test."""
        # Create a project
        result = await construction_system.propose_project(
            initiator_id="agent_1",
            name="Test Building",
            description="A test building project",
            project_type=ProjectType.NEW_LOCATION
        )
        project_id = result["project_id"]
        
        # Get project info
        info = construction_system.get_project_info(project_id)
        
        assert "project_id" in info
        assert info["name"] == "Test Building"
        assert info["type"] == ProjectType.NEW_LOCATION.value
        assert info["status"] == ProjectStatus.PROPOSED.value
        assert "progress" in info
        assert "timeline" in info
        assert "resources" in info
    
    def test_get_project_info_nonexistent(self, construction_system):
        """Test getting info for nonexistent project."""
        asyncio.run(self._test_get_project_info_nonexistent_async(construction_system))
    
    async def _test_get_project_info_nonexistent_async(self, construction_system):
        """Async helper for nonexistent project test."""
        info = construction_system.get_project_info("nonexistent")
        
        assert "error" in info
    
    def test_get_agent_projects(self, construction_system):
        """Test getting projects for an agent."""
        asyncio.run(self._test_get_agent_projects_async(construction_system))
    
    async def _test_get_agent_projects_async(self, construction_system):
        """Async helper for agent projects test."""
        # Create projects
        await construction_system.propose_project(
            initiator_id="agent_1",
            name="Project 1",
            description="First project",
            project_type=ProjectType.NEW_LOCATION
        )
        
        await construction_system.propose_project(
            initiator_id="agent_2",
            name="Project 2",
            description="Second project",
            project_type=ProjectType.REPAIR
        )
        
        # Get agent projects
        agent1_projects = construction_system.get_agent_projects("agent_1")
        
        assert len(agent1_projects) == 1
        assert agent1_projects[0]["name"] == "Project 1"
        assert agent1_projects[0]["role"] == "initiator"
    
    def test_get_available_projects(self, construction_system):
        """Test getting available projects for an agent."""
        asyncio.run(self._test_get_available_projects_async(construction_system))
    
    async def _test_get_available_projects_async(self, construction_system):
        """Async helper for available projects test."""
        # Create a project
        await construction_system.propose_project(
            initiator_id="agent_1",
            name="Available Project",
            description="A project available for joining",
            project_type=ProjectType.NEW_LOCATION
        )
        
        # Get available projects for agent_2
        available = construction_system.get_available_projects("agent_2")
        
        assert len(available) >= 1
        project = available[0]
        assert project["name"] == "Available Project"
        assert project["status"] == ProjectStatus.PROPOSED.value
    
    def test_get_construction_stats(self, construction_system):
        """Test getting construction statistics."""
        asyncio.run(self._test_get_construction_stats_async(construction_system))
    
    async def _test_get_construction_stats_async(self, construction_system):
        """Async helper for construction stats test."""
        # Create some projects
        await construction_system.propose_project(
            initiator_id="agent_1",
            name="Project 1",
            description="First project",
            project_type=ProjectType.NEW_LOCATION
        )
        
        stats = construction_system.get_construction_stats()
        
        assert "total_projects" in stats
        assert "active_projects" in stats
        assert "completed_projects" in stats
        assert "project_status_breakdown" in stats
        assert "project_type_breakdown" in stats
        assert stats["total_projects"] >= 1


class TestConstructionConflict:
    """Test the ConstructionConflict class."""
    
    def test_conflict_creation(self):
        """Test creating a construction conflict."""
        conflict = ConstructionConflict(
            conflict_id="test_conflict",
            conflict_type=ConflictType.RESOURCE_DISPUTE,
            project_id="test_project",
            involved_agents=["agent_1", "agent_2"],
            description="Dispute over resource allocation"
        )
        
        assert conflict.conflict_id == "test_conflict"
        assert conflict.conflict_type == ConflictType.RESOURCE_DISPUTE
        assert conflict.project_id == "test_project"
        assert len(conflict.involved_agents) == 2
        assert conflict.status == "open"


if __name__ == "__main__":
    pytest.main([__file__])