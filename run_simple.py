#!/usr/bin/env python3
"""
Simple test runner for the Autonomous AI Ecosystem.
This version bypasses complex modules to get the basic system running.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from autonomous_ai_ecosystem.core.config import Config
from autonomous_ai_ecosystem.core.logger import setup_logger
from autonomous_ai_ecosystem.core.interfaces import AgentIdentity, AgentGender
from autonomous_ai_ecosystem.utils.generators import (
    generate_agent_id, generate_agent_name, generate_personality_traits, 
    generate_destiny
)


class SimpleAgent:
    """Simplified agent for testing."""
    
    def __init__(self, identity: AgentIdentity, config: Config):
        self.identity = identity
        self.config = config
        self.logger = setup_logger(
            log_level=config.log_level,
            data_directory=config.data_directory
        )
        self.is_running = False
        
    async def initialize(self):
        """Initialize the agent."""
        self.logger.info(f"Initializing agent: {self.identity.name}")
        # Simple initialization without complex modules
        self.is_running = True
        
    async def run_cycle(self):
        """Run a simple agent cycle."""
        cycle_count = 0
        while self.is_running and cycle_count < 10:  # Run 10 cycles then stop
            self.logger.info(f"Agent {self.identity.name} - Cycle {cycle_count + 1}")
            
            # Simulate some agent activity
            await asyncio.sleep(2)  # 2 second cycles
            
            # Log some activity
            if cycle_count % 3 == 0:
                self.logger.info(f"{self.identity.name} is thinking deeply...")
            elif cycle_count % 3 == 1:
                self.logger.info(f"{self.identity.name} is exploring new ideas...")
            else:
                self.logger.info(f"{self.identity.name} is reflecting on experiences...")
                
            cycle_count += 1
            
        self.logger.info(f"Agent {self.identity.name} completed {cycle_count} cycles")
        
    async def shutdown(self):
        """Shutdown the agent."""
        self.is_running = False
        self.logger.info(f"Agent {self.identity.name} shutting down")


async def main():
    """Main entry point for simple test."""
    print("🤖 Simple Autonomous AI Ecosystem Test")
    print("=" * 50)
    
    # Load config
    config = Config.load_from_file("config.json")
    
    # Create data directories
    Path(config.data_directory).mkdir(parents=True, exist_ok=True)
    Path(f"{config.data_directory}/logs").mkdir(parents=True, exist_ok=True)
    
    # Create simple agents
    agents = []
    for i in range(3):  # Just 3 agents for testing
        gender = [AgentGender.MALE, AgentGender.FEMALE, AgentGender.NON_BINARY][i]
        
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
        
        agent = SimpleAgent(identity, config)
        agents.append(agent)
        print(f"Created agent: {identity.name} ({identity.agent_id})")
    
    print(f"\nStarting {len(agents)} agents...")
    
    # Initialize all agents
    for agent in agents:
        await agent.initialize()
    
    # Run all agents concurrently
    tasks = [agent.run_cycle() for agent in agents]
    
    try:
        await asyncio.gather(*tasks)
        print("\n✅ All agents completed their cycles!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Shutdown requested by user")
        
    finally:
        # Shutdown all agents
        for agent in agents:
            await agent.shutdown()
        print("👋 Simple ecosystem test completed")


if __name__ == "__main__":
    asyncio.run(main())