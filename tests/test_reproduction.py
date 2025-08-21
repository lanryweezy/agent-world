"""
Unit tests for the ReproductionManager module.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from autonomous_ai_ecosystem.agents.reproduction_manager import ReproductionManager, ReproductionReadiness
from autonomous_ai_ecosystem.agents.genetics import GeneticAlgorithm
from autonomous_ai_ecosystem.agents.social_manager import SocialManager
from autonomous_ai_ecosystem.agents.status_manager import StatusManager
from autonomous_ai_ecosystem.agents.emotions import EmotionEngine
from autonomous_ai_ecosystem.core.interfaces import AgentIdentity, AgentGender
from datetime import datetime

@pytest.mark.asyncio
class TestReproductionManager:
    """Test cases for the ReproductionManager."""

    @pytest.fixture
    def mock_genetics(self):
        """Fixture for a mock GeneticAlgorithm."""
        mock = Mock(spec=GeneticAlgorithm)
        mock.genetic_profiles = {}
        # Mock the creation of a profile
        def mock_create_profile(identity):
            mock.genetic_profiles[identity.agent_id] = Mock(
                agent_id=identity.agent_id,
                genetic_fitness=0.7,
                generation=identity.generation,
                lineage=identity.parent_agents
            )
        mock.create_genetic_profile = Mock(side_effect=mock_create_profile)
        mock._calculate_genetic_distance = Mock(return_value=0.5)
        return mock

    @pytest.fixture
    def mock_social_manager(self):
        """Fixture for a mock SocialManager."""
        mock = Mock(spec=SocialManager)
        mock.get_agent_social_profile = Mock(return_value={"network_connections": 5})
        mock.get_relationship = AsyncMock(return_value=Mock(strength=0.8, trust_level=0.8, respect_level=0.8))
        return mock

    @pytest.fixture
    def mock_status_manager(self):
        """Fixture for a mock StatusManager."""
        mock = Mock(spec=StatusManager)
        mock.get_agent_status = Mock(return_value={"hierarchy_position": {"hierarchy_level": 3}})
        return mock

    @pytest.fixture
    def mock_emotion_engine(self):
        """Fixture for a mock EmotionEngine."""
        mock = Mock(spec=EmotionEngine)
        mock.get_current_emotional_state = Mock(return_value={"happiness": 0.8, "motivation": 0.8})
        return mock

    @pytest.fixture
    async def reproduction_manager(self, mock_genetics, mock_social_manager, mock_status_manager, mock_emotion_engine):
        """Fixture to create a ReproductionManager instance."""
        manager = ReproductionManager(
            agent_id="test_repro_manager",
            genetic_algorithm=mock_genetics,
            social_manager=mock_social_manager,
            status_manager=mock_status_manager,
            emotion_engine=mock_emotion_engine
        )
        await manager.initialize()
        return manager

    @pytest.fixture
    def agent1_identity(self):
        return AgentIdentity(agent_id="agent1", name="Agent 1", gender=AgentGender.MALE, personality_traits={}, destiny="", birth_timestamp=datetime.now(), generation=1)

    @pytest.fixture
    def agent2_identity(self):
        return AgentIdentity(agent_id="agent2", name="Agent 2", gender=AgentGender.FEMALE, personality_traits={}, destiny="", birth_timestamp=datetime.now(), generation=1)


    async def test_assess_reproduction_readiness(self, reproduction_manager, agent1_identity):
        """Test assessing an agent's readiness to reproduce."""
        # Create a genetic profile for the agent so it can be assessed
        reproduction_manager.genetic_algorithm.create_genetic_profile(agent1_identity)

        desire = await reproduction_manager.assess_reproduction_readiness(agent1_identity.agent_id)

        assert desire is not None
        assert desire.agent_id == agent1_identity.agent_id
        assert desire.motivation_score > 0.5 # Based on mocked high values
        assert desire.readiness_level != ReproductionReadiness.NOT_READY

    async def test_propose_reproduction(self, reproduction_manager, agent1_identity, agent2_identity):
        """Test proposing reproduction to another agent."""
        # Create profiles for both agents
        reproduction_manager.genetic_algorithm.create_genetic_profile(agent1_identity)
        reproduction_manager.genetic_algorithm.create_genetic_profile(agent2_identity)

        # Ensure the proposer is ready
        await reproduction_manager.assess_reproduction_readiness(agent1_identity.agent_id)
        reproduction_manager.reproduction_desires[agent1_identity.agent_id].readiness_level = ReproductionReadiness.EAGER

        proposal_id = await reproduction_manager.propose_reproduction(agent1_identity.agent_id, agent2_identity.agent_id)

        assert proposal_id is not None
        assert proposal_id in reproduction_manager.active_proposals

    async def test_respond_to_proposal_accept(self, reproduction_manager, agent1_identity, agent2_identity):
        """Test accepting a reproduction proposal."""
        # Create profiles
        reproduction_manager.genetic_algorithm.create_genetic_profile(agent1_identity)
        reproduction_manager.genetic_algorithm.create_genetic_profile(agent2_identity)

        # Make a proposal
        await reproduction_manager.assess_reproduction_readiness(agent1_identity.agent_id)
        reproduction_manager.reproduction_desires[agent1_identity.agent_id].readiness_level = ReproductionReadiness.EAGER
        proposal_id = await reproduction_manager.propose_reproduction(agent1_identity.agent_id, agent2_identity.agent_id)

        # Make the target agent ready to accept
        await reproduction_manager.assess_reproduction_readiness(agent2_identity.agent_id)
        reproduction_manager.reproduction_desires[agent2_identity.agent_id].readiness_level = ReproductionReadiness.READY

        # Mock the execution result
        reproduction_manager._execute_reproduction = AsyncMock(return_value=True)

        # Respond to the proposal
        accepted = await reproduction_manager.respond_to_proposal(proposal_id, accept=True)

        assert accepted
        assert proposal_id not in reproduction_manager.active_proposals
        reproduction_manager._execute_reproduction.assert_awaited_once()
