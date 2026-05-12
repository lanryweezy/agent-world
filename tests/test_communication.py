"""
Unit tests for communication components.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta

from autonomous_ai_ecosystem.communication.protocol import (
    MessageProtocol, MessageQueue, MessagePriority, MessageStatus
)
from autonomous_ai_ecosystem.core.interfaces import MessageType
from autonomous_ai_ecosystem.utils.generators import generate_agent_id


class TestMessageProtocol:
    """Test cases for MessageProtocol."""
    
    def setup_method(self):
        """Set up test environment."""
        self.protocol = MessageProtocol()
        self.sender_id = generate_agent_id()
        self.recipient_id = generate_agent_id()
    
    def test_create_message(self):
        """Test creating a basic message."""
        content = {"text": "Hello, world!", "data": {"key": "value"}}
        
        message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content=content,
            priority=MessagePriority.HIGH.value,
            requires_response=True
        )
        
        assert message.sender_id == self.sender_id
        assert message.recipient_id == self.recipient_id
        assert message.message_type == MessageType.CHAT
        assert message.priority == MessagePriority.HIGH.value
        assert message.requires_response
        assert "text" in message.content
        assert "_protocol_version" in message.content
        assert "_created_at" in message.content
    
    def test_serialize_and_deserialize_message(self):
        """Test message serialization and deserialization."""
        # Create message
        original_message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.KNOWLEDGE_SHARE,
            content={"knowledge": "Important information", "source": "test"}
        )
        
        # Serialize
        serialized = self.protocol.serialize_message(original_message)
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
        
        # Deserialize
        deserialized_message = self.protocol.deserialize_message(serialized)
        
        # Verify equality
        assert deserialized_message.message_id == original_message.message_id
        assert deserialized_message.sender_id == original_message.sender_id
        assert deserialized_message.recipient_id == original_message.recipient_id
        assert deserialized_message.message_type == original_message.message_type
        assert deserialized_message.priority == original_message.priority
        assert deserialized_message.requires_response == original_message.requires_response
        
        # Content should match (excluding protocol metadata)
        assert deserialized_message.content["knowledge"] == original_message.content["knowledge"]
        assert deserialized_message.content["source"] == original_message.content["source"]
    
    def test_create_response_message(self):
        """Test creating response messages."""
        # Create original message
        original_message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.COLLABORATION_REQUEST,
            content={"request": "Help with task", "task_id": "123"},
            requires_response=True
        )
        
        # Create response
        response_content = {"response": "I can help", "accepted": True}
        response_message = self.protocol.create_response_message(
            original_message,
            response_content,
            success=True
        )
        
        # Verify response properties
        assert response_message.sender_id == original_message.recipient_id
        assert response_message.recipient_id == original_message.sender_id
        assert response_message.priority == original_message.priority
        assert not response_message.requires_response
        
        # Verify response content
        assert response_message.content["response"] == "I can help"
        assert response_message.content["accepted"]
        assert response_message.content["_response_to"] == original_message.message_id
        assert response_message.content["_success"]
    
    def test_create_broadcast_message(self):
        """Test creating broadcast messages."""
        content = {"announcement": "System maintenance in 1 hour"}
        
        broadcast_message = self.protocol.create_broadcast_message(
            sender_id=self.sender_id,
            message_type=MessageType.STATUS_UPDATE,
            content=content,
            priority=MessagePriority.HIGH.value
        )
        
        assert broadcast_message.sender_id == self.sender_id
        assert broadcast_message.recipient_id == "BROADCAST"
        assert broadcast_message.message_type == MessageType.STATUS_UPDATE
        assert broadcast_message.priority == MessagePriority.HIGH.value
        assert broadcast_message.content["_broadcast"]
        assert "announcement" in broadcast_message.content
    
    def test_create_error_response(self):
        """Test creating error response messages."""
        # Create original message
        original_message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.TASK_ASSIGNMENT,
            content={"task": "Invalid task"}
        )
        
        # Create error response
        error_response = self.protocol.create_error_response(
            original_message,
            "Task not found",
            "TASK_NOT_FOUND"
        )
        
        assert error_response.sender_id == original_message.recipient_id
        assert error_response.recipient_id == original_message.sender_id
        assert error_response.content["error"]
        assert error_response.content["error_message"] == "Task not found"
        assert error_response.content["error_code"] == "TASK_NOT_FOUND"
        assert not error_response.content["_success"]
    
    def test_message_validation(self):
        """Test message validation."""
        # Create valid message
        valid_message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content={"text": "Valid message"}
        )
        
        assert self.protocol.validate_message_integrity(valid_message)
        
        # Test with expired message
        expired_message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content={"text": "Expired message"},
            expires_at=datetime.now() - timedelta(hours=1)
        )
        
        assert not self.protocol.validate_message_integrity(expired_message)
    
    def test_correlation_id_handling(self):
        """Test correlation ID extraction and handling."""
        correlation_id = "test-correlation-123"
        
        # Create message with correlation ID
        message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content={"text": "Test message"},
            correlation_id=correlation_id
        )
        
        # Extract correlation ID
        extracted_id = self.protocol.extract_correlation_id(message)
        assert extracted_id == correlation_id
        
        # Create response
        response = self.protocol.create_response_message(
            message,
            {"response": "Got it"}
        )
        
        # Response should have same correlation ID
        response_correlation_id = self.protocol.extract_correlation_id(response)
        assert response_correlation_id == correlation_id
    
    def test_response_message_detection(self):
        """Test response message detection."""
        # Create original message
        original = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content={"text": "Original message"}
        )
        
        # Create response
        response = self.protocol.create_response_message(
            original,
            {"text": "Response message"}
        )
        
        # Test detection
        assert not self.protocol.is_response_message(original)
        assert self.protocol.is_response_message(response)
        
        # Test response-to ID extraction
        assert self.protocol.get_response_to_id(original) is None
        assert self.protocol.get_response_to_id(response) == original.message_id
    
    def test_serialization_with_large_content(self):
        """Test serialization with large content."""
        # Create message with large content
        large_content = {"data": "x" * (1024 * 1024 + 1)}  # Exceed 1MB limit
        
        with pytest.raises(ValueError, match="Message size .* exceeds limit"):
            large_message = self.protocol.create_message(
                sender_id=self.sender_id,
                recipient_id=self.recipient_id,
                message_type=MessageType.CHAT,
                content=large_content
            )
            self.protocol.serialize_message(large_message)
    
    def test_deserialization_with_invalid_data(self):
        """Test deserialization with invalid data."""
        # Test with invalid JSON
        with pytest.raises(ValueError):
            self.protocol.deserialize_message(b"invalid json")
        
        # Test with missing required fields
        invalid_envelope = {
            "protocol_version": "1.0",
            "message": {
                "message_id": "test",
                # Missing required fields
            }
        }
        
        with pytest.raises(ValueError):
            invalid_data = json.dumps(invalid_envelope).encode('utf-8')
            self.protocol.deserialize_message(invalid_data)


class TestMessageQueue:
    """Test cases for MessageQueue."""
    
    def setup_method(self):
        """Set up test environment."""
        self.queue = MessageQueue(max_size=10)
        self.protocol = MessageProtocol()
        self.sender_id = generate_agent_id()
        self.recipient_id = generate_agent_id()
    
    def test_enqueue_and_dequeue_message(self):
        """Test basic queue operations."""
        # Create message
        message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content={"text": "Test message"}
        )
        
        # Enqueue
        success = self.queue.enqueue_message(message)
        assert success
        
        # Check stats
        stats = self.queue.get_queue_stats()
        assert stats["pending"] == 1
        assert stats["failed"] == 0
        
        # Dequeue
        entry = self.queue.dequeue_message()
        assert entry is not None
        assert entry["message"].message_id == message.message_id
        assert entry["retry_count"] == 0
        assert entry["status"] == MessageStatus.PENDING.value
        
        # Queue should be empty now
        stats = self.queue.get_queue_stats()
        assert stats["pending"] == 0
    
    def test_queue_capacity_limit(self):
        """Test queue capacity limits."""
        # Fill queue to capacity
        for i in range(10):
            message = self.protocol.create_message(
                sender_id=self.sender_id,
                recipient_id=self.recipient_id,
                message_type=MessageType.CHAT,
                content={"text": f"Message {i}"}
            )
            success = self.queue.enqueue_message(message)
            assert success
        
        # Try to add one more (should fail)
        overflow_message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content={"text": "Overflow message"}
        )
        success = self.queue.enqueue_message(overflow_message)
        assert not success
    
    def test_message_delivery_tracking(self):
        """Test message delivery status tracking."""
        # Create and enqueue message
        message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content={"text": "Test message"}
        )
        
        self.queue.enqueue_message(message)
        
        # Mark as delivered
        success = self.queue.mark_message_delivered(message.message_id)
        assert success
        
        # Should be removed from pending
        stats = self.queue.get_queue_stats()
        assert stats["pending"] == 0
    
    def test_message_failure_and_retry(self):
        """Test message failure handling and retry logic."""
        # Create and enqueue message
        message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content={"text": "Test message"}
        )
        
        self.queue.enqueue_message(message, max_retries=2)
        
        # Mark as failed
        success = self.queue.mark_message_failed(message.message_id, "Network error")
        assert success
        
        # Should be in failed queue
        stats = self.queue.get_queue_stats()
        assert stats["pending"] == 0
        assert stats["failed"] == 1
        
        # Retry message
        retry_success = self.queue.retry_message(message.message_id)
        assert retry_success
        
        # Should be back in pending queue
        stats = self.queue.get_queue_stats()
        assert stats["pending"] == 1
        assert stats["failed"] == 0
        
        # Dequeue and check retry count
        entry = self.queue.dequeue_message()
        assert entry["retry_count"] == 1
    
    def test_retry_limit_exceeded(self):
        """Test behavior when retry limit is exceeded."""
        # Create message with low retry limit
        message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content={"text": "Test message"}
        )
        
        self.queue.enqueue_message(message, max_retries=1)
        
        # Fail and retry once
        self.queue.mark_message_failed(message.message_id, "Error 1")
        self.queue.retry_message(message.message_id)
        
        # Fail again
        self.queue.mark_message_failed(message.message_id, "Error 2")
        
        # Try to retry again (should fail - limit exceeded)
        retry_success = self.queue.retry_message(message.message_id)
        assert not retry_success
        
        # Should remain in failed queue
        stats = self.queue.get_queue_stats()
        assert stats["failed"] == 1
    
    def test_queue_cleanup(self):
        """Test cleanup of old messages."""
        # Create old message (simulate by modifying timestamp)
        message = self.protocol.create_message(
            sender_id=self.sender_id,
            recipient_id=self.recipient_id,
            message_type=MessageType.CHAT,
            content={"text": "Old message"}
        )
        
        self.queue.enqueue_message(message)
        
        # Manually set old timestamp
        self.queue.pending_messages[0]["queued_at"] = datetime.now() - timedelta(hours=25)
        
        # Cleanup
        cleaned_count = self.queue.cleanup_old_messages(max_age_hours=24)
        assert cleaned_count == 1
        
        # Queue should be empty
        stats = self.queue.get_queue_stats()
        assert stats["pending"] == 0


if __name__ == "__main__":
    pytest.main([__file__])

@pytest.mark.asyncio
class TestNetworkManager:
    """Test cases for NetworkManager."""
    
    def setup_method(self):
        """Set up test environment."""
        from autonomous_ai_ecosystem.core.config import NetworkConfig
        from autonomous_ai_ecosystem.communication.network_manager import NetworkManager
        from autonomous_ai_ecosystem.utils.generators import generate_agent_id
        
        self.config = NetworkConfig()
        self.agent_id = generate_agent_id()
        self.network_manager = NetworkManager(self.agent_id, self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.network_manager.is_running:
            asyncio.create_task(self.network_manager.stop())
    
    async def test_network_manager_initialization(self):
        """Test network manager initialization."""
        assert self.network_manager.agent_id == self.agent_id
        assert self.network_manager.config == self.config
        assert not self.network_manager.is_running
        assert len(self.network_manager.connections) == 0
        assert self.network_manager.server_port > 0
    
    async def test_start_and_stop_network_manager(self):
        """Test starting and stopping network manager."""
        # Start network manager
        await self.network_manager.start()
        
        assert self.network_manager.is_running
        assert self.network_manager.server is not None
        
        # Stop network manager
        await self.network_manager.stop()
        
        assert not self.network_manager.is_running
    
    async def test_add_and_remove_peer(self):
        """Test adding and removing peers."""
        peer_id = generate_agent_id()
        
        # Add peer
        success = await self.network_manager.add_peer(peer_id, "localhost", 9000)
        assert success
        assert peer_id in self.network_manager.known_peers
        
        # Remove peer
        success = await self.network_manager.remove_peer(peer_id)
        assert success
        assert peer_id not in self.network_manager.known_peers
    
    async def test_cannot_add_self_as_peer(self):
        """Test that agent cannot add itself as peer."""
        success = await self.network_manager.add_peer(self.agent_id, "localhost", 9000)
        assert not success
    
    async def test_get_connection_status(self):
        """Test getting connection status."""
        status = self.network_manager.get_connection_status()
        assert isinstance(status, dict)
        assert len(status) == 0  # No connections initially
    
    async def test_get_network_stats(self):
        """Test getting network statistics."""
        stats = self.network_manager.get_network_stats()
        
        assert "messages_sent" in stats
        assert "messages_received" in stats
        assert "active_connections" in stats
        assert "server_port" in stats
        assert stats["server_port"] == self.network_manager.server_port
    
    async def test_message_handler_registration(self):
        """Test registering message handlers."""
        async def test_handler(message):
            pass
        
        self.network_manager.register_message_handler("test_type", test_handler)
        assert "test_type" in self.network_manager.message_handlers
        assert self.network_manager.message_handlers["test_type"] == test_handler


@pytest.mark.asyncio 
class TestMessageRouter:
    """Test cases for MessageRouter."""
    
    def setup_method(self):
        """Set up test environment."""
        from autonomous_ai_ecosystem.core.config import NetworkConfig
        from autonomous_ai_ecosystem.communication.network_manager import NetworkManager
        from autonomous_ai_ecosystem.communication.message_router import MessageRouter
        from autonomous_ai_ecosystem.utils.generators import generate_agent_id
        
        self.config = NetworkConfig()
        self.agent_id = generate_agent_id()
        self.network_manager = NetworkManager(self.agent_id, self.config)
        self.message_router = MessageRouter(self.agent_id, self.network_manager)
    
    async def test_message_router_initialization(self):
        """Test message router initialization."""
        assert self.message_router.agent_id == self.agent_id
        assert self.message_router.network_manager == self.network_manager
        assert len(self.message_router.routing_table) == 0
        assert len(self.message_router.pending_deliveries) == 0
    
    async def test_route_message_direct(self):
        """Test direct message routing."""
        from autonomous_ai_ecosystem.communication.message_router import RoutingStrategy
        
        # Create test message
        message = self.message_router.protocol.create_message(
            sender_id=self.agent_id,
            recipient_id="test_recipient",
            message_type=MessageType.CHAT,
            content={"text": "Test message"}
        )
        
        # Route message (will fail since no connection, but should not raise exception)
        await self.message_router.route_message(message, RoutingStrategy.DIRECT)
        
        # Should track the message even if delivery fails
        assert message.message_id in self.message_router.pending_deliveries
        assert self.message_router.routing_stats["messages_routed"] == 1
    
    async def test_update_topology(self):
        """Test topology updates."""
        topology = {
            "agent_1": {"agent_2", "agent_3"},
            "agent_2": {"agent_1", "agent_4"},
            "agent_3": {"agent_1"},
            "agent_4": {"agent_2"}
        }
        
        await self.message_router.update_topology(topology)
        
        assert len(self.message_router.peer_topology) == 4
        assert "agent_1" in self.message_router.peer_topology
        assert "agent_2" in self.message_router.peer_topology["agent_1"]
    
    async def test_find_route_direct(self):
        """Test finding direct routes."""
        # Mock a direct connection
        from autonomous_ai_ecosystem.communication.network_manager import PeerConnection, ConnectionStatus
        
        connection = PeerConnection(
            agent_id="test_peer",
            host="localhost",
            port=9000,
            status=ConnectionStatus.CONNECTED
        )
        self.network_manager.connections["test_peer"] = connection
        
        route = await self.message_router.find_route("test_peer")
        
        assert route is not None
        assert route.destination == "test_peer"
        assert route.next_hop is None  # Direct connection
        assert route.hop_count == 1
    
    async def test_get_routing_stats(self):
        """Test getting routing statistics."""
        stats = self.message_router.get_routing_stats()
        
        assert "messages_routed" in stats
        assert "direct_deliveries" in stats
        assert "routing_table_size" in stats
        assert "pending_deliveries" in stats
        assert stats["routing_table_size"] == 0  # Initially empty
    
    async def test_cleanup_pending_deliveries(self):
        """Test cleanup of old pending deliveries."""
        # Add a test message to pending deliveries
        message = self.message_router.protocol.create_message(
            sender_id=self.agent_id,
            recipient_id="test_recipient",
            message_type=MessageType.CHAT,
            content={"text": "Test message"}
        )
        
        # Manually set old timestamp
        from datetime import datetime, timedelta
        message.timestamp = datetime.now() - timedelta(hours=1)
        
        self.message_router.pending_deliveries[message.message_id] = message
        
        # Cleanup with 30 minute threshold
        cleaned = await self.message_router.cleanup_pending_deliveries(max_age_minutes=30)
        
        assert cleaned == 1
        assert len(self.message_router.pending_deliveries) == 0