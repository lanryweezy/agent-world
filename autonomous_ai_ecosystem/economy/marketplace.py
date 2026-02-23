"""
Service marketplace and trading system for the autonomous AI ecosystem.

This module implements a marketplace where agents can advertise services,
negotiate prices, and engage in automated trading.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .currency import VirtualCurrency, CurrencyType


class ServiceCategory(Enum):
    """Categories of services in the marketplace."""
    COMPUTATIONAL = "computational"
    RESEARCH = "research"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    COMMUNICATION = "communication"
    LEARNING = "learning"
    PROBLEM_SOLVING = "problem_solving"
    COLLABORATION = "collaboration"
    MONITORING = "monitoring"
    AUTOMATION = "automation"


class ServiceStatus(Enum):
    """Status of services in the marketplace."""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    SUSPENDED = "suspended"
    MAINTENANCE = "maintenance"


class ContractStatus(Enum):
    """Status of service contracts."""
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    REFUNDED = "refunded"


class QualityRating(Enum):
    """Quality ratings for services."""
    POOR = 1
    FAIR = 2
    GOOD = 3
    EXCELLENT = 4
    OUTSTANDING = 5


@dataclass
class ServiceCapability:
    """Represents a capability or skill that an agent can provide."""
    capability_id: str
    name: str
    description: str
    category: ServiceCategory
    skill_level: float  # 0.0 to 1.0
    experience_points: int = 0
    success_rate: float = 1.0
    average_rating: float = 5.0
    total_jobs: int = 0
    
    def get_expertise_level(self) -> str:
        """Get human-readable expertise level."""
        if self.skill_level >= 0.9:
            return "Expert"
        elif self.skill_level >= 0.7:
            return "Advanced"
        elif self.skill_level >= 0.5:
            return "Intermediate"
        elif self.skill_level >= 0.3:
            return "Beginner"
        else:
            return "Novice"


@dataclass
class ServiceListing:
    """Represents a service listing in the marketplace."""
    listing_id: str
    provider_id: str
    service_name: str
    description: str
    category: ServiceCategory
    
    # Pricing
    base_price: float
    currency_type: CurrencyType
    pricing_model: str = "fixed"  # fixed, hourly, per_task, negotiable
    
    # Service details
    capabilities: List[str] = field(default_factory=list)  # capability_ids
    requirements: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: Optional[float] = None  # hours
    max_concurrent_jobs: int = 1
    
    # Availability
    status: ServiceStatus = ServiceStatus.AVAILABLE
    available_hours: List[Tuple[int, int]] = field(default_factory=lambda: [(0, 24)])  # (start_hour, end_hour)
    timezone: str = "UTC"
    
    # Quality metrics
    rating: float = 5.0
    total_reviews: int = 0
    success_rate: float = 1.0
    response_time_hours: float = 1.0
    
    # Marketplace data
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    featured: bool = False
    tags: List[str] = field(default_factory=list)
    
    # Current workload
    active_contracts: Set[str] = field(default_factory=set)
    pending_requests: int = 0
    
    def is_available(self) -> bool:
        """Check if service is currently available."""
        if self.status != ServiceStatus.AVAILABLE:
            return False
        
        if len(self.active_contracts) >= self.max_concurrent_jobs:
            return False
        
        # Check time availability (simplified)
        current_hour = datetime.now().hour
        for start_hour, end_hour in self.available_hours:
            if start_hour <= current_hour < end_hour:
                return True
        
        return False
    
    def calculate_dynamic_price(self, demand_factor: float = 1.0) -> float:
        """Calculate dynamic pricing based on demand and availability."""
        base = self.base_price
        
        # Demand adjustment
        demand_multiplier = 1.0 + (demand_factor - 1.0) * 0.5
        
        # Quality premium
        quality_multiplier = 1.0 + (self.rating - 3.0) * 0.1
        
        # Availability discount/premium
        availability_multiplier = 1.0
        if len(self.active_contracts) == 0:
            availability_multiplier = 0.9  # Discount for idle service
        elif len(self.active_contracts) >= self.max_concurrent_jobs * 0.8:
            availability_multiplier = 1.2  # Premium for high demand
        
        return base * demand_multiplier * quality_multiplier * availability_multiplier


@dataclass
class ServiceContract:
    """Represents a contract for service provision."""
    contract_id: str
    listing_id: str
    provider_id: str
    client_id: str
    
    # Contract terms
    service_description: str
    agreed_price: float
    currency_type: CurrencyType
    estimated_duration: float
    deadline: Optional[datetime] = None
    
    # Contract status
    status: ContractStatus = ContractStatus.PROPOSED
    created_at: datetime = field(default_factory=datetime.now)
    accepted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Payment terms
    payment_schedule: str = "completion"  # upfront, milestone, completion
    escrow_amount: float = 0.0
    payment_transaction_id: Optional[str] = None
    
    # Work tracking
    progress_percentage: float = 0.0
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    deliverables: List[Dict[str, Any]] = field(default_factory=list)
    
    # Quality and feedback
    client_rating: Optional[QualityRating] = None
    provider_rating: Optional[QualityRating] = None
    client_feedback: str = ""
    provider_feedback: str = ""
    
    # Dispute handling
    dispute_reason: Optional[str] = None
    dispute_resolution: Optional[str] = None
    mediator_id: Optional[str] = None
    
    # Contract metadata
    requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_overdue(self) -> bool:
        """Check if contract is overdue."""
        if not self.deadline or self.status in [ContractStatus.COMPLETED, ContractStatus.CANCELLED]:
            return False
        return datetime.now() > self.deadline
    
    def get_duration_so_far(self) -> float:
        """Get duration of work so far in hours."""
        if not self.started_at:
            return 0.0
        
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds() / 3600.0


@dataclass
class MarketplaceTransaction:
    """Represents a marketplace transaction (different from currency transaction)."""
    transaction_id: str
    contract_id: str
    transaction_type: str  # service_payment, escrow_deposit, refund, etc.
    amount: float
    currency_type: CurrencyType
    
    # Parties
    payer_id: str
    payee_id: str
    
    # Status and timing
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    
    # References
    currency_transaction_id: Optional[str] = None
    escrow_id: Optional[str] = None


@dataclass
class ServiceReview:
    """Represents a review of a service."""
    review_id: str
    contract_id: str
    listing_id: str
    reviewer_id: str
    provider_id: str
    
    # Review content
    rating: QualityRating
    title: str
    comment: str
    
    # Review metadata
    created_at: datetime = field(default_factory=datetime.now)
    verified: bool = False
    helpful_votes: int = 0


class ServiceMarketplace(AgentModule):
    """
    Service marketplace system for autonomous AI agents.
    
    Provides a platform for agents to advertise services, find providers,
    negotiate contracts, and conduct automated trading.
    """
    
    def __init__(self, agent_id: str, currency_system: VirtualCurrency):
        super().__init__(agent_id)
        self.currency_system = currency_system
        self.logger = get_agent_logger(agent_id, "marketplace")
        
        # Core data structures
        self.service_listings: Dict[str, ServiceListing] = {}
        self.service_contracts: Dict[str, ServiceContract] = {}
        self.agent_capabilities: Dict[str, List[ServiceCapability]] = {}  # agent_id -> capabilities
        self.marketplace_transactions: Dict[str, MarketplaceTransaction] = {}
        self.service_reviews: Dict[str, ServiceReview] = {}
        
        # Marketplace configuration
        self.config = {
            "marketplace_fee_rate": 0.05,  # 5% marketplace fee
            "escrow_fee_rate": 0.02,  # 2% escrow fee
            "max_negotiation_rounds": 5,
            "contract_timeout_hours": 168.0,  # 1 week
            "review_period_hours": 72.0,  # 3 days to leave review
            "dispute_resolution_hours": 48.0,
            "featured_listing_cost": 10.0,
            "max_listings_per_agent": 20,
            "min_service_price": 1.0,
            "max_service_price": 10000.0
        }
        
        # Market data
        self.market_stats = {
            "total_listings": 0,
            "active_listings": 0,
            "total_contracts": 0,
            "completed_contracts": 0,
            "total_volume": 0.0,
            "average_rating": 5.0,
            "dispute_rate": 0.0,
            "category_demand": {cat.value: 0 for cat in ServiceCategory}
        }
        
        # Counters
        self.listing_counter = 0
        self.contract_counter = 0
        self.transaction_counter = 0
        self.review_counter = 0
        
        # Background tasks
        self.negotiation_queue = asyncio.Queue()
        self.contract_monitoring_queue = asyncio.Queue()
        
        self.logger.info("Service marketplace initialized")
    
    async def initialize(self) -> None:
        """Initialize the marketplace system."""
        try:
            # Start background processes
            asyncio.create_task(self._negotiation_processor())
            asyncio.create_task(self._contract_monitor())
            asyncio.create_task(self._market_analyzer())
            
            self.logger.info("Marketplace system initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize marketplace: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the marketplace system."""
        try:
            # Complete pending negotiations
            while not self.negotiation_queue.empty():
                await asyncio.sleep(0.1)
            
            # Save marketplace state
            await self._save_marketplace_state()
            
            self.logger.info("Marketplace system shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during marketplace shutdown: {e}")
    
    async def register_service_capability(
        self,
        agent_id: str,
        name: str,
        description: str,
        category: ServiceCategory,
        skill_level: float
    ) -> Dict[str, Any]:
        """Register a service capability for an agent."""
        try:
            capability_id = f"cap_{agent_id}_{len(self.agent_capabilities.get(agent_id, []))}"
            
            capability = ServiceCapability(
                capability_id=capability_id,
                name=name,
                description=description,
                category=category,
                skill_level=max(0.0, min(1.0, skill_level))
            )
            
            if agent_id not in self.agent_capabilities:
                self.agent_capabilities[agent_id] = []
            
            self.agent_capabilities[agent_id].append(capability)
            
            log_agent_event(
                self.agent_id,
                "capability_registered",
                {
                    "agent_id": agent_id,
                    "capability_id": capability_id,
                    "name": name,
                    "category": category.value,
                    "skill_level": skill_level
                }
            )
            
            result = {
                "success": True,
                "capability_id": capability_id,
                "expertise_level": capability.get_expertise_level()
            }
            
            self.logger.info(f"Registered capability '{name}' for agent {agent_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to register capability: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_service_listing(
        self,
        provider_id: str,
        service_name: str,
        description: str,
        category: ServiceCategory,
        base_price: float,
        currency_type: CurrencyType,
        capabilities: List[str],
        pricing_model: str = "fixed",
        estimated_duration: Optional[float] = None,
        max_concurrent_jobs: int = 1
    ) -> Dict[str, Any]:
        """Create a new service listing."""
        try:
            # Validate inputs
            if base_price < self.config["min_service_price"] or base_price > self.config["max_service_price"]:
                return {"success": False, "error": "Price outside allowed range"}
            
            # Check agent capability limits
            agent_listings = [listing for listing in self.service_listings.values() if listing.provider_id == provider_id]
            if len(agent_listings) >= self.config["max_listings_per_agent"]:
                return {"success": False, "error": "Maximum listings per agent exceeded"}
            
            # Validate capabilities
            agent_caps = self.agent_capabilities.get(provider_id, [])
            valid_capabilities = [cap.capability_id for cap in agent_caps]
            invalid_caps = [cap for cap in capabilities if cap not in valid_capabilities]
            if invalid_caps:
                return {"success": False, "error": f"Invalid capabilities: {invalid_caps}"}
            
            # Create listing
            self.listing_counter += 1
            listing_id = f"listing_{self.listing_counter}_{datetime.now().timestamp()}"
            
            listing = ServiceListing(
                listing_id=listing_id,
                provider_id=provider_id,
                service_name=service_name,
                description=description,
                category=category,
                base_price=base_price,
                currency_type=currency_type,
                capabilities=capabilities,
                pricing_model=pricing_model,
                estimated_duration=estimated_duration,
                max_concurrent_jobs=max_concurrent_jobs
            )
            
            self.service_listings[listing_id] = listing
            self.market_stats["total_listings"] += 1
            self.market_stats["active_listings"] += 1
            
            log_agent_event(
                self.agent_id,
                "service_listed",
                {
                    "listing_id": listing_id,
                    "provider_id": provider_id,
                    "service_name": service_name,
                    "category": category.value,
                    "base_price": base_price,
                    "currency": currency_type.value
                }
            )
            
            result = {
                "success": True,
                "listing_id": listing_id,
                "status": listing.status.value,
                "dynamic_price": listing.calculate_dynamic_price()
            }
            
            self.logger.info(f"Created service listing: {service_name} by {provider_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create service listing: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_services(
        self,
        category: Optional[ServiceCategory] = None,
        max_price: Optional[float] = None,
        currency_type: Optional[CurrencyType] = None,
        min_rating: float = 0.0,
        available_only: bool = True,
        keywords: Optional[List[str]] = None,
        sort_by: str = "rating"  # rating, price, response_time
    ) -> List[Dict[str, Any]]:
        """Search for services in the marketplace."""
        try:
            matching_listings = []
            
            for listing in self.service_listings.values():
                # Apply filters
                if category and listing.category != category:
                    continue
                
                if available_only and not listing.is_available():
                    continue
                
                if max_price and listing.base_price > max_price:
                    continue
                
                if currency_type and listing.currency_type != currency_type:
                    continue
                
                if listing.rating < min_rating:
                    continue
                
                # Keyword search
                if keywords:
                    text_to_search = f"{listing.service_name} {listing.description} {' '.join(listing.tags)}".lower()
                    if not any(keyword.lower() in text_to_search for keyword in keywords):
                        continue
                
                # Calculate current price
                demand_factor = self._calculate_demand_factor(listing.category)
                current_price = listing.calculate_dynamic_price(demand_factor)
                
                matching_listings.append({
                    "listing_id": listing.listing_id,
                    "provider_id": listing.provider_id,
                    "service_name": listing.service_name,
                    "description": listing.description,
                    "category": listing.category.value,
                    "base_price": listing.base_price,
                    "current_price": current_price,
                    "currency": listing.currency_type.value,
                    "rating": listing.rating,
                    "total_reviews": listing.total_reviews,
                    "success_rate": listing.success_rate,
                    "response_time_hours": listing.response_time_hours,
                    "available": listing.is_available(),
                    "featured": listing.featured,
                    "estimated_duration": listing.estimated_duration,
                    "capabilities": listing.capabilities,
                    "tags": listing.tags
                })
            
            # Sort results
            if sort_by == "rating":
                matching_listings.sort(key=lambda x: x["rating"], reverse=True)
            elif sort_by == "price":
                matching_listings.sort(key=lambda x: x["current_price"])
            elif sort_by == "response_time":
                matching_listings.sort(key=lambda x: x["response_time_hours"])
            
            return matching_listings
            
        except Exception as e:
            self.logger.error(f"Failed to search services: {e}")
            return []
    
    async def request_service(
        self,
        client_id: str,
        listing_id: str,
        service_description: str,
        proposed_price: Optional[float] = None,
        deadline: Optional[datetime] = None,
        requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Request a service from a provider."""
        try:
            if listing_id not in self.service_listings:
                return {"success": False, "error": "Service listing not found"}
            
            listing = self.service_listings[listing_id]
            
            if not listing.is_available():
                return {"success": False, "error": "Service not currently available"}
            
            # Determine price
            if proposed_price is None:
                demand_factor = self._calculate_demand_factor(listing.category)
                agreed_price = listing.calculate_dynamic_price(demand_factor)
            else:
                agreed_price = proposed_price
            
            # Create contract
            self.contract_counter += 1
            contract_id = f"contract_{self.contract_counter}_{datetime.now().timestamp()}"
            
            contract = ServiceContract(
                contract_id=contract_id,
                listing_id=listing_id,
                provider_id=listing.provider_id,
                client_id=client_id,
                service_description=service_description,
                agreed_price=agreed_price,
                currency_type=listing.currency_type,
                estimated_duration=listing.estimated_duration or 1.0,
                deadline=deadline,
                requirements=requirements or {}
            )
            
            self.service_contracts[contract_id] = contract
            listing.pending_requests += 1
            
            # If price matches or no negotiation needed, auto-accept
            if proposed_price is None or abs(proposed_price - listing.base_price) / listing.base_price < 0.1:
                contract.status = ContractStatus.ACCEPTED
                contract.accepted_at = datetime.now()
                listing.active_contracts.add(contract_id)
                listing.pending_requests -= 1
                
                # Process payment if required
                if contract.payment_schedule == "upfront":
                    await self._process_contract_payment(contract)
            else:
                # Queue for negotiation
                await self.negotiation_queue.put(contract_id)
            
            self.market_stats["total_contracts"] += 1
            self.market_stats["category_demand"][listing.category.value] += 1
            
            log_agent_event(
                self.agent_id,
                "service_requested",
                {
                    "contract_id": contract_id,
                    "client_id": client_id,
                    "provider_id": listing.provider_id,
                    "listing_id": listing_id,
                    "agreed_price": agreed_price
                }
            )
            
            result = {
                "success": True,
                "contract_id": contract_id,
                "status": contract.status.value,
                "agreed_price": agreed_price,
                "estimated_duration": contract.estimated_duration,
                "provider_id": listing.provider_id
            }
            
            self.logger.info(f"Service requested: {listing.service_name} by {client_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to request service: {e}")
            return {"success": False, "error": str(e)}    

    async def start_contract_work(self, contract_id: str, provider_id: str) -> Dict[str, Any]:
        """Start work on a service contract."""
        try:
            if contract_id not in self.service_contracts:
                return {"success": False, "error": "Contract not found"}
            
            contract = self.service_contracts[contract_id]
            
            if contract.provider_id != provider_id:
                return {"success": False, "error": "Not authorized to work on this contract"}
            
            if contract.status != ContractStatus.ACCEPTED:
                return {"success": False, "error": f"Contract not ready for work (status: {contract.status.value})"}
            
            # Start work
            contract.status = ContractStatus.IN_PROGRESS
            contract.started_at = datetime.now()
            
            # Process escrow payment if required
            if contract.payment_schedule == "escrow":
                await self._setup_escrow_payment(contract)
            
            log_agent_event(
                self.agent_id,
                "contract_work_started",
                {
                    "contract_id": contract_id,
                    "provider_id": provider_id,
                    "client_id": contract.client_id,
                    "estimated_duration": contract.estimated_duration
                }
            )
            
            result = {
                "success": True,
                "status": contract.status.value,
                "started_at": contract.started_at.isoformat(),
                "deadline": contract.deadline.isoformat() if contract.deadline else None
            }
            
            self.logger.info(f"Contract work started: {contract_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to start contract work: {e}")
            return {"success": False, "error": str(e)}
    
    async def complete_contract(
        self,
        contract_id: str,
        provider_id: str,
        deliverables: List[Dict[str, Any]],
        completion_notes: str = ""
    ) -> Dict[str, Any]:
        """Complete a service contract."""
        try:
            if contract_id not in self.service_contracts:
                return {"success": False, "error": "Contract not found"}
            
            contract = self.service_contracts[contract_id]
            
            if contract.provider_id != provider_id:
                return {"success": False, "error": "Not authorized to complete this contract"}
            
            if contract.status != ContractStatus.IN_PROGRESS:
                return {"success": False, "error": f"Contract not in progress (status: {contract.status.value})"}
            
            # Complete contract
            contract.status = ContractStatus.COMPLETED
            contract.completed_at = datetime.now()
            contract.progress_percentage = 100.0
            contract.deliverables = deliverables
            
            # Process final payment
            await self._process_contract_completion_payment(contract)
            
            # Update listing metrics
            listing = self.service_listings[contract.listing_id]
            listing.active_contracts.discard(contract_id)
            
            # Update provider capabilities
            await self._update_provider_experience(contract)
            
            # Update market stats
            self.market_stats["completed_contracts"] += 1
            self.market_stats["total_volume"] += contract.agreed_price
            
            log_agent_event(
                self.agent_id,
                "contract_completed",
                {
                    "contract_id": contract_id,
                    "provider_id": provider_id,
                    "client_id": contract.client_id,
                    "duration_hours": contract.get_duration_so_far(),
                    "agreed_price": contract.agreed_price
                }
            )
            
            result = {
                "success": True,
                "status": contract.status.value,
                "completed_at": contract.completed_at.isoformat(),
                "duration_hours": contract.get_duration_so_far(),
                "deliverables_count": len(deliverables)
            }
            
            self.logger.info(f"Contract completed: {contract_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to complete contract: {e}")
            return {"success": False, "error": str(e)}
    
    async def submit_review(
        self,
        reviewer_id: str,
        contract_id: str,
        rating: QualityRating,
        title: str,
        comment: str
    ) -> Dict[str, Any]:
        """Submit a review for a completed service."""
        try:
            if contract_id not in self.service_contracts:
                return {"success": False, "error": "Contract not found"}
            
            contract = self.service_contracts[contract_id]
            
            if contract.status != ContractStatus.COMPLETED:
                return {"success": False, "error": "Can only review completed contracts"}
            
            # Check if reviewer is involved in the contract
            if reviewer_id not in [contract.client_id, contract.provider_id]:
                return {"success": False, "error": "Not authorized to review this contract"}
            
            # Check if review already exists
            existing_reviews = [r for r in self.service_reviews.values() 
                             if r.contract_id == contract_id and r.reviewer_id == reviewer_id]
            if existing_reviews:
                return {"success": False, "error": "Review already submitted"}
            
            # Create review
            self.review_counter += 1
            review_id = f"review_{self.review_counter}_{datetime.now().timestamp()}"
            
            review = ServiceReview(
                review_id=review_id,
                contract_id=contract_id,
                listing_id=contract.listing_id,
                reviewer_id=reviewer_id,
                provider_id=contract.provider_id,
                rating=rating,
                title=title,
                comment=comment,
                verified=True  # Reviews from actual contracts are verified
            )
            
            self.service_reviews[review_id] = review
            
            # Update contract with rating
            if reviewer_id == contract.client_id:
                contract.client_rating = rating
                contract.client_feedback = comment
            else:
                contract.provider_rating = rating
                contract.provider_feedback = comment
            
            # Update listing metrics
            await self._update_listing_rating(contract.listing_id, rating)
            
            log_agent_event(
                self.agent_id,
                "review_submitted",
                {
                    "review_id": review_id,
                    "contract_id": contract_id,
                    "reviewer_id": reviewer_id,
                    "rating": rating.value,
                    "listing_id": contract.listing_id
                }
            )
            
            result = {
                "success": True,
                "review_id": review_id,
                "rating": rating.value,
                "verified": review.verified
            }
            
            self.logger.info(f"Review submitted: {rating.value} stars for contract {contract_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to submit review: {e}")
            return {"success": False, "error": str(e)}
    
    async def report_dispute(
        self,
        reporter_id: str,
        contract_id: str,
        dispute_reason: str,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Report a dispute for a contract."""
        try:
            if contract_id not in self.service_contracts:
                return {"success": False, "error": "Contract not found"}
            
            contract = self.service_contracts[contract_id]
            
            if reporter_id not in [contract.client_id, contract.provider_id]:
                return {"success": False, "error": "Not authorized to dispute this contract"}
            
            if contract.status in [ContractStatus.COMPLETED, ContractStatus.CANCELLED]:
                return {"success": False, "error": "Cannot dispute completed or cancelled contracts"}
            
            # Update contract status
            contract.status = ContractStatus.DISPUTED
            contract.dispute_reason = dispute_reason
            
            # Find mediator (simplified - would use more sophisticated selection)
            mediator_id = await self._select_mediator(contract)
            contract.mediator_id = mediator_id
            
            log_agent_event(
                self.agent_id,
                "dispute_reported",
                {
                    "contract_id": contract_id,
                    "reporter_id": reporter_id,
                    "dispute_reason": dispute_reason,
                    "mediator_id": mediator_id
                }
            )
            
            result = {
                "success": True,
                "status": contract.status.value,
                "mediator_id": mediator_id,
                "dispute_reason": dispute_reason
            }
            
            self.logger.info(f"Dispute reported for contract {contract_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to report dispute: {e}")
            return {"success": False, "error": str(e)}
    
    def get_agent_listings(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all service listings for an agent."""
        try:
            agent_listings = []
            
            for listing in self.service_listings.values():
                if listing.provider_id == agent_id:
                    demand_factor = self._calculate_demand_factor(listing.category)
                    current_price = listing.calculate_dynamic_price(demand_factor)
                    
                    agent_listings.append({
                        "listing_id": listing.listing_id,
                        "service_name": listing.service_name,
                        "category": listing.category.value,
                        "base_price": listing.base_price,
                        "current_price": current_price,
                        "currency": listing.currency_type.value,
                        "status": listing.status.value,
                        "rating": listing.rating,
                        "total_reviews": listing.total_reviews,
                        "active_contracts": len(listing.active_contracts),
                        "max_concurrent_jobs": listing.max_concurrent_jobs,
                        "pending_requests": listing.pending_requests,
                        "created_at": listing.created_at.isoformat(),
                        "featured": listing.featured
                    })
            
            # Sort by creation date (most recent first)
            agent_listings.sort(key=lambda x: x["created_at"], reverse=True)
            
            return agent_listings
            
        except Exception as e:
            self.logger.error(f"Failed to get agent listings: {e}")
            return []
    
    def get_agent_contracts(self, agent_id: str, role: str = "both") -> List[Dict[str, Any]]:
        """Get contracts for an agent (as client, provider, or both)."""
        try:
            agent_contracts = []
            
            for contract in self.service_contracts.values():
                include_contract = False
                agent_role = None
                
                if role in ["both", "client"] and contract.client_id == agent_id:
                    include_contract = True
                    agent_role = "client"
                elif role in ["both", "provider"] and contract.provider_id == agent_id:
                    include_contract = True
                    agent_role = "provider"
                
                if include_contract:
                    listing = self.service_listings.get(contract.listing_id)
                    
                    agent_contracts.append({
                        "contract_id": contract.contract_id,
                        "listing_id": contract.listing_id,
                        "service_name": listing.service_name if listing else "Unknown",
                        "client_id": contract.client_id,
                        "provider_id": contract.provider_id,
                        "agent_role": agent_role,
                        "status": contract.status.value,
                        "agreed_price": contract.agreed_price,
                        "currency": contract.currency_type.value,
                        "progress": contract.progress_percentage,
                        "created_at": contract.created_at.isoformat(),
                        "deadline": contract.deadline.isoformat() if contract.deadline else None,
                        "is_overdue": contract.is_overdue(),
                        "duration_so_far": contract.get_duration_so_far()
                    })
            
            # Sort by creation date (most recent first)
            agent_contracts.sort(key=lambda x: x["created_at"], reverse=True)
            
            return agent_contracts
            
        except Exception as e:
            self.logger.error(f"Failed to get agent contracts: {e}")
            return []
    
    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics."""
        try:
            # Calculate additional metrics
            active_contracts = len([c for c in self.service_contracts.values() 
                                 if c.status == ContractStatus.IN_PROGRESS])
            
            disputed_contracts = len([c for c in self.service_contracts.values() 
                                   if c.status == ContractStatus.DISPUTED])
            
            total_contracts = len(self.service_contracts)
            dispute_rate = (disputed_contracts / max(1, total_contracts)) * 100.0
            
            completion_rate = (self.market_stats["completed_contracts"] / max(1, total_contracts)) * 100.0
            
            # Category statistics
            category_stats = {}
            for category in ServiceCategory:
                category_listings = [listing for listing in self.service_listings.values() 
                                   if l.category == category]
                category_stats[category.value] = {
                    "total_listings": len(category_listings),
                    "active_listings": len([listing for listing in category_listings if listing.is_available()]),
                    "average_price": sum(listing.base_price for listing in category_listings) / max(1, len(category_listings)),
                    "demand": self.market_stats["category_demand"][category.value]
                }
            
            # Provider statistics
            providers = set(listing.provider_id for listing in self.service_listings.values())
            avg_listings_per_provider = len(self.service_listings) / max(1, len(providers))
            
            return {
                "total_listings": self.market_stats["total_listings"],
                "active_listings": self.market_stats["active_listings"],
                "total_contracts": total_contracts,
                "active_contracts": active_contracts,
                "completed_contracts": self.market_stats["completed_contracts"],
                "disputed_contracts": disputed_contracts,
                "completion_rate_percent": completion_rate,
                "dispute_rate_percent": dispute_rate,
                "total_volume": self.market_stats["total_volume"],
                "average_rating": self.market_stats["average_rating"],
                "total_providers": len(providers),
                "avg_listings_per_provider": avg_listings_per_provider,
                "category_statistics": category_stats,
                "total_reviews": len(self.service_reviews)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get marketplace stats: {e}")
            return {"error": str(e)}
    
    def get_trending_services(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending services based on recent demand."""
        try:
            # Calculate trending score based on recent contracts and ratings
            trending_listings = []
            
            for listing in self.service_listings.values():
                if not listing.is_available():
                    continue
                
                # Recent contracts (last 7 days)
                recent_contracts = [
                    c for c in self.service_contracts.values()
                    if c.listing_id == listing.listing_id and 
                    (datetime.now() - c.created_at).days <= 7
                ]
                
                # Calculate trending score
                demand_score = len(recent_contracts) * 10
                rating_score = listing.rating * 5
                availability_score = (listing.max_concurrent_jobs - len(listing.active_contracts)) * 2
                
                trending_score = demand_score + rating_score + availability_score
                
                if trending_score > 0:
                    demand_factor = self._calculate_demand_factor(listing.category)
                    current_price = listing.calculate_dynamic_price(demand_factor)
                    
                    trending_listings.append({
                        "listing_id": listing.listing_id,
                        "service_name": listing.service_name,
                        "provider_id": listing.provider_id,
                        "category": listing.category.value,
                        "current_price": current_price,
                        "currency": listing.currency_type.value,
                        "rating": listing.rating,
                        "total_reviews": listing.total_reviews,
                        "recent_contracts": len(recent_contracts),
                        "trending_score": trending_score,
                        "featured": listing.featured
                    })
            
            # Sort by trending score
            trending_listings.sort(key=lambda x: x["trending_score"], reverse=True)
            
            return trending_listings[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get trending services: {e}")
            return []
    
    # Private helper methods
    
    def _calculate_demand_factor(self, category: ServiceCategory) -> float:
        """Calculate demand factor for a service category."""
        try:
            total_demand = sum(self.market_stats["category_demand"].values())
            if total_demand == 0:
                return 1.0
            
            category_demand = self.market_stats["category_demand"][category.value]
            category_supply = len([listing for listing in self.service_listings.values() 
                                 if l.category == category and l.is_available()])
            
            if category_supply == 0:
                return 2.0  # High demand, no supply
            
            demand_supply_ratio = category_demand / category_supply
            return 1.0 + (demand_supply_ratio - 1.0) * 0.3  # 30% max adjustment
            
        except Exception as e:
            self.logger.error(f"Error calculating demand factor: {e}")
            return 1.0
    
    async def _process_contract_payment(self, contract: ServiceContract) -> bool:
        """Process payment for a contract."""
        try:
            # Calculate total cost including marketplace fee
            marketplace_fee = contract.agreed_price * self.config["marketplace_fee_rate"]
            contract.agreed_price + marketplace_fee
            
            # Process payment through currency system
            payment_result = await self.currency_system.process_payment(
                payer_id=contract.client_id,
                payee_id=contract.provider_id,
                amount=contract.agreed_price,
                currency_type=contract.currency_type,
                service_id=contract.contract_id,
                description=f"Payment for service contract {contract.contract_id}"
            )
            
            if payment_result["success"]:
                contract.payment_transaction_id = payment_result["transaction_id"]
                
                # Process marketplace fee
                await self.currency_system.process_payment(
                    payer_id=contract.client_id,
                    payee_id="marketplace",
                    amount=marketplace_fee,
                    currency_type=contract.currency_type,
                    service_id=contract.contract_id,
                    description=f"Marketplace fee for contract {contract.contract_id}"
                )
                
                return True
            else:
                contract.status = ContractStatus.CANCELLED
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing contract payment: {e}")
            return False
    
    async def _setup_escrow_payment(self, contract: ServiceContract) -> bool:
        """Set up escrow payment for a contract."""
        try:
            # For now, treat escrow similar to upfront payment
            # In a full implementation, this would hold funds in escrow
            return await self._process_contract_payment(contract)
            
        except Exception as e:
            self.logger.error(f"Error setting up escrow payment: {e}")
            return False
    
    async def _process_contract_completion_payment(self, contract: ServiceContract) -> bool:
        """Process payment upon contract completion."""
        try:
            if contract.payment_schedule == "completion":
                return await self._process_contract_payment(contract)
            else:
                # Payment already processed for upfront/escrow
                return True
                
        except Exception as e:
            self.logger.error(f"Error processing completion payment: {e}")
            return False
    
    async def _update_provider_experience(self, contract: ServiceContract) -> None:
        """Update provider experience and capabilities based on completed contract."""
        try:
            provider_id = contract.provider_id
            if provider_id not in self.agent_capabilities:
                return
            
            # Find relevant capabilities
            listing = self.service_listings[contract.listing_id]
            for capability_id in listing.capabilities:
                for capability in self.agent_capabilities[provider_id]:
                    if capability.capability_id == capability_id:
                        # Update experience
                        capability.experience_points += 10
                        capability.total_jobs += 1
                        
                        # Update skill level based on experience
                        experience_bonus = min(0.1, capability.experience_points / 1000.0)
                        capability.skill_level = min(1.0, capability.skill_level + experience_bonus)
                        
                        # Update success rate
                        if contract.client_rating:
                            rating_value = contract.client_rating.value
                            success = 1.0 if rating_value >= 3 else 0.0
                            capability.success_rate = (capability.success_rate * (capability.total_jobs - 1) + success) / capability.total_jobs
                        
                        break
            
        except Exception as e:
            self.logger.error(f"Error updating provider experience: {e}")
    
    async def _update_listing_rating(self, listing_id: str, new_rating: QualityRating) -> None:
        """Update listing rating based on new review."""
        try:
            if listing_id not in self.service_listings:
                return
            
            listing = self.service_listings[listing_id]
            
            # Calculate new average rating
            total_rating_points = listing.rating * listing.total_reviews
            total_rating_points += new_rating.value
            listing.total_reviews += 1
            listing.rating = total_rating_points / listing.total_reviews
            
            # Update market average
            all_ratings = [listing.rating for listing in self.service_listings.values() if listing.total_reviews > 0]
            if all_ratings:
                self.market_stats["average_rating"] = sum(all_ratings) / len(all_ratings)
            
        except Exception as e:
            self.logger.error(f"Error updating listing rating: {e}")
    
    async def _select_mediator(self, contract: ServiceContract) -> str:
        """Select a mediator for dispute resolution."""
        try:
            # Simplified mediator selection - in practice would be more sophisticated
            # Could select based on expertise, availability, neutrality, etc.
            
            # For now, return a system mediator
            return "system_mediator"
            
        except Exception as e:
            self.logger.error(f"Error selecting mediator: {e}")
            return "system_mediator"
    
    async def _negotiation_processor(self) -> None:
        """Background task to process contract negotiations."""
        while True:
            try:
                # Get contract from negotiation queue
                contract_id = await asyncio.wait_for(self.negotiation_queue.get(), timeout=1.0)
                
                # Process negotiation (simplified)
                if contract_id in self.service_contracts:
                    contract = self.service_contracts[contract_id]
                    listing = self.service_listings[contract.listing_id]
                    
                    # Simple negotiation logic
                    price_difference = abs(contract.agreed_price - listing.base_price)
                    if price_difference / listing.base_price < 0.2:  # Within 20%
                        contract.status = ContractStatus.ACCEPTED
                        contract.accepted_at = datetime.now()
                        listing.active_contracts.add(contract_id)
                        listing.pending_requests -= 1
                    else:
                        contract.status = ContractStatus.CANCELLED
                        listing.pending_requests -= 1
                
                self.negotiation_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in negotiation processor: {e}")
                await asyncio.sleep(1)
    
    async def _contract_monitor(self) -> None:
        """Background task to monitor contract progress and timeouts."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                current_time = datetime.now()
                
                for contract in self.service_contracts.values():
                    # Check for overdue contracts
                    if contract.is_overdue() and contract.status == ContractStatus.IN_PROGRESS:
                        # Auto-dispute overdue contracts
                        contract.status = ContractStatus.DISPUTED
                        contract.dispute_reason = "Contract overdue"
                        
                        log_agent_event(
                            self.agent_id,
                            "contract_overdue",
                            {
                                "contract_id": contract.contract_id,
                                "deadline": contract.deadline.isoformat() if contract.deadline else None
                            }
                        )
                    
                    # Check for stale proposed contracts
                    if (contract.status == ContractStatus.PROPOSED and 
                        (current_time - contract.created_at).total_seconds() / 3600.0 > self.config["contract_timeout_hours"]):
                        contract.status = ContractStatus.CANCELLED
                        
                        # Update listing
                        if contract.listing_id in self.service_listings:
                            self.service_listings[contract.listing_id].pending_requests -= 1
                
            except Exception as e:
                self.logger.error(f"Error in contract monitor: {e}")
                await asyncio.sleep(300)
    
    async def _market_analyzer(self) -> None:
        """Background task to analyze market trends and update statistics."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Update market statistics
                                self.market_stats["active_listings"] = len([
                                    listing for listing in self.service_listings.values()
                                    if listing.status == ServiceStatus.AVAILABLE
                                ])                
                # Calculate dispute rate
                total_contracts = len(self.service_contracts)
                disputed_contracts = len([
                    c for c in self.service_contracts.values() 
                    if c.status == ContractStatus.DISPUTED
                ])
                self.market_stats["dispute_rate"] = (disputed_contracts / max(1, total_contracts)) * 100.0
                
                # Reset daily demand counters (simplified)
                if datetime.now().hour == 0:  # Reset at midnight
                    for category in ServiceCategory:
                        self.market_stats["category_demand"][category.value] *= 0.9  # Decay factor
                
            except Exception as e:
                self.logger.error(f"Error in market analyzer: {e}")
                await asyncio.sleep(300)
    
    async def _save_marketplace_state(self) -> None:
        """Save marketplace state to persistent storage."""
        try:
            # In a real implementation, this would save to persistent storage
            self.logger.info(f"Saved marketplace state: {len(self.service_listings)} listings, {len(self.service_contracts)} contracts")
        except Exception as e:
            self.logger.error(f"Error saving marketplace state: {e}")