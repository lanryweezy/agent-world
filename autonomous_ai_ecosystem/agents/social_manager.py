"""
Social relationship management system for autonomous AI agents.

This module implements social relationship tracking, influence calculation,
and command authority systems for agent interactions.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class RelationshipType(Enum):
    """Types of relationships between agents."""
    NEUTRAL = "neutral"
    FRIEND = "friend"
    ALLY = "ally"
    MENTOR = "mentor"
    MENTEE = "mentee"
    RIVAL = "rival"
    COLLABORATOR = "collaborator"
    SUBORDINATE = "subordinate"
    SUPERIOR = "superior"
    ENEMY = "enemy"


class InteractionType(Enum):
    """Types of interactions between agents."""
    MESSAGE = "message"
    COLLABORATION = "collaboration"
    COMPETITION = "competition"
    HELP_REQUEST = "help_request"
    HELP_PROVIDED = "help_provided"
    KNOWLEDGE_SHARE = "knowledge_share"
    CONFLICT = "conflict"
    PRAISE = "praise"
    CRITICISM = "criticism"
    COMMAND = "command"


@dataclass
class SocialRelationship:
    """Represents a relationship between two agents."""
    agent1_id: str
    agent2_id: str
    relationship_type: RelationshipType
    strength: float  # 0.0 to 1.0
    trust_level: float  # 0.0 to 1.0
    respect_level: float  # 0.0 to 1.0
    interaction_count: int = 0
    last_interaction: Optional[datetime] = None
    shared_projects: List[str] = field(default_factory=list)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class SocialInteraction:
    """Represents an interaction between agents."""
    interaction_id: str
    initiator_id: str
    target_id: str
    interaction_type: InteractionType
    content: Dict[str, Any]
    outcome: Optional[str] = None
    satisfaction_score: float = 0.5  # 0.0 to 1.0
    impact_on_relationship: float = 0.0  # -1.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SocialInfluence:
    """Represents social influence metrics for an agent."""
    agent_id: str
    influence_score: float = 0.0
    reputation_score: float = 0.0
    charisma_score: float = 0.0
    leadership_score: float = 0.0
    network_centrality: float = 0.0
    follower_count: int = 0
    following_count: int = 0
    last_calculated: datetime = field(default_factory=datetime.now)


class SocialManager(AgentModule):
    """
    Social relationship management system that tracks relationships,
    calculates influence, and manages social dynamics between agents.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "social_manager")
        
        # Relationship storage
        self.relationships: Dict[Tuple[str, str], SocialRelationship] = {}
        self.interactions: Dict[str, SocialInteraction] = {}
        self.influence_metrics: Dict[str, SocialInfluence] = {}
        
        # Social network graph
        self.social_network: Dict[str, Set[str]] = {}  # agent_id -> connected agents
        
        # Relationship decay parameters
        self.relationship_decay = {
            "decay_rate": 0.98,  # 2% decay per period
            "decay_period_days": 7,
            "minimum_strength": 0.1
        }
        
        # Influence calculation parameters
        self.influence_weights = {
            "relationship_strength": 0.3,
            "interaction_frequency": 0.2,
            "network_position": 0.2,
            "reputation": 0.15,
            "leadership_actions": 0.15
        }
        
        # Statistics
        self.social_stats = {
            "total_relationships": 0,
            "total_interactions": 0,
            "relationship_types": {rt.value: 0 for rt in RelationshipType},
            "interaction_types": {it.value: 0 for it in InteractionType},
            "influence_updates": 0
        }
        
        self.logger.info(f"Social manager initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the social manager."""
        try:
            # Load existing social data
            await self._load_social_data()
            
            # Initialize influence metrics
            await self._initialize_influence_metrics()
            
            self.logger.info("Social manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize social manager: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the social manager gracefully."""
        try:
            # Save social data
            await self._save_social_data()
            
            self.logger.info("Social manager shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during social manager shutdown: {e}")
    
    async def record_interaction(
        self,
        initiator_id: str,
        target_id: str,
        interaction_type: InteractionType,
        content: Dict[str, Any],
        outcome: Optional[str] = None,
        satisfaction_score: float = 0.5
    ) -> str:
        """
        Record an interaction between two agents.
        
        Args:
            initiator_id: ID of the agent who initiated the interaction
            target_id: ID of the target agent
            interaction_type: Type of interaction
            content: Interaction content and details
            outcome: Optional outcome description
            satisfaction_score: Satisfaction level (0.0 to 1.0)
            
        Returns:
            Interaction ID
        """
        try:
            interaction_id = f"interaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.interactions)}"
            
            # Calculate relationship impact
            impact = self._calculate_interaction_impact(interaction_type, satisfaction_score)
            
            # Create interaction record
            interaction = SocialInteraction(
                interaction_id=interaction_id,
                initiator_id=initiator_id,
                target_id=target_id,
                interaction_type=interaction_type,
                content=content,
                outcome=outcome,
                satisfaction_score=satisfaction_score,
                impact_on_relationship=impact
            )
            
            self.interactions[interaction_id] = interaction
            
            # Update relationship
            await self._update_relationship_from_interaction(interaction)
            
            # Update social network
            self._update_social_network(initiator_id, target_id)
            
            # Update statistics
            self.social_stats["total_interactions"] += 1
            self.social_stats["interaction_types"][interaction_type.value] += 1
            
            log_agent_event(
                self.agent_id,
                "social_interaction_recorded",
                {
                    "interaction_id": interaction_id,
                    "initiator": initiator_id,
                    "target": target_id,
                    "type": interaction_type.value,
                    "satisfaction": satisfaction_score,
                    "impact": impact
                }
            )
            
            self.logger.debug(f"Recorded interaction {interaction_id}: {initiator_id} -> {target_id} ({interaction_type.value})")
            
            return interaction_id
            
        except Exception as e:
            self.logger.error(f"Failed to record interaction: {e}")
            raise