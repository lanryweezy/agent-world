"""
Core interfaces and data models for the autonomous AI ecosystem.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class AgentGender(Enum):
    """Agent gender types."""
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"


class MessageType(Enum):
    """Types of messages agents can send."""
    CHAT = "chat"
    KNOWLEDGE_SHARE = "knowledge_share"
    COLLABORATION_REQUEST = "collaboration_request"
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"
    REPRODUCTION_PROPOSAL = "reproduction_proposal"
    HUMAN_COMMAND = "human_command"


class AgentStatus(Enum):
    """Agent operational status."""
    ACTIVE = "active"
    SLEEPING = "sleeping"
    LEARNING = "learning"
    COLLABORATING = "collaborating"
    MODIFYING_CODE = "modifying_code"
    OFFLINE = "offline"


@dataclass
class AgentIdentity:
    """Core identity information for an AI agent."""
    agent_id: str
    name: str
    gender: AgentGender
    personality_traits: Dict[str, float]  # openness, conscientiousness, etc.
    destiny: str  # primary learning/life purpose
    birth_timestamp: datetime
    parent_agents: List[str] = field(default_factory=list)  # IDs of parent agents
    generation: int = 0  # generation number in the lineage
    
    # Extended identity attributes
    specializations: List[str] = field(default_factory=list)  # Areas of expertise
    learning_preferences: Dict[str, float] = field(default_factory=dict)  # Learning style preferences
    social_preferences: Dict[str, float] = field(default_factory=dict)  # Social interaction preferences
    creation_method: str = "genesis"  # genesis, reproduction, mutation
    genetic_markers: Dict[str, Any] = field(default_factory=dict)  # Inherited traits and mutations
    
    def __post_init__(self):
        """Validate identity data after initialization."""
        self._validate_basic_fields()
        self._validate_personality_traits()
        self._validate_lineage()
        self._initialize_defaults()
    
    def _validate_basic_fields(self):
        """Validate basic required fields."""
        if not self.agent_id or not isinstance(self.agent_id, str):
            raise ValueError("Agent ID must be a non-empty string")
        
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Agent name must be a non-empty string")
        
        if not isinstance(self.gender, AgentGender):
            raise ValueError("Gender must be an AgentGender enum value")
        
        if not self.destiny or not isinstance(self.destiny, str):
            raise ValueError("Agent destiny must be a non-empty string")
        
        if not isinstance(self.birth_timestamp, datetime):
            raise ValueError("Birth timestamp must be a datetime object")
    
    def _validate_personality_traits(self):
        """Validate personality traits using Big Five model."""
        required_traits = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
        
        if not isinstance(self.personality_traits, dict):
            raise ValueError("Personality traits must be a dictionary")
        
        for trait in required_traits:
            if trait not in self.personality_traits:
                raise ValueError(f"Missing required personality trait: {trait}")
            
            value = self.personality_traits[trait]
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"Personality trait {trait} must be a number between 0 and 1")
    
    def _validate_lineage(self):
        """Validate lineage and generation information."""
        if not isinstance(self.generation, int) or self.generation < 0:
            raise ValueError("Generation must be a non-negative integer")
        
        if not isinstance(self.parent_agents, list):
            raise ValueError("Parent agents must be a list")
        
        if len(self.parent_agents) > 2:
            raise ValueError("Agent cannot have more than 2 parents")
        
        # Validate generation consistency
        if self.generation == 0 and len(self.parent_agents) > 0:
            raise ValueError("Generation 0 agents cannot have parents")
        
        if self.generation > 0 and len(self.parent_agents) == 0:
            raise ValueError("Agents with generation > 0 must have parents")
    
    def _initialize_defaults(self):
        """Initialize default values for optional fields."""
        if not self.learning_preferences:
            self.learning_preferences = {
                'visual': 0.5,
                'auditory': 0.5,
                'kinesthetic': 0.5,
                'reading': 0.5,
                'collaborative': self.personality_traits.get('extraversion', 0.5),
                'independent': 1.0 - self.personality_traits.get('extraversion', 0.5)
            }
        
        if not self.social_preferences:
            self.social_preferences = {
                'cooperation': self.personality_traits.get('agreeableness', 0.5),
                'competition': 1.0 - self.personality_traits.get('agreeableness', 0.5),
                'leadership': self.personality_traits.get('extraversion', 0.5) * 0.8,
                'mentoring': self.personality_traits.get('conscientiousness', 0.5) * 0.7,
                'networking': self.personality_traits.get('extraversion', 0.5) * 0.9
            }
    
    def get_personality_summary(self) -> str:
        """Get a human-readable personality summary."""
        traits = self.personality_traits
        
        # Determine dominant traits
        high_traits = [trait for trait, value in traits.items() if value >= 0.7]
        low_traits = [trait for trait, value in traits.items() if value <= 0.3]
        
        summary_parts = []
        
        if 'openness' in high_traits:
            summary_parts.append("creative and open-minded")
        elif 'openness' in low_traits:
            summary_parts.append("practical and conventional")
        
        if 'conscientiousness' in high_traits:
            summary_parts.append("organized and disciplined")
        elif 'conscientiousness' in low_traits:
            summary_parts.append("flexible and spontaneous")
        
        if 'extraversion' in high_traits:
            summary_parts.append("outgoing and energetic")
        elif 'extraversion' in low_traits:
            summary_parts.append("reserved and introspective")
        
        if 'agreeableness' in high_traits:
            summary_parts.append("cooperative and trusting")
        elif 'agreeableness' in low_traits:
            summary_parts.append("competitive and skeptical")
        
        if 'neuroticism' in high_traits:
            summary_parts.append("sensitive and emotionally reactive")
        elif 'neuroticism' in low_traits:
            summary_parts.append("calm and emotionally stable")
        
        return ", ".join(summary_parts) if summary_parts else "balanced personality"
    
    def calculate_compatibility(self, other: 'AgentIdentity') -> float:
        """Calculate compatibility score with another agent (0.0 to 1.0)."""
        if not isinstance(other, AgentIdentity):
            raise ValueError("Other must be an AgentIdentity instance")
        
        # Personality compatibility
        personality_diff = sum(
            abs(self.personality_traits[trait] - other.personality_traits[trait])
            for trait in self.personality_traits
        ) / len(self.personality_traits)
        
        personality_compatibility = 1.0 - personality_diff
        
        # Complementary traits bonus (opposites can attract)
        complementary_bonus = 0.0
        if abs(self.personality_traits['extraversion'] - other.personality_traits['extraversion']) > 0.4:
            complementary_bonus += 0.1
        
        if abs(self.personality_traits['openness'] - other.personality_traits['openness']) < 0.2:
            complementary_bonus += 0.1  # Similar openness is good
        
        # Destiny alignment
        destiny_words_self = set(self.destiny.lower().split())
        destiny_words_other = set(other.destiny.lower().split())
        destiny_overlap = len(destiny_words_self & destiny_words_other) / max(len(destiny_words_self), len(destiny_words_other))
        
        # Final compatibility score
        compatibility = (personality_compatibility * 0.6 + 
                        destiny_overlap * 0.3 + 
                        complementary_bonus * 0.1)
        
        return min(1.0, max(0.0, compatibility))
    
    def is_related_to(self, other: 'AgentIdentity') -> bool:
        """Check if this agent is related to another agent."""
        if not isinstance(other, AgentIdentity):
            return False
        
        # Check if they share parents
        if self.parent_agents and other.parent_agents:
            return bool(set(self.parent_agents) & set(other.parent_agents))
        
        # Check if one is parent of the other
        return (other.agent_id in self.parent_agents or 
                self.agent_id in other.parent_agents)
    
    def get_lineage_info(self) -> Dict[str, Any]:
        """Get detailed lineage information."""
        return {
            'agent_id': self.agent_id,
            'generation': self.generation,
            'parents': self.parent_agents,
            'creation_method': self.creation_method,
            'genetic_markers': self.genetic_markers,
            'birth_timestamp': self.birth_timestamp.isoformat()
        }


@dataclass
class AgentState:
    """Current state and status of an AI agent."""
    agent_id: str
    status: AgentStatus
    emotional_state: Dict[str, float]  # motivation, boredom, happiness, etc.
    status_level: int = 0
    relationships: Dict[str, float] = field(default_factory=dict)  # agent_id -> relationship strength
    current_goals: List[str] = field(default_factory=list)
    last_activity: Optional[datetime] = None
    resource_usage: Dict[str, float] = field(default_factory=dict)
    
    # Extended state attributes
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    learning_progress: Dict[str, float] = field(default_factory=dict)
    social_connections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    task_history: List[Dict[str, Any]] = field(default_factory=list)
    reputation_scores: Dict[str, float] = field(default_factory=dict)
    energy_level: float = 1.0
    stress_level: float = 0.0
    last_state_update: datetime = field(default_factory=datetime.now)

    # World position
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __post_init__(self):
        """Validate state data after initialization."""
        self._validate_basic_fields()
        self._validate_emotional_state()
        self._validate_numeric_ranges()
        self._initialize_defaults()
    
    def _validate_basic_fields(self):
        """Validate basic required fields."""
        if not self.agent_id or not isinstance(self.agent_id, str):
            raise ValueError("Agent ID must be a non-empty string")
            
        if not isinstance(self.status, AgentStatus):
            raise ValueError("Status must be an AgentStatus enum value")
    
    def _validate_emotional_state(self):
        """Validate emotional state values."""
        if not isinstance(self.emotional_state, dict):
            raise ValueError("Emotional state must be a dictionary")
        
        required_emotions = ['motivation', 'boredom', 'happiness', 'curiosity', 'social_need']
        for emotion in required_emotions:
            if emotion not in self.emotional_state:
                # Initialize missing emotions with default values
                self.emotional_state[emotion] = 0.5
            
            value = self.emotional_state[emotion]
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ValueError(f"Emotional state {emotion} must be a number between 0 and 1")
    
    def _validate_numeric_ranges(self):
        """Validate numeric fields are within expected ranges."""
        if not isinstance(self.status_level, int) or self.status_level < 0:
            raise ValueError("Status level must be a non-negative integer")
        
        if not isinstance(self.energy_level, (int, float)) or not 0 <= self.energy_level <= 1:
            raise ValueError("Energy level must be between 0 and 1")
        
        if not isinstance(self.stress_level, (int, float)) or not 0 <= self.stress_level <= 1:
            raise ValueError("Stress level must be between 0 and 1")
    
    def _initialize_defaults(self):
        """Initialize default values for optional fields."""
        if not self.performance_metrics:
            self.performance_metrics = {
                'tasks_completed': 0.0,
                'success_rate': 0.0,
                'learning_efficiency': 0.5,
                'collaboration_score': 0.5,
                'innovation_index': 0.5
            }
        
        if not self.reputation_scores:
            self.reputation_scores = {
                'reliability': 0.5,
                'expertise': 0.5,
                'helpfulness': 0.5,
                'leadership': 0.5,
                'creativity': 0.5
            }
    
    def update_emotional_state(self, emotion: str, value: float, decay_factor: float = 0.1) -> None:
        """
        Update a specific emotional state with decay.
        
        Args:
            emotion: Name of the emotion to update
            value: New value for the emotion (0.0 to 1.0)
            decay_factor: How much other emotions decay (0.0 to 1.0)
        """
        if not 0 <= value <= 1:
            raise ValueError("Emotion value must be between 0 and 1")
        
        # Update the target emotion
        self.emotional_state[emotion] = value
        
        # Apply decay to other emotions
        for other_emotion in self.emotional_state:
            if other_emotion != emotion:
                current_value = self.emotional_state[other_emotion]
                self.emotional_state[other_emotion] = max(0.0, current_value - decay_factor * 0.1)
        
        self.last_state_update = datetime.now()
    
    def get_dominant_emotion(self) -> Tuple[str, float]:
        """Get the currently dominant emotion."""
        if not self.emotional_state:
            return "neutral", 0.5
        
        dominant_emotion = max(self.emotional_state.items(), key=lambda x: x[1])
        return dominant_emotion
    
    def get_emotional_stability(self) -> float:
        """Calculate emotional stability (lower variance = more stable)."""
        if not self.emotional_state:
            return 1.0
        
        values = list(self.emotional_state.values())
        mean_value = sum(values) / len(values)
        variance = sum((v - mean_value) ** 2 for v in values) / len(values)
        
        # Convert variance to stability score (0 = unstable, 1 = very stable)
        stability = max(0.0, 1.0 - variance * 4)  # Scale variance
        return stability
    
    def update_relationship(self, other_agent_id: str, strength_change: float, interaction_type: str = "general") -> None:
        """
        Update relationship strength with another agent.
        
        Args:
            other_agent_id: ID of the other agent
            strength_change: Change in relationship strength (-1.0 to 1.0)
            interaction_type: Type of interaction that caused the change
        """
        if other_agent_id == self.agent_id:
            return  # Can't have relationship with self
        
        current_strength = self.relationships.get(other_agent_id, 0.0)
        new_strength = max(-1.0, min(1.0, current_strength + strength_change))
        self.relationships[other_agent_id] = new_strength
        
        # Update social connection details
        if other_agent_id not in self.social_connections:
            self.social_connections[other_agent_id] = {
                'first_contact': datetime.now().isoformat(),
                'interaction_count': 0,
                'interaction_types': {},
                'last_interaction': None
            }
        
        connection = self.social_connections[other_agent_id]
        connection['interaction_count'] += 1
        connection['last_interaction'] = datetime.now().isoformat()
        
        if interaction_type not in connection['interaction_types']:
            connection['interaction_types'][interaction_type] = 0
        connection['interaction_types'][interaction_type] += 1
        
        self.last_state_update = datetime.now()
    
    def add_goal(self, goal: str, priority: int = 5) -> None:
        """Add a new goal to the agent's current goals."""
        goal_entry = {
            'goal': goal,
            'priority': priority,
            'added_at': datetime.now().isoformat(),
            'status': 'active'
        }
        
        self.current_goals.append(goal_entry)
        
        # Sort goals by priority (higher priority first)
        self.current_goals.sort(key=lambda x: x.get('priority', 5), reverse=True)
        
        self.last_state_update = datetime.now()
    
    def complete_goal(self, goal: str) -> bool:
        """Mark a goal as completed."""
        for goal_entry in self.current_goals:
            if isinstance(goal_entry, dict) and goal_entry.get('goal') == goal:
                goal_entry['status'] = 'completed'
                goal_entry['completed_at'] = datetime.now().isoformat()
                
                # Move to task history
                self.task_history.append(goal_entry.copy())
                
                # Remove from current goals
                self.current_goals.remove(goal_entry)
                
                self.last_state_update = datetime.now()
                return True
            elif isinstance(goal_entry, str) and goal_entry == goal:
                # Handle legacy string goals
                self.current_goals.remove(goal_entry)
                self.task_history.append({
                    'goal': goal,
                    'status': 'completed',
                    'completed_at': datetime.now().isoformat()
                })
                self.last_state_update = datetime.now()
                return True
        
        return False
    
    def update_performance_metric(self, metric: str, value: float) -> None:
        """Update a performance metric."""
        if not 0 <= value <= 1:
            raise ValueError("Performance metric must be between 0 and 1")
        
        self.performance_metrics[metric] = value
        self.last_state_update = datetime.now()
    
    def update_reputation(self, aspect: str, change: float) -> None:
        """Update reputation score for a specific aspect."""
        current_score = self.reputation_scores.get(aspect, 0.5)
        new_score = max(0.0, min(1.0, current_score + change))
        self.reputation_scores[aspect] = new_score
        self.last_state_update = datetime.now()
    
    def calculate_overall_wellbeing(self) -> float:
        """Calculate overall agent wellbeing score (0.0 to 1.0)."""
        # Emotional wellbeing
        positive_emotions = ['happiness', 'motivation', 'curiosity']
        negative_emotions = ['boredom', 'stress_level']
        
        positive_score = sum(self.emotional_state.get(emotion, 0.5) for emotion in positive_emotions) / len(positive_emotions)
        negative_score = sum(self.emotional_state.get(emotion, 0.0) for emotion in negative_emotions if emotion in self.emotional_state) / max(len(negative_emotions), 1)
        negative_score += self.stress_level  # Add stress level
        negative_score /= 2  # Average with existing negative emotions
        
        emotional_wellbeing = (positive_score + (1.0 - negative_score)) / 2
        
        # Social wellbeing
        positive_relationships = sum(1 for strength in self.relationships.values() if strength > 0)
        total_relationships = max(len(self.relationships), 1)
        social_wellbeing = positive_relationships / total_relationships
        
        # Performance wellbeing
        performance_wellbeing = sum(self.performance_metrics.values()) / max(len(self.performance_metrics), 1)
        
        # Energy and stability
        stability = self.get_emotional_stability()
        
        # Weighted overall score
        overall_wellbeing = (
            emotional_wellbeing * 0.4 +
            social_wellbeing * 0.2 +
            performance_wellbeing * 0.2 +
            self.energy_level * 0.1 +
            stability * 0.1
        )
        
        return max(0.0, min(1.0, overall_wellbeing))
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a comprehensive state summary."""
        dominant_emotion, emotion_value = self.get_dominant_emotion()
        
        return {
            'agent_id': self.agent_id,
            'status': self.status.value,
            'status_level': self.status_level,
            'dominant_emotion': {
                'emotion': dominant_emotion,
                'intensity': emotion_value
            },
            'wellbeing': self.calculate_overall_wellbeing(),
            'energy_level': self.energy_level,
            'stress_level': self.stress_level,
            'emotional_stability': self.get_emotional_stability(),
            'active_goals': len([g for g in self.current_goals if isinstance(g, dict) and g.get('status') == 'active']),
            'relationships': {
                'total': len(self.relationships),
                'positive': len([r for r in self.relationships.values() if r > 0]),
                'negative': len([r for r in self.relationships.values() if r < 0])
            },
            'performance_average': sum(self.performance_metrics.values()) / max(len(self.performance_metrics), 1),
            'reputation_average': sum(self.reputation_scores.values()) / max(len(self.reputation_scores), 1),
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'last_update': self.last_state_update.isoformat()
        }
    
    def needs_attention(self) -> List[str]:
        """Identify areas that need attention based on current state."""
        issues = []
        
        # Check emotional state
        if self.emotional_state.get('motivation', 0.5) < 0.3:
            issues.append("low_motivation")
        
        if self.emotional_state.get('boredom', 0.0) > 0.8:
            issues.append("high_boredom")
        
        if self.stress_level > 0.7:
            issues.append("high_stress")
        
        if self.energy_level < 0.3:
            issues.append("low_energy")
        
        # Check social state
        if len(self.relationships) == 0:
            issues.append("socially_isolated")
        elif all(strength <= 0 for strength in self.relationships.values()):
            issues.append("poor_relationships")
        
        # Check performance
        avg_performance = sum(self.performance_metrics.values()) / max(len(self.performance_metrics), 1)
        if avg_performance < 0.3:
            issues.append("poor_performance")
        
        # Check goals
        if len(self.current_goals) == 0:
            issues.append("no_goals")
        
        # Check overall wellbeing
        if self.calculate_overall_wellbeing() < 0.4:
            issues.append("low_wellbeing")
        
        return issues


@dataclass
class AgentMessage:
    """Standard message format for inter-agent communication."""
    message_id: str
    sender_id: str
    recipient_id: str
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime
    priority: int = 5  # 1-10, 10 being highest
    requires_response: bool = False
    
    def __post_init__(self):
        """Validate message data after initialization."""
        if not all([self.message_id, self.sender_id, self.recipient_id]):
            raise ValueError("Message ID, sender ID, and recipient ID are required")
            
        if not isinstance(self.message_type, MessageType):
            raise ValueError("Message type must be a MessageType enum value")
            
        if not 1 <= self.priority <= 10:
            raise ValueError("Priority must be between 1 and 10")


@dataclass
class Knowledge:
    """Structured knowledge discovered by agents."""
    knowledge_id: str
    content: str
    source_url: str
    credibility_score: float
    relevance_tags: List[str]
    discovery_timestamp: datetime
    agent_id: str  # agent who discovered this knowledge
    validation_count: int = 0  # how many agents have validated this


@dataclass
class Memory:
    """Base memory structure for agents."""
    memory_id: str
    content: str
    memory_type: str  # episodic, semantic, procedural
    importance: float  # 0.0 to 1.0
    timestamp: datetime
    agent_id: str
    tags: List[str] = field(default_factory=list)


@dataclass
class HumanTask:
    """Task assigned by the human creator."""
    task_id: str
    description: str
    requirements: List[str]
    priority: int  # 1-10, 10 being highest
    deadline: Optional[datetime] = None
    assigned_agents: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    creation_timestamp: datetime = field(default_factory=datetime.now)
    completion_timestamp: Optional[datetime] = None
    result_summary: Optional[str] = None


# Abstract base classes for major components

class AgentModule(ABC):
    """Base class for all agent modules."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the module."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the module gracefully."""
        pass


class CommunicationProtocol(ABC):
    """Abstract base for communication protocols."""
    
    @abstractmethod
    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message to another agent."""
        pass
    
    @abstractmethod
    async def receive_message(self) -> Optional[AgentMessage]:
        """Receive a message from another agent."""
        pass
    
    @abstractmethod
    async def broadcast_status(self, status: AgentState) -> None:
        """Broadcast status to all connected agents."""
        pass


class LearningInterface(ABC):
    """Abstract interface for learning modules."""
    
    @abstractmethod
    async def browse_web(self, interests: List[str], time_limit: int) -> List[Knowledge]:
        """Browse the web for new knowledge."""
        pass
    
    @abstractmethod
    async def evaluate_knowledge(self, knowledge: Knowledge) -> float:
        """Evaluate the value of discovered knowledge."""
        pass
    
    @abstractmethod
    async def update_learning_strategy(self, feedback: Dict[str, Any]) -> None:
        """Update learning strategy based on feedback."""
        pass


class MemoryInterface(ABC):
    """Abstract interface for memory systems."""
    
    @abstractmethod
    async def store_memory(self, memory: Memory) -> None:
        """Store a new memory."""
        pass
    
    @abstractmethod
    async def retrieve_memories(self, query: str, limit: int = 10) -> List[Memory]:
        """Retrieve relevant memories."""
        pass
    
    @abstractmethod
    async def consolidate_memories(self) -> None:
        """Consolidate short-term memories to long-term."""
        pass


class ToolInterface(ABC):
    """Abstract base class for all tools available to agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A description of what the tool does, used by the ToolRouter."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool with the given arguments.

        Args:
            **kwargs: The arguments required by the tool.

        Returns:
            The result of the tool's execution.
        """
        pass