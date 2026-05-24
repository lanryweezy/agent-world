"""
Skill-First models and structure for the HARNESSAPI framework.

Defines the base classes for Skill input/output and the Skill metadata
container, ensuring a unified schema for HTTP and MCP transports.
"""

from typing import List, Dict, Any, Optional, Callable, Type
from dataclasses import dataclass, field
from pydantic import BaseModel
from enum import Enum

class SkillInput(BaseModel):
    """Base class for all skill inputs."""
    pass

class SkillOutput(BaseModel):
    """Base class for all skill outputs."""
    pass

@dataclass
class SkillMetadata:
    """Metadata for a skill."""
    name: str
    description: str
    is_mcp: bool = True
    tags: List[str] = field(default_factory=list)
    timeout_secs: int = 30

@dataclass
class Skill:
    """
    Complete definition of a Skill, derived from a skill folder.
    Contains handler logic and Pydantic schemas.
    """
    meta: SkillMetadata
    input_model: Type[SkillInput]
    output_model: Type[SkillOutput]
    handler_func: Callable
    is_streaming: bool = False

    # Path to the source folder
    folder_path: Optional[str] = None

    def is_streaming_handler(self) -> bool:
        """Check if the handler is a streaming (async generator) function."""
        import inspect
        return inspect.isasyncgenfunction(self.handler_func)

    async def effective_handler(self, input_data: SkillInput):
        """Invoke the skill handler."""
        return self.handler_func(input_data)
