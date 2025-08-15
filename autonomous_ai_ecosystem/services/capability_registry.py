"""
Service capability registration and management system.

This module implements agent skill tracking, capability assessment,
and service discovery and matching algorithms.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import statistics

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class ServiceType(Enum):
    """Types of services agents can provide."""
    RESEARCH = "research"
    CODING = "coding"
    DATA_ANALYSIS = "data_analysis"
    CREATIVE_CONTENT = "creative_content"
    MONITORING = "monitoring"
    AUTOMATION = "automation"
    PROBLEM_SOLVING = "problem_solving"
    COMMUNICATION = "communication"
    LEARNING = "learning"
    WORLD_BUILDING = "world_building"
    ECONOMIC_TRADING = "economic_trading"


class ExpertiseLevel(Enum):
    """Levels of expertise for services."""
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class CapabilityStatus(Enum):
    """Status of agent capabilities."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEVELOPING = "developing"
    DEPRECATED = "deprecated"


@dataclass
class ServiceCapability:
    """Represents an agent's capability to provide a specific service."""
    capability_id: str
    agent_id: str
    service_type: ServiceType
    
    # Capability details
    name: str
    description: str
    expertise_level: ExpertiseLevel
    specializations: List[str] = field(default_factory=list)
    
    # Performance metrics
    success_rate: float = 0.0
    average_completion_time: float = 0.0
    quality_score: float = 0.0
    reliability_score: float = 0.0
    
    # Usage statistics
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    average_rating: float = 0.0
    
    # Availability
    status: CapabilityStatus = CapabilityStatus.ACTIVE
    max_concurrent_tasks: int = 3
    current_load: int = 0
    
    # Requirements and constraints
    required_resources: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    
    def calculate_overall_score(self) -> float:
        """Calculate overall capability score."""
        scores = [
            self.success_rate,
            self.quality_score,
            self.reliability_score,
            min(1.0, self.average_rating / 5.0)  # Normalize rating to 0-1
        ]
        
        # Weight by expertise level
        expertise_weights = {
            ExpertiseLevel.NOVICE: 0.3,
            ExpertiseLevel.BEGINNER: 0.5,
            ExpertiseLevel.INTERMEDIATE: 0.7,
            ExpertiseLevel.ADVANCED: 0.85,
            ExpertiseLevel.EXPERT: 0.95,
            ExpertiseLevel.MASTER: 1.0
        }
        
        base_score = sum(scores) / len(scores)
        expertise_weight = expertise_weights.get(self.expertise_level, 0.5)
        
        return base_score * expertise_weight
    
    def is_available(self) -> bool:
        """Check if capability is available for new tasks."""
        return (self.status == CapabilityStatus.ACTIVE and 
                self.current_load < self.max_concurrent_tasks)
    
    def update_performance_metrics(
        self,
        success: bool,
        completion_time: float,
        quality_score: float,
        rating: Optional[float] = None
    ) -> None:
        """Update performance metrics based on task completion."""
        self.total_requests += 1
        
        if success:
            self.completed_requests += 1
        else:
            self.failed_requests += 1
        
        # Update success rate
        self.success_rate = self.completed_requests / self.total_requests
        
        # Update average completion time
        if self.average_completion_time == 0:
            self.average_completion_time = completion_time
        else:
            self.average_completion_time = (
                (self.average_completion_time * (self.total_requests - 1) + completion_time) / 
                self.total_requests
            )
        
        # Update quality score
        if self.quality_score == 0:
            self.quality_score = quality_score
        else:
            self.quality_score = (
                (self.quality_score * (self.total_requests - 1) + quality_score) / 
                self.total_requests
            )
        
        # Update rating if provided
        if rating is not None:
            if self.average_rating == 0:
                self.average_rating = rating
            else:
                self.average_rating = (
                    (self.average_rating * (self.total_requests - 1) + rating) / 
                    self.total_requests
                )
        
        # Update reliability score based on recent performance
        recent_success_rate = self.success_rate
        consistency_factor = 1.0 - abs(self.quality_score - quality_score) / max(self.quality_score, 0.1)
        self.reliability_score = (recent_success_rate + consistency_factor) / 2
        
        self.last_updated = datetime.now()
        self.last_used = datetime.now()


@dataclass
class ServiceRequest:
    """Represents a request for a specific service."""
    request_id: str
    service_type: ServiceType
    description: str
    
    # Requirements
    required_expertise: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    required_specializations: List[str] = field(default_factory=list)
    max_completion_time: Optional[float] = None
    min_quality_score: float = 0.7
    
    # Preferences
    preferred_agents: List[str] = field(default_factory=list)
    excluded_agents: List[str] = field(default_factory=list)
    
    # Context
    priority: int = 5  # 1-10, 10 being highest
    deadline: Optional[datetime] = None
    budget: Optional[float] = None
    
    # Metadata
    requested_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ServiceMatch:
    """Represents a match between a service request and agent capability."""
    match_id: str
    request_id: str
    capability_id: str
    agent_id: str
    
    # Match quality
    compatibility_score: float
    confidence_score: float
    estimated_completion_time: float
    estimated_quality: float
    
    # Match details
    matching_specializations: List[str] = field(default_factory=list)
    expertise_match: bool = False
    availability_confirmed: bool = False
    
    # Ranking factors
    agent_reputation: float = 0.0
    past_performance: float = 0.0
    current_workload: float = 0.0
    
    def calculate_overall_match_score(self) -> float:
        """Calculate overall match score."""
        scores = [
            self.compatibility_score * 0.3,
            self.confidence_score * 0.2,
            self.agent_reputation * 0.2,
            self.past_performance * 0.2,
            (1.0 - self.current_workload) * 0.1  # Lower workload is better
        ]
        
        base_score = sum(scores)
        
        # Bonus for expertise match
        if self.expertise_match:
            base_score *= 1.1
        
        # Bonus for availability
        if self.availability_confirmed:
            base_score *= 1.05
        
        return min(1.0, base_score)


class ServiceCapabilityRegistry(AgentModule):
    """
    Service capability registration and management system.
    
    Manages agent capabilities, handles service discovery,
    and provides matching algorithms for service requests.
    """
    
    def __init__(self, agent_id: str = "capability_registry"):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "capability_registry")
        
        # Core data structures
        self.capabilities: Dict[str, ServiceCapability] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}  # agent_id -> capability_ids
        self.service_requests: Dict[str, ServiceRequest] = {}
        self.service_matches: Dict[str, List[ServiceMatch]] = {}  # request_id -> matches
        
        # Indexing for fast lookup
        self.capabilities_by_service: Dict[ServiceType, List[str]] = {
            service_type: [] for service_type in ServiceType
        }
        self.capabilities_by_expertise: Dict[ExpertiseLevel, List[str]] = {
            expertise: [] for expertise in ExpertiseLevel
        }
        
        # Configuration
        self.config = {
            "max_matches_per_request": 10,
            "min_compatibility_score": 0.3,
            "capability_expiry_days": 90,
            "performance_history_limit": 100,
            "auto_update_expertise": True,
            "expertise_promotion_threshold": 0.9,
            "expertise_demotion_threshold": 0.4,
            "default_max_concurrent_tasks": 3
        }
        
        # Statistics
        self.stats = {
            "total_capabilities": 0,
            "active_capabilities": 0,
            "total_requests": 0,
            "successful_matches": 0,
            "average_match_score": 0.0,
            "capabilities_by_service": {service.value: 0 for service in ServiceType},
            "capabilities_by_expertise": {level.value: 0 for level in ExpertiseLevel},
            "agent_count": 0
        }
        
        # Counters
        self.capability_counter = 0
        self.request_counter = 0
        self.match_counter = 0
        
        self.logger.info("Service capability registry initialized")
    
    async def initialize(self) -> None:
        """Initialize the capability registry."""
        try:
            # Start background tasks
            asyncio.create_task(self._update_statistics())
            asyncio.create_task(self._cleanup_expired_data())
            asyncio.create_task(self._auto_update_expertise_levels())
            
            self.logger.info("Service capability registry initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize capability registry: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the capability registry."""
        try:
            self.logger.info("Service capability registry shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during capability registry shutdown: {e}")
    
    async def register_capability(
        self,
        agent_id: str,
        service_type: ServiceType,
        name: str,
        description: str,
        expertise_level: ExpertiseLevel = ExpertiseLevel.BEGINNER,
        specializations: Optional[List[str]] = None,
        max_concurrent_tasks: int = 3,
        required_resources: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a new service capability for an agent."""
        try:
            # Create capability
            self.capability_counter += 1
            capability_id = f"cap_{self.capability_counter}_{datetime.now().timestamp()}"
            
            capability = ServiceCapability(
                capability_id=capability_id,
                agent_id=agent_id,
                service_type=service_type,
                name=name,
                description=description,
                expertise_level=expertise_level,
                specializations=specializations or [],
                max_concurrent_tasks=max_concurrent_tasks,
                required_resources=required_resources or {}
            )
            
            # Store capability
            self.capabilities[capability_id] = capability
            
            # Update agent capabilities index
            if agent_id not in self.agent_capabilities:
                self.agent_capabilities[agent_id] = []
            self.agent_capabilities[agent_id].append(capability_id)
            
            # Update service type index
            self.capabilities_by_service[service_type].append(capability_id)
            
            # Update expertise level index
            self.capabilities_by_expertise[expertise_level].append(capability_id)
            
            # Update statistics
            self.stats["total_capabilities"] += 1
            self.stats["active_capabilities"] += 1
            self.stats["capabilities_by_service"][service_type.value] += 1
            self.stats["capabilities_by_expertise"][expertise_level.value] += 1
            
            if agent_id not in [cap.agent_id for cap in self.capabilities.values()]:
                self.stats["agent_count"] += 1
            
            log_agent_event(
                agent_id,
                "capability_registered",
                {
                    "capability_id": capability_id,
                    "service_type": service_type.value,
                    "expertise_level": expertise_level.value,
                    "specializations": specializations or []
                }
            )
            
            self.logger.info(f"Capability registered: {name} for agent {agent_id}")
            
            return capability_id
            
        except Exception as e:
            self.logger.error(f"Failed to register capability: {e}")
            return ""
    
    async def update_capability(
        self,
        capability_id: str,
        **updates
    ) -> bool:
        """Update an existing capability."""
        try:
            if capability_id not in self.capabilities:
                return False
            
            capability = self.capabilities[capability_id]
            old_service_type = capability.service_type
            old_expertise = capability.expertise_level
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(capability, key):
                    setattr(capability, key, value)
            
            capability.last_updated = datetime.now()
            
            # Update indexes if service type or expertise changed
            if 'service_type' in updates and updates['service_type'] != old_service_type:
                self.capabilities_by_service[old_service_type].remove(capability_id)
                self.capabilities_by_service[capability.service_type].append(capability_id)
                
                self.stats["capabilities_by_service"][old_service_type.value] -= 1
                self.stats["capabilities_by_service"][capability.service_type.value] += 1
            
            if 'expertise_level' in updates and updates['expertise_level'] != old_expertise:
                self.capabilities_by_expertise[old_expertise].remove(capability_id)
                self.capabilities_by_expertise[capability.expertise_level].append(capability_id)
                
                self.stats["capabilities_by_expertise"][old_expertise.value] -= 1
                self.stats["capabilities_by_expertise"][capability.expertise_level.value] += 1
            
            log_agent_event(
                capability.agent_id,
                "capability_updated",
                {
                    "capability_id": capability_id,
                    "updates": list(updates.keys())
                }
            )
            
            self.logger.info(f"Capability updated: {capability_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update capability: {e}")
            return False
    
    async def deactivate_capability(self, capability_id: str) -> bool:
        """Deactivate a capability."""
        try:
            if capability_id not in self.capabilities:
                return False
            
            capability = self.capabilities[capability_id]
            capability.status = CapabilityStatus.INACTIVE
            capability.last_updated = datetime.now()
            
            self.stats["active_capabilities"] -= 1
            
            log_agent_event(
                capability.agent_id,
                "capability_deactivated",
                {"capability_id": capability_id}
            )
            
            self.logger.info(f"Capability deactivated: {capability_id}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deactivate capability: {e}")
            return False
    
    async def find_service_providers(
        self,
        service_type: ServiceType,
        required_expertise: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE,
        required_specializations: Optional[List[str]] = None,
        max_results: int = 10,
        min_quality_score: float = 0.5,
        exclude_agents: Optional[List[str]] = None
    ) -> List[ServiceCapability]:
        """Find agents capable of providing a specific service."""
        try:
            # Get capabilities for the service type
            candidate_ids = self.capabilities_by_service.get(service_type, [])
            candidates = [self.capabilities[cap_id] for cap_id in candidate_ids]
            
            # Filter by status
            candidates = [cap for cap in candidates if cap.status == CapabilityStatus.ACTIVE]
            
            # Filter by expertise level
            expertise_order = list(ExpertiseLevel)
            min_expertise_index = expertise_order.index(required_expertise)
            candidates = [
                cap for cap in candidates 
                if expertise_order.index(cap.expertise_level) >= min_expertise_index
            ]
            
            # Filter by quality score
            candidates = [cap for cap in candidates if cap.quality_score >= min_quality_score]
            
            # Filter by excluded agents
            if exclude_agents:
                candidates = [cap for cap in candidates if cap.agent_id not in exclude_agents]
            
            # Filter by specializations if specified
            if required_specializations:
                filtered_candidates = []
                for cap in candidates:
                    if any(spec in cap.specializations for spec in required_specializations):
                        filtered_candidates.append(cap)
                candidates = filtered_candidates
            
            # Sort by overall score
            candidates.sort(key=lambda cap: cap.calculate_overall_score(), reverse=True)
            
            # Return top results
            return candidates[:max_results]
            
        except Exception as e:
            self.logger.error(f"Failed to find service providers: {e}")
            return []
    
    async def match_service_request(
        self,
        service_type: ServiceType,
        description: str,
        required_expertise: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE,
        required_specializations: Optional[List[str]] = None,
        max_completion_time: Optional[float] = None,
        min_quality_score: float = 0.7,
        preferred_agents: Optional[List[str]] = None,
        excluded_agents: Optional[List[str]] = None,
        priority: int = 5
    ) -> List[ServiceMatch]:
        """Match a service request with available capabilities."""
        try:
            # Create service request
            self.request_counter += 1
            request_id = f"req_{self.request_counter}_{datetime.now().timestamp()}"
            
            request = ServiceRequest(
                request_id=request_id,
                service_type=service_type,
                description=description,
                required_expertise=required_expertise,
                required_specializations=required_specializations or [],
                max_completion_time=max_completion_time,
                min_quality_score=min_quality_score,
                preferred_agents=preferred_agents or [],
                excluded_agents=excluded_agents or [],
                priority=priority
            )
            
            self.service_requests[request_id] = request
            
            # Find potential providers
            providers = await self.find_service_providers(
                service_type=service_type,
                required_expertise=required_expertise,
                required_specializations=required_specializations,
                max_results=self.config["max_matches_per_request"] * 2,  # Get more for better matching
                min_quality_score=min_quality_score,
                exclude_agents=excluded_agents
            )
            
            # Create matches
            matches = []
            for provider in providers:
                match = await self._create_service_match(request, provider)
                if match and match.compatibility_score >= self.config["min_compatibility_score"]:
                    matches.append(match)
            
            # Sort matches by overall score
            matches.sort(key=lambda m: m.calculate_overall_match_score(), reverse=True)
            
            # Limit results
            matches = matches[:self.config["max_matches_per_request"]]
            
            # Store matches
            self.service_matches[request_id] = matches
            
            # Update statistics
            self.stats["total_requests"] += 1
            if matches:
                self.stats["successful_matches"] += 1
                match_scores = [match.calculate_overall_match_score() for match in matches]
                avg_score = sum(match_scores) / len(match_scores)
                
                if self.stats["average_match_score"] == 0:
                    self.stats["average_match_score"] = avg_score
                else:
                    total_requests = self.stats["total_requests"]
                    self.stats["average_match_score"] = (
                        (self.stats["average_match_score"] * (total_requests - 1) + avg_score) / 
                        total_requests
                    )
            
            log_agent_event(
                self.agent_id,
                "service_request_matched",
                {
                    "request_id": request_id,
                    "service_type": service_type.value,
                    "matches_found": len(matches),
                    "top_match_score": matches[0].calculate_overall_match_score() if matches else 0
                }
            )
            
            self.logger.info(f"Service request matched: {request_id} ({len(matches)} matches)")
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Failed to match service request: {e}")
            return []
    
    async def update_capability_performance(
        self,
        capability_id: str,
        success: bool,
        completion_time: float,
        quality_score: float,
        rating: Optional[float] = None
    ) -> bool:
        """Update capability performance metrics."""
        try:
            if capability_id not in self.capabilities:
                return False
            
            capability = self.capabilities[capability_id]
            capability.update_performance_metrics(success, completion_time, quality_score, rating)
            
            # Auto-update expertise level if enabled
            if self.config["auto_update_expertise"]:
                await self._maybe_update_expertise_level(capability)
            
            log_agent_event(
                capability.agent_id,
                "capability_performance_updated",
                {
                    "capability_id": capability_id,
                    "success": success,
                    "quality_score": quality_score,
                    "new_overall_score": capability.calculate_overall_score()
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update capability performance: {e}")
            return False
    
    async def get_agent_capabilities(self, agent_id: str) -> List[ServiceCapability]:
        """Get all capabilities for a specific agent."""
        try:
            capability_ids = self.agent_capabilities.get(agent_id, [])
            return [self.capabilities[cap_id] for cap_id in capability_ids if cap_id in self.capabilities]
        except Exception as e:
            self.logger.error(f"Failed to get agent capabilities: {e}")
            return []
    
    async def get_capability_statistics(self, capability_id: str) -> Dict[str, Any]:
        """Get detailed statistics for a capability."""
        try:
            if capability_id not in self.capabilities:
                return {}
            
            capability = self.capabilities[capability_id]
            
            return {
                "capability_id": capability_id,
                "agent_id": capability.agent_id,
                "service_type": capability.service_type.value,
                "expertise_level": capability.expertise_level.value,
                "overall_score": capability.calculate_overall_score(),
                "success_rate": capability.success_rate,
                "average_completion_time": capability.average_completion_time,
                "quality_score": capability.quality_score,
                "reliability_score": capability.reliability_score,
                "total_requests": capability.total_requests,
                "completed_requests": capability.completed_requests,
                "failed_requests": capability.failed_requests,
                "average_rating": capability.average_rating,
                "current_load": capability.current_load,
                "max_concurrent_tasks": capability.max_concurrent_tasks,
                "availability": capability.is_available(),
                "last_used": capability.last_used.isoformat() if capability.last_used else None,
                "specializations": capability.specializations
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get capability statistics: {e}")
            return {}
    
    async def get_service_statistics(self, service_type: ServiceType) -> Dict[str, Any]:
        """Get statistics for a specific service type."""
        try:
            capability_ids = self.capabilities_by_service.get(service_type, [])
            capabilities = [self.capabilities[cap_id] for cap_id in capability_ids]
            active_capabilities = [cap for cap in capabilities if cap.status == CapabilityStatus.ACTIVE]
            
            if not active_capabilities:
                return {
                    "service_type": service_type.value,
                    "total_providers": 0,
                    "active_providers": 0,
                    "average_quality": 0.0,
                    "average_success_rate": 0.0,
                    "total_requests": 0
                }
            
            # Calculate aggregated statistics
            total_requests = sum(cap.total_requests for cap in active_capabilities)
            avg_quality = sum(cap.quality_score for cap in active_capabilities) / len(active_capabilities)
            avg_success_rate = sum(cap.success_rate for cap in active_capabilities) / len(active_capabilities)
            
            # Group by expertise level
            expertise_distribution = {}
            for level in ExpertiseLevel:
                count = len([cap for cap in active_capabilities if cap.expertise_level == level])
                expertise_distribution[level.value] = count
            
            return {
                "service_type": service_type.value,
                "total_providers": len(capabilities),
                "active_providers": len(active_capabilities),
                "average_quality": avg_quality,
                "average_success_rate": avg_success_rate,
                "total_requests": total_requests,
                "expertise_distribution": expertise_distribution,
                "top_providers": [
                    {
                        "agent_id": cap.agent_id,
                        "name": cap.name,
                        "overall_score": cap.calculate_overall_score(),
                        "expertise_level": cap.expertise_level.value
                    }
                    for cap in sorted(active_capabilities, key=lambda c: c.calculate_overall_score(), reverse=True)[:5]
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get service statistics: {e}")
            return {}
    
    async def _create_service_match(
        self,
        request: ServiceRequest,
        capability: ServiceCapability
    ) -> Optional[ServiceMatch]:
        """Create a service match between a request and capability."""
        try:
            # Calculate compatibility score
            compatibility_score = await self._calculate_compatibility_score(request, capability)
            
            # Calculate confidence score
            confidence_score = await self._calculate_confidence_score(request, capability)
            
            # Estimate completion time and quality
            estimated_completion_time = capability.average_completion_time or 3600  # Default 1 hour
            estimated_quality = capability.quality_score
            
            # Check expertise match
            expertise_order = list(ExpertiseLevel)
            required_index = expertise_order.index(request.required_expertise)
            capability_index = expertise_order.index(capability.expertise_level)
            expertise_match = capability_index >= required_index
            
            # Find matching specializations
            matching_specializations = []
            if request.required_specializations:
                matching_specializations = [
                    spec for spec in request.required_specializations 
                    if spec in capability.specializations
                ]
            
            # Create match
            self.match_counter += 1
            match_id = f"match_{self.match_counter}_{datetime.now().timestamp()}"
            
            match = ServiceMatch(
                match_id=match_id,
                request_id=request.request_id,
                capability_id=capability.capability_id,
                agent_id=capability.agent_id,
                compatibility_score=compatibility_score,
                confidence_score=confidence_score,
                estimated_completion_time=estimated_completion_time,
                estimated_quality=estimated_quality,
                matching_specializations=matching_specializations,
                expertise_match=expertise_match,
                availability_confirmed=capability.is_available(),
                agent_reputation=capability.calculate_overall_score(),
                past_performance=capability.success_rate,
                current_workload=capability.current_load / max(capability.max_concurrent_tasks, 1)
            )
            
            return match
            
        except Exception as e:
            self.logger.error(f"Failed to create service match: {e}")
            return None
    
    async def _calculate_compatibility_score(
        self,
        request: ServiceRequest,
        capability: ServiceCapability
    ) -> float:
        """Calculate compatibility score between request and capability."""
        try:
            score = 0.0
            
            # Service type match (required)
            if request.service_type == capability.service_type:
                score += 0.4
            else:
                return 0.0  # No match if service types don't align
            
            # Expertise level match
            expertise_order = list(ExpertiseLevel)
            required_index = expertise_order.index(request.required_expertise)
            capability_index = expertise_order.index(capability.expertise_level)
            
            if capability_index >= required_index:
                # Higher expertise is better, but with diminishing returns
                expertise_bonus = min(0.3, 0.1 + (capability_index - required_index) * 0.05)
                score += expertise_bonus
            else:
                # Penalize insufficient expertise
                score -= 0.2
            
            # Specialization match
            if request.required_specializations:
                matching_specs = len([
                    spec for spec in request.required_specializations 
                    if spec in capability.specializations
                ])
                spec_score = matching_specs / len(request.required_specializations)
                score += spec_score * 0.2
            else:
                score += 0.1  # Small bonus for no specific requirements
            
            # Quality requirement match
            if capability.quality_score >= request.min_quality_score:
                quality_bonus = min(0.1, (capability.quality_score - request.min_quality_score) * 0.2)
                score += quality_bonus
            else:
                score -= 0.1
            
            # Completion time requirement
            if request.max_completion_time and capability.average_completion_time > 0:
                if capability.average_completion_time <= request.max_completion_time:
                    score += 0.1
                else:
                    time_penalty = min(0.2, (capability.average_completion_time - request.max_completion_time) / request.max_completion_time)
                    score -= time_penalty
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate compatibility score: {e}")
            return 0.0
    
    async def _calculate_confidence_score(
        self,
        request: ServiceRequest,
        capability: ServiceCapability
    ) -> float:
        """Calculate confidence score for the match."""
        try:
            # Base confidence on historical performance
            base_confidence = capability.reliability_score
            
            # Adjust based on request complexity (simplified)
            complexity_factor = 1.0
            if len(request.description) > 500:  # Long description = complex request
                complexity_factor = 0.9
            elif len(request.description) < 100:  # Short description = simple request
                complexity_factor = 1.1
            
            # Adjust based on agent experience
            experience_factor = min(1.2, 1.0 + (capability.total_requests / 100))
            
            # Adjust based on current workload
            workload_factor = 1.0 - (capability.current_load / max(capability.max_concurrent_tasks, 1)) * 0.2
            
            confidence = base_confidence * complexity_factor * experience_factor * workload_factor
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate confidence score: {e}")
            return 0.5
    
    async def _maybe_update_expertise_level(self, capability: ServiceCapability) -> None:
        """Maybe update expertise level based on performance."""
        try:
            if capability.total_requests < 10:  # Need minimum experience
                return
            
            current_score = capability.calculate_overall_score()
            current_level = capability.expertise_level
            expertise_order = list(ExpertiseLevel)
            current_index = expertise_order.index(current_level)
            
            # Check for promotion
            if (current_score >= self.config["expertise_promotion_threshold"] and 
                current_index < len(expertise_order) - 1):
                
                new_level = expertise_order[current_index + 1]
                await self.update_capability(capability.capability_id, expertise_level=new_level)
                
                log_agent_event(
                    capability.agent_id,
                    "expertise_promoted",
                    {
                        "capability_id": capability.capability_id,
                        "old_level": current_level.value,
                        "new_level": new_level.value,
                        "performance_score": current_score
                    }
                )
            
            # Check for demotion
            elif (current_score <= self.config["expertise_demotion_threshold"] and 
                  current_index > 0):
                
                new_level = expertise_order[current_index - 1]
                await self.update_capability(capability.capability_id, expertise_level=new_level)
                
                log_agent_event(
                    capability.agent_id,
                    "expertise_demoted",
                    {
                        "capability_id": capability.capability_id,
                        "old_level": current_level.value,
                        "new_level": new_level.value,
                        "performance_score": current_score
                    }
                )
        
        except Exception as e:
            self.logger.error(f"Failed to update expertise level: {e}")
    
    async def _update_statistics(self) -> None:
        """Update registry statistics."""
        while True:
            try:
                # Update active capabilities count
                active_count = sum(
                    1 for cap in self.capabilities.values() 
                    if cap.status == CapabilityStatus.ACTIVE
                )
                self.stats["active_capabilities"] = active_count
                
                # Update agent count
                unique_agents = set(cap.agent_id for cap in self.capabilities.values())
                self.stats["agent_count"] = len(unique_agents)
                
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_expired_data(self) -> None:
        """Clean up expired capabilities and old requests."""
        while True:
            try:
                now = datetime.now()
                expiry_threshold = now - timedelta(days=self.config["capability_expiry_days"])
                
                # Find expired capabilities
                expired_capabilities = [
                    cap_id for cap_id, cap in self.capabilities.items()
                    if (cap.last_used and cap.last_used < expiry_threshold and 
                        cap.status == CapabilityStatus.INACTIVE)
                ]
                
                # Remove expired capabilities
                for cap_id in expired_capabilities:
                    capability = self.capabilities[cap_id]
                    
                    # Remove from indexes
                    self.capabilities_by_service[capability.service_type].remove(cap_id)
                    self.capabilities_by_expertise[capability.expertise_level].remove(cap_id)
                    self.agent_capabilities[capability.agent_id].remove(cap_id)
                    
                    # Remove capability
                    del self.capabilities[cap_id]
                    
                    self.stats["total_capabilities"] -= 1
                
                if expired_capabilities:
                    self.logger.info(f"Cleaned up {len(expired_capabilities)} expired capabilities")
                
                # Clean up old service requests (keep for 7 days)
                request_expiry = now - timedelta(days=7)
                expired_requests = [
                    req_id for req_id, req in self.service_requests.items()
                    if req.created_at < request_expiry
                ]
                
                for req_id in expired_requests:
                    del self.service_requests[req_id]
                    if req_id in self.service_matches:
                        del self.service_matches[req_id]
                
                if expired_requests:
                    self.logger.info(f"Cleaned up {len(expired_requests)} old service requests")
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def _auto_update_expertise_levels(self) -> None:
        """Automatically update expertise levels based on performance."""
        while True:
            try:
                if not self.config["auto_update_expertise"]:
                    await asyncio.sleep(3600)
                    continue
                
                # Check all capabilities for expertise updates
                for capability in self.capabilities.values():
                    if capability.status == CapabilityStatus.ACTIVE:
                        await self._maybe_update_expertise_level(capability)
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in auto expertise update: {e}")
                await asyncio.sleep(3600)