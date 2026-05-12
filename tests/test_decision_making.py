"""
Unit tests for decision making system.
"""

import pytest
from datetime import datetime

from autonomous_ai_ecosystem.agents.emotions import (
    EmotionEngine
)
from autonomous_ai_ecosystem.utils.generators import generate_personality_traits


class TestDecisionMaking:
    """Test cases for DecisionMaking system."""
    
    def setup_method(self):
        """Set up test environment."""
        from autonomous_ai_ecosystem.agents.decision_making import (
            DecisionMaker
        )
        from autonomous_ai_ecosystem.agents.memory import MemorySystem
        import tempfile
        
        self.agent_id = "test_agent_decisions"
        self.personality_traits = generate_personality_traits()
        self.emotion_engine = EmotionEngine(self.agent_id, self.personality_traits)
        self.memory_system = MemorySystem(self.agent_id, tempfile.mkdtemp())
        self.decision_maker = DecisionMaker(self.agent_id, self.emotion_engine, self.memory_system)
    
    def teardown_method(self):
        """Clean up test environment."""
        import asyncio
        if hasattr(self, 'decision_maker'):
            asyncio.create_task(self.decision_maker.shutdown())
        if hasattr(self, 'memory_system'):
            asyncio.create_task(self.memory_system.shutdown())
        if hasattr(self, 'emotion_engine'):
            asyncio.create_task(self.emotion_engine.shutdown())
    
    @pytest.mark.asyncio
    async def test_decision_maker_initialization(self):
        """Test decision maker initialization."""
        await self.decision_maker.initialize()
        
        assert self.decision_maker.agent_id == self.agent_id
        assert self.decision_maker.emotion_engine == self.emotion_engine
        assert self.decision_maker.memory_system == self.memory_system
        assert len(self.decision_maker.decision_options) > 0
        assert self.decision_maker.motivation_state is not None
    
    @pytest.mark.asyncio
    async def test_decision_making_process(self):
        """Test the complete decision-making process."""
        from autonomous_ai_ecosystem.agents.decision_making import DecisionContext
        
        await self.decision_maker.initialize()
        
        # Create decision context
        context = DecisionContext(
            current_emotional_state={
                "motivation": 0.8,
                "boredom": 0.6,
                "curiosity": 0.9,
                "social_need": 0.4
            },
            available_resources={"time": 5.0, "energy": 0.8},
            social_environment={"peers": 3},
            recent_experiences=[],
            time_constraints=None,
            external_pressures=[],
            opportunities=["learning_opportunity"]
        )
        
        # Make decision
        decision = await self.decision_maker.make_decision(context)
        
        assert decision is not None
        assert hasattr(decision, 'option_id')
        assert hasattr(decision, 'description')
        assert hasattr(decision, 'decision_type')
        
        # Check that decision was recorded
        assert len(self.decision_maker.decision_history) > 0
    
    @pytest.mark.asyncio
    async def test_motivation_state_updates(self):
        """Test motivation state updates."""
        initial_motivations = self.decision_maker.motivation_state.primary_motivations.copy()
        
        # Create mock experiences
        experiences = [
            {"type": "learning_success", "satisfaction": 0.8},
            {"type": "social_interaction", "satisfaction": 0.6}
        ]
        
        # Update motivation
        await self.decision_maker.update_motivation(experiences)
        
        # Check that motivation state was updated
        assert self.decision_maker.motivation_state.last_updated is not None
        
        # Motivations might have changed (depending on implementation)
        updated_motivations = self.decision_maker.motivation_state.primary_motivations
        assert len(updated_motivations) == len(initial_motivations)
    
    def test_decision_option_management(self):
        """Test adding and removing decision options."""
        from autonomous_ai_ecosystem.agents.decision_making import DecisionOption, DecisionType
        
        initial_count = len(self.decision_maker.decision_options)
        
        # Add new option
        new_option = DecisionOption(
            option_id="test_option",
            description="Test decision option",
            decision_type=DecisionType.EXPLORATION,
            expected_outcomes={"discovery": 0.7},
            resource_cost={"time": 1.0},
            time_cost=1.0,
            risk_level=0.3,
            social_impact=0.0,
            learning_potential=0.8
        )
        
        self.decision_maker.add_decision_option(new_option)
        assert len(self.decision_maker.decision_options) == initial_count + 1
        assert "test_option" in self.decision_maker.decision_options
        
        # Remove option
        success = self.decision_maker.remove_decision_option("test_option")
        assert success
        assert len(self.decision_maker.decision_options) == initial_count
        assert "test_option" not in self.decision_maker.decision_options
        
        # Try to remove non-existent option
        success = self.decision_maker.remove_decision_option("non_existent")
        assert not success
    
    @pytest.mark.asyncio
    async def test_learning_from_outcomes(self):
        """Test learning from decision outcomes."""
        from autonomous_ai_ecosystem.agents.decision_making import DecisionContext
        
        await self.decision_maker.initialize()
        
        # Make a decision first
        context = DecisionContext(
            current_emotional_state={"motivation": 0.7},
            available_resources={"time": 3.0},
            social_environment={},
            recent_experiences=[],
            time_constraints=None,
            external_pressures=[],
            opportunities=[]
        )
        
        decision = await self.decision_maker.make_decision(context)
        assert decision is not None
        
        # Get decision ID from history
        decision_record = self.decision_maker.decision_history[-1]
        decision_id = decision_record["decision_id"]
        
        # Learn from outcome
        actual_outcomes = {"satisfaction": 0.9, "learning": 0.8}
        satisfaction_level = 0.85
        
        await self.decision_maker.learn_from_outcome(
            decision_id, actual_outcomes, satisfaction_level
        )
        
        # Check that outcome was recorded
        option_id = decision.option_id
        assert option_id in self.decision_maker.decision_outcomes
        assert len(self.decision_maker.decision_outcomes[option_id]) > 0
        assert self.decision_maker.decision_outcomes[option_id][-1] == satisfaction_level
    
    def test_decision_statistics(self):
        """Test decision statistics calculation."""
        # Add some mock decision history
        mock_decisions = [
            {
                "decision_id": "test_1",
                "option_id": "learn_new_topic",
                "decision_type": "learning_activity",
                "timestamp": datetime.now()
            },
            {
                "decision_id": "test_2", 
                "option_id": "social_interaction",
                "decision_type": "social_interaction",
                "timestamp": datetime.now()
            }
        ]
        
        self.decision_maker.decision_history.extend(mock_decisions)
        
        # Add some outcomes
        self.decision_maker.decision_outcomes["learn_new_topic"] = [0.8, 0.7, 0.9]
        self.decision_maker.decision_outcomes["social_interaction"] = [0.6, 0.8]
        
        # Get statistics
        stats = self.decision_maker.get_decision_statistics()
        
        assert "total_decisions" in stats
        assert "decision_types" in stats
        assert "average_satisfaction" in stats
        assert "available_options" in stats
        
        assert stats["total_decisions"] >= 2
        assert "learning_activity" in stats["decision_types"]
        assert "social_interaction" in stats["decision_types"]
        assert 0.0 <= stats["average_satisfaction"] <= 1.0
