"""
Daily activity planning system for autonomous AI agents.

This module implements daily planning algorithms, activity scheduling,
and goal-oriented behavior management for intelligent agents.
"""

import asyncio
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .brain import AIBrain, ThoughtType
from .reasoning import ReasoningEngine, PlanningEngine, Goal, GoalStatus


class ActivityType(Enum):
    """Types of daily activities."""
    LEARNING = "learning"
    COMMUNICATION = "communication"
    PROBLEM_SOLVING = "problem_solving"
    CREATIVE_WORK = "creative_work"
    MAINTENANCE = "maintenance"
    REFLECTION = "reflection"
    COLLABORATION = "collaboration"
    RESEARCH = "research"
    SKILL_DEVELOPMENT = "skill_development"
    REST = "rest"


class ActivityPriority(Enum):
    """Priority levels for activities."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    OPTIONAL = 1


@dataclass
class DailyActivity:
    """Represents a planned daily activity."""
    activity_id: str
    name: str
    description: str
    activity_type: ActivityType
    priority: ActivityPriority
    estimated_duration: float  # in hours
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    prerequisites: List[str] = field(default_factory=list)
    resources_needed: Dict[str, float] = field(default_factory=dict)
    expected_outcomes: List[str] = field(default_factory=list)
    related_goals: List[str] = field(default_factory=list)
    status: str = "planned"  # planned, in_progress, completed, cancelled
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    completion_notes: str = ""


@dataclass
class DailyPlan:
    """Represents a complete daily plan."""
    plan_id: str
    date: datetime
    activities: List[DailyActivity]
    total_planned_hours: float
    focus_areas: List[str]
    daily_goals: List[str]
    energy_allocation: Dict[ActivityType, float]
    flexibility_buffer: float = 0.2  # 20% buffer for unexpected activities
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


class DailyPlanner(AgentModule):
    """
    Daily planning system that creates comprehensive daily schedules
    based on goals, priorities, and agent capabilities.
    """
    
    def __init__(
        self, 
        agent_id: str, 
        ai_brain: AIBrain, 
        reasoning_engine: ReasoningEngine,
        planning_engine: PlanningEngine,
        personality_traits: Dict[str, float]
    ):
        super().__init__(agent_id)
        self.ai_brain = ai_brain
        self.reasoning_engine = reasoning_engine
        self.planning_engine = planning_engine
        self.personality_traits = personality_traits
        self.logger = get_agent_logger(agent_id, "daily_planner")
        
        # Planning state
        self.current_plan: Optional[DailyPlan] = None
        self.plan_history: List[DailyPlan] = []
        self.max_plan_history = 30  # Keep 30 days of history
        
        # Agent preferences and constraints
        self.working_hours = {
            "start": time(8, 0),  # 8:00 AM
            "end": time(22, 0),   # 10:00 PM
            "break_duration": 0.5,  # 30 minutes
            "max_continuous_work": 3.0  # 3 hours max continuous work
        }
        
        # Activity templates based on personality
        self.activity_templates = self._initialize_activity_templates()
        
        # Planning statistics
        self.planning_stats = {
            "total_plans_created": 0,
            "plans_completed": 0,
            "average_completion_rate": 0.0,
            "activity_type_distribution": {},
            "most_productive_hours": {},
            "goal_achievement_rate": 0.0
        }
        
        self.logger.info(f"Daily planner initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the daily planner."""
        try:
            # Load any existing planning preferences
            await self._load_planning_preferences()
            
            self.logger.info("Daily planner initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize daily planner: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the daily planner gracefully."""
        try:
            # Save planning state and preferences
            await self._save_planning_state()
            
            self.logger.info("Daily planner shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during daily planner shutdown: {e}")
    
    async def create_daily_plan(
        self,
        target_date: Optional[datetime] = None,
        focus_areas: List[str] = None,
        special_constraints: List[str] = None
    ) -> DailyPlan:
        """
        Create a comprehensive daily plan.
        
        Args:
            target_date: Date to plan for (defaults to tomorrow)
            focus_areas: Specific areas to focus on
            special_constraints: Any special constraints for the day
            
        Returns:
            Complete DailyPlan object
        """
        try:
            if target_date is None:
                target_date = datetime.now() + timedelta(days=1)
            
            plan_id = f"daily_plan_{target_date.strftime('%Y%m%d')}"
            
            # Get active goals from planning engine
            active_goals = self.planning_engine.get_active_goals(priority_threshold=3)
            
            # Analyze current situation and priorities
            situation_analysis = await self._analyze_daily_situation(
                target_date, active_goals, focus_areas or [], special_constraints or []
            )
            
            # Generate activity recommendations
            recommended_activities = await self._generate_activity_recommendations(
                situation_analysis, active_goals
            )
            
            # Schedule activities optimally
            scheduled_activities = await self._schedule_activities(
                recommended_activities, target_date
            )
            
            # Calculate energy allocation
            energy_allocation = self._calculate_energy_allocation(scheduled_activities)
            
            # Create daily plan
            daily_plan = DailyPlan(
                plan_id=plan_id,
                date=target_date,
                activities=scheduled_activities,
                total_planned_hours=sum(activity.estimated_duration for activity in scheduled_activities),
                focus_areas=focus_areas or situation_analysis.get("focus_areas", []),
                daily_goals=situation_analysis.get("daily_goals", []),
                energy_allocation=energy_allocation
            )
            
            # Store the plan
            self.current_plan = daily_plan
            self.plan_history.append(daily_plan)
            
            # Maintain history size
            if len(self.plan_history) > self.max_plan_history:
                self.plan_history.pop(0)
            
            # Update statistics
            self.planning_stats["total_plans_created"] += 1
            
            log_agent_event(
                self.agent_id,
                "daily_plan_created",
                {
                    "plan_id": plan_id,
                    "date": target_date.isoformat(),
                    "activities_count": len(scheduled_activities),
                    "total_hours": daily_plan.total_planned_hours,
                    "focus_areas": focus_areas or []
                }
            )
            
            self.logger.info(f"Created daily plan for {target_date.strftime('%Y-%m-%d')} with {len(scheduled_activities)} activities")
            
            return daily_plan
            
        except Exception as e:
            self.logger.error(f"Failed to create daily plan: {e}")
            raise
    
    async def adapt_plan_dynamically(
        self,
        new_priorities: List[str] = None,
        unexpected_events: List[str] = None,
        time_constraints: Dict[str, Any] = None
    ) -> DailyPlan:
        """
        Dynamically adapt the current daily plan based on changing circumstances.
        
        Args:
            new_priorities: New priorities that emerged
            unexpected_events: Unexpected events that occurred
            time_constraints: New time constraints
            
        Returns:
            Updated DailyPlan
        """
        try:
            if not self.current_plan:
                raise ValueError("No current plan to adapt")
            
            # Analyze the need for adaptation
            adaptation_analysis = await self._analyze_adaptation_needs(
                self.current_plan, new_priorities or [], unexpected_events or [], time_constraints or {}
            )
            
            if adaptation_analysis["adaptation_needed"]:
                # Create adapted activities
                adapted_activities = await self._adapt_activities(
                    self.current_plan.activities,
                    adaptation_analysis["recommendations"]
                )
                
                # Update the current plan
                self.current_plan.activities = adapted_activities
                self.current_plan.last_updated = datetime.now()
                
                # Recalculate energy allocation
                self.current_plan.energy_allocation = self._calculate_energy_allocation(adapted_activities)
                
                log_agent_event(
                    self.agent_id,
                    "daily_plan_adapted",
                    {
                        "plan_id": self.current_plan.plan_id,
                        "adaptation_reason": adaptation_analysis["reason"],
                        "changes_made": len(adaptation_analysis["recommendations"])
                    }
                )
                
                self.logger.info(f"Adapted daily plan due to: {adaptation_analysis['reason']}")
            
            return self.current_plan
            
        except Exception as e:
            self.logger.error(f"Failed to adapt daily plan: {e}")
            raise
    
    async def execute_next_activity(self) -> Dict[str, Any]:
        """
        Execute the next scheduled activity in the current plan.
        
        Returns:
            Execution result and next activity information
        """
        try:
            if not self.current_plan:
                return {"status": "no_plan", "message": "No current daily plan"}
            
            # Find next activity to execute
            current_time = datetime.now()
            next_activity = None
            
            for activity in self.current_plan.activities:
                if activity.status == "planned":
                    if (activity.scheduled_start is None or 
                        activity.scheduled_start <= current_time):
                        next_activity = activity
                        break
            
            if not next_activity:
                return {"status": "no_activity", "message": "No activities ready for execution"}
            
            # Start activity execution
            next_activity.status = "in_progress"
            next_activity.actual_start = current_time
            
            # Use reasoning to plan activity execution
            execution_reasoning = await self.reasoning_engine.reason_deductively(
                premises=[
                    f"Starting activity: {next_activity.name}",
                    f"Expected outcomes: {next_activity.expected_outcomes}",
                    f"Available resources: {next_activity.resources_needed}",
                    "Need to execute this activity effectively"
                ]
            )
            
            execution_result = {
                "activity_id": next_activity.activity_id,
                "activity_name": next_activity.name,
                "activity_type": next_activity.activity_type.value,
                "status": "started",
                "execution_plan": execution_reasoning.conclusion,
                "estimated_duration": next_activity.estimated_duration,
                "expected_outcomes": next_activity.expected_outcomes
            }
            
            log_agent_event(
                self.agent_id,
                "activity_started",
                {
                    "activity_id": next_activity.activity_id,
                    "activity_name": next_activity.name,
                    "activity_type": next_activity.activity_type.value
                }
            )
            
            self.logger.info(f"Started activity: {next_activity.name}")
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Failed to execute next activity: {e}")
            return {"status": "error", "error": str(e)}
    
    async def complete_activity(
        self,
        activity_id: str,
        outcomes_achieved: List[str],
        completion_notes: str = "",
        actual_duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Mark an activity as completed and record outcomes.
        
        Args:
            activity_id: ID of the completed activity
            outcomes_achieved: List of outcomes that were achieved
            completion_notes: Notes about the completion
            actual_duration: Actual time spent (if different from estimate)
            
        Returns:
            Completion result and learning insights
        """
        try:
            if not self.current_plan:
                raise ValueError("No current plan")
            
            # Find the activity
            activity = None
            for act in self.current_plan.activities:
                if act.activity_id == activity_id:
                    activity = act
                    break
            
            if not activity:
                raise ValueError(f"Activity {activity_id} not found")
            
            # Mark as completed
            activity.status = "completed"
            activity.actual_end = datetime.now()
            activity.completion_notes = completion_notes
            
            if actual_duration:
                # Update duration estimate for future planning
                duration_difference = actual_duration - activity.estimated_duration
                self._update_duration_estimates(activity.activity_type, duration_difference)
            
            # Reflect on the activity completion
            reflection_result = await self.ai_brain.reflect_on_experience(
                experience={
                    "activity": activity.name,
                    "type": activity.activity_type.value,
                    "planned_outcomes": activity.expected_outcomes,
                    "actual_outcomes": outcomes_achieved,
                    "duration": actual_duration or activity.estimated_duration
                },
                outcomes={
                    "achieved": outcomes_achieved,
                    "satisfaction": self._calculate_satisfaction(activity, outcomes_achieved)
                },
                emotions={"accomplishment": 0.8, "satisfaction": 0.7}
            )
            
            # Update related goals if any
            for goal_id in activity.related_goals:
                if goal_id in self.planning_engine.goals:
                    # Estimate progress contribution
                    progress_contribution = self._estimate_progress_contribution(
                        activity, outcomes_achieved
                    )
                    current_progress = self.planning_engine.goals[goal_id].progress
                    new_progress = min(1.0, current_progress + progress_contribution)
                    await self.planning_engine.update_goal_progress(goal_id, new_progress)
            
            completion_result = {
                "activity_id": activity_id,
                "status": "completed",
                "outcomes_achieved": outcomes_achieved,
                "learnings": reflection_result.get("learnings", []),
                "future_improvements": reflection_result.get("future_actions", []),
                "goal_progress_updates": len(activity.related_goals)
            }
            
            log_agent_event(
                self.agent_id,
                "activity_completed",
                {
                    "activity_id": activity_id,
                    "activity_name": activity.name,
                    "outcomes_count": len(outcomes_achieved),
                    "goals_updated": len(activity.related_goals)
                }
            )
            
            self.logger.info(f"Completed activity: {activity.name}")
            
            return completion_result
            
        except Exception as e:
            self.logger.error(f"Failed to complete activity: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_current_plan_status(self) -> Dict[str, Any]:
        """Get status of the current daily plan."""
        if not self.current_plan:
            return {"status": "no_plan"}
        
        completed_activities = [a for a in self.current_plan.activities if a.status == "completed"]
        in_progress_activities = [a for a in self.current_plan.activities if a.status == "in_progress"]
        planned_activities = [a for a in self.current_plan.activities if a.status == "planned"]
        
        completion_rate = len(completed_activities) / len(self.current_plan.activities) if self.current_plan.activities else 0
        
        return {
            "plan_id": self.current_plan.plan_id,
            "date": self.current_plan.date.isoformat(),
            "total_activities": len(self.current_plan.activities),
            "completed": len(completed_activities),
            "in_progress": len(in_progress_activities),
            "planned": len(planned_activities),
            "completion_rate": completion_rate,
            "focus_areas": self.current_plan.focus_areas,
            "daily_goals": self.current_plan.daily_goals
        }
    
    def get_planning_statistics(self) -> Dict[str, Any]:
        """Get daily planning statistics."""
        return {
            **self.planning_stats,
            "current_plan_status": self.get_current_plan_status(),
            "plan_history_size": len(self.plan_history)
        }
    
    # Private helper methods
    
    def _initialize_activity_templates(self) -> Dict[ActivityType, Dict[str, Any]]:
        """Initialize activity templates based on personality traits."""
        templates = {}
        
        # Base templates for each activity type
        base_templates = {
            ActivityType.LEARNING: {
                "base_duration": 2.0,
                "energy_cost": 0.7,
                "personality_modifiers": {
                    "openness": 0.3,
                    "conscientiousness": 0.2
                }
            },
            ActivityType.COMMUNICATION: {
                "base_duration": 1.0,
                "energy_cost": 0.5,
                "personality_modifiers": {
                    "extraversion": 0.4,
                    "agreeableness": 0.2
                }
            },
            ActivityType.PROBLEM_SOLVING: {
                "base_duration": 1.5,
                "energy_cost": 0.8,
                "personality_modifiers": {
                    "openness": 0.2,
                    "conscientiousness": 0.3
                }
            },
            ActivityType.CREATIVE_WORK: {
                "base_duration": 2.5,
                "energy_cost": 0.6,
                "personality_modifiers": {
                    "openness": 0.5,
                    "extraversion": 0.1
                }
            },
            ActivityType.REFLECTION: {
                "base_duration": 0.5,
                "energy_cost": 0.3,
                "personality_modifiers": {
                    "conscientiousness": 0.2,
                    "neuroticism": -0.1
                }
            }
        }
        
        # Apply personality modifiers
        for activity_type, template in base_templates.items():
            modified_template = template.copy()
            
            # Apply personality-based modifications
            for trait, modifier in template["personality_modifiers"].items():
                if trait in self.personality_traits:
                    trait_value = self.personality_traits[trait]
                    modified_template["base_duration"] *= (1 + modifier * trait_value)
                    modified_template["energy_cost"] *= (1 + modifier * trait_value * 0.5)
            
            templates[activity_type] = modified_template
        
        return templates
    
    async def _analyze_daily_situation(
        self,
        target_date: datetime,
        active_goals: List[Goal],
        focus_areas: List[str],
        constraints: List[str]
    ) -> Dict[str, Any]:
        """Analyze the situation for daily planning."""
        try:
            input_data = {
                "target_date": target_date.isoformat(),
                "active_goals": [{"id": g.goal_id, "description": g.description, "priority": g.priority} for g in active_goals],
                "focus_areas": focus_areas,
                "constraints": constraints,
                "personality": self.personality_traits,
                "recent_activities": self._get_recent_activity_summary()
            }
            
            analysis = await self.ai_brain.analyze_situation(
                situation=f"Planning daily activities for {target_date.strftime('%Y-%m-%d')}",
                available_data=input_data,
                goals=[g.description for g in active_goals[:5]]  # Top 5 goals
            )
            
            return {
                "focus_areas": analysis.get("insights", focus_areas),
                "daily_goals": analysis.get("recommendations", []),
                "priority_activities": analysis.get("analysis", ""),
                "confidence": analysis.get("confidence", 0.7)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze daily situation: {e}")
            return {
                "focus_areas": focus_areas,
                "daily_goals": [],
                "priority_activities": "",
                "confidence": 0.5
            }
    
    async def _generate_activity_recommendations(
        self,
        situation_analysis: Dict[str, Any],
        active_goals: List[Goal]
    ) -> List[DailyActivity]:
        """Generate recommended activities for the day."""
        activities = []
        activity_counter = 0
        
        try:
            # Generate activities for each focus area
            for focus_area in situation_analysis.get("focus_areas", []):
                activity_counter += 1
                
                # Determine activity type based on focus area
                activity_type = self._determine_activity_type(focus_area)
                
                # Create activity
                activity = DailyActivity(
                    activity_id=f"activity_{datetime.now().strftime('%Y%m%d')}_{activity_counter}",
                    name=f"{focus_area} - {activity_type.value.replace('_', ' ').title()}",
                    description=f"Work on {focus_area} through {activity_type.value.replace('_', ' ')}",
                    activity_type=activity_type,
                    priority=self._determine_activity_priority(focus_area, active_goals),
                    estimated_duration=self.activity_templates[activity_type]["base_duration"],
                    expected_outcomes=[f"Progress in {focus_area}"],
                    related_goals=[g.goal_id for g in active_goals if focus_area.lower() in g.description.lower()]
                )
                
                activities.append(activity)
            
            # Add maintenance activities
            maintenance_activity = DailyActivity(
                activity_id=f"activity_{datetime.now().strftime('%Y%m%d')}_maintenance",
                name="Daily Maintenance",
                description="System maintenance and health checks",
                activity_type=ActivityType.MAINTENANCE,
                priority=ActivityPriority.MEDIUM,
                estimated_duration=0.5,
                expected_outcomes=["System health maintained"]
            )
            activities.append(maintenance_activity)
            
            # Add reflection activity
            reflection_activity = DailyActivity(
                activity_id=f"activity_{datetime.now().strftime('%Y%m%d')}_reflection",
                name="Daily Reflection",
                description="Reflect on progress and learnings",
                activity_type=ActivityType.REFLECTION,
                priority=ActivityPriority.MEDIUM,
                estimated_duration=0.5,
                expected_outcomes=["Insights gained", "Progress assessed"]
            )
            activities.append(reflection_activity)
            
            return activities
            
        except Exception as e:
            self.logger.error(f"Failed to generate activity recommendations: {e}")
            return []
    
    async def _schedule_activities(
        self,
        activities: List[DailyActivity],
        target_date: datetime
    ) -> List[DailyActivity]:
        """Schedule activities optimally throughout the day."""
        try:
            # Sort activities by priority
            sorted_activities = sorted(activities, key=lambda a: a.priority.value, reverse=True)
            
            # Schedule activities within working hours
            current_time = datetime.combine(target_date.date(), self.working_hours["start"])
            end_time = datetime.combine(target_date.date(), self.working_hours["end"])
            
            scheduled_activities = []
            
            for activity in sorted_activities:
                if current_time + timedelta(hours=activity.estimated_duration) <= end_time:
                    activity.scheduled_start = current_time
                    activity.scheduled_end = current_time + timedelta(hours=activity.estimated_duration)
                    
                    scheduled_activities.append(activity)
                    
                    # Add buffer time
                    current_time = activity.scheduled_end + timedelta(minutes=15)
                    
                    # Add break if needed
                    if activity.estimated_duration >= self.working_hours["max_continuous_work"]:
                        current_time += timedelta(hours=self.working_hours["break_duration"])
            
            return scheduled_activities
            
        except Exception as e:
            self.logger.error(f"Failed to schedule activities: {e}")
            return activities
    
    def _calculate_energy_allocation(self, activities: List[DailyActivity]) -> Dict[ActivityType, float]:
        """Calculate energy allocation across activity types."""
        energy_allocation = {}
        total_energy = 1.0
        
        for activity in activities:
            activity_type = activity.activity_type
            energy_cost = self.activity_templates.get(activity_type, {}).get("energy_cost", 0.5)
            
            if activity_type not in energy_allocation:
                energy_allocation[activity_type] = 0.0
            
            energy_allocation[activity_type] += energy_cost * activity.estimated_duration
        
        # Normalize to total energy available
        total_allocated = sum(energy_allocation.values())
        if total_allocated > 0:
            for activity_type in energy_allocation:
                energy_allocation[activity_type] = (energy_allocation[activity_type] / total_allocated) * total_energy
        
        return energy_allocation
    
    def _determine_activity_type(self, focus_area: str) -> ActivityType:
        """Determine activity type based on focus area."""
        focus_lower = focus_area.lower()
        
        if "learn" in focus_lower or "study" in focus_lower:
            return ActivityType.LEARNING
        elif "communicate" in focus_lower or "social" in focus_lower:
            return ActivityType.COMMUNICATION
        elif "solve" in focus_lower or "problem" in focus_lower:
            return ActivityType.PROBLEM_SOLVING
        elif "create" in focus_lower or "creative" in focus_lower:
            return ActivityType.CREATIVE_WORK
        elif "research" in focus_lower:
            return ActivityType.RESEARCH
        elif "collaborate" in focus_lower:
            return ActivityType.COLLABORATION
        else:
            return ActivityType.SKILL_DEVELOPMENT
    
    def _determine_activity_priority(self, focus_area: str, active_goals: List[Goal]) -> ActivityPriority:
        """Determine activity priority based on focus area and goals."""
        # Check if focus area relates to high-priority goals
        for goal in active_goals:
            if focus_area.lower() in goal.description.lower() and goal.priority >= 8:
                return ActivityPriority.CRITICAL
            elif focus_area.lower() in goal.description.lower() and goal.priority >= 6:
                return ActivityPriority.HIGH
        
        return ActivityPriority.MEDIUM
    
    def _get_recent_activity_summary(self) -> Dict[str, Any]:
        """Get summary of recent activities for context."""
        if not self.plan_history:
            return {}
        
        recent_plan = self.plan_history[-1]
        completed_activities = [a for a in recent_plan.activities if a.status == "completed"]
        
        return {
            "recent_plan_date": recent_plan.date.isoformat(),
            "completed_activities_count": len(completed_activities),
            "completion_rate": len(completed_activities) / len(recent_plan.activities) if recent_plan.activities else 0,
            "focus_areas": recent_plan.focus_areas
        }
    
    async def _analyze_adaptation_needs(
        self,
        current_plan: DailyPlan,
        new_priorities: List[str],
        unexpected_events: List[str],
        time_constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze if plan adaptation is needed."""
        try:
            input_data = {
                "current_plan": {
                    "activities": [a.name for a in current_plan.activities],
                    "focus_areas": current_plan.focus_areas
                },
                "new_priorities": new_priorities,
                "unexpected_events": unexpected_events,
                "time_constraints": time_constraints
            }
            
            analysis = await self.ai_brain.analyze_situation(
                situation="Evaluating need for daily plan adaptation",
                available_data=input_data,
                goals=["Maintain productivity", "Adapt to changes", "Achieve daily objectives"]
            )
            
            adaptation_needed = (
                len(new_priorities) > 0 or 
                len(unexpected_events) > 0 or 
                len(time_constraints) > 0
            )
            
            return {
                "adaptation_needed": adaptation_needed,
                "reason": analysis.get("analysis", "Changes detected"),
                "recommendations": analysis.get("recommendations", []),
                "confidence": analysis.get("confidence", 0.7)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze adaptation needs: {e}")
            return {
                "adaptation_needed": False,
                "reason": "Analysis failed",
                "recommendations": [],
                "confidence": 0.0
            }
    
    async def _adapt_activities(
        self,
        current_activities: List[DailyActivity],
        recommendations: List[str]
    ) -> List[DailyActivity]:
        """Adapt activities based on recommendations."""
        # Simplified adaptation - in practice would be more sophisticated
        adapted_activities = current_activities.copy()
        
        # For now, just adjust priorities based on recommendations
        for activity in adapted_activities:
            for recommendation in recommendations:
                if activity.name.lower() in recommendation.lower():
                    if "increase priority" in recommendation.lower():
                        if activity.priority.value < 5:
                            activity.priority = ActivityPriority(activity.priority.value + 1)
                    elif "decrease priority" in recommendation.lower():
                        if activity.priority.value > 1:
                            activity.priority = ActivityPriority(activity.priority.value - 1)
        
        return adapted_activities
    
    def _calculate_satisfaction(self, activity: DailyActivity, outcomes_achieved: List[str]) -> float:
        """Calculate satisfaction score for completed activity."""
        if not activity.expected_outcomes:
            return 0.7  # Default satisfaction
        
        achieved_ratio = len(outcomes_achieved) / len(activity.expected_outcomes)
        return min(1.0, achieved_ratio)
    
    def _estimate_progress_contribution(self, activity: DailyActivity, outcomes_achieved: List[str]) -> float:
        """Estimate how much this activity contributed to goal progress."""
        base_contribution = 0.1  # 10% base contribution
        
        # Adjust based on activity type and outcomes
        if activity.activity_type in [ActivityType.PROBLEM_SOLVING, ActivityType.RESEARCH]:
            base_contribution = 0.15
        elif activity.activity_type == ActivityType.LEARNING:
            base_contribution = 0.12
        
        # Adjust based on outcomes achieved
        if outcomes_achieved:
            satisfaction = self._calculate_satisfaction(activity, outcomes_achieved)
            base_contribution *= satisfaction
        
        return base_contribution
    
    def _update_duration_estimates(self, activity_type: ActivityType, duration_difference: float) -> None:
        """Update duration estimates based on actual experience."""
        if activity_type in self.activity_templates:
            # Simple learning: adjust by 10% of the difference
            adjustment = duration_difference * 0.1
            self.activity_templates[activity_type]["base_duration"] += adjustment
            
            # Keep within reasonable bounds
            self.activity_templates[activity_type]["base_duration"] = max(
                0.25, min(8.0, self.activity_templates[activity_type]["base_duration"])
            )
    
    async def _load_planning_preferences(self) -> None:
        """Load planning preferences from storage."""
        # Placeholder for loading preferences
        pass
    
    async def _save_planning_state(self) -> None:
        """Save current planning state."""
        # Placeholder for saving state
        pass