"""
Reproduction decision-making system for autonomous AI agents.

This module implements compatibility assessment, reproduction motivation,
and decision-making for agent reproduction and child-rearing behavior.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .genetics import GeneticAlgorithm, GeneticProfile, ReproductionParameters
from .social_manager import SocialManager
from .status_manager import StatusManager
from .emotions import EmotionEngine


class ReproductionReadiness(Enum):
    """Readiness levels for reproduction."""
    NOT_READY = "not_ready"
    CONSIDERING = "considering"
    READY = "ready"
    EAGER = "eager"
    DESPERATE = "desperate"


class CompatibilityFactor(Enum):
    """Factors affecting reproduction compatibility."""
    GENETIC_DIVERSITY = "genetic_diversity"
    SOCIAL_COMPATIBILITY = "social_compatibility"
    STATUS_COMPATIBILITY = "status_compatibility"
    EMOTIONAL_COMPATIBILITY = "emotional_compatibility"
    PERSONALITY_MATCH = "personality_match"
    SHARED_GOALS = "shared_goals"
    MUTUAL_RESPECT = "mutual_respect"


@dataclass
class ReproductionDesire:
    """Represents an agent's desire to reproduce."""
    agent_id: str
    readiness_level: ReproductionReadiness
    motivation_score: float  # 0.0 to 1.0
    preferred_partners: List[str] = field(default_factory=list)
    partner_requirements: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    reproduction_history: List[str] = field(default_factory=list)  # offspring IDs
    cooldown_until: Optional[datetime] = None


@dataclass
class CompatibilityAssessment:
    """Assessment of compatibility between potential partners."""
    agent1_id: str
    agent2_id: str
    overall_compatibility: float  # 0.0 to 1.0
    factor_scores: Dict[CompatibilityFactor, float]
    genetic_distance: float
    social_relationship_strength: float
    status_difference: float
    personality_harmony: float
    mutual_attraction: float
    reproduction_potential: float
    assessment_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReproductionProposal:
    """Proposal for reproduction between two agents."""
    proposal_id: str
    proposer_id: str
    target_id: str
    compatibility_score: float
    motivation_level: float
    proposal_timestamp: datetime
    response_deadline: datetime
    status: str = "pending"  # pending, accepted, rejected, expired
    response_timestamp: Optional[datetime] = None
    rejection_reason: Optional[str] = None


@dataclass
class ChildRearingPlan:
    """Plan for raising offspring."""
    child_id: str
    parent1_id: str
    parent2_id: str
    primary_caregiver: str
    secondary_caregiver: str
    rearing_responsibilities: Dict[str, str]
    development_goals: List[str]
    mentorship_plan: Dict[str, Any]
    resource_allocation: Dict[str, float]
    milestone_tracking: Dict[str, Any] = field(default_factory=dict)


class ReproductionManager(AgentModule):
    """
    Reproduction decision-making system that manages compatibility assessment,
    reproduction motivation, and child-rearing behavior.
    """
    
    def __init__(
        self,
        agent_id: str,
        genetic_algorithm: GeneticAlgorithm,
        social_manager: SocialManager,
        status_manager: StatusManager,
        emotion_engine: EmotionEngine
    ):
        super().__init__(agent_id)
        self.genetic_algorithm = genetic_algorithm
        self.social_manager = social_manager
        self.status_manager = status_manager
        self.emotion_engine = emotion_engine
        self.logger = get_agent_logger(agent_id, "reproduction_manager")
        
        # Reproduction state tracking
        self.reproduction_desires: Dict[str, ReproductionDesire] = {}
        self.compatibility_cache: Dict[Tuple[str, str], CompatibilityAssessment] = {}
        self.active_proposals: Dict[str, ReproductionProposal] = {}
        self.child_rearing_plans: Dict[str, ChildRearingPlan] = {}
        
        # Reproduction parameters
        self.reproduction_config = {
            "min_age_for_reproduction": 24.0,  # hours
            "max_reproduction_frequency": 168.0,  # hours (1 week)
            "compatibility_threshold": 0.6,
            "motivation_threshold": 0.7,
            "proposal_timeout_hours": 24.0,
            "genetic_diversity_weight": 0.3,
            "social_compatibility_weight": 0.25,
            "status_compatibility_weight": 0.2,
            "emotional_compatibility_weight": 0.15,
            "personality_match_weight": 0.1
        }
        
        # Child-rearing parameters
        self.child_rearing_config = {
            "mentorship_duration_hours": 168.0,  # 1 week
            "primary_caregiver_responsibility": 0.6,
            "secondary_caregiver_responsibility": 0.4,
            "development_check_interval_hours": 24.0,
            "independence_threshold": 0.8
        }
        
        # Statistics
        self.reproduction_stats = {
            "total_proposals": 0,
            "accepted_proposals": 0,
            "rejected_proposals": 0,
            "successful_reproductions": 0,
            "children_raised": 0,
            "average_compatibility": 0.0,
            "reproduction_rate": 0.0
        }
        
        self.logger.info(f"Reproduction manager initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the reproduction manager."""
        try:
            # Load existing reproduction data
            await self._load_reproduction_data()
            
            self.logger.info("Reproduction manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize reproduction manager: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the reproduction manager gracefully."""
        try:
            # Save reproduction data
            await self._save_reproduction_data()
            
            # Complete any active child-rearing
            await self._complete_active_child_rearing()
            
            self.logger.info("Reproduction manager shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during reproduction manager shutdown: {e}")
    
    async def assess_reproduction_readiness(self, agent_id: str) -> ReproductionDesire:
        """Assess an agent's readiness and desire to reproduce."""
        try:
            # Get agent information
            agent_status = self.status_manager.get_agent_status(agent_id)
            social_profile = self.social_manager.get_agent_social_profile(agent_id)
            genetic_profile = self.genetic_algorithm.genetic_profiles.get(agent_id)
            
            if not genetic_profile:
                return ReproductionDesire(
                    agent_id=agent_id,
                    readiness_level=ReproductionReadiness.NOT_READY,
                    motivation_score=0.0
                )
            
            # Calculate motivation factors
            motivation_factors = await self._calculate_motivation_factors(
                agent_id, agent_status, social_profile, genetic_profile
            )
            
            # Determine overall motivation
            motivation_score = sum(motivation_factors.values()) / len(motivation_factors)
            
            # Determine readiness level
            readiness_level = self._determine_readiness_level(motivation_score, agent_status)
            
            # Generate partner requirements
            partner_requirements = self._generate_partner_requirements(genetic_profile, agent_status)
            
            # Find preferred partners
            preferred_partners = await self._find_preferred_partners(agent_id, partner_requirements)
            
            # Create or update reproduction desire
            desire = ReproductionDesire(
                agent_id=agent_id,
                readiness_level=readiness_level,
                motivation_score=motivation_score,
                preferred_partners=preferred_partners,
                partner_requirements=partner_requirements,
                reproduction_history=self._get_reproduction_history(agent_id)
            )
            
            # Check cooldown
            if self._is_in_reproduction_cooldown(agent_id):
                desire.readiness_level = ReproductionReadiness.NOT_READY
                desire.cooldown_until = self._get_cooldown_end_time(agent_id)
            
            self.reproduction_desires[agent_id] = desire
            
            log_agent_event(
                self.agent_id,
                "reproduction_readiness_assessed",
                {
                    "agent_id": agent_id,
                    "readiness_level": readiness_level.value,
                    "motivation_score": motivation_score,
                    "preferred_partners_count": len(preferred_partners)
                }
            )
            
            return desire
            
        except Exception as e:
            self.logger.error(f"Failed to assess reproduction readiness: {e}")
            return ReproductionDesire(
                agent_id=agent_id,
                readiness_level=ReproductionReadiness.NOT_READY,
                motivation_score=0.0
            )
    
    async def assess_compatibility(self, agent1_id: str, agent2_id: str) -> CompatibilityAssessment:
        """Assess compatibility between two potential partners."""
        try:
            # Check cache first
            cache_key = (min(agent1_id, agent2_id), max(agent1_id, agent2_id))
            if cache_key in self.compatibility_cache:
                cached = self.compatibility_cache[cache_key]
                # Use cache if recent (within 24 hours)
                if datetime.now() - cached.assessment_timestamp < timedelta(hours=24):
                    return cached
            
            # Get agent information
            genetic1 = self.genetic_algorithm.genetic_profiles.get(agent1_id)
            genetic2 = self.genetic_algorithm.genetic_profiles.get(agent2_id)
            
            if not genetic1 or not genetic2:
                return CompatibilityAssessment(
                    agent1_id=agent1_id,
                    agent2_id=agent2_id,
                    overall_compatibility=0.0,
                    factor_scores={},
                    genetic_distance=0.0,
                    social_relationship_strength=0.0,
                    status_difference=1.0,
                    personality_harmony=0.0,
                    mutual_attraction=0.0,
                    reproduction_potential=0.0
                )
            
            # Calculate compatibility factors
            factor_scores = {}
            
            # Genetic diversity (higher genetic distance is better)
            genetic_distance = self.genetic_algorithm._calculate_genetic_distance(genetic1, genetic2)
            factor_scores[CompatibilityFactor.GENETIC_DIVERSITY] = genetic_distance
            
            # Social compatibility
            relationship = await self.social_manager.get_relationship(agent1_id, agent2_id)
            social_score = 0.5  # Default neutral
            if relationship:
                social_score = (relationship.strength + relationship.trust_level + relationship.respect_level) / 3.0
            factor_scores[CompatibilityFactor.SOCIAL_COMPATIBILITY] = social_score
            
            # Status compatibility (similar status is better)
            status1 = self.status_manager.get_agent_status(agent1_id)
            status2 = self.status_manager.get_agent_status(agent2_id)
            status_score = self._calculate_status_compatibility(status1, status2)
            factor_scores[CompatibilityFactor.STATUS_COMPATIBILITY] = status_score
            
            # Emotional compatibility
            emotional_score = await self._calculate_emotional_compatibility(agent1_id, agent2_id)
            factor_scores[CompatibilityFactor.EMOTIONAL_COMPATIBILITY] = emotional_score
            
            # Personality match
            personality_score = self._calculate_personality_harmony(genetic1, genetic2)
            factor_scores[CompatibilityFactor.PERSONALITY_MATCH] = personality_score
            
            # Calculate overall compatibility
            overall_compatibility = (
                factor_scores[CompatibilityFactor.GENETIC_DIVERSITY] * self.reproduction_config["genetic_diversity_weight"] +
                factor_scores[CompatibilityFactor.SOCIAL_COMPATIBILITY] * self.reproduction_config["social_compatibility_weight"] +
                factor_scores[CompatibilityFactor.STATUS_COMPATIBILITY] * self.reproduction_config["status_compatibility_weight"] +
                factor_scores[CompatibilityFactor.EMOTIONAL_COMPATIBILITY] * self.reproduction_config["emotional_compatibility_weight"] +
                factor_scores[CompatibilityFactor.PERSONALITY_MATCH] * self.reproduction_config["personality_match_weight"]
            )
            
            # Calculate mutual attraction (simplified)
            mutual_attraction = (social_score + emotional_score) / 2.0
            
            # Calculate reproduction potential
            reproduction_potential = min(genetic1.genetic_fitness, genetic2.genetic_fitness) * overall_compatibility
            
            # Create assessment
            assessment = CompatibilityAssessment(
                agent1_id=agent1_id,
                agent2_id=agent2_id,
                overall_compatibility=overall_compatibility,
                factor_scores=factor_scores,
                genetic_distance=genetic_distance,
                social_relationship_strength=social_score,
                status_difference=1.0 - status_score,  # Invert for difference
                personality_harmony=personality_score,
                mutual_attraction=mutual_attraction,
                reproduction_potential=reproduction_potential
            )
            
            # Cache assessment
            self.compatibility_cache[cache_key] = assessment
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"Failed to assess compatibility: {e}")
            return CompatibilityAssessment(
                agent1_id=agent1_id,
                agent2_id=agent2_id,
                overall_compatibility=0.0,
                factor_scores={},
                genetic_distance=0.0,
                social_relationship_strength=0.0,
                status_difference=1.0,
                personality_harmony=0.0,
                mutual_attraction=0.0,
                reproduction_potential=0.0
            )    

    async def propose_reproduction(self, proposer_id: str, target_id: str) -> str:
        """Propose reproduction to another agent."""
        try:
            # Check if proposer is ready
            proposer_desire = await self.assess_reproduction_readiness(proposer_id)
            if proposer_desire.readiness_level == ReproductionReadiness.NOT_READY:
                raise ValueError("Proposer is not ready for reproduction")
            
            # Assess compatibility
            compatibility = await self.assess_compatibility(proposer_id, target_id)
            if compatibility.overall_compatibility < self.reproduction_config["compatibility_threshold"]:
                raise ValueError(f"Compatibility too low: {compatibility.overall_compatibility:.2f}")
            
            # Create proposal
            proposal_id = f"repro_proposal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{proposer_id}_{target_id}"
            
            proposal = ReproductionProposal(
                proposal_id=proposal_id,
                proposer_id=proposer_id,
                target_id=target_id,
                compatibility_score=compatibility.overall_compatibility,
                motivation_level=proposer_desire.motivation_score,
                proposal_timestamp=datetime.now(),
                response_deadline=datetime.now() + timedelta(hours=self.reproduction_config["proposal_timeout_hours"])
            )
            
            self.active_proposals[proposal_id] = proposal
            
            # Update statistics
            self.reproduction_stats["total_proposals"] += 1
            
            log_agent_event(
                self.agent_id,
                "reproduction_proposed",
                {
                    "proposal_id": proposal_id,
                    "proposer": proposer_id,
                    "target": target_id,
                    "compatibility": compatibility.overall_compatibility,
                    "motivation": proposer_desire.motivation_score
                }
            )
            
            self.logger.info(f"Reproduction proposed: {proposer_id} -> {target_id} (compatibility: {compatibility.overall_compatibility:.2f})")
            
            return proposal_id
            
        except Exception as e:
            self.logger.error(f"Failed to propose reproduction: {e}")
            raise
    
    async def respond_to_proposal(self, proposal_id: str, accept: bool, reason: str = "") -> bool:
        """Respond to a reproduction proposal."""
        try:
            if proposal_id not in self.active_proposals:
                raise ValueError("Proposal not found")
            
            proposal = self.active_proposals[proposal_id]
            
            # Check if proposal is still valid
            if datetime.now() > proposal.response_deadline:
                proposal.status = "expired"
                return False
            
            # Update proposal
            proposal.response_timestamp = datetime.now()
            
            if accept:
                proposal.status = "accepted"
                
                # Assess target's readiness
                target_desire = await self.assess_reproduction_readiness(proposal.target_id)
                if target_desire.readiness_level == ReproductionReadiness.NOT_READY:
                    proposal.status = "rejected"
                    proposal.rejection_reason = "Target not ready for reproduction"
                    accept = False
                else:
                    # Proceed with reproduction
                    success = await self._execute_reproduction(proposal)
                    if success:
                        self.reproduction_stats["accepted_proposals"] += 1
                        self.reproduction_stats["successful_reproductions"] += 1
                    else:
                        proposal.status = "failed"
                        accept = False
            else:
                proposal.status = "rejected"
                proposal.rejection_reason = reason
                self.reproduction_stats["rejected_proposals"] += 1
            
            # Remove from active proposals
            del self.active_proposals[proposal_id]
            
            log_agent_event(
                self.agent_id,
                "reproduction_proposal_responded",
                {
                    "proposal_id": proposal_id,
                    "accepted": accept,
                    "reason": reason,
                    "final_status": proposal.status
                }
            )
            
            return accept
            
        except Exception as e:
            self.logger.error(f"Failed to respond to proposal: {e}")
            return False
    
    async def create_child_rearing_plan(
        self,
        child_id: str,
        parent1_id: str,
        parent2_id: str
    ) -> ChildRearingPlan:
        """Create a plan for raising offspring."""
        try:
            # Determine primary caregiver based on various factors
            primary_caregiver = await self._determine_primary_caregiver(parent1_id, parent2_id)
            secondary_caregiver = parent2_id if primary_caregiver == parent1_id else parent1_id
            
            # Define rearing responsibilities
            responsibilities = {
                "emotional_development": primary_caregiver,
                "skill_training": secondary_caregiver,
                "social_integration": primary_caregiver,
                "knowledge_transfer": secondary_caregiver,
                "safety_monitoring": primary_caregiver,
                "independence_training": secondary_caregiver
            }
            
            # Set development goals based on parent traits
            development_goals = await self._generate_development_goals(child_id, parent1_id, parent2_id)
            
            # Create mentorship plan
            mentorship_plan = {
                "duration_hours": self.child_rearing_config["mentorship_duration_hours"],
                "check_intervals": self.child_rearing_config["development_check_interval_hours"],
                "milestones": self._generate_development_milestones(),
                "learning_objectives": development_goals
            }
            
            # Allocate resources
            resource_allocation = {
                "time_commitment": {
                    primary_caregiver: self.child_rearing_config["primary_caregiver_responsibility"],
                    secondary_caregiver: self.child_rearing_config["secondary_caregiver_responsibility"]
                },
                "knowledge_sharing": 0.8,
                "emotional_support": 0.9,
                "skill_development": 0.7
            }
            
            # Create plan
            plan = ChildRearingPlan(
                child_id=child_id,
                parent1_id=parent1_id,
                parent2_id=parent2_id,
                primary_caregiver=primary_caregiver,
                secondary_caregiver=secondary_caregiver,
                rearing_responsibilities=responsibilities,
                development_goals=development_goals,
                mentorship_plan=mentorship_plan,
                resource_allocation=resource_allocation
            )
            
            self.child_rearing_plans[child_id] = plan
            
            # Update statistics
            self.reproduction_stats["children_raised"] += 1
            
            log_agent_event(
                self.agent_id,
                "child_rearing_plan_created",
                {
                    "child_id": child_id,
                    "parent1": parent1_id,
                    "parent2": parent2_id,
                    "primary_caregiver": primary_caregiver,
                    "development_goals_count": len(development_goals)
                }
            )
            
            self.logger.info(f"Created child-rearing plan for {child_id}")
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Failed to create child-rearing plan: {e}")
            raise
    
    async def monitor_child_development(self, child_id: str) -> Dict[str, Any]:
        """Monitor the development of a child agent."""
        try:
            if child_id not in self.child_rearing_plans:
                return {"error": "Child-rearing plan not found"}
            
            plan = self.child_rearing_plans[child_id]
            
            # Get child's current status
            child_genetic_profile = self.genetic_algorithm.genetic_profiles.get(child_id)
            child_status = self.status_manager.get_agent_status(child_id)
            child_social_profile = self.social_manager.get_agent_social_profile(child_id)
            
            if not child_genetic_profile:
                return {"error": "Child genetic profile not found"}
            
            # Assess development progress
            development_progress = {}
            
            # Skill development progress
            for goal in plan.development_goals:
                progress = self._assess_goal_progress(child_id, goal, child_status, child_genetic_profile)
                development_progress[goal] = progress
            
            # Overall development score
            overall_progress = sum(development_progress.values()) / len(development_progress) if development_progress else 0.0
            
            # Check for independence
            independence_score = self._calculate_independence_score(child_genetic_profile, child_status, child_social_profile)
            is_independent = independence_score >= self.child_rearing_config["independence_threshold"]
            
            # Update milestone tracking
            plan.milestone_tracking.update({
                "last_assessment": datetime.now().isoformat(),
                "development_progress": development_progress,
                "overall_progress": overall_progress,
                "independence_score": independence_score,
                "is_independent": is_independent
            })
            
            # Generate recommendations
            recommendations = self._generate_development_recommendations(
                plan, development_progress, independence_score
            )
            
            result = {
                "child_id": child_id,
                "overall_progress": overall_progress,
                "development_progress": development_progress,
                "independence_score": independence_score,
                "is_independent": is_independent,
                "recommendations": recommendations,
                "caregivers": {
                    "primary": plan.primary_caregiver,
                    "secondary": plan.secondary_caregiver
                }
            }
            
            log_agent_event(
                self.agent_id,
                "child_development_monitored",
                {
                    "child_id": child_id,
                    "overall_progress": overall_progress,
                    "independence_score": independence_score,
                    "is_independent": is_independent
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to monitor child development: {e}")
            return {"error": str(e)}
    
    def get_reproduction_statistics(self) -> Dict[str, Any]:
        """Get reproduction system statistics."""
        return {
            **self.reproduction_stats,
            "active_proposals": len(self.active_proposals),
            "active_child_rearing": len(self.child_rearing_plans),
            "agents_with_desires": len(self.reproduction_desires),
            "compatibility_cache_size": len(self.compatibility_cache)
        }
    
    def get_agent_reproduction_profile(self, agent_id: str) -> Dict[str, Any]:
        """Get reproduction profile for an agent."""
        try:
            desire = self.reproduction_desires.get(agent_id)
            reproduction_history = self._get_reproduction_history(agent_id)
            
            # Count children being raised
            children_raising = [
                plan.child_id for plan in self.child_rearing_plans.values()
                if plan.parent1_id == agent_id or plan.parent2_id == agent_id
            ]
            
            profile = {
                "agent_id": agent_id,
                "current_readiness": desire.readiness_level.value if desire else "unknown",
                "motivation_score": desire.motivation_score if desire else 0.0,
                "preferred_partners": desire.preferred_partners if desire else [],
                "reproduction_history": reproduction_history,
                "children_count": len(reproduction_history),
                "currently_raising": children_raising,
                "is_in_cooldown": self._is_in_reproduction_cooldown(agent_id)
            }
            
            if desire and desire.cooldown_until:
                profile["cooldown_until"] = desire.cooldown_until.isoformat()
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to get reproduction profile: {e}")
            return {"agent_id": agent_id, "error": str(e)} 
   
    # Private helper methods
    
    async def _calculate_motivation_factors(
        self,
        agent_id: str,
        agent_status: Dict[str, Any],
        social_profile: Dict[str, Any],
        genetic_profile: GeneticProfile
    ) -> Dict[str, float]:
        """Calculate factors affecting reproduction motivation."""
        try:
            factors = {}
            
            # Age factor (mature agents more likely to reproduce)
            age_hours = (datetime.now().timestamp() - genetic_profile.generation * 24) / 3600
            age_factor = min(1.0, max(0.0, (age_hours - 24) / 168))  # Peaks at 1 week old
            factors["age_readiness"] = age_factor
            
            # Status factor (higher status agents more motivated)
            if "hierarchy_position" in agent_status and agent_status["hierarchy_position"]:
                hierarchy_level = agent_status["hierarchy_position"].get("hierarchy_level", 10)
                status_factor = max(0.0, 1.0 - (hierarchy_level - 1) / 10.0)
            else:
                status_factor = 0.3
            factors["status_motivation"] = status_factor
            
            # Social factor (well-connected agents more motivated)
            network_connections = social_profile.get("network_connections", 0)
            social_factor = min(1.0, network_connections / 10.0)
            factors["social_readiness"] = social_factor
            
            # Genetic fitness factor
            fitness_factor = genetic_profile.genetic_fitness
            factors["genetic_fitness"] = fitness_factor
            
            # Emotional factor (get from emotion engine)
            emotional_state = self.emotion_engine.get_current_emotional_state()
            happiness = emotional_state.get("happiness", 0.5)
            motivation = emotional_state.get("motivation", 0.5)
            emotional_factor = (happiness + motivation) / 2.0
            factors["emotional_readiness"] = emotional_factor
            
            # Loneliness factor (agents without close relationships more motivated)
            close_relationships = social_profile.get("relationship_summary", {})
            friend_count = close_relationships.get("friend", 0) + close_relationships.get("ally", 0)
            loneliness_factor = max(0.0, 1.0 - friend_count / 5.0)
            factors["loneliness_motivation"] = loneliness_factor
            
            # Legacy factor (agents want to pass on their traits)
            reproduction_history = self._get_reproduction_history(agent_id)
            legacy_factor = max(0.0, 1.0 - len(reproduction_history) / 3.0)  # Decreases with more children
            factors["legacy_desire"] = legacy_factor
            
            return factors
            
        except Exception as e:
            self.logger.error(f"Failed to calculate motivation factors: {e}")
            return {"default": 0.5}
    
    def _determine_readiness_level(self, motivation_score: float, agent_status: Dict[str, Any]) -> ReproductionReadiness:
        """Determine readiness level based on motivation score."""
        try:
            if motivation_score < 0.3:
                return ReproductionReadiness.NOT_READY
            elif motivation_score < 0.5:
                return ReproductionReadiness.CONSIDERING
            elif motivation_score < 0.7:
                return ReproductionReadiness.READY
            elif motivation_score < 0.9:
                return ReproductionReadiness.EAGER
            else:
                return ReproductionReadiness.DESPERATE
                
        except Exception:
            return ReproductionReadiness.NOT_READY
    
    def _generate_partner_requirements(
        self,
        genetic_profile: GeneticProfile,
        agent_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate partner requirements based on agent characteristics."""
        try:
            requirements = {}
            
            # Genetic diversity requirement
            requirements["min_genetic_distance"] = 0.3
            requirements["max_genetic_distance"] = 0.8
            
            # Status requirements
            if "hierarchy_position" in agent_status and agent_status["hierarchy_position"]:
                agent_level = agent_status["hierarchy_position"].get("hierarchy_level", 5)
                requirements["max_status_difference"] = 3
                requirements["preferred_status_range"] = (max(1, agent_level - 2), agent_level + 2)
            
            # Fitness requirements
            requirements["min_genetic_fitness"] = max(0.3, genetic_profile.genetic_fitness - 0.2)
            
            # Personality compatibility
            requirements["personality_preferences"] = {
                "complementary_traits": ["openness", "agreeableness"],
                "similar_traits": ["conscientiousness"],
                "avoid_extremes": ["neuroticism"]
            }
            
            # Social requirements
            requirements["min_social_connections"] = 2
            requirements["preferred_relationship_types"] = ["friend", "ally", "collaborator"]
            
            return requirements
            
        except Exception as e:
            self.logger.error(f"Failed to generate partner requirements: {e}")
            return {}
    
    async def _find_preferred_partners(self, agent_id: str, requirements: Dict[str, Any]) -> List[str]:
        """Find preferred partners based on requirements."""
        try:
            preferred_partners = []
            
            # Get all potential partners (exclude self and close relatives)
            all_agents = list(self.genetic_algorithm.genetic_profiles.keys())
            genetic_profile = self.genetic_algorithm.genetic_profiles[agent_id]
            
            potential_partners = [
                other_id for other_id in all_agents
                if other_id != agent_id and other_id not in genetic_profile.lineage
            ]
            
            # Assess each potential partner
            partner_scores = []
            for partner_id in potential_partners:
                compatibility = await self.assess_compatibility(agent_id, partner_id)
                if compatibility.overall_compatibility >= self.reproduction_config["compatibility_threshold"]:
                    partner_scores.append((partner_id, compatibility.overall_compatibility))
            
            # Sort by compatibility and take top candidates
            partner_scores.sort(key=lambda x: x[1], reverse=True)
            preferred_partners = [partner_id for partner_id, _ in partner_scores[:5]]
            
            return preferred_partners
            
        except Exception as e:
            self.logger.error(f"Failed to find preferred partners: {e}")
            return []
    
    def _get_reproduction_history(self, agent_id: str) -> List[str]:
        """Get reproduction history for an agent."""
        try:
            history = []
            for plan in self.child_rearing_plans.values():
                if plan.parent1_id == agent_id or plan.parent2_id == agent_id:
                    history.append(plan.child_id)
            return history
        except Exception:
            return []
    
    def _is_in_reproduction_cooldown(self, agent_id: str) -> bool:
        """Check if agent is in reproduction cooldown."""
        try:
            desire = self.reproduction_desires.get(agent_id)
            if desire and desire.cooldown_until:
                return datetime.now() < desire.cooldown_until
            
            # Check recent reproduction activity
            recent_reproductions = [
                plan for plan in self.child_rearing_plans.values()
                if (plan.parent1_id == agent_id or plan.parent2_id == agent_id)
            ]
            
            if recent_reproductions:
                # Simple cooldown based on max frequency
                return len(recent_reproductions) > 0  # Simplified for now
            
            return False
            
        except Exception:
            return False
    
    def _get_cooldown_end_time(self, agent_id: str) -> Optional[datetime]:
        """Get when reproduction cooldown ends."""
        try:
            desire = self.reproduction_desires.get(agent_id)
            if desire and desire.cooldown_until:
                return desire.cooldown_until
            
            # Calculate based on last reproduction
            recent_plans = [
                plan for plan in self.child_rearing_plans.values()
                if plan.parent1_id == agent_id or plan.parent2_id == agent_id
            ]
            
            if recent_plans:
                # Find most recent
                max(recent_plans, key=lambda p: datetime.fromisoformat(p.milestone_tracking.get("last_assessment", "2000-01-01T00:00:00")))
                return datetime.now() + timedelta(hours=self.reproduction_config["max_reproduction_frequency"])
            
            return None
            
        except Exception:
            return None
    
    def _calculate_status_compatibility(self, status1: Dict[str, Any], status2: Dict[str, Any]) -> float:
        """Calculate status compatibility between two agents."""
        try:
            # Get hierarchy levels
            level1 = 5  # Default
            level2 = 5  # Default
            
            if "hierarchy_position" in status1 and status1["hierarchy_position"]:
                level1 = status1["hierarchy_position"].get("hierarchy_level", 5)
            
            if "hierarchy_position" in status2 and status2["hierarchy_position"]:
                level2 = status2["hierarchy_position"].get("hierarchy_level", 5)
            
            # Calculate compatibility (closer levels are more compatible)
            level_difference = abs(level1 - level2)
            compatibility = max(0.0, 1.0 - level_difference / 10.0)
            
            return compatibility
            
        except Exception:
            return 0.5
    
    async def _calculate_emotional_compatibility(self, agent1_id: str, agent2_id: str) -> float:
        """Calculate emotional compatibility between two agents."""
        try:
            # This would ideally get emotional states from both agents
            # For now, use a simplified approach based on social relationship
            relationship = await self.social_manager.get_relationship(agent1_id, agent2_id)
            
            if relationship:
                # Use trust and respect as proxies for emotional compatibility
                emotional_compatibility = (relationship.trust_level + relationship.respect_level) / 2.0
            else:
                emotional_compatibility = 0.5  # Neutral
            
            return emotional_compatibility
            
        except Exception:
            return 0.5
    
    def _calculate_personality_harmony(self, genetic1: GeneticProfile, genetic2: GeneticProfile) -> float:
        """Calculate personality harmony between two genetic profiles."""
        try:
            personality1 = genetic1.personality_genes
            personality2 = genetic2.personality_genes
            
            harmony_score = 0.0
            trait_count = 0
            
            for trait_name in personality1:
                if trait_name in personality2:
                    value1 = personality1[trait_name]
                    value2 = personality2[trait_name]
                    
                    # Some traits are better when similar, others when complementary
                    if trait_name in ["conscientiousness", "agreeableness"]:
                        # Similar is better
                        harmony = 1.0 - abs(value1 - value2)
                    elif trait_name in ["openness", "extraversion"]:
                        # Complementary can be good
                        similarity = 1.0 - abs(value1 - value2)
                        complementarity = abs(value1 - value2)
                        harmony = max(similarity, complementarity * 0.8)
                    else:  # neuroticism
                        # Lower is generally better for both
                        harmony = 1.0 - max(value1, value2)
                    
                    harmony_score += harmony
                    trait_count += 1
            
            return harmony_score / trait_count if trait_count > 0 else 0.5
            
        except Exception:
            return 0.5
    
    async def _execute_reproduction(self, proposal: ReproductionProposal) -> bool:
        """Execute the reproduction process."""
        try:
            # Create reproduction parameters
            reproduction_params = ReproductionParameters(
                parent1_id=proposal.proposer_id,
                parent2_id=proposal.target_id,
                mutation_rate=0.05,
                crossover_rate=0.7
            )
            
            # Perform genetic reproduction
            offspring_result = self.genetic_algorithm.reproduce_agents(
                proposal.proposer_id,
                proposal.target_id,
                reproduction_params
            )
            
            if not offspring_result.success:
                self.logger.error(f"Genetic reproduction failed: {offspring_result.error_message}")
                return False
            
            # Create child-rearing plan
            await self.create_child_rearing_plan(
                offspring_result.offspring_identity.agent_id,
                proposal.proposer_id,
                proposal.target_id
            )
            
            # Set cooldown for both parents
            cooldown_end = datetime.now() + timedelta(hours=self.reproduction_config["max_reproduction_frequency"])
            
            if proposal.proposer_id in self.reproduction_desires:
                self.reproduction_desires[proposal.proposer_id].cooldown_until = cooldown_end
            
            if proposal.target_id in self.reproduction_desires:
                self.reproduction_desires[proposal.target_id].cooldown_until = cooldown_end
            
            log_agent_event(
                self.agent_id,
                "reproduction_executed",
                {
                    "parent1": proposal.proposer_id,
                    "parent2": proposal.target_id,
                    "child": offspring_result.offspring_identity.agent_id,
                    "fitness_score": offspring_result.fitness_score,
                    "diversity_score": offspring_result.diversity_score
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to execute reproduction: {e}")
            return False
    
    async def _determine_primary_caregiver(self, parent1_id: str, parent2_id: str) -> str:
        """Determine which parent should be the primary caregiver."""
        try:
            # Get parent information
            parent1_status = self.status_manager.get_agent_status(parent1_id)
            parent2_status = self.status_manager.get_agent_status(parent2_id)
            
            parent1_genetic = self.genetic_algorithm.genetic_profiles.get(parent1_id)
            parent2_genetic = self.genetic_algorithm.genetic_profiles.get(parent2_id)
            
            # Factors for determining primary caregiver
            parent1_score = 0.0
            parent2_score = 0.0
            
            # Social ability (better social skills = better caregiver)
            if parent1_genetic:
                parent1_score += parent1_genetic.capability_genes.get("social_ability", 0.5)
            if parent2_genetic:
                parent2_score += parent2_genetic.capability_genes.get("social_ability", 0.5)
            
            # Agreeableness (more agreeable = better caregiver)
            if parent1_genetic:
                parent1_score += parent1_genetic.personality_genes.get("agreeableness", 0.5)
            if parent2_genetic:
                parent2_score += parent2_genetic.personality_genes.get("agreeableness", 0.5)
            
            # Conscientiousness (more conscientious = more reliable caregiver)
            if parent1_genetic:
                parent1_score += parent1_genetic.personality_genes.get("conscientiousness", 0.5)
            if parent2_genetic:
                parent2_score += parent2_genetic.personality_genes.get("conscientiousness", 0.5)
            
            # Status (higher status might have more resources but less time)
            if "hierarchy_position" in parent1_status and parent1_status["hierarchy_position"]:
                level1 = parent1_status["hierarchy_position"].get("hierarchy_level", 5)
                parent1_score += (10 - level1) / 20.0  # Slight preference for lower status (more time)
            
            if "hierarchy_position" in parent2_status and parent2_status["hierarchy_position"]:
                level2 = parent2_status["hierarchy_position"].get("hierarchy_level", 5)
                parent2_score += (10 - level2) / 20.0
            
            # Return the parent with higher score
            return parent1_id if parent1_score >= parent2_score else parent2_id
            
        except Exception as e:
            self.logger.error(f"Failed to determine primary caregiver: {e}")
            return parent1_id  # Default to first parent
    
    async def _generate_development_goals(self, child_id: str, parent1_id: str, parent2_id: str) -> List[str]:
        """Generate development goals for a child based on parent traits."""
        try:
            goals = []
            
            # Get parent genetic profiles
            parent1_genetic = self.genetic_algorithm.genetic_profiles.get(parent1_id)
            parent2_genetic = self.genetic_algorithm.genetic_profiles.get(parent2_id)
            
            if parent1_genetic and parent2_genetic:
                # Combine parent capabilities to determine focus areas
                combined_capabilities = {}
                for capability in parent1_genetic.capability_genes:
                    if capability in parent2_genetic.capability_genes:
                        combined_capabilities[capability] = (
                            parent1_genetic.capability_genes[capability] +
                            parent2_genetic.capability_genes[capability]
                        ) / 2.0
                
                # Generate goals based on strongest combined capabilities
                sorted_capabilities = sorted(combined_capabilities.items(), key=lambda x: x[1], reverse=True)
                
                for capability, strength in sorted_capabilities[:3]:  # Top 3 capabilities
                    if capability == "analytical_ability":
                        goals.append("Develop strong analytical and logical thinking skills")
                    elif capability == "creative_ability":
                        goals.append("Foster creativity and innovative problem-solving")
                    elif capability == "social_ability":
                        goals.append("Build excellent communication and social skills")
                    elif capability == "technical_ability":
                        goals.append("Master technical skills and system understanding")
                    elif capability == "learning_rate":
                        goals.append("Cultivate rapid learning and knowledge acquisition")
            
            # Add general development goals
            goals.extend([
                "Develop emotional intelligence and self-awareness",
                "Build independence and self-reliance",
                "Establish positive relationships with other agents",
                "Contribute meaningfully to the agent community"
            ])
            
            return goals[:6]  # Limit to 6 goals
            
        except Exception as e:
            self.logger.error(f"Failed to generate development goals: {e}")
            return ["Develop basic agent capabilities", "Build social connections", "Achieve independence"]
    
    def _generate_development_milestones(self) -> List[Dict[str, Any]]:
        """Generate development milestones for child-rearing."""
        return [
            {"milestone": "First successful communication", "target_hours": 6},
            {"milestone": "Basic problem-solving demonstration", "target_hours": 24},
            {"milestone": "Social interaction with other agents", "target_hours": 48},
            {"milestone": "Independent task completion", "target_hours": 72},
            {"milestone": "Knowledge sharing with community", "target_hours": 120},
            {"milestone": "Full independence achievement", "target_hours": 168}
        ]
    
    def _assess_goal_progress(
        self,
        child_id: str,
        goal: str,
        child_status: Dict[str, Any],
        child_genetic: GeneticProfile
    ) -> float:
        """Assess progress toward a development goal."""
        try:
            # Simplified progress assessment based on genetic fitness and status
            base_progress = child_genetic.genetic_fitness
            
            # Adjust based on goal type
            if "analytical" in goal.lower():
                capability_bonus = child_genetic.capability_genes.get("analytical_ability", 0.5) * 0.3
            elif "creative" in goal.lower():
                capability_bonus = child_genetic.capability_genes.get("creative_ability", 0.5) * 0.3
            elif "social" in goal.lower():
                capability_bonus = child_genetic.capability_genes.get("social_ability", 0.5) * 0.3
            elif "technical" in goal.lower():
                capability_bonus = child_genetic.capability_genes.get("technical_ability", 0.5) * 0.3
            elif "learning" in goal.lower():
                capability_bonus = child_genetic.capability_genes.get("learning_rate", 0.5) * 0.3
            else:
                capability_bonus = 0.1
            
            progress = min(1.0, base_progress + capability_bonus)
            return progress
            
        except Exception:
            return 0.5
    
    def _calculate_independence_score(
        self,
        genetic_profile: GeneticProfile,
        status: Dict[str, Any],
        social_profile: Dict[str, Any]
    ) -> float:
        """Calculate independence score for a child agent."""
        try:
            # Base independence from genetic fitness
            base_independence = genetic_profile.genetic_fitness
            
            # Bonus for social connections (independent agents can form relationships)
            social_connections = social_profile.get("network_connections", 0)
            social_bonus = min(0.2, social_connections / 10.0)
            
            # Bonus for status achievements
            status_bonus = 0.0
            if "category_status" in status:
                for category, category_status in status["category_status"].items():
                    if category_status.get("current_points", 0) > 0:
                        status_bonus += 0.05
            
            independence = min(1.0, base_independence + social_bonus + status_bonus)
            return independence
            
        except Exception:
            return 0.5
    
    def _generate_development_recommendations(
        self,
        plan: ChildRearingPlan,
        progress: Dict[str, float],
        independence_score: float
    ) -> List[str]:
        """Generate recommendations for child development."""
        try:
            recommendations = []
            
            # Check for low progress areas
            for goal, progress_score in progress.items():
                if progress_score < 0.5:
                    recommendations.append(f"Focus more attention on: {goal}")
            
            # Independence recommendations
            if independence_score < 0.3:
                recommendations.append("Encourage more independent activities and decision-making")
            elif independence_score > 0.8:
                recommendations.append("Consider transitioning to full independence soon")
            
            # General recommendations
            if not recommendations:
                recommendations.append("Continue current development approach - progress is good")
            
            return recommendations
            
        except Exception:
            return ["Monitor development closely and adjust approach as needed"]
    
    async def _complete_active_child_rearing(self) -> None:
        """Complete any active child-rearing during shutdown."""
        try:
            for child_id, plan in list(self.child_rearing_plans.items()):
                # Mark as completed
                plan.milestone_tracking["completion_reason"] = "system_shutdown"
                plan.milestone_tracking["completed_at"] = datetime.now().isoformat()
                
                self.logger.info(f"Completed child-rearing for {child_id} due to shutdown")
                
        except Exception as e:
            self.logger.error(f"Failed to complete active child-rearing: {e}")
    
    async def _load_reproduction_data(self) -> None:
        """Load reproduction data from storage."""
        # Placeholder for loading from persistent storage
        pass
    
    async def _save_reproduction_data(self) -> None:
        """Save reproduction data to storage."""
        # Placeholder for saving to persistent storage
        pass