"""
Emotion engine and personality system for autonomous AI agents.

This module implements sophisticated emotional state tracking, personality-based
responses, and dynamic emotional evolution based on experiences and interactions.
"""

import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import copy

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class EmotionType(Enum):
    """Core emotion types based on psychological research."""
    MOTIVATION = "motivation"
    BOREDOM = "boredom"
    HAPPINESS = "happiness"
    CURIOSITY = "curiosity"
    SOCIAL_NEED = "social_need"
    ANXIETY = "anxiety"
    CONFIDENCE = "confidence"
    SATISFACTION = "satisfaction"
    FRUSTRATION = "frustration"
    EXCITEMENT = "excitement"


class PersonalityTrait(Enum):
    """Big Five personality traits."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class MoodState(Enum):
    """Overall mood states."""
    EUPHORIC = "euphoric"
    HAPPY = "happy"
    CONTENT = "content"
    NEUTRAL = "neutral"
    MELANCHOLY = "melancholy"
    FRUSTRATED = "frustrated"
    ANXIOUS = "anxious"


@dataclass
class PersonalityProfile:
    """Complete personality profile for an agent."""
    traits: Dict[str, float]  # PersonalityTrait -> value (0.0 to 1.0)
    emotional_stability: float  # 0.0 to 1.0
    social_orientation: float   # 0.0 to 1.0
    learning_preference: float  # 0.0 to 1.0
    risk_tolerance: float       # 0.0 to 1.0
    creativity_level: float     # 0.0 to 1.0
    
    def __post_init__(self):
        """Validate personality profile."""
        for trait, value in self.traits.items():
            if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
                raise ValueError(f"Personality trait {trait} must be between 0.0 and 1.0")


@dataclass
class EmotionalState:
    """Current emotional state of an agent."""
    motivation: float = 0.5
    boredom: float = 0.5
    happiness: float = 0.5
    curiosity: float = 0.5
    social_need: float = 0.5
    anxiety: float = 0.5
    confidence: float = 0.5
    satisfaction: float = 0.5
    frustration: float = 0.5
    excitement: float = 0.5


@dataclass
class EmotionalMemory:
    """Record of an emotional event and its impact."""
    event_id: str
    timestamp: datetime
    emotional_impact: Dict[str, float]
    context: Dict[str, Any]
    intensity: float
    duration: timedelta


@dataclass
class MoodProfile:
    """Mood characteristics based on personality."""
    base_mood: MoodState
    mood_volatility: float  # How quickly moods change
    mood_recovery_rate: float  # How quickly negative moods fade
    positive_bias: float  # Tendency toward positive moods


class EmotionEngine(AgentModule):
    """
    Advanced emotion engine that manages emotional states, personality influence,
    and dynamic emotional evolution based on experiences.
    """
    
    def __init__(self, agent_id: str, personality_traits: Dict[str, float]):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "emotion_engine")
        
        # First create personality profile with just traits
        self.personality = PersonalityProfile(
            traits=personality_traits.copy(),
            emotional_stability=0.0,
            social_orientation=0.0,
            learning_preference=0.0,
            risk_tolerance=0.0,
            creativity_level=0.0
        )
        
        # Now calculate the personality properties
        self.personality.emotional_stability = self._calculate_emotional_stability()
        self.personality.social_orientation = self._calculate_social_orientation()
        self.personality.learning_preference = self._calculate_learning_preference()
        self.personality.risk_tolerance = self._calculate_risk_tolerance()
        self.personality.creativity_level = self._calculate_creativity_level()
        
        # Initialize emotional state
        self.emotional_state = self._initialize_emotional_state()
        self.baseline_emotions = copy.deepcopy(self.emotional_state)
        
        # Emotional dynamics
        self.emotion_decay_rate = 0.1  # How quickly emotions return to baseline
        self.emotion_sensitivity = 1.0  # How strongly events affect emotions
        self.mood_threshold = 0.2  # Threshold for mood changes
        
        # Emotional memory and learning
        self.emotional_memories: List[EmotionalMemory] = []
        self.max_emotional_memories = 100
        self.emotional_patterns: Dict[str, List[float]] = {}
        
        # Current mood and state
        self.current_mood = MoodState.NEUTRAL
        self.mood_duration = timedelta(0)
        self.last_mood_change = datetime.now()
        
        # Statistics
        self.emotion_stats = {
            "total_emotional_events": 0,
            "mood_changes": 0,
            "average_happiness": 0.5,
            "average_motivation": 0.5,
            "emotional_volatility": 0.5,
            "social_interactions": 0
        }
        
        self.logger.info(f"Emotion engine initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the emotion engine."""
        try:
            await self._load_emotional_patterns()
            self.logger.info("Emotion engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize emotion engine: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the emotion engine gracefully."""
        try:
            await self._save_emotional_patterns()
            self.logger.info("Emotion engine shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during emotion engine shutdown: {e}")
    
    async def process_emotional_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an emotional event and update emotional state.
        
        Args:
            event_data: Dictionary containing event information
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Log the event
            self.emotion_stats["total_emotional_events"] += 1
            
            # Apply personality-based filtering to emotional impact
            filtered_impact = self._apply_personality_filter(event_data.get("emotional_impact", {}))
            
            # Modulate emotional change based on current state and personality
            changes = self._modulate_emotional_change(filtered_impact)
            
            # Apply changes to emotional state
            state_before = copy.deepcopy(self.emotional_state)
            for emotion, change in changes.items():
                if hasattr(self.emotional_state, emotion):
                    current_value = getattr(self.emotional_state, emotion)
                    new_value = max(0.0, min(1.0, current_value + change))
                    setattr(self.emotional_state, emotion, new_value)
            
            # Update mood if necessary
            self._update_mood()
            
            # Store emotional memory
            self._store_emotional_memory(event_data, filtered_impact)
            
            self.logger.debug(f"Processed emotional event: {event_data.get('event_type', 'unknown')}")
            
            return {
                "state_before": state_before,
                "changes": changes,
                "new_mood": self.current_mood.value
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process emotional event: {e}")
            return {"error": str(e)}
    
    async def update_emotional_state(self, emotional_state: Dict[str, float]) -> None:
        """Update the emotional state from external source."""
        try:
            for emotion, value in emotional_state.items():
                if hasattr(self.emotional_state, emotion):
                    setattr(self.emotional_state, emotion, max(0.0, min(1.0, value)))
            
            # Update mood based on new state
            self._update_mood()
            
        except Exception as e:
            self.logger.error(f"Failed to update emotional state: {e}")
    
    def get_personality_influence_on_decision(self, decision_factors: Dict[str, float]) -> Dict[str, float]:
        """
        Get personality influence on decision-making factors.
        
        Args:
            decision_factors: Base decision factors
            
        Returns:
            Dictionary of personality-adjusted weights
        """
        try:
            adjusted_factors = {}
            
            for factor, base_weight in decision_factors.items():
                # Apply personality-based adjustments
                openness_adj = (self.personality.traits.get("openness", 0.5) - 0.5) * 0.4
                neuroticism_adj = (self.personality.traits.get("neuroticism", 0.5) - 0.5) * -0.3
                agreeableness_adj = (self.personality.traits.get("agreeableness", 0.5) - 0.5) * 0.5
                extraversion_adj = (self.personality.traits.get("extraversion", 0.5) - 0.5) * 0.3
                conscientiousness_adj = (self.personality.traits.get("conscientiousness", 0.5) - 0.5) * 0.4
                
                # Factor-specific adjustments
                if factor == "risk_taking":
                    adjustment = openness_adj + neuroticism_adj
                elif factor == "social_cooperation":
                    adjustment = agreeableness_adj + extraversion_adj
                elif factor == "careful_planning":
                    adjustment = conscientiousness_adj + neuroticism_adj
                elif factor == "novelty_seeking":
                    adjustment = openness_adj + extraversion_adj
                else:
                    adjustment = 0.0
                
                adjusted_weight = max(0.0, min(1.0, base_weight + adjustment))
                adjusted_factors[factor] = adjusted_weight
            
            return adjusted_factors
            
        except Exception as e:
            self.logger.error(f"Failed to calculate personality influence on decision: {e}")
            return decision_factors
    
    # Private helper methods
    
    def _initialize_emotional_state(self) -> EmotionalState:
        """Initialize emotional state based on personality."""
        emotional_state = EmotionalState()
        
        # Base emotions influenced by personality
        emotional_state.motivation = 0.3 + self.personality.traits.get("conscientiousness", 0.5) * 0.4
        emotional_state.boredom = 0.1 + (1.0 - self.personality.traits.get("openness", 0.5)) * 0.2
        emotional_state.happiness = 0.4 + (1.0 - self.personality.traits.get("neuroticism", 0.5)) * 0.3
        emotional_state.curiosity = 0.5 + self.personality.traits.get("openness", 0.5) * 0.4
        emotional_state.social_need = 0.3 + self.personality.traits.get("extraversion", 0.5) * 0.4
        emotional_state.anxiety = 0.1 + self.personality.traits.get("neuroticism", 0.5) * 0.3
        emotional_state.confidence = 0.5 + (1.0 - self.personality.traits.get("neuroticism", 0.5)) * 0.2
        emotional_state.excitement = 0.3 + self.personality.traits.get("openness", 0.5) * 0.2
        
        return emotional_state
    
    def _calculate_emotional_stability(self) -> float:
        """Calculate emotional stability from personality traits."""
        return 1.0 - self.personality.traits.get("neuroticism", 0.5)
    
    def _calculate_social_orientation(self) -> float:
        """Calculate social orientation from personality traits."""
        extraversion = self.personality.traits.get("extraversion", 0.5)
        agreeableness = self.personality.traits.get("agreeableness", 0.5)
        return (extraversion + agreeableness) / 2.0
    
    def _calculate_learning_preference(self) -> float:
        """Calculate learning preference from personality traits."""
        openness = self.personality.traits.get("openness", 0.5)
        conscientiousness = self.personality.traits.get("conscientiousness", 0.5)
        return (openness * 0.7 + conscientiousness * 0.3)
    
    def _calculate_risk_tolerance(self) -> float:
        """Calculate risk tolerance from personality traits."""
        openness = self.personality.traits.get("openness", 0.5)
        neuroticism = self.personality.traits.get("neuroticism", 0.5)
        return (openness * 0.6 + (1.0 - neuroticism) * 0.4)
    
    def _calculate_creativity_level(self) -> float:
        """Calculate creativity level from personality traits."""
        return self.personality.traits.get("openness", 0.5)
    
    def _apply_personality_filter(self, emotional_impact: Dict[str, float]) -> Dict[str, float]:
        """Apply personality-based filtering to emotional impact."""
        filtered_impact = {}
        stability_factor = self.personality.emotional_stability
        
        for emotion, intensity in emotional_impact.items():
            # Base filtering
            filtered_intensity = intensity * stability_factor
            
            # Specific personality influences
            neuroticism_factor = self.personality.traits.get("neuroticism", 0.5)
            extraversion_factor = self.personality.traits.get("extraversion", 0.5)
            openness_factor = self.personality.traits.get("openness", 0.5)
            
            # Adjust based on personality
            if emotion in ["anxiety", "frustration"]:
                filtered_intensity *= (1.0 + neuroticism_factor * 0.5)
            elif emotion in ["excitement", "curiosity"]:
                filtered_intensity *= (1.0 + openness_factor * 0.3)
            elif emotion in ["social_need"]:
                filtered_intensity *= (1.0 + extraversion_factor * 0.4)
            
            filtered_impact[emotion] = max(-1.0, min(1.0, filtered_intensity))
        
        return filtered_impact
    
    def _modulate_emotional_change(self, emotional_impact: Dict[str, float]) -> Dict[str, float]:
        """Modulate emotional change based on current state and personality."""
        changes = {}
        
        for emotion, impact in emotional_impact.items():
            # Apply sensitivity
            change = impact * self.emotion_sensitivity
            
            # Apply personality-based modulation
            if emotion == "motivation":
                change *= (1.0 + self.personality.traits.get("conscientiousness", 0.5) * 0.2)
            elif emotion == "social_need":
                change *= (1.0 + self.personality.traits.get("extraversion", 0.5) * 0.3)
            elif emotion == "curiosity":
                change *= (1.0 + self.personality.traits.get("openness", 0.5) * 0.3)
            
            changes[emotion] = change
        
        return changes
    
    def _update_mood(self) -> None:
        """Update mood based on current emotional state."""
        # Calculate overall emotional valence
        positive_emotions = (self.emotional_state.happiness + 
                           self.emotional_state.excitement + 
                           self.emotional_state.confidence +
                           self.emotional_state.motivation)
        negative_emotions = (self.emotional_state.anxiety + 
                           self.emotional_state.frustration + 
                           self.emotional_state.boredom)
        
        valence = (positive_emotions - negative_emotions) / 4.0
        
        # Determine new mood based on valence
        if valence > 0.5:
            new_mood = MoodState.EUPHORIC if valence > 0.8 else MoodState.HAPPY
        elif valence > 0.1:
            new_mood = MoodState.CONTENT
        elif valence > -0.1:
            new_mood = MoodState.NEUTRAL
        elif valence > -0.5:
            new_mood = MoodState.MELANCHOLY
        else:
            new_mood = MoodState.ANXIOUS if valence < -0.8 else MoodState.FRUSTRATED
        
        # Update mood if changed
        if new_mood != self.current_mood:
            self.current_mood = new_mood
            self.mood_duration = timedelta(0)
            self.last_mood_change = datetime.now()
            self.emotion_stats["mood_changes"] += 1
        else:
            self.mood_duration += timedelta(seconds=1)
    
    def _store_emotional_memory(self, event_data: Dict[str, Any], filtered_impact: Dict[str, float]) -> None:
        """Store emotional memory for learning and pattern recognition."""
        try:
            memory = EmotionalMemory(
                event_id=f"emotion_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.emotional_memories)}",
                timestamp=datetime.now(),
                emotional_impact=filtered_impact,
                context=event_data.get("context", {}),
                intensity=max(abs(v) for v in filtered_impact.values()) if filtered_impact else 0.0,
                duration=timedelta(seconds=event_data.get("duration", 10))
            )
            
            self.emotional_memories.append(memory)
            
            # Maintain memory size limit
            if len(self.emotional_memories) > self.max_emotional_memories:
                self.emotional_memories.pop(0)
            
            # Update emotional patterns
            self._update_emotional_patterns(filtered_impact)
            
        except Exception as e:
            self.logger.error(f"Failed to store emotional memory: {e}")
    
    def _update_emotional_patterns(self, filtered_impact: Dict[str, float]) -> None:
        """Update emotional patterns for learning."""
        try:
            for emotion, value in filtered_impact.items():
                if emotion not in self.emotional_patterns:
                    self.emotional_patterns[emotion] = []
                
                self.emotional_patterns[emotion].append(value)
                
                # Maintain pattern size limit
                if len(self.emotional_patterns[emotion]) > 50:
                    self.emotional_patterns[emotion].pop(0)
            
            # Update statistics
            if self.emotional_patterns.get("happiness"):
                self.emotion_stats["average_happiness"] = (
                    sum(self.emotional_patterns["happiness"]) / len(self.emotional_patterns["happiness"])
                )
            
            if self.emotional_patterns.get("motivation"):
                self.emotion_stats["average_motivation"] = (
                    sum(self.emotional_patterns["motivation"]) / len(self.emotional_patterns["motivation"])
                )
            
            # Calculate emotional volatility
            all_values = []
            for values in self.emotional_patterns.values():
                all_values.extend(values)
            
            if len(all_values) > 1:
                mean = sum(all_values) / len(all_values)
                variance = sum((x - mean) ** 2 for x in all_values) / len(all_values)
                self.emotion_stats["emotional_volatility"] = math.sqrt(variance)
                
        except Exception as e:
            self.logger.error(f"Failed to update emotional patterns: {e}")
    
    async def _load_emotional_patterns(self) -> None:
        """Load emotional patterns from persistent storage."""
        # Placeholder for loading from database or file
        pass
    
    async def _save_emotional_patterns(self) -> None:
        """Save emotional patterns to persistent storage."""
        # Placeholder for saving to database or file
        pass