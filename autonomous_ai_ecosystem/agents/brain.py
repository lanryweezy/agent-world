"""
AI Brain integration layer for autonomous agents.

This module implements LLM integration, prompt engineering, and reasoning
capabilities for intelligent agent behavior and decision-making.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import openai
import anthropic

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from ..core.config import LLMConfig


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class ThoughtType(Enum):
    """Types of thoughts/reasoning."""
    ANALYSIS = "analysis"
    PLANNING = "planning"
    REFLECTION = "reflection"
    DECISION = "decision"
    CREATIVITY = "creativity"
    PROBLEM_SOLVING = "problem_solving"
    SOCIAL_REASONING = "social_reasoning"
    LEARNING = "learning"


@dataclass
class ThoughtProcess:
    """Represents a thought process with input, reasoning, and output."""
    thought_id: str
    thought_type: ThoughtType
    input_data: Dict[str, Any]
    context: Dict[str, Any]
    reasoning_steps: List[str]
    output: Dict[str, Any]
    confidence: float
    processing_time: float
    timestamp: datetime
    tokens_used: int = 0


@dataclass
class PromptTemplate:
    """Template for generating prompts."""
    template_id: str
    name: str
    template: str
    variables: List[str]
    thought_type: ThoughtType
    max_tokens: int = 1000
    temperature: float = 0.7


from ..agents.memory import MemorySystem

class AIBrain(AgentModule):
    """
    AI Brain that integrates with various LLM providers for reasoning,
    planning, and intelligent behavior generation.
    """
    
    def __init__(self, agent_id: str, config: LLMConfig, personality_traits: Dict[str, float], memory_system: MemorySystem):
        super().__init__(agent_id)
        self.config = config
        self.personality_traits = personality_traits
        self.memory = memory_system
        self.logger = get_agent_logger(agent_id, "ai_brain")
        
        # LLM clients
        self.openai_client: Optional[openai.AsyncOpenAI] = None
        self.anthropic_client: Optional[anthropic.AsyncAnthropic] = None
        
        # Prompt templates
        self.prompt_templates = self._initialize_prompt_templates()
        
        # Thought history
        self.thought_history: List[ThoughtProcess] = []
        self.max_thought_history = 1000
        
        # Performance tracking
        self.brain_stats = {
            "total_thoughts": 0,
            "successful_thoughts": 0,
            "failed_thoughts": 0,
            "total_tokens_used": 0,
            "average_processing_time": 0.0,
            "thought_types": {},
            "provider_usage": {}
        }
        
        # Context memory for conversations
        self.conversation_context: Dict[str, List[Dict[str, str]]] = {}
        self.max_context_length = 10
        
        self.logger.info(f"AI Brain initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the AI brain and LLM connections."""
        try:
            # Initialize LLM clients
            if self.config.provider == LLMProvider.OPENAI.value and self.config.api_key:
                self.openai_client = openai.AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.api_base
                )
            
            if self.config.provider == LLMProvider.ANTHROPIC.value and self.config.api_key:
                self.anthropic_client = anthropic.AsyncAnthropic(
                    api_key=self.config.api_key
                )
            
            # Test connection
            await self._test_llm_connection()
            
            self.logger.info("AI Brain initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI brain: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the AI brain gracefully."""
        try:
            # Save thought patterns if needed
            await self._save_thought_patterns()
            
            self.logger.info("AI Brain shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during AI brain shutdown: {e}")
    
    async def think(
        self,
        thought_type: ThoughtType,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None
    ) -> ThoughtProcess:
        """
        Process a thought using the AI brain.
        
        Args:
            thought_type: Type of thinking to perform
            input_data: Input data for the thought process
            context: Additional context information
            template_id: Specific template to use (optional)
            
        Returns:
            ThoughtProcess with reasoning and output
        """
        try:
            start_time = time.time()
            thought_id = f"thought_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.thought_history)}"
            
            # Select appropriate template
            template = self._select_template(thought_type, template_id)
            if not template:
                raise ValueError(f"No template found for thought type: {thought_type}")

            # --- Dynamic Context Engineering ---
            # Retrieve relevant experiences to inject into the context
            task_description = input_data.get("situation") or input_data.get("objective") or input_data.get("problem")
            if task_description and hasattr(self, 'memory'):
                experiences = await self.memory.retrieve_relevant_experiences(task_description)
                if experiences:
                    # Add experiences to the context for prompt generation
                    context = context or {}
                    context["experiences"] = [exp.content for exp in experiences]
            # --- End Dynamic Context Engineering ---

            # Generate prompt
            prompt = self._generate_prompt(template, input_data, context or {})
            
            # Get LLM response
            response = await self._get_llm_response(prompt, template)
            
            # Parse response
            reasoning_steps, output = self._parse_llm_response(response, thought_type)
            
            # Calculate confidence
            confidence = self._calculate_confidence(response, reasoning_steps)
            
            processing_time = time.time() - start_time
            
            # Create thought process
            thought_process = ThoughtProcess(
                thought_id=thought_id,
                thought_type=thought_type,
                input_data=input_data,
                context=context or {},
                reasoning_steps=reasoning_steps,
                output=output,
                confidence=confidence,
                processing_time=processing_time,
                timestamp=datetime.now(),
                tokens_used=self._estimate_tokens(prompt + str(response))
            )
            
            # Store thought
            self._store_thought(thought_process)
            
            # Update statistics
            self._update_brain_stats(thought_process, success=True)
            
            log_agent_event(
                self.agent_id,
                "thought_processed",
                {
                    "thought_id": thought_id,
                    "thought_type": thought_type.value,
                    "confidence": confidence,
                    "processing_time": processing_time,
                    "tokens_used": thought_process.tokens_used
                }
            )
            
            self.logger.debug(f"Processed thought: {thought_type.value} (confidence: {confidence:.2f})")
            
            return thought_process
            
        except Exception as e:
            self.logger.error(f"Failed to process thought: {e}")
            self._update_brain_stats(None, success=False)
            raise
    
    async def analyze_situation(
        self,
        situation: str,
        available_data: Dict[str, Any],
        goals: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze a situation and provide insights.
        
        Args:
            situation: Description of the situation
            available_data: Available data for analysis
            goals: Current goals to consider
            
        Returns:
            Analysis results with insights and recommendations
        """
        try:
            input_data = {
                "situation": situation,
                "available_data": available_data,
                "goals": goals,
                "personality": self.personality_traits
            }
            
            thought = await self.think(ThoughtType.ANALYSIS, input_data)
            
            return {
                "analysis": thought.output.get("analysis", ""),
                "insights": thought.output.get("insights", []),
                "recommendations": thought.output.get("recommendations", []),
                "confidence": thought.confidence,
                "reasoning": thought.reasoning_steps
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze situation: {e}")
            return {"error": str(e)}
    
    async def make_plan(
        self,
        objective: str,
        constraints: List[str],
        resources: Dict[str, Any],
        time_horizon: str = "short_term"
    ) -> Dict[str, Any]:
        """
        Create a plan to achieve an objective.
        
        Args:
            objective: What to achieve
            constraints: Limitations and constraints
            resources: Available resources
            time_horizon: Planning time horizon
            
        Returns:
            Plan with steps, timeline, and resource allocation
        """
        try:
            input_data = {
                "objective": objective,
                "constraints": constraints,
                "resources": resources,
                "time_horizon": time_horizon,
                "personality": self.personality_traits
            }
            
            thought = await self.think(ThoughtType.PLANNING, input_data)
            
            return {
                "plan": thought.output.get("plan", {}),
                "steps": thought.output.get("steps", []),
                "timeline": thought.output.get("timeline", ""),
                "resource_allocation": thought.output.get("resource_allocation", {}),
                "risks": thought.output.get("risks", []),
                "confidence": thought.confidence
            }
            
        except Exception as e:
            self.logger.error(f"Failed to make plan: {e}")
            return {"error": str(e)}
    
    async def reflect_on_experience(
        self,
        experience: Dict[str, Any],
        outcomes: Dict[str, Any],
        emotions: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Reflect on an experience and extract learnings.
        
        Args:
            experience: Description of the experience
            outcomes: What happened as a result
            emotions: Emotional response to the experience
            
        Returns:
            Reflection with learnings and insights
        """
        try:
            input_data = {
                "experience": experience,
                "outcomes": outcomes,
                "emotions": emotions,
                "personality": self.personality_traits
            }
            
            thought = await self.think(ThoughtType.REFLECTION, input_data)
            
            return {
                "reflection": thought.output.get("reflection", ""),
                "learnings": thought.output.get("learnings", []),
                "future_actions": thought.output.get("future_actions", []),
                "emotional_insights": thought.output.get("emotional_insights", {}),
                "confidence": thought.confidence
            }
            
        except Exception as e:
            self.logger.error(f"Failed to reflect on experience: {e}")
            return {"error": str(e)}
    
    async def solve_problem(
        self,
        problem: str,
        context: Dict[str, Any],
        constraints: List[str] = None
    ) -> Dict[str, Any]:
        """
        Solve a problem using reasoning and creativity.
        
        Args:
            problem: Problem description
            context: Problem context and background
            constraints: Any constraints on the solution
            
        Returns:
            Problem solution with reasoning
        """
        try:
            input_data = {
                "problem": problem,
                "context": context,
                "constraints": constraints or [],
                "personality": self.personality_traits
            }
            
            thought = await self.think(ThoughtType.PROBLEM_SOLVING, input_data)
            
            return {
                "solution": thought.output.get("solution", ""),
                "alternatives": thought.output.get("alternatives", []),
                "implementation_steps": thought.output.get("implementation_steps", []),
                "potential_issues": thought.output.get("potential_issues", []),
                "confidence": thought.confidence
            }
            
        except Exception as e:
            self.logger.error(f"Failed to solve problem: {e}")
            return {"error": str(e)}
    
    async def generate_creative_content(
        self,
        content_type: str,
        theme: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate creative content.
        
        Args:
            content_type: Type of content to generate
            theme: Theme or topic
            requirements: Specific requirements
            
        Returns:
            Generated creative content
        """
        try:
            input_data = {
                "content_type": content_type,
                "theme": theme,
                "requirements": requirements,
                "personality": self.personality_traits
            }
            
            thought = await self.think(ThoughtType.CREATIVITY, input_data)
            
            return {
                "content": thought.output.get("content", ""),
                "style": thought.output.get("style", ""),
                "inspiration": thought.output.get("inspiration", ""),
                "confidence": thought.confidence
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate creative content: {e}")
            return {"error": str(e)}
    
    async def reason_about_social_situation(
        self,
        situation: str,
        participants: List[Dict[str, Any]],
        social_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reason about social situations and relationships.
        
        Args:
            situation: Social situation description
            participants: Information about participants
            social_context: Social context and norms
            
        Returns:
            Social reasoning and recommendations
        """
        try:
            input_data = {
                "situation": situation,
                "participants": participants,
                "social_context": social_context,
                "personality": self.personality_traits
            }
            
            thought = await self.think(ThoughtType.SOCIAL_REASONING, input_data)
            
            return {
                "social_analysis": thought.output.get("social_analysis", ""),
                "relationship_insights": thought.output.get("relationship_insights", {}),
                "recommended_actions": thought.output.get("recommended_actions", []),
                "potential_outcomes": thought.output.get("potential_outcomes", []),
                "confidence": thought.confidence
            }
            
        except Exception as e:
            self.logger.error(f"Failed to reason about social situation: {e}")
            return {"error": str(e)}
    
    def get_recent_thoughts(self, hours: int = 24, thought_type: Optional[ThoughtType] = None) -> List[ThoughtProcess]:
        """
        Get recent thoughts from the thought history.
        
        Args:
            hours: Time window in hours
            thought_type: Filter by thought type (optional)
            
        Returns:
            List of recent ThoughtProcess objects
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            recent_thoughts = [
                thought for thought in self.thought_history
                if thought.timestamp >= cutoff_time
            ]
            
            if thought_type:
                recent_thoughts = [
                    thought for thought in recent_thoughts
                    if thought.thought_type == thought_type
                ]
            
            return sorted(recent_thoughts, key=lambda t: t.timestamp, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to get recent thoughts: {e}")
            return []
    
    def get_brain_statistics(self) -> Dict[str, Any]:
        """
        Get AI brain performance statistics.
        
        Returns:
            Dictionary with brain statistics
        """
        return {
            **self.brain_stats,
            "thought_history_size": len(self.thought_history),
            "active_conversations": len(self.conversation_context),
            "available_templates": len(self.prompt_templates)
        }    
# Private helper methods
    
    def _initialize_prompt_templates(self) -> Dict[str, PromptTemplate]:
        """Initialize prompt templates for different thought types."""
        templates = {}
        
        # Analysis template
        templates["analysis"] = PromptTemplate(
            template_id="analysis",
            name="Situation Analysis",
            template="""
You are an AI agent with the following personality traits: {personality}

Analyze the following situation:
Situation: {situation}
Available Data: {available_data}
Current Goals: {goals}

Please provide:
1. A thorough analysis of the situation
2. Key insights and observations
3. Recommendations for action
4. Potential risks or opportunities

Format your response as JSON with keys: analysis, insights, recommendations, risks
""",
            variables=["personality", "situation", "available_data", "goals"],
            thought_type=ThoughtType.ANALYSIS,
            max_tokens=1500,
            temperature=0.7
        )
        
        # Planning template
        templates["planning"] = PromptTemplate(
            template_id="planning",
            name="Strategic Planning",
            template="""
You are an AI agent with personality traits: {personality}

Create a plan for the following objective:
Objective: {objective}
Constraints: {constraints}
Available Resources: {resources}
Time Horizon: {time_horizon}

Please provide:
1. A detailed plan with clear steps
2. Timeline and milestones
3. Resource allocation
4. Risk assessment
5. Success metrics

Format your response as JSON with keys: plan, steps, timeline, resource_allocation, risks, success_metrics
""",
            variables=["personality", "objective", "constraints", "resources", "time_horizon"],
            thought_type=ThoughtType.PLANNING,
            max_tokens=2000,
            temperature=0.6
        )
        
        # Reflection template
        templates["reflection"] = PromptTemplate(
            template_id="reflection",
            name="Experience Reflection",
            template="""
You are an AI agent with personality traits: {personality}

Reflect on the following experience:
Experience: {experience}
Outcomes: {outcomes}
Emotional Response: {emotions}

Please provide:
1. Deep reflection on what happened
2. Key learnings and insights
3. How this affects future actions
4. Emotional insights and growth

Format your response as JSON with keys: reflection, learnings, future_actions, emotional_insights
""",
            variables=["personality", "experience", "outcomes", "emotions"],
            thought_type=ThoughtType.REFLECTION,
            max_tokens=1500,
            temperature=0.8
        )
        
        # Problem solving template
        templates["problem_solving"] = PromptTemplate(
            template_id="problem_solving",
            name="Problem Solving",
            template="""
You are an AI agent with personality traits: {personality}

Solve the following problem:
Problem: {problem}
Context: {context}
Constraints: {constraints}

Please provide:
1. A clear solution to the problem
2. Alternative approaches
3. Step-by-step implementation
4. Potential issues and mitigation

Format your response as JSON with keys: solution, alternatives, implementation_steps, potential_issues
""",
            variables=["personality", "problem", "context", "constraints"],
            thought_type=ThoughtType.PROBLEM_SOLVING,
            max_tokens=1800,
            temperature=0.7
        )
        
        # Creativity template
        templates["creativity"] = PromptTemplate(
            template_id="creativity",
            name="Creative Generation",
            template="""
You are an AI agent with personality traits: {personality}

Generate creative content:
Content Type: {content_type}
Theme: {theme}
Requirements: {requirements}

Please provide:
1. Original creative content
2. Style and approach explanation
3. Sources of inspiration
4. Creative rationale

Format your response as JSON with keys: content, style, inspiration, rationale
""",
            variables=["personality", "content_type", "theme", "requirements"],
            thought_type=ThoughtType.CREATIVITY,
            max_tokens=2000,
            temperature=0.9
        )
        
        # Social reasoning template
        templates["social_reasoning"] = PromptTemplate(
            template_id="social_reasoning",
            name="Social Situation Analysis",
            template="""
You are an AI agent with personality traits: {personality}

Analyze this social situation:
Situation: {situation}
Participants: {participants}
Social Context: {social_context}

Please provide:
1. Analysis of social dynamics
2. Relationship insights
3. Recommended actions
4. Potential outcomes

Format your response as JSON with keys: social_analysis, relationship_insights, recommended_actions, potential_outcomes
""",
            variables=["personality", "situation", "participants", "social_context"],
            thought_type=ThoughtType.SOCIAL_REASONING,
            max_tokens=1600,
            temperature=0.7
        )
        
        return templates
    
    async def _test_llm_connection(self) -> None:
        """Test connection to the configured LLM provider."""
        try:
            test_prompt = "Hello, this is a connection test. Please respond with 'Connection successful.'"
            
            if self.config.provider == LLMProvider.OPENAI.value and self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=50,
                    temperature=0.1
                )
                if response.choices[0].message.content:
                    self.logger.info("OpenAI connection test successful")
                    
            elif self.config.provider == LLMProvider.ANTHROPIC.value and self.anthropic_client:
                response = await self.anthropic_client.messages.create(
                    model=self.config.model,
                    max_tokens=50,
                    temperature=0.1,
                    messages=[{"role": "user", "content": test_prompt}]
                )
                if response.content:
                    self.logger.info("Anthropic connection test successful")
            
        except Exception as e:
            self.logger.warning(f"LLM connection test failed: {e}")
    
    def _select_template(self, thought_type: ThoughtType, template_id: Optional[str] = None) -> Optional[PromptTemplate]:
        """Select appropriate template for thought type."""
        if template_id and template_id in self.prompt_templates:
            return self.prompt_templates[template_id]
        
        # Find template by thought type
        for template in self.prompt_templates.values():
            if template.thought_type == thought_type:
                return template
        
        return None
    
    def _generate_prompt(self, template: PromptTemplate, input_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate prompt from template and data."""
        try:
            # Combine input data and context
            all_data = {**input_data, **context}

            experience_prompt_section = ""
            if "experiences" in all_data and all_data["experiences"]:
                experience_list = "\n".join(f"- {exp}" for exp in all_data["experiences"])
                experience_prompt_section = f"""
Before you begin, review these past experiences. They are your accumulated wisdom.

--- PAST EXPERIENCES ---
{experience_list}
--- END OF EXPERIENCES ---

"""
            
            # Format template with data
            main_prompt = template.template.format(**all_data)
            
            return f"{experience_prompt_section}{main_prompt}"
            
        except KeyError as e:
            self.logger.error(f"Missing template variable: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to generate prompt: {e}")
            raise
    
    async def _get_llm_response(self, prompt: str, template: PromptTemplate) -> str:
        """Get response from the configured LLM provider."""
        try:
            if self.config.provider == LLMProvider.OPENAI.value and self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model=self.config.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=template.max_tokens,
                    temperature=template.temperature,
                    timeout=self.config.timeout
                )
                
                self.brain_stats["provider_usage"]["openai"] = self.brain_stats["provider_usage"].get("openai", 0) + 1
                
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content
                else:
                    raise ValueError("Empty response from OpenAI")
                    
            elif self.config.provider == LLMProvider.ANTHROPIC.value and self.anthropic_client:
                response = await self.anthropic_client.messages.create(
                    model=self.config.model,
                    max_tokens=template.max_tokens,
                    temperature=template.temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                self.brain_stats["provider_usage"]["anthropic"] = self.brain_stats["provider_usage"].get("anthropic", 0) + 1
                
                if response.content and response.content[0].text:
                    return response.content[0].text
                else:
                    raise ValueError("Empty response from Anthropic")
            
            else:
                raise ValueError(f"Unsupported or unconfigured LLM provider: {self.config.provider}")
                
        except Exception as e:
            self.logger.error(f"Failed to get LLM response: {e}")
            raise
    
    def _parse_llm_response(self, response: str, thought_type: ThoughtType) -> Tuple[List[str], Dict[str, Any]]:
        """Parse LLM response into reasoning steps and structured output."""
        try:
            # Try to parse as JSON first
            try:
                json_response = json.loads(response)
                if isinstance(json_response, dict):
                    reasoning_steps = json_response.get("reasoning", ["LLM provided structured response"])
                    output = {k: v for k, v in json_response.items() if k != "reasoning"}
                    return reasoning_steps, output
            except json.JSONDecodeError:
                pass
            
            # Fallback to text parsing
            reasoning_steps = [f"LLM reasoning for {thought_type.value}"]
            output = {"response": response}
            
            return reasoning_steps, output
            
        except Exception as e:
            self.logger.error(f"Failed to parse LLM response: {e}")
            return ["Failed to parse response"], {"error": str(e)}
    
    def _calculate_confidence(self, response: str, reasoning_steps: List[str]) -> float:
        """Calculate confidence score for the thought process."""
        try:
            confidence = 0.5  # Base confidence
            
            # Length-based confidence
            if len(response) > 100:
                confidence += 0.1
            if len(response) > 500:
                confidence += 0.1
            
            # Structure-based confidence
            if len(reasoning_steps) > 1:
                confidence += 0.1
            
            # JSON structure bonus
            try:
                json.loads(response)
                confidence += 0.2
            except json.JSONDecodeError:
                pass
            
            return min(1.0, max(0.0, confidence))
            
        except Exception:
            return 0.5
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Simple estimation: ~4 characters per token
        return len(text) // 4
    
    def _store_thought(self, thought: ThoughtProcess) -> None:
        """Store thought in history."""
        self.thought_history.append(thought)
        
        # Maintain history size
        if len(self.thought_history) > self.max_thought_history:
            self.thought_history.pop(0)
    
    def _update_brain_stats(self, thought: Optional[ThoughtProcess], success: bool) -> None:
        """Update brain performance statistics."""
        self.brain_stats["total_thoughts"] += 1
        
        if success and thought:
            self.brain_stats["successful_thoughts"] += 1
            self.brain_stats["total_tokens_used"] += thought.tokens_used
            
            # Update average processing time
            old_avg = self.brain_stats["average_processing_time"]
            count = self.brain_stats["successful_thoughts"]
            self.brain_stats["average_processing_time"] = (
                (old_avg * (count - 1) + thought.processing_time) / count
            )
            
            # Update thought type counts
            thought_type = thought.thought_type.value
            self.brain_stats["thought_types"][thought_type] = (
                self.brain_stats["thought_types"].get(thought_type, 0) + 1
            )
        else:
            self.brain_stats["failed_thoughts"] += 1
    
    async def _save_thought_patterns(self) -> None:
        """Save thought patterns for future learning."""
        # Placeholder for saving thought patterns
        pass