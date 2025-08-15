#!/usr/bin/env python3
"""
Simple test to check emotion engine and decision maker initialization.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from autonomous_ai_ecosystem.core.config import Config
from autonomous_ai_ecosystem.utils.generators import generate_personality_traits
from autonomous_ai_ecosystem.agents.emotions import EmotionEngine
from autonomous_ai_ecosystem.agents.decision_making import DecisionMaker
from autonomous_ai_ecosystem.agents.memory import MemorySystem

def test_initialization():
    """Test emotion engine and decision maker initialization."""
    print("Testing emotion engine and decision maker initialization...")
    
    # Create test data
    agent_id = "test_agent_001"
    personality_traits = generate_personality_traits()
    print(f"Generated personality traits: {personality_traits}")
    
    # Create config
    config = Config.load_from_file("config.json")
    
    try:
        # Create memory system
        memory_system = MemorySystem(agent_id, config.data_directory)
        print("Memory system created successfully")
        
        # Create emotion engine
        emotion_engine = EmotionEngine(agent_id, personality_traits)
        print("Emotion engine created successfully")
        
        # Check if emotion engine has personality attribute
        if hasattr(emotion_engine, 'personality'):
            print("Emotion engine has personality attribute")
            print(f"Personality traits: {emotion_engine.personality.traits}")
        else:
            print("ERROR: Emotion engine does not have personality attribute")
            return False
            
        # Create decision maker
        decision_maker = DecisionMaker(agent_id, emotion_engine, memory_system)
        print("Decision maker created successfully")
        
        # Check if decision maker has motivation state
        if hasattr(decision_maker, 'motivation_state'):
            print("Decision maker has motivation state")
            print(f"Motivations: {decision_maker.motivation_state.primary_motivations}")
        else:
            print("ERROR: Decision maker does not have motivation state")
            return False
            
        print("All tests passed!")
        return True
        
    except Exception as e:
        print(f"Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_initialization()
    sys.exit(0 if success else 1)