"""
Web-related tools for the Autonomous AI Ecosystem.

This module provides tool wrappers that conform to the ToolInterface
for web browsing and searching functionalities.
"""

from typing import Any, Dict

from ..core.interfaces import ToolInterface
from ..learning.web_browser import WebBrowser

class WebSearchTool(ToolInterface):
    """
    A tool for searching the web and browsing pages.

    This tool wraps the WebBrowser module to make it compatible with the
    ToolRouter.
    """

    def __init__(self, web_browser: WebBrowser):
        """
        Initializes the WebSearchTool.

        Args:
            web_browser: An instance of the WebBrowser module.
        """
        self._web_browser = web_browser

    @property
    def name(self) -> str:
        """The unique name of the tool."""
        return "web_search"

    @property
    def description(self) -> str:
        """A description of what the tool does."""
        return (
            "Searches the web for a given query, browses the top results, "
            "and returns a summary of their content. Use this to find information, "
            "research topics, or answer questions about recent events."
        )

    async def execute(self, query: str, num_pages: int = 3) -> Dict[str, str]:
        """
        Executes a web search for the given query.

        Args:
            query: The search query string.
            num_pages: The number of top search results to browse.

        Returns:
            A dictionary where keys are the URLs of the browsed pages and
            values are their content.
        """
        if not hasattr(self._web_browser, 'search_and_browse'):
            return {"error": "The provided web browser object does not have a 'search_and_browse' method."}

        return await self._web_browser.search_and_browse(query, num_pages=num_pages)
