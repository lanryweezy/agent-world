"""
Unit tests for reasoning and planning systems.

Tests the reasoning engine, planning engine, daily planner, and thought processor
components for correct functionality and integration.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, time
from unittest.mock import Mock, AsyncMock, patch

from autonomous_ai_ecosystem.agents.brain import AIBrain, ThoughtType, LLMConfig
from autonomous_ai_ecosystem.agents.reasoning import (
    ReasoningEngine, PlanningEngine, ReasoningType, 
    Goal, GoalStatus, PlanningStrategy
)
from autonomous_ai_ecosystem.agents.daily_planner import (
    DailyPlanner, ActivityType, ActivityPriority, DailyActivity
)
from autonomous_ai_ecosystem.agents.thought_processor import (
    ThoughtProcessor, ThoughtRequest, ThoughtPriority, ThoughtTrigger
)
from autonomous_ai_ecosystem.agents.emotions import EmotionEngine
from autonomous_ai_ecosystem.agents.memory import MemorySystem


class TestReasoningEngine:
    """Test cases for the ReasoningEngine."""
    
    @pytest.fixture
    def mock_ai_brain(self):
        """Create a mock AI brain."""
        brain = Mock(spec=AIBrain)
        brain.think = AsyncMock()
        return brain
    
    @pytest.fixture
    def reasoning_engine(self, mock_ai_brain):
        """Create a ReasoningEngine instance for testing."""
        return ReasoningEngine("test_agent", mock_ai_brain)
    
    @pytest.mark.asyncio
    async def test_initialization(self, reasoning_engine):
        """Test reasoning engine initialization."""
        await reasoning_engine.initialize()
        assert reasoning_engine.agent_id == "test_agent"
        assert len(reasoning_engine.reasoning_chains) == 0
        assert len(reasoning_engine.facts) == 0
        assert len(reasoning_engine.rules) == 0
    
    @pytest.mark.asyncio
    async def test_deductive_reasoning(self, reasoning_engine, mock_ai_brain):
        """Test deductive reasoning functionality."""
        # Setup mock response
        mock_thought = Mock()
        mock_thought.reasoning_steps = ["Step 1: Analyze premises", "Step 2: Apply logic"]
        mock_thought.output = {"conclusion": "Therefore, X is true"}
        mock_thought.confidence = 0.9
        mock_ai_brain.think.return_value = mock_thought
        
        # Test deductive reasoning
        premises = ["All humans are mortal", "Socrates is human"]
        result = await reasoning_engine.reason_deductively(premises)
        
        assert result.reasoning_type == ReasoningType.DEDUCTIVE
        assert result.premises == premises
        assert result.conclusion == "Therefore, X is true"
        assert result.confidence == 0.9
        assert len(reasoning_engine.reasoning_chains) == 1
    
    @pytest.mark.asyncio
    async def test_inductive_reasoning(self, reasoning_engine, mock_ai_brain):
        """Test inductive reasoning functionality."""
        # Setup mock response
        mock_thought = Mock()
        mock_thought.reasoning_steps = ["Observe patterns", "Generalize"]
        mock_thought.output = {"pattern": "All observed swans are white"}
        mock_thought.confidence = 0.8
        mock_ai_brain.think.return_value = mock_thought
        
        # Test inductive reasoning
        observations = ["Swan 1 is white", "Swan 2 is white", "Swan 3 is white"]
        result = await reasoning_engine.reason_inductively(observations)
        
        assert result.reasoning_type == ReasoningType.INDUCTIVE
        assert result.premises == observations
        assert result.conclusion == "All observed swans are white"
        assert result.confidence == 0.64  # 0.8 * 0.8 (inductive penalty)
    
    @pytest.mark.asyncio
    async def test_abductive_reasoning(self, reasoning_engine, mock_ai_brain):
        """Test abductive reasoning functionality."""
        # Setup mock response
        mock_thought = Mock()
        mock_thought.reasoning_steps = ["Consider explanations", "Select best"]
        mock_thought.output = {"best_explanation": "The grass is wet because it rained"}
        mock_thought.confidence = 0.7
        mock_ai_brain.think.return_value = mock_thought
        
        # Test abductive reasoning
        observation = "The grass is wet"
        explanations = ["It rained", "Sprinkler was on", "Dew formed"]
        result = await reasoning_engine.reason_abductively(observation, explanations)
        
        assert result.reasoning_type == ReasoningType.ABDUCTIVE
        assert result.premises == [observation]
        assert result.conclusion == "The grass is wet because it rained"
        assert result.confidence == 0.49  # 0.7 * 0.7 (abductive penalty)
    
    def test_knowledge_base_management(self, reasoning_engine):
        """Test knowledge base fact and rule management."""
        # Add facts
        reasoning_engine.add_fact("The sky is blue")
        reasoning_engine.add_fact("Water boils at 100°C")
        
        assert len(reasoning_engine.facts) == 2
        assert "The sky is blue" in reasoning_engine.facts
        
        # Add rules
        rule = {"if": "temperature > 100", "then": "water boils"}
        reasoning_engine.add_rule(rule)
        
        assert len(reasoning_engine.rules) == 1
        assert rule in reasoning_engine.rules
    
    def test_beliefs_management(self, reasoning_engine):
        """Test belief system management."""
        # Initially no beliefs
        beliefs = reasoning_engine.get_beliefs()
        assert len(beliefs) == 0
        
        # Add some beliefs manually (normally done through reasoning)
        reasoning_engine.beliefs["The sun will rise tomorrow"] = 0.95
        reasoning_engine.beliefs["It will rain today"] = 0.3
        reasoning_engine.beliefs["Uncertain event"] = 0.4
        
        # Get beliefs above threshold
        high_confidence_beliefs = reasoning_engine.get_beliefs(min_confidence=0.5)
        assert len(high_confidence_beliefs) == 1
        assert "The sun will rise tomorrow" in high_confidence_beliefs
        
        all_beliefs = reasoning_engine.get_beliefs(min_confidence=0.0)
        assert len(all_beliefs) == 3


class TestPlanningEngine:
    """Test cases for the PlanningEngine."""
    
    @pytest.fixture
    def mock_ai_brain(self):
        """Create a mock AI brain."""
        brain = Mock(spec=AIBrain)
        brain.make_plan = AsyncMock()
        return brain
    
    @pytest.fixture
    def mock_reasoning_engine(self):
        """Create a mock reasoning engine."""
        engine = Mock(spec=ReasoningEngine)
        engine.reason_deductively = AsyncMock()
        return engine
    
    @pytest.fixture
    def planning_engine(self, mock_ai_brain, mock_reasoning_engine):
        """Create a PlanningEngine instance for testing."""
        return PlanningEngine("test_agent", mock_ai_brain, mock_reasoning_engine)
    
    @pytest.mark.asyncio
    async def test_goal_creation(self, planning_engine):
        """Test goal creation functionality."""
        await planning_engine.initialize()
        
        goal = await planning_engine.create_goal(
            description="Learn Python programming",
            priority=8,
            deadline=datetime.now() + timedelta(days=30),
            success_criteria=["Complete Python course", "Build a project"],
            required_resources={"time": 40.0, "focus": 0.8}
        )
        
        assert goal.description == "Learn Python programming"
        assert goal.priority == 8
        assert goal.status == GoalStatus.ACTIVE
        assert len(goal.success_criteria) == 2
        assert goal.goal_id in planning_engine.goals
    
    @pytest.mark.asyncio
    async def test_plan_creation(self, planning_engine, mock_ai_brain):
        """Test plan creation functionality."""
        await planning_engine.initialize()
        
        # Create a goal first
        goal = await planning_engine.create_goal(
            description="Build a web application",
            priority=7,
            success_criteria=["Design UI", "Implement backend", "Deploy"]
        )
        
        # Setup mock AI brain response
        mock_ai_brain.make_plan.return_value = {
            "steps": [
                "Design database schema",
                "Create API endpoints",
                "Build frontend components",
                "Test and deploy"
            ],
            "confidence": 0.8
        }
        
        # Create plan
        plan = await planning_engine.create_plan(
            goal_id=goal.goal_id,
            strategy=PlanningStrategy.HIERARCHICAL,
            constraints=["Budget: $1000", "Timeline: 3 months"]
        )
        
        assert plan.goal_id == goal.goal_id
        assert plan.strategy == PlanningStrategy.HIERARCHICAL
        assert len(plan.steps) == 4
        assert plan.success_probability == 0.8
        assert plan.plan_id in planning_engine.plans
    
    @pytest.mark.asyncio
    async def test_plan_execution(self, planning_engine, mock_ai_brain, mock_reasoning_engine):
        """Test plan step execution."""
        await planning_engine.initialize()
        
        # Setup goal and plan
        goal = await planning_engine.create_goal("Test goal", 5)
        
        mock_ai_brain.make_plan.return_value = {
            "steps": ["Step 1", "Step 2", "Step 3"],
            "confidence": 0.7
        }
        
        plan = await planning_engine.create_plan(goal.goal_id)
        
        # Setup reasoning mock
        mock_reasoning_result = Mock()
        mock_reasoning_result.conclusion = "Execute step effectively"
        mock_reasoning_result.confidence = 0.8
        mock_reasoning_engine.reason_deductively.return_value = mock_reasoning_result
        
        # Execute first step
        result = await planning_engine.execute_plan_step(plan.plan_id)
        
        assert result["status"] == "executed"
        assert result["step_number"] == 1
        assert result["step_description"] == "Step 1"
        assert plan.current_step == 1
        
        # Execute remaining steps
        await planning_engine.execute_plan_step(plan.plan_id)
        await planning_engine.execute_plan_step(plan.plan_id)
        
        # Plan should be completed
        assert plan.status == "completed"
        assert plan.current_step == 3
    
    @pytest.mark.asyncio
    async def test_goal_progress_tracking(self, planning_engine):
        """Test goal progress tracking."""
        await planning_engine.initialize()
        
        goal = await planning_engine.create_goal("Test progress goal", 6)
        
        # Update progress
        await planning_engine.update_goal_progress(goal.goal_id, 0.5)
        assert goal.progress == 0.5
        assert goal.status == GoalStatus.ACTIVE
        
        # Complete goal
        await planning_engine.update_goal_progress(goal.goal_id, 1.0)
        assert goal.progress == 1.0
        assert goal.status == GoalStatus.COMPLETED
    
    def test_active_goals_filtering(self, planning_engine):
        """Test filtering of active goals by priority."""
        # This would need to be async in real implementation
        # Simplified for testing
        planning_engine.goals = {
            "goal1": Goal("goal1", "Low priority", 2, GoalStatus.ACTIVE, datetime.now()),
            "goal2": Goal("goal2", "High priority", 8, GoalStatus.ACTIVE, datetime.now()),
            "goal3": Goal("goal3", "Completed", 7, GoalStatus.COMPLETED, datetime.now()),
            "goal4": Goal("goal4", "Medium priority", 5, GoalStatus.ACTIVE, datetime.now())
        }
        
        active_goals = planning_engine.get_active_goals(priority_threshold=5)
        
        assert len(active_goals) == 2
        goal_descriptions = [g.description for g in active_goals]
        assert "High priority" in goal_descriptions
        assert "Medium priority" in goal_descriptions


class TestDailyPlanner:
    """Test cases for the DailyPlanner."""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components for daily planner."""
        ai_brain = Mock(spec=AIBrain)
        ai_brain.analyze_situation = AsyncMock()
        ai_brain.make_plan = AsyncMock()
        ai_brain.reflect_on_experience = AsyncMock()
        
        reasoning_engine = Mock(spec=ReasoningEngine)
        reasoning_engine.reason_deductively = AsyncMock()
        
        planning_engine = Mock(spec=PlanningEngine)
        planning_engine.get_active_goals = Mock(return_value=[])
        planning_engine.update_goal_progress = AsyncMock()
        planning_engine.goals = {}
        
        return ai_brain, reasoning_engine, planning_engine
    
    @pytest.fixture
    def daily_planner(self, mock_components):
        """Create a DailyPlanner instance for testing."""
        ai_brain, reasoning_engine, planning_engine = mock_components
        personality_traits = {
            "openness": 0.7,
            "conscientiousness": 0.8,
            "extraversion": 0.6,
            "agreeableness": 0.7,
            "neuroticism": 0.3
        }
        
        return DailyPlanner(
            "test_agent", ai_brain, reasoning_engine, 
            planning_engine, personality_traits
        )
    
    @pytest.mark.asyncio
    async def test_daily_plan_creation(self, daily_planner, mock_components):
        """Test daily plan creation."""
        ai_brain, reasoning_engine, planning_engine = mock_components
        
        # Setup mocks
        ai_brain.analyze_situation.return_value = {
            "insights": ["Focus on learning", "Improve communication"],
            "recommendations": ["Study for 2 hours", "Practice coding"],
            "analysis": "Good day for productive work",
            "confidence": 0.8
        }
        
        await daily_planner.initialize()
        
        # Create daily plan
        target_date = datetime.now() + timedelta(days=1)
        plan = await daily_planner.create_daily_plan(
            target_date=target_date,
            focus_areas=["learning", "coding"],
            special_constraints=["Meeting at 2 PM"]
        )
        
        assert plan.date.date() == target_date.date()
        assert len(plan.activities) > 0
        assert "learning" in plan.focus_areas or "coding" in plan.focus_areas
        assert plan.total_planned_hours > 0
    
    @pytest.mark.asyncio
    async def test_activity_execution(self, daily_planner, mock_components):
        """Test activity execution workflow."""
        ai_brain, reasoning_engine, planning_engine = mock_components
        
        # Setup mocks
        ai_brain.analyze_situation.return_value = {
            "insights": ["Focus on learning"],
            "recommendations": ["Study programming"],
            "analysis": "Good for learning",
            "confidence": 0.7
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.conclusion = "Execute learning activity effectively"
        reasoning_engine.reason_deductively.return_value = mock_reasoning_result
        
        await daily_planner.initialize()
        
        # Create plan with activities
        plan = await daily_planner.create_daily_plan()
        
        # Execute next activity
        result = await daily_planner.execute_next_activity()
        
        if result["status"] == "started":
            assert "activity_id" in result
            assert "activity_name" in result
            assert "execution_plan" in result
    
    @pytest.mark.asyncio
    async def test_activity_completion(self, daily_planner, mock_components):
        """Test activity completion and reflection."""
        ai_brain, reasoning_engine, planning_engine = mock_components
        
        # Setup reflection mock
        ai_brain.reflect_on_experience.return_value = {
            "learnings": ["Learned new concepts", "Improved focus"],
            "future_actions": ["Continue practice", "Seek feedback"],
            "confidence": 0.8
        }
        
        await daily_planner.initialize()
        
        # Create a plan first
        await daily_planner.create_daily_plan()
        
        # Create a test activity
        activity = DailyActivity(
            activity_id="test_activity",
            name="Learning Session",
            description="Study programming concepts",
            activity_type=ActivityType.LEARNING,
            priority=ActivityPriority.HIGH,
            estimated_duration=2.0,
            expected_outcomes=["Learn new concepts", "Complete exercises"],
            related_goals=[]
        )
        
        # Add to current plan
        if daily_planner.current_plan:
            daily_planner.current_plan.activities.append(activity)
            activity.status = "in_progress"
            
            # Complete the activity
            result = await daily_planner.complete_activity(
                activity_id="test_activity",
                outcomes_achieved=["Learned Python basics", "Completed 5 exercises"],
                completion_notes="Good progress made",
                actual_duration=1.8
            )
            
            assert result["status"] == "completed"
            assert len(result["outcomes_achieved"]) == 2
            assert len(result["learnings"]) == 2
    
    def test_activity_templates_personality_adjustment(self, daily_planner):
        """Test that activity templates are adjusted based on personality."""
        templates = daily_planner.activity_templates
        
        # Check that templates exist for different activity types
        assert ActivityType.LEARNING in templates
        assert ActivityType.COMMUNICATION in templates
        assert ActivityType.CREATIVE_WORK in templates
        
        # Check that personality traits affected the templates
        learning_template = templates[ActivityType.LEARNING]
        assert "base_duration" in learning_template
        assert "energy_cost" in learning_template
        
        # High conscientiousness should increase learning duration
        assert learning_template["base_duration"] > 2.0
    
    def test_plan_status_tracking(self, daily_planner):
        """Test daily plan status tracking."""
        # Initially no plan
        status = daily_planner.get_current_plan_status()
        assert status["status"] == "no_plan"
        
        # After creating a plan (simplified test)
        from autonomous_ai_ecosystem.agents.daily_planner import DailyPlan
        
        activities = [
            DailyActivity("1", "Task 1", "Description", ActivityType.LEARNING, 
                         ActivityPriority.HIGH, 1.0),
            DailyActivity("2", "Task 2", "Description", ActivityType.COMMUNICATION, 
                         ActivityPriority.MEDIUM, 0.5)
        ]
        activities[0].status = "completed"
        activities[1].status = "planned"
        
        daily_planner.current_plan = DailyPlan(
            plan_id="test_plan",
            date=datetime.now(),
            activities=activities,
            total_planned_hours=1.5,
            focus_areas=["learning", "communication"],
            daily_goals=["Complete tasks"]
        )
        
        status = daily_planner.get_current_plan_status()
        assert status["total_activities"] == 2
        assert status["completed"] == 1
        assert status["planned"] == 1
        assert status["completion_rate"] == 0.5


class TestThoughtProcessor:
    """Test cases for the ThoughtProcessor."""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components for thought processor."""
        ai_brain = Mock(spec=AIBrain)
        ai_brain.analyze_situation = AsyncMock()
        ai_brain.think = AsyncMock()
        ai_brain.solve_problem = AsyncMock()
        ai_brain.reflect_on_experience = AsyncMock()
        ai_brain.generate_creative_content = AsyncMock()
        
        reasoning_engine = Mock(spec=ReasoningEngine)
        reasoning_engine.reason_deductively = AsyncMock()
        reasoning_engine.reason_inductively = AsyncMock()
        reasoning_engine.reason_abductively = AsyncMock()
        
        planning_engine = Mock(spec=PlanningEngine)
        planning_engine.create_goal = AsyncMock()
        planning_engine.create_plan = AsyncMock()
        
        daily_planner = Mock(spec=DailyPlanner)
        
        emotion_engine = Mock(spec=EmotionEngine)
        emotion_engine.get_current_emotional_state = Mock(return_value={
            "happiness": 0.7, "motivation": 0.8, "stress": 0.3
        })
        
        memory_system = Mock(spec=MemorySystem)
        memory_system.retrieve_memories = AsyncMock(return_value=[])
        memory_system.store_memory = AsyncMock()
        
        return (ai_brain, reasoning_engine, planning_engine, 
                daily_planner, emotion_engine, memory_system)
    
    @pytest.fixture
    def thought_processor(self, mock_components):
        """Create a ThoughtProcessor instance for testing."""
        (ai_brain, reasoning_engine, planning_engine, 
         daily_planner, emotion_engine, memory_system) = mock_components
        
        personality_traits = {
            "openness": 0.8,
            "conscientiousness": 0.7,
            "extraversion": 0.6,
            "agreeableness": 0.8,
            "neuroticism": 0.2
        }
        
        return ThoughtProcessor(
            "test_agent", ai_brain, reasoning_engine, planning_engine,
            daily_planner, emotion_engine, memory_system, personality_traits
        )
    
    @pytest.mark.asyncio
    async def test_thought_request_submission(self, thought_processor):
        """Test thought request submission and queuing."""
        await thought_processor.initialize()
        
        request = ThoughtRequest(
            request_id="test_request_1",
            trigger=ThoughtTrigger.EXTERNAL_EVENT,
            priority=ThoughtPriority.HIGH,
            context={"situation": "Need to solve a problem"},
            required_capabilities=["analysis", "reasoning"]
        )
        
        request_id = await thought_processor.submit_thought_request(request)
        
        assert request_id == "test_request_1"
        assert len(thought_processor.thought_queue) == 1
        
        # Submit another request with different priority
        request2 = ThoughtRequest(
            request_id="test_request_2",
            trigger=ThoughtTrigger.GOAL_DRIVEN,
            priority=ThoughtPriority.CRITICAL,
            context={"goal": "Urgent goal"},
            required_capabilities=["planning"]
        )
        
        await thought_processor.submit_thought_request(request2)
        
        # Queue should be sorted by priority (CRITICAL first)
        assert len(thought_processor.thought_queue) == 2
        assert thought_processor.thought_queue[0].priority == ThoughtPriority.CRITICAL
    
    @pytest.mark.asyncio
    async def test_immediate_thought_processing(self, thought_processor, mock_components):
        """Test immediate thought processing."""
        ai_brain = mock_components[0]
        
        # Setup mock response
        ai_brain.analyze_situation.return_value = {
            "analysis": "Situation analyzed",
            "insights": ["Key insight 1", "Key insight 2"],
            "recommendations": ["Action 1", "Action 2"],
            "confidence": 0.8
        }
        
        await thought_processor.initialize()
        
        request = ThoughtRequest(
            request_id="immediate_test",
            trigger=ThoughtTrigger.EXTERNAL_EVENT,
            priority=ThoughtPriority.HIGH,
            context={
                "situation": "Analyze this situation",
                "thinking_mode": "comprehensive_analysis"
            },
            required_capabilities=["analysis"]
        )
        
        result = await thought_processor.process_immediate_thought(request)
        
        assert result.request_id == "immediate_test"
        assert result.confidence == 0.8
        assert len(result.insights_gained) > 0
        assert len(result.actions_planned) > 0
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_situation_thinking(self, thought_processor, mock_components):
        """Test comprehensive situation thinking."""
        ai_brain, reasoning_engine = mock_components[0], mock_components[1]
        
        # Setup mocks
        ai_brain.analyze_situation.return_value = {
            "analysis": "Complex situation requiring careful analysis",
            "insights": ["Pattern identified", "Risk assessed"],
            "recommendations": ["Take action A", "Monitor situation"],
            "confidence": 0.85
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.conclusion = "Logical conclusion reached"
        mock_reasoning_result.confidence = 0.9
        reasoning_engine.reason_deductively.return_value = mock_reasoning_result
        reasoning_engine.reason_inductively.return_value = mock_reasoning_result
        
        await thought_processor.initialize()
        
        result = await thought_processor.think_about_situation(
            situation="Complex problem requiring analysis",
            context={"urgency": "high", "resources": "limited"},
            priority=ThoughtPriority.HIGH
        )
        
        assert result.confidence > 0.8
        assert len(result.insights_gained) >= 3  # Analysis + 2 reasoning conclusions
        assert len(result.actions_planned) > 0
        assert len(result.reasoning_chains) == 2  # Deductive + Inductive
    
    @pytest.mark.asyncio
    async def test_goal_planning_thought(self, thought_processor, mock_components):
        """Test goal planning thought process."""
        planning_engine = mock_components[2]
        reasoning_engine = mock_components[1]
        
        # Setup mocks
        mock_goal = Mock()
        mock_goal.goal_id = "test_goal_123"
        planning_engine.create_goal.return_value = mock_goal
        
        mock_plan = Mock()
        mock_plan.steps = ["Step 1", "Step 2", "Step 3"]
        mock_plan.success_probability = 0.8
        planning_engine.create_plan.return_value = mock_plan
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.conclusion = "Plan is feasible and well-structured"
        reasoning_engine.reason_deductively.return_value = mock_reasoning_result
        
        await thought_processor.initialize()
        
        result = await thought_processor.plan_for_goal(
            goal_description="Learn advanced machine learning",
            constraints=["Time: 6 months", "Budget: $500"],
            deadline=datetime.now() + timedelta(days=180)
        )
        
        assert result.confidence == 0.8
        assert len(result.insights_gained) >= 3
        assert len(result.actions_planned) == 3  # First 3 steps
        assert len(result.decisions_made) == 1
    
    @pytest.mark.asyncio
    async def test_creative_problem_solving(self, thought_processor, mock_components):
        """Test creative problem solving thought process."""
        ai_brain, reasoning_engine = mock_components[0], mock_components[1]
        
        # Setup mocks
        ai_brain.solve_problem.return_value = {
            "solution": "Innovative solution approach",
            "alternatives": ["Alternative 1", "Alternative 2"],
            "implementation_steps": ["Implement A", "Test B", "Deploy C"],
            "confidence": 0.75
        }
        
        ai_brain.generate_creative_content.return_value = {
            "content": "Creative alternative solution",
            "style": "innovative",
            "inspiration": "biomimicry"
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.conclusion = "Hybrid approach is best"
        reasoning_engine.reason_abductively.return_value = mock_reasoning_result
        
        await thought_processor.initialize()
        
        result = await thought_processor.solve_problem_creatively(
            problem="How to optimize energy consumption in smart buildings",
            context={"building_type": "office", "size": "large"},
            constraints=["Budget constraints", "Regulatory compliance"]
        )
        
        assert result.confidence == 0.75
        assert len(result.insights_gained) >= 2
        assert len(result.actions_planned) == 3  # Implementation steps
        assert len(result.decisions_made) == 1
        assert result.resources_used["creativity"] == 0.9
    
    def test_queue_management(self, thought_processor):
        """Test thought queue management and prioritization."""
        # Test queue status
        status = thought_processor.get_thought_queue_status()
        assert status["queue_size"] == 0
        assert status["processing_active"] == False
        
        # Add requests manually to test prioritization
        requests = [
            ThoughtRequest("req1", ThoughtTrigger.BACKGROUND, ThoughtPriority.LOW, {}),
            ThoughtRequest("req2", ThoughtTrigger.EXTERNAL_EVENT, ThoughtPriority.CRITICAL, {}),
            ThoughtRequest("req3", ThoughtTrigger.GOAL_DRIVEN, ThoughtPriority.MEDIUM, {})
        ]
        
        for req in requests:
            thought_processor.thought_queue.append(req)
        
        # Sort by priority (should happen automatically in real submission)
        thought_processor.thought_queue.sort(key=lambda r: r.priority.value, reverse=True)
        
        assert thought_processor.thought_queue[0].priority == ThoughtPriority.CRITICAL
        assert thought_processor.thought_queue[-1].priority == ThoughtPriority.LOW
    
    @pytest.mark.asyncio
    async def test_reflection_processing(self, thought_processor, mock_components):
        """Test reflection thought processing."""
        ai_brain, reasoning_engine, memory_system = mock_components[0], mock_components[1], mock_components[5]
        
        # Setup mocks
        ai_brain.reflect_on_experience.return_value = {
            "reflection": "Deep reflection on the experience",
            "learnings": ["Learning 1", "Learning 2"],
            "future_actions": ["Action 1", "Action 2"],
            "emotional_insights": {"growth": "Significant personal growth"},
            "confidence": 0.8
        }
        
        mock_reasoning_result = Mock()
        mock_reasoning_result.conclusion = "Experience taught valuable lessons"
        reasoning_engine.reason_inductively.return_value = mock_reasoning_result
        
        await thought_processor.initialize()
        
        result = await thought_processor.reflect_on_experience(
            experience={"event": "Completed challenging project", "duration": "3 months"},
            outcomes={"success": True, "skills_gained": ["leadership", "problem_solving"]},
            emotions={"satisfaction": 0.9, "pride": 0.8, "relief": 0.7}
        )
        
        assert result.confidence == 0.8
        assert len(result.insights_gained) >= 3  # Learnings + reasoning conclusion + emotional insights
        assert len(result.actions_planned) == 2
        
        # Verify memory storage was called
        memory_system.store_memory.assert_called()
    
    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self, thought_processor):
        """Test proper shutdown and cleanup."""
        await thought_processor.initialize()
        
        # Add some requests to queue
        request = ThoughtRequest(
            "shutdown_test", ThoughtTrigger.BACKGROUND, 
            ThoughtPriority.LOW, {"test": "data"}
        )
        await thought_processor.submit_thought_request(request)
        
        assert len(thought_processor.thought_queue) == 1
        
        # Shutdown should process remaining thoughts
        await thought_processor.shutdown()
        
        assert thought_processor.processing_active == False
        assert thought_processor.background_task.cancelled()


# Integration tests
class TestReasoningPlanningIntegration:
    """Integration tests for reasoning and planning systems."""
    
    @pytest.mark.asyncio
    async def test_full_reasoning_planning_workflow(self):
        """Test complete workflow from reasoning to planning to execution."""
        # This would test the full integration between all components
        # Simplified version for demonstration
        
        # Create mock components
        ai_brain = Mock(spec=AIBrain)
        ai_brain.analyze_situation = AsyncMock(return_value={
            "analysis": "Need systematic approach",
            "insights": ["Break down into steps"],
            "recommendations": ["Create detailed plan"],
            "confidence": 0.8
        })
        ai_brain.make_plan = AsyncMock(return_value={
            "steps": ["Research", "Design", "Implement", "Test"],
            "confidence": 0.85
        })
        
        reasoning_engine = ReasoningEngine("integration_test", ai_brain)
        planning_engine = PlanningEngine("integration_test", ai_brain, reasoning_engine)
        
        await reasoning_engine.initialize()
        await planning_engine.initialize()
        
        # Step 1: Reason about a problem
        reasoning_result = await reasoning_engine.reason_deductively([
            "Complex project requires systematic approach",
            "Available resources are limited",
            "Timeline is constrained"
        ])
        
        assert reasoning_result.confidence > 0.5
        
        # Step 2: Create goal based on reasoning
        goal = await planning_engine.create_goal(
            description="Complete complex project systematically",
            priority=8,
            success_criteria=["All phases completed", "Quality standards met"]
        )
        
        assert goal.status == GoalStatus.ACTIVE
        
        # Step 3: Create plan for goal
        plan = await planning_engine.create_plan(goal.goal_id)
        
        assert len(plan.steps) == 4
        assert plan.success_probability > 0.8
        
        # Step 4: Execute first step
        execution_result = await planning_engine.execute_plan_step(plan.plan_id)
        
        assert execution_result["status"] == "executed"
        assert plan.current_step == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])