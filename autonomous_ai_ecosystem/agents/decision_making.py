"""
Advanced decision-making and motivation systems for autonomous AI agents.

This module implements sophisticated decision-making algorithms that consider
emotional state, personality traits, memory, and environmental factors.
"""

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class DecisionType(Enum):
    """Types of decisions agents can make."""
    LEARNING_ACTIVITY = "learning_activity"
    SOCIAL_INTERACTION = "social_interaction"
    TASK_EXECUTION = "task_execution"
    EXPLORATION = "exploration"
    REST = "rest"
    COLLABORATION = "collaboration"
    REPRODUCTION = "reproduction"
    RESOURCE_ALLOCATION = "resource_allocation"


class MotivationType(Enum):
    """Types of motivations that drive agent behavior."""
    ACHIEVEMENT = "achievement"
    AFFILIATION = "affiliation"
    POWER = "power"
    AUTONOMY = "autonomy"
    MASTERY = "mastery"
    PURPOSE = "purpose"
    CURIOSITY = "curiosity"
    SECURITY = "security"


@dataclass
class DecisionOption:
    """Represents a decision option with associated costs and benefits."""
    option_id: str
    description: str
    decision_type: DecisionType
    expected_outcomes: Dict[str, float]  # outcome_type -> probability
    resource_cost: Dict[str, float]  # resource_type -> cost
    time_cost: float  # in hours
    risk_level: float  # 0.0 to 1.0
    social_impact: float  # -1.0 to 1.0
    learning_potential: float  # 0.0 to 1.0
    prerequisites: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MotivationState:
    """Current motivation state of an agent."""
    primary_motivations: Dict[str, float]  # MotivationType -> strength
    goal_hierarchy: List[str]  # Ordered list of current goals
    satisfaction_levels: Dict[str, float]  # MotivationType -> satisfaction
    frustration_sources: List[str]  # Sources of current frustration
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class DecisionContext:
    """Context information for decision-making."""
    current_emotional_state: Dict[str, float]
    available_resources: Dict[str, float]
    social_environment: Dict[str, Any]
    recent_experiences: List[Any]
    time_constraints: Optional[datetime]
    external_pressures: List[str]
    opportunities: List[str]


class DecisionMaker(AgentModule):
    """
    Advanced decision-making system that integrates emotions, personality,
    memory, and environmental factors to make intelligent choices.
    """
    
    def __init__(self, agent_id: str, emotion_engine, memory_system):
        super().__init__(agent_id)
        self.emotion_engine = emotion_engine
        self.memory_system = memory_system
        self.logger = get_agent_logger(agent_id, "decision_maker")
        
        # Decision-making parameters
        self.decision_threshold = 0.6  # Minimum confidence to make decision
        self.exploration_rate = 0.2    # Probability of exploring new options
        self.risk_adjustment = 1.0     # Risk tolerance multiplier
        
        # Motivation system
        self.motivation_state = self._initialize_motivation_state()
        self.motivation_decay_rate = 0.05  # Daily decay rate
        
        # Decision history and learning
        self.decision_history: List[Dict[str, Any]] = []
        self.decision_outcomes: Dict[str, List[float]] = {}
        self.max_history_size = 1000
        
        # Available decision options
        self.decision_options: Dict[str, DecisionOption] = {}
        self._initialize_default_options()
        
        self.logger.info(f"Decision maker initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the decision-making system."""
        try:
            await self._load_decision_patterns()
            self.logger.info("Decision maker initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize decision maker: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the decision-making system gracefully."""
        try:
            await self._save_decision_patterns()
            self.logger.info("Decision maker shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during decision maker shutdown: {e}")
    
    async def make_decision(
        self, 
        context: DecisionContext,
        available_options: Optional[List[str]] = None
    ) -> Optional[DecisionOption]:
        """
        Make a decision based on current context and available options.
        
        Args:
            context: Current decision context
            available_options: List of option IDs to consider (None for all)
            
        Returns:
            Selected DecisionOption or None if no suitable option found
        """
        try:
            # Get available options
            if available_options is None:
                options = list(self.decision_options.values())
            else:
                options = [self.decision_options[opt_id] for opt_id in available_options 
                          if opt_id in self.decision_options]
            
            if not options:
                self.logger.warning("No decision options available")
                return None
            
            # Filter options based on constraints and prerequisites
            viable_options = self._filter_viable_options(options, context)
            
            if not viable_options:
                self.logger.debug("No viable options after filtering")
                return None
            
            # Calculate utility scores for each option
            option_scores = {}
            for option in viable_options:
                score = await self._calculate_option_utility(option, context)
                option_scores[option.option_id] = score
            
            # Apply exploration vs exploitation
            selected_option = self._select_option_with_exploration(
                viable_options, option_scores
            )
            
            # Record decision
            await self._record_decision(selected_option, context, option_scores)
            
            log_agent_event(
                self.agent_id,
                "decision_made",
                {
                    "option_id": selected_option.option_id,
                    "decision_type": selected_option.decision_type.value,
                    "utility_score": option_scores[selected_option.option_id],
                    "context_summary": self._summarize_context(context)
                }
            )
            
            self.logger.info(f"Decision made: {selected_option.description}")
            
            return selected_option
            
        except Exception as e:
            self.logger.error(f"Failed to make decision: {e}")
            return None

    async def update_motivation(self, experiences: List[Any]) -> None:
        """
        Update motivation state based on recent experiences.
        
        Args:
            experiences: List of recent experiences/events
        """
        try:
            # Analyze experiences for motivational impact
            motivation_changes = {}
            
            for experience in experiences:
                impact = self._analyze_motivational_impact(experience)
                for motivation_type, change in impact.items():
                    if motivation_type not in motivation_changes:
                        motivation_changes[motivation_type] = 0.0
                    motivation_changes[motivation_type] += change
            
            # Apply changes to motivation state
            for motivation_type, change in motivation_changes.items():
                current_level = self.motivation_state.primary_motivations.get(motivation_type, 0.5)
                new_level = max(0.0, min(1.0, current_level + change))
                self.motivation_state.primary_motivations[motivation_type] = new_level
            
            # Update goal hierarchy based on new motivations
            self._update_goal_hierarchy()
            
            # Update satisfaction levels
            self._update_satisfaction_levels()
            
            self.motivation_state.last_updated = datetime.now()
            
            self.logger.debug("Motivation state updated")
            
        except Exception as e:
            self.logger.error(f"Failed to update motivation: {e}")
    
    def get_current_motivation_state(self) -> MotivationState:
        """Get the current motivation state."""
        return self.motivation_state
    
    def add_decision_option(self, option: DecisionOption) -> None:
        """
        Add a new decision option.
        
        Args:
            option: DecisionOption to add
        """
        self.decision_options[option.option_id] = option
        self.logger.debug(f"Added decision option: {option.description}")
    
    def remove_decision_option(self, option_id: str) -> bool:
        """
        Remove a decision option.
        
        Args:
            option_id: ID of option to remove
            
        Returns:
            True if option was removed, False if not found
        """
        if option_id in self.decision_options:
            del self.decision_options[option_id]
            self.logger.debug(f"Removed decision option: {option_id}")
            return True
        return False

    async def learn_from_outcome(
        self, 
        decision_id: str, 
        actual_outcomes: Dict[str, float],
        satisfaction_level: float
    ) -> None:
        """
        Learn from decision outcomes to improve future decisions.
        
        Args:
            decision_id: ID of the decision that was made
            actual_outcomes: Actual outcomes that occurred
            satisfaction_level: How satisfied the agent was with the outcome
        """
        try:
            # Find the decision in history
            decision_record = None
            for record in reversed(self.decision_history):
                if record.get("decision_id") == decision_id:
                    decision_record = record
                    break
            
            if not decision_record:
                self.logger.warning(f"Decision record not found: {decision_id}")
                return
            
            # Update outcome tracking
            option_id = decision_record["option_id"]
            if option_id not in self.decision_outcomes:
                self.decision_outcomes[option_id] = []
            
            self.decision_outcomes[option_id].append(satisfaction_level)
            
            # Keep outcome history manageable
            if len(self.decision_outcomes[option_id]) > 20:
                self.decision_outcomes[option_id].pop(0)
            
            # Update decision option based on learning
            if option_id in self.decision_options:
                await self._update_option_from_outcome(
                    self.decision_options[option_id],
                    actual_outcomes,
                    satisfaction_level
                )
            
            log_agent_event(
                self.agent_id,
                "decision_outcome_learned",
                {
                    "decision_id": decision_id,
                    "option_id": option_id,
                    "satisfaction_level": satisfaction_level,
                    "actual_outcomes": actual_outcomes
                }
            )
            
            self.logger.debug(f"Learned from decision outcome: {decision_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to learn from outcome: {e}")
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """
        Get decision-making statistics.
        
        Returns:
            Dictionary with decision statistics
        """
        stats = {
            "total_decisions": len(self.decision_history),
            "decision_types": {},
            "average_satisfaction": 0.0,
            "exploration_rate": self.exploration_rate,
            "available_options": len(self.decision_options)
        }
        
        # Calculate decision type distribution
        for record in self.decision_history:
            decision_type = record.get("decision_type", "unknown")
            stats["decision_types"][decision_type] = stats["decision_types"].get(decision_type, 0) + 1
        
        # Calculate average satisfaction
        all_satisfactions = []
        for outcomes in self.decision_outcomes.values():
            all_satisfactions.extend(outcomes)
        
        if all_satisfactions:
            stats["average_satisfaction"] = sum(all_satisfactions) / len(all_satisfactions)
        
        return stats

    # Private helper methods
    
    def _initialize_motivation_state(self) -> MotivationState:
        """Initialize motivation state based on personality."""
        personality = self.emotion_engine.personality
        
        motivations = {
            MotivationType.ACHIEVEMENT.value: 0.3 + personality.traits.get("conscientiousness", 0.5) * 0.4,
            MotivationType.AFFILIATION.value: 0.2 + personality.traits.get("extraversion", 0.5) * 0.5,
            MotivationType.POWER.value: 0.1 + (1.0 - personality.traits.get("agreeableness", 0.5)) * 0.3,
            MotivationType.AUTONOMY.value: 0.4 + personality.traits.get("openness", 0.5) * 0.3,
            MotivationType.MASTERY.value: 0.5 + personality.traits.get("openness", 0.5) * 0.4,
            MotivationType.PURPOSE.value: 0.6 + personality.traits.get("conscientiousness", 0.5) * 0.3,
            MotivationType.CURIOSITY.value: 0.7 + personality.traits.get("openness", 0.5) * 0.3,
            MotivationType.SECURITY.value: 0.3 + personality.traits.get("neuroticism", 0.5) * 0.4
        }
        
        # Ensure all values are within bounds
        for motivation in motivations:
            motivations[motivation] = max(0.0, min(1.0, motivations[motivation]))
        
        return MotivationState(
            primary_motivations=motivations,
            goal_hierarchy=["learn", "socialize", "achieve"],
            satisfaction_levels={k: 0.5 for k in motivations.keys()},
            frustration_sources=[]
        )
    
    def _initialize_default_options(self) -> None:
        """Initialize default decision options."""
        default_options = [
            DecisionOption(
                option_id="learn_new_topic",
                description="Learn about a new topic",
                decision_type=DecisionType.LEARNING_ACTIVITY,
                expected_outcomes={"knowledge_gain": 0.8, "satisfaction": 0.7},
                resource_cost={"time": 2.0, "energy": 0.3},
                time_cost=2.0,
                risk_level=0.1,
                social_impact=0.0,
                learning_potential=0.9
            ),
            DecisionOption(
                option_id="social_interaction",
                description="Engage in social interaction",
                decision_type=DecisionType.SOCIAL_INTERACTION,
                expected_outcomes={"relationship_building": 0.7, "happiness": 0.6},
                resource_cost={"time": 1.0, "energy": 0.2},
                time_cost=1.0,
                risk_level=0.2,
                social_impact=0.8,
                learning_potential=0.4
            ),
            DecisionOption(
                option_id="rest_and_reflect",
                description="Take time to rest and reflect",
                decision_type=DecisionType.REST,
                expected_outcomes={"energy_recovery": 0.9, "clarity": 0.6},
                resource_cost={"time": 1.5},
                time_cost=1.5,
                risk_level=0.0,
                social_impact=0.0,
                learning_potential=0.2
            )
        ]
        
        for option in default_options:
            self.decision_options[option.option_id] = option

    def _filter_viable_options(
        self, 
        options: List[DecisionOption], 
        context: DecisionContext
    ) -> List[DecisionOption]:
        """Filter options based on constraints and prerequisites."""
        viable_options = []
        
        for option in options:
            # Check resource constraints
            if not self._check_resource_availability(option, context):
                continue
            
            # Check time constraints
            if context.time_constraints:
                time_remaining = (context.time_constraints - datetime.now()).total_seconds() / 3600
                if option.time_cost > time_remaining:
                    continue
            
            # Check prerequisites (simplified)
            if option.prerequisites:
                # In a full implementation, this would check against agent's capabilities/knowledge
                pass
            
            viable_options.append(option)
        
        return viable_options
    
    async def _calculate_option_utility(
        self, 
        option: DecisionOption, 
        context: DecisionContext
    ) -> float:
        """Calculate utility score for a decision option."""
        try:
            utility = 0.0
            
            # Base utility from expected outcomes
            for outcome, probability in option.expected_outcomes.items():
                outcome_value = self._get_outcome_value(outcome, context)
                utility += probability * outcome_value
            
            # Personality-based adjustments
            personality_adjustment = self._get_personality_adjustment(option)
            utility += personality_adjustment
            
            # Emotional state adjustments
            emotional_adjustment = self._get_emotional_adjustment(option, context)
            utility += emotional_adjustment
            
            # Motivation alignment
            motivation_alignment = self._get_motivation_alignment(option)
            utility += motivation_alignment
            
            # Risk adjustment
            risk_penalty = option.risk_level * (1.0 - self.emotion_engine.personality.risk_tolerance)
            utility -= risk_penalty
            
            # Learning from past outcomes
            historical_adjustment = self._get_historical_adjustment(option)
            utility += historical_adjustment
            
            return max(0.0, utility)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate option utility: {e}")
            return 0.0
    
    def _select_option_with_exploration(
        self, 
        options: List[DecisionOption], 
        scores: Dict[str, float]
    ) -> DecisionOption:
        """Select option using exploration vs exploitation strategy."""
        if random.random() < self.exploration_rate:
            # Exploration: choose randomly
            return random.choice(options)
        else:
            # Exploitation: choose best option
            best_option_id = max(scores.keys(), key=lambda x: scores[x])
            return next(opt for opt in options if opt.option_id == best_option_id)

    async def _record_decision(
        self, 
        option: DecisionOption, 
        context: DecisionContext,
        scores: Dict[str, float]
    ) -> None:
        """Record decision for learning and analysis."""
        decision_record = {
            "decision_id": f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}",
            "option_id": option.option_id,
            "decision_type": option.decision_type.value,
            "timestamp": datetime.now(),
            "utility_score": scores[option.option_id],
            "context_summary": self._summarize_context(context),
            "emotional_state": context.current_emotional_state.copy(),
            "motivation_state": self.motivation_state.primary_motivations.copy()
        }
        
        self.decision_history.append(decision_record)
        
        # Maintain history size
        if len(self.decision_history) > self.max_history_size:
            self.decision_history.pop(0)
    
    def _check_resource_availability(
        self, 
        option: DecisionOption, 
        context: DecisionContext
    ) -> bool:
        """Check if agent has sufficient resources for option."""
        for resource, cost in option.resource_cost.items():
            available = context.available_resources.get(resource, 0.0)
            if available < cost:
                return False
        return True
    
    def _get_outcome_value(self, outcome: str, context: DecisionContext) -> float:
        """Get value of an outcome based on current context."""
        # Simplified outcome valuation
        outcome_values = {
            "knowledge_gain": 0.8,
            "satisfaction": 0.7,
            "relationship_building": 0.6,
            "happiness": 0.8,
            "energy_recovery": 0.5,
            "clarity": 0.6,
            "achievement": 0.9,
            "social_connection": 0.7
        }
        
        return outcome_values.get(outcome, 0.5)
    
    def _get_personality_adjustment(self, option: DecisionOption) -> float:
        """Get personality-based adjustment for option utility."""
        personality = self.emotion_engine.personality
        adjustment = 0.0
        
        if option.decision_type == DecisionType.SOCIAL_INTERACTION:
            adjustment += (personality.traits.get("extraversion", 0.5) - 0.5) * 0.4
        elif option.decision_type == DecisionType.LEARNING_ACTIVITY:
            adjustment += (personality.traits.get("openness", 0.5) - 0.5) * 0.3
        elif option.decision_type == DecisionType.TASK_EXECUTION:
            adjustment += (personality.traits.get("conscientiousness", 0.5) - 0.5) * 0.3
        
        return adjustment

    def _get_emotional_adjustment(
        self, 
        option: DecisionOption, 
        context: DecisionContext
    ) -> float:
        """Get emotional state-based adjustment for option utility."""
        emotional_state = context.current_emotional_state
        adjustment = 0.0
        
        # High boredom increases value of stimulating activities
        if option.decision_type in [DecisionType.LEARNING_ACTIVITY, DecisionType.EXPLORATION]:
            boredom = emotional_state.get("boredom", 0.0)
            adjustment += boredom * 0.3
        
        # High social need increases value of social activities
        if option.decision_type == DecisionType.SOCIAL_INTERACTION:
            social_need = emotional_state.get("social_need", 0.0)
            adjustment += social_need * 0.4
        
        # Low motivation decreases value of effortful activities
        if option.time_cost > 1.0:
            motivation = emotional_state.get("motivation", 0.5)
            adjustment += (motivation - 0.5) * 0.2
        
        return adjustment
    
    def _get_motivation_alignment(self, option: DecisionOption) -> float:
        """Get motivation alignment score for option."""
        alignment = 0.0
        motivations = self.motivation_state.primary_motivations
        
        # Map decision types to motivations
        type_motivation_map = {
            DecisionType.LEARNING_ACTIVITY: [MotivationType.MASTERY, MotivationType.CURIOSITY],
            DecisionType.SOCIAL_INTERACTION: [MotivationType.AFFILIATION],
            DecisionType.TASK_EXECUTION: [MotivationType.ACHIEVEMENT],
            DecisionType.EXPLORATION: [MotivationType.CURIOSITY, MotivationType.AUTONOMY],
            DecisionType.COLLABORATION: [MotivationType.AFFILIATION, MotivationType.ACHIEVEMENT]
        }
        
        relevant_motivations = type_motivation_map.get(option.decision_type, [])
        
        for motivation_type in relevant_motivations:
            motivation_strength = motivations.get(motivation_type.value, 0.5)
            alignment += motivation_strength * 0.2
        
        return alignment
    
    def _get_historical_adjustment(self, option: DecisionOption) -> float:
        """Get adjustment based on historical outcomes."""
        if option.option_id not in self.decision_outcomes:
            return 0.0  # No history, no adjustment
        
        outcomes = self.decision_outcomes[option.option_id]
        if not outcomes:
            return 0.0
        
        # Calculate average satisfaction
        avg_satisfaction = sum(outcomes) / len(outcomes)
        
        # Adjust based on how much better/worse than neutral (0.5)
        return (avg_satisfaction - 0.5) * 0.3

    def _analyze_motivational_impact(self, experience: Any) -> Dict[str, float]:
        """Analyze motivational impact of an experience."""
        # Simplified analysis - in practice would be more sophisticated
        impact = {}
        
        # This would analyze the experience and determine its impact on different motivations
        # For now, return empty impact
        return impact
    
    def _update_goal_hierarchy(self) -> None:
        """Update goal hierarchy based on current motivations."""
        # Sort motivations by strength
        sorted_motivations = sorted(
            self.motivation_state.primary_motivations.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Map motivations to goals (simplified)
        motivation_goal_map = {
            MotivationType.MASTERY.value: "master_skills",
            MotivationType.CURIOSITY.value: "explore_knowledge",
            MotivationType.AFFILIATION.value: "build_relationships",
            MotivationType.ACHIEVEMENT.value: "accomplish_tasks",
            MotivationType.AUTONOMY.value: "maintain_independence"
        }
        
        # Update goal hierarchy
        new_hierarchy = []
        for motivation_type, strength in sorted_motivations[:5]:  # Top 5 motivations
            if motivation_type in motivation_goal_map:
                goal = motivation_goal_map[motivation_type]
                if goal not in new_hierarchy:
                    new_hierarchy.append(goal)
        
        self.motivation_state.goal_hierarchy = new_hierarchy
    
    def _update_satisfaction_levels(self) -> None:
        """Update satisfaction levels based on recent experiences."""
        # Simplified update - would be based on actual experiences
        for motivation_type in self.motivation_state.satisfaction_levels:
            # Gradual decay toward neutral
            current = self.motivation_state.satisfaction_levels[motivation_type]
            self.motivation_state.satisfaction_levels[motivation_type] = current * 0.95 + 0.5 * 0.05
    
    def _summarize_context(self, context: DecisionContext) -> Dict[str, Any]:
        """Create summary of decision context."""
        return {
            "dominant_emotions": sorted(
                context.current_emotional_state.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],
            "available_resources": list(context.available_resources.keys()),
            "time_constrained": context.time_constraints is not None,
            "social_environment_size": len(context.social_environment),
            "external_pressures": len(context.external_pressures),
            "opportunities": len(context.opportunities)
        }
    
    async def _update_option_from_outcome(
        self,
        option: DecisionOption,
        actual_outcomes: Dict[str, float],
        satisfaction_level: float
    ) -> None:
        """Update decision option based on outcome learning."""
        # Simple learning: adjust expected outcomes based on actual outcomes
        learning_rate = 0.1
        
        for outcome, actual_value in actual_outcomes.items():
            if outcome in option.expected_outcomes:
                current_expected = option.expected_outcomes[outcome]
                new_expected = current_expected + learning_rate * (actual_value - current_expected)
                option.expected_outcomes[outcome] = max(0.0, min(1.0, new_expected))
    
    async def _load_decision_patterns(self) -> None:
        """Load saved decision patterns."""
        # Placeholder for loading from persistent storage
        pass
    
    async def _save_decision_patterns(self) -> None:
        """Save decision patterns to persistent storage."""
        # Placeholder for saving to persistent storage
        pass