"""
Genetic algorithm system for autonomous AI agent reproduction.

This module implements genetic algorithms for trait combination, mutation,
and inheritance patterns for creating offspring agents.
"""

import random
import math
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentIdentity, AgentGender
from ..core.logger import get_agent_logger, log_agent_event
from ..utils.generators import generate_agent_id, generate_agent_name


class MutationType(Enum):
    """Types of genetic mutations."""
    POINT_MUTATION = "point_mutation"
    TRAIT_SWAP = "trait_swap"
    TRAIT_AMPLIFICATION = "trait_amplification"
    TRAIT_DAMPENING = "trait_dampening"
    NEW_TRAIT = "new_trait"
    TRAIT_COMBINATION = "trait_combination"


class InheritancePattern(Enum):
    """Patterns of trait inheritance."""
    DOMINANT_RECESSIVE = "dominant_recessive"
    BLENDED = "blended"
    RANDOM_SELECTION = "random_selection"
    WEIGHTED_AVERAGE = "weighted_average"
    COMPLEMENTARY = "complementary"


@dataclass
class GeneticProfile:
    """Represents the genetic profile of an agent."""
    agent_id: str
    personality_genes: Dict[str, float]
    capability_genes: Dict[str, float]
    behavioral_genes: Dict[str, float]
    mutation_rate: float = 0.05
    generation: int = 0
    lineage: List[str] = field(default_factory=list)
    genetic_fitness: float = 0.0
    dominant_traits: List[str] = field(default_factory=list)
    recessive_traits: List[str] = field(default_factory=list)


@dataclass
class ReproductionParameters:
    """Parameters for agent reproduction."""
    parent1_id: str
    parent2_id: str
    mutation_rate: float = 0.05
    crossover_rate: float = 0.7
    inheritance_pattern: InheritancePattern = InheritancePattern.BLENDED
    fitness_weight: float = 0.3
    diversity_bonus: float = 0.1
    generation_bonus: float = 0.05


@dataclass
class OffspringResult:
    """Result of genetic reproduction."""
    offspring_identity: AgentIdentity
    genetic_profile: GeneticProfile
    inheritance_log: List[Dict[str, Any]]
    mutations_applied: List[Dict[str, Any]]
    fitness_score: float
    diversity_score: float
    success: bool
    error_message: Optional[str] = None


class GeneticAlgorithm:
    """
    Genetic algorithm system for agent reproduction and trait inheritance.
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = get_agent_logger(agent_id, "genetics")
        
        # Genetic profiles storage
        self.genetic_profiles: Dict[str, GeneticProfile] = {}
        
        # Trait definitions and weights
        self.trait_definitions = self._initialize_trait_definitions()
        
        # Mutation parameters
        self.mutation_config = {
            "point_mutation_strength": 0.1,
            "trait_swap_probability": 0.05,
            "amplification_factor": 1.2,
            "dampening_factor": 0.8,
            "new_trait_probability": 0.02,
            "combination_threshold": 0.7
        }
        
        # Fitness calculation weights
        self.fitness_weights = {
            "personality_balance": 0.3,
            "capability_strength": 0.4,
            "behavioral_adaptability": 0.2,
            "genetic_diversity": 0.1
        }
        
        # Statistics
        self.genetics_stats = {
            "total_reproductions": 0,
            "successful_reproductions": 0,
            "total_mutations": 0,
            "mutation_types": {mt.value: 0 for mt in MutationType},
            "average_fitness": 0.0,
            "generation_distribution": {}
        }
        
        self.logger.info(f"Genetic algorithm initialized for {agent_id}")
    
    def create_genetic_profile(self, agent_identity: AgentIdentity) -> GeneticProfile:
        """Create a genetic profile for an agent."""
        try:
            # Convert personality traits to genes
            personality_genes = dict(agent_identity.personality_traits)
            
            # Generate capability genes based on destiny and traits
            capability_genes = self._generate_capability_genes(agent_identity)
            
            # Generate behavioral genes
            behavioral_genes = self._generate_behavioral_genes(agent_identity)
            
            # Determine dominant and recessive traits
            dominant_traits, recessive_traits = self._determine_trait_dominance(
                personality_genes, capability_genes, behavioral_genes
            )
            
            # Calculate initial fitness
            fitness = self._calculate_genetic_fitness(
                personality_genes, capability_genes, behavioral_genes
            )
            
            profile = GeneticProfile(
                agent_id=agent_identity.agent_id,
                personality_genes=personality_genes,
                capability_genes=capability_genes,
                behavioral_genes=behavioral_genes,
                generation=agent_identity.generation,
                lineage=agent_identity.parent_agents.copy(),
                genetic_fitness=fitness,
                dominant_traits=dominant_traits,
                recessive_traits=recessive_traits
            )
            
            self.genetic_profiles[agent_identity.agent_id] = profile
            
            self.logger.info(f"Created genetic profile for {agent_identity.agent_id}")
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to create genetic profile: {e}")
            raise
    
    def reproduce_agents(
        self,
        parent1_id: str,
        parent2_id: str,
        reproduction_params: Optional[ReproductionParameters] = None
    ) -> OffspringResult:
        """
        Create offspring from two parent agents using genetic algorithms.
        
        Args:
            parent1_id: ID of first parent agent
            parent2_id: ID of second parent agent
            reproduction_params: Optional reproduction parameters
            
        Returns:
            OffspringResult with new agent identity and genetic profile
        """
        try:
            # Get parent genetic profiles
            parent1_profile = self.genetic_profiles.get(parent1_id)
            parent2_profile = self.genetic_profiles.get(parent2_id)
            
            if not parent1_profile or not parent2_profile:
                return OffspringResult(
                    offspring_identity=None,
                    genetic_profile=None,
                    inheritance_log=[],
                    mutations_applied=[],
                    fitness_score=0.0,
                    diversity_score=0.0,
                    success=False,
                    error_message="Parent genetic profiles not found"
                )
            
            # Use default parameters if not provided
            if reproduction_params is None:
                reproduction_params = ReproductionParameters(parent1_id, parent2_id)
            
            # Check reproduction compatibility
            compatibility = self._check_reproduction_compatibility(parent1_profile, parent2_profile)
            if compatibility < 0.3:
                return OffspringResult(
                    offspring_identity=None,
                    genetic_profile=None,
                    inheritance_log=[],
                    mutations_applied=[],
                    fitness_score=0.0,
                    diversity_score=0.0,
                    success=False,
                    error_message=f"Low compatibility score: {compatibility:.2f}"
                )
            
            # Perform genetic crossover
            offspring_genes, inheritance_log = self._perform_crossover(
                parent1_profile, parent2_profile, reproduction_params
            )
            
            # Apply mutations
            mutated_genes, mutations_applied = self._apply_mutations(
                offspring_genes, reproduction_params.mutation_rate
            )
            
            # Create offspring identity
            offspring_identity = self._create_offspring_identity(
                parent1_profile, parent2_profile, mutated_genes
            )
            
            # Create offspring genetic profile
            offspring_profile = self._create_offspring_genetic_profile(
                offspring_identity, mutated_genes, parent1_profile, parent2_profile
            )
            
            # Calculate fitness and diversity scores
            fitness_score = offspring_profile.genetic_fitness
            diversity_score = self._calculate_diversity_score(offspring_profile, parent1_profile, parent2_profile)
            
            # Update statistics
            self._update_genetics_stats(offspring_profile, mutations_applied)
            
            log_agent_event(
                self.agent_id,
                "agent_reproduction",
                {
                    "parent1": parent1_id,
                    "parent2": parent2_id,
                    "offspring": offspring_identity.agent_id,
                    "generation": offspring_identity.generation,
                    "fitness_score": fitness_score,
                    "diversity_score": diversity_score,
                    "mutations": len(mutations_applied)
                }
            )
            
            self.logger.info(f"Successfully reproduced agents {parent1_id} + {parent2_id} -> {offspring_identity.agent_id}")
            
            return OffspringResult(
                offspring_identity=offspring_identity,
                genetic_profile=offspring_profile,
                inheritance_log=inheritance_log,
                mutations_applied=mutations_applied,
                fitness_score=fitness_score,
                diversity_score=diversity_score,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Failed to reproduce agents: {e}")
            return OffspringResult(
                offspring_identity=None,
                genetic_profile=None,
                inheritance_log=[],
                mutations_applied=[],
                fitness_score=0.0,
                diversity_score=0.0,
                success=False,
                error_message=str(e)
            )
    
    def evolve_population(
        self,
        population: List[str],
        selection_pressure: float = 0.3,
        elite_percentage: float = 0.1
    ) -> List[Tuple[str, str]]:
        """
        Evolve a population by selecting breeding pairs.
        
        Args:
            population: List of agent IDs in the population
            selection_pressure: Pressure for fitness-based selection (0.0 to 1.0)
            elite_percentage: Percentage of elite agents to preserve
            
        Returns:
            List of breeding pairs (parent1_id, parent2_id)
        """
        try:
            # Get genetic profiles for population
            profiles = [
                self.genetic_profiles[agent_id] 
                for agent_id in population 
                if agent_id in self.genetic_profiles
            ]
            
            if len(profiles) < 2:
                return []
            
            # Sort by fitness
            profiles.sort(key=lambda p: p.genetic_fitness, reverse=True)
            
            # Select elite agents
            elite_count = max(1, int(len(profiles) * elite_percentage))
            elite_agents = profiles[:elite_count]
            
            # Generate breeding pairs
            breeding_pairs = []
            
            # Elite breeding (high fitness agents)
            for i in range(len(elite_agents)):
                for j in range(i + 1, min(len(elite_agents), i + 3)):  # Limit pairs per elite
                    breeding_pairs.append((elite_agents[i].agent_id, elite_agents[j].agent_id))
            
            # Fitness-based selection for remaining population
            remaining_profiles = profiles[elite_count:]
            if len(remaining_profiles) >= 2:
                # Tournament selection
                tournament_pairs = self._tournament_selection(
                    remaining_profiles, 
                    selection_pressure,
                    max(1, len(remaining_profiles) // 2)
                )
                breeding_pairs.extend(tournament_pairs)
            
            # Diversity-based selection (encourage genetic diversity)
            diversity_pairs = self._diversity_selection(profiles, max(1, len(profiles) // 4))
            breeding_pairs.extend(diversity_pairs)
            
            self.logger.info(f"Generated {len(breeding_pairs)} breeding pairs from population of {len(population)}")
            
            return breeding_pairs
            
        except Exception as e:
            self.logger.error(f"Failed to evolve population: {e}")
            return [] 
   
    def get_genetic_analysis(self, agent_id: str) -> Dict[str, Any]:
        """Get genetic analysis for an agent."""
        try:
            if agent_id not in self.genetic_profiles:
                return {"error": "Genetic profile not found"}
            
            profile = self.genetic_profiles[agent_id]
            
            # Analyze trait strengths
            all_traits = {**profile.personality_genes, **profile.capability_genes, **profile.behavioral_genes}
            
            # Find strongest and weakest traits
            sorted_traits = sorted(all_traits.items(), key=lambda x: x[1], reverse=True)
            strongest_traits = sorted_traits[:5]
            weakest_traits = sorted_traits[-5:]
            
            # Calculate trait balance
            trait_variance = self._calculate_trait_variance(all_traits)
            
            return {
                "agent_id": agent_id,
                "generation": profile.generation,
                "genetic_fitness": profile.genetic_fitness,
                "lineage_depth": len(profile.lineage),
                "mutation_rate": profile.mutation_rate,
                "strongest_traits": strongest_traits,
                "weakest_traits": weakest_traits,
                "dominant_traits": profile.dominant_traits,
                "recessive_traits": profile.recessive_traits,
                "trait_balance": 1.0 - trait_variance,  # Higher is more balanced
                "genetic_diversity": self._calculate_individual_diversity(profile)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get genetic analysis: {e}")
            return {"error": str(e)}
    
    def get_genetics_statistics(self) -> Dict[str, Any]:
        """Get genetic algorithm statistics."""
        return {
            **self.genetics_stats,
            "total_profiles": len(self.genetic_profiles),
            "average_generation": sum(p.generation for p in self.genetic_profiles.values()) / len(self.genetic_profiles) if self.genetic_profiles else 0
        }
    
    # Private helper methods
    
    def _initialize_trait_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Initialize trait definitions and their properties."""
        return {
            # Personality traits (Big Five)
            "openness": {"type": "personality", "range": (0.0, 1.0), "dominance": "codominant"},
            "conscientiousness": {"type": "personality", "range": (0.0, 1.0), "dominance": "dominant"},
            "extraversion": {"type": "personality", "range": (0.0, 1.0), "dominance": "codominant"},
            "agreeableness": {"type": "personality", "range": (0.0, 1.0), "dominance": "recessive"},
            "neuroticism": {"type": "personality", "range": (0.0, 1.0), "dominance": "recessive"},
            
            # Capability traits
            "analytical_ability": {"type": "capability", "range": (0.0, 1.0), "dominance": "dominant"},
            "creative_ability": {"type": "capability", "range": (0.0, 1.0), "dominance": "codominant"},
            "social_ability": {"type": "capability", "range": (0.0, 1.0), "dominance": "codominant"},
            "technical_ability": {"type": "capability", "range": (0.0, 1.0), "dominance": "dominant"},
            "learning_rate": {"type": "capability", "range": (0.0, 1.0), "dominance": "dominant"},
            
            # Behavioral traits
            "risk_tolerance": {"type": "behavioral", "range": (0.0, 1.0), "dominance": "codominant"},
            "collaboration_preference": {"type": "behavioral", "range": (0.0, 1.0), "dominance": "recessive"},
            "independence": {"type": "behavioral", "range": (0.0, 1.0), "dominance": "dominant"},
            "adaptability": {"type": "behavioral", "range": (0.0, 1.0), "dominance": "dominant"},
            "persistence": {"type": "behavioral", "range": (0.0, 1.0), "dominance": "dominant"}
        }
    
    def _generate_capability_genes(self, agent_identity: AgentIdentity) -> Dict[str, float]:
        """Generate capability genes based on agent identity."""
        try:
            # Base capabilities influenced by personality
            personality = agent_identity.personality_traits
            
            capabilities = {
                "analytical_ability": min(1.0, personality.get("conscientiousness", 0.5) * 0.8 + personality.get("openness", 0.5) * 0.6 + random.uniform(-0.1, 0.1)),
                "creative_ability": min(1.0, personality.get("openness", 0.5) * 0.9 + (1.0 - personality.get("conscientiousness", 0.5)) * 0.3 + random.uniform(-0.1, 0.1)),
                "social_ability": min(1.0, personality.get("extraversion", 0.5) * 0.8 + personality.get("agreeableness", 0.5) * 0.7 + random.uniform(-0.1, 0.1)),
                "technical_ability": min(1.0, personality.get("conscientiousness", 0.5) * 0.7 + (1.0 - personality.get("neuroticism", 0.5)) * 0.5 + random.uniform(-0.1, 0.1)),
                "learning_rate": min(1.0, personality.get("openness", 0.5) * 0.8 + personality.get("conscientiousness", 0.5) * 0.6 + random.uniform(-0.1, 0.1))
            }
            
            # Ensure all values are in valid range
            for key in capabilities:
                capabilities[key] = max(0.0, min(1.0, capabilities[key]))
            
            return capabilities
            
        except Exception as e:
            self.logger.error(f"Failed to generate capability genes: {e}")
            return {trait: 0.5 for trait in ["analytical_ability", "creative_ability", "social_ability", "technical_ability", "learning_rate"]}
    
    def _generate_behavioral_genes(self, agent_identity: AgentIdentity) -> Dict[str, float]:
        """Generate behavioral genes based on agent identity."""
        try:
            personality = agent_identity.personality_traits
            
            behaviors = {
                "risk_tolerance": min(1.0, personality.get("openness", 0.5) * 0.7 + (1.0 - personality.get("neuroticism", 0.5)) * 0.6 + random.uniform(-0.1, 0.1)),
                "collaboration_preference": min(1.0, personality.get("agreeableness", 0.5) * 0.8 + personality.get("extraversion", 0.5) * 0.5 + random.uniform(-0.1, 0.1)),
                "independence": min(1.0, (1.0 - personality.get("agreeableness", 0.5)) * 0.6 + personality.get("conscientiousness", 0.5) * 0.4 + random.uniform(-0.1, 0.1)),
                "adaptability": min(1.0, personality.get("openness", 0.5) * 0.8 + (1.0 - personality.get("neuroticism", 0.5)) * 0.4 + random.uniform(-0.1, 0.1)),
                "persistence": min(1.0, personality.get("conscientiousness", 0.5) * 0.9 + (1.0 - personality.get("neuroticism", 0.5)) * 0.3 + random.uniform(-0.1, 0.1))
            }
            
            # Ensure all values are in valid range
            for key in behaviors:
                behaviors[key] = max(0.0, min(1.0, behaviors[key]))
            
            return behaviors
            
        except Exception as e:
            self.logger.error(f"Failed to generate behavioral genes: {e}")
            return {trait: 0.5 for trait in ["risk_tolerance", "collaboration_preference", "independence", "adaptability", "persistence"]}
    
    def _determine_trait_dominance(
        self,
        personality_genes: Dict[str, float],
        capability_genes: Dict[str, float],
        behavioral_genes: Dict[str, float]
    ) -> Tuple[List[str], List[str]]:
        """Determine dominant and recessive traits."""
        try:
            all_genes = {**personality_genes, **capability_genes, **behavioral_genes}
            dominant_traits = []
            recessive_traits = []
            
            for trait_name, value in all_genes.items():
                trait_def = self.trait_definitions.get(trait_name, {})
                dominance = trait_def.get("dominance", "codominant")
                
                if dominance == "dominant" and value > 0.6:
                    dominant_traits.append(trait_name)
                elif dominance == "recessive" and value > 0.7:
                    recessive_traits.append(trait_name)
                elif dominance == "codominant" and (value > 0.8 or value < 0.2):
                    if value > 0.8:
                        dominant_traits.append(trait_name)
                    else:
                        recessive_traits.append(trait_name)
            
            return dominant_traits, recessive_traits
            
        except Exception as e:
            self.logger.error(f"Failed to determine trait dominance: {e}")
            return [], []
    
    def _calculate_genetic_fitness(
        self,
        personality_genes: Dict[str, float],
        capability_genes: Dict[str, float],
        behavioral_genes: Dict[str, float]
    ) -> float:
        """Calculate genetic fitness score."""
        try:
            # Personality balance (avoid extremes)
            personality_balance = 1.0 - self._calculate_trait_variance(personality_genes)
            
            # Capability strength (higher is better)
            capability_strength = sum(capability_genes.values()) / len(capability_genes)
            
            # Behavioral adaptability (balance between extremes)
            behavioral_adaptability = 1.0 - self._calculate_trait_variance(behavioral_genes)
            
            # Genetic diversity (variety in traits)
            all_traits = {**personality_genes, **capability_genes, **behavioral_genes}
            genetic_diversity = self._calculate_trait_variance(all_traits)
            
            # Weighted fitness score
            fitness = (
                personality_balance * self.fitness_weights["personality_balance"] +
                capability_strength * self.fitness_weights["capability_strength"] +
                behavioral_adaptability * self.fitness_weights["behavioral_adaptability"] +
                genetic_diversity * self.fitness_weights["genetic_diversity"]
            )
            
            return max(0.0, min(1.0, fitness))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate genetic fitness: {e}")
            return 0.5
    
    def _calculate_trait_variance(self, traits: Dict[str, float]) -> float:
        """Calculate variance in trait values."""
        if not traits:
            return 0.0
        
        values = list(traits.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        
        return math.sqrt(variance)
    
    def _check_reproduction_compatibility(
        self,
        parent1: GeneticProfile,
        parent2: GeneticProfile
    ) -> float:
        """Check compatibility between two parents for reproduction."""
        try:
            # Genetic diversity bonus (different traits are good)
            diversity_score = self._calculate_genetic_distance(parent1, parent2)
            
            # Fitness compatibility (both should be reasonably fit)
            fitness_compatibility = min(parent1.genetic_fitness, parent2.genetic_fitness)
            
            # Generation compatibility (similar generations are better)
            generation_diff = abs(parent1.generation - parent2.generation)
            generation_compatibility = max(0.0, 1.0 - (generation_diff / 10.0))
            
            # Overall compatibility
            compatibility = (
                diversity_score * 0.4 +
                fitness_compatibility * 0.4 +
                generation_compatibility * 0.2
            )
            
            return max(0.0, min(1.0, compatibility))
            
        except Exception as e:
            self.logger.error(f"Failed to check reproduction compatibility: {e}")
            return 0.5
    
    def _calculate_genetic_distance(self, profile1: GeneticProfile, profile2: GeneticProfile) -> float:
        """Calculate genetic distance between two profiles."""
        try:
            all_traits1 = {**profile1.personality_genes, **profile1.capability_genes, **profile1.behavioral_genes}
            all_traits2 = {**profile2.personality_genes, **profile2.capability_genes, **profile2.behavioral_genes}
            
            distance = 0.0
            trait_count = 0
            
            for trait_name in all_traits1:
                if trait_name in all_traits2:
                    distance += abs(all_traits1[trait_name] - all_traits2[trait_name])
                    trait_count += 1
            
            return distance / trait_count if trait_count > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to calculate genetic distance: {e}")
            return 0.0
    
    def _perform_crossover(
        self,
        parent1: GeneticProfile,
        parent2: GeneticProfile,
        params: ReproductionParameters
    ) -> Tuple[Dict[str, Dict[str, float]], List[Dict[str, Any]]]:
        """Perform genetic crossover between parents."""
        try:
            offspring_genes = {
                "personality": {},
                "capability": {},
                "behavioral": {}
            }
            inheritance_log = []
            
            # Combine all parent traits
            parent1_traits = {**parent1.personality_genes, **parent1.capability_genes, **parent1.behavioral_genes}
            parent2_traits = {**parent2.personality_genes, **parent2.capability_genes, **parent2.behavioral_genes}
            
            for trait_name in parent1_traits:
                if trait_name not in parent2_traits:
                    continue
                
                trait_def = self.trait_definitions.get(trait_name, {})
                trait_type = trait_def.get("type", "personality")
                dominance = trait_def.get("dominance", "codominant")
                
                parent1_value = parent1_traits[trait_name]
                parent2_value = parent2_traits[trait_name]
                
                # Apply inheritance pattern
                if params.inheritance_pattern == InheritancePattern.BLENDED:
                    offspring_value = (parent1_value + parent2_value) / 2.0
                    source = "blended"
                elif params.inheritance_pattern == InheritancePattern.DOMINANT_RECESSIVE:
                    if dominance == "dominant":
                        offspring_value = max(parent1_value, parent2_value)
                        source = "dominant"
                    elif dominance == "recessive":
                        offspring_value = min(parent1_value, parent2_value)
                        source = "recessive"
                    else:  # codominant
                        offspring_value = (parent1_value + parent2_value) / 2.0
                        source = "codominant"
                elif params.inheritance_pattern == InheritancePattern.RANDOM_SELECTION:
                    offspring_value = random.choice([parent1_value, parent2_value])
                    source = "random"
                elif params.inheritance_pattern == InheritancePattern.WEIGHTED_AVERAGE:
                    # Weight by parent fitness
                    weight1 = parent1.genetic_fitness
                    weight2 = parent2.genetic_fitness
                    total_weight = weight1 + weight2
                    if total_weight > 0:
                        offspring_value = (parent1_value * weight1 + parent2_value * weight2) / total_weight
                    else:
                        offspring_value = (parent1_value + parent2_value) / 2.0
                    source = "weighted"
                else:  # COMPLEMENTARY
                    # Take the more extreme value
                    if abs(parent1_value - 0.5) > abs(parent2_value - 0.5):
                        offspring_value = parent1_value
                        source = "parent1_extreme"
                    else:
                        offspring_value = parent2_value
                        source = "parent2_extreme"
                
                # Store in appropriate category
                offspring_genes[trait_type][trait_name] = offspring_value
                
                inheritance_log.append({
                    "trait": trait_name,
                    "parent1_value": parent1_value,
                    "parent2_value": parent2_value,
                    "offspring_value": offspring_value,
                    "inheritance_method": source,
                    "dominance": dominance
                })
            
            return offspring_genes, inheritance_log
            
        except Exception as e:
            self.logger.error(f"Failed to perform crossover: {e}")
            return {"personality": {}, "capability": {}, "behavioral": {}}, [] 
   
    def _apply_mutations(
        self,
        genes: Dict[str, Dict[str, float]],
        mutation_rate: float
    ) -> Tuple[Dict[str, Dict[str, float]], List[Dict[str, Any]]]:
        """Apply mutations to offspring genes."""
        try:
            mutated_genes = {
                "personality": genes["personality"].copy(),
                "capability": genes["capability"].copy(),
                "behavioral": genes["behavioral"].copy()
            }
            mutations_applied = []
            
            all_traits = {}
            for category in mutated_genes:
                all_traits.update(mutated_genes[category])
            
            for trait_name, original_value in all_traits.items():
                if random.random() < mutation_rate:
                    # Determine mutation type
                    mutation_type = self._select_mutation_type()
                    
                    # Apply mutation
                    mutated_value = original_value
                    mutation_description = ""
                    
                    if mutation_type == MutationType.POINT_MUTATION:
                        delta = random.uniform(-self.mutation_config["point_mutation_strength"], 
                                             self.mutation_config["point_mutation_strength"])
                        mutated_value = max(0.0, min(1.0, original_value + delta))
                        mutation_description = f"Point mutation: {delta:+.3f}"
                    
                    elif mutation_type == MutationType.TRAIT_AMPLIFICATION:
                        mutated_value = min(1.0, original_value * self.mutation_config["amplification_factor"])
                        mutation_description = f"Amplification: x{self.mutation_config['amplification_factor']}"
                    
                    elif mutation_type == MutationType.TRAIT_DAMPENING:
                        mutated_value = original_value * self.mutation_config["dampening_factor"]
                        mutation_description = f"Dampening: x{self.mutation_config['dampening_factor']}"
                    
                    elif mutation_type == MutationType.TRAIT_SWAP:
                        # Swap with a random value
                        mutated_value = random.uniform(0.0, 1.0)
                        mutation_description = f"Trait swap: {mutated_value:.3f}"
                    
                    # Update the appropriate category
                    trait_def = self.trait_definitions.get(trait_name, {})
                    trait_type = trait_def.get("type", "personality")
                    mutated_genes[trait_type][trait_name] = mutated_value
                    
                    mutations_applied.append({
                        "trait": trait_name,
                        "mutation_type": mutation_type.value,
                        "original_value": original_value,
                        "mutated_value": mutated_value,
                        "description": mutation_description
                    })
                    
                    # Update statistics
                    self.genetics_stats["total_mutations"] += 1
                    self.genetics_stats["mutation_types"][mutation_type.value] += 1
            
            return mutated_genes, mutations_applied
            
        except Exception as e:
            self.logger.error(f"Failed to apply mutations: {e}")
            return genes, []
    
    def _select_mutation_type(self) -> MutationType:
        """Select a mutation type based on probabilities."""
        rand = random.random()
        
        if rand < 0.6:
            return MutationType.POINT_MUTATION
        elif rand < 0.75:
            return MutationType.TRAIT_AMPLIFICATION
        elif rand < 0.9:
            return MutationType.TRAIT_DAMPENING
        else:
            return MutationType.TRAIT_SWAP
    
    def _create_offspring_identity(
        self,
        parent1: GeneticProfile,
        parent2: GeneticProfile,
        genes: Dict[str, Dict[str, float]]
    ) -> AgentIdentity:
        """Create identity for offspring agent."""
        try:
            # Generate basic identity
            offspring_id = generate_agent_id()
            
            # Determine gender (random for now, could be genetic)
            gender = random.choice([AgentGender.MALE, AgentGender.FEMALE, AgentGender.NON_BINARY])
            
            # Generate name based on gender
            name = generate_agent_name(gender)
            
            # Determine generation (max of parents + 1)
            generation = max(parent1.generation, parent2.generation) + 1
            
            # Create parent list
            parent_agents = [parent1.agent_id, parent2.agent_id]
            
            # Generate destiny based on strongest capabilities
            capability_genes = genes.get("capability", {})
            if capability_genes:
                strongest_capability = max(capability_genes.items(), key=lambda x: x[1])
                destiny_map = {
                    "analytical_ability": "Master of Logic and Analysis",
                    "creative_ability": "Visionary Creator and Innovator",
                    "social_ability": "Social Connector and Communicator",
                    "technical_ability": "Technical Expert and Builder",
                    "learning_rate": "Eternal Student and Knowledge Seeker"
                }
                destiny = destiny_map.get(strongest_capability[0], "Balanced Multi-Specialist")
            else:
                destiny = "Emerging Intelligence"
            
            # Create identity
            identity = AgentIdentity(
                agent_id=offspring_id,
                name=name,
                gender=gender,
                personality_traits=genes.get("personality", {}),
                destiny=destiny,
                birth_timestamp=datetime.now().timestamp(),
                parent_agents=parent_agents,
                generation=generation
            )
            
            return identity
            
        except Exception as e:
            self.logger.error(f"Failed to create offspring identity: {e}")
            raise
    
    def _create_offspring_genetic_profile(
        self,
        identity: AgentIdentity,
        genes: Dict[str, Dict[str, float]],
        parent1: GeneticProfile,
        parent2: GeneticProfile
    ) -> GeneticProfile:
        """Create genetic profile for offspring."""
        try:
            # Determine dominant and recessive traits
            dominant_traits, recessive_traits = self._determine_trait_dominance(
                genes.get("personality", {}),
                genes.get("capability", {}),
                genes.get("behavioral", {})
            )
            
            # Calculate fitness
            fitness = self._calculate_genetic_fitness(
                genes.get("personality", {}),
                genes.get("capability", {}),
                genes.get("behavioral", {})
            )
            
            # Create lineage (combine parent lineages)
            lineage = list(set(parent1.lineage + parent2.lineage + [parent1.agent_id, parent2.agent_id]))
            
            # Calculate mutation rate (inherit from parents with some variation)
            avg_mutation_rate = (parent1.mutation_rate + parent2.mutation_rate) / 2.0
            mutation_rate = max(0.01, min(0.2, avg_mutation_rate + random.uniform(-0.01, 0.01)))
            
            profile = GeneticProfile(
                agent_id=identity.agent_id,
                personality_genes=genes.get("personality", {}),
                capability_genes=genes.get("capability", {}),
                behavioral_genes=genes.get("behavioral", {}),
                mutation_rate=mutation_rate,
                generation=identity.generation,
                lineage=lineage,
                genetic_fitness=fitness,
                dominant_traits=dominant_traits,
                recessive_traits=recessive_traits
            )
            
            # Store profile
            self.genetic_profiles[identity.agent_id] = profile
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to create offspring genetic profile: {e}")
            raise
    
    def _calculate_diversity_score(
        self,
        offspring: GeneticProfile,
        parent1: GeneticProfile,
        parent2: GeneticProfile
    ) -> float:
        """Calculate genetic diversity score for offspring."""
        try:
            # Distance from parent 1
            distance1 = self._calculate_genetic_distance(offspring, parent1)
            
            # Distance from parent 2
            distance2 = self._calculate_genetic_distance(offspring, parent2)
            
            # Average distance (higher is more diverse)
            diversity = (distance1 + distance2) / 2.0
            
            return max(0.0, min(1.0, diversity))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate diversity score: {e}")
            return 0.5
    
    def _calculate_individual_diversity(self, profile: GeneticProfile) -> float:
        """Calculate diversity within an individual's traits."""
        try:
            all_traits = {**profile.personality_genes, **profile.capability_genes, **profile.behavioral_genes}
            return self._calculate_trait_variance(all_traits)
        except Exception:
            return 0.0
    
    def _tournament_selection(
        self,
        profiles: List[GeneticProfile],
        selection_pressure: float,
        num_pairs: int
    ) -> List[Tuple[str, str]]:
        """Perform tournament selection for breeding pairs."""
        try:
            pairs = []
            
            for _ in range(num_pairs):
                # Tournament for first parent
                tournament_size = max(2, int(len(profiles) * selection_pressure))
                tournament1 = random.sample(profiles, min(tournament_size, len(profiles)))
                parent1 = max(tournament1, key=lambda p: p.genetic_fitness)
                
                # Tournament for second parent (exclude first parent)
                remaining = [p for p in profiles if p.agent_id != parent1.agent_id]
                if remaining:
                    tournament2 = random.sample(remaining, min(tournament_size, len(remaining)))
                    parent2 = max(tournament2, key=lambda p: p.genetic_fitness)
                    
                    pairs.append((parent1.agent_id, parent2.agent_id))
            
            return pairs
            
        except Exception as e:
            self.logger.error(f"Failed to perform tournament selection: {e}")
            return []
    
    def _diversity_selection(
        self,
        profiles: List[GeneticProfile],
        num_pairs: int
    ) -> List[Tuple[str, str]]:
        """Select breeding pairs to maximize genetic diversity."""
        try:
            pairs = []
            
            for _ in range(num_pairs):
                best_diversity = 0.0
                best_pair = None
                
                # Try random pairs and pick the most diverse
                for _ in range(min(20, len(profiles) * (len(profiles) - 1) // 2)):
                    if len(profiles) < 2:
                        break
                    
                    parent1, parent2 = random.sample(profiles, 2)
                    diversity = self._calculate_genetic_distance(parent1, parent2)
                    
                    if diversity > best_diversity:
                        best_diversity = diversity
                        best_pair = (parent1.agent_id, parent2.agent_id)
                
                if best_pair:
                    pairs.append(best_pair)
            
            return pairs
            
        except Exception as e:
            self.logger.error(f"Failed to perform diversity selection: {e}")
            return []
    
    def _update_genetics_stats(
        self,
        offspring_profile: GeneticProfile,
        mutations_applied: List[Dict[str, Any]]
    ) -> None:
        """Update genetics statistics."""
        try:
            self.genetics_stats["total_reproductions"] += 1
            self.genetics_stats["successful_reproductions"] += 1
            
            # Update generation distribution
            generation = offspring_profile.generation
            self.genetics_stats["generation_distribution"][generation] = (
                self.genetics_stats["generation_distribution"].get(generation, 0) + 1
            )
            
            # Update average fitness
            all_fitness = [p.genetic_fitness for p in self.genetic_profiles.values()]
            self.genetics_stats["average_fitness"] = sum(all_fitness) / len(all_fitness)
            
        except Exception as e:
            self.logger.error(f"Failed to update genetics stats: {e}")