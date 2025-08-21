"""
Collaborative construction mechanics for the virtual world.

This module implements systems for multi-agent collaboration in building
and modifying the virtual world, including resource sharing, project
coordination, and conflict resolution.
"""

import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .virtual_world import VirtualWorld, Location, LocationType, Resource, ResourceType, Coordinates


# Singleton Metaclass
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class ProjectType(Enum):
    """Types of construction projects."""
    NEW_LOCATION = "new_location"
    LOCATION_EXPANSION = "location_expansion"
    RESOURCE_FACILITY = "resource_facility"
    INFRASTRUCTURE = "infrastructure"
    DECORATION = "decoration"
    REPAIR = "repair"
    DEMOLITION = "demolition"


class ProjectStatus(Enum):
    """Status of construction projects."""
    PROPOSED = "proposed"
    PLANNING = "planning"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ContributionType(Enum):
    """Types of contributions to construction projects."""
    RESOURCES = "resources"
    LABOR = "labor"
    DESIGN = "design"
    MANAGEMENT = "management"
    FUNDING = "funding"
    EXPERTISE = "expertise"


class ConflictType(Enum):
    """Types of construction conflicts."""
    RESOURCE_DISPUTE = "resource_dispute"
    DESIGN_DISAGREEMENT = "design_disagreement"
    LOCATION_CONFLICT = "location_conflict"
    PRIORITY_CONFLICT = "priority_conflict"
    OWNERSHIP_DISPUTE = "ownership_dispute"
    QUALITY_DISPUTE = "quality_dispute"


@dataclass
class ResourceRequirement:
    """Represents a resource requirement for a construction project."""
    resource_type: ResourceType
    quantity_needed: float
    quality_threshold: float = 0.5
    quantity_contributed: float = 0.0
    contributors: Dict[str, float] = field(default_factory=dict)  # agent_id -> quantity
    
    @property
    def is_fulfilled(self) -> bool:
        """Check if the resource requirement is fulfilled."""
        return self.quantity_contributed >= self.quantity_needed
    
    @property
    def completion_percentage(self) -> float:
        """Get completion percentage for this requirement."""
        return min(100.0, (self.quantity_contributed / self.quantity_needed) * 100.0)


@dataclass
class ProjectContribution:
    """Represents a contribution to a construction project."""
    contribution_id: str
    agent_id: str
    project_id: str
    contribution_type: ContributionType
    value: float  # Quantified value of the contribution
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    verified: bool = False
    quality_score: float = 1.0


@dataclass
class ConstructionProject:
    """Represents a construction project in the virtual world."""
    project_id: str
    name: str
    description: str
    project_type: ProjectType
    initiator_id: str
    target_location_id: Optional[str]  # Where the project will be built
    target_coordinates: Optional[Coordinates]  # For new locations
    
    # Project details
    status: ProjectStatus = ProjectStatus.PROPOSED
    priority: int = 1  # 1-10, higher is more important
    estimated_duration_hours: float = 24.0
    actual_duration_hours: float = 0.0
    
    # Resource requirements
    resource_requirements: Dict[str, ResourceRequirement] = field(default_factory=dict)
    
    # Participants
    participants: Set[str] = field(default_factory=set)  # agent_ids
    project_manager: Optional[str] = None
    required_skills: List[str] = field(default_factory=list)
    
    # Progress tracking
    progress_percentage: float = 0.0
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    contributions: List[ProjectContribution] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    # Voting and approval
    votes: Dict[str, bool] = field(default_factory=dict)  # agent_id -> approve/reject
    approval_threshold: float = 0.6  # Percentage of votes needed to approve
    
    # Conflict tracking
    conflicts: List[str] = field(default_factory=list)  # conflict_ids
    
    # Results
    result_data: Dict[str, Any] = field(default_factory=dict)
    
    def get_total_resource_progress(self) -> float:
        """Get overall resource collection progress."""
        if not self.resource_requirements:
            return 100.0
        
        total_progress = sum(req.completion_percentage for req in self.resource_requirements.values())
        return total_progress / len(self.resource_requirements)
    
    def get_approval_percentage(self) -> float:
        """Get current approval percentage."""
        if not self.votes:
            return 0.0
        
        approvals = sum(1 for vote in self.votes.values() if vote)
        return (approvals / len(self.votes)) * 100.0
    
    def is_approved(self) -> bool:
        """Check if project is approved."""
        return self.get_approval_percentage() >= (self.approval_threshold * 100.0)


@dataclass
class ConstructionConflict:
    """Represents a conflict in construction projects."""
    conflict_id: str
    conflict_type: ConflictType
    project_id: str
    involved_agents: List[str]
    description: str
    
    # Resolution
    status: str = "open"  # open, mediation, resolved, escalated
    mediator_id: Optional[str] = None
    resolution: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    
    # Evidence and arguments
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    arguments: Dict[str, str] = field(default_factory=dict)  # agent_id -> argument


class CollaborativeConstruction(AgentModule, metaclass=SingletonMeta):
    """
    System for managing collaborative construction projects in the virtual world.
    
    Handles multi-agent coordination, resource sharing, conflict resolution,
    and project management for world building activities.
    """
    
    def __init__(self, agent_id: str, virtual_world: VirtualWorld):
        super().__init__(agent_id)
        self.virtual_world = virtual_world
        self.logger = get_agent_logger(agent_id, "construction")
        
        # Project management
        self.projects: Dict[str, ConstructionProject] = {}
        self.conflicts: Dict[str, ConstructionConflict] = {}
        self.project_counter = 0
        self.conflict_counter = 0
        
        # Construction configuration
        self.config = {
            "max_concurrent_projects": 10,
            "min_participants_for_major_project": 3,
            "resource_sharing_radius": 100.0,
            "project_timeout_hours": 168.0,  # 1 week
            "conflict_resolution_timeout_hours": 24.0,
            "quality_threshold": 0.7,
            "collaboration_bonus": 1.2,  # Bonus for collaborative work
            "skill_matching_threshold": 0.8
        }
        
        # Skill requirements for different project types
        self.project_skill_requirements = {
            ProjectType.NEW_LOCATION: ["architecture", "planning", "construction"],
            ProjectType.LOCATION_EXPANSION: ["construction", "engineering"],
            ProjectType.RESOURCE_FACILITY: ["engineering", "resource_management"],
            ProjectType.INFRASTRUCTURE: ["engineering", "planning"],
            ProjectType.DECORATION: ["creativity", "design"],
            ProjectType.REPAIR: ["maintenance", "construction"],
            ProjectType.DEMOLITION: ["construction", "safety"]
        }
        
        # Statistics
        self.stats = {
            "projects_created": 0,
            "projects_completed": 0,
            "projects_failed": 0,
            "conflicts_resolved": 0,
            "total_contributions": 0,
            "collaborative_hours": 0.0
        }
        
        self.logger.info("Collaborative construction system initialized")
    
    async def initialize(self) -> None:
        """Initialize the construction system."""
        try:
            # Start background processes
            asyncio.create_task(self._project_monitoring_loop())
            asyncio.create_task(self._conflict_resolution_loop())
            
            self.logger.info("Construction system initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize construction system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the construction system."""
        try:
            # Save project states
            await self._save_project_states()
            
            self.logger.info("Construction system shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during construction system shutdown: {e}")
    
    async def propose_project(
        self,
        initiator_id: str,
        name: str,
        description: str,
        project_type: ProjectType,
        target_location_id: Optional[str] = None,
        target_coordinates: Optional[Coordinates] = None,
        resource_requirements: Optional[Dict[ResourceType, Tuple[float, float]]] = None,
        estimated_duration_hours: float = 24.0,
        priority: int = 1
    ) -> Dict[str, Any]:
        """Propose a new construction project."""
        try:
            # Generate project ID
            self.project_counter += 1
            project_id = f"project_{self.project_counter}_{datetime.now().timestamp()}"
            
            # Create resource requirements
            requirements = {}
            if resource_requirements:
                for resource_type, (quantity, quality) in resource_requirements.items():
                    req_id = f"{project_id}_{resource_type.value}"
                    requirements[req_id] = ResourceRequirement(
                        resource_type=resource_type,
                        quantity_needed=quantity,
                        quality_threshold=quality
                    )
            
            # Determine required skills
            required_skills = self.project_skill_requirements.get(project_type, [])
            
            # Create project
            project = ConstructionProject(
                project_id=project_id,
                name=name,
                description=description,
                project_type=project_type,
                initiator_id=initiator_id,
                target_location_id=target_location_id,
                target_coordinates=target_coordinates,
                resource_requirements=requirements,
                estimated_duration_hours=estimated_duration_hours,
                priority=priority,
                required_skills=required_skills
            )
            
            # Add initiator as participant
            project.participants.add(initiator_id)
            
            # Store project
            self.projects[project_id] = project
            self.stats["projects_created"] += 1
            
            # Log event
            log_agent_event(
                self.agent_id,
                "project_proposed",
                {
                    "project_id": project_id,
                    "initiator": initiator_id,
                    "project_type": project_type.value,
                    "name": name
                }
            )
            
            self.logger.info(f"Project proposed: {name} by {initiator_id}")
            
            return {
                "success": True,
                "project_id": project_id,
                "status": project.status.value,
                "required_approvals": max(1, len(project.participants) * project.approval_threshold)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to propose project: {e}")
            return {"success": False, "error": str(e)}
    
    async def vote_on_project(self, agent_id: str, project_id: str, approve: bool) -> Dict[str, Any]:
        """Vote on a proposed project."""
        try:
            if project_id not in self.projects:
                return {"success": False, "error": "Project not found"}
            
            project = self.projects[project_id]
            
            # Check if agent can vote (must be in the area or have relevant skills)
            if not await self._can_agent_participate(agent_id, project):
                return {"success": False, "error": "Agent not eligible to vote on this project"}
            
            # Record vote
            project.votes[agent_id] = approve
            
            # Add as participant if approving
            if approve:
                project.participants.add(agent_id)
            
            # Check if project is now approved
            if project.status == ProjectStatus.PROPOSED and project.is_approved():
                project.status = ProjectStatus.PLANNING
                
                # Select project manager (highest status participant)
                project.project_manager = await self._select_project_manager(project)
                
                log_agent_event(
                    self.agent_id,
                    "project_approved",
                    {
                        "project_id": project_id,
                        "project_manager": project.project_manager,
                        "participants": list(project.participants)
                    }
                )
            
            result = {
                "success": True,
                "vote_recorded": approve,
                "current_approval": project.get_approval_percentage(),
                "is_approved": project.is_approved(),
                "status": project.status.value
            }
            
            self.logger.info(f"Vote recorded for project {project_id}: {approve} by {agent_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to record vote: {e}")
            return {"success": False, "error": str(e)}
    
    async def contribute_to_project(
        self,
        agent_id: str,
        project_id: str,
        contribution_type: ContributionType,
        value: float,
        description: str,
        resource_type: Optional[ResourceType] = None
    ) -> Dict[str, Any]:
        \"\"\"Make a contribution to a construction project.\"\"\"
        try:
            if project_id not in self.projects:
                return {\"success\": False, \"error\": \"Project not found\"}
            
            project = self.projects[project_id]
            
            # Check if project accepts contributions
            if project.status not in [ProjectStatus.PLANNING, ProjectStatus.APPROVED, ProjectStatus.IN_PROGRESS]:
                return {\"success\": False, \"error\": f\"Project not accepting contributions (status: {project.status.value})\"}
            
            # Validate contribution
            if not await self._validate_contribution(agent_id, project, contribution_type, value, resource_type):
                return {\"success\": False, \"error\": \"Invalid contribution\"}
            
            # Create contribution record
            contribution_id = f\"contrib_{len(project.contributions)}_{datetime.now().timestamp()}\"
            contribution = ProjectContribution(
                contribution_id=contribution_id,
                agent_id=agent_id,
                project_id=project_id,
                contribution_type=contribution_type,
                value=value,
                description=description
            )
            
            # Process resource contributions
            if contribution_type == ContributionType.RESOURCES and resource_type:
                await self._process_resource_contribution(project, agent_id, resource_type, value)
            
            # Add contribution
            project.contributions.append(contribution)
            project.participants.add(agent_id)
            
            # Update project progress
            await self._update_project_progress(project)
            
            # Update statistics
            self.stats[\"total_contributions\"] += 1
            
            log_agent_event(
                self.agent_id,
                \"project_contribution\",
                {
                    \"project_id\": project_id,
                    \"contributor\": agent_id,
                    \"contribution_type\": contribution_type.value,
                    \"value\": value
                }
            )
            
            result = {
                \"success\": True,
                \"contribution_id\": contribution_id,
                \"project_progress\": project.progress_percentage,
                \"resource_progress\": project.get_total_resource_progress()
            }
            
            self.logger.info(f\"Contribution made to project {project_id}: {contribution_type.value} by {agent_id}\")
            
            return result
            
        except Exception as e:
            self.logger.error(f\"Failed to process contribution: {e}\")
            return {\"success\": False, \"error\": str(e)}
    
    async def start_project(self, project_id: str, manager_id: Optional[str] = None) -> Dict[str, Any]:
        \"\"\"Start a construction project.\"\"\"
        try:
            if project_id not in self.projects:
                return {\"success\": False, \"error\": \"Project not found\"}
            
            project = self.projects[project_id]
            
            # Check if project can be started
            if project.status != ProjectStatus.APPROVED:
                return {\"success\": False, \"error\": f\"Project not ready to start (status: {project.status.value})\"}
            
            # Check resource requirements
            resource_progress = project.get_total_resource_progress()
            if resource_progress < 80.0:  # Need at least 80% of resources
                return {\"success\": False, \"error\": f\"Insufficient resources ({resource_progress:.1f}% collected)\"}
            
            # Set project manager if not already set
            if manager_id and manager_id in project.participants:
                project.project_manager = manager_id
            elif not project.project_manager:
                project.project_manager = await self._select_project_manager(project)
            
            # Start project
            project.status = ProjectStatus.IN_PROGRESS
            project.started_at = datetime.now()
            
            # Set deadline
            project.deadline = datetime.now() + timedelta(hours=project.estimated_duration_hours * 1.5)
            
            log_agent_event(
                self.agent_id,
                \"project_started\",
                {
                    \"project_id\": project_id,
                    \"project_manager\": project.project_manager,
                    \"participants\": list(project.participants),
                    \"deadline\": project.deadline.isoformat() if project.deadline else None
                }
            )
            
            result = {
                \"success\": True,
                \"status\": project.status.value,
                \"project_manager\": project.project_manager,
                \"deadline\": project.deadline.isoformat() if project.deadline else None,
                \"participants\": list(project.participants)
            }
            
            self.logger.info(f\"Project started: {project_id} managed by {project.project_manager}\")
            
            return result
            
        except Exception as e:
            self.logger.error(f\"Failed to start project: {e}\")
            return {\"success\": False, \"error\": str(e)}"    
    
async def complete_project(self, project_id: str) -> Dict[str, Any]:
        """Complete a construction project and apply its effects."""
        try:
            if project_id not in self.projects:
                return {"success": False, "error": "Project not found"}
            
            project = self.projects[project_id]
            
            if project.status != ProjectStatus.IN_PROGRESS:
                return {"success": False, "error": f"Project not in progress (status: {project.status.value})"}
            
            # Apply project effects to the virtual world
            result_data = await self._apply_project_effects(project)
            
            # Complete project
            project.status = ProjectStatus.COMPLETED
            project.completed_at = datetime.now()
            project.progress_percentage = 100.0
            project.result_data = result_data
            
            if project.started_at:
                project.actual_duration_hours = (datetime.now() - project.started_at).total_seconds() / 3600.0
            
            # Update statistics
            self.stats["projects_completed"] += 1
            self.stats["collaborative_hours"] += project.actual_duration_hours
            
            # Reward participants
            await self._reward_participants(project)
            
            log_agent_event(
                self.agent_id,
                "project_completed",
                {
                    "project_id": project_id,
                    "duration_hours": project.actual_duration_hours,
                    "participants": list(project.participants),
                    "result": result_data
                }
            )
            
            result = {
                "success": True,
                "status": project.status.value,
                "duration_hours": project.actual_duration_hours,
                "result": result_data,
                "participants_rewarded": len(project.participants)
            }
            
            self.logger.info(f"Project completed: {project_id} in {project.actual_duration_hours:.1f} hours")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to complete project: {e}")
            return {"success": False, "error": str(e)}
    
    async def report_conflict(
        self,
        reporter_id: str,
        project_id: str,
        conflict_type: ConflictType,
        description: str,
        involved_agents: List[str]
    ) -> Dict[str, Any]:
        """Report a conflict in a construction project."""
        try:
            if project_id not in self.projects:
                return {"success": False, "error": "Project not found"}
            
            project = self.projects[project_id]
            
            # Validate reporter is involved in project
            if reporter_id not in project.participants:
                return {"success": False, "error": "Reporter not involved in project"}
            
            # Create conflict
            self.conflict_counter += 1
            conflict_id = f"conflict_{self.conflict_counter}_{datetime.now().timestamp()}"
            
            conflict = ConstructionConflict(
                conflict_id=conflict_id,
                conflict_type=conflict_type,
                project_id=project_id,
                involved_agents=involved_agents,
                description=description
            )
            
            # Store conflict
            self.conflicts[conflict_id] = conflict
            project.conflicts.append(conflict_id)
            
            # Pause project if it's a major conflict
            if conflict_type in [ConflictType.DESIGN_DISAGREEMENT, ConflictType.OWNERSHIP_DISPUTE]:
                if project.status == ProjectStatus.IN_PROGRESS:
                    project.status = ProjectStatus.PAUSED
            
            log_agent_event(
                self.agent_id,
                "conflict_reported",
                {
                    "conflict_id": conflict_id,
                    "project_id": project_id,
                    "conflict_type": conflict_type.value,
                    "reporter": reporter_id,
                    "involved_agents": involved_agents
                }
            )
            
            result = {
                "success": True,
                "conflict_id": conflict_id,
                "status": conflict.status,
                "project_paused": project.status == ProjectStatus.PAUSED
            }
            
            self.logger.info(f"Conflict reported: {conflict_type.value} in project {project_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to report conflict: {e}")
            return {"success": False, "error": str(e)}
    
    async def resolve_conflict(self, conflict_id: str, mediator_id: str, resolution: str) -> Dict[str, Any]:
        """Resolve a construction conflict."""
        try:
            if conflict_id not in self.conflicts:
                return {"success": False, "error": "Conflict not found"}
            
            conflict = self.conflicts[conflict_id]
            project = self.projects[conflict.project_id]
            
            # Set mediator and resolution
            conflict.mediator_id = mediator_id
            conflict.resolution = resolution
            conflict.status = "resolved"
            conflict.resolved_at = datetime.now()
            
            # Resume project if it was paused
            if project.status == ProjectStatus.PAUSED:
                project.status = ProjectStatus.IN_PROGRESS
            
            # Update statistics
            self.stats["conflicts_resolved"] += 1
            
            log_agent_event(
                self.agent_id,
                "conflict_resolved",
                {
                    "conflict_id": conflict_id,
                    "project_id": conflict.project_id,
                    "mediator": mediator_id,
                    "resolution": resolution
                }
            )
            
            result = {
                "success": True,
                "status": conflict.status,
                "project_resumed": project.status == ProjectStatus.IN_PROGRESS,
                "resolution": resolution
            }
            
            self.logger.info(f"Conflict resolved: {conflict_id} by {mediator_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to resolve conflict: {e}")
            return {"success": False, "error": str(e)}
    
    def get_project_info(self, project_id: str) -> Dict[str, Any]:
        """Get detailed information about a project."""
        try:
            if project_id not in self.projects:
                return {"error": "Project not found"}
            
            project = self.projects[project_id]
            
            # Calculate progress metrics
            resource_progress = project.get_total_resource_progress()
            approval_percentage = project.get_approval_percentage()
            
            # Get contribution summary
            contribution_summary = {}
            for contrib in project.contributions:
                contrib_type = contrib.contribution_type.value
                if contrib_type not in contribution_summary:
                    contribution_summary[contrib_type] = {"count": 0, "total_value": 0.0}
                contribution_summary[contrib_type]["count"] += 1
                contribution_summary[contrib_type]["total_value"] += contrib.value
            
            return {
                "project_id": project.project_id,
                "name": project.name,
                "description": project.description,
                "type": project.project_type.value,
                "status": project.status.value,
                "initiator": project.initiator_id,
                "project_manager": project.project_manager,
                "participants": list(project.participants),
                "progress": {
                    "overall": project.progress_percentage,
                    "resources": resource_progress,
                    "approval": approval_percentage
                },
                "timeline": {
                    "created": project.created_at.isoformat(),
                    "started": project.started_at.isoformat() if project.started_at else None,
                    "completed": project.completed_at.isoformat() if project.completed_at else None,
                    "deadline": project.deadline.isoformat() if project.deadline else None,
                    "estimated_duration": project.estimated_duration_hours,
                    "actual_duration": project.actual_duration_hours
                },
                "resources": {
                    req_id: {
                        "type": req.resource_type.value,
                        "needed": req.quantity_needed,
                        "contributed": req.quantity_contributed,
                        "completion": req.completion_percentage,
                        "contributors": req.contributors
                    }
                    for req_id, req in project.resource_requirements.items()
                },
                "contributions": contribution_summary,
                "conflicts": len(project.conflicts),
                "votes": {
                    "total": len(project.votes),
                    "approvals": sum(1 for vote in project.votes.values() if vote),
                    "rejections": sum(1 for vote in project.votes.values() if not vote)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get project info: {e}")
            return {"error": str(e)}
    
    def get_agent_projects(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all projects an agent is involved in."""
        try:
            agent_projects = []
            
            for project in self.projects.values():
                if agent_id in project.participants or agent_id == project.initiator_id:
                    agent_projects.append({
                        "project_id": project.project_id,
                        "name": project.name,
                        "type": project.project_type.value,
                        "status": project.status.value,
                        "role": self._get_agent_role_in_project(agent_id, project),
                        "progress": project.progress_percentage,
                        "created": project.created_at.isoformat()
                    })
            
            # Sort by creation date (most recent first)
            agent_projects.sort(key=lambda p: p["created"], reverse=True)
            
            return agent_projects
            
        except Exception as e:
            self.logger.error(f"Failed to get agent projects: {e}")
            return []
    
    def get_available_projects(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get projects available for an agent to join."""
        try:
            available_projects = []
            
            for project in self.projects.values():
                # Skip if agent is already involved
                if agent_id in project.participants:
                    continue
                
                # Only show projects that are accepting participants
                if project.status not in [ProjectStatus.PROPOSED, ProjectStatus.PLANNING, ProjectStatus.APPROVED]:
                    continue
                
                # Check if agent can participate
                if not asyncio.run(self._can_agent_participate(agent_id, project)):
                    continue
                
                available_projects.append({
                    "project_id": project.project_id,
                    "name": project.name,
                    "description": project.description,
                    "type": project.project_type.value,
                    "status": project.status.value,
                    "initiator": project.initiator_id,
                    "participants": len(project.participants),
                    "progress": project.progress_percentage,
                    "resource_progress": project.get_total_resource_progress(),
                    "approval_progress": project.get_approval_percentage(),
                    "required_skills": project.required_skills,
                    "priority": project.priority,
                    "created": project.created_at.isoformat()
                })
            
            # Sort by priority and creation date
            available_projects.sort(key=lambda p: (p["priority"], p["created"]), reverse=True)
            
            return available_projects
            
        except Exception as e:
            self.logger.error(f"Failed to get available projects: {e}")
            return []
    
    def get_construction_stats(self) -> Dict[str, Any]:
        """Get construction system statistics."""
        try:
            # Project status breakdown
            status_breakdown = {}
            for status in ProjectStatus:
                status_breakdown[status.value] = len([
                    p for p in self.projects.values() 
                    if p.status == status
                ])
            
            # Project type breakdown
            type_breakdown = {}
            for project_type in ProjectType:
                type_breakdown[project_type.value] = len([
                    p for p in self.projects.values() 
                    if p.project_type == project_type
                ])
            
            # Active conflicts
            active_conflicts = len([
                c for c in self.conflicts.values() 
                if c.status == "open"
            ])
            
            return {
                "total_projects": len(self.projects),
                "active_projects": len([p for p in self.projects.values() if p.status == ProjectStatus.IN_PROGRESS]),
                "completed_projects": self.stats["projects_completed"],
                "failed_projects": self.stats["projects_failed"],
                "total_contributions": self.stats["total_contributions"],
                "collaborative_hours": self.stats["collaborative_hours"],
                "active_conflicts": active_conflicts,
                "resolved_conflicts": self.stats["conflicts_resolved"],
                "project_status_breakdown": status_breakdown,
                "project_type_breakdown": type_breakdown,
                "success_rate": (self.stats["projects_completed"] / max(1, len(self.projects))) * 100.0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get construction stats: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _can_agent_participate(self, agent_id: str, project: ConstructionProject) -> bool:
        """Check if an agent can participate in a project."""
        try:
            # Check if agent is in the virtual world
            if agent_id not in self.virtual_world.agent_positions:
                return False
            
            # Check location proximity for location-based projects
            if project.target_location_id:
                agent_position = self.virtual_world.agent_positions[agent_id]
                agent_location = self.virtual_world.locations[agent_position.current_location_id]
                target_location = self.virtual_world.locations[project.target_location_id]
                
                distance = agent_location.coordinates.distance_to(target_location.coordinates)
                if distance > self.config["resource_sharing_radius"]:
                    return False
            
            # Check skill requirements (simplified - would need agent skill system)
            # For now, assume all agents can participate
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking agent participation eligibility: {e}")
            return False
    
    async def _select_project_manager(self, project: ConstructionProject) -> str:
        """Select a project manager from participants."""
        try:
            # For now, select the initiator or a random participant
            # In a full implementation, this would consider agent skills and status
            if project.initiator_id in project.participants:
                return project.initiator_id
            
            return random.choice(list(project.participants))
            
        except Exception as e:
            self.logger.error(f"Error selecting project manager: {e}")
            return list(project.participants)[0] if project.participants else project.initiator_id
    
    async def _validate_contribution(
        self,
        agent_id: str,
        project: ConstructionProject,
        contribution_type: ContributionType,
        value: float,
        resource_type: Optional[ResourceType]
    ) -> bool:
        """Validate a contribution to a project."""
        try:
            # Basic validation
            if value <= 0:
                return False
            
            # Check if agent is in the world
            if agent_id not in self.virtual_world.agent_positions:
                return False
            
            # Validate resource contributions
            if contribution_type == ContributionType.RESOURCES:
                if not resource_type:
                    return False
                
                # Check if agent has access to the resource
                agent_position = self.virtual_world.agent_positions[agent_id]
                agent_location = self.virtual_world.locations[agent_position.current_location_id]
                
                # Check if resource is available in agent's location
                has_resource = any(
                    res.resource_type == resource_type and res.quantity >= value
                    for res in agent_location.resources.values()
                )
                
                if not has_resource:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating contribution: {e}")
            return False
    
    async def _process_resource_contribution(
        self,
        project: ConstructionProject,
        agent_id: str,
        resource_type: ResourceType,
        quantity: float
    ) -> None:
        """Process a resource contribution to a project."""
        try:
            # Find matching resource requirement
            for req in project.resource_requirements.values():
                if req.resource_type == resource_type and not req.is_fulfilled:
                    # Calculate how much can be contributed
                    needed = req.quantity_needed - req.quantity_contributed
                    contributed = min(quantity, needed)
                    
                    # Update requirement
                    req.quantity_contributed += contributed
                    req.contributors[agent_id] = req.contributors.get(agent_id, 0) + contributed
                    
                    # Remove resource from agent's location (simplified)
                    agent_position = self.virtual_world.agent_positions[agent_id]
                    agent_location = self.virtual_world.locations[agent_position.current_location_id]
                    
                    for resource in agent_location.resources.values():
                        if resource.resource_type == resource_type:
                            resource.quantity = max(0, resource.quantity - contributed)
                            break
                    
                    break
            
        except Exception as e:
            self.logger.error(f"Error processing resource contribution: {e}")
    
    async def _update_project_progress(self, project: ConstructionProject) -> None:
        """Update the overall progress of a project."""
        try:
            # Calculate progress based on resource collection and contributions
            resource_progress = project.get_total_resource_progress()
            
            # Factor in other contributions (simplified)
            contribution_bonus = min(20.0, len(project.contributions) * 2.0)
            
            # Calculate overall progress
            project.progress_percentage = min(100.0, (resource_progress * 0.8) + contribution_bonus)
            
            # Check if project is ready for completion
            if project.progress_percentage >= 95.0 and project.status == ProjectStatus.IN_PROGRESS:
                # Auto-complete if very close to done
                await self.complete_project(project.project_id)
            
        except Exception as e:
            self.logger.error(f"Error updating project progress: {e}")
    
    async def _apply_project_effects(self, project: ConstructionProject) -> Dict[str, Any]:
        """Apply the effects of a completed project to the virtual world."""
        try:
            result_data = {}
            
            if project.project_type == ProjectType.NEW_LOCATION:
                # Create new location
                result_data = await self._create_new_location(project)
            
            elif project.project_type == ProjectType.LOCATION_EXPANSION:
                # Expand existing location
                result_data = await self._expand_location(project)
            
            elif project.project_type == ProjectType.RESOURCE_FACILITY:
                # Add resource generation facility
                result_data = await self._create_resource_facility(project)
            
            elif project.project_type == ProjectType.INFRASTRUCTURE:
                # Improve connections between locations
                result_data = await self._build_infrastructure(project)
            
            elif project.project_type == ProjectType.DECORATION:
                # Improve location aesthetics
                result_data = await self._add_decoration(project)
            
            elif project.project_type == ProjectType.REPAIR:
                # Repair location or restore resources
                result_data = await self._repair_location(project)
            
            return result_data
            
        except Exception as e:
            self.logger.error(f"Error applying project effects: {e}")
            return {"error": str(e)}
    
    async def _create_new_location(self, project: ConstructionProject) -> Dict[str, Any]:
        """Create a new location from a construction project."""
        try:
            from .virtual_world import Location, ActivityType
            
            # Determine location type based on project details
            location_type = LocationType.WORKSPACE  # Default
            if "residential" in project.name.lower():
                location_type = LocationType.RESIDENTIAL
            elif "lab" in project.name.lower():
                location_type = LocationType.LABORATORY
            elif "library" in project.name.lower():
                location_type = LocationType.LIBRARY
            
            # Create location
            location_id = f"constructed_{project.project_id}"
            location = Location(
                location_id=location_id,
                name=project.name,
                description=f"Constructed by collaborative effort: {project.description}",
                location_type=location_type,
                coordinates=project.target_coordinates or Coordinates(
                    random.uniform(0, self.virtual_world.world_size[0]),
                    random.uniform(0, self.virtual_world.world_size[1]),
                    0
                ),
                capacity=max(10, len(project.participants) * 2),
                available_activities=[ActivityType.COLLABORATION, ActivityType.SOCIALIZING]
            )
            
            # Add to virtual world
            self.virtual_world.locations[location_id] = location
            self.virtual_world.world_stats["total_locations"] += 1
            
            return {
                "location_id": location_id,
                "location_name": location.name,
                "location_type": location_type.value,
                "capacity": location.capacity
            }
            
        except Exception as e:
            self.logger.error(f"Error creating new location: {e}")
            return {"error": str(e)}
    
    async def _expand_location(self, project: ConstructionProject) -> Dict[str, Any]:
        """Expand an existing location."""
        try:
            if not project.target_location_id or project.target_location_id not in self.virtual_world.locations:
                return {"error": "Target location not found"}
            
            location = self.virtual_world.locations[project.target_location_id]
            
            # Increase capacity
            old_capacity = location.capacity
            location.capacity = int(location.capacity * 1.5)
            
            # Add new activities if not present
            new_activities = [ActivityType.COLLABORATION, ActivityType.CREATION]
            for activity in new_activities:
                if activity not in location.available_activities:
                    location.available_activities.append(activity)
            
            return {
                "location_id": location.location_id,
                "old_capacity": old_capacity,
                "new_capacity": location.capacity,
                "activities_added": len(new_activities)
            }
            
        except Exception as e:
            self.logger.error(f"Error expanding location: {e}")
            return {"error": str(e)}
    
    async def _create_resource_facility(self, project: ConstructionProject) -> Dict[str, Any]:
        """Create a resource generation facility."""
        try:
            if not project.target_location_id or project.target_location_id not in self.virtual_world.locations:
                return {"error": "Target location not found"}
            
            location = self.virtual_world.locations[project.target_location_id]
            
            # Add resource generation
            from .virtual_world import Resource
            
            resource_type = ResourceType.COMPUTATIONAL_POWER  # Default
            if "energy" in project.name.lower():
                resource_type = ResourceType.ENERGY_CRYSTALS
            elif "knowledge" in project.name.lower():
                resource_type = ResourceType.KNOWLEDGE_DATABASE
            
            resource_id = f"facility_{project.project_id}"
            resource = Resource(
                resource_id=resource_id,
                resource_type=resource_type,
                quantity=500.0,
                quality=0.8,
                location_id=location.location_id,
                regeneration_rate=10.0,
                max_quantity=1000.0
            )
            
            location.resources[resource_id] = resource
            
            return {
                "location_id": location.location_id,
                "resource_type": resource_type.value,
                "initial_quantity": resource.quantity,
                "regeneration_rate": resource.regeneration_rate
            }
            
        except Exception as e:
            self.logger.error(f"Error creating resource facility: {e}")
            return {"error": str(e)}
    
    async def _build_infrastructure(self, project: ConstructionProject) -> Dict[str, Any]:
        """Build infrastructure connections."""
        try:
            connections_added = 0
            
            # Connect nearby locations that aren't already connected
            for loc1_id, loc1 in self.virtual_world.locations.items():
                for loc2_id, loc2 in self.virtual_world.locations.items():
                    if loc1_id != loc2_id and loc2_id not in loc1.connections:
                        distance = loc1.coordinates.distance_to(loc2.coordinates)
                        if distance < 150.0:  # Connect nearby locations
                            loc1.connections.append(loc2_id)
                            loc2.connections.append(loc1_id)
                            connections_added += 1
            
            return {
                "connections_added": connections_added,
                "infrastructure_type": "transportation_network"
            }
            
        except Exception as e:
            self.logger.error(f"Error building infrastructure: {e}")
            return {"error": str(e)}
    
    async def _add_decoration(self, project: ConstructionProject) -> Dict[str, Any]:
        """Add decorative improvements to a location."""
        try:
            if not project.target_location_id or project.target_location_id not in self.virtual_world.locations:
                return {"error": "Target location not found"}
            
            location = self.virtual_world.locations[project.target_location_id]
            
            # Add aesthetic improvements to environment properties
            if "environment_properties" not in location.environment_properties:
                location.environment_properties = {}
            
            location.environment_properties.update({
                "aesthetic_rating": location.environment_properties.get("aesthetic_rating", 5.0) + 2.0,
                "comfort_level": location.environment_properties.get("comfort_level", 5.0) + 1.5,
                "decoration_project": project.project_id
            })
            
            return {
                "location_id": location.location_id,
                "aesthetic_improvement": 2.0,
                "comfort_improvement": 1.5
            }
            
        except Exception as e:
            self.logger.error(f"Error adding decoration: {e}")
            return {"error": str(e)}
    
    async def _repair_location(self, project: ConstructionProject) -> Dict[str, Any]:
        """Repair a location or restore resources."""
        try:
            if not project.target_location_id or project.target_location_id not in self.virtual_world.locations:
                return {"error": "Target location not found"}
            
            location = self.virtual_world.locations[project.target_location_id]
            
            # Restore resource quantities
            resources_repaired = 0
            for resource in location.resources.values():
                if resource.quantity < resource.max_quantity * 0.8:
                    resource.quantity = min(resource.max_quantity, resource.quantity * 1.5)
                    resources_repaired += 1
            
            return {
                "location_id": location.location_id,
                "resources_repaired": resources_repaired,
                "repair_type": "resource_restoration"
            }
            
        except Exception as e:
            self.logger.error(f"Error repairing location: {e}")
            return {"error": str(e)}
    
    async def _reward_participants(self, project: ConstructionProject) -> None:
        """Reward participants for completing a project."""
        try:
            # Calculate base reward based on project complexity
            base_reward = project.estimated_duration_hours * 10.0
            
            # Apply collaboration bonus
            collaboration_bonus = len(project.participants) * self.config["collaboration_bonus"]
            total_reward = base_reward * collaboration_bonus
            
            # Distribute rewards (simplified - would integrate with agent status system)
            reward_per_participant = total_reward / len(project.participants)
            
            for participant_id in project.participants:
                # In a full implementation, this would update agent status/reputation
                log_agent_event(
                    self.agent_id,
                    "project_reward",
                    {
                        "agent_id": participant_id,
                        "project_id": project.project_id,
                        "reward_points": reward_per_participant,
                        "project_type": project.project_type.value
                    }
                )
            
        except Exception as e:
            self.logger.error(f"Error rewarding participants: {e}")
    
    def _get_agent_role_in_project(self, agent_id: str, project: ConstructionProject) -> str:
        """Get an agent's role in a project."""
        if agent_id == project.initiator_id:
            return "initiator"
        elif agent_id == project.project_manager:
            return "manager"
        elif agent_id in project.participants:
            return "participant"
        else:
            return "observer"
    
    async def _project_monitoring_loop(self) -> None:
        """Background loop to monitor project progress and timeouts."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                current_time = datetime.now()
                
                for project in self.projects.values():
                    # Check for project timeouts
                    if project.deadline and current_time > project.deadline:
                        if project.status == ProjectStatus.IN_PROGRESS:
                            project.status = ProjectStatus.FAILED
                            self.stats["projects_failed"] += 1
                            
                            log_agent_event(
                                self.agent_id,
                                "project_timeout",
                                {
                                    "project_id": project.project_id,
                                    "deadline": project.deadline.isoformat()
                                }
                            )
                    
                    # Auto-progress projects that are ready
                    if project.status == ProjectStatus.APPROVED and project.get_total_resource_progress() >= 80.0:
                        await self.start_project(project.project_id)
                
            except Exception as e:
                self.logger.error(f"Error in project monitoring loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _conflict_resolution_loop(self) -> None:
        """Background loop to handle conflict resolution timeouts."""
        while True:
            try:
                await asyncio.sleep(1800)  # Check every 30 minutes
                
                current_time = datetime.now()
                timeout_hours = self.config["conflict_resolution_timeout_hours"]
                
                for conflict in self.conflicts.values():
                    if conflict.status == "open":
                        time_since_creation = current_time - conflict.created_at
                        
                        if time_since_creation.total_seconds() / 3600.0 > timeout_hours:
                            # Auto-resolve with default resolution
                            await self.resolve_conflict(
                                conflict.conflict_id,
                                "system",
                                "Auto-resolved due to timeout - proceeding with majority consensus"
                            )
                
            except Exception as e:
                self.logger.error(f"Error in conflict resolution loop: {e}")
                await asyncio.sleep(300)
    
    async def _save_project_states(self) -> None:
        """Save current project states."""
        try:
            # In a real implementation, this would save to persistent storage
            self.logger.info(f"Saved states for {len(self.projects)} projects and {len(self.conflicts)} conflicts")
        except Exception as e:
            self.logger.error(f"Error saving project states: {e}")