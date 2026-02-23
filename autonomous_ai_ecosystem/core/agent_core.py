"""
Core agent orchestrator that manages the agent's lifecycle and coordinates between modules.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from .interfaces import (
    AgentIdentity, AgentState, AgentMessage, AgentStatus, 
    AgentModule, MessageType
)
from .config import Config
from .logger import get_agent_logger, log_agent_event


class LifecyclePhase(Enum):
    """Agent lifecycle phases."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    LEARNING = "learning"
    SLEEPING = "sleeping"
    MODIFYING = "modifying"
    REPRODUCING = "reproducing"
    SHUTTING_DOWN = "shutting_down"


class AgentCore:
    """
    Central orchestrator for each agent that manages the agent's lifecycle,
    coordinates between modules, and handles the sleep/wake cycle.
    """
    
    def __init__(self, identity: AgentIdentity, config: Config):
        self.identity = identity
        self.config = config
        self.logger = get_agent_logger(identity.agent_id, "core")
        
        # Agent state
        self.state = AgentState(
            agent_id=identity.agent_id,
            status=AgentStatus.OFFLINE,
            emotional_state={
                "motivation": 0.8,
                "boredom": 0.2,
                "happiness": 0.6,
                "curiosity": 0.9,
                "social_need": 0.5
            }
        )
        
        # Lifecycle management
        self.current_phase = LifecyclePhase.INITIALIZING
        self.last_sleep_time: Optional[datetime] = None
        self.daily_cycle_start: Optional[datetime] = None
        self.is_running = False
        
        # Module registry
        self.modules: Dict[str, AgentModule] = {}
        self.module_dependencies: Dict[str, List[str]] = {}
        
        # Task and message queues
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.human_commands: asyncio.Queue = asyncio.Queue()
        
        # Performance metrics
        self.metrics = {
            "uptime": 0.0,
            "messages_processed": 0,
            "tasks_completed": 0,
            "learning_sessions": 0,
            "code_modifications": 0,
            "social_interactions": 0
        }
        
        self.logger.info(f"Agent core initialized for {identity.name} ({identity.agent_id})")
    
    async def initialize(self) -> None:
        """Initialize the agent and all its modules."""
        try:
            self.logger.info("Starting agent initialization")
            self.current_phase = LifecyclePhase.INITIALIZING
            
            # Setup core modules
            await self._setup_core_modules()
            
            # Initialize modules in dependency order
            await self._initialize_modules()
            
            # Set initial state
            self.state.status = AgentStatus.ACTIVE
            self.state.last_activity = datetime.now()
            self.daily_cycle_start = datetime.now()
            self.is_running = True
            
            # Log birth event
            log_agent_event(
                self.identity.agent_id,
                "birth",
                {
                    "name": self.identity.name,
                    "gender": self.identity.gender.value,
                    "destiny": self.identity.destiny,
                    "generation": self.identity.generation,
                    "parents": self.identity.parent_agents
                }
            )
            
            self.logger.info("Agent initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent: {e}")
            raise
    
    async def run_daily_cycle(self) -> None:
        """Execute the main learning and interaction loop."""
        self.logger.info("Starting daily cycle")
        self.current_phase = LifecyclePhase.ACTIVE
        
        cycle_start = datetime.now()
        
        try:
            # Main activity loop
            while self.is_running and self._should_continue_cycle():
                await self._process_pending_messages()
                await self._process_human_commands()
                await self._execute_scheduled_tasks()
                await self._update_emotional_state()
                
                # Check if it's time for specific activities
                if self._should_enter_learning_phase():
                    await self._enter_learning_phase()
                
                if self._should_enter_sleep_mode():
                    await self._enter_sleep_mode()
                    break
                
                # Brief pause to prevent busy waiting
                await asyncio.sleep(1)
            
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            self.metrics["uptime"] += cycle_duration
            
            self.logger.info(f"Daily cycle completed in {cycle_duration:.2f} seconds")
            
        except Exception as e:
            self.logger.error(f"Error in daily cycle: {e}")
            raise
    
    async def enter_sleep_mode(self) -> None:
        """Prepare for code modification during sleep cycle."""
        self.logger.info("Entering sleep mode for code modification")
        self.current_phase = LifecyclePhase.SLEEPING
        self.state.status = AgentStatus.SLEEPING
        
        try:
            # Save current state
            await self._save_agent_state()
            
            # Notify other agents
            await self._broadcast_status_change()
            
            # Enter modification phase if enabled
            if self.config.safety.code_modification_enabled:
                await self._enter_modification_phase()
            
            self.last_sleep_time = datetime.now()
            
            log_agent_event(
                self.identity.agent_id,
                "sleep",
                {"reason": "daily_cycle_complete", "modifications_planned": True}
            )
            
        except Exception as e:
            self.logger.error(f"Error entering sleep mode: {e}")
            raise
    
    async def wake_up(self) -> None:
        """Resume operation after code changes."""
        self.logger.info("Waking up from sleep mode")
        
        try:
            # Validate any code changes
            if await self._validate_code_changes():
                self.logger.info("Code changes validated successfully")
            else:
                self.logger.warning("Code validation failed, reverting changes")
                await self._revert_code_changes()
            
            # Restart modules if necessary
            await self._restart_modified_modules()
            
            # Update state
            self.state.status = AgentStatus.ACTIVE
            self.current_phase = LifecyclePhase.ACTIVE
            self.daily_cycle_start = datetime.now()
            
            # Broadcast wake up
            await self._broadcast_status_change()
            
            log_agent_event(
                self.identity.agent_id,
                "wake_up",
                {"sleep_duration": self._get_sleep_duration(), "changes_applied": True}
            )
            
        except Exception as e:
            self.logger.error(f"Error waking up: {e}")
            raise
    
    async def process_message(self, message: AgentMessage) -> None:
        """Handle incoming communications."""
        self.logger.debug(f"Processing message from {message.sender_id}: {message.message_type.value}")
        
        try:
            # Add to message queue for processing
            await self.message_queue.put(message)
            self.metrics["messages_processed"] += 1
            
            # Handle high-priority messages immediately
            if message.priority >= 8:
                await self._handle_priority_message(message)
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    async def register_module(self, name: str, module: AgentModule, dependencies: List[str] = None) -> None:
        """Register a module with the agent core."""
        self.modules[name] = module
        self.module_dependencies[name] = dependencies or []
        self.logger.debug(f"Registered module: {name}")
    
    async def get_module(self, name: str) -> Optional[AgentModule]:
        """Get a registered module by name."""
        return self.modules.get(name)
    
    async def shutdown(self) -> None:
        """Shutdown the agent gracefully."""
        self.logger.info("Shutting down agent")
        self.current_phase = LifecyclePhase.SHUTTING_DOWN
        self.is_running = False
        
        try:
            # Save final state
            await self._save_agent_state()
            
            # Shutdown modules in reverse dependency order
            await self._shutdown_modules()
            
            # Log death event
            log_agent_event(
                self.identity.agent_id,
                "shutdown",
                {
                    "uptime": self.metrics["uptime"],
                    "final_status": self.state.status.value,
                    "metrics": self.metrics
                }
            )
            
            self.logger.info("Agent shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    # Public API methods for reasoning and planning
    
    async def think_about_situation(self, situation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Use the thought processor to think about a situation."""
        if hasattr(self, 'thought_processor'):
            result = await self.thought_processor.think_about_situation(situation, context)
            return {
                "insights": result.insights_gained,
                "actions": result.actions_planned,
                "confidence": result.confidence,
                "processing_time": result.processing_time
            }
        return {"error": "Thought processor not available"}
    
    async def create_daily_plan(self, focus_areas: List[str] = None) -> Dict[str, Any]:
        """Create a daily plan using the daily planner."""
        if hasattr(self, 'daily_planner'):
            plan = await self.daily_planner.create_daily_plan(focus_areas=focus_areas)
            return {
                "plan_id": plan.plan_id,
                "activities_count": len(plan.activities),
                "focus_areas": plan.focus_areas,
                "daily_goals": plan.daily_goals,
                "total_hours": plan.total_planned_hours
            }
        return {"error": "Daily planner not available"}
    
    async def execute_next_activity(self) -> Dict[str, Any]:
        """Execute the next activity in the daily plan."""
        if hasattr(self, 'daily_planner'):
            return await self.daily_planner.execute_next_activity()
        return {"error": "Daily planner not available"}
    
    # Private helper methods
    
    async def _setup_core_modules(self) -> None:
        """Setup and register all core agent modules."""
        try:
            self.logger.info("Setting up core modules")
            
            # Import module classes (delayed import to avoid circular dependencies)
            from ..agents.memory import MemorySystem
            from ..agents.emotions import EmotionEngine
            from ..agents.decision_making import DecisionMaker
            from ..agents.brain import AIBrain
            from ..agents.reasoning import ReasoningEngine, PlanningEngine
            from ..agents.daily_planner import DailyPlanner
            from ..agents.thought_processor import ThoughtProcessor
            
            # Create core modules
            memory_system = MemorySystem(self.identity.agent_id, self.config.data_directory)
            emotion_engine = EmotionEngine(self.identity.agent_id, self.identity.personality_traits)
            ai_brain = AIBrain(self.identity.agent_id, self.config.llm, self.identity.personality_traits)
            
            # Create decision maker with the correct parameters
            decision_maker = DecisionMaker(self.identity.agent_id, emotion_engine, memory_system)
            
            # Create reasoning and planning modules
            reasoning_engine = ReasoningEngine(self.identity.agent_id, ai_brain)
            planning_engine = PlanningEngine(self.identity.agent_id, ai_brain, reasoning_engine)
            daily_planner = DailyPlanner(
                self.identity.agent_id, ai_brain, reasoning_engine, 
                planning_engine, self.identity.personality_traits
            )
            thought_processor = ThoughtProcessor(
                self.identity.agent_id, ai_brain, reasoning_engine,
                planning_engine, daily_planner, emotion_engine,
                memory_system, self.identity.personality_traits
            )
            
            # Register modules with dependencies
            await self.register_module("memory_system", memory_system)
            await self.register_module("emotion_engine", emotion_engine)
            await self.register_module("ai_brain", ai_brain)
            await self.register_module("decision_maker", decision_maker, ["emotion_engine", "memory_system"])
            await self.register_module("reasoning_engine", reasoning_engine, ["ai_brain"])
            await self.register_module("planning_engine", planning_engine, ["ai_brain", "reasoning_engine"])
            await self.register_module("daily_planner", daily_planner, ["ai_brain", "reasoning_engine", "planning_engine"])
            await self.register_module("thought_processor", thought_processor, 
                                     ["ai_brain", "reasoning_engine", "planning_engine", 
                                      "daily_planner", "emotion_engine", "memory_system"])
            
            # Store references for easy access
            self.memory_system = memory_system
            self.emotion_engine = emotion_engine
            self.decision_maker = decision_maker
            self.ai_brain = ai_brain
            self.reasoning_engine = reasoning_engine
            self.planning_engine = planning_engine
            self.daily_planner = daily_planner
            self.thought_processor = thought_processor
            
            self.logger.info("Core modules setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup core modules: {e}")
            raise
    
    async def _initialize_modules(self) -> None:
        """Initialize all registered modules in dependency order."""
        try:
            self.logger.info("Initializing modules")
            
            # Topological sort to initialize modules in dependency order
            sorted_modules = self._topological_sort_modules()
            
            for module_name in sorted_modules:
                if module_name in self.modules:
                    module = self.modules[module_name]
                    self.logger.debug(f"Initializing module: {module_name}")
                    await module.initialize()
            
            self.logger.info("All modules initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize modules: {e}")
            raise
    
    def _topological_sort_modules(self) -> List[str]:
        """Sort modules in dependency order using topological sort."""
        # Simple implementation for small number of modules
        sorted_modules = []
        visited = set()
        
        def visit(module_name: str):
            if module_name in visited:
                return
            visited.add(module_name)
            
            # Visit dependencies first
            for dep in self.module_dependencies.get(module_name, []):
                if dep in self.modules:
                    visit(dep)
            
            sorted_modules.append(module_name)
        
        # Visit all modules
        for module_name in self.modules:
            visit(module_name)
        
        return sorted_modules
    
    async def _shutdown_modules(self) -> None:
        """Shutdown all modules in reverse dependency order."""
        try:
            self.logger.info("Shutting down modules")
            
            # Reverse topological sort for shutdown
            sorted_modules = self._topological_sort_modules()
            sorted_modules.reverse()
            
            for module_name in sorted_modules:
                if module_name in self.modules:
                    module = self.modules[module_name]
                    self.logger.debug(f"Shutting down module: {module_name}")
                    await module.shutdown()
            
            self.logger.info("All modules shut down successfully")
            
        except Exception as e:
            self.logger.error(f"Error during module shutdown: {e}")
    
    async def _save_agent_state(self) -> None:
        """Save current agent state to persistent storage."""
        try:
            # Save to database or file
            pass
        except Exception as e:
            self.logger.error(f"Failed to save agent state: {e}")
    
    async def _process_pending_messages(self) -> None:
        """Process messages in the queue."""
        try:
            # Process a limited number of messages per cycle
            for _ in range(5):  # Process up to 5 messages per cycle
                if not self.message_queue.empty():
                    message = await self.message_queue.get()
                    await self._handle_message(message)
                else:
                    break
        except Exception as e:
            self.logger.error(f"Error processing messages: {e}")
    
    async def _process_human_commands(self) -> None:
        """Process commands from human creator."""
        try:
            # Process human commands if any
            pass
        except Exception as e:
            self.logger.error(f"Error processing human commands: {e}")
    
    async def _execute_scheduled_tasks(self) -> None:
        """Execute scheduled tasks."""
        try:
            # Execute any scheduled tasks
            pass
        except Exception as e:
            self.logger.error(f"Error executing scheduled tasks: {e}")
    
    async def _update_emotional_state(self) -> None:
        """Update agent's emotional state."""
        try:
            if hasattr(self, 'emotion_engine'):
                await self.emotion_engine.update_emotional_state(self.state.emotional_state)
        except Exception as e:
            self.logger.error(f"Error updating emotional state: {e}")
    
    def _should_continue_cycle(self) -> bool:
        """Check if the daily cycle should continue."""
        if not self.is_running:
            return False
            
        # Check if daily cycle time limit has been reached
        if self.daily_cycle_start:
            cycle_duration = (datetime.now() - self.daily_cycle_start).total_seconds()
            max_cycle_time = self.config.agent_lifecycle_hours * 3600  # Convert to seconds
            if cycle_duration >= max_cycle_time:
                return False
        
        return True
    
    def _should_enter_learning_phase(self) -> bool:
        """Check if it's time to enter learning phase."""
        # Simplified logic - would be more complex in reality
        return False
    
    async def _enter_learning_phase(self) -> None:
        """Enter learning phase to acquire new knowledge."""
        self.logger.info("Entering learning phase")
        self.current_phase = LifecyclePhase.LEARNING
        
        try:
            # Would integrate with learning module here
            await asyncio.sleep(2)  # Simulate learning time
            
            self.metrics["learning_sessions"] += 1
            self.current_phase = LifecyclePhase.ACTIVE
            
        except Exception as e:
            self.logger.error(f"Error in learning phase: {e}")
            self.current_phase = LifecyclePhase.ACTIVE
    
    def _should_enter_sleep_mode(self) -> bool:
        """Check if it's time to enter sleep mode."""
        # Simplified logic - would be more complex in reality
        return False
    
    async def _enter_sleep_mode(self) -> None:
        """Enter sleep mode for code modification."""
        await self.enter_sleep_mode()
    
    async def _enter_modification_phase(self) -> None:
        """Allow agent to modify its own code during sleep."""
        self.logger.info("Entering code modification phase")
        self.current_phase = LifecyclePhase.MODIFYING
        
        try:
            # Would integrate with code modification module here
            await asyncio.sleep(1)  # Simulate modification time
            
            self.metrics["code_modifications"] += 1
            self.current_phase = LifecyclePhase.SLEEPING
            
        except Exception as e:
            self.logger.error(f"Error in modification phase: {e}")
            self.current_phase = LifecyclePhase.SLEEPING
    
    async def _validate_code_changes(self) -> bool:
        """Validate any code changes made during sleep."""
        # Would integrate with validation module here
        return True
    
    async def _revert_code_changes(self) -> None:
        """Revert invalid code changes."""
        self.logger.info("Reverting code changes")
        # Would integrate with sandbox/reversion module here
    
    async def _restart_modified_modules(self) -> None:
        """Restart modules that were modified."""
        # Would restart any modified modules here
        pass
    
    async def _broadcast_status_change(self) -> None:
        """Notify other agents of status change."""
        # Would send status update messages to other agents
        pass
    
    def _get_sleep_duration(self) -> float:
        """Get duration of sleep period."""
        if self.last_sleep_time:
            return (datetime.now() - self.last_sleep_time).total_seconds()
        return 0.0
    
    async def _handle_message(self, message: AgentMessage) -> None:
        """Handle an individual message."""
        try:
            # Route message to appropriate handler based on type
            if message.message_type == MessageType.CHAT:
                await self._handle_chat_message(message)
            elif message.message_type == MessageType.TASK:
                await self._handle_task_message(message)
            elif message.message_type == MessageType.KNOWLEDGE:
                await self._handle_knowledge_message(message)
            elif message.message_type == MessageType.COMMAND:
                await self._handle_command_message(message)
            else:
                self.logger.warning(f"Unknown message type: {message.message_type}")
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    async def _handle_chat_message(self, message: AgentMessage) -> None:
        """Handle chat messages."""
        self.logger.debug(f"Handling chat from {message.sender_id}: {message.content}")
        # Would process chat message using AI brain
    
    async def _handle_task_message(self, message: AgentMessage) -> None:
        """Handle task assignment messages."""
        self.logger.debug(f"Handling task from {message.sender_id}: {message.content}")
        # Would process task using planning engine
    
    async def _handle_knowledge_message(self, message: AgentMessage) -> None:
        """Handle knowledge sharing messages."""
        self.logger.debug(f"Handling knowledge from {message.sender_id}: {message.content}")
        # Would process knowledge using memory system
    
    async def _handle_command_message(self, message: AgentMessage) -> None:
        """Handle command messages."""
        self.logger.debug(f"Handling command from {message.sender_id}: {message.content}")
        # Would process command using decision maker
    
    async def _handle_priority_message(self, message: AgentMessage) -> None:
        """Handle high-priority messages immediately."""
        await self._handle_message(message)