"""
Unit tests for the ReflectionEngine module.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from autonomous_ai_ecosystem.agents.reflection import ReflectionEngine
from autonomous_ai_ecosystem.agents.brain import AIBrain
from autonomous_ai_ecosystem.agents.memory import MemorySystem
from autonomous_ai_ecosystem.core.interfaces import Memory


class TestReflectionEngine(unittest.TestCase):

    def setUp(self):
        """Set up the test environment."""
        self.agent_id = "test_agent_001"

        # Mock the dependencies
        self.mock_brain = MagicMock(spec=AIBrain)
        self.mock_memory = MagicMock(spec=MemorySystem)

        # Configure async mocks for the methods that will be called
        self.mock_brain.generate_text = AsyncMock()
        self.mock_memory.store_memory = AsyncMock()

        # Instantiate the ReflectionEngine with mocks
        self.reflection_engine = ReflectionEngine(
            agent_id=self.agent_id,
            brain=self.mock_brain,
            memory=self.mock_memory
        )

    def test_initialization(self):
        """Test that the ReflectionEngine initializes correctly."""
        self.assertEqual(self.reflection_engine.agent_id, self.agent_id)
        self.assertIsNotNone(self.reflection_engine.brain)
        self.assertIsNotNone(self.reflection_engine.memory)

    def test_self_reflection(self):
        """Test the self_reflect method."""
        # --- Arrange ---
        task = {"description": "Analyze market trends."}
        outcome = {
            "actions_taken": ["searched for 'market trends 2024'"],
            "reasoning_trace": "I decided to search for recent trends.",
            "result": "The market is volatile."
        }
        expected_experience = "When markets are volatile, it's important to diversify research sources."

        # Configure the mock brain to return a specific experience
        self.mock_brain.generate_text.return_value = expected_experience

        # --- Act ---
        result = asyncio.run(self.reflection_engine.self_reflect(task, outcome))

        # --- Assert ---
        # Check that the brain was called to generate text
        self.mock_brain.generate_text.assert_called_once()

        # Check that the memory system was called to store the experience
        self.mock_memory.store_memory.assert_called_once()

        # Check the content of the stored memory
        stored_memory_arg = self.mock_memory.store_memory.call_args[0][0]
        self.assertIsInstance(stored_memory_arg, Memory)
        self.assertEqual(stored_memory_arg.content, expected_experience)
        self.assertEqual(stored_memory_arg.memory_type, "procedural")
        self.assertIn("self_reflection", stored_memory_arg.tags)

        # Check the return value
        self.assertEqual(result, expected_experience)

    def test_verified_reflection_success(self):
        """Test the verified_reflect method for a successful outcome."""
        # --- Arrange ---
        task = {"description": "Calculate 2 + 2."}
        outcome = {"result": 4}
        ground_truth = 4
        expected_experience = "For simple arithmetic, direct calculation is consistently effective."

        # Configure the mock brain
        self.mock_brain.generate_text.return_value = expected_experience

        # --- Act ---
        result = asyncio.run(self.reflection_engine.verified_reflect(task, outcome, ground_truth))

        # --- Assert ---
        self.mock_brain.generate_text.assert_called_once()
        self.mock_memory.store_memory.assert_called_once()

        stored_memory_arg = self.mock_memory.store_memory.call_args[0][0]
        self.assertEqual(stored_memory_arg.content, expected_experience)
        self.assertIn("verified_reflection", stored_memory_arg.tags)
        self.assertEqual(result, expected_experience)

        # Verify that the prompt sent to the brain indicates success
        prompt = self.mock_brain.generate_text.call_args[0][0]
        self.assertIn("Success: Yes", prompt)

    def test_verified_reflection_failure(self):
        """Test the verified_reflect method for a failed outcome."""
        # --- Arrange ---
        task = {"description": "What is the capital of Australia?"}
        outcome = {"result": "Sydney"}
        ground_truth = "Canberra"
        expected_experience = "When answering factual questions, always verify with a reliable source instead of relying on common misconceptions."

        # Configure the mock brain
        self.mock_brain.generate_text.return_value = expected_experience

        # --- Act ---
        result = asyncio.run(self.reflection_engine.verified_reflect(task, outcome, ground_truth))

        # --- Assert ---
        self.mock_brain.generate_text.assert_called_once()
        self.mock_memory.store_memory.assert_called_once()

        stored_memory_arg = self.mock_memory.store_memory.call_args[0][0]
        self.assertEqual(stored_memory_arg.content, expected_experience)
        self.assertEqual(result, expected_experience)

        # Verify that the prompt sent to the brain indicates failure
        prompt = self.mock_brain.generate_text.call_args[0][0]
        self.assertIn("Success: No", prompt)


if __name__ == '__main__':
    unittest.main()
