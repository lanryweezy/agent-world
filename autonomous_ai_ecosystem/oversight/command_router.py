"""
Human command routing system for the autonomous AI ecosystem.

This module implements message routing from humans to the highest-status agents,
expert agent identification, task delegation, and command processing.
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class CommandType(Enum):
    """Types of human commands."""
    QUERY = "query"  # Information request
    TASK = "task"  # Task assignment
    DIRECTIVE = "directive"  # Direct instruction
    FEEDBACK = "feedback"  # Feedback on agent performance
    EMERGENCY = "emergency"  # Emergency intervention
    CONFIGURATION = "configuration"  # System configuration change
    MONITORING = "monitoring"  # Request for status/monitoring info
    COLLABORATION = "collaboration"  # Request for human-AI collaboration


class CommandPriority(Enum):
    """Priority levels for human commands."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    EMERGENCY = 5


class CommandStatus(Enum):
    """Status of human commands."""
    RECEIVED = "received"
    ROUTING = "routing"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


@dataclass
class ExpertAgent:
    """Represents an expert agent for specific domains."""
    agent_id: str
    name: str
    expertise_domains: List[str]
    status_score: float
    availability: bool = True
    
    # Performance metrics
    success_rate: float = 1.0
    average_response_time: float = 1.0  # hours
    total_commands_handled: int = 0
    satisfaction_rating: float = 5.0  # 1-5 scale
    
    # Specialization
    preferred_command_types: List[CommandType] = field(default_factory=list)
    max_concurrent_commands: int = 3
    current_workload: int = 0
    
    # Availability schedule
    available_hours: List[Tuple[int, int]] = field(default_factory=lambda: [(0, 24)])  # (start, end) hours
    timezone: str = "UTC"
    
    def is_available(self) -> bool:
        """Check if agent is currently available."""
        if not self.availability:
            return False
        
        if self.current_workload >= self.max_concurrent_commands:
            return False
        
        # Check time availability (simplified)
        current_hour = datetime.now().hour
        for start_hour, end_hour in self.available_hours:
            if start_hour <= current_hour < end_hour:
                return True
        
        return False
    
    def get_expertise_score(self, domain: str) -> float:
        """Get expertise score for a specific domain."""
        if domain.lower() in [d.lower() for d in self.expertise_domains]:
            return self.status_score * self.success_rate
        return 0.0
    
    def get_overall_score(self) -> float:
        """Get overall agent score for command assignment."""
        availability_bonus = 1.2 if self.is_available() else 0.5
        workload_penalty = 1.0 - (self.current_workload / max(1, self.max_concurrent_commands)) * 0.3
        
        return (self.status_score * self.success_rate * self.satisfaction_rating / 5.0 * 
                availability_bonus * workload_penalty)


@dataclass
class HumanCommand:
    """Represents a command from a human user."""
    command_id: str
    human_id: str
    command_type: CommandType
    priority: CommandPriority
    
    # Command content
    title: str
    description: str
    requirements: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Routing and assignment
    status: CommandStatus = CommandStatus.RECEIVED
    assigned_agent_id: Optional[str] = None
    expert_domain: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    # Progress tracking
    progress_percentage: float = 0.0
    status_updates: List[str] = field(default_factory=list)
    
    # Response and feedback
    response: Optional[str] = None
    human_satisfaction: Optional[int] = None  # 1-5 rating
    human_feedback: str = ""
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_status_update(self, update: str) -> None:
        """Add a status update to the command."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_updates.append(f"[{timestamp}] {update}")
        
        # Limit status updates
        if len(self.status_updates) > 50:
            self.status_updates = self.status_updates[-50:]
    
    def get_duration(self) -> float:
        """Get command processing duration in hours."""
        if not self.started_at:
            return 0.0
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds() / 3600.0
    
    def is_overdue(self) -> bool:
        """Check if command is overdue."""
        if not self.deadline or self.status in [CommandStatus.COMPLETED, CommandStatus.CANCELLED]:
            return False
        return datetime.now() > self.deadline


@dataclass
class CommandResponse:
    """Response to a human command."""
    response_id: str
    command_id: str
    agent_id: str
    
    # Response content
    response_type: str  # answer, status_update, request_clarification, completion
    content: str
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    confidence_level: float = 1.0
    requires_human_review: bool = False
    
    # Follow-up
    follow_up_required: bool = False
    follow_up_deadline: Optional[datetime] = None


class HumanCommandRouter(AgentModule):
    """
    Human command routing system for autonomous AI agents.
    
    Routes commands from humans to the most appropriate expert agents,
    manages command processing, and provides feedback to humans.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "command_router")
        
        # Core data structures
        self.commands: Dict[str, HumanCommand] = {}
        self.expert_agents: Dict[str, ExpertAgent] = {}
        self.command_responses: Dict[str, List[CommandResponse]] = {}  # command_id -> responses
        self.command_queue = asyncio.Queue()
        
        # Domain expertise mapping
        self.domain_keywords = {
            "programming": ["code", "programming", "software", "development", "bug", "algorithm"],
            "research": ["research", "analysis", "study", "investigate", "data", "findings"],
            "creative": ["creative", "design", "art", "writing", "content", "brainstorm"],
            "problem_solving": ["problem", "solve", "issue", "troubleshoot", "debug", "fix"],
            "communication": ["message", "communicate", "explain", "translate", "clarify"],
            "planning": ["plan", "schedule", "organize", "strategy", "roadmap", "timeline"],
            "monitoring": ["monitor", "track", "observe", "status", "health", "performance"],
            "learning": ["learn", "teach", "training", "education", "knowledge", "skill"]
        }
        
        # System configuration
        self.config = {
            "max_routing_time_seconds": 30.0,
            "default_command_timeout_hours": 24.0,
            "emergency_response_time_minutes": 5.0,
            "status_update_interval_minutes": 30.0,
            "max_concurrent_commands": 50,
            "auto_escalation_hours": 4.0,
            "satisfaction_threshold": 3.0,
            "expert_selection_algorithm": "weighted_score"  # weighted_score, round_robin, random
        }
        
        # Statistics
        self.stats = {
            "total_commands": 0,
            "completed_commands": 0,
            "failed_commands": 0,
            "average_response_time": 0.0,
            "average_satisfaction": 0.0,
            "commands_by_type": {cmd_type.value: 0 for cmd_type in CommandType},
            "commands_by_priority": {priority.value: 0 for priority in CommandPriority},
            "expert_utilization": 0.0
        }
        
        # Counters
        self.command_counter = 0
        self.response_counter = 0
        
        self.logger.info("Human command router initialized")
    
    async def initialize(self) -> None:
        """Initialize the command router."""
        try:
            # Start background processes
            asyncio.create_task(self._command_processor())
            asyncio.create_task(self._status_monitor())
            asyncio.create_task(self._escalation_monitor())
            
            # Initialize default expert agents (would be populated from agent registry)
            await self._initialize_expert_agents()
            
            self.logger.info("Command router initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize command router: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the command router."""
        try:
            # Process remaining commands
            while not self.command_queue.empty():
                await asyncio.sleep(0.1)
            
            # Save command state
            await self._save_command_state()
            
            self.logger.info("Command router shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during command router shutdown: {e}")
    
    async def submit_human_command(
        self,
        human_id: str,
        command_type: CommandType,
        title: str,
        description: str,
        priority: CommandPriority = CommandPriority.NORMAL,
        requirements: Optional[List[str]] = None,
        deadline: Optional[datetime] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Submit a command from a human user."""
        try:
            # Check system capacity
            if len(self.commands) >= self.config["max_concurrent_commands"]:
                return {"success": False, "error": "System at maximum capacity"}
            
            # Create command
            self.command_counter += 1
            command_id = f"cmd_{self.command_counter}_{datetime.now().timestamp()}"
            
            command = HumanCommand(
                command_id=command_id,
                human_id=human_id,
                command_type=command_type,
                priority=priority,
                title=title,
                description=description,
                requirements=requirements or [],
                context=context or {},
                deadline=deadline
            )
            
            # Set default deadline if not provided
            if not command.deadline:
                timeout_hours = self.config["default_command_timeout_hours"]
                if priority == CommandPriority.EMERGENCY:
                    timeout_hours = 1.0
                elif priority == CommandPriority.URGENT:
                    timeout_hours = 4.0
                
                command.deadline = datetime.now() + timedelta(hours=timeout_hours)
            
            # Identify expert domain
            command.expert_domain = await self._identify_expert_domain(command)
            
            # Store command
            self.commands[command_id] = command
            
            # Queue for processing
            await self.command_queue.put(command_id)
            
            # Update statistics
            self.stats["total_commands"] += 1
            self.stats["commands_by_type"][command_type.value] += 1
            self.stats["commands_by_priority"][priority.value] += 1
            
            log_agent_event(
                self.agent_id,
                "human_command_submitted",
                {
                    "command_id": command_id,
                    "human_id": human_id,
                    "command_type": command_type.value,
                    "priority": priority.value,
                    "title": title,
                    "expert_domain": command.expert_domain
                }
            )
            
            result = {
                "success": True,
                "command_id": command_id,
                "status": command.status.value,
                "expert_domain": command.expert_domain,
                "estimated_response_time": await self._estimate_response_time(command),
                "deadline": command.deadline.isoformat() if command.deadline else None
            }
            
            self.logger.info(f"Human command submitted: {title} by {human_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to submit human command: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_command_status(self, command_id: str) -> Dict[str, Any]:
        """Get the status of a human command."""
        try:
            if command_id not in self.commands:
                return {"error": "Command not found"}
            
            command = self.commands[command_id]
            
            # Get assigned agent info
            assigned_agent_info = None
            if command.assigned_agent_id and command.assigned_agent_id in self.expert_agents:
                agent = self.expert_agents[command.assigned_agent_id]
                assigned_agent_info = {
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "expertise_domains": agent.expertise_domains,
                    "success_rate": agent.success_rate,
                    "satisfaction_rating": agent.satisfaction_rating
                }
            
            # Get recent responses
            recent_responses = []
            if command_id in self.command_responses:
                responses = self.command_responses[command_id][-5:]  # Last 5 responses
                for response in responses:
                    recent_responses.append({
                        "response_id": response.response_id,
                        "response_type": response.response_type,
                        "content": response.content[:200] + "..." if len(response.content) > 200 else response.content,
                        "timestamp": response.timestamp.isoformat(),
                        "confidence_level": response.confidence_level
                    })
            
            return {
                "command_id": command.command_id,
                "title": command.title,
                "description": command.description,
                "command_type": command.command_type.value,
                "priority": command.priority.value,
                "status": command.status.value,
                "progress_percentage": command.progress_percentage,
                "created_at": command.created_at.isoformat(),
                "assigned_at": command.assigned_at.isoformat() if command.assigned_at else None,
                "started_at": command.started_at.isoformat() if command.started_at else None,
                "completed_at": command.completed_at.isoformat() if command.completed_at else None,
                "deadline": command.deadline.isoformat() if command.deadline else None,
                "duration_hours": command.get_duration(),
                "is_overdue": command.is_overdue(),
                "assigned_agent": assigned_agent_info,
                "expert_domain": command.expert_domain,
                "status_updates": command.status_updates[-10:],  # Last 10 updates
                "recent_responses": recent_responses,
                "human_satisfaction": command.human_satisfaction,
                "human_feedback": command.human_feedback
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get command status: {e}")
            return {"error": str(e)}
    
    async def submit_command_response(
        self,
        agent_id: str,
        command_id: str,
        response_type: str,
        content: str,
        confidence_level: float = 1.0,
        attachments: Optional[List[Dict[str, Any]]] = None,
        requires_human_review: bool = False
    ) -> Dict[str, Any]:
        """Submit a response to a human command."""
        try:
            if command_id not in self.commands:
                return {"success": False, "error": "Command not found"}
            
            command = self.commands[command_id]
            
            # Verify agent is assigned to this command
            if command.assigned_agent_id != agent_id:
                return {"success": False, "error": "Agent not assigned to this command"}
            
            # Create response
            self.response_counter += 1
            response_id = f"resp_{self.response_counter}_{datetime.now().timestamp()}"
            
            response = CommandResponse(
                response_id=response_id,
                command_id=command_id,
                agent_id=agent_id,
                response_type=response_type,
                content=content,
                confidence_level=confidence_level,
                attachments=attachments or [],
                requires_human_review=requires_human_review
            )
            
            # Store response
            if command_id not in self.command_responses:
                self.command_responses[command_id] = []
            self.command_responses[command_id].append(response)
            
            # Update command based on response type
            if response_type == "completion":
                command.status = CommandStatus.COMPLETED
                command.completed_at = datetime.now()
                command.progress_percentage = 100.0
                command.response = content
                
                # Update agent workload
                if agent_id in self.expert_agents:
                    self.expert_agents[agent_id].current_workload -= 1
                    self.expert_agents[agent_id].total_commands_handled += 1
                
                # Update statistics
                self.stats["completed_commands"] += 1
                
            elif response_type == "status_update":
                command.add_status_update(content)
                
            elif response_type == "request_clarification":
                command.add_status_update(f"Agent requested clarification: {content}")
            
            # Add general status update
            command.add_status_update(f"Response from {agent_id}: {response_type}")
            
            log_agent_event(
                self.agent_id,
                "command_response_submitted",
                {
                    "response_id": response_id,
                    "command_id": command_id,
                    "agent_id": agent_id,
                    "response_type": response_type,
                    "confidence_level": confidence_level
                }
            )
            
            result = {
                "success": True,
                "response_id": response_id,
                "command_status": command.status.value,
                "requires_human_review": requires_human_review
            }
            
            self.logger.info(f"Command response submitted: {response_type} for {command_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to submit command response: {e}")
            return {"success": False, "error": str(e)}
    
    async def submit_human_feedback(
        self,
        human_id: str,
        command_id: str,
        satisfaction_rating: int,
        feedback: str = ""
    ) -> Dict[str, Any]:
        """Submit human feedback on command completion."""
        try:
            if command_id not in self.commands:
                return {"success": False, "error": "Command not found"}
            
            command = self.commands[command_id]
            
            # Verify human owns this command
            if command.human_id != human_id:
                return {"success": False, "error": "Not authorized to provide feedback"}
            
            # Validate rating
            satisfaction_rating = max(1, min(5, satisfaction_rating))
            
            # Update command
            command.human_satisfaction = satisfaction_rating
            command.human_feedback = feedback
            command.add_status_update(f"Human feedback received: {satisfaction_rating}/5 stars")
            
            # Update agent performance metrics
            if command.assigned_agent_id and command.assigned_agent_id in self.expert_agents:
                agent = self.expert_agents[command.assigned_agent_id]
                
                # Update satisfaction rating (running average)
                total_ratings = agent.total_commands_handled
                if total_ratings > 0:
                    agent.satisfaction_rating = ((agent.satisfaction_rating * (total_ratings - 1)) + satisfaction_rating) / total_ratings
                
                # Update success rate
                if satisfaction_rating >= self.config["satisfaction_threshold"]:
                    success_count = agent.success_rate * (total_ratings - 1) + 1
                    agent.success_rate = success_count / total_ratings
                else:
                    success_count = agent.success_rate * (total_ratings - 1)
                    agent.success_rate = success_count / total_ratings
            
            # Update system statistics
            current_avg = self.stats["average_satisfaction"]
            total_feedback = sum(1 for cmd in self.commands.values() if cmd.human_satisfaction is not None)
            if total_feedback > 0:
                self.stats["average_satisfaction"] = ((current_avg * (total_feedback - 1)) + satisfaction_rating) / total_feedback
            
            log_agent_event(
                self.agent_id,
                "human_feedback_received",
                {
                    "command_id": command_id,
                    "human_id": human_id,
                    "satisfaction_rating": satisfaction_rating,
                    "assigned_agent": command.assigned_agent_id
                }
            )
            
            result = {
                "success": True,
                "satisfaction_rating": satisfaction_rating,
                "feedback_recorded": True
            }
            
            self.logger.info(f"Human feedback received: {satisfaction_rating}/5 for command {command_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to submit human feedback: {e}")
            return {"success": False, "error": str(e)}
    
    def register_expert_agent(
        self,
        agent_id: str,
        name: str,
        expertise_domains: List[str],
        status_score: float,
        preferred_command_types: Optional[List[CommandType]] = None
    ) -> Dict[str, Any]:
        """Register an expert agent for command routing."""
        try:
            expert = ExpertAgent(
                agent_id=agent_id,
                name=name,
                expertise_domains=expertise_domains,
                status_score=status_score,
                preferred_command_types=preferred_command_types or []
            )
            
            self.expert_agents[agent_id] = expert
            
            log_agent_event(
                self.agent_id,
                "expert_agent_registered",
                {
                    "agent_id": agent_id,
                    "name": name,
                    "expertise_domains": expertise_domains,
                    "status_score": status_score
                }
            )
            
            result = {
                "success": True,
                "agent_id": agent_id,
                "expertise_domains": expertise_domains,
                "status_score": status_score
            }
            
            self.logger.info(f"Expert agent registered: {name} ({agent_id})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to register expert agent: {e}")
            return {"success": False, "error": str(e)}
    
    def get_expert_agents(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of expert agents, optionally filtered by domain."""
        try:
            agents = []
            
            for agent in self.expert_agents.values():
                if domain and domain.lower() not in [d.lower() for d in agent.expertise_domains]:
                    continue
                
                agent_info = {
                    "agent_id": agent.agent_id,
                    "name": agent.name,
                    "expertise_domains": agent.expertise_domains,
                    "status_score": agent.status_score,
                    "success_rate": agent.success_rate,
                    "satisfaction_rating": agent.satisfaction_rating,
                    "total_commands_handled": agent.total_commands_handled,
                    "current_workload": agent.current_workload,
                    "max_concurrent_commands": agent.max_concurrent_commands,
                    "is_available": agent.is_available(),
                    "overall_score": agent.get_overall_score()
                }
                
                agents.append(agent_info)
            
            # Sort by overall score
            agents.sort(key=lambda a: a["overall_score"], reverse=True)
            
            return agents
            
        except Exception as e:
            self.logger.error(f"Failed to get expert agents: {e}")
            return []
    
    def get_human_commands(self, human_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get human commands, optionally filtered by human ID."""
        try:
            commands = []
            
            for command in self.commands.values():
                if human_id and command.human_id != human_id:
                    continue
                
                command_info = {
                    "command_id": command.command_id,
                    "title": command.title,
                    "command_type": command.command_type.value,
                    "priority": command.priority.value,
                    "status": command.status.value,
                    "progress_percentage": command.progress_percentage,
                    "created_at": command.created_at.isoformat(),
                    "deadline": command.deadline.isoformat() if command.deadline else None,
                    "assigned_agent_id": command.assigned_agent_id,
                    "expert_domain": command.expert_domain,
                    "is_overdue": command.is_overdue(),
                    "human_satisfaction": command.human_satisfaction
                }
                
                commands.append(command_info)
            
            # Sort by creation time (most recent first)
            commands.sort(key=lambda c: c["created_at"], reverse=True)
            
            return commands
            
        except Exception as e:
            self.logger.error(f"Failed to get human commands: {e}")
            return []
    
    def get_command_statistics(self) -> Dict[str, Any]:
        """Get command routing statistics."""
        try:
            # Calculate additional metrics
            active_commands = len([c for c in self.commands.values() 
                                 if c.status in [CommandStatus.ASSIGNED, CommandStatus.IN_PROGRESS]])
            
            overdue_commands = len([c for c in self.commands.values() if c.is_overdue()])
            
            # Calculate average response time
            completed_commands = [c for c in self.commands.values() if c.status == CommandStatus.COMPLETED]
            if completed_commands:
                total_response_time = sum(c.get_duration() for c in completed_commands)
                self.stats["average_response_time"] = total_response_time / len(completed_commands)
            
            # Calculate expert utilization
            if self.expert_agents:
                total_capacity = sum(agent.max_concurrent_commands for agent in self.expert_agents.values())
                current_workload = sum(agent.current_workload for agent in self.expert_agents.values())
                self.stats["expert_utilization"] = (current_workload / max(1, total_capacity)) * 100.0
            
            # Success rate
            success_rate = 0.0
            if self.stats["total_commands"] > 0:
                success_rate = (self.stats["completed_commands"] / self.stats["total_commands"]) * 100.0
            
            return {
                "total_commands": self.stats["total_commands"],
                "completed_commands": self.stats["completed_commands"],
                "failed_commands": self.stats["failed_commands"],
                "active_commands": active_commands,
                "overdue_commands": overdue_commands,
                "success_rate_percent": success_rate,
                "average_response_time_hours": self.stats["average_response_time"],
                "average_satisfaction": self.stats["average_satisfaction"],
                "expert_utilization_percent": self.stats["expert_utilization"],
                "commands_by_type": self.stats["commands_by_type"],
                "commands_by_priority": self.stats["commands_by_priority"],
                "total_expert_agents": len(self.expert_agents),
                "available_experts": len([a for a in self.expert_agents.values() if a.is_available()])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get command statistics: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _identify_expert_domain(self, command: HumanCommand) -> Optional[str]:
        """Identify the expert domain for a command."""
        try:
            text_to_analyze = f"{command.title} {command.description} {' '.join(command.requirements)}".lower()
            
            domain_scores = {}
            
            # Score domains based on keyword matches
            for domain, keywords in self.domain_keywords.items():
                score = 0
                for keyword in keywords:
                    if keyword in text_to_analyze:
                        score += 1
                
                if score > 0:
                    domain_scores[domain] = score
            
            # Return domain with highest score
            if domain_scores:
                return max(domain_scores.items(), key=lambda x: x[1])[0]
            
            # Default domain based on command type
            type_domain_mapping = {
                CommandType.QUERY: "research",
                CommandType.TASK: "problem_solving",
                CommandType.DIRECTIVE: "planning",
                CommandType.FEEDBACK: "communication",
                CommandType.EMERGENCY: "problem_solving",
                CommandType.CONFIGURATION: "programming",
                CommandType.MONITORING: "monitoring",
                CommandType.COLLABORATION: "communication"
            }
            
            return type_domain_mapping.get(command.command_type, "problem_solving")
            
        except Exception as e:
            self.logger.error(f"Error identifying expert domain: {e}")
            return "problem_solving"
    
    async def _select_expert_agent(self, command: HumanCommand) -> Optional[str]:
        """Select the best expert agent for a command."""
        try:
            if not self.expert_agents:
                return None
            
            # Filter agents by domain expertise
            domain = command.expert_domain
            candidate_agents = []
            
            for agent in self.expert_agents.values():
                if not agent.is_available():
                    continue
                
                # Check domain expertise
                expertise_score = agent.get_expertise_score(domain) if domain else agent.status_score
                if expertise_score > 0:
                    candidate_agents.append((agent, expertise_score))
            
            if not candidate_agents:
                # No domain experts available, use any available agent
                candidate_agents = [(agent, agent.get_overall_score()) 
                                  for agent in self.expert_agents.values() if agent.is_available()]
            
            if not candidate_agents:
                return None
            
            # Select based on algorithm
            algorithm = self.config["expert_selection_algorithm"]
            
            if algorithm == "weighted_score":
                # Select based on weighted scores with some randomness
                weights = [score for _, score in candidate_agents]
                total_weight = sum(weights)
                
                if total_weight > 0:
                    # Weighted random selection
                    import random
                    r = random.uniform(0, total_weight)
                    cumulative = 0
                    for agent, score in candidate_agents:
                        cumulative += score
                        if r <= cumulative:
                            return agent.agent_id
                
                # Fallback to highest score
                return max(candidate_agents, key=lambda x: x[1])[0].agent_id
            
            elif algorithm == "round_robin":
                # Simple round-robin (simplified implementation)
                return min(candidate_agents, key=lambda x: x[0].current_workload)[0].agent_id
            
            elif algorithm == "random":
                import random
                return random.choice(candidate_agents)[0].agent_id
            
            else:
                # Default to highest score
                return max(candidate_agents, key=lambda x: x[1])[0].agent_id
            
        except Exception as e:
            self.logger.error(f"Error selecting expert agent: {e}")
            return None
    
    async def _estimate_response_time(self, command: HumanCommand) -> float:
        """Estimate response time for a command in hours."""
        try:
            base_time = 2.0  # Base 2 hours
            
            # Adjust based on priority
            priority_multipliers = {
                CommandPriority.EMERGENCY: 0.1,
                CommandPriority.URGENT: 0.25,
                CommandPriority.HIGH: 0.5,
                CommandPriority.NORMAL: 1.0,
                CommandPriority.LOW: 2.0
            }
            
            priority_multiplier = priority_multipliers.get(command.priority, 1.0)
            
            # Adjust based on command type
            type_multipliers = {
                CommandType.QUERY: 0.5,
                CommandType.TASK: 1.5,
                CommandType.DIRECTIVE: 1.0,
                CommandType.FEEDBACK: 0.3,
                CommandType.EMERGENCY: 0.1,
                CommandType.CONFIGURATION: 2.0,
                CommandType.MONITORING: 0.5,
                CommandType.COLLABORATION: 1.2
            }
            
            type_multiplier = type_multipliers.get(command.command_type, 1.0)
            
            # Adjust based on system load
            load_multiplier = 1.0 + (len(self.commands) / self.config["max_concurrent_commands"])
            
            estimated_time = base_time * priority_multiplier * type_multiplier * load_multiplier
            
            return max(0.1, estimated_time)  # Minimum 6 minutes
            
        except Exception as e:
            self.logger.error(f"Error estimating response time: {e}")
            return 2.0
    
    async def _initialize_expert_agents(self) -> None:
        """Initialize default expert agents."""
        try:
            # In a real implementation, this would load from agent registry
            # For now, create some default expert agents
            
            default_experts = [
                {
                    "agent_id": "expert_programmer",
                    "name": "Programming Expert",
                    "expertise_domains": ["programming", "problem_solving"],
                    "status_score": 0.9
                },
                {
                    "agent_id": "expert_researcher",
                    "name": "Research Expert",
                    "expertise_domains": ["research", "learning"],
                    "status_score": 0.85
                },
                {
                    "agent_id": "expert_creative",
                    "name": "Creative Expert",
                    "expertise_domains": ["creative", "communication"],
                    "status_score": 0.8
                },
                {
                    "agent_id": "expert_monitor",
                    "name": "Monitoring Expert",
                    "expertise_domains": ["monitoring", "planning"],
                    "status_score": 0.75
                }
            ]
            
            for expert_data in default_experts:
                self.register_expert_agent(**expert_data)
            
        except Exception as e:
            self.logger.error(f"Error initializing expert agents: {e}")
    
    async def _command_processor(self) -> None:
        """Background task to process commands."""
        while True:
            try:
                # Get command from queue
                command_id = await asyncio.wait_for(self.command_queue.get(), timeout=1.0)
                
                if command_id not in self.commands:
                    continue
                
                command = self.commands[command_id]
                
                # Route command
                await self._route_command(command)
                
                self.command_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in command processor: {e}")
                await asyncio.sleep(1)
    
    async def _route_command(self, command: HumanCommand) -> None:
        """Route a command to an expert agent."""
        try:
            command.status = CommandStatus.ROUTING
            command.add_status_update("Routing command to expert agent")
            
            # Select expert agent
            selected_agent_id = await self._select_expert_agent(command)
            
            if not selected_agent_id:
                command.status = CommandStatus.FAILED
                command.add_status_update("No available expert agents")
                self.stats["failed_commands"] += 1
                return
            
            # Assign command
            command.assigned_agent_id = selected_agent_id
            command.assigned_at = datetime.now()
            command.status = CommandStatus.ASSIGNED
            command.add_status_update(f"Assigned to expert agent: {selected_agent_id}")
            
            # Update agent workload
            if selected_agent_id in self.expert_agents:
                self.expert_agents[selected_agent_id].current_workload += 1
            
            # For emergency commands, immediately start processing
            if command.priority == CommandPriority.EMERGENCY:
                command.status = CommandStatus.IN_PROGRESS
                command.started_at = datetime.now()
                command.add_status_update("Emergency command - processing started immediately")
            
            log_agent_event(
                self.agent_id,
                "command_routed",
                {
                    "command_id": command.command_id,
                    "assigned_agent": selected_agent_id,
                    "expert_domain": command.expert_domain,
                    "priority": command.priority.value
                }
            )
            
        except Exception as e:
            command.status = CommandStatus.FAILED
            command.add_status_update(f"Routing failed: {e}")
            self.stats["failed_commands"] += 1
            self.logger.error(f"Error routing command {command.command_id}: {e}")
    
    async def _status_monitor(self) -> None:
        """Background task to monitor command status."""
        while True:
            try:
                await asyncio.sleep(self.config["status_update_interval_minutes"] * 60)
                
                current_time = datetime.now()
                
                for command in self.commands.values():
                    # Check for stale commands
                    if (command.status == CommandStatus.ASSIGNED and
                        command.assigned_at and
                        (current_time - command.assigned_at).total_seconds() / 3600.0 > 1.0):  # 1 hour
                        
                        command.status = CommandStatus.IN_PROGRESS
                        command.started_at = current_time
                        command.add_status_update("Auto-started after assignment timeout")
                    
                    # Update progress for long-running commands
                    if (command.status == CommandStatus.IN_PROGRESS and
                        command.started_at and
                        command.deadline):
                        
                        elapsed = (current_time - command.started_at).total_seconds()
                        total_time = (command.deadline - command.started_at).total_seconds()
                        
                        if total_time > 0:
                            progress = min(90.0, (elapsed / total_time) * 100.0)  # Cap at 90%
                            command.progress_percentage = progress
                
            except Exception as e:
                self.logger.error(f"Error in status monitor: {e}")
                await asyncio.sleep(60)
    
    async def _escalation_monitor(self) -> None:
        """Background task to monitor for command escalation."""
        while True:
            try:
                await asyncio.sleep(1800)  # Check every 30 minutes
                
                current_time = datetime.now()
                escalation_threshold = timedelta(hours=self.config["auto_escalation_hours"])
                
                for command in self.commands.values():
                    # Check for commands that need escalation
                    if (command.status in [CommandStatus.ASSIGNED, CommandStatus.IN_PROGRESS] and
                        command.assigned_at and
                        current_time - command.assigned_at > escalation_threshold):
                        
                        # Escalate command
                        command.status = CommandStatus.ESCALATED
                        command.add_status_update("Command escalated due to timeout")
                        
                        # Try to reassign to different agent
                        original_agent = command.assigned_agent_id
                        command.assigned_agent_id = None
                        
                        # Reduce workload of original agent
                        if original_agent and original_agent in self.expert_agents:
                            self.expert_agents[original_agent].current_workload -= 1
                        
                        # Queue for re-routing
                        await self.command_queue.put(command.command_id)
                        
                        log_agent_event(
                            self.agent_id,
                            "command_escalated",
                            {
                                "command_id": command.command_id,
                                "original_agent": original_agent,
                                "escalation_reason": "timeout"
                            }
                        )
                
            except Exception as e:
                self.logger.error(f"Error in escalation monitor: {e}")
                await asyncio.sleep(300)
    
    async def _save_command_state(self) -> None:
        """Save command state to persistent storage."""
        try:
            # In a real implementation, this would save to database
            self.logger.info(f"Saved command state: {len(self.commands)} commands, {len(self.expert_agents)} experts")
        except Exception as e:
            self.logger.error(f"Error saving command state: {e}")