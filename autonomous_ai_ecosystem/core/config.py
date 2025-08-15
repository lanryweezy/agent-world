"""
Configuration management for the autonomous AI ecosystem.
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    type: str = "sqlite"  # sqlite, postgresql, mongodb
    host: str = "localhost"
    port: int = 5432
    database: str = "ai_ecosystem"
    username: Optional[str] = None
    password: Optional[str] = None
    connection_pool_size: int = 10


@dataclass
class LLMConfig:
    """Language model configuration."""
    provider: str = "openai"  # openai, anthropic, local
    model: str = "gpt-4"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 30


@dataclass
class NetworkConfig:
    """Network communication configuration."""
    base_port: int = 8000
    max_connections: int = 100
    heartbeat_interval: int = 30
    message_timeout: int = 10
    retry_attempts: int = 3
    buffer_size: int = 8192


@dataclass
class LearningConfig:
    """Learning and browsing configuration."""
    daily_learning_hours: int = 8
    max_concurrent_browsers: int = 5
    browser_timeout: int = 30
    content_filter_enabled: bool = True
    max_pages_per_session: int = 50
    knowledge_validation_threshold: float = 0.7


@dataclass
class SafetyConfig:
    """Safety and security configuration."""
    code_modification_enabled: bool = True
    sandbox_enabled: bool = True
    max_code_changes_per_day: int = 5
    validation_required: bool = True
    emergency_shutdown_enabled: bool = True
    resource_limits: Dict[str, Any] = field(default_factory=lambda: {
        "max_memory_mb": 1024,
        "max_cpu_percent": 80,
        "max_disk_mb": 500
    })


@dataclass
class MemoryConfig:
    """Memory system configuration."""
    max_short_term_memory_items: int = 1000
    max_long_term_memory_items: int = 10000
    consolidation_threshold: float = 0.7
    forgetting_threshold: float = 0.3
    memory_retention_hours: int = 168  # 1 week
    compression_enabled: bool = True
    max_compressed_memory_size: int = 1000000  # 1MB


@dataclass
class Config:
    """Main configuration class for the AI ecosystem."""
    
    # Core settings
    ecosystem_name: str = "AutonomousAI"
    data_directory: str = "./data"
    log_level: str = "INFO"
    debug_mode: bool = False
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    
    # Agent settings
    max_agents: int = 50
    initial_agent_count: int = 5
    agent_lifecycle_hours: int = 24
    reproduction_enabled: bool = True
    
    # Human oversight
    human_oversight_enabled: bool = True
    god_mode_enabled: bool = True
    intervention_alerts: bool = True
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'Config':
        """Load configuration from a JSON file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            # Create default config file
            default_config = cls()
            default_config.save_to_file(config_path)
            return default_config
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        return cls.from_dict(config_data)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Config':
        """Create config from dictionary."""
        # Extract nested configurations
        database_config = DatabaseConfig(**config_dict.get('database', {}))
        llm_config = LLMConfig(**config_dict.get('llm', {}))
        network_config = NetworkConfig(**config_dict.get('network', {}))
        learning_config = LearningConfig(**config_dict.get('learning', {}))
        safety_config = SafetyConfig(**config_dict.get('safety', {}))
        memory_config = MemoryConfig(**config_dict.get('memory', {}))
        
        # Remove nested configs from main dict
        main_config = {k: v for k, v in config_dict.items() 
                      if k not in ['database', 'llm', 'network', 'learning', 'safety', 'memory']}
        
        return cls(
            database=database_config,
            llm=llm_config,
            network=network_config,
            learning=learning_config,
            safety=safety_config,
            memory=memory_config,
            **main_config
        )
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to a JSON file."""
        config_dict = self.to_dict()
        
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'ecosystem_name': self.ecosystem_name,
            'data_directory': self.data_directory,
            'log_level': self.log_level,
            'debug_mode': self.debug_mode,
            'max_agents': self.max_agents,
            'initial_agent_count': self.initial_agent_count,
            'agent_lifecycle_hours': self.agent_lifecycle_hours,
            'reproduction_enabled': self.reproduction_enabled,
            'human_oversight_enabled': self.human_oversight_enabled,
            'god_mode_enabled': self.god_mode_enabled,
            'intervention_alerts': self.intervention_alerts,
            'database': {
                'type': self.database.type,
                'host': self.database.host,
                'port': self.database.port,
                'database': self.database.database,
                'username': self.database.username,
                'password': self.database.password,
                'connection_pool_size': self.database.connection_pool_size
            },
            'llm': {
                'provider': self.llm.provider,
                'model': self.llm.model,
                'api_key': self.llm.api_key,
                'api_base': self.llm.api_base,
                'max_tokens': self.llm.max_tokens,
                'temperature': self.llm.temperature,
                'timeout': self.llm.timeout
            },
            'network': {
                'base_port': self.network.base_port,
                'max_connections': self.network.max_connections,
                'heartbeat_interval': self.network.heartbeat_interval,
                'message_timeout': self.network.message_timeout,
                'retry_attempts': self.network.retry_attempts,
                'buffer_size': self.network.buffer_size
            },
            'learning': {
                'daily_learning_hours': self.learning.daily_learning_hours,
                'max_concurrent_browsers': self.learning.max_concurrent_browsers,
                'browser_timeout': self.learning.browser_timeout,
                'content_filter_enabled': self.learning.content_filter_enabled,
                'max_pages_per_session': self.learning.max_pages_per_session,
                'knowledge_validation_threshold': self.learning.knowledge_validation_threshold
            },
            'safety': {
                'code_modification_enabled': self.safety.code_modification_enabled,
                'sandbox_enabled': self.safety.sandbox_enabled,
                'max_code_changes_per_day': self.safety.max_code_changes_per_day,
                'validation_required': self.safety.validation_required,
                'emergency_shutdown_enabled': self.safety.emergency_shutdown_enabled,
                'resource_limits': self.safety.resource_limits
            },
            'memory': {
                'max_short_term_memory_items': self.memory.max_short_term_memory_items,
                'max_long_term_memory_items': self.memory.max_long_term_memory_items,
                'consolidation_threshold': self.memory.consolidation_threshold,
                'forgetting_threshold': self.memory.forgetting_threshold,
                'memory_retention_hours': self.memory.memory_retention_hours,
                'compression_enabled': self.memory.compression_enabled,
                'max_compressed_memory_size': self.memory.max_compressed_memory_size
            }
        }
    
    def get_agent_port(self, agent_id: str) -> int:
        """Get unique port for an agent based on its ID."""
        # Simple hash-based port assignment
        agent_hash = hash(agent_id) % 1000
        return self.network.base_port + agent_hash
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        if self.max_agents <= 0:
            issues.append("max_agents must be positive")
        
        if self.initial_agent_count > self.max_agents:
            issues.append("initial_agent_count cannot exceed max_agents")
        
        if self.network.base_port < 1024:
            issues.append("base_port should be >= 1024 to avoid privileged ports")
        
        if self.learning.daily_learning_hours > 24:
            issues.append("daily_learning_hours cannot exceed 24")
        
        if not os.path.exists(self.data_directory):
            try:
                os.makedirs(self.data_directory, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create data directory: {e}")
        
        return issues