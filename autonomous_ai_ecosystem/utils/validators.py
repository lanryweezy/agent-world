"""
Validation utilities for the autonomous AI ecosystem.
"""

import re
from typing import List, Dict, Any
from datetime import datetime

from ..core.interfaces import AgentIdentity, AgentMessage, AgentGender, MessageType


def validate_agent_identity(identity: AgentIdentity) -> List[str]:
    """
    Validate an agent identity and return list of validation errors.
    
    Args:
        identity: AgentIdentity to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Validate agent ID format
    if not identity.agent_id:
        errors.append("Agent ID is required")
    elif not re.match(r'^[a-zA-Z0-9_-]+$', identity.agent_id):
        errors.append("Agent ID must contain only alphanumeric characters, underscores, and hyphens")
    elif len(identity.agent_id) > 50:
        errors.append("Agent ID must be 50 characters or less")
    
    # Validate name
    if not identity.name:
        errors.append("Agent name is required")
    elif len(identity.name) > 100:
        errors.append("Agent name must be 100 characters or less")
    elif not re.match(r'^[a-zA-Z0-9\s_-]+$', identity.name):
        errors.append("Agent name contains invalid characters")
    
    # Validate gender
    if not isinstance(identity.gender, AgentGender):
        errors.append("Gender must be a valid AgentGender enum value")
    
    # Validate personality traits
    if not identity.personality_traits:
        errors.append("Personality traits are required")
    else:
        required_traits = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
        for trait in required_traits:
            if trait not in identity.personality_traits:
                errors.append(f"Missing required personality trait: {trait}")
            else:
                value = identity.personality_traits[trait]
                if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                    errors.append(f"Personality trait {trait} must be a number between 0 and 1")
    
    # Validate destiny
    if not identity.destiny:
        errors.append("Agent destiny is required")
    elif len(identity.destiny) > 500:
        errors.append("Agent destiny must be 500 characters or less")
    
    # Validate birth timestamp
    if not isinstance(identity.birth_timestamp, datetime):
        errors.append("Birth timestamp must be a datetime object")
    elif identity.birth_timestamp > datetime.now():
        errors.append("Birth timestamp cannot be in the future")
    
    # Validate generation
    if not isinstance(identity.generation, int) or identity.generation < 0:
        errors.append("Generation must be a non-negative integer")
    
    # Validate parent agents
    if identity.parent_agents:
        if len(identity.parent_agents) > 2:
            errors.append("Agent cannot have more than 2 parents")
        for parent_id in identity.parent_agents:
            if not isinstance(parent_id, str) or not parent_id:
                errors.append("Parent agent IDs must be non-empty strings")
    
    return errors


def validate_message(message: AgentMessage) -> List[str]:
    """
    Validate an agent message and return list of validation errors.
    
    Args:
        message: AgentMessage to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Validate message ID
    if not message.message_id:
        errors.append("Message ID is required")
    elif not isinstance(message.message_id, str):
        errors.append("Message ID must be a string")
    
    # Validate sender and recipient IDs
    if not message.sender_id:
        errors.append("Sender ID is required")
    elif not isinstance(message.sender_id, str):
        errors.append("Sender ID must be a string")
    
    if not message.recipient_id:
        errors.append("Recipient ID is required")
    elif not isinstance(message.recipient_id, str):
        errors.append("Recipient ID must be a string")
    
    if message.sender_id == message.recipient_id:
        errors.append("Sender and recipient cannot be the same")
    
    # Validate message type
    if not isinstance(message.message_type, MessageType):
        errors.append("Message type must be a valid MessageType enum value")
    
    # Validate content
    if not isinstance(message.content, dict):
        errors.append("Message content must be a dictionary")
    
    # Validate timestamp
    if not isinstance(message.timestamp, datetime):
        errors.append("Timestamp must be a datetime object")
    elif message.timestamp > datetime.now():
        errors.append("Timestamp cannot be in the future")
    
    # Validate priority
    if not isinstance(message.priority, int) or not 1 <= message.priority <= 10:
        errors.append("Priority must be an integer between 1 and 10")
    
    # Validate requires_response
    if not isinstance(message.requires_response, bool):
        errors.append("requires_response must be a boolean")
    
    return errors


def validate_personality_traits(traits: Dict[str, float]) -> List[str]:
    """
    Validate personality traits dictionary.
    
    Args:
        traits: Dictionary of personality traits
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    required_traits = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
    
    for trait in required_traits:
        if trait not in traits:
            errors.append(f"Missing required personality trait: {trait}")
        else:
            value = traits[trait]
            if not isinstance(value, (int, float)):
                errors.append(f"Personality trait {trait} must be a number")
            elif not 0 <= value <= 1:
                errors.append(f"Personality trait {trait} must be between 0 and 1")
    
    # Check for unknown traits
    for trait in traits:
        if trait not in required_traits:
            errors.append(f"Unknown personality trait: {trait}")
    
    return errors


def validate_emotional_state(emotional_state: Dict[str, float]) -> List[str]:
    """
    Validate emotional state dictionary.
    
    Args:
        emotional_state: Dictionary of emotional states
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    required_emotions = ['motivation', 'boredom', 'happiness', 'curiosity', 'social_need']
    
    for emotion in required_emotions:
        if emotion not in emotional_state:
            errors.append(f"Missing required emotional state: {emotion}")
        else:
            value = emotional_state[emotion]
            if not isinstance(value, (int, float)):
                errors.append(f"Emotional state {emotion} must be a number")
            elif not 0 <= value <= 1:
                errors.append(f"Emotional state {emotion} must be between 0 and 1")
    
    return errors


def validate_agent_name(name: str) -> bool:
    """
    Validate agent name format.
    
    Args:
        name: Agent name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not name or not isinstance(name, str):
        return False
    
    if len(name) > 100:
        return False
    
    # Allow letters, numbers, spaces, underscores, and hyphens
    return bool(re.match(r'^[a-zA-Z0-9\s_-]+$', name))


def validate_destiny(destiny: str) -> bool:
    """
    Validate agent destiny format.
    
    Args:
        destiny: Agent destiny to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not destiny or not isinstance(destiny, str):
        return False
    
    if len(destiny) > 500:
        return False
    
    # Basic content validation - should be meaningful text
    if len(destiny.strip()) < 10:
        return False
    
    return True


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input text.
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\']', '', text)
    
    # Limit length
    sanitized = sanitized[:max_length]
    
    # Remove excessive whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized