"""
Advanced reasoning and planning systems for autonomous AI agents.

This module implements sophisticated reasoning algorithms, planning strategies,
and goal-oriented behavior for intelligent agent decision-making.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .brain import AIBrain, ThoughtType


class ReasoningType(Enum):
    """Types of reasoning processes."""
    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    ANALOGICAL = "analogical"
    CAUSAL = "causal"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    PROBABILISTIC = "probabilistic"


class PlanningStrategy(Enum):
    """Planning strategies for goal achievement."""
    FORWARD_CHAINING = "forward_chaining"
    BACKWARD_CHAINING = "backward_chaining"
    HIERARCHICAL = "hierarchical"
    REACTIVE = "reactive"
    HYBRID = "hybrid"


class GoalStatus(Enum):
    """Status of goals in the planning system."""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class Goal:
    """Represents a goal with associated metadata."""
    goal_id: str
    description: str
    priority: int  # 1-10, 10 being highest
    status: GoalStatus
    created_at: datetime
    deadline: Optional[datetime] = None
    parent_goal: Optional[str] = None
    sub_goals: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    required_resources: Dict[str, float] = field(default_factory=dict)
    progress: float = 0.0
    estimated_effort: float = 1.0
    actual_effort: float = 0.0


@dataclass
class Plan:
    """Represents a plan to achieve goals."""
    plan_id: str
    goal_id: str
    strategy: PlanningStrategy
    steps: List[Dict[str, Any]]
    estimated_duration: float
    required_resources: Dict[str, float]
    success_probability: float
    created_at: datetime
    last_updated: datetime
    status: str = "active"
    current_step: int = 0


@dataclass
class ReasoningChain:
    """Represents a chain of reasoning steps."""
    chain_id: str
    reasoning_type: ReasoningType
    premises: List[str]
    steps: List[Dict[str, Any]]
    conclusion: str
    confidence: float
    evidence: List[str]
    timestamp: datetime


class ReasoningEngine(AgentModule):
    """
    Advanced reasoning engine that performs various types of logical reasoning
    and inference for intelligent agent behavior.
    """
    
    def __init__(self, agent_id: str, ai_brain: AIBrain):
        super().__init__(agent_id)
        self.ai_brain = ai_brain
        self.logger = get_agent_logger(agent_id, "reasoning_engine")
        
        # Reasoning history
        self.reasoning_chains: List[ReasoningChain] = []
        self.max_reasoning_history = 500
        
        # Knowledge base for reasoning
        self.facts: Set[str] = set()
        self.rules: List[Dict[str, Any]] = []
        self.beliefs: Dict[str, float] = {}  # belief -> confidence
        
        # Reasoning statistics
        self.reasoning_stats = {
            "total_reasoning_chains": 0,
            "successful_inferences": 0,
            "failed_inferences": 0,
            "reasoning_types": {},
            "average_confidence": 0.0
        }
        
        self.logger.info(f"Reasoning engine initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the reasoning engine."""
        try:
            # Load any existing knowledge base
            await self._load_knowledge_base()
            
            self.logger.info("Reasoning engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize reasoning engine: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the reasoning engine gracefully."""
        try:
            # Save reasoning patterns
            await self._save_reasoning_patterns()
            
            self.logger.info("Reasoning engine shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during reasoning engine shutdown: {e}")
    
    async def reason_deductively(
        self,
        premises: List[str],
        rules: List[str] = None
    ) -> ReasoningChain:
        """
        Perform deductive reasoning from premises to conclusion.
        
        Args:
            premises: List of premises to reason from
            rules: Optional logical rules to apply
            
        Returns:
            ReasoningChain with deductive inference
        """
        try:
            chain_id = f"deductive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Use AI brain for complex deductive reasoning
            input_data = {
                "premises": premises,
                "rules": rules or [],
                "reasoning_type": "deductive",
                "task": "Apply logical deduction to derive valid conclusions"
            }
            
            thought = await self.ai_brain.think(ThoughtType.ANALYSIS, input_data)
            
            # Extract reasoning steps and conclusion
            steps = self._extract_reasoning_steps(thought.reasoning_steps)
            conclusion = thought.output.get("conclusion", "No conclusion reached")
            confidence = thought.confidence
            
            # Create reasoning chain
            reasoning_chain = ReasoningChain(
                chain_id=chain_id,
                reasoning_type=ReasoningType.DEDUCTIVE,
                premises=premises,
                steps=steps,
                conclusion=conclusion,
                confidence=confidence,
                evidence=premises,
                timestamp=datetime.now()
            )
            
            # Store reasoning chain
            self._store_reasoning_chain(reasoning_chain)
            
            # Update beliefs based on conclusion
            if confidence > 0.7:
                self.beliefs[conclusion] = confidence
            
            self.logger.debug(f"Deductive reasoning completed: {conclusion}")
            
            return reasoning_chain
            
        except Exception as e:
            self.logger.error(f"Failed to perform deductive reasoning: {e}")
            raise
    
    async def reason_inductively(
        self,
        observations: List[str],
        context: Dict[str, Any] = None
    ) -> ReasoningChain:
        """
        Perform inductive reasoning from observations to general patterns.
        
        Args:
            observations: List of observations
            context: Additional context for reasoning
            
        Returns:
            ReasoningChain with inductive inference
        """
        try:
            chain_id = f"inductive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            input_data = {
                "observations": observations,
                "context": context or {},
                "reasoning_type": "inductive",
                "task": "Identify patterns and make generalizations from observations"
            }
            
            thought = await self.ai_brain.think(ThoughtType.ANALYSIS, input_data)
            
            steps = self._extract_reasoning_steps(thought.reasoning_steps)
            conclusion = thought.output.get("pattern", "No pattern identified")
            confidence = thought.confidence * 0.8  # Inductive reasoning is less certain
            
            reasoning_chain = ReasoningChain(
                chain_id=chain_id,
                reasoning_type=ReasoningType.INDUCTIVE,
                premises=observations,
                steps=steps,
                conclusion=conclusion,
                confidence=confidence,
                evidence=observations,
                timestamp=datetime.now()
            )
            
            self._store_reasoning_chain(reasoning_chain)
            
            # Update beliefs with lower confidence for inductive conclusions
            if confidence > 0.6:
                self.beliefs[conclusion] = confidence
            
            self.logger.debug(f"Inductive reasoning completed: {conclusion}")
            
            return reasoning_chain
            
        except Exception as e:
            self.logger.error(f"Failed to perform inductive reasoning: {e}")
            raise
    
    async def reason_abductively(
        self,
        observation: str,
        possible_explanations: List[str] = None
    ) -> ReasoningChain:
        """
        Perform abductive reasoning to find best explanation for observation.
        
        Args:
            observation: Observation to explain
            possible_explanations: Optional list of candidate explanations
            
        Returns:
            ReasoningChain with abductive inference
        """
        try:
            chain_id = f"abductive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            input_data = {
                "observation": observation,
                "possible_explanations": possible_explanations or [],
                "reasoning_type": "abductive",
                "task": "Find the best explanation for the given observation"
            }
            
            thought = await self.ai_brain.think(ThoughtType.ANALYSIS, input_data)
            
            steps = self._extract_reasoning_steps(thought.reasoning_steps)
            conclusion = thought.output.get("best_explanation", "No explanation found")
            confidence = thought.confidence * 0.7  # Abductive reasoning is speculative
            
            reasoning_chain = ReasoningChain(
                chain_id=chain_id,
                reasoning_type=ReasoningType.ABDUCTIVE,
                premises=[observation],
                steps=steps,
                conclusion=conclusion,
                confidence=confidence,
                evidence=[observation],
                timestamp=datetime.now()
            )
            
            self._store_reasoning_chain(reasoning_chain)
            
            self.logger.debug(f"Abductive reasoning completed: {conclusion}")
            
            return reasoning_chain
            
        except Exception as e:
            self.logger.error(f"Failed to perform abductive reasoning: {e}")
            raise
    
    async def reason_by_analogy(
        self,
        source_situation: Dict[str, Any],
        target_situation: Dict[str, Any],
        mapping_hints: List[str] = None
    ) -> ReasoningChain:
        """
        Perform analogical reasoning between two situations.
        
        Args:
            source_situation: Known situation to reason from
            target_situation: Target situation to reason about
            mapping_hints: Optional hints for mapping between situations
            
        Returns:
            ReasoningChain with analogical inference
        """
        try:
            chain_id = f"analogical_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            input_data = {
                "source_situation": source_situation,
                "target_situation": target_situation,
                "mapping_hints": mapping_hints or [],
                "reasoning_type": "analogical",
                "task": "Apply knowledge from source situation to target situation"
            }
            
            thought = await self.ai_brain.think(ThoughtType.ANALYSIS, input_data)
            
            steps = self._extract_reasoning_steps(thought.reasoning_steps)
            conclusion = thought.output.get("analogical_inference", "No analogy found")
            confidence = thought.confidence * 0.6  # Analogical reasoning varies in reliability
            
            reasoning_chain = ReasoningChain(
                chain_id=chain_id,
                reasoning_type=ReasoningType.ANALOGICAL,
                premises=[str(source_situation), str(target_situation)],
                steps=steps,
                conclusion=conclusion,
                confidence=confidence,
                evidence=[str(source_situation)],
                timestamp=datetime.now()
            )
            
            self._store_reasoning_chain(reasoning_chain)
            
            self.logger.debug(f"Analogical reasoning completed: {conclusion}")
            
            return reasoning_chain
            
        except Exception as e:
            self.logger.error(f"Failed to perform analogical reasoning: {e}")
            raise
    
    async def reason_causally(
        self,
        events: List[Dict[str, Any]],
        temporal_order: bool = True
    ) -> ReasoningChain:
        """
        Perform causal reasoning to identify cause-effect relationships.
        
        Args:
            events: List of events with timestamps and descriptions
            temporal_order: Whether to consider temporal ordering
            
        Returns:
            ReasoningChain with causal inference
        """
        try:
            chain_id = f"causal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            input_data = {
                "events": events,
                "temporal_order": temporal_order,
                "reasoning_type": "causal",
                "task": "Identify causal relationships between events"
            }
            
            thought = await self.ai_brain.think(ThoughtType.ANALYSIS, input_data)
            
            steps = self._extract_reasoning_steps(thought.reasoning_steps)
            conclusion = thought.output.get("causal_relationships", "No causal relationships identified")
            confidence = thought.confidence
            
            reasoning_chain = ReasoningChain(
                chain_id=chain_id,
                reasoning_type=ReasoningType.CAUSAL,
                premises=[str(event) for event in events],
                steps=steps,
                conclusion=conclusion,
                confidence=confidence,
                evidence=[str(event) for event in events],
                timestamp=datetime.now()
            )
            
            self._store_reasoning_chain(reasoning_chain)
            
            self.logger.debug(f"Causal reasoning completed: {conclusion}")
            
            return reasoning_chain
            
        except Exception as e:
            self.logger.error(f"Failed to perform causal reasoning: {e}")
            raise
    
    def add_fact(self, fact: str) -> None:
        """Add a fact to the knowledge base."""
        self.facts.add(fact)
        self.logger.debug(f"Added fact: {fact}")
    
    def add_rule(self, rule: Dict[str, Any]) -> None:
        """Add a logical rule to the knowledge base."""
        self.rules.append(rule)
        self.logger.debug(f"Added rule: {rule}")
    
    def get_beliefs(self, min_confidence: float = 0.5) -> Dict[str, float]:
        """Get current beliefs above minimum confidence threshold."""
        return {
            belief: confidence 
            for belief, confidence in self.beliefs.items() 
            if confidence >= min_confidence
        }
    
    def get_reasoning_history(self, reasoning_type: Optional[ReasoningType] = None) -> List[ReasoningChain]:
        """Get reasoning history, optionally filtered by type."""
        if reasoning_type:
            return [
                chain for chain in self.reasoning_chains 
                if chain.reasoning_type == reasoning_type
            ]
        return self.reasoning_chains.copy()
    
    def get_reasoning_statistics(self) -> Dict[str, Any]:
        """Get reasoning engine statistics."""
        return {
            **self.reasoning_stats,
            "total_facts": len(self.facts),
            "total_rules": len(self.rules),
            "total_beliefs": len(self.beliefs),
            "reasoning_history_size": len(self.reasoning_chains)
        }
    
    # Private helper methods
    
    def _extract_reasoning_steps(self, thought_steps: List[str]) -> List[Dict[str, Any]]:
        """Extract structured reasoning steps from thought process."""
        steps = []
        for i, step in enumerate(thought_steps):
            steps.append({
                "step_number": i + 1,
                "description": step,
                "type": "reasoning_step"
            })
        return steps
    
    def _store_reasoning_chain(self, chain: ReasoningChain) -> None:
        """Store reasoning chain in history."""
        self.reasoning_chains.append(chain)
        
        # Maintain history size
        if len(self.reasoning_chains) > self.max_reasoning_history:
            self.reasoning_chains.pop(0)
        
        # Update statistics
        self.reasoning_stats["total_reasoning_chains"] += 1
        
        reasoning_type = chain.reasoning_type.value
        self.reasoning_stats["reasoning_types"][reasoning_type] = (
            self.reasoning_stats["reasoning_types"].get(reasoning_type, 0) + 1
        )
        
        if chain.confidence > 0.5:
            self.reasoning_stats["successful_inferences"] += 1
        else:
            self.reasoning_stats["failed_inferences"] += 1
        
        # Update average confidence
        total_successful = self.reasoning_stats["successful_inferences"]
        if total_successful > 0:
            old_avg = self.reasoning_stats["average_confidence"]
            self.reasoning_stats["average_confidence"] = (
                (old_avg * (total_successful - 1) + chain.confidence) / total_successful
            )
    
    async def _load_knowledge_base(self) -> None:
        """Load existing knowledge base."""
        # Placeholder for loading from persistent storage
        pass
    
    async def _save_reasoning_patterns(self) -> None:
        """Save reasoning patterns for future learning."""
        # Placeholder for saving reasoning patterns
        pass


class PlanningEngine(AgentModule):
    """
    Advanced planning engine that creates and executes plans to achieve goals
    using various planning strategies and algorithms.
    """
    
    def __init__(self, agent_id: str, ai_brain: AIBrain, reasoning_engine: ReasoningEngine):
        super().__init__(agent_id)
        self.ai_brain = ai_brain
        self.reasoning_engine = reasoning_engine
        self.logger = get_agent_logger(agent_id, "planning_engine")
        
        # Goal and plan management
        self.goals: Dict[str, Goal] = {}
        self.plans: Dict[str, Plan] = {}
        self.active_plans: List[str] = []
        
        # Planning statistics
        self.planning_stats = {
            "total_goals": 0,
            "completed_goals": 0,
            "failed_goals": 0,
            "total_plans": 0,
            "successful_plans": 0,
            "planning_strategies": {},
            "average_plan_success_rate": 0.0
        }
        
        self.logger.info(f"Planning engine initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the planning engine."""
        try:
            # Load any existing goals and plans
            await self._load_planning_state()
            
            self.logger.info("Planning engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize planning engine: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the planning engine gracefully."""
        try:
            # Save planning state
            await self._save_planning_state()
            
            self.logger.info("Planning engine shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during planning engine shutdown: {e}")
    
    async def create_goal(
        self,
        description: str,
        priority: int,
        deadline: Optional[datetime] = None,
        success_criteria: List[str] = None,
        required_resources: Dict[str, float] = None,
        parent_goal: Optional[str] = None
    ) -> Goal:
        """
        Create a new goal.
        
        Args:
            description: Goal description
            priority: Priority level (1-10)
            deadline: Optional deadline
            success_criteria: Criteria for success
            required_resources: Required resources
            parent_goal: Parent goal ID if this is a sub-goal
            
        Returns:
            Created Goal object
        """
        try:
            goal_id = f"goal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.goals)}"
            
            goal = Goal(
                goal_id=goal_id,
                description=description,
                priority=max(1, min(10, priority)),
                status=GoalStatus.ACTIVE,
                created_at=datetime.now(),
                deadline=deadline,
                parent_goal=parent_goal,
                success_criteria=success_criteria or [],
                required_resources=required_resources or {},
                estimated_effort=self._estimate_goal_effort(description, success_criteria or [])
            )
            
            self.goals[goal_id] = goal
            
            # Update parent goal if specified
            if parent_goal and parent_goal in self.goals:
                self.goals[parent_goal].sub_goals.append(goal_id)
            
            self.planning_stats["total_goals"] += 1
            
            log_agent_event(
                self.agent_id,
                "goal_created",
                {
                    "goal_id": goal_id,
                    "description": description,
                    "priority": priority,
                    "deadline": deadline.isoformat() if deadline else None
                }
            )
            
            self.logger.info(f"Created goal: {description}")
            
            return goal
            
        except Exception as e:
            self.logger.error(f"Failed to create goal: {e}")
            raise
    
    async def create_plan(
        self,
        goal_id: str,
        strategy: PlanningStrategy = PlanningStrategy.HYBRID,
        constraints: List[str] = None
    ) -> Plan:
        """
        Create a plan to achieve a goal.
        
        Args:
            goal_id: ID of the goal to plan for
            strategy: Planning strategy to use
            constraints: Planning constraints
            
        Returns:
            Created Plan object
        """
        try:
            if goal_id not in self.goals:
                raise ValueError(f"Goal {goal_id} not found")
            
            goal = self.goals[goal_id]
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{goal_id}"
            
            # Use AI brain to create the plan
            input_data = {
                "goal": goal.description,
                "success_criteria": goal.success_criteria,
                "required_resources": goal.required_resources,
                "constraints": constraints or [],
                "strategy": strategy.value,
                "deadline": goal.deadline.isoformat() if goal.deadline else None
            }
            
            thought = await self.ai_brain.make_plan(
                objective=goal.description,
                constraints=constraints or [],
                resources=goal.required_resources,
                time_horizon="medium_term"
            )
            
            # Extract plan details
            steps = thought.get("steps", [])
            estimated_duration = self._estimate_plan_duration(steps)
            success_probability = thought.get("confidence", 0.7)
            
            plan = Plan(
                plan_id=plan_id,
                goal_id=goal_id,
                strategy=strategy,
                steps=steps,
                estimated_duration=estimated_duration,
                required_resources=goal.required_resources,
                success_probability=success_probability,
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
            
            self.plans[plan_id] = plan
            self.active_plans.append(plan_id)
            
            self.planning_stats["total_plans"] += 1
            strategy_name = strategy.value
            self.planning_stats["planning_strategies"][strategy_name] = (
                self.planning_stats["planning_strategies"].get(strategy_name, 0) + 1
            )
            
            log_agent_event(
                self.agent_id,
                "plan_created",
                {
                    "plan_id": plan_id,
                    "goal_id": goal_id,
                    "strategy": strategy.value,
                    "steps_count": len(steps),
                    "estimated_duration": estimated_duration
                }
            )
            
            self.logger.info(f"Created plan for goal: {goal.description}")
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Failed to create plan: {e}")
            raise
    
    async def execute_plan_step(self, plan_id: str) -> Dict[str, Any]:
        """
        Execute the next step in a plan.
        
        Args:
            plan_id: ID of the plan to execute
            
        Returns:
            Execution result
        """
        try:
            if plan_id not in self.plans:
                raise ValueError(f"Plan {plan_id} not found")
            
            plan = self.plans[plan_id]
            
            if plan.current_step >= len(plan.steps):
                return {"status": "completed", "message": "All steps completed"}
            
            current_step = plan.steps[plan.current_step]
            
            # Use reasoning engine to analyze step execution
            reasoning_result = await self.reasoning_engine.reason_deductively(
                premises=[
                    f"Current step: {current_step}",
                    f"Goal: {self.goals[plan.goal_id].description}",
                    "Need to execute this step effectively"
                ]
            )
            
            # Execute step (simplified - would integrate with actual execution systems)
            execution_result = {
                "step_number": plan.current_step + 1,
                "step_description": current_step,
                "status": "executed",
                "reasoning": reasoning_result.conclusion,
                "confidence": reasoning_result.confidence
            }
            
            # Update plan progress
            plan.current_step += 1
            plan.last_updated = datetime.now()
            
            # Check if plan is complete
            if plan.current_step >= len(plan.steps):
                plan.status = "completed"
                self._complete_plan(plan_id)
            
            log_agent_event(
                self.agent_id,
                "plan_step_executed",
                {
                    "plan_id": plan_id,
                    "step_number": execution_result["step_number"],
                    "status": execution_result["status"]
                }
            )
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Failed to execute plan step: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def update_goal_progress(self, goal_id: str, progress: float) -> None:
        """Update progress on a goal."""
        try:
            if goal_id not in self.goals:
                raise ValueError(f"Goal {goal_id} not found")
            
            goal = self.goals[goal_id]
            goal.progress = max(0.0, min(1.0, progress))
            
            # Check if goal is completed
            if goal.progress >= 1.0:
                goal.status = GoalStatus.COMPLETED
                self.planning_stats["completed_goals"] += 1
                
                log_agent_event(
                    self.agent_id,
                    "goal_completed",
                    {"goal_id": goal_id, "description": goal.description}
                )
            
        except Exception as e:
            self.logger.error(f"Failed to update goal progress: {e}")
    
    def get_active_goals(self, priority_threshold: int = 1) -> List[Goal]:
        """Get active goals above priority threshold."""
        return [
            goal for goal in self.goals.values()
            if goal.status == GoalStatus.ACTIVE and goal.priority >= priority_threshold
        ]
    
    def get_active_plans(self) -> List[Plan]:
        """Get currently active plans."""
        return [self.plans[plan_id] for plan_id in self.active_plans if plan_id in self.plans]
    
    def get_planning_statistics(self) -> Dict[str, Any]:
        """Get planning engine statistics."""
        return {
            **self.planning_stats,
            "total_active_goals": len([g for g in self.goals.values() if g.status == GoalStatus.ACTIVE]),
            "total_active_plans": len(self.active_plans),
            "goal_completion_rate": (
                self.planning_stats["completed_goals"] / max(1, self.planning_stats["total_goals"])
            )
        }
    
    # Private helper methods
    
    def _estimate_goal_effort(self, description: str, success_criteria: List[str]) -> float:
        """Estimate effort required for a goal."""
        base_effort = 1.0
        
        # Adjust based on description complexity
        if len(description.split()) > 10:
            base_effort += 0.5
        
        # Adjust based on success criteria
        base_effort += len(success_criteria) * 0.2
        
        return base_effort
    
    def _estimate_plan_duration(self, steps: List[Dict[str, Any]]) -> float:
        """Estimate duration for plan execution."""
        # Simple estimation based on number of steps
        base_duration = len(steps) * 0.5  # 0.5 hours per step
        
        # Adjust based on step complexity (simplified)
        for step in steps:
            step_desc = str(step)
            if len(step_desc) > 100:
                base_duration += 0.25
        
        return base_duration
    
    def _complete_plan(self, plan_id: str) -> None:
        """Mark plan as completed and update statistics."""
        if plan_id in self.active_plans:
            self.active_plans.remove(plan_id)
        
        self.planning_stats["successful_plans"] += 1
        
        # Update average success rate
        total_plans = self.planning_stats["total_plans"]
        successful_plans = self.planning_stats["successful_plans"]
        self.planning_stats["average_plan_success_rate"] = successful_plans / max(1, total_plans)
    
    async def _load_planning_state(self) -> None:
        """Load existing planning state."""
        # Placeholder for loading from persistent storage
        pass
    
    async def _save_planning_state(self) -> None:
        """Save planning state to persistent storage."""
        # Placeholder for saving to persistent storage
        pass