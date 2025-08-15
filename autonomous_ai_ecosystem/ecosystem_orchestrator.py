"""
Main ecosystem orchestrator for the autonomous AI ecosystem.

This module coordinates all systems and provides the main application
entry point for initializing and managing the entire ecosystem.
"""

import asyncio
import json
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
import uuid

from .core.interfaces import AgentModule
from .core.logger import get_agent_logger, log_agent_event
from .core.config import DatabaseConfig, LLMConfig, NetworkConfig
from .core.identity_manager import IdentityManager
from .core.state_manager import StateManager

# Import core system components (import others dynamically to avoid circular imports)
from .safety.safety_validator import ComprehensiveSafetyValidator
from .safety.emergency_response import EmergencyResponseSystem
from .orchestration.agent_manager import AgentManager
from .orchestration.distributed_coordinator import DistributedCoordinator


@dataclass
class SystemStatus:
    """Status of a system component."""
    name: str
    status: str  # initializing, running, stopped, failed
    initialized_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EcosystemConfig:
    """Configuration for the entire ecosystem."""
    # Core settings
    ecosystem_id: str = field(default_factory=lambda: f"ecosystem_{uuid.uuid4().hex[:8]}")
    log_level: str = "INFO"
    data_directory: str = "ecosystem_data"
    
    # System enablement flags
    enable_web_browsing: bool = True
    enable_virtual_world: bool = True
    enable_economy: bool = True
    enable_reproduction: bool = True
    enable_distributed_mode: bool = False
    enable_human_oversight: bool = True
    enable_safety_systems: bool = True
    
    # Resource limits
    max_agents: int = 50
    max_memory_mb: int = 4096
    max_cpu_percent: float = 80.0
    
    # Network settings
    host: str = "localhost"
    port: int = 8080
    cluster_mode: bool = False
    
    # Safety settings
    safety_level: str = "high"  # low, medium, high, maximum
    emergency_shutdown_enabled: bool = True
    
    # Performance settings
    health_check_interval: int = 60
    cleanup_interval: int = 300
    backup_interval: int = 3600


class EcosystemOrchestrator:
    """
    Main orchestrator for the autonomous AI ecosystem.
    
    Coordinates all systems, manages configuration, handles startup/shutdown,
    and provides integration testing capabilities.
    """
    
    def __init__(self, config: Optional[EcosystemConfig] = None):
        self.config = config or EcosystemConfig()
        self.logger = get_agent_logger("ecosystem_orchestrator", "orchestrator")
        
        # System components
        self.systems: Dict[str, AgentModule] = {}
        self.system_status: Dict[str, SystemStatus] = {}
        
        # Core systems (always required)
        self.identity_manager: Optional[IdentityManager] = None
        self.state_manager: Optional[StateManager] = None
        
        # Communication
        self.message_router: Optional[MessageRouter] = None
        
        # Agent systems
        self.agent_manager: Optional[AgentManager] = None
        self.distributed_coordinator: Optional[DistributedCoordinator] = None
        
        # Safety systems
        self.safety_validator: Optional[ComprehensiveSafetyValidator] = None
        self.emergency_response: Optional[EmergencyResponseSystem] = None
        
        # Service systems
        self.capability_registry: Optional[ServiceCapabilityRegistry] = None
        self.quality_feedback: Optional[ServiceQualityFeedbackSystem] = None
        
        # Oversight systems
        self.command_router: Optional[CommandRouter] = None
        self.task_delegator: Optional[TaskDelegator] = None
        self.monitoring_reporting: Optional[MonitoringReporting] = None
        
        # Runtime state
        self.is_running = False
        self.startup_time: Optional[datetime] = None
        self.shutdown_requested = False
        
        # Background tasks
        self.health_check_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "total_systems": 0,
            "running_systems": 0,
            "failed_systems": 0,
            "total_agents": 0,
            "uptime_seconds": 0.0,
            "startup_time_seconds": 0.0,
            "health_checks_performed": 0,
            "system_restarts": 0
        }
        
        self.logger.info(f"Ecosystem orchestrator created (ID: {self.config.ecosystem_id})")
    
    async def initialize(self) -> bool:
        """Initialize the entire ecosystem."""
        try:
            self.logger.info("Starting ecosystem initialization...")
            start_time = datetime.now()
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Initialize core systems first
            await self._initialize_core_systems()
            
            # Initialize communication systems
            await self._initialize_communication_systems()
            
            # Initialize safety systems
            if self.config.enable_safety_systems:
                await self._initialize_safety_systems()
            
            # Initialize orchestration systems
            await self._initialize_orchestration_systems()
            
            # Initialize service systems
            await self._initialize_service_systems()
            
            # Initialize oversight systems
            if self.config.enable_human_oversight:
                await self._initialize_oversight_systems()
            
            # Initialize optional systems based on configuration
            await self._initialize_optional_systems()
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Mark as running
            self.is_running = True
            self.startup_time = datetime.now()
            
            startup_duration = (self.startup_time - start_time).total_seconds()
            self.stats["startup_time_seconds"] = startup_duration
            
            log_agent_event(
                "ecosystem_orchestrator",
                "ecosystem_initialized",
                {
                    "ecosystem_id": self.config.ecosystem_id,
                    "total_systems": len(self.systems),
                    "startup_time_seconds": startup_duration,
                    "enabled_features": self._get_enabled_features()
                }
            )
            
            self.logger.info(f"Ecosystem initialization completed in {startup_duration:.2f}s")
            self.logger.info(f"Total systems initialized: {len(self.systems)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ecosystem: {e}")
            await self._emergency_shutdown()
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the entire ecosystem gracefully."""
        try:
            if self.shutdown_requested:
                return
            
            self.shutdown_requested = True
            self.logger.info("Starting ecosystem shutdown...")
            
            # Cancel background tasks
            if self.health_check_task:
                self.health_check_task.cancel()
            if self.cleanup_task:
                self.cleanup_task.cancel()
            
            # Shutdown systems in reverse order of initialization
            shutdown_order = [
                # Optional systems first
                "virtual_world", "construction_system", "currency_system", "marketplace",
                "dataset_manager", "model_trainer", "web_browser", "knowledge_extractor",
                
                # Service systems
                "creative_service", "automation_service", "monitoring_service",
                "data_analysis_service", "coding_service", "research_service",
                "quality_feedback", "capability_registry",
                
                # Oversight systems
                "monitoring_reporting", "task_delegator", "command_router",
                
                # Orchestration systems
                "distributed_coordinator", "agent_manager",
                
                # Safety systems
                "emergency_response", "safety_validator",
                
                # Communication systems
                "message_router",
                
                # Core systems last
                "state_manager", "identity_manager"
            ]
            
            for system_name in shutdown_order:
                if system_name in self.systems:
                    await self._shutdown_system(system_name)
            
            self.is_running = False
            
            log_agent_event(
                "ecosystem_orchestrator",
                "ecosystem_shutdown",
                {
                    "ecosystem_id": self.config.ecosystem_id,
                    "uptime_seconds": self._get_uptime_seconds(),
                    "systems_shutdown": len(self.systems)
                }
            )
            
            self.logger.info("Ecosystem shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during ecosystem shutdown: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        try:
            # Update statistics
            self.stats["total_systems"] = len(self.systems)
            self.stats["running_systems"] = len([
                status for status in self.system_status.values()
                if status.status == "running"
            ])
            self.stats["failed_systems"] = len([
                status for status in self.system_status.values()
                if status.status == "failed"
            ])
            self.stats["uptime_seconds"] = self._get_uptime_seconds()
            
            # Get agent count from agent manager
            if self.agent_manager:
                agent_statuses = await self.agent_manager.get_all_agents_status()
                self.stats["total_agents"] = len(agent_statuses)
            
            return {
                "ecosystem_id": self.config.ecosystem_id,
                "is_running": self.is_running,
                "startup_time": self.startup_time.isoformat() if self.startup_time else None,
                "uptime_seconds": self.stats["uptime_seconds"],
                "statistics": self.stats,
                "configuration": {
                    "max_agents": self.config.max_agents,
                    "enable_web_browsing": self.config.enable_web_browsing,
                    "enable_virtual_world": self.config.enable_virtual_world,
                    "enable_economy": self.config.enable_economy,
                    "enable_reproduction": self.config.enable_reproduction,
                    "enable_distributed_mode": self.config.enable_distributed_mode,
                    "enable_human_oversight": self.config.enable_human_oversight,
                    "enable_safety_systems": self.config.enable_safety_systems,
                    "safety_level": self.config.safety_level
                },
                "systems": {
                    name: {
                        "status": status.status,
                        "initialized_at": status.initialized_at.isoformat() if status.initialized_at else None,
                        "last_health_check": status.last_health_check.isoformat() if status.last_health_check else None,
                        "error_message": status.error_message,
                        "metadata": status.metadata
                    }
                    for name, status in self.system_status.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system status: {e}")
            return {}
    
    async def restart_system(self, system_name: str) -> bool:
        """Restart a specific system."""
        try:
            if system_name not in self.systems:
                return False
            
            self.logger.info(f"Restarting system: {system_name}")
            
            # Shutdown system
            await self._shutdown_system(system_name)
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Reinitialize system
            success = await self._initialize_system(system_name, self.systems[system_name])
            
            if success:
                self.stats["system_restarts"] += 1
                self.logger.info(f"System restarted successfully: {system_name}")
            else:
                self.logger.error(f"Failed to restart system: {system_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to restart system {system_name}: {e}")
            return False
    
    async def spawn_agent(self, agent_config: Dict[str, Any]) -> str:
        """Spawn a new agent in the ecosystem."""
        try:
            if not self.agent_manager:
                raise Exception("Agent manager not available")
            
            agent_id = agent_config.get("agent_id", f"agent_{uuid.uuid4().hex[:8]}")
            
            process_id = await self.agent_manager.spawn_agent(
                agent_id=agent_id,
                config=agent_config.get("config", {}),
                environment=agent_config.get("environment", {}),
                resource_limits=agent_config.get("resource_limits", {})
            )
            
            if process_id:
                self.logger.info(f"Agent spawned successfully: {agent_id}")
                return agent_id
            else:
                raise Exception("Failed to spawn agent")
            
        except Exception as e:
            self.logger.error(f"Failed to spawn agent: {e}")
            return ""
    
    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a specific agent."""
        try:
            if not self.agent_manager:
                return False
            
            return await self.agent_manager.stop_agent(agent_id)
            
        except Exception as e:
            self.logger.error(f"Failed to stop agent {agent_id}: {e}")
            return False
    
    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent."""
        try:
            if not self.agent_manager:
                return None
            
            return await self.agent_manager.get_agent_status(agent_id)
            
        except Exception as e:
            self.logger.error(f"Failed to get agent status for {agent_id}: {e}")
            return None
    
    async def _initialize_core_systems(self) -> None:
        """Initialize core systems."""
        # Identity manager
        self.identity_manager = IdentityManager()
        # Core systems don't need async initialization
        self.systems["identity_manager"] = self.identity_manager
        self.system_status["identity_manager"] = SystemStatus(
            name="identity_manager",
            status="running",
            initialized_at=datetime.now()
        )
        
        # State manager
        self.state_manager = StateManager()
        self.systems["state_manager"] = self.state_manager
        self.system_status["state_manager"] = SystemStatus(
            name="state_manager",
            status="running",
            initialized_at=datetime.now()
        )
    
    async def _initialize_communication_systems(self) -> None:
        """Initialize communication systems."""
        try:
            from .communication.message_router import MessageRouter
            from .communication.protocol import NetworkManager
            
            # Create network manager first
            network_manager = NetworkManager()
            await self._initialize_system("network_manager", network_manager)
            
            # Message router
            self.message_router = MessageRouter("message_router", network_manager)
            await self._initialize_system("message_router", self.message_router)
        except ImportError as e:
            self.logger.warning(f"Failed to import communication systems: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize communication systems: {e}")
    
    async def _initialize_safety_systems(self) -> None:
        """Initialize safety systems."""
        # Safety validator
        self.safety_validator = ComprehensiveSafetyValidator()
        await self._initialize_system("safety_validator", self.safety_validator)
        
        # Emergency response system
        if self.config.emergency_shutdown_enabled:
            self.emergency_response = EmergencyResponseSystem()
            await self._initialize_system("emergency_response", self.emergency_response)
    
    async def _initialize_orchestration_systems(self) -> None:
        """Initialize orchestration systems."""
        # Agent manager
        self.agent_manager = AgentManager()
        await self._initialize_system("agent_manager", self.agent_manager)
        
        # Distributed coordinator (if enabled)
        if self.config.enable_distributed_mode:
            self.distributed_coordinator = DistributedCoordinator()
            await self._initialize_system("distributed_coordinator", self.distributed_coordinator)
    
    async def _initialize_service_systems(self) -> None:
        """Initialize service systems."""
        try:
            from .services.capability_registry import ServiceCapabilityRegistry
            from .services.quality_feedback_system import ServiceQualityFeedbackSystem
            from .services.research_service import WebResearchService
            from .services.coding_service import CodingAssistanceService
            from .services.data_analysis_service import DataAnalysisService
            from .services.monitoring_service import ContinuousMonitoringService
            from .services.automation_service import WorkflowAutomationService
            from .services.creative_service import CreativeContentService
            
            # Service capability registry
            self.capability_registry = ServiceCapabilityRegistry()
            await self._initialize_system("capability_registry", self.capability_registry)
            
            # Quality feedback system
            self.quality_feedback = ServiceQualityFeedbackSystem()
            await self._initialize_system("quality_feedback", self.quality_feedback)
            
            # Research service
            research_service = WebResearchService("research_service")
            await self._initialize_system("research_service", research_service)
            
            # Coding service
            coding_service = CodingAssistanceService("coding_service")
            await self._initialize_system("coding_service", coding_service)
            
            # Data analysis service
            data_analysis_service = DataAnalysisService("data_analysis_service")
            await self._initialize_system("data_analysis_service", data_analysis_service)
            
            # Monitoring service
            monitoring_service = ContinuousMonitoringService("monitoring_service")
            await self._initialize_system("monitoring_service", monitoring_service)
            
            # Automation service
            automation_service = WorkflowAutomationService("automation_service")
            await self._initialize_system("automation_service", automation_service)
            
            # Creative service
            creative_service = CreativeContentService("creative_service")
            await self._initialize_system("creative_service", creative_service)
            
        except ImportError as e:
            self.logger.warning(f"Failed to import service systems: {e}")
    
    async def _initialize_oversight_systems(self) -> None:
        """Initialize human oversight systems."""
        try:
            from .oversight.command_router import CommandRouter
            from .oversight.task_delegator import TaskDelegator
            from .oversight.monitoring_reporting import MonitoringReporting
            
            # Command router
            self.command_router = CommandRouter()
            await self._initialize_system("command_router", self.command_router)
            
            # Task delegator
            self.task_delegator = TaskDelegator()
            await self._initialize_system("task_delegator", self.task_delegator)
            
            # Monitoring and reporting
            self.monitoring_reporting = MonitoringReporting()
            await self._initialize_system("monitoring_reporting", self.monitoring_reporting)
            
        except ImportError as e:
            self.logger.warning(f"Failed to import oversight systems: {e}")
    
    async def _initialize_optional_systems(self) -> None:
        """Initialize optional systems based on configuration."""
        # Web browsing and learning
        if self.config.enable_web_browsing:
            try:
                from .learning.web_browser import WebBrowser
                from .learning.knowledge_extractor import KnowledgeExtractor
                
                web_browser = WebBrowser("web_browser")
                await self._initialize_system("web_browser", web_browser)
                
                knowledge_extractor = KnowledgeExtractor("knowledge_extractor")
                await self._initialize_system("knowledge_extractor", knowledge_extractor)
            except ImportError as e:
                self.logger.warning(f"Failed to import web browsing systems: {e}")
        
        # Virtual world
        if self.config.enable_virtual_world:
            try:
                from .world.virtual_world import VirtualWorld
                from .world.construction import ConstructionSystem
                
                virtual_world = VirtualWorld()
                await self._initialize_system("virtual_world", virtual_world)
                
                construction_system = ConstructionSystem()
                await self._initialize_system("construction_system", construction_system)
            except ImportError as e:
                self.logger.warning(f"Failed to import virtual world systems: {e}")
        
        # Economy
        if self.config.enable_economy:
            try:
                from .economy.currency import CurrencySystem
                from .economy.marketplace import Marketplace
                
                currency_system = CurrencySystem()
                await self._initialize_system("currency_system", currency_system)
                
                marketplace = Marketplace()
                await self._initialize_system("marketplace", marketplace)
            except ImportError as e:
                self.logger.warning(f"Failed to import economy systems: {e}")
        
        # Knowledge and training
        try:
            from .knowledge.dataset_manager import DatasetManager
            from .knowledge.model_trainer import ModelTrainer
            
            dataset_manager = DatasetManager()
            await self._initialize_system("dataset_manager", dataset_manager)
            
            model_trainer = ModelTrainer()
            await self._initialize_system("model_trainer", model_trainer)
        except ImportError as e:
            self.logger.warning(f"Failed to import knowledge systems: {e}")
    
    async def _initialize_system(self, name: str, system: AgentModule) -> bool:
        """Initialize a single system."""
        try:
            self.logger.info(f"Initializing system: {name}")
            
            # Create status entry
            status = SystemStatus(
                name=name,
                status="initializing"
            )
            self.system_status[name] = status
            
            # Initialize the system
            await system.initialize()
            
            # Store system reference
            self.systems[name] = system
            
            # Update status
            status.status = "running"
            status.initialized_at = datetime.now()
            
            self.logger.info(f"System initialized successfully: {name}")
            return True
            
        except Exception as e:
            # Update status with error
            if name in self.system_status:
                self.system_status[name].status = "failed"
                self.system_status[name].error_message = str(e)
            
            self.logger.error(f"Failed to initialize system {name}: {e}")
            return False
    
    async def _shutdown_system(self, name: str) -> None:
        """Shutdown a single system."""
        try:
            if name not in self.systems:
                return
            
            self.logger.info(f"Shutting down system: {name}")
            
            system = self.systems[name]
            await system.shutdown()
            
            # Update status
            if name in self.system_status:
                self.system_status[name].status = "stopped"
            
            self.logger.info(f"System shutdown completed: {name}")
            
        except Exception as e:
            self.logger.error(f"Error shutting down system {name}: {e}")
    
    async def _start_background_tasks(self) -> None:
        """Start background monitoring and maintenance tasks."""
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _health_check_loop(self) -> None:
        """Periodic health check of all systems."""
        while self.is_running and not self.shutdown_requested:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                for name, system in self.systems.items():
                    await self._check_system_health(name, system)
                
                self.stats["health_checks_performed"] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of resources and old data."""
        while self.is_running and not self.shutdown_requested:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                
                # Perform cleanup operations
                await self._perform_cleanup()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    async def _check_system_health(self, name: str, system: AgentModule) -> None:
        """Check health of a specific system."""
        try:
            # Update last health check time
            if name in self.system_status:
                self.system_status[name].last_health_check = datetime.now()
            
            # TODO: Implement actual health check logic
            # For now, just verify the system is still accessible
            if hasattr(system, 'get_status'):
                status = await system.get_status()
                if name in self.system_status:
                    self.system_status[name].metadata.update(status or {})
            
        except Exception as e:
            self.logger.warning(f"Health check failed for system {name}: {e}")
            
            if name in self.system_status:
                self.system_status[name].status = "failed"
                self.system_status[name].error_message = str(e)
    
    async def _perform_cleanup(self) -> None:
        """Perform periodic cleanup operations."""
        try:
            # Clean up old log entries, temporary files, etc.
            # This is a placeholder for actual cleanup logic
            pass
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def _emergency_shutdown(self) -> None:
        """Perform emergency shutdown of the ecosystem."""
        try:
            self.logger.critical("Performing emergency shutdown")
            
            if self.emergency_response:
                await self.emergency_response.trigger_emergency_shutdown(
                    reason="system_initialization_failure",
                    description="Emergency shutdown due to initialization failure"
                )
            else:
                # Fallback emergency shutdown
                await self.shutdown()
            
        except Exception as e:
            self.logger.critical(f"Emergency shutdown failed: {e}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(self.shutdown())
        
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except Exception as e:
            self.logger.warning(f"Failed to setup signal handlers: {e}")
    
    def _get_uptime_seconds(self) -> float:
        """Get ecosystem uptime in seconds."""
        if self.startup_time:
            return (datetime.now() - self.startup_time).total_seconds()
        return 0.0
    
    def _get_enabled_features(self) -> List[str]:
        """Get list of enabled features."""
        features = []
        
        if self.config.enable_web_browsing:
            features.append("web_browsing")
        if self.config.enable_virtual_world:
            features.append("virtual_world")
        if self.config.enable_economy:
            features.append("economy")
        if self.config.enable_reproduction:
            features.append("reproduction")
        if self.config.enable_distributed_mode:
            features.append("distributed_mode")
        if self.config.enable_human_oversight:
            features.append("human_oversight")
        if self.config.enable_safety_systems:
            features.append("safety_systems")
        
        return features


async def main():
    """Main entry point for the ecosystem."""
    try:
        # Load configuration from file if it exists
        config_file = "ecosystem_config.json"
        config = EcosystemConfig()
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    # Update config with loaded data
                    for key, value in config_data.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
                print(f"Configuration loaded from {config_file}")
            except Exception as e:
                print(f"Warning: Failed to load config from {config_file}: {e}")
        
        # Create and initialize orchestrator
        orchestrator = EcosystemOrchestrator(config)
        
        print(f"Starting Autonomous AI Ecosystem (ID: {config.ecosystem_id})")
        print(f"Safety Level: {config.safety_level}")
        print(f"Max Agents: {config.max_agents}")
        print("Initializing systems...")
        
        success = await orchestrator.initialize()
        
        if not success:
            print("Failed to initialize ecosystem")
            return 1
        
        print("Ecosystem initialized successfully!")
        print(f"Systems running: {len(orchestrator.systems)}")
        
        # Print system status
        status = await orchestrator.get_system_status()
        print(f"Uptime: {status['uptime_seconds']:.1f}s")
        print(f"Running systems: {status['statistics']['running_systems']}")
        print(f"Failed systems: {status['statistics']['failed_systems']}")
        
        # Keep running until shutdown signal
        try:
            while orchestrator.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutdown requested by user")
        
        # Graceful shutdown
        print("Shutting down ecosystem...")
        await orchestrator.shutdown()
        print("Ecosystem shutdown completed")
        
        return 0
        
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    import os
    sys.exit(asyncio.run(main()))