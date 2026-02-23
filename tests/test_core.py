"""
Unit tests for core components of the autonomous AI ecosystem.
"""

import pytest
from datetime import datetime
from unittest.mock import patch

from autonomous_ai_ecosystem.core.interfaces import (
    AgentIdentity, AgentMessage, AgentGender, 
    MessageType, AgentStatus
)
from autonomous_ai_ecosystem.core.config import Config
from autonomous_ai_ecosystem.core.agent_core import AgentCore
from autonomous_ai_ecosystem.utils.validators import (
    validate_agent_identity, validate_message
)
from autonomous_ai_ecosystem.utils.generators import (
    generate_agent_id, generate_personality_traits, generate_agent_name
)


class TestAgentIdentity:
    """Test cases for AgentIdentity."""
    
    def test_valid_identity_creation(self):
        """Test creating a valid agent identity."""
        identity = AgentIdentity(
            agent_id="test_agent_001",
            name="Test Agent",
            gender=AgentGender.MALE,
            personality_traits={
                'openness': 0.8,
                'conscientiousness': 0.7,
                'extraversion': 0.6,
                'agreeableness': 0.9,
                'neuroticism': 0.3
            },
            destiny="To test the system thoroughly",
            birth_timestamp=datetime.now()
        )
        
        assert identity.agent_id == "test_agent_001"
        assert identity.name == "Test Agent"
        assert identity.gender == AgentGender.MALE
        assert identity.generation == 0
        assert len(identity.parent_agents) == 0
    
    def test_identity_validation(self):
        """Test identity validation."""
        identity = AgentIdentity(
            agent_id="test_agent_001",
            name="Test Agent",
            gender=AgentGender.FEMALE,
            personality_traits={
                'openness': 0.8,
                'conscientiousness': 0.7,
                'extraversion': 0.6,
                'agreeableness': 0.9,
                'neuroticism': 0.3
            },
            destiny="To test the system thoroughly",
            birth_timestamp=datetime.now()
        )
        
        errors = validate_agent_identity(identity)
        assert len(errors) == 0
    
    def test_invalid_personality_traits(self):
        """Test validation with invalid personality traits."""
        with pytest.raises(ValueError):
            AgentIdentity(
                agent_id="test_agent_001",
                name="Test Agent",
                gender=AgentGender.MALE,
                personality_traits={
                    'openness': 1.5,  # Invalid: > 1.0
                    'conscientiousness': 0.7,
                    'extraversion': 0.6,
                    'agreeableness': 0.9,
                    'neuroticism': 0.3
                },
                destiny="To test the system thoroughly",
                birth_timestamp=datetime.now()
            )


class TestAgentMessage:
    """Test cases for AgentMessage."""
    
    def test_valid_message_creation(self):
        """Test creating a valid agent message."""
        message = AgentMessage(
            message_id="msg_001",
            sender_id="agent_001",
            recipient_id="agent_002",
            message_type=MessageType.CHAT,
            content={"text": "Hello, fellow agent!"},
            timestamp=datetime.now()
        )
        
        assert message.message_id == "msg_001"
        assert message.sender_id == "agent_001"
        assert message.recipient_id == "agent_002"
        assert message.message_type == MessageType.CHAT
        assert message.priority == 5  # default
        assert not message.requires_response  # default
    
    def test_message_validation(self):
        """Test message validation."""
        message = AgentMessage(
            message_id="msg_001",
            sender_id="agent_001",
            recipient_id="agent_002",
            message_type=MessageType.KNOWLEDGE_SHARE,
            content={"knowledge": "Important information"},
            timestamp=datetime.now(),
            priority=8,
            requires_response=True
        )
        
        errors = validate_message(message)
        assert len(errors) == 0
    
    def test_invalid_priority(self):
        """Test validation with invalid priority."""
        with pytest.raises(ValueError):
            AgentMessage(
                message_id="msg_001",
                sender_id="agent_001",
                recipient_id="agent_002",
                message_type=MessageType.CHAT,
                content={"text": "Hello"},
                timestamp=datetime.now(),
                priority=15  # Invalid: > 10
            )


class TestConfig:
    """Test cases for Config."""
    
    def test_default_config(self):
        """Test default configuration creation."""
        config = Config()
        
        assert config.ecosystem_name == "AutonomousAI"
        assert config.max_agents == 50
        assert config.initial_agent_count == 5
        assert config.human_oversight_enabled
        assert config.god_mode_enabled
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = Config()
        issues = config.validate()
        
        # Default config should be valid
        assert len(issues) == 0
    
    def test_invalid_config(self):
        """Test configuration with invalid values."""
        config = Config()
        config.max_agents = -1  # Invalid
        config.initial_agent_count = 100  # Invalid: > max_agents
        
        issues = config.validate()
        assert len(issues) > 0


class TestGenerators:
    """Test cases for generator utilities."""
    
    def test_generate_agent_id(self):
        """Test agent ID generation."""
        agent_id = generate_agent_id()
        
        assert isinstance(agent_id, str)
        assert agent_id.startswith("agent_")
        assert len(agent_id) > 10
    
    def test_generate_personality_traits(self):
        """Test personality traits generation."""
        traits = generate_personality_traits()
        
        required_traits = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
        
        assert len(traits) == 5
        for trait in required_traits:
            assert trait in traits
            assert 0 <= traits[trait] <= 1
    
    def test_generate_agent_name(self):
        """Test agent name generation."""
        name = generate_agent_name(AgentGender.MALE)
        
        assert isinstance(name, str)
        assert len(name) > 5
        assert " " in name  # Should have first name and suffix


@pytest.mark.asyncio
class TestAgentCore:
    """Test cases for AgentCore."""
    
    async def test_agent_core_creation(self):
        """Test creating an agent core."""
        identity = AgentIdentity(
            agent_id="test_agent_001",
            name="Test Agent",
            gender=AgentGender.MALE,
            personality_traits=generate_personality_traits(),
            destiny="To test the system thoroughly",
            birth_timestamp=datetime.now()
        )
        
        config = Config()
        agent = AgentCore(identity, config)
        
        assert agent.identity == identity
        assert agent.config == config
        assert agent.state.agent_id == identity.agent_id
        assert agent.state.status == AgentStatus.OFFLINE
        assert not agent.is_running
    
    async def test_agent_initialization(self):
        """Test agent initialization."""
        identity = AgentIdentity(
            agent_id="test_agent_001",
            name="Test Agent",
            gender=AgentGender.FEMALE,
            personality_traits=generate_personality_traits(),
            destiny="To test the system thoroughly",
            birth_timestamp=datetime.now()
        )
        
        config = Config()
        agent = AgentCore(identity, config)
        
        # Mock the module initialization
        with patch.object(agent, '_initialize_modules'):
            await agent.initialize()
        
        assert agent.state.status == AgentStatus.ACTIVE
        assert agent.is_running
        assert agent.daily_cycle_start is not None
    
    async def test_message_processing(self):
        """Test message processing."""
        identity = AgentIdentity(
            agent_id="test_agent_001",
            name="Test Agent",
            gender=AgentGender.NON_BINARY,
            personality_traits=generate_personality_traits(),
            destiny="To test the system thoroughly",
            birth_timestamp=datetime.now()
        )
        
        config = Config()
        agent = AgentCore(identity, config)
        
        message = AgentMessage(
            message_id="msg_001",
            sender_id="agent_002",
            recipient_id="test_agent_001",
            message_type=MessageType.CHAT,
            content={"text": "Hello!"},
            timestamp=datetime.now()
        )
        
        await agent.process_message(message)
        
        # Message should be queued
        assert not agent.message_queue.empty()
        assert agent.metrics["messages_processed"] == 1


if __name__ == "__main__":
    pytest.main([__file__])

class TestStateManager:
    """Test cases for StateManager."""
    
    def setup_method(self):
        """Set up test environment."""
        import tempfile
        from autonomous_ai_ecosystem.core.state_manager import StateManager
        
        self.temp_dir = tempfile.mkdtemp()
        self.state_manager = StateManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        import time
        # Close any database connections first
        if hasattr(self.state_manager, 'db_connection') and self.state_manager.db_connection:
            self.state_manager.db_connection.close()
        # Wait a moment for file handles to be released
        time.sleep(0.1)
        try:
            shutil.rmtree(self.temp_dir)
        except PermissionError:
            # On Windows, sometimes files are still locked, try again after a short delay
            time.sleep(0.5)
            shutil.rmtree(self.temp_dir)
    
    def test_create_state_with_defaults(self):
        """Test creating state with default values."""
        state = self.state_manager.create_state("test_agent_001")
        
        assert state.agent_id == "test_agent_001"
        assert state.status == AgentStatus.ACTIVE
        assert len(state.emotional_state) == 5
        assert state.status_level == 0
        assert len(state.relationships) == 0
        assert len(state.current_goals) == 0
        assert state.last_activity is not None
    
    def test_create_state_with_custom_emotions(self):
        """Test creating state with custom emotional state."""
        custom_emotions = {
            'motivation': 0.9,
            'boredom': 0.1,
            'happiness': 0.8,
            'curiosity': 0.7,
            'social_need': 0.6
        }
        
        state = self.state_manager.create_state("test_agent_002", custom_emotions)
        
        assert state.emotional_state == custom_emotions
    
    def test_store_and_retrieve_state(self):
        """Test storing and retrieving state from database."""
        # Create state
        original_state = self.state_manager.create_state("test_agent_003")
        
        # Retrieve state
        retrieved_state = self.state_manager.get_state("test_agent_003")
        
        assert retrieved_state is not None
        assert retrieved_state.agent_id == original_state.agent_id
        assert retrieved_state.status == original_state.status
        assert retrieved_state.emotional_state == original_state.emotional_state
        assert retrieved_state.status_level == original_state.status_level
    
    def test_update_emotional_state(self):
        """Test updating emotional state."""
        # Create state
        state = self.state_manager.create_state("test_agent_004")
        original_motivation = state.emotional_state['motivation']
        
        # Update emotions
        emotion_changes = {'motivation': 0.2, 'boredom': -0.1}
        success = self.state_manager.update_emotional_state(
            "test_agent_004", 
            emotion_changes, 
            "test_update"
        )
        
        assert success
        
        # Retrieve updated state
        updated_state = self.state_manager.get_state("test_agent_004")
        assert updated_state.emotional_state['motivation'] == min(1.0, original_motivation + 0.2)
    
    def test_update_relationship(self):
        """Test updating relationships between agents."""
        # Create states for two agents
        self.state_manager.create_state("agent_a")
        self.state_manager.create_state("agent_b")
        
        # Update relationship
        success = self.state_manager.update_relationship(
            "agent_a", "agent_b", 0.3, "friend"
        )
        
        assert success
        
        # Check relationships
        relationships = self.state_manager.get_relationships("agent_a")
        assert "agent_b" in relationships
        assert relationships["agent_b"]["strength"] == 0.3
        assert relationships["agent_b"]["type"] == "friend"
    
    def test_add_and_update_goal(self):
        """Test adding and updating goals."""
        # Create state
        self.state_manager.create_state("test_agent_005")
        
        # Add goal
        success = self.state_manager.add_goal(
            "test_agent_005",
            "Learn about quantum computing",
            priority=8
        )
        
        assert success
        
        # Update goal progress
        success = self.state_manager.update_goal_progress(
            "test_agent_005",
            "Learn about quantum computing",
            0.5
        )
        
        assert success
    
    def test_state_history_tracking(self):
        """Test state history tracking."""
        # Create state
        state = self.state_manager.create_state("test_agent_006")
        
        # Update status to trigger history
        state.status = AgentStatus.LEARNING
        self.state_manager.update_state(state, "entered_learning_phase")
        
        # Get history
        history = self.state_manager.get_state_history("test_agent_006")
        
        assert len(history) > 0
        assert history[0]['status'] == AgentStatus.LEARNING.value
        assert history[0]['change_reason'] == "entered_learning_phase"