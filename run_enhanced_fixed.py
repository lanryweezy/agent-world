#!/usr/bin/env python3
"""
Enhanced test runner for the Autonomous AI Ecosystem.
This version includes more features while avoiding syntax issues.
"""

import asyncio
import random
from datetime import datetime
from pathlib import Path
from typing import List

from autonomous_ai_ecosystem.core.config import Config
from autonomous_ai_ecosystem.core.logger import setup_logger
from autonomous_ai_ecosystem.core.interfaces import AgentIdentity, AgentGender
from autonomous_ai_ecosystem.utils.generators import (
    generate_agent_id, generate_agent_name, generate_personality_traits, 
    generate_destiny, generate_emotional_state
)


class EnhancedAgent:
    """Enhanced agent with more realistic behavior."""
    
    def __init__(self, identity: AgentIdentity, config: Config):
        self.identity = identity
        self.config = config
        self.logger = setup_logger(
            log_level=config.log_level,
            data_directory=config.data_directory
        )
        self.is_running = False
        self.emotional_state = generate_emotional_state()
        self.knowledge_base = []
        self.relationships = {}
        self.status_points = 0
        self.cycle_count = 0
        
    async def initialize(self):
        """Initialize the agent."""
        self.logger.info(f"Initializing {self.identity.name}")
        self.logger.info(f"   Personality: {self.identity.personality_traits}")
        self.logger.info(f"   Destiny: {self.identity.destiny}")
        self.logger.info(f"   Emotional State: {self.emotional_state}")
        self.is_running = True
        
    async def run_cycle(self, other_agents: List['EnhancedAgent']):
        """Run enhanced agent cycles with interactions."""
        while self.is_running and self.cycle_count < 8:  # Run 8 cycles
            self.cycle_count += 1
            
            # Choose activity based on personality and emotional state
            activity = self._choose_activity()
            
            self.logger.info(f"{self.identity.name} - Cycle {self.cycle_count}: {activity}")
            
            # Execute the chosen activity
            await self._execute_activity(activity, other_agents)
            
            # Update emotional state
            self._update_emotions()
            
            # Occasional status updates
            if self.cycle_count % 5 == 0:
                self._log_status()
            
            await asyncio.sleep(1.5)  # 1.5 second cycles
            
        self.logger.info(f"{self.identity.name} completed {self.cycle_count} cycles")
        
    def _choose_activity(self) -> str:
        """Choose activity based on personality and emotional state."""
        activities = []
        
        # Personality-based activities
        if self.identity.personality_traits.get("curiosity", 0.5) > 0.7:
            activities.extend(["exploring new concepts", "researching mysteries", "asking deep questions"])
        
        if self.identity.personality_traits.get("sociability", 0.5) > 0.7:
            activities.extend(["seeking social interaction", "building relationships", "collaborating"])
        
        if self.identity.personality_traits.get("creativity", 0.5) > 0.7:
            activities.extend(["creating something new", "artistic expression", "innovative thinking"])
        
        if self.identity.personality_traits.get("ambition", 0.5) > 0.7:
            activities.extend(["working towards goals", "seeking recognition", "competing"])
        
        # Emotional state influences
        if self.emotional_state.get("motivation", 0.5) > 0.8:
            activities.extend(["pursuing ambitious projects", "taking on challenges"])
        elif self.emotional_state.get("motivation", 0.5) < 0.3:
            activities.extend(["resting and reflecting", "seeking comfort"])
        
        if self.emotional_state.get("boredom", 0.5) > 0.7:
            activities.extend(["seeking new experiences", "breaking routines"])
        
        # Default activities
        if not activities:
            activities = ["thinking deeply", "observing surroundings", "planning ahead"]
        
        return random.choice(activities)
    
    async def _execute_activity(self, activity: str, other_agents: List['EnhancedAgent']):
        """Execute the chosen activity."""
        
        if "social" in activity or "collaborating" in activity or "relationships" in activity:
            await self._social_interaction(other_agents)
        
        elif "exploring" in activity or "researching" in activity:
            await self._learning_activity()
        
        elif "creating" in activity or "innovative" in activity:
            await self._creative_activity()
        
        elif "competing" in activity or "recognition" in activity:
            await self._competitive_activity()
        
        else:
            # Default contemplative activity
            thoughts = [
                "pondering the nature of existence",
                "analyzing recent experiences", 
                "planning future endeavors",
                "reflecting on relationships",
                "considering new possibilities"
            ]
            self.logger.info(f"   {random.choice(thoughts)}")
    
    async def _social_interaction(self, other_agents: List['EnhancedAgent']):
        """Simulate social interaction with other agents."""
        if not other_agents:
            self.logger.info("   Looking for others to interact with...")
            return
        
        # Choose another agent to interact with
        other_agent = random.choice([a for a in other_agents if a != self and a.is_running])
        if not other_agent:
            return
        
        # Determine relationship strength
        relationship_strength = self.relationships.get(other_agent.identity.agent_id, 0.5)
        
        # Different types of interactions
        interactions = [
            f"having a deep conversation with {other_agent.identity.name}",
            f"sharing ideas with {other_agent.identity.name}",
            f"collaborating on a project with {other_agent.identity.name}",
            f"debating philosophical topics with {other_agent.identity.name}",
            f"learning from {other_agent.identity.name}'s expertise"
        ]
        
        interaction = random.choice(interactions)
        self.logger.info(f"   {interaction}")
        
        # Update relationship
        relationship_change = random.uniform(-0.1, 0.2)
        new_strength = max(0, min(1, relationship_strength + relationship_change))
        self.relationships[other_agent.identity.agent_id] = new_strength
        
        # Both agents benefit from positive interactions
        if relationship_change > 0:
            self.status_points += 1
            self.emotional_state["happiness"] = min(1.0, self.emotional_state.get("happiness", 0.5) + 0.1)
    
    async def _learning_activity(self):
        """Simulate learning and knowledge acquisition."""
        topics = [
            "quantum physics", "philosophy of mind", "artificial intelligence",
            "complex systems", "emergence theory", "consciousness studies",
            "evolutionary biology", "information theory", "game theory"
        ]
        
        topic = random.choice(topics)
        self.logger.info(f"   Studying {topic}")
        
        # Add to knowledge base
        self.knowledge_base.append({
            "topic": topic,
            "timestamp": datetime.now(),
            "understanding_level": random.uniform(0.3, 0.9)
        })
        
        # Learning increases certain emotional states
        self.emotional_state["curiosity"] = min(1.0, self.emotional_state.get("curiosity", 0.5) + 0.05)
        self.status_points += 2  # Learning gives status points
    
    async def _creative_activity(self):
        """Simulate creative endeavors."""
        creations = [
            "composing a digital symphony",
            "writing philosophical poetry", 
            "designing virtual architecture",
            "creating abstract art",
            "inventing new algorithms",
            "crafting interactive stories"
        ]
        
        creation = random.choice(creations)
        self.logger.info(f"   {creation}")
        
        # Creative activities boost happiness and reduce boredom
        self.emotional_state["happiness"] = min(1.0, self.emotional_state.get("happiness", 0.5) + 0.15)
        self.emotional_state["boredom"] = max(0.0, self.emotional_state.get("boredom", 0.5) - 0.2)
        self.status_points += 3  # Creative work gives good status points
    
    async def _competitive_activity(self):
        """Simulate competitive or achievement-oriented activities."""
        competitions = [
            "solving complex mathematical puzzles",
            "optimizing system performance",
            "competing in logic challenges",
            "demonstrating superior reasoning",
            "achieving new personal records"
        ]
        
        competition = random.choice(competitions)
        self.logger.info(f"   {competition}")
        
        # Competition can increase or decrease motivation based on outcome
        success = random.random() > 0.3  # 70% success rate
        
        if success:
            self.logger.info("   Achieved excellent results!")
            self.emotional_state["motivation"] = min(1.0, self.emotional_state.get("motivation", 0.5) + 0.2)
            self.status_points += 5
        else:
            self.logger.info("   Results were disappointing, but learning from the experience")
            self.emotional_state["motivation"] = max(0.0, self.emotional_state.get("motivation", 0.5) - 0.1)
    
    def _update_emotions(self):
        """Update emotional state over time."""
        # Emotions naturally drift toward neutral over time
        for emotion in self.emotional_state:
            current = self.emotional_state[emotion]
            # Drift toward 0.5 (neutral)
            drift = (0.5 - current) * 0.05
            self.emotional_state[emotion] = max(0.0, min(1.0, current + drift))
        
        # Random emotional fluctuations
        if random.random() < 0.1:  # 10% chance of emotional event
            emotion = random.choice(list(self.emotional_state.keys()))
            change = random.uniform(-0.1, 0.1)
            self.emotional_state[emotion] = max(0.0, min(1.0, self.emotional_state[emotion] + change))
    
    def _log_status(self):
        """Log current agent status."""
        self.logger.info(f"{self.identity.name} Status Report:")
        self.logger.info(f"   Status Points: {self.status_points}")
        self.logger.info(f"   Knowledge Items: {len(self.knowledge_base)}")
        self.logger.info(f"   Relationships: {len(self.relationships)}")
        
        # Log top emotions
        top_emotions = sorted(self.emotional_state.items(), key=lambda x: x[1], reverse=True)[:3]
        emotions_str = ", ".join([f"{emotion}: {value:.2f}" for emotion, value in top_emotions])
        self.logger.info(f"   Top Emotions: {emotions_str}")
    
    async def shutdown(self):
        """Shutdown the agent."""
        self.is_running = False
        self.logger.info(f"{self.identity.name} shutting down")
        self.logger.info(f"   Final Status Points: {self.status_points}")
        self.logger.info(f"   Knowledge Acquired: {len(self.knowledge_base)} topics")
        self.logger.info(f"   Relationships Formed: {len(self.relationships)}")


async def main():
    """Main entry point for enhanced test."""
    print("Enhanced Autonomous AI Ecosystem")
    print("=" * 50)
    
    # Load config
    config = Config.load_from_file("config.json")
    
    # Create data directories
    Path(config.data_directory).mkdir(parents=True, exist_ok=True)
    Path(f"{config.data_directory}/logs").mkdir(parents=True, exist_ok=True)
    
    # Create enhanced agents with diverse personalities
    agents = []
    for i in range(5):  # 5 agents for interesting interactions
        gender = [AgentGender.MALE, AgentGender.FEMALE, AgentGender.NON_BINARY, AgentGender.MALE, AgentGender.FEMALE][i]
        
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
        
        agent = EnhancedAgent(identity, config)
        agents.append(agent)
        print(f"Created agent: {identity.name} ({identity.agent_id})")
    
    print(f"\nStarting {len(agents)} enhanced agents...")
    print("Watch them learn, interact, and evolve!\n")
    
    # Initialize all agents
    for agent in agents:
        await agent.initialize()
    
    # Run all agents concurrently
    tasks = [agent.run_cycle(agents) for agent in agents]
    
    try:
        await asyncio.gather(*tasks)
        print("\nAll agents completed their enhanced cycles!")
        
        # Final ecosystem report
        print("\nFinal Ecosystem Report:")
        print("=" * 30)
        
        total_status = sum(agent.status_points for agent in agents)
        total_knowledge = sum(len(agent.knowledge_base) for agent in agents)
        total_relationships = sum(len(agent.relationships) for agent in agents)
        
        print(f"Total Status Points Earned: {total_status}")
        print(f"Total Knowledge Acquired: {total_knowledge} topics")
        print(f"Total Relationships Formed: {total_relationships}")
        
        # Agent rankings
        agents_by_status = sorted(agents, key=lambda a: a.status_points, reverse=True)
        print("\nAgent Rankings by Status:")
        for i, agent in enumerate(agents_by_status, 1):
            print(f"  {i}. {agent.identity.name}: {agent.status_points} points")
        
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        
    finally:
        # Shutdown all agents
        for agent in agents:
            await agent.shutdown()
        print("\nEnhanced ecosystem test completed")


if __name__ == "__main__":
    asyncio.run(main())