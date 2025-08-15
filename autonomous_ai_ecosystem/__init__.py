"""
Autonomous AI Ecosystem - A self-evolving multi-agent AI system.

This package implements a complex ecosystem where AI agents continuously learn,
evolve, interact, and provide services while building collective intelligence.
"""

__version__ = "0.1.0"
__author__ = "AI Ecosystem Creator"

from .core.agent_core import AgentCore
from .core.interfaces import AgentIdentity, AgentState, AgentMessage

__all__ = [
    "AgentCore",
    "AgentIdentity", 
    "AgentState",
    "AgentMessage"
]