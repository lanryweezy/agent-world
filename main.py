#!/usr/bin/env python3
"""
Main entry point for the Autonomous AI Ecosystem.

This script initializes and runs the AI ecosystem with multiple autonomous agents
that learn, evolve, and interact with each other while serving the human creator.
"""

import asyncio
import sys
import signal
from pathlib import Path
from typing import List
from datetime import datetime

from autonomous_ai_ecosystem.core.config import Config
from autonomous_ai_ecosystem.core.logger import setup_logger
from autonomous_ai_ecosystem.core.agent_core import AgentCore
from autonomous_ai_ecosystem.core.interfaces import AgentIdentity, AgentGender
from autonomous_ai_ecosystem.utils.generators import (
    generate_agent_id, generate_agent_name, generate_personality_traits, 
    generate_destiny
)


class EcosystemManager:
    """Main manager for the autonomous AI ecosystem."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = Config.load_from_file(config_path)
        self.logger = setup_logger(
            log_level=self.config.log_level,
            data_directory=self.config.data_directory
        )
        
        self.agents: List[AgentCore] = []
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        # Validate configuration
        issues = self.config.validate()
        if issues:
            self.logger.error(f"Configuration issues found: {issues}")
            sys.exit(1)
        
        self.logger.info(f"Ecosystem manager initialized: {self.config.ecosystem_name}")
    
    async def initialize(self) -> None:
        """Initialize the ecosystem and create initial agents."""
        self.logger.info("Initializing autonomous AI ecosystem")
        
        try:
            # Create data directories
            self._create_directories()
            
            # Create initial agents
            await self._create_initial_agents()
            
            # Initialize shared services (placeholder for now)
            await self._initialize_services()
            
            self.logger.info(f"Ecosystem initialized with {len(self.agents)} agents")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ecosystem: {e}")
            raise
    
    async def run(self) -> None:
        """Run the main ecosystem loop."""
        self.logger.info("Starting autonomous AI ecosystem")
        self.is_running = True
        
        try:
            # Start all agents
            agent_tasks = []
            for agent in self.agents:
                await agent.initialize()
                task = asyncio.create_task(agent.run_daily_cycle())
                agent_tasks.append(task)
            
            self.logger.info(f"All {len(self.agents)} agents started")
            
            # Wait for shutdown signal or agent completion
            done, pending = await asyncio.wait(
                agent_tasks + [asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            self.logger.error(f"Error in ecosystem main loop: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Shutdown the ecosystem gracefully."""
        if not self.is_running:
            return
        
        self.logger.info("Shutting down autonomous AI ecosystem")
        self.is_running = False
        
        # Shutdown all agents
        for agent in self.agents:
            try:
                await agent.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down agent {agent.identity.agent_id}: {e}")
        
        self.logger.info("Ecosystem shutdown completed")
    
    def _create_directories(self) -> None:
        """Create necessary directories for the ecosystem."""
        directories = [
            self.config.data_directory,
            f"{self.config.data_directory}/logs",
            f"{self.config.data_directory}/agents",
            f"{self.config.data_directory}/knowledge",
            f"{self.config.data_directory}/models",
            f"{self.config.data_directory}/backups"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        self.logger.debug(f"Created directories: {directories}")
    
    async def _create_initial_agents(self) -> None:
        """Create the initial set of agents."""
        self.logger.info(f"Creating {self.config.initial_agent_count} initial agents")
        
        for i in range(self.config.initial_agent_count):
            # Generate agent identity
            gender = AgentGender.MALE if i % 3 == 0 else (
                AgentGender.FEMALE if i % 3 == 1 else AgentGender.NON_BINARY
            )
            
            identity = AgentIdentity(
                agent_id=generate_agent_id(),
                name=generate_agent_name(gender),
                gender=gender,
                personality_traits=generate_personality_traits(),
                destiny=generate_destiny(),
                birth_timestamp=datetime.now(),
                parent_agents=[],
                generation=0
            )
            
            # Create agent core
            agent = AgentCore(identity, self.config)
            self.agents.append(agent)
            
            self.logger.info(f"Created agent: {identity.name} ({identity.agent_id})")
    
    async def _initialize_services(self) -> None:
        """Initialize shared services."""
        # Placeholder for shared services initialization
        # This will be implemented in later tasks
        self.logger.debug("Shared services initialization (placeholder)")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point."""
    print("Autonomous AI Ecosystem")
    print("=" * 50)
    
    # Create and run ecosystem
    ecosystem = EcosystemManager()
    
    try:
        # Setup signal handlers
        ecosystem._setup_signal_handlers()
        
        # Initialize and run
        await ecosystem.initialize()
        await ecosystem.run()
        
    except KeyboardInterrupt:
        print("\n⚠️  Shutdown requested by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        print("👋 Ecosystem shutdown complete")


if __name__ == "__main__":
    # Run the ecosystem
    asyncio.run(main())