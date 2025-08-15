"""
Logging infrastructure for the autonomous AI ecosystem.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import json


class EcosystemFormatter(logging.Formatter):
    """Custom formatter for ecosystem logs."""
    
    def __init__(self):
        super().__init__()
        self.start_time = datetime.now()
    
    def format(self, record):
        # Add ecosystem-specific fields
        if not hasattr(record, 'agent_id'):
            record.agent_id = 'SYSTEM'
        
        if not hasattr(record, 'component'):
            record.component = record.name.split('.')[-1]
        
        # Calculate runtime
        runtime = datetime.now() - self.start_time
        record.runtime = f"{runtime.total_seconds():.2f}s"
        
        # Format the message
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        return (f"[{timestamp}] [{record.runtime}] "
                f"{record.levelname:8} | {record.agent_id:12} | "
                f"{record.component:15} | {record.getMessage()}")


class AgentLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds agent context to log messages."""
    
    def __init__(self, logger, agent_id: str, component: str = ""):
        super().__init__(logger, {})
        self.agent_id = agent_id
        self.component = component
    
    def process(self, msg, kwargs):
        # Add agent context to extra fields
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra']['agent_id'] = self.agent_id
        kwargs['extra']['component'] = self.component
        
        return msg, kwargs


def setup_logger(
    name: str = "autonomous_ai_ecosystem",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    data_directory: str = "./data"
) -> logging.Logger:
    """
    Set up logging for the autonomous AI ecosystem.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        data_directory: Directory for log files
    
    Returns:
        Configured logger instance
    """
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = EcosystemFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(data_directory) / "logs" / log_file
    else:
        log_path = Path(data_directory) / "logs" / f"ecosystem_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add a JSON handler for structured logging
    json_log_path = log_path.with_suffix('.json')
    json_handler = logging.FileHandler(json_log_path)
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)
    
    logger.info(f"Logging initialized - Console: {log_level}, File: {log_path}")
    
    return logger


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add agent-specific fields if available
        if hasattr(record, 'agent_id'):
            log_entry['agent_id'] = record.agent_id
        
        if hasattr(record, 'component'):
            log_entry['component'] = record.component
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


def get_agent_logger(agent_id: str, component: str = "") -> AgentLoggerAdapter:
    """
    Get a logger adapter for a specific agent.
    
    Args:
        agent_id: Unique agent identifier
        component: Component name (e.g., 'brain', 'memory', 'communication')
    
    Returns:
        Logger adapter with agent context
    """
    base_logger = logging.getLogger("autonomous_ai_ecosystem")
    return AgentLoggerAdapter(base_logger, agent_id, component)


def log_agent_event(
    agent_id: str,
    event_type: str,
    details: dict,
    level: str = "INFO"
) -> None:
    """
    Log a structured agent event.
    
    Args:
        agent_id: Agent identifier
        event_type: Type of event (e.g., 'birth', 'learning', 'communication')
        details: Event details dictionary
        level: Log level
    """
    logger = get_agent_logger(agent_id, "events")
    
    message = f"{event_type.upper()}: {json.dumps(details, default=str)}"
    
    log_method = getattr(logger, level.lower())
    log_method(message)


def log_system_metric(metric_name: str, value: float, tags: dict = None) -> None:
    """
    Log a system metric.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        tags: Optional tags for the metric
    """
    logger = logging.getLogger("autonomous_ai_ecosystem")
    
    metric_data = {
        'metric': metric_name,
        'value': value,
        'timestamp': datetime.now().isoformat()
    }
    
    if tags:
        metric_data['tags'] = tags
    
    logger.info(f"METRIC: {json.dumps(metric_data)}", extra={'component': 'metrics'})