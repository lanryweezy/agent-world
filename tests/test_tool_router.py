"""
Unit tests for the ToolRouter module.
"""

import unittest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock

from autonomous_ai_ecosystem.tools.tool_router import ToolRouter
from autonomous_ai_ecosystem.core.interfaces import ToolInterface
from autonomous_ai_ecosystem.agents.brain import AIBrain

# Mock Tool for testing purposes
class MockTool(ToolInterface):
    def __init__(self, name, description):
        self._name = name
        self._description = description
        self.execute_mock = AsyncMock(return_value="Mock tool executed successfully")

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def execute(self, **kwargs) -> str:
        return await self.execute_mock(**kwargs)


class TestToolRouter(unittest.TestCase):

    def setUp(self):
        """Set up the test environment."""
        self.mock_brain = MagicMock(spec=AIBrain)
        self.mock_brain.generate_text = AsyncMock()

        self.tool1 = MockTool("tool1", "Description for tool 1, used for task A.")
        self.tool2 = MockTool("tool2", "Description for tool 2, used for task B.")

        self.tool_router = ToolRouter(
            tools=[self.tool1, self.tool2],
            brain=self.mock_brain,
            agent_id="test_agent_router"
        )

    def test_initialization(self):
        """Test that the ToolRouter initializes correctly."""
        self.assertIn("tool1", self.tool_router.tools)
        self.assertIn("tool2", self.tool_router.tools)
        self.assertEqual(len(self.tool_router.tools), 2)

    def test_prompt_construction(self):
        """Test that the prompt is constructed correctly."""
        request = "Perform task A."
        prompt = self.tool_router._construct_prompt(request)

        self.assertIn(request, prompt)
        self.assertIn(self.tool1.name, prompt)
        self.assertIn(self.tool1.description, prompt)
        self.assertIn(self.tool2.name, prompt)
        self.assertIn(self.tool2.description, prompt)
        self.assertIn("You must respond with a JSON object", prompt)

    def test_successful_routing_and_execution(self):
        """Test a successful request routing and tool execution."""
        # --- Arrange ---
        request = "Please use tool 1 for something."
        tool_response = {
            "tool_name": "tool1",
            "arguments": {"param1": "value1"}
        }
        self.mock_brain.generate_text.return_value = json.dumps(tool_response)

        # --- Act ---
        result = asyncio.run(self.tool_router.route_request(request))

        # --- Assert ---
        # Brain was called to select a tool
        self.mock_brain.generate_text.assert_called_once()

        # The correct tool's execute method was called with the correct arguments
        self.tool1.execute_mock.assert_awaited_once_with(param1="value1")

        # The other tool was not called
        self.tool2.execute_mock.assert_not_awaited()

        # The result from the tool is returned
        self.assertEqual(result, "Mock tool executed successfully")

    def test_routing_with_no_tool_found(self):
        """Test routing when the LLM determines no tool is suitable."""
        # --- Arrange ---
        request = "Do something impossible."
        tool_response = {
            "tool_name": "no_tool_found",
            "arguments": {"reason": "No tool can do the impossible."}
        }
        self.mock_brain.generate_text.return_value = json.dumps(tool_response)

        # --- Act ---
        result = asyncio.run(self.tool_router.route_request(request))

        # --- Assert ---
        self.assertIn("Error: No suitable tool found", result)
        self.tool1.execute_mock.assert_not_awaited()
        self.tool2.execute_mock.assert_not_awaited()

    def test_routing_with_malformed_json(self):
        """Test routing when the LLM returns malformed JSON."""
        # --- Arrange ---
        request = "Another request."
        self.mock_brain.generate_text.return_value = "This is not JSON"

        # --- Act ---
        result = asyncio.run(self.tool_router.route_request(request))

        # --- Assert ---
        self.assertIn("Error: Could not process the tool selection response", result)
        self.tool1.execute_mock.assert_not_awaited()

    def test_routing_with_unknown_tool(self):
        """Test routing when the LLM returns an unknown tool name."""
        # --- Arrange ---
        request = "A request for a tool that doesn't exist."
        tool_response = {"tool_name": "unknown_tool", "arguments": {}}
        self.mock_brain.generate_text.return_value = json.dumps(tool_response)

        # --- Act ---
        result = asyncio.run(self.tool_router.route_request(request))

        # --- Assert ---
        self.assertIn("Error: No suitable tool found", result)
        self.tool1.execute_mock.assert_not_awaited()

if __name__ == '__main__':
    unittest.main()
