"""
Unit tests for AI brain and reasoning systems.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.agents.brain import (
    AIBrain, ThoughtProcess, ThoughtType, LLMProvider
)
from autonomous_ai_ecosystem.agents.reasoning import (
    ReasoningEngine, PlanningEngine, Goal, Plan, ReasoningType, 
    PlanningStrategy, GoalStatus
)
from autonomous_ai_ecosystem.core.config import LLMConfig
from autonomous_ai_ecosystem.utils.generators import generate_personality_traits
from autonomous_ai_ecosystem.agents.memory import MemorySystem


class TestAIBrain:
    """Test cases for AIBrain."""
    
    def setup_method(self):
        """Set up test environment."""
        self.agent_id = "test_agent_brain"
        self.config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="test_key",
            max_tokens=1000,
            temperature=0.7
        )
        self.personality_traits = generate_personality_traits()

        # Mock MemorySystem
        self.mock_memory_system = Mock(spec=MemorySystem)
        self.mock_memory_system.retrieve_relevant_experiences = AsyncMock(return_value=[])

        self.ai_brain = AIBrain(self.agent_id, self.config, self.personality_traits, self.mock_memory_system)
    
    def teardown_method(self):
        """Clean up test environment."""
        import asyncio
        if hasattr(self, 'ai_brain'):
            asyncio.create_task(self.ai_brain.shutdown())
    
    @pytest.mark.asyncio
    async def test_ai_brain_initialization(self):
        """Test AI brain initialization."""
        # Mock the LLM connection test
        with patch.object(self.ai_brain, '_test_llm_connection'):
            await self.ai_brain.initialize()
        
        assert self.ai_brain.agent_id == self.agent_id
        assert self.ai_brain.config == self.config
        assert self.ai_brain.personality_traits == self.personality_traits
        assert len(self.ai_brain.prompt_templates) > 0
    
    @pytest.mark.asyncio
    async def test_thought_process_with_mocked_llm(self):
        """Test thought processing with mocked LLM response."""
        # Mock LLM response
        mock_response = '{"analysis": "Test analysis", "insights": ["Insight 1", "Insight 2"], "recommendations": ["Rec 1"]}'
        
        with patch.object(self.ai_brain, '_get_llm_response', return_value=mock_response):
            input_data = {
                "situation": "Test situation",
                "available_data": {"key": "value"},
                "goals": ["Test goal"]
            }
            
            thought = await self.ai_brain.think(ThoughtType.ANALYSIS, input_data)
            
            assert thought.thought_type == ThoughtType.ANALYSIS
            assert thought.input_data == input_data
            assert thought.confidence > 0.0
            assert len(thought.reasoning_steps) > 0
            assert "analysis" in thought.output
    
    @pytest.mark.asyncio
    async def test_situation_analysis(self):
        """Test situation analysis functionality."""
        # Mock the think method
        mock_thought = ThoughtProcess(
            thought_id="test_thought",
            thought_type=ThoughtType.ANALYSIS,
            input_data={},
            context={},
            reasoning_steps=["Step 1", "Step 2"],
            output={
                "analysis": "Test analysis",
                "insights": ["Insight 1"],
                "recommendations": ["Recommendation 1"]
            },
            confidence=0.8,
            processing_time=1.0,
            timestamp=datetime.now()
        )
        
        with patch.object(self.ai_brain, 'think', return_value=mock_thought):
            result = await self.ai_brain.analyze_situation(
                situation="Test situation",
                available_data={"data": "value"},
                goals=["Goal 1"]
            )
            
            assert "analysis" in result
            assert "insights" in result
            assert "recommendations" in result
            assert "confidence" in result
            assert result["confidence"] == 0.8
    
    def test_prompt_template_initialization(self):
        """Test prompt template initialization."""
        templates = self.ai_brain.prompt_templates
        
        assert len(templates) > 0
        assert "analysis" in templates
        assert "planning" in templates
        assert "reflection" in templates
        
        # Check template structure
        analysis_template = templates["analysis"]
        assert analysis_template.thought_type == ThoughtType.ANALYSIS
        assert len(analysis_template.variables) > 0
        assert analysis_template.max_tokens > 0
    
    def test_recent_thoughts_retrieval(self):
        """Test recent thoughts retrieval."""
        # Add mock thoughts to history
        mock_thoughts = []
        for i in range(5):
            thought = ThoughtProcess(
                thought_id=f"thought_{i}",
                thought_type=ThoughtType.ANALYSIS,
                input_data={},
                context={},
                reasoning_steps=[],
                output={},
                confidence=0.7,
                processing_time=1.0,
                timestamp=datetime.now() - timedelta(hours=i)
            )
            mock_thoughts.append(thought)
        
        self.ai_brain.thought_history.extend(mock_thoughts)
        
        # Get recent thoughts
        recent = self.ai_brain.get_recent_thoughts(hours=3)
        
        # Should get thoughts from last 3 hours (thoughts 0, 1, 2)
        assert len(recent) == 3
        
        # Should be sorted by timestamp (most recent first)
        assert recent[0].thought_id == "thought_0"
        assert recent[1].thought_id == "thought_1"
        assert recent[2].thought_id == "thought_2"
    
    def test_brain_statistics(self):
        """Test brain statistics calculation."""
        # Add some mock data
        self.ai_brain.brain_stats["total_thoughts"] = 10
        self.ai_brain.brain_stats["successful_thoughts"] = 8
        self.ai_brain.brain_stats["failed_thoughts"] = 2
        
        stats = self.ai_brain.get_brain_statistics()
        
        expected_fields = [
            "total_thoughts", "successful_thoughts", "failed_thoughts",
            "total_tokens_used", "average_processing_time", "thought_types",
            "provider_usage", "thought_history_size", "active_conversations",
            "available_templates"
        ]
        
        for field in expected_fields:
            assert field in stats
        
        assert stats["total_thoughts"] == 10
        assert stats["successful_thoughts"] == 8
        assert stats["failed_thoughts"] == 2

    @pytest.mark.asyncio
    async def test_think_with_dynamic_context(self):
        """Test that the think method retrieves and uses experiences."""
        # --- Arrange ---
        # Mock the LLM response
        mock_llm_response = '{"analysis": "Analysis based on experience", "insights": []}'

        # Mock the experience to be returned by the memory system
        mock_experience = Mock()
        mock_experience.content = "Past experience: Complex calculations are prone to error."
        self.mock_memory_system.retrieve_relevant_experiences.return_value = [mock_experience]

        input_data = {
            "situation": "A complex calculation is required.",
            "available_data": {},
            "goals": []
        }

        # --- Act ---
        # We patch _get_llm_response to avoid actual API calls
        # and _generate_prompt to capture the prompt that was built.
        with patch.object(self.ai_brain, '_get_llm_response', return_value=mock_llm_response) as mock_get_response, \
             patch.object(self.ai_brain, '_generate_prompt', wraps=self.ai_brain._generate_prompt) as mock_generate_prompt:

            await self.ai_brain.think(ThoughtType.ANALYSIS, input_data)

            # --- Assert ---
            # 1. Assert that the memory system was queried
            self.mock_memory_system.retrieve_relevant_experiences.assert_awaited_once_with("A complex calculation is required.")

            # 2. Assert that the generated prompt includes the experience
            mock_generate_prompt.assert_called_once()
            final_prompt = mock_generate_prompt.call_args[0][0].template.format(**mock_generate_prompt.call_args[0][1])

            # We can't easily get the final formatted string back due to the new implementation,
            # so we'll check the context passed to the generation function.
            passed_context = mock_generate_prompt.call_args[0][2]
            assert "experiences" in passed_context
            assert passed_context["experiences"][0] == mock_experience.content