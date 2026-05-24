"""
HarnessAPI Core for unified Streaming APIs and MCP Tools.

Subclasses FastAPI to automatically discover and project Skills onto
HTTP (REST/SSE) and MCP transports from a single typed source of truth.
"""

import asyncio
import os
import importlib.util
import types
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Set
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError
try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

from ..core.skills import Skill, SkillMetadata, SkillInput, SkillOutput
from ..core.logger import get_agent_logger

class HarnessAPI(FastAPI):
    """
    Skill-First framework that derives HTTP and MCP interfaces from skill folders.
    """

    def __init__(self, agent_id: str, skills_dir: str = "skills", **kwargs):
        super().__init__(**kwargs)
        self.agent_id = agent_id
        self.skills_dir = skills_dir
        self.logger = get_agent_logger(agent_id, "harness_api")
        self.skills: Dict[str, Skill] = {}

        # Initialize MCP Server
        self.mcp = FastMCP(f"agent_{agent_id}_tools")

        # Discover and register skills
        self.discover_skills()

    def discover_skills(self):
        """Walk the skills directory and load all valid skill folders."""
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir)
            return

        path = Path(self.skills_dir)
        for folder in path.iterdir():
            if folder.is_dir() and (folder / "handler.py").exists() and (folder / "models.py").exists():
                try:
                    skill = self._load_skill(folder)
                    self._register_skill(skill)
                    self.logger.info(f"Discovered and registered skill: {skill.meta.name}")
                except Exception as e:
                    self.logger.error(f"Failed to load skill from {folder}: {e}")

    def _load_skill(self, folder: Path) -> Skill:
        """Load a Skill from a folder with module isolation."""
        name = folder.name

        # Create a synthetic package namespace for isolation
        pkg_name = f"_harness_skills.{name}"
        pkg = types.ModuleType(pkg_name)
        import sys
        sys.modules[pkg_name] = pkg

        # Load models
        models_spec = importlib.util.spec_from_file_location(f"{pkg_name}.models", folder / "models.py")
        models_mod = importlib.util.module_from_spec(models_spec)
        models_spec.loader.exec_module(models_mod)

        # Load handler
        handler_spec = importlib.util.spec_from_file_location(f"{pkg_name}.handler", folder / "handler.py")
        handler_mod = importlib.util.module_from_spec(handler_spec)
        handler_spec.loader.exec_module(handler_mod)

        # Parse skill.toml if exists
        meta_data = {"name": name, "description": handler_mod.handle.__doc__ or "No description"}
        if (folder / "skill.toml").exists():
            import toml
            with open(folder / "skill.toml", "r") as f:
                toml_data = toml.load(f)
                if "skill" in toml_data:
                    meta_data.update(toml_data["skill"])

        meta = SkillMetadata(**meta_data)

        return Skill(
            meta=meta,
            input_model=getattr(models_mod, "Input"),
            output_model=getattr(models_mod, "Output"),
            handler_func=getattr(handler_mod, "handle"),
            folder_path=str(folder)
        )

    def _register_skill(self, skill: Skill):
        """Register skill for both HTTP and MCP transports."""
        name = skill.meta.name
        self.skills[name] = skill

        # 1. HTTP Registration (POST /skills/{name})
        @self.post(f"/skills/{name}", tags=["Skills"], name=name)
        async def skill_endpoint(request: Request):
            body = await request.json()
            try:
                inp = skill.input_model.model_validate(body)
            except ValidationError as exc:
                raise HTTPException(status_code=422, detail=exc.errors())

            # Content Negotiation: SSE vs JSON
            accept_header = request.headers.get("accept", "")
            if "application/json" in accept_header:
                return await self._handle_json_request(skill, inp)
            else:
                return self._handle_sse_request(skill, inp)

        # 2. MCP Registration
        if skill.meta.is_mcp:
            self._register_mcp_tool(skill)

    async def _handle_json_request(self, skill: Skill, inp: SkillInput):
        """Handle standard JSON request-response."""
        if skill.is_streaming_handler():
            chunks = []
            async for chunk in skill.handler_func(inp):
                chunks.append(str(chunk))
            return {"chunks": chunks}
        else:
            result = await asyncio.wait_for(skill.handler_func(inp), timeout=skill.meta.timeout_secs)
            return result.model_dump()

    def _handle_sse_request(self, skill: Skill, inp: SkillInput):
        """Handle SSE streaming response."""
        async def event_generator():
            try:
                if skill.is_streaming_handler():
                    async for chunk in skill.handler_func(inp):
                        yield f"event: chunk\ndata: {chunk}\n\n"
                else:
                    result = await asyncio.wait_for(skill.handler_func(inp), timeout=skill.meta.timeout_secs)
                    yield f"event: result\ndata: {result.model_dump_json()}\n\n"
                yield "event: done\ndata: \n\n"
            except Exception as e:
                yield f"event: error\ndata: {str(e)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    def _register_mcp_tool(self, skill: Skill):
        """Register skill as an MCP tool using dynamic wrapper generation."""
        import inspect

        # Use dynamic compilation to propagate Pydantic types correctly to FastMCP
        globs = {
            "asyncio": asyncio,
            "Any": Any,
            "input_model": skill.input_model,
            "handler": skill.handler_func,
            "is_streaming": skill.is_streaming_handler(),
            "timeout": skill.meta.timeout_secs
        }

        src = (
            f"async def mcp_wrapper(input: input_model) -> Any:\n"
            f"    if is_streaming:\n"
            f"        chunks = []\n"
            f"        async for c in handler(input): chunks.append(str(c))\n"
            f"        return '\\n'.join(chunks)\n"
            f"    else:\n"
            f"        r = await asyncio.wait_for(handler(input), timeout)\n"
            f"        return r.model_dump()\n"
        )

        exec(compile(src, f"<mcp_wrapper_{skill.meta.name}>", "exec"), globs)
        mcp_wrapper = globs["mcp_wrapper"]
        mcp_wrapper.__name__ = skill.meta.name
        mcp_wrapper.__doc__ = skill.meta.description

        # Register with FastMCP
        self.mcp.tool(name=skill.meta.name, description=skill.meta.description)(mcp_wrapper)
