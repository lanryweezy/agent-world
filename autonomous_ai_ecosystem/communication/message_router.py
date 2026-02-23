"""
Message routing and delivery system for agent communication.

This module handles intelligent message routing, delivery confirmation,
and coordination between multiple network managers.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

from ..core.interfaces import AgentMessage, MessageType
from ..core.logger import get_agent_logger, log_agent_event
from .protocol import MessageProtocol
from .network_manager import NetworkManager


class RoutingStrategy(Enum):
    """Message routing strategies."""
    DIRECT = "direct"  # Direct connection to recipient
    BROADCAST = "broadcast"  # Broadcast to all peers
    RELAY = "relay"  # Route through intermediate peers
    MULTICAST = "multicast"  # Send to multiple specific recipients


@dataclass
class RouteInfo:
    """Information about a message route."""
    destination: str
    next_hop: Optional[str]
    hop_count: int
    last_updated: datetime
    reliability_score: float


class MessageRouter:
    """
    Intelligent message router that handles delivery, routing, and coordination.
    """
    
    def __init__(self, agent_id: str, network_manager: NetworkManager):
        self.agent_id = agent_id
        self.network_manager = network_manager
        self.protocol = MessageProtocol()
        self.logger = get_agent_logger(agent_id, "message_router")
        
        # Routing table and topology
        self.routing_table: Dict[str, RouteInfo] = {}
        self.peer_topology: Dict[str, Set[str]] = {}  # agent_id -> set of connected peers
        
        # Message tracking
        self.pending_deliveries: Dict[str, AgentMessage] = {}
        self.delivery_confirmations: Dict[str, datetime] = {}
        self.message_history: List[Dict[str, Any]] = []
        
        # Routing statistics
        self.routing_stats = {
            "messages_routed": 0,
            "direct_deliveries": 0,
            "relay_deliveries": 0,
            "broadcast_deliveries": 0,
            "failed_deliveries": 0,
            "average_hop_count": 0.0
        }
        
        # Register message handlers
        self._register_handlers()
        
        self.logger.info(f"Message router initialized for {agent_id}")
    
    async def route_message(
        self, 
        message: AgentMessage, 
        strategy: RoutingStrategy = RoutingStrategy.DIRECT
    ) -> bool:
        """
        Route a message using the specified strategy.
        
        Args:
            message: AgentMessage to route
            strategy: Routing strategy to use
            
        Returns:
            True if routing initiated successfully, False otherwise
        """
        try:
            self.routing_stats["messages_routed"] += 1
            
            # Track message for delivery confirmation
            self.pending_deliveries[message.message_id] = message
            
            # Add routing metadata
            message.content["_routing_strategy"] = strategy.value
            message.content["_route_timestamp"] = datetime.now().isoformat()
            message.content["_hop_count"] = message.content.get("_hop_count", 0)
            
            # Route based on strategy
            if strategy == RoutingStrategy.DIRECT:
                success = await self._route_direct(message)
            elif strategy == RoutingStrategy.BROADCAST:
                success = await self._route_broadcast(message)
            elif strategy == RoutingStrategy.RELAY:
                success = await self._route_relay(message)
            elif strategy == RoutingStrategy.MULTICAST:
                success = await self._route_multicast(message)
            else:
                self.logger.error(f"Unknown routing strategy: {strategy}")
                return False
            
            # Log routing attempt
            log_agent_event(
                self.agent_id,
                "message_routed",
                {
                    "message_id": message.message_id,
                    "strategy": strategy.value,
                    "recipient": message.recipient_id,
                    "success": success
                }
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to route message {message.message_id}: {e}")
            self.routing_stats["failed_deliveries"] += 1
            return False
    
    async def update_topology(self, peer_connections: Dict[str, Set[str]]) -> None:
        """
        Update the network topology information.
        
        Args:
            peer_connections: Dictionary mapping agent_id to set of connected peers
        """
        try:
            self.peer_topology.update(peer_connections)
            
            # Update routing table based on new topology
            await self._update_routing_table()
            
            self.logger.debug(f"Updated topology with {len(peer_connections)} peer updates")
            
        except Exception as e:
            self.logger.error(f"Failed to update topology: {e}")
    
    async def find_route(self, destination: str) -> Optional[RouteInfo]:
        """
        Find the best route to a destination.
        
        Args:
            destination: Target agent ID
            
        Returns:
            RouteInfo if route found, None otherwise
        """
        try:
            # Check direct connection first
            if destination in self.network_manager.connections:
                connection = self.network_manager.connections[destination]
                if connection.status.value == "connected":
                    return RouteInfo(
                        destination=destination,
                        next_hop=None,  # Direct connection
                        hop_count=1,
                        last_updated=datetime.now(),
                        reliability_score=1.0
                    )
            
            # Check routing table
            if destination in self.routing_table:
                route = self.routing_table[destination]
                # Verify route is still valid (not too old)
                if datetime.now() - route.last_updated < timedelta(minutes=5):
                    return route
            
            # Try to discover route through topology
            route = await self._discover_route(destination)
            if route:
                self.routing_table[destination] = route
                return route
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to find route to {destination}: {e}")
            return None
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics.
        
        Returns:
            Dictionary with routing statistics
        """
        return {
            **self.routing_stats,
            "routing_table_size": len(self.routing_table),
            "pending_deliveries": len(self.pending_deliveries),
            "known_topology_size": len(self.peer_topology)
        }
    
    def get_message_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent message routing history.
        
        Args:
            limit: Maximum number of history entries
            
        Returns:
            List of message history entries
        """
        return self.message_history[-limit:]
    
    # Private routing methods
    
    async def _route_direct(self, message: AgentMessage) -> bool:
        """Route message directly to recipient."""
        try:
            success = await self.network_manager.send_message(message)
            
            if success:
                self.routing_stats["direct_deliveries"] += 1
            else:
                self.routing_stats["failed_deliveries"] += 1
            
            return success
            
        except Exception as e:
            self.logger.error(f"Direct routing failed: {e}")
            return False
    
    async def _route_broadcast(self, message: AgentMessage) -> bool:
        """Broadcast message to all connected peers."""
        try:
            # Create broadcast message
            broadcast_msg = self.protocol.create_broadcast_message(
                sender_id=self.agent_id,
                message_type=message.message_type,
                content=message.content,
                priority=message.priority
            )
            
            success = await self.network_manager.send_message(broadcast_msg)
            
            if success:
                self.routing_stats["broadcast_deliveries"] += 1
            else:
                self.routing_stats["failed_deliveries"] += 1
            
            return success
            
        except Exception as e:
            self.logger.error(f"Broadcast routing failed: {e}")
            return False
    
    async def _route_relay(self, message: AgentMessage) -> bool:
        """Route message through intermediate peers."""
        try:
            route = await self.find_route(message.recipient_id)
            
            if not route or not route.next_hop:
                # No relay route available, try direct
                return await self._route_direct(message)
            
            # Increment hop count
            message.content["_hop_count"] = message.content.get("_hop_count", 0) + 1
            
            # Check hop limit
            if message.content["_hop_count"] > 5:  # Max 5 hops
                self.logger.warning(f"Message {message.message_id} exceeded hop limit")
                return False
            
            # Create relay message
            relay_message = self.protocol.create_message(
                sender_id=self.agent_id,
                recipient_id=route.next_hop,
                message_type=MessageType.CHAT,  # Relay wrapper
                content={
                    "_relay": True,
                    "_original_message": message.content,
                    "_final_destination": message.recipient_id,
                    "_hop_count": message.content["_hop_count"]
                },
                priority=message.priority
            )
            
            success = await self.network_manager.send_message(relay_message)
            
            if success:
                self.routing_stats["relay_deliveries"] += 1
                self.routing_stats["average_hop_count"] = (
                    (self.routing_stats["average_hop_count"] * (self.routing_stats["relay_deliveries"] - 1) + 
                     message.content["_hop_count"]) / self.routing_stats["relay_deliveries"]
                )
            else:
                self.routing_stats["failed_deliveries"] += 1
            
            return success
            
        except Exception as e:
            self.logger.error(f"Relay routing failed: {e}")
            return False
    
    async def _route_multicast(self, message: AgentMessage) -> bool:
        """Route message to multiple recipients."""
        try:
            # Extract recipient list from message content
            recipients = message.content.get("_multicast_recipients", [])
            
            if not recipients:
                self.logger.warning("Multicast message without recipients")
                return False
            
            success_count = 0
            
            for recipient_id in recipients:
                # Create individual message for each recipient
                individual_message = self.protocol.create_message(
                    sender_id=message.sender_id,
                    recipient_id=recipient_id,
                    message_type=message.message_type,
                    content=message.content,
                    priority=message.priority,
                    requires_response=message.requires_response
                )
                
                if await self._route_direct(individual_message):
                    success_count += 1
            
            success = success_count > 0
            
            if success:
                self.routing_stats["broadcast_deliveries"] += 1
            else:
                self.routing_stats["failed_deliveries"] += 1
            
            return success
            
        except Exception as e:
            self.logger.error(f"Multicast routing failed: {e}")
            return False
    
    async def _discover_route(self, destination: str) -> Optional[RouteInfo]:
        """Discover route to destination using topology information."""
        try:
            # Simple breadth-first search through topology
            visited = set()
            queue = [(self.agent_id, 0, None)]  # (current_node, hop_count, next_hop)
            
            while queue:
                current, hops, next_hop = queue.pop(0)
                
                if current in visited:
                    continue
                
                visited.add(current)
                
                # Check if we found the destination
                if current == destination:
                    return RouteInfo(
                        destination=destination,
                        next_hop=next_hop,
                        hop_count=hops,
                        last_updated=datetime.now(),
                        reliability_score=max(0.1, 1.0 - (hops * 0.2))  # Decrease reliability with hops
                    )
                
                # Add neighbors to queue
                if current in self.peer_topology:
                    for neighbor in self.peer_topology[current]:
                        if neighbor not in visited:
                            # For first hop, next_hop is the neighbor
                            # For subsequent hops, keep the original next_hop
                            hop_next = neighbor if next_hop is None else next_hop
                            queue.append((neighbor, hops + 1, hop_next))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Route discovery failed: {e}")
            return None
    
    async def _update_routing_table(self) -> None:
        """Update routing table based on current topology."""
        try:
            # Remove stale routes
            current_time = datetime.now()
            stale_routes = [
                dest for dest, route in self.routing_table.items()
                if current_time - route.last_updated > timedelta(minutes=10)
            ]
            
            for dest in stale_routes:
                del self.routing_table[dest]
            
            self.logger.debug(f"Updated routing table, removed {len(stale_routes)} stale routes")
            
        except Exception as e:
            self.logger.error(f"Failed to update routing table: {e}")
    
    def _register_handlers(self) -> None:
        """Register message handlers for routing-specific messages."""
        
        async def handle_relay_message(message: AgentMessage) -> None:
            """Handle relay messages."""
            try:
                if not message.content.get("_relay"):
                    return
                
                final_destination = message.content.get("_final_destination")
                original_content = message.content.get("_original_message", {})
                
                if not final_destination:
                    self.logger.warning("Relay message without final destination")
                    return
                
                # Check if we are the final destination
                if final_destination == self.agent_id:
                    # Deliver the original message
                    original_message = self.protocol.create_message(
                        sender_id=message.sender_id,
                        recipient_id=self.agent_id,
                        message_type=MessageType.CHAT,
                        content=original_content
                    )
                    
                    # Process as received message
                    await self._handle_delivered_message(original_message)
                else:
                    # Continue relaying
                    relay_message = self.protocol.create_message(
                        sender_id=message.sender_id,
                        recipient_id=final_destination,
                        message_type=MessageType.CHAT,
                        content=original_content
                    )
                    
                    await self.route_message(relay_message, RoutingStrategy.RELAY)
                
            except Exception as e:
                self.logger.error(f"Error handling relay message: {e}")
        
        async def handle_delivery_confirmation(message: AgentMessage) -> None:
            """Handle delivery confirmation messages."""
            try:
                if not message.content.get("_delivery_confirmation"):
                    return
                
                original_message_id = message.content.get("_original_message_id")
                if original_message_id in self.pending_deliveries:
                    # Mark as delivered
                    self.delivery_confirmations[original_message_id] = datetime.now()
                    del self.pending_deliveries[original_message_id]
                    
                    log_agent_event(
                        self.agent_id,
                        "delivery_confirmed",
                        {"message_id": original_message_id}
                    )
                
            except Exception as e:
                self.logger.error(f"Error handling delivery confirmation: {e}")
        
        # Register handlers with network manager
        self.network_manager.register_message_handler("chat", handle_relay_message)
        self.network_manager.register_message_handler("status_update", handle_delivery_confirmation)
    
    async def _handle_delivered_message(self, message: AgentMessage) -> None:
        """Handle a message that was successfully delivered to this agent."""
        try:
            # Send delivery confirmation if requested
            if message.content.get("_request_confirmation"):
                confirmation = self.protocol.create_message(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    message_type=MessageType.STATUS_UPDATE,
                    content={
                        "_delivery_confirmation": True,
                        "_original_message_id": message.message_id,
                        "_delivered_at": datetime.now().isoformat()
                    }
                )
                
                await self.network_manager.send_message(confirmation)
            
            # Add to message history
            self.message_history.append({
                "message_id": message.message_id,
                "sender": message.sender_id,
                "type": message.message_type.value,
                "delivered_at": datetime.now().isoformat(),
                "hop_count": message.content.get("_hop_count", 1)
            })
            
            # Keep history size manageable
            if len(self.message_history) > 1000:
                self.message_history = self.message_history[-500:]
            
        except Exception as e:
            self.logger.error(f"Error handling delivered message: {e}")
    
    async def cleanup_pending_deliveries(self, max_age_minutes: int = 30) -> int:
        """
        Clean up old pending deliveries.
        
        Args:
            max_age_minutes: Maximum age for pending deliveries
            
        Returns:
            Number of deliveries cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
            
            expired_deliveries = []
            for message_id, message in self.pending_deliveries.items():
                if message.timestamp < cutoff_time:
                    expired_deliveries.append(message_id)
            
            for message_id in expired_deliveries:
                del self.pending_deliveries[message_id]
                self.routing_stats["failed_deliveries"] += 1
            
            if expired_deliveries:
                self.logger.info(f"Cleaned up {len(expired_deliveries)} expired pending deliveries")
            
            return len(expired_deliveries)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up pending deliveries: {e}")
            return 0