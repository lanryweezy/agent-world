"""
Peer-to-peer networking foundation for agent communication.

This module implements TCP-based networking with connection management,
heartbeat mechanisms, and message routing for the agent ecosystem.
"""

import asyncio
import socket
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Callable, Any
from dataclasses import dataclass
from enum import Enum

from ..core.interfaces import AgentMessage, CommunicationProtocol
from ..core.logger import get_agent_logger, log_agent_event
from ..core.config import NetworkConfig
from .protocol import MessageProtocol, MessageQueue


class ConnectionStatus(Enum):
    """Connection status types."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class PeerConnection:
    """Represents a connection to another agent."""
    agent_id: str
    host: str
    port: int
    status: ConnectionStatus
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    last_heartbeat: Optional[datetime] = None
    connection_time: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3


class NetworkManager(CommunicationProtocol):
    """
    Manages peer-to-peer networking for agent communication.
    
    Each agent acts as both a server (accepting connections) and client
    (connecting to other agents) in the P2P network.
    """
    
    def __init__(self, agent_id: str, config: NetworkConfig):
        self.agent_id = agent_id
        self.config = config
        self.logger = get_agent_logger(agent_id, "network_manager")
        
        # Protocol and message handling
        self.protocol = MessageProtocol()
        self.message_queue = MessageQueue()
        
        # Network state
        self.server_port = self._calculate_agent_port()
        self.server: Optional[asyncio.Server] = None
        self.is_running = False
        
        # Connection management
        self.connections: Dict[str, PeerConnection] = {}
        self.known_peers: Dict[str, Tuple[str, int]] = {}  # agent_id -> (host, port)
        
        # Message handling
        self.message_handlers: Dict[str, Callable] = {}
        self.pending_responses: Dict[str, asyncio.Future] = {}
        
        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "connections_established": 0,
            "connection_failures": 0,
            "heartbeats_sent": 0,
            "heartbeats_received": 0
        }
        
        # Background tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        self.logger.info(f"Network manager initialized for {agent_id} on port {self.server_port}")
    
    async def start(self) -> None:
        """Start the network manager (server and client operations)."""
        try:
            self.logger.info("Starting network manager")
            
            # Start TCP server
            await self._start_server()
            
            # Start background tasks
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.is_running = True
            
            log_agent_event(
                self.agent_id,
                "network_started",
                {"port": self.server_port, "max_connections": self.config.max_connections}
            )
            
            self.logger.info(f"Network manager started on port {self.server_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start network manager: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the network manager and close all connections."""
        try:
            self.logger.info("Stopping network manager")
            self.is_running = False
            
            # Cancel background tasks
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Close all peer connections
            for connection in list(self.connections.values()):
                await self._close_connection(connection)
            
            # Stop server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            log_agent_event(
                self.agent_id,
                "network_stopped",
                {"stats": self.stats}
            )
            
            self.logger.info("Network manager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping network manager: {e}")
    
    async def add_peer(self, agent_id: str, host: str, port: int) -> bool:
        """
        Add a peer to the known peers list and attempt connection.
        
        Args:
            agent_id: ID of the peer agent
            host: Peer host address
            port: Peer port number
            
        Returns:
            True if peer added successfully, False otherwise
        """
        try:
            if agent_id == self.agent_id:
                self.logger.warning("Cannot add self as peer")
                return False
            
            self.known_peers[agent_id] = (host, port)
            
            # Attempt connection if not already connected
            if agent_id not in self.connections:
                await self._connect_to_peer(agent_id, host, port)
            
            self.logger.info(f"Added peer {agent_id} at {host}:{port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add peer {agent_id}: {e}")
            return False
    
    async def remove_peer(self, agent_id: str) -> bool:
        """
        Remove a peer and close its connection.
        
        Args:
            agent_id: ID of the peer to remove
            
        Returns:
            True if peer removed successfully, False otherwise
        """
        try:
            # Close connection if exists
            if agent_id in self.connections:
                await self._close_connection(self.connections[agent_id])
            
            # Remove from known peers
            if agent_id in self.known_peers:
                del self.known_peers[agent_id]
            
            self.logger.info(f"Removed peer {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove peer {agent_id}: {e}")
            return False
    
    async def send_message(self, message: AgentMessage) -> bool:
        """
        Send a message to another agent.
        
        Args:
            message: AgentMessage to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            recipient_id = message.recipient_id
            
            # Handle broadcast messages
            if recipient_id == "BROADCAST":
                return await self._broadcast_message(message)
            
            # Check if we have a connection to the recipient
            if recipient_id not in self.connections:
                # Try to establish connection if we know the peer
                if recipient_id in self.known_peers:
                    host, port = self.known_peers[recipient_id]
                    await self._connect_to_peer(recipient_id, host, port)
                else:
                    self.logger.warning(f"Unknown peer {recipient_id}")
                    return False
            
            connection = self.connections.get(recipient_id)
            if not connection or connection.status != ConnectionStatus.CONNECTED:
                # Queue message for later delivery
                self.message_queue.enqueue_message(message)
                self.logger.debug(f"Queued message {message.message_id} for {recipient_id}")
                return True
            
            # Send message
            success = await self._send_message_to_connection(message, connection)
            
            if success:
                self.stats["messages_sent"] += 1
                
                log_agent_event(
                    self.agent_id,
                    "message_sent",
                    {
                        "message_id": message.message_id,
                        "recipient": recipient_id,
                        "type": message.message_type.value,
                        "priority": message.priority
                    }
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send message {message.message_id}: {e}")
            return False
    
    async def receive_message(self) -> Optional[AgentMessage]:
        """
        Receive a message from the network (non-blocking).
        
        Returns:
            AgentMessage if available, None otherwise
        """
        # This is handled by the connection handlers
        # Messages are processed as they arrive
        return None
    
    async def broadcast_status(self, status_data: Dict[str, Any]) -> None:
        """
        Broadcast status update to all connected peers.
        
        Args:
            status_data: Status information to broadcast
        """
        try:
            # Create broadcast message
            broadcast_message = self.protocol.create_broadcast_message(
                sender_id=self.agent_id,
                message_type=MessageType.STATUS_UPDATE,
                content=status_data,
                priority=5
            )
            
            # Send to all connected peers
            await self.send_message(broadcast_message)
            
            self.logger.debug("Broadcasted status update")
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast status: {e}")
    
    def register_message_handler(self, message_type: str, handler: Callable) -> None:
        """
        Register a handler for specific message types.
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        """
        self.message_handlers[message_type] = handler
        self.logger.debug(f"Registered handler for {message_type}")
    
    def get_connection_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all connections.
        
        Returns:
            Dictionary with connection status information
        """
        status = {}
        
        for agent_id, connection in self.connections.items():
            status[agent_id] = {
                "status": connection.status.value,
                "host": connection.host,
                "port": connection.port,
                "connected_at": connection.connection_time.isoformat() if connection.connection_time else None,
                "last_heartbeat": connection.last_heartbeat.isoformat() if connection.last_heartbeat else None,
                "retry_count": connection.retry_count
            }
        
        return status
    
    def get_network_stats(self) -> Dict[str, Any]:
        """
        Get network statistics.
        
        Returns:
            Dictionary with network statistics
        """
        return {
            **self.stats,
            "active_connections": len([c for c in self.connections.values() if c.status == ConnectionStatus.CONNECTED]),
            "total_peers": len(self.known_peers),
            "server_port": self.server_port,
            "queue_stats": self.message_queue.get_queue_stats()
        }
    
    # Private methods
    
    def _calculate_agent_port(self) -> int:
        """Calculate unique port for this agent."""
        # Simple hash-based port assignment
        agent_hash = hash(self.agent_id) % 1000
        return self.config.base_port + agent_hash
    
    async def _start_server(self) -> None:
        """Start the TCP server for incoming connections."""
        try:
            self.server = await asyncio.start_server(
                self._handle_client_connection,
                '0.0.0.0',
                self.server_port,
                limit=self.config.buffer_size
            )
            
            self.logger.info(f"Server started on port {self.server_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            raise
    
    async def _handle_client_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle incoming client connection."""
        client_addr = writer.get_extra_info('peername')
        self.logger.debug(f"New client connection from {client_addr}")
        
        try:
            # Read handshake message to identify the peer
            handshake_data = await asyncio.wait_for(
                reader.read(self.config.buffer_size),
                timeout=self.config.message_timeout
            )
            
            if not handshake_data:
                self.logger.warning("Empty handshake from client")
                writer.close()
                await writer.wait_closed()
                return
            
            # Parse handshake
            handshake = json.loads(handshake_data.decode('utf-8'))
            peer_agent_id = handshake.get('agent_id')
            
            if not peer_agent_id:
                self.logger.warning("Invalid handshake - missing agent_id")
                writer.close()
                await writer.wait_closed()
                return
            
            # Create or update connection
            if peer_agent_id in self.connections:
                # Update existing connection
                connection = self.connections[peer_agent_id]
                connection.reader = reader
                connection.writer = writer
                connection.status = ConnectionStatus.CONNECTED
                connection.connection_time = datetime.now()
                connection.retry_count = 0
            else:
                # Create new connection
                connection = PeerConnection(
                    agent_id=peer_agent_id,
                    host=client_addr[0],
                    port=client_addr[1],
                    status=ConnectionStatus.CONNECTED,
                    reader=reader,
                    writer=writer,
                    connection_time=datetime.now()
                )
                self.connections[peer_agent_id] = connection
            
            # Send handshake response
            response = {
                'agent_id': self.agent_id,
                'status': 'connected',
                'timestamp': datetime.now().isoformat()
            }
            writer.write(json.dumps(response).encode('utf-8'))
            await writer.drain()
            
            self.stats["connections_established"] += 1
            
            log_agent_event(
                self.agent_id,
                "peer_connected",
                {"peer_id": peer_agent_id, "address": f"{client_addr[0]}:{client_addr[1]}"}
            )
            
            # Handle messages from this connection
            await self._handle_connection_messages(connection)
            
        except Exception as e:
            self.logger.error(f"Error handling client connection: {e}")
            writer.close()
            await writer.wait_closed()
    
    async def _connect_to_peer(self, agent_id: str, host: str, port: int) -> bool:
        """Connect to a peer agent."""
        try:
            self.logger.debug(f"Connecting to peer {agent_id} at {host}:{port}")
            
            # Create connection entry
            connection = PeerConnection(
                agent_id=agent_id,
                host=host,
                port=port,
                status=ConnectionStatus.CONNECTING
            )
            self.connections[agent_id] = connection
            
            # Establish TCP connection
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=self.config.message_timeout
                )
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                self.logger.warning(f"Failed to connect to {agent_id}: {e}")
                connection.status = ConnectionStatus.FAILED
                connection.retry_count += 1
                self.stats["connection_failures"] += 1
                return False
            
            # Send handshake
            handshake = {
                'agent_id': self.agent_id,
                'timestamp': datetime.now().isoformat()
            }
            writer.write(json.dumps(handshake).encode('utf-8'))
            await writer.drain()
            
            # Wait for handshake response
            response_data = await asyncio.wait_for(
                reader.read(self.config.buffer_size),
                timeout=self.config.message_timeout
            )
            
            if not response_data:
                raise ConnectionError("No handshake response")
            
            response = json.loads(response_data.decode('utf-8'))
            if response.get('status') != 'connected':
                raise ConnectionError(f"Handshake failed: {response}")
            
            # Update connection
            connection.reader = reader
            connection.writer = writer
            connection.status = ConnectionStatus.CONNECTED
            connection.connection_time = datetime.now()
            connection.retry_count = 0
            
            self.stats["connections_established"] += 1
            
            log_agent_event(
                self.agent_id,
                "peer_connected",
                {"peer_id": agent_id, "address": f"{host}:{port}"}
            )
            
            # Start handling messages from this connection
            asyncio.create_task(self._handle_connection_messages(connection))
            
            self.logger.info(f"Connected to peer {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to peer {agent_id}: {e}")
            if agent_id in self.connections:
                self.connections[agent_id].status = ConnectionStatus.FAILED
                self.connections[agent_id].retry_count += 1
            self.stats["connection_failures"] += 1
            return False
    
    async def _handle_connection_messages(self, connection: PeerConnection) -> None:
        """Handle messages from a specific connection."""
        try:
            while connection.status == ConnectionStatus.CONNECTED and self.is_running:
                try:
                    # Read message data
                    data = await asyncio.wait_for(
                        connection.reader.read(self.config.buffer_size),
                        timeout=self.config.heartbeat_interval
                    )
                    
                    if not data:
                        # Connection closed by peer
                        break
                    
                    # Deserialize message
                    message = self.protocol.deserialize_message(data)
                    
                    # Update connection heartbeat
                    connection.last_heartbeat = datetime.now()
                    
                    # Process message
                    await self._process_received_message(message, connection)
                    
                    self.stats["messages_received"] += 1
                    
                except asyncio.TimeoutError:
                    # Check if connection is still alive
                    if connection.last_heartbeat:
                        time_since_heartbeat = datetime.now() - connection.last_heartbeat
                        if time_since_heartbeat.total_seconds() > self.config.heartbeat_interval * 2:
                            self.logger.warning(f"Connection to {connection.agent_id} timed out")
                            break
                    continue
                    
                except Exception as e:
                    self.logger.error(f"Error processing message from {connection.agent_id}: {e}")
                    break
            
        except Exception as e:
            self.logger.error(f"Error in connection handler for {connection.agent_id}: {e}")
        finally:
            await self._close_connection(connection)
    
    async def _process_received_message(self, message: AgentMessage, connection: PeerConnection) -> None:
        """Process a received message."""
        try:
            log_agent_event(
                self.agent_id,
                "message_received",
                {
                    "message_id": message.message_id,
                    "sender": message.sender_id,
                    "type": message.message_type.value,
                    "priority": message.priority
                }
            )
            
            # Check if this is a response to a pending request
            if self.protocol.is_response_message(message):
                response_to_id = self.protocol.get_response_to_id(message)
                if response_to_id in self.pending_responses:
                    future = self.pending_responses.pop(response_to_id)
                    if not future.done():
                        future.set_result(message)
                    return
            
            # Route to appropriate handler
            message_type = message.message_type.value
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                await handler(message)
            else:
                self.logger.debug(f"No handler for message type {message_type}")
            
            # Send acknowledgment if required
            if message.requires_response:
                ack_response = self.protocol.create_response_message(
                    message,
                    {"acknowledged": True},
                    success=True
                )
                await self._send_message_to_connection(ack_response, connection)
            
        except Exception as e:
            self.logger.error(f"Error processing received message: {e}")
    
    async def _send_message_to_connection(self, message: AgentMessage, connection: PeerConnection) -> bool:
        """Send a message to a specific connection."""
        try:
            if connection.status != ConnectionStatus.CONNECTED or not connection.writer:
                return False
            
            # Serialize message
            data = self.protocol.serialize_message(message)
            
            # Send data
            connection.writer.write(data)
            await connection.writer.drain()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message to {connection.agent_id}: {e}")
            return False
    
    async def _broadcast_message(self, message: AgentMessage) -> bool:
        """Broadcast a message to all connected peers."""
        try:
            success_count = 0
            
            for connection in self.connections.values():
                if connection.status == ConnectionStatus.CONNECTED:
                    if await self._send_message_to_connection(message, connection):
                        success_count += 1
            
            self.logger.debug(f"Broadcasted message to {success_count} peers")
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast message: {e}")
            return False
    
    async def _close_connection(self, connection: PeerConnection) -> None:
        """Close a peer connection."""
        try:
            if connection.writer:
                connection.writer.close()
                await connection.writer.wait_closed()
            
            connection.status = ConnectionStatus.DISCONNECTED
            connection.reader = None
            connection.writer = None
            
            # Remove from connections if failed permanently
            if connection.retry_count >= connection.max_retries:
                if connection.agent_id in self.connections:
                    del self.connections[connection.agent_id]
            
            log_agent_event(
                self.agent_id,
                "peer_disconnected",
                {"peer_id": connection.agent_id, "retry_count": connection.retry_count}
            )
            
            self.logger.debug(f"Closed connection to {connection.agent_id}")
            
        except Exception as e:
            self.logger.error(f"Error closing connection to {connection.agent_id}: {e}")
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to maintain connections."""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                
                for connection in list(self.connections.values()):
                    if connection.status == ConnectionStatus.CONNECTED:
                        # Send heartbeat
                        heartbeat_message = self.protocol.create_message(
                            sender_id=self.agent_id,
                            recipient_id=connection.agent_id,
                            message_type=MessageType.STATUS_UPDATE,
                            content={"heartbeat": True, "timestamp": datetime.now().isoformat()},
                            priority=1
                        )
                        
                        if await self._send_message_to_connection(heartbeat_message, connection):
                            self.stats["heartbeats_sent"] += 1
                        else:
                            # Connection failed, mark for reconnection
                            connection.status = ConnectionStatus.FAILED
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of failed connections and old messages."""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Cleanup old messages
                self.message_queue.cleanup_old_messages()
                
                # Retry failed connections
                for agent_id, connection in list(self.connections.items()):
                    if (connection.status == ConnectionStatus.FAILED and 
                        connection.retry_count < connection.max_retries):
                        
                        # Wait before retry
                        if connection.connection_time:
                            time_since_failure = datetime.now() - connection.connection_time
                            if time_since_failure.total_seconds() > 60:  # Wait 1 minute
                                await self._connect_to_peer(agent_id, connection.host, connection.port)
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")