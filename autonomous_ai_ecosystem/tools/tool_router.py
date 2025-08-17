"""
Tool Router for the Autonomous AI Ecosystem.

This module provides a ToolRouter that can take a natural language request
and route it to the most appropriate registered tool.
"""

import json
from typing import List, Dict, Any, Optional

from ..core.interfaces import ToolInterface
from ..agents.brain import AIBrain
from ..core.logger import get_agent_logger

class ToolRouter:
    """
    A class to manage and route requests to a set of tools.

    This router uses an LLM to select the best tool for a given natural
    language request based on the tools' descriptions.
    """

    def __init__(self, tools: List[ToolInterface], brain: AIBrain, agent_id: str = "system"):
        """
        Initializes the ToolRouter.

        Args:
            tools: A list of tool objects that implement the ToolInterface.
            brain: An AIBrain instance to use for LLM-based routing.
            agent_id: The ID of the agent this router belongs to, for logging.
        """
        self.tools = {tool.name: tool for tool in tools}
        self.brain = brain
        self.logger = get_agent_logger(agent_id, "tool_router")
        self.logger.info(f"ToolRouter initialized with tools: {list(self.tools.keys())}")

    def _construct_prompt(self, request: str) -> str:
        """
        Constructs the prompt for the LLM to select a tool.

        Args:
            request: The natural language user request.

        Returns:
            A formatted prompt string.
        """
        tool_descriptions = "\n".join(
            f"- {name}: {tool.description}" for name, tool in self.tools.items()
        )

        prompt = f"""
        You are an expert tool router for an autonomous AI agent.
        Your task is to select the most appropriate tool to handle the user's request
        and determine the arguments to pass to that tool.

        The user's request is: "{request}"

        Here are the available tools:
        {tool_descriptions}

        Based on the user's request, you must respond with a JSON object containing two keys:
        1. "tool_name": The name of the selected tool.
        2. "arguments": A dictionary of the arguments required by the tool.

        For example, if the user asks "What is the weather in London?", and you have a 'get_weather' tool,
        your response should be:
        {{
          "tool_name": "get_weather",
          "arguments": {{
            "city": "London"
          }}
        }}

        If no tool seems appropriate, respond with:
        {{
          "tool_name": "no_tool_found",
          "arguments": {{
            "reason": "I could not find an appropriate tool to handle this request."
          }}
        }}

        Now, process the user's request and provide the JSON response.
        """
        return prompt

    async def route_request(self, request: str) -> Any:
        """
        Routes a natural language request to the appropriate tool and executes it.

        Args:
            request: The natural language request from the agent.

        Returns:
            The result of the executed tool, or an error message if routing fails.
        """
        self.logger.info(f"Routing request: '{request}'")
        prompt = self._construct_prompt(request)

        try:
            # Use the brain to get the tool selection in JSON format
            response_text = await self.brain.generate_text(prompt, max_tokens=300)

            # Clean up potential markdown code blocks
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()

            response_json = json.loads(response_text)

            tool_name = response_json.get("tool_name")
            arguments = response_json.get("arguments", {})

            if not tool_name or tool_name not in self.tools:
                self.logger.warning(f"No suitable tool found for request: '{request}'")
                return f"Error: No suitable tool found. Reason: {arguments.get('reason', 'N/A')}"

            selected_tool = self.tools[tool_name]
            self.logger.info(f"Selected tool '{tool_name}' with arguments: {arguments}")

            # Execute the selected tool
            result = await selected_tool.execute(**arguments)
            return result

        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode LLM response into JSON: {response_text}")
            return "Error: Could not process the tool selection response."
        except Exception as e:
            self.logger.error(f"An error occurred during tool routing: {e}")
            return f"Error: An unexpected error occurred: {e}"
