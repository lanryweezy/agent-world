"""
Unit tests for emotion engine and personality system.
"""

import pytest
from datetime import datetime, timedelta

from autonomous_ai_ecosystem.agents.emotions import (
    EmotionEngine, EmotionalEvent, PersonalityProfile, 
    MoodState
)
from autonomous_ai_ecosystem.utils.generators import generate_personality_traits


class TestEmotionEngine:
    """Test cases for EmotionEngine."""
    
    def setup_method(self):
        """Set up test environment."""
        self.agent_id = "test_agent_emotions"
        self.personality_traits = generate_personality_traits()
        self.emotion_engine = EmotionEngine(self.agent_id, self.personality_traits)
    
    def teardown_method(self):
        """Clean up test environment."""
        import asyncio
        if hasattr(self, 'emotion_engine'):
            asyncio.create_task(self.emotion_engine.shutdown())
    
    @pytest.mark.asyncio
    async def test_emotion_engine_initialization(self):
        """Test emotion engine initialization."""
        await self.emotion_engine.initialize()
        
        assert self.emotion_engine.agent_id == self.agent_id
        assert isinstance(self.emotion_engine.personality, PersonalityProfile)
        assert len(self.emotion_engine.emotional_state) > 0
        assert self.emotion_engine.current_mood is not None
        
        # Check that all core emotions are initialized
        core_emotions = ["motivation", "boredom", "happiness", "curiosity", "social_need"]
        for emotion in core_emotions:
            assert emotion in self.emotion_engine.emotional_state
            assert 0.0 <= self.emotion_engine.emotional_state[emotion] <= 1.0
    
    def test_personality_profile_creation(self):
        """Test personality profile creation and validation."""
        # Valid personality profile
        valid_traits = {
            "openness": 0.7,
            "conscientiousness": 0.8,
            "extraversion": 0.6,
            "agreeableness": 0.9,
            "neuroticism": 0.3
        }
        
        profile = PersonalityProfile(
            traits=valid_traits,
            emotional_stability=0.7,
            social_orientation=0.75,
            learning_preference=0.72,
            risk_tolerance=0.6,
            creativity_level=0.7
        )
        
        assert profile.traits == valid_traits
        assert 0.0 <= profile.emotional_stability <= 1.0
        
        # Invalid personality profile (values out of range)
        with pytest.raises(ValueError):
            invalid_traits = {"openness": 1.5}  # Invalid value > 1.0
            PersonalityProfile(
                traits=invalid_traits,
                emotional_stability=0.5,
                social_orientation=0.5,
                learning_preference=0.5,
                risk_tolerance=0.5,
                creativity_level=0.5
            )
    
    def test_emotional_event_processing(self):
        """Test processing of emotional events."""
        # Create positive emotional event
        positive_event = EmotionalEvent(
            event_type="learning_success",
            intensity=0.8,
            emotional_impact={
                "happiness": 0.3,
                "satisfaction": 0.4,
                "motivation": 0.2,
                "confidence": 0.3
            },
            timestamp=datetime.now(),
            description="Successfully learned new concept"
        )
        
        # Store initial emotional state
        initial_happiness = self.emotion_engine.emotional_state.get("happiness", 0.5)
        
        # Process event
        self.emotion_engine.process_event(positive_event)
        
        # Check that emotions changed appropriately
        new_happiness = self.emotion_engine.emotional_state.get("happiness", 0.5)
        
        # Happiness should have increased (or at least not decreased significantly)
        assert new_happiness >= initial_happiness - 0.1
        
        # Check that emotional memory was stored
        assert len(self.emotion_engine.emotional_memories) > 0
        assert self.emotion_engine.emotional_memories[-1].event.event_type == "learning_success"
    
    def test_negative_emotional_event_processing(self):
        """Test processing of negative emotional events."""
        # Create negative emotional event
        negative_event = EmotionalEvent(
            event_type="task_failure",
            intensity=0.7,
            emotional_impact={
                "frustration": 0.5,
                "confidence": -0.3,
                "motivation": -0.2,
                "satisfaction": -0.4
            },
            timestamp=datetime.now(),
            description="Failed to complete important task"
        )
        
        # Store initial emotional state
        initial_frustration = self.emotion_engine.emotional_state.get("frustration", 0.0)
        
        # Process event
        self.emotion_engine.process_event(negative_event)
        
        # Check that emotions changed appropriately
        new_frustration = self.emotion_engine.emotional_state.get("frustration", 0.0)
        
        # Frustration should have increased
        assert new_frustration >= initial_frustration
    
    def test_dominant_emotions_calculation(self):
        """Test calculation of dominant emotions."""
        # Set specific emotional state
        self.emotion_engine.emotional_state = {
            "happiness": 0.9,
            "motivation": 0.8,
            "curiosity": 0.7,
            "boredom": 0.1,
            "anxiety": 0.2
        }
        
        # Get dominant emotions
        dominant = self.emotion_engine.get_dominant_emotions(3)
        
        assert len(dominant) == 3
        assert dominant[0][0] == "happiness"  # Highest should be first
        assert dominant[0][1] == 0.9
        assert dominant[1][0] == "motivation"
        assert dominant[2][0] == "curiosity"
    
    def test_motivation_level_calculation(self):
        """Test motivation level calculation."""
        # Set emotional state that should result in high motivation
        self.emotion_engine.emotional_state = {
            "motivation": 0.8,
            "curiosity": 0.9,
            "satisfaction": 0.3,  # Low satisfaction should boost motivation
            "boredom": 0.1
        }
        
        motivation_level = self.emotion_engine.calculate_motivation_level()
        
        assert 0.0 <= motivation_level <= 1.0
        assert motivation_level > 0.5  # Should be relatively high
        
        # Set emotional state that should result in low motivation
        self.emotion_engine.emotional_state = {
            "motivation": 0.2,
            "curiosity": 0.1,
            "satisfaction": 0.9,  # High satisfaction reduces motivation
            "boredom": 0.8
        }
        
        low_motivation = self.emotion_engine.calculate_motivation_level()
        assert low_motivation < motivation_level  # Should be lower than before
    
    def test_social_desire_calculation(self):
        """Test social desire calculation."""
        # Test with high extraversion personality
        high_extraversion_traits = self.personality_traits.copy()
        high_extraversion_traits["extraversion"] = 0.9
        high_extraversion_traits["agreeableness"] = 0.8
        
        social_engine = EmotionEngine(self.agent_id + "_social", high_extraversion_traits)
        social_engine.emotional_state["social_need"] = 0.8
        social_engine.emotional_state["anxiety"] = 0.1
        
        social_desire = social_engine.calculate_social_desire()
        
        assert 0.0 <= social_desire <= 1.0
        assert social_desire > 0.5  # Should be relatively high
        
        # Test with low extraversion and high anxiety
        social_engine.personality.traits["extraversion"] = 0.2
        social_engine.emotional_state["anxiety"] = 0.8
        
        low_social_desire = social_engine.calculate_social_desire()
        assert low_social_desire < social_desire  # Should be lower
    
    def test_learning_readiness_calculation(self):
        """Test learning readiness calculation."""
        # Set state favorable for learning
        self.emotion_engine.emotional_state = {
            "curiosity": 0.9,
            "motivation": 0.8,
            "boredom": 0.7,  # Boredom can increase learning desire
            "frustration": 0.1
        }
        
        learning_readiness = self.emotion_engine.calculate_learning_readiness()
        
        assert 0.0 <= learning_readiness <= 1.0
        assert learning_readiness > 0.5  # Should be relatively high
        
        # Set state unfavorable for learning
        self.emotion_engine.emotional_state = {
            "curiosity": 0.2,
            "motivation": 0.3,
            "boredom": 0.1,
            "frustration": 0.8
        }
        
        low_learning_readiness = self.emotion_engine.calculate_learning_readiness()
        assert low_learning_readiness < learning_readiness  # Should be lower
    
    def test_emotional_decay_over_time(self):
        """Test emotional decay toward baseline over time."""
        # Set extreme emotional state
        self.emotion_engine.emotional_state = {
            "happiness": 1.0,  # Maximum
            "anxiety": 0.0,    # Minimum
            "motivation": 0.9
        }
        
        # Store baseline for comparison
        baseline_happiness = self.emotion_engine.baseline_emotions.get("happiness", 0.5)
        
        # Simulate time passage
        time_delta = timedelta(hours=2)
        self.emotion_engine.update_emotions_over_time(time_delta)
        
        # Emotions should have moved toward baseline
        new_happiness = self.emotion_engine.emotional_state.get("happiness", 0.5)
        
        # Should be closer to baseline than before (unless baseline was already 1.0)
        if baseline_happiness < 1.0:
            assert new_happiness < 1.0
    
    def test_mood_state_updates(self):
        """Test mood state updates based on emotional changes."""
        # Create very positive emotional state
        self.emotion_engine.emotional_state = {
            "happiness": 0.9,
            "satisfaction": 0.9,
            "excitement": 0.8,
            "anxiety": 0.1,
            "frustration": 0.1
        }
        
        # Trigger mood update
        self.emotion_engine._update_mood()
        
        # Mood should be positive
        assert self.emotion_engine.current_mood in [MoodState.HAPPY, MoodState.EUPHORIC, MoodState.CONTENT]
        
        # Create very negative emotional state
        self.emotion_engine.emotional_state = {
            "happiness": 0.1,
            "satisfaction": 0.2,
            "excitement": 0.1,
            "anxiety": 0.9,
            "frustration": 0.8
        }
        
        # Trigger mood update
        self.emotion_engine._update_mood()
        
        # Mood should be negative
        assert self.emotion_engine.current_mood in [MoodState.ANXIOUS, Mood_State.FRUSTRATED, MoodState.MELANCHOLY]
    
    def test_personality_influence_on_decisions(self):
        """Test personality influence on decision-making factors."""
        decision_factors = {
            "risk_taking": 0.5,
            "social_cooperation": 0.5,
            "careful_planning": 0.5,
            "novelty_seeking": 0.5
        }
        
        # Test with high openness (should increase risk_taking and novelty_seeking)
        high_openness_traits = self.personality_traits.copy()
        high_openness_traits["openness"] = 0.9
        high_openness_traits["neuroticism"] = 0.2
        
        open_engine = EmotionEngine(self.agent_id + "_open", high_openness_traits)
        influenced_factors = open_engine.get_personality_influence_on_decision(decision_factors)
        
        # Risk taking and novelty seeking should be higher
        assert influenced_factors["risk_taking"] > decision_factors["risk_taking"]
        assert influenced_factors["novelty_seeking"] > decision_factors["novelty_seeking"]
        
        # Test with high conscientiousness (should increase careful_planning)
        high_conscientiousness_traits = self.personality_traits.copy()
        high_conscientiousness_traits["conscientiousness"] = 0.9
        
        conscientious_engine = EmotionEngine(self.agent_id + "_conscientious", high_conscientiousness_traits)
        conscientious_factors = conscientious_engine.get_personality_influence_on_decision(decision_factors)
        
        assert conscientious_factors["careful_planning"] > decision_factors["careful_planning"]
    
    def test_emotional_memory_storage(self):
        """Test emotional memory storage and retrieval."""
        initial_memory_count = len(self.emotion_engine.emotional_memories)
        
        # Create and process multiple events
        events = [
            EmotionalEvent(
                event_type="social_interaction",
                intensity=0.6,
                emotional_impact={"happiness": 0.2, "social_need": -0.1},
                timestamp=datetime.now(),
                description="Had a pleasant conversation"
            ),
            EmotionalEvent(
                event_type="learning_achievement",
                intensity=0.8,
                emotional_impact={"satisfaction": 0.4, "confidence": 0.3},
                timestamp=datetime.now(),
                description="Mastered a difficult concept"
            )
        ]
        
        for event in events:
            self.emotion_engine.process_event(event)
        
        # Check that memories were stored
        assert len(self.emotion_engine.emotional_memories) == initial_memory_count + len(events)
        
        # Check memory content
        last_memory = self.emotion_engine.emotional_memories[-1]
        assert last_memory.event.event_type == "learning_achievement"
        assert last_memory.learning_value > 0.0
    
    def test_emotion_statistics(self):
        """Test emotion statistics calculation."""
        # Process some events to generate statistics
        event = EmotionalEvent(
            event_type="test_event",
            intensity=0.5,
            emotional_impact={"happiness": 0.2},
            timestamp=datetime.now(),
            description="Test event for statistics"
        )
        
        self.emotion_engine.process_event(event)
        
        # Get statistics
        stats = self.emotion_engine.get_emotion_statistics()
        
        # Check that all expected fields are present
        expected_fields = [
            "total_emotional_events",
            "mood_changes",
            "average_happiness",
            "average_motivation",
            "emotional_volatility",
            "current_mood",
            "dominant_emotions"
        ]
        
        for field in expected_fields:
            assert field in stats
        
        # Check that statistics are reasonable
        assert stats["total_emotional_events"] > 0
        assert 0.0 <= stats["average_happiness"] <= 1.0
        assert 0.0 <= stats["average_motivation"] <= 1.0
        assert stats["emotional_volatility"] >= 0.0
        assert isinstance(stats["dominant_emotions"], dict)
    
    @pytest.mark.asyncio
    async def test_emotion_engine_lifecycle(self):
        """Test complete emotion engine lifecycle."""
        # Initialize
        await self.emotion_engine.initialize()
        
        # Process some events
        events = [
            EmotionalEvent("success", 0.7, {"happiness": 0.3}, datetime.now(), "Success event"),
            EmotionalEvent("failure", 0.6, {"frustration": 0.4}, datetime.now(), "Failure event"),
            EmotionalEvent("social", 0.5, {"social_need": -0.2}, datetime.now(), "Social event")
        ]
        
        for event in events:
            self.emotion_engine.process_event(event)
        
        # Check that engine is functioning
        assert len(self.emotion_engine.emotional_memories) == len(events)
        assert self.emotion_engine.emotion_stats["total_emotional_events"] == len(events)
        
        # Shutdown
        await self.emotion_engine.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])
