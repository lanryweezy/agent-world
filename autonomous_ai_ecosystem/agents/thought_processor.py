"""
Thought processing pipeline for autonomous AI agents.

This module implements a comprehensive thought processing system that integrates
reasoning, planning, and decision-making capabilities for intelligent agent behavior.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .brain import AIBrain, ThoughtType, ThoughtProcess
from .reasoning import ReasoningEngine, PlanningEngine, ReasoningType
from .daily_planner import DailyPlanner, ActivityType
from .emotions import EmotionEngine
from .memory import MemorySystem


class ThoughtPriority(Enum):
    """Priority levels for thoughts."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    BACKGROUND = 1


class ThoughtTrigger(Enum):
    """What triggered a thought process."""
    EXTERNAL_EVENT = "external_event"
    INTERNAL_STATE = "internal_state"
    SCHEDULED = "scheduled"
    GOAL_DRIVEN = "goal_driven"
    REACTIVE = "reactive"
    PROACTIVE = "proactive"


@dataclass
class ThoughtRequest:
    """Represents a request for thought processing."""
    request_id: str
    trigger: ThoughtTrigger
    priority: ThoughtPriority
    context: Dict[str, Any]
    required_capabilities: List[str]
    deadline: Optional[datetime] = None
    related_goals: List[str] = field(default_factory=list)
    emotional_context: Dict[str, float] = field(default_factory=dict)
    memory_context: List[str] = field(default_factory=list)


@dataclass
class ThoughtResult:
    """Result of thought processing."""
    request_id: str
    thought_processes: List[ThoughtProcess]
    reasoning_chains: List[Any]  # ReasoningChain objects
    decisions_made: List[Dict[str, Any]]
    actions_planned: List[Dict[str, Any]]
    insights_gained: List[str]
    confidence: float
    processing_time: float
    resources_used: Dict[str, float]
    follow_up_thoughts: List[str] = field(default_factory=list)


class ThoughtProcessor(AgentModule):
    """
    Comprehensive thought processing system that orchestrates reasoning,
    planning, and decision-making for intelligent agent behavior.
    """
    
    def __init__(
        self,
        agent_id: str,
        ai_brain: AIBrain,
        reasoning_engine: ReasoningEngine,
        planning_engine: PlanningEngine,
        daily_planner: DailyPlanner,
        emotion_engine: EmotionEngine,
        memory_system: MemorySystem,
        personality_traits: Dict[str, float]
    ):
        super().__init__(agent_id)
        self.ai_brain = ai_brain
        self.reasoning_engine = reasoning_engine
        self.planning_engine = planning_engine
        self.daily_planner = daily_planner
        self.emotion_engine = emotion_engine
        self.memory_system = memory_system
        self.personality_traits = personality_traits
        self.logger = get_agent_logger(agent_id, "thought_processor")
        
        # Thought processing queue
        self.thought_queue: List[ThoughtRequest] = []
        self.processing_lock = asyncio.Lock()
        self.max_queue_size = 100
        
        # Processing history
        self.thought_history: List[ThoughtResult] = []
        self.max_history_size = 500
        
        # Processing statistics
        self.processing_stats = {
            "total_thoughts_processed": 0,
            "successful_processes": 0,
            "failed_processes": 0,
            "average_processing_time": 0.0,
            "thought_types_processed": {},
            "trigger_types": {},
            "priority_distribution": {}
        }
        
        # Background processing task
        self.background_task: Optional[asyncio.Task] = None
        self.processing_active = False
        
        self.logger.info(f"Thought processor initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the thought processor."""
        try:
            # Start background processing
            self.processing_active = True
            self.background_task = asyncio.create_task(self._background_processing_loop())
            
            self.logger.info("Thought processor initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize thought processor: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the thought processor gracefully."""
        try:
            # Stop background processing
            self.processing_active = False
            if self.background_task:
                self.background_task.cancel()
                try:
                    await self.background_task
                except asyncio.CancelledError:
                    pass
            
            # Process remaining thoughts in queue
            await self._process_remaining_thoughts()
            
            self.logger.info("Thought processor shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during thought processor shutdown: {e}")
    
    async def submit_thought_request(self, request: ThoughtRequest) -> str:
        """
        Submit a thought request for processing.
        
        Args:
            request: ThoughtRequest to process
            
        Returns:
            Request ID for tracking
        """
        try:
            async with self.processing_lock:
                if len(self.thought_queue) >= self.max_queue_size:
                    # Remove lowest priority item
                    self.thought_queue.sort(key=lambda r: r.priority.value)
                    removed = self.thought_queue.pop(0)
                    self.logger.warning(f"Queue full, removed request: {removed.request_id}")
                
                self.thought_queue.append(request)
                
                # Sort by priority
                self.thought_queue.sort(key=lambda r: r.priority.value, reverse=True)
            
            log_agent_event(
                self.agent_id,
                "thought_request_submitted",
                {
                    "request_id": request.request_id,
                    "trigger": request.trigger.value,
                    "priority": request.priority.value,
                    "queue_size": len(self.thought_queue)
                }
            )
            
            self.logger.debug(f"Submitted thought request: {request.request_id}")
            
            return request.request_id
            
        except Exception as e:
            self.logger.error(f"Failed to submit thought request: {e}")
            raise
    
    async def process_immediate_thought(self, request: ThoughtRequest) -> ThoughtResult:
        """
        Process a thought request immediately (bypassing queue).
        
        Args:
            request: ThoughtRequest to process immediately
            
        Returns:
            ThoughtResult with processing results
        """
        try:
            start_time = datetime.now()
            
            # Process the thought request
            result = await self._process_thought_request(request)
            
            # Record processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time = processing_time
            
            # Store in history
            self._store_thought_result(result)
            
            # Update statistics
            self._update_processing_stats(result, success=True)
            
            log_agent_event(
                self.agent_id,
                "immediate_thought_processed",
                {
                    "request_id": request.request_id,
                    "processing_time": processing_time,
                    "confidence": result.confidence,
                    "insights_count": len(result.insights_gained)
                }
            )
            
            self.logger.info(f"Processed immediate thought: {request.request_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process immediate thought: {e}")
            self._update_processing_stats(None, success=False)
            raise
    
    async def think_about_situation(
        self,
        situation: str,
        context: Dict[str, Any] = None,
        priority: ThoughtPriority = ThoughtPriority.MEDIUM
    ) -> ThoughtResult:
        """
        Think about a specific situation comprehensively.
        
        Args:
            situation: Description of the situation
            context: Additional context information
            priority: Priority level for processing
            
        Returns:
            ThoughtResult with comprehensive analysis
        """
        try:
            request = ThoughtRequest(
                request_id=f"situation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                trigger=ThoughtTrigger.EXTERNAL_EVENT,
                priority=priority,
                context={
                    "situation": situation,
                    "context": context or {},
                    "thinking_mode": "comprehensive_analysis"
                },
                required_capabilities=["analysis", "reasoning", "planning"],
                emotional_context=self.emotion_engine.get_current_emotional_state(),
                memory_context=await self._get_relevant_memories(situation)
            )
            
            return await self.process_immediate_thought(request)
            
        except Exception as e:
            self.logger.error(f"Failed to think about situation: {e}")
            raise
    
    async def plan_for_goal(
        self,
        goal_description: str,
        constraints: List[str] = None,
        deadline: Optional[datetime] = None
    ) -> ThoughtResult:
        """
        Create a comprehensive plan for achieving a goal.
        
        Args:
            goal_description: Description of the goal
            constraints: Any constraints to consider
            deadline: Optional deadline for the goal
            
        Returns:
            ThoughtResult with planning analysis
        """
        try:
            request = ThoughtRequest(
                request_id=f"goal_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                trigger=ThoughtTrigger.GOAL_DRIVEN,
                priority=ThoughtPriority.HIGH,
                context={
                    "goal": goal_description,
                    "constraints": constraints or [],
                    "deadline": deadline.isoformat() if deadline else None,
                    "thinking_mode": "goal_planning"
                },
                required_capabilities=["planning", "reasoning", "analysis"],
                deadline=deadline,
                emotional_context=self.emotion_engine.get_current_emotional_state()
            )
            
            return await self.process_immediate_thought(request)
            
        except Exception as e:
            self.logger.error(f"Failed to plan for goal: {e}")
            raise
    
    async def reflect_on_experience(
        self,
        experience: Dict[str, Any],
        outcomes: Dict[str, Any],
        emotions: Dict[str, float] = None
    ) -> ThoughtResult:
        """
        Reflect on an experience to extract learnings.
        
        Args:
            experience: Description of the experience
            outcomes: What happened as a result
            emotions: Emotional response to the experience
            
        Returns:
            ThoughtResult with reflection insights
        """
        try:
            request = ThoughtRequest(
                request_id=f"reflection_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                trigger=ThoughtTrigger.INTERNAL_STATE,
                priority=ThoughtPriority.MEDIUM,
                context={
                    "experience": experience,
                    "outcomes": outcomes,
                    "thinking_mode": "reflection"
                },
                required_capabilities=["reflection", "analysis", "learning"],
                emotional_context=emotions or self.emotion_engine.get_current_emotional_state()
            )
            
            return await self.process_immediate_thought(request)
            
        except Exception as e:
            self.logger.error(f"Failed to reflect on experience: {e}")
            raise
    
    async def solve_problem_creatively(
        self,
        problem: str,
        context: Dict[str, Any] = None,
        constraints: List[str] = None
    ) -> ThoughtResult:
        """
        Solve a problem using creative and analytical thinking.
        
        Args:
            problem: Problem description
            context: Problem context
            constraints: Any constraints on the solution
            
        Returns:
            ThoughtResult with problem solution
        """
        try:
            request = ThoughtRequest(
                request_id=f"problem_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                trigger=ThoughtTrigger.EXTERNAL_EVENT,
                priority=ThoughtPriority.HIGH,
                context={
                    "problem": problem,
                    "context": context or {},
                    "constraints": constraints or [],
                    "thinking_mode": "creative_problem_solving"
                },
                required_capabilities=["problem_solving", "creativity", "reasoning", "analysis"],
                emotional_context=self.emotion_engine.get_current_emotional_state(),
                memory_context=await self._get_relevant_memories(problem)
            )
            
            return await self.process_immediate_thought(request)
            
        except Exception as e:
            self.logger.error(f"Failed to solve problem creatively: {e}")
            raise
    
    def get_thought_queue_status(self) -> Dict[str, Any]:
        """Get current status of the thought processing queue."""
        priority_counts = {}
        trigger_counts = {}
        
        for request in self.thought_queue:
            priority = request.priority.value
            trigger = request.trigger.value
            
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        
        return {
            "queue_size": len(self.thought_queue),
            "max_queue_size": self.max_queue_size,
            "priority_distribution": priority_counts,
            "trigger_distribution": trigger_counts,
            "processing_active": self.processing_active
        }
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get thought processing statistics."""
        return {
            **self.processing_stats,
            "queue_status": self.get_thought_queue_status(),
            "history_size": len(self.thought_history)
        }
    
    # Private methods
    
    async def _background_processing_loop(self) -> None:
        """Background loop for processing thoughts from the queue."""
        while self.processing_active:
            try:
                # Process next thought in queue
                request = await self._get_next_thought_request()
                
                if request:
                    start_time = datetime.now()
                    
                    try:
                        result = await self._process_thought_request(request)
                        result.processing_time = (datetime.now() - start_time).total_seconds()
                        
                        self._store_thought_result(result)
                        self._update_processing_stats(result, success=True)
                        
                        self.logger.debug(f"Background processed thought: {request.request_id}")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to process background thought {request.request_id}: {e}")
                        self._update_processing_stats(None, success=False)
                
                else:
                    # No thoughts to process, wait a bit
                    await asyncio.sleep(1.0)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in background processing loop: {e}")
                await asyncio.sleep(5.0)  # Wait before retrying
    
    async def _get_next_thought_request(self) -> Optional[ThoughtRequest]:
        """Get the next thought request from the queue."""
        async with self.processing_lock:
            if self.thought_queue:
                return self.thought_queue.pop(0)
            return None
    
    async def _process_thought_request(self, request: ThoughtRequest) -> ThoughtResult:
        """Process a single thought request."""
        try:
            thought_processes = []
            reasoning_chains = []
            decisions_made = []
            actions_planned = []
            insights_gained = []
            
            # Determine processing strategy based on context
            thinking_mode = request.context.get("thinking_mode", "general")
            
            if thinking_mode == "comprehensive_analysis":
                result = await self._process_comprehensive_analysis(request)
            elif thinking_mode == "goal_planning":
                result = await self._process_goal_planning(request)
            elif thinking_mode == "reflection":
                result = await self._process_reflection(request)
            elif thinking_mode == "creative_problem_solving":
                result = await self._process_creative_problem_solving(request)
            else:
                result = await self._process_general_thinking(request)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process thought request {request.request_id}: {e}")
            raise
    
    async def _process_comprehensive_analysis(self, request: ThoughtRequest) -> ThoughtResult:
        """Process comprehensive situation analysis."""
        situation = request.context.get("situation", "")
        context = request.context.get("context", {})
        
        # Step 1: Analyze the situation
        analysis_thought = await self.ai_brain.analyze_situation(
            situation=situation,
            available_data=context,
            goals=request.related_goals
        )
        
        # Step 2: Perform deductive reasoning
        premises = [
            situation,
            f"Available information: {context}",
            f"Current emotional state: {request.emotional_context}"
        ]
        deductive_reasoning = await self.reasoning_engine.reason_deductively(premises)
        
        # Step 3: Look for patterns (inductive reasoning)
        observations = [
            situation,
            analysis_thought.get("analysis", ""),
            str(context)
        ]
        inductive_reasoning = await self.reasoning_engine.reason_inductively(observations)
        
        # Step 4: Generate insights
        insights = []
        insights.extend(analysis_thought.get("insights", []))
        insights.append(deductive_reasoning.conclusion)
        insights.append(inductive_reasoning.conclusion)
        
        # Step 5: Plan actions
        actions = []
        for recommendation in analysis_thought.get("recommendations", []):
            actions.append({
                "action": recommendation,
                "priority": "medium",
                "reasoning": "Based on situation analysis"
            })
        
        return ThoughtResult(
            request_id=request.request_id,
            thought_processes=[],  # Would include actual ThoughtProcess objects
            reasoning_chains=[deductive_reasoning, inductive_reasoning],
            decisions_made=[],
            actions_planned=actions,
            insights_gained=insights,
            confidence=analysis_thought.get("confidence", 0.7),
            processing_time=0.0,  # Will be set by caller
            resources_used={"cognitive_load": 0.8, "memory_access": 0.6}
        )
    
    async def _process_goal_planning(self, request: ThoughtRequest) -> ThoughtResult:
        """Process goal planning request."""
        goal = request.context.get("goal", "")
        constraints = request.context.get("constraints", [])
        deadline = request.context.get("deadline")
        
        # Step 1: Create goal in planning engine
        goal_obj = await self.planning_engine.create_goal(
            description=goal,
            priority=8,  # High priority for explicit goal planning
            deadline=datetime.fromisoformat(deadline) if deadline else None,
            success_criteria=[f"Successfully achieve: {goal}"],
            required_resources={"time": 1.0, "cognitive_effort": 0.8}
        )
        
        # Step 2: Create plan
        plan = await self.planning_engine.create_plan(
            goal_id=goal_obj.goal_id,
            constraints=constraints
        )
        
        # Step 3: Reason about the plan
        plan_reasoning = await self.reasoning_engine.reason_deductively([
            f"Goal: {goal}",
            f"Plan steps: {len(plan.steps)}",
            f"Constraints: {constraints}",
            "Need to ensure plan is feasible and effective"
        ])
        
        # Step 4: Generate insights and actions
        insights = [
            f"Created plan with {len(plan.steps)} steps",
            f"Estimated success probability: {plan.success_probability:.2f}",
            plan_reasoning.conclusion
        ]
        
        actions = [
            {
                "action": f"Execute plan step: {step}",
                "priority": "high",
                "reasoning": "Part of goal achievement plan"
            }
            for step in plan.steps[:3]  # First 3 steps
        ]
        
        return ThoughtResult(
            request_id=request.request_id,
            thought_processes=[],
            reasoning_chains=[plan_reasoning],
            decisions_made=[{"decision": "Create structured plan", "rationale": "Goal requires systematic approach"}],
            actions_planned=actions,
            insights_gained=insights,
            confidence=plan.success_probability,
            processing_time=0.0,
            resources_used={"cognitive_load": 0.9, "planning_effort": 1.0}
        )
    
    async def _process_reflection(self, request: ThoughtRequest) -> ThoughtResult:
        """Process reflection request."""
        experience = request.context.get("experience", {})
        outcomes = request.context.get("outcomes", {})
        
        # Step 1: Reflect using AI brain
        reflection_result = await self.ai_brain.reflect_on_experience(
            experience=experience,
            outcomes=outcomes,
            emotions=request.emotional_context
        )
        
        # Step 2: Reason about lessons learned
        lessons_reasoning = await self.reasoning_engine.reason_inductively([
            f"Experience: {experience}",
            f"Outcomes: {outcomes}",
            f"Emotional response: {request.emotional_context}"
        ])
        
        # Step 3: Store insights in memory
        for learning in reflection_result.get("learnings", []):
            await self.memory_system.store_memory(
                content=learning,
                memory_type="episodic",
                importance=0.8,
                tags=["reflection", "learning", "experience"]
            )
        
        insights = []
        insights.extend(reflection_result.get("learnings", []))
        insights.append(lessons_reasoning.conclusion)
        insights.extend(reflection_result.get("emotional_insights", {}).values())
        
        actions = [
            {
                "action": action,
                "priority": "medium",
                "reasoning": "Based on reflection insights"
            }
            for action in reflection_result.get("future_actions", [])
        ]
        
        return ThoughtResult(
            request_id=request.request_id,
            thought_processes=[],
            reasoning_chains=[lessons_reasoning],
            decisions_made=[],
            actions_planned=actions,
            insights_gained=insights,
            confidence=reflection_result.get("confidence", 0.7),
            processing_time=0.0,
            resources_used={"cognitive_load": 0.6, "emotional_processing": 0.8}
        )
    
    async def _process_creative_problem_solving(self, request: ThoughtRequest) -> ThoughtResult:
        """Process creative problem solving request."""
        problem = request.context.get("problem", "")
        context = request.context.get("context", {})
        constraints = request.context.get("constraints", [])
        
        # Step 1: Solve problem using AI brain
        solution_result = await self.ai_brain.solve_problem(
            problem=problem,
            context=context,
            constraints=constraints
        )
        
        # Step 2: Generate creative alternatives
        creative_result = await self.ai_brain.generate_creative_content(
            content_type="problem_solution",
            theme=problem,
            requirements={"constraints": constraints, "context": context}
        )
        
        # Step 3: Reason about best approach
        approach_reasoning = await self.reasoning_engine.reason_abductively(
            observation=f"Problem: {problem}",
            possible_explanations=[
                solution_result.get("solution", ""),
                creative_result.get("content", "")
            ]
        )
        
        insights = [
            solution_result.get("solution", ""),
            approach_reasoning.conclusion
        ]
        insights.extend(solution_result.get("alternatives", []))
        
        actions = [
            {
                "action": step,
                "priority": "high",
                "reasoning": "Problem solving implementation step"
            }
            for step in solution_result.get("implementation_steps", [])
        ]
        
        return ThoughtResult(
            request_id=request.request_id,
            thought_processes=[],
            reasoning_chains=[approach_reasoning],
            decisions_made=[{"decision": "Use hybrid analytical-creative approach", "rationale": approach_reasoning.conclusion}],
            actions_planned=actions,
            insights_gained=insights,
            confidence=solution_result.get("confidence", 0.7),
            processing_time=0.0,
            resources_used={"cognitive_load": 1.0, "creativity": 0.9}
        )
    
    async def _process_general_thinking(self, request: ThoughtRequest) -> ThoughtResult:
        """Process general thinking request."""
        # Simple general processing
        context = request.context
        
        # Basic analysis
        analysis_thought = await self.ai_brain.think(
            ThoughtType.ANALYSIS,
            context
        )
        
        insights = [analysis_thought.output.get("response", "General thinking completed")]
        
        return ThoughtResult(
            request_id=request.request_id,
            thought_processes=[analysis_thought],
            reasoning_chains=[],
            decisions_made=[],
            actions_planned=[],
            insights_gained=insights,
            confidence=analysis_thought.confidence,
            processing_time=0.0,
            resources_used={"cognitive_load": 0.5}
        )
    
    async def _get_relevant_memories(self, query: str) -> List[str]:
        """Get relevant memories for context."""
        try:
            memories = await self.memory_system.retrieve_memories(
                query=query,
                limit=5,
                min_importance=0.6
            )
            return [memory.content for memory in memories]
        except Exception as e:
            self.logger.error(f"Failed to retrieve relevant memories: {e}")
            return []
    
    def _store_thought_result(self, result: ThoughtResult) -> None:
        """Store thought result in history."""
        self.thought_history.append(result)
        
        # Maintain history size
        if len(self.thought_history) > self.max_history_size:
            self.thought_history.pop(0)
    
    def _update_processing_stats(self, result: Optional[ThoughtResult], success: bool) -> None:
        """Update processing statistics."""
        self.processing_stats["total_thoughts_processed"] += 1
        
        if success:
            self.processing_stats["successful_processes"] += 1
            
            if result:
                # Update average processing time
                total_successful = self.processing_stats["successful_processes"]
                old_avg = self.processing_stats["average_processing_time"]
                self.processing_stats["average_processing_time"] = (
                    (old_avg * (total_successful - 1) + result.processing_time) / total_successful
                )
        else:
            self.processing_stats["failed_processes"] += 1
    
    async def _process_remaining_thoughts(self) -> None:
        """Process any remaining thoughts in the queue during shutdown."""
        while self.thought_queue:
            request = self.thought_queue.pop(0)
            try:
                await self._process_thought_request(request)
                self.logger.debug(f"Processed remaining thought: {request.request_id}")
            except Exception as e:
                self.logger.error(f"Failed to process remaining thought {request.request_id}: {e}")