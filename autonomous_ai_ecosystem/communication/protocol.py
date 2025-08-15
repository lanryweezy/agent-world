"""
Message protocol and serialization for agent communication.

This module implements the standardized message format, serialization,
and validation for inter-agent communication in the ecosystem.
"""

import json
import uuid
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import asdict
from enum import Enum

from ..core.interfaces import AgentMessage, MessageType
from ..core.logger import get_agent_logger
from ..utils.validators import validate_message
from ..utils.generators import generate_message_id


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


class MessageStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"


class ProtocolVersion(Enum):
    """Protocol version for compatibility."""
    V1_0 = "1.0"
    CURRENT = V1_0


class MessageProtocol:
    """
    Handles message protocol, serialization, and validation for agent communication.
    """
    
    def __init__(self):
        self.logger = get_agent_logger("SYSTEM", "message_protocol")
        self.protocol_version = ProtocolVersion.CURRENT
        self.max_message_size = 1024 * 1024  # 1MB
        self.message_ttl = 3600  # 1 hour in seconds
    
    def create_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: MessageType,
        content: Dict[str, Any],
        priority: int = MessagePriority.NORMAL.value,
        requires_response: bool = False,
        correlation_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> AgentMessage:
        """
        Create a new agent message with proper formatting and validation.
        
        Args:
            sender_id: ID of the sending agent
            recipient_id: ID of the receiving agent
            message_type: Type of message
            content: Message content dictionary
            priority: Message priority (1-10)
            requires_response: Whether response is required
            correlation_id: Optional correlation ID for request/response pairs
            expires_at: Optional expiration timestamp
            
        Returns:
            Created AgentMessage
            
        Raises:
            ValueError: If message validation fails
        """
        try:
            # Generate message ID
            message_id = generate_message_id()
            
            # Add protocol metadata to content
            enhanced_content = {
                **content,
                "_protocol_version": self.protocol_version.value,
                "_created_at": datetime.now().isoformat(),
                "_correlation_id": correlation_id,
                "_expires_at": expires_at.isoformat() if expires_at else None
            }
            
            # Create message
            message = AgentMessage(
                message_id=message_id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                message_type=message_type,
                content=enhanced_content,
                timestamp=datetime.now(),
                priority=priority,
                requires_response=requires_response
            )
            
            # Validate message
            validation_errors = validate_message(message)
            if validation_errors:
                raise ValueError(f"Message validation failed: {validation_errors}")
            
            self.logger.debug(f"Created message {message_id} from {sender_id} to {recipient_id}")
            
            return message
            
        except Exception as e:
            self.logger.error(f"Failed to create message: {e}")
            raise
    
    def serialize_message(self, message: AgentMessage) -> bytes:
        """
        Serialize a message to bytes for transmission.
        
        Args:
            message: AgentMessage to serialize
            
        Returns:
            Serialized message as bytes
            
        Raises:
            ValueError: If serialization fails
        """
        try:
            # Convert message to dictionary
            message_dict = {
                "message_id": message.message_id,
                "sender_id": message.sender_id,
                "recipient_id": message.recipient_id,
                "message_type": message.message_type.value,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "priority": message.priority,
                "requires_response": message.requires_response
            }
            
            # Add protocol envelope
            envelope = {
                "protocol_version": self.protocol_version.value,
                "message": message_dict,
                "checksum": self._calculate_checksum(message_dict),
                "serialized_at": datetime.now().isoformat()
            }
            
            # Serialize to JSON bytes
            serialized = json.dumps(envelope, ensure_ascii=False).encode('utf-8')
            
            # Check size limit
            if len(serialized) > self.max_message_size:
                raise ValueError(f"Message size {len(serialized)} exceeds limit {self.max_message_size}")
            
            self.logger.debug(f"Serialized message {message.message_id} ({len(serialized)} bytes)")
            
            return serialized
            
        except Exception as e:
            self.logger.error(f"Failed to serialize message {message.message_id}: {e}")
            raise
    
    def deserialize_message(self, data: bytes) -> AgentMessage:
        """
        Deserialize bytes back to an AgentMessage.
        
        Args:
            data: Serialized message bytes
            
        Returns:
            Deserialized AgentMessage
            
        Raises:
            ValueError: If deserialization fails
        """
        try:
            # Decode JSON
            envelope = json.loads(data.decode('utf-8'))
            
            # Validate protocol version
            if envelope.get("protocol_version") != self.protocol_version.value:
                raise ValueError(f"Unsupported protocol version: {envelope.get('protocol_version')}")
            
            # Extract message data
            message_dict = envelope["message"]
            
            # Verify checksum
            expected_checksum = envelope.get("checksum")
            actual_checksum = self._calculate_checksum(message_dict)
            if expected_checksum != actual_checksum:
                raise ValueError("Message checksum verification failed")
            
            # Create AgentMessage
            message = AgentMessage(
                message_id=message_dict["message_id"],
                sender_id=message_dict["sender_id"],
                recipient_id=message_dict["recipient_id"],
                message_type=MessageType(message_dict["message_type"]),
                content=message_dict["content"],
                timestamp=datetime.fromisoformat(message_dict["timestamp"]),
                priority=message_dict["priority"],
                requires_response=message_dict["requires_response"]
            )
            
            # Validate deserialized message
            validation_errors = validate_message(message)
            if validation_errors:
                raise ValueError(f"Deserialized message validation failed: {validation_errors}")
            
            # Check if message has expired
            if self._is_message_expired(message):
                raise ValueError("Message has expired")
            
            self.logger.debug(f"Deserialized message {message.message_id}")
            
            return message
            
        except Exception as e:
            self.logger.error(f"Failed to deserialize message: {e}")
            raise
    
    def create_response_message(
        self,
        original_message: AgentMessage,
        response_content: Dict[str, Any],
        success: bool = True
    ) -> AgentMessage:
        """
        Create a response message to an original message.
        
        Args:
            original_message: Original message being responded to
            response_content: Response content
            success: Whether the response indicates success
            
        Returns:
            Response AgentMessage
        """
        try:
            # Prepare response content
            enhanced_content = {
                **response_content,
                "_response_to": original_message.message_id,
                "_success": success,
                "_response_timestamp": datetime.now().isoformat()
            }
            
            # Create response message
            response = self.create_message(
                sender_id=original_message.recipient_id,
                recipient_id=original_message.sender_id,
                message_type=MessageType.CHAT,  # Default response type
                content=enhanced_content,
                priority=original_message.priority,
                requires_response=False,
                correlation_id=original_message.content.get("_correlation_id")
            )
            
            self.logger.debug(f"Created response {response.message_id} for {original_message.message_id}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to create response message: {e}")
            raise
    
    def create_broadcast_message(
        self,
        sender_id: str,
        message_type: MessageType,
        content: Dict[str, Any],
        priority: int = MessagePriority.NORMAL.value
    ) -> AgentMessage:
        """
        Create a broadcast message for multiple recipients.
        
        Args:
            sender_id: ID of the sending agent
            message_type: Type of message
            content: Message content
            priority: Message priority
            
        Returns:
            Broadcast AgentMessage (recipient_id will be "BROADCAST")
        """
        try:
            # Add broadcast metadata
            enhanced_content = {
                **content,
                "_broadcast": True,
                "_broadcast_timestamp": datetime.now().isoformat()
            }
            
            # Create broadcast message
            message = self.create_message(
                sender_id=sender_id,
                recipient_id="BROADCAST",
                message_type=message_type,
                content=enhanced_content,
                priority=priority,
                requires_response=False
            )
            
            self.logger.debug(f"Created broadcast message {message.message_id}")
            
            return message
            
        except Exception as e:
            self.logger.error(f"Failed to create broadcast message: {e}")
            raise
    
    def validate_message_integrity(self, message: AgentMessage) -> bool:
        """
        Validate message integrity and format.
        
        Args:
            message: AgentMessage to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic validation
            validation_errors = validate_message(message)
            if validation_errors:
                self.logger.warning(f"Message validation failed: {validation_errors}")
                return False
            
            # Check protocol version
            protocol_version = message.content.get("_protocol_version")
            if protocol_version and protocol_version != self.protocol_version.value:
                self.logger.warning(f"Unsupported protocol version: {protocol_version}")
                return False
            
            # Check expiration
            if self._is_message_expired(message):
                self.logger.warning(f"Message {message.message_id} has expired")
                return False
            
            # Check content size
            content_size = len(json.dumps(message.content))
            if content_size > self.max_message_size:
                self.logger.warning(f"Message content too large: {content_size} bytes")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating message integrity: {e}")
            return False
    
    def extract_correlation_id(self, message: AgentMessage) -> Optional[str]:
        """
        Extract correlation ID from message for request/response tracking.
        
        Args:
            message: AgentMessage to extract from
            
        Returns:
            Correlation ID if present, None otherwise
        """
        return message.content.get("_correlation_id")
    
    def is_response_message(self, message: AgentMessage) -> bool:
        """
        Check if message is a response to another message.
        
        Args:
            message: AgentMessage to check
            
        Returns:
            True if it's a response message, False otherwise
        """
        return "_response_to" in message.content
    
    def get_response_to_id(self, message: AgentMessage) -> Optional[str]:
        """
        Get the ID of the message this is responding to.
        
        Args:
            message: Response message
            
        Returns:
            Original message ID if this is a response, None otherwise
        """
        return message.content.get("_response_to")
    
    def create_error_response(
        self,
        original_message: AgentMessage,
        error_message: str,
        error_code: Optional[str] = None
    ) -> AgentMessage:
        """
        Create an error response message.
        
        Args:
            original_message: Original message that caused the error
            error_message: Error description
            error_code: Optional error code
            
        Returns:
            Error response AgentMessage
        """
        try:
            error_content = {
                "error": True,
                "error_message": error_message,
                "error_code": error_code,
                "original_message_id": original_message.message_id
            }
            
            return self.create_response_message(
                original_message,
                error_content,
                success=False
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create error response: {e}")
            raise
    
    # Private helper methods
    
    def _calculate_checksum(self, message_dict: Dict[str, Any]) -> str:
        """Calculate checksum for message integrity."""
        # Create deterministic string representation
        message_str = json.dumps(message_dict, sort_keys=True, ensure_ascii=False)
        
        # Calculate SHA-256 hash
        return hashlib.sha256(message_str.encode('utf-8')).hexdigest()[:16]
    
    def _is_message_expired(self, message: AgentMessage) -> bool:
        """Check if message has expired."""
        expires_at_str = message.content.get("_expires_at")
        if not expires_at_str:
            # Check default TTL
            message_age = (datetime.now() - message.timestamp).total_seconds()
            return message_age > self.message_ttl
        
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            return datetime.now() > expires_at
        except (ValueError, TypeError):
            return False


class MessageQueue:
    """
    Simple message queue for handling message delivery and retry logic.
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.pending_messages: List[Dict[str, Any]] = []
        self.failed_messages: List[Dict[str, Any]] = []
        self.logger = get_agent_logger("SYSTEM", "message_queue")
    
    def enqueue_message(
        self,
        message: AgentMessage,
        retry_count: int = 0,
        max_retries: int = 3
    ) -> bool:
        """
        Add message to the queue for delivery.
        
        Args:
            message: AgentMessage to queue
            retry_count: Current retry count
            max_retries: Maximum retry attempts
            
        Returns:
            True if queued successfully, False if queue is full
        """
        if len(self.pending_messages) >= self.max_size:
            self.logger.warning("Message queue is full")
            return False
        
        queue_entry = {
            "message": message,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "queued_at": datetime.now(),
            "status": MessageStatus.PENDING.value
        }
        
        self.pending_messages.append(queue_entry)
        self.logger.debug(f"Queued message {message.message_id}")
        
        return True
    
    def dequeue_message(self) -> Optional[Dict[str, Any]]:
        """
        Get next message from queue for delivery.
        
        Returns:
            Next message entry or None if queue is empty
        """
        if not self.pending_messages:
            return None
        
        return self.pending_messages.pop(0)
    
    def mark_message_delivered(self, message_id: str) -> bool:
        """
        Mark a message as successfully delivered.
        
        Args:
            message_id: ID of delivered message
            
        Returns:
            True if found and marked, False otherwise
        """
        # Remove from pending if still there
        self.pending_messages = [
            entry for entry in self.pending_messages 
            if entry["message"].message_id != message_id
        ]
        
        self.logger.debug(f"Marked message {message_id} as delivered")
        return True
    
    def mark_message_failed(self, message_id: str, error: str) -> bool:
        """
        Mark a message as failed delivery.
        
        Args:
            message_id: ID of failed message
            error: Error description
            
        Returns:
            True if found and marked, False otherwise
        """
        # Find and move to failed queue
        for i, entry in enumerate(self.pending_messages):
            if entry["message"].message_id == message_id:
                entry["status"] = MessageStatus.FAILED.value
                entry["error"] = error
                entry["failed_at"] = datetime.now()
                
                failed_entry = self.pending_messages.pop(i)
                self.failed_messages.append(failed_entry)
                
                self.logger.warning(f"Marked message {message_id} as failed: {error}")
                return True
        
        return False
    
    def retry_message(self, message_id: str) -> bool:
        """
        Retry a failed message if retries are available.
        
        Args:
            message_id: ID of message to retry
            
        Returns:
            True if retry queued, False otherwise
        """
        # Find in failed messages
        for i, entry in enumerate(self.failed_messages):
            if entry["message"].message_id == message_id:
                if entry["retry_count"] < entry["max_retries"]:
                    # Move back to pending with incremented retry count
                    entry["retry_count"] += 1
                    entry["status"] = MessageStatus.PENDING.value
                    entry["retried_at"] = datetime.now()
                    
                    retry_entry = self.failed_messages.pop(i)
                    self.pending_messages.append(retry_entry)
                    
                    self.logger.info(f"Retrying message {message_id} (attempt {entry['retry_count']})")
                    return True
        
        return False
    
    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        return {
            "pending": len(self.pending_messages),
            "failed": len(self.failed_messages),
            "total_capacity": self.max_size,
            "available_capacity": self.max_size - len(self.pending_messages)
        }
    
    def cleanup_old_messages(self, max_age_hours: int = 24) -> int:
        """
        Clean up old messages from the queue.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of messages cleaned up
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Clean pending messages
        old_pending = [
            entry for entry in self.pending_messages
            if entry["queued_at"] < cutoff_time
        ]
        self.pending_messages = [
            entry for entry in self.pending_messages
            if entry["queued_at"] >= cutoff_time
        ]
        
        # Clean failed messages
        old_failed = [
            entry for entry in self.failed_messages
            if entry.get("failed_at", entry["queued_at"]) < cutoff_time
        ]
        self.failed_messages = [
            entry for entry in self.failed_messages
            if entry.get("failed_at", entry["queued_at"]) >= cutoff_time
        ]
        
        cleaned_count = len(old_pending) + len(old_failed)
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} old messages")
        
        return cleaned_count