"""
Unit tests for the Genetics and GeneticAlgorithm modules.
"""

import pytest
from unittest.mock import Mock

from autonomous_ai_ecosystem.agents.genetics import GeneticAlgorithm
from autonomous_ai_ecosystem.core.interfaces import AgentIdentity, AgentGender
from autonomous_ai_ecosystem.utils.generators import generate_personality_traits
from datetime import datetime

@pytest.mark.asyncio
class TestGeneticAlgorithm:
    """Test cases for the GeneticAlgorithm."""

    @pytest.fixture
    def genetic_algorithm(self):
        """Fixture to create a GeneticAlgorithm instance."""
        return GeneticAlgorithm("test_genetics_system")

    @pytest.fixture
    def parent1(self):
        """Fixture for parent 1's identity."""
        return AgentIdentity(
            agent_id="parent_1",
            name="Parent One",
            gender=AgentGender.MALE,
            personality_traits={'openness': 0.8, 'conscientiousness': 0.8, 'extraversion': 0.8, 'agreeableness': 0.8, 'neuroticism': 0.2},
            destiny="to explore the unknown",
            birth_timestamp=datetime.now(),
            generation=1
        )

    @pytest.fixture
    def parent2(self):
        """Fixture for parent 2's identity."""
        return AgentIdentity(
            agent_id="parent_2",
            name="Parent Two",
            gender=AgentGender.FEMALE,
            personality_traits={'openness': 0.4, 'conscientiousness': 0.4, 'extraversion': 0.4, 'agreeableness': 0.4, 'neuroticism': 0.6},
            destiny="to build a community",
            birth_timestamp=datetime.now(),
            generation=1
        )

    def test_reproduction(self, genetic_algorithm, parent1, parent2):
        """Test the reproduction of two agents."""
        # The genetic algorithm needs profiles for the parents first
        genetic_algorithm.create_genetic_profile(parent1)
        genetic_algorithm.create_genetic_profile(parent2)

        result = genetic_algorithm.reproduce_agents(parent1.agent_id, parent2.agent_id)

        assert result.success
        child_identity = result.offspring_identity

        assert child_identity is not None
        assert child_identity.agent_id != parent1.agent_id
        assert child_identity.agent_id != parent2.agent_id

        # Check parentage and generation
        assert parent1.agent_id in child_identity.parent_agents
        assert parent2.agent_id in child_identity.parent_agents
        assert child_identity.generation == max(parent1.generation, parent2.generation) + 1

        # Check that personality traits are within a plausible range
        for trait, value in child_identity.personality_traits.items():
            assert 0.0 <= value <= 1.0
            # The child's trait should be roughly between the parents, allowing for mutation
            p1_val = parent1.personality_traits[trait]
            p2_val = parent2.personality_traits[trait]
            assert (min(p1_val, p2_val) - genetic_algorithm.mutation_strength) <= value <= (max(p1_val, p2_val) + genetic_algorithm.mutation_strength)

    def test_genetic_profile_creation(self, genetic_algorithm, parent1):
        """Test the creation of a genetic profile."""
        profile = genetic_algorithm.create_genetic_profile(parent1)

        assert profile.agent_id == parent1.agent_id
        assert profile.genetic_fitness > 0.0
        assert len(profile.personality_genes) == 5
        assert len(profile.capability_genes) > 0
        assert len(profile.behavioral_genes) > 0
