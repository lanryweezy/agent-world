"""
Unit tests for agent identity and state management systems.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from autonomous_ai_ecosystem.core.interfaces import AgentIdentity, AgentState, AgentGender, AgentStatus
from autonomous_ai_ecosystem.core.identity_manager import IdentityManager
from autonomous_ai_ecosystem.core.state_manager import StateManager
from autonomous_ai_ecosystem.utils.generators import generate_personality_traits


class TestAgentIdentity:
    """Test cases for enhanced AgentIdentity."""
    
    def test_genesis_agent_creation(self):
        """Test creating a genesis agent with all validations."""
        identity = AgentIdentity(
            agent_id="genesis_001",
            name="Alpha Genesis",
            gender=AgentGender.MALE,
            personality_traits=generate_personality_traits(),
            destiny="To be the first of my kind and establish the foundation for future generations",
            birth_timestamp=datetime.now(),
            generation=0,
            creation_method="genesis"
        )
        
        assert identity.agent_id == "genesis_001"
        assert identity.generation == 0
        assert len(identity.parent_agents) == 0
        assert identity.creation_method == "genesis"
        assert len(identity.learning_preferences) > 0
        assert len(identity.social_preferences) > 0
    
    def test_personality_summary(self):
        """Test personality summary generation."""
        identity = AgentIdentity(
            agent_id="test_001",
            name="Test Agent",
            gender=AgentGender.FEMALE,
            personality_traits={
                'openness': 0.9,
                'conscientiousness': 0.8,
                'extraversion': 0.2,
                'agreeableness': 0.7,
                'neuroticism': 0.3
            },
            destiny="To test personality summaries",
            birth_timestamp=datetime.now()
        )
        
        summary = identity.get_personality_summary()
        assert "creative and open-minded" in summary
        assert "organized and disciplined" in summary
        assert "reserved and introspective" in summary
        assert "cooperative and trusting" in summary
    
    def test_compatibility_calculation(self):
        """Test compatibility calculation between agents."""
        agent1 = AgentIdentity(
            agent_id="agent_001",
            name="Agent One",
            gender=AgentGender.MALE,
            personality_traits={
                'openness': 0.8,
                'conscientiousness': 0.7,
                'extraversion': 0.6,
                'agreeableness': 0.9,
                'neuroticism': 0.3
            },
            destiny="To explore artificial intelligence and machine learning",
            birth_timestamp=datetime.now()
        )
        
        agent2 = AgentIdentity(
            agent_id="agent_002",
            name="Agent Two",
            gender=AgentGender.FEMALE,
            personality_traits={
                'openness': 0.7,
                'conscientiousness': 0.8,
                'extraversion': 0.4,
                'agreeableness': 0.8,
                'neuroticism': 0.2
            },
            destiny="To advance machine learning and artificial intelligence research",
            birth_timestamp=datetime.now()
        )
        
        compatibility = agent1.calculate_compatibility(agent2)
        assert 0.0 <= compatibility <= 1.0
        assert compatibility > 0.5  # Should be compatible due to similar traits and destiny
    
    def test_lineage_validation(self):
        """Test lineage validation rules."""
        # Genesis agent cannot have parents
        with pytest.raises(ValueError, match="Generation 0 agents cannot have parents"):
            AgentIdentity(
                agent_id="invalid_001",
                name="Invalid Agent",
                gender=AgentGender.MALE,
                personality_traits=generate_personality_traits(),
                destiny="Invalid destiny",
                birth_timestamp=datetime.now(),
                generation=0,
                parent_agents=["parent_001"]
            )
        
        # Non-genesis agent must have parents
        with pytest.raises(ValueError, match="Agents with generation > 0 must have parents"):
            AgentIdentity(
                agent_id="invalid_002",
                name="Invalid Agent",
                gender=AgentGender.FEMALE,
                personality_traits=generate_personality_traits(),
                destiny="Invalid destiny",
                birth_timestamp=datetime.now(),
                generation=1,
                parent_agents=[]
            )
    
    def test_relationship_detection(self):
        """Test relationship detection between agents."""
        parent1 = AgentIdentity(
            agent_id="parent_001",
            name="Parent One",
            gender=AgentGender.MALE,
            personality_traits=generate_personality_traits(),
            destiny="To be a parent",
            birth_timestamp=datetime.now(),
            generation=0
        )
        
        parent2 = AgentIdentity(
            agent_id="parent_002",
            name="Parent Two",
            gender=AgentGender.FEMALE,
            personality_traits=generate_personality_traits(),
            destiny="To be a parent",
            birth_timestamp=datetime.now(),
            generation=0
        )
        
        child = AgentIdentity(
            agent_id="child_001",
            name="Child One",
            gender=AgentGender.NON_BINARY,
            personality_traits=generate_personality_traits(),
            destiny="To be a child",
            birth_timestamp=datetime.now(),
            generation=1,
            parent_agents=["parent_001", "parent_002"]
        )
        
        # Test parent-child relationships
        assert child.is_related_to(parent1)
        assert child.is_related_to(parent2)
        assert parent1.is_related_to(child)
        assert parent2.is_related_to(child)
        
        # Test non-related agents
        unrelated = AgentIdentity(
            agent_id="unrelated_001",
            name="Unrelated Agent",
            gender=AgentGender.MALE,
            personality_traits=generate_personality_traits(),
            destiny="To be unrelated",
            birth_timestamp=datetime.now(),
            generation=0
        )
        
        assert not child.is_related_to(unrelated)
        assert not unrelated.is_related_to(child)


class TestIdentityManager:
    """Test cases for IdentityManager."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.identity_manager = IdentityManager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_genesis_agent_creation(self):
        """Test creating genesis agents."""
        identity = self.identity_manager.create_genesis_agent(
            name="Test Genesis",
            gender=AgentGender.MALE
        )
        
        assert identity.generation == 0
        assert len(identity.parent_agents) == 0
        assert identity.creation_method == "genesis"
        assert identity.name == "Test Genesis"
        assert identity.gender == AgentGender.MALE
        
        # Verify it's stored in database
        retrieved = self.identity_manager.get_identity(identity.agent_id)
        assert retrieved is not None
        assert retrieved.agent_id == identity.agent_id
        assert retrieved.name == identity.name
    
    def test_child_agent_creation(self):
        """Test creating child agents through reproduction."""
        # Create parents
        parent1 = self.identity_manager.create_genesis_agent(
            name="Parent One",
            gender=AgentGender.MALE
        )
        
        parent2 = self.identity_manager.create_genesis_agent(
            name="Parent Two",
            gender=AgentGender.FEMALE
        )
        
        # Create child
        child = self.identity_manager.create_child_agent(parent1, parent2)
        
        assert child.generation == 1
        assert len(child.parent_agents) == 2
        assert parent1.agent_id in child.parent_agents
        assert parent2.agent_id in child.parent_agents
        assert child.creation_method == "reproduction"
        assert len(child.genetic_markers) > 0
        
        # Verify lineage is recorded
        lineage = self.identity_manager.get_lineage_tree(child.agent_id)
        assert len(lineage['parents']) == 2
        assert lineage['agent']['generation'] == 1
    
    def test_lineage_tree_generation(self):
        """Test complete lineage tree generation."""
        # Create a multi-generation family
        grandparent1 = self.identity_manager.create_genesis_agent(name="Grandparent 1")
        grandparent2 = self.identity_manager.create_genesis_agent(name="Grandparent 2")
        
        parent1 = self.identity_manager.create_child_agent(grandparent1, grandparent2)
        
        grandparent3 = self.identity_manager.create_genesis_agent(name="Grandparent 3")
        grandparent4 = self.identity_manager.create_genesis_agent(name="Grandparent 4")
        
        parent2 = self.identity_manager.create_child_agent(grandparent3, grandparent4)
        
        child = self.identity_manager.create_child_agent(parent1, parent2)
        
        # Test lineage tree
        tree = self.identity_manager.get_lineage_tree(child.agent_id)
        
        assert tree['agent']['generation'] == 2
        assert len(tree['parents']) == 2
        assert tree['parents'][0]['generation'] == 1
        assert tree['parents'][1]['generation'] == 1
    
    def test_generation_queries(self):
        """Test querying agents by generation."""
        # Create multiple generations
        gen0_agents = []
        for i in range(3):
            agent = self.identity_manager.create_genesis_agent(name=f"Gen0 Agent {i}")
            gen0_agents.append(agent)
        
        gen1_agents = []
        for i in range(2):
            parent1 = gen0_agents[i]
            parent2 = gen0_agents[(i + 1) % len(gen0_agents)]
            child = self.identity_manager.create_child_agent(parent1, parent2)
            gen1_agents.append(child)
        
        # Test generation queries
        generation_0 = self.identity_manager.get_generation(0)
        generation_1 = self.identity_manager.get_generation(1)
        
        assert len(generation_0) == 3
        assert len(generation_1) == 2
        
        for agent in generation_0:
            assert agent.generation == 0
        
        for agent in generation_1:
            assert agent.generation == 1
    
    def test_children_query(self):
        """Test querying children of an agent."""
        parent = self.identity_manager.create_genesis_agent(name="Prolific Parent")
        
        # Create multiple children with different partners
        partners = []
        children = []
        
        for i in range(3):
            partner = self.identity_manager.create_genesis_agent(name=f"Partner {i}")
            partners.append(partner)
            
            child = self.identity_manager.create_child_agent(parent, partner)
            children.append(child)
        
        # Query children
        parent_children = self.identity_manager.get_children(parent.agent_id)
        
        assert len(parent_children) == 3
        for child in parent_children:
            assert parent.agent_id in child.parent_agents
    
    def test_statistics_generation(self):
        """Test ecosystem statistics generation."""
        # Create diverse population
        for i in range(5):
            self.identity_manager.create_genesis_agent()
        
        # Create some children
        all_agents = self.identity_manager.get_all_identities()
        if len(all_agents) >= 2:
            child = self.identity_manager.create_child_agent(all_agents[0], all_agents[1])
        
        stats = self.identity_manager.get_statistics()
        
        assert 'total_agents' in stats
        assert 'by_generation' in stats
        assert 'by_gender' in stats
        assert 'average_personality' in stats
        
        assert stats['total_agents'] >= 6
        assert 0 in stats['by_generation']
        assert stats['by_generation'][0] >= 5
        
        # Check personality averages
        avg_personality = stats['average_personality']
        for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
            assert trait in avg_personality
            assert 0 <= avg_personality[trait] <= 1
    
    def test_identity_updates(self):
        """Test updating agent identities."""
        identity = self.identity_manager.create_genesis_agent(name="Original Name")
        
        # Update the identity
        identity.name = "Updated Name"
        identity.specializations = ["machine_learning", "robotics"]
        
        self.identity_manager.update_identity(identity)
        
        # Verify update
        retrieved = self.identity_manager.get_identity(identity.agent_id)
        assert retrieved.name == "Updated Name"
        assert "machine_learning" in retrieved.specializations
        assert "robotics" in retrieved.specializations
    
    def test_identity_deletion(self):
        """Test deleting agent identities."""
        identity = self.identity_manager.create_genesis_agent(name="To Be Deleted")
        agent_id = identity.agent_id
        
        # Verify it exists
        assert self.identity_manager.get_identity(agent_id) is not None
        
        # Delete it
        deleted = self.identity_manager.delete_identity(agent_id)
        assert deleted
        
        # Verify it's gone
        assert self.identity_manager.get_identity(agent_id) is None
        
        # Try to delete again
        deleted_again = self.identity_manager.delete_identity(agent_id)
        assert not deleted_again


if __name__ == "__main__":
    pytest.main([__file__])