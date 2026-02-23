"""
Advanced memory consolidation and forgetting mechanisms.

This module implements sophisticated algorithms for memory consolidation,
importance decay, associative memory formation, and intelligent forgetting.
"""

import math
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

from ..core.interfaces import Memory
from ..core.logger import get_agent_logger, log_agent_event


class ConsolidationStrategy(Enum):
    """Memory consolidation strategies."""
    IMPORTANCE_BASED = "importance_based"
    FREQUENCY_BASED = "frequency_based"
    RECENCY_BASED = "recency_based"
    ASSOCIATIVE = "associative"
    HYBRID = "hybrid"


class ForgettingCurve(Enum):
    """Types of forgetting curves."""
    EXPONENTIAL = "exponential"
    POWER_LAW = "power_law"
    LINEAR = "linear"
    LOGARITHMIC = "logarithmic"


@dataclass
class MemoryAssociation:
    """Represents an association between two memories."""
    memory1_id: str
    memory2_id: str
    strength: float
    association_type: str
    created_at: datetime
    reinforcement_count: int = 0


@dataclass
class ConsolidationMetrics:
    """Metrics for memory consolidation performance."""
    total_memories_processed: int
    memories_consolidated: int
    memories_forgotten: int
    average_importance_change: float
    consolidation_time_ms: float
    associations_created: int
    associations_strengthened: int


class MemoryConsolidator:
    """
    Advanced memory consolidation system with multiple strategies and forgetting curves.
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = get_agent_logger(agent_id, "memory_consolidator")
        
        # Consolidation parameters
        self.importance_decay_rate = 0.05  # Daily decay rate
        self.association_threshold = 0.3   # Minimum strength for associations
        self.consolidation_batch_size = 100
        self.max_associations_per_memory = 10
        
        # Forgetting parameters
        self.forgetting_curve = ForgettingCurve.EXPONENTIAL
        self.forgetting_rate = 0.1
        self.minimum_importance = 0.1
        
        # Memory associations
        self.associations: Dict[str, List[MemoryAssociation]] = {}
        self.association_strength_cache: Dict[Tuple[str, str], float] = {}
        
        # Statistics
        self.consolidation_stats = {
            "total_consolidations": 0,
            "total_forgettings": 0,
            "associations_created": 0,
            "importance_adjustments": 0,
            "average_consolidation_time": 0.0
        }
        
        self.logger.info(f"Memory consolidator initialized for {agent_id}")
    
    async def consolidate_memories(
        self,
        memories: List[Memory],
        strategy: ConsolidationStrategy = ConsolidationStrategy.HYBRID
    ) -> ConsolidationMetrics:
        """
        Consolidate a batch of memories using the specified strategy.
        
        Args:
            memories: List of memories to consolidate
            strategy: Consolidation strategy to use
            
        Returns:
            ConsolidationMetrics with consolidation results
        """
        try:
            start_time = datetime.now()
            
            # Initialize metrics
            metrics = ConsolidationMetrics(
                total_memories_processed=len(memories),
                memories_consolidated=0,
                memories_forgotten=0,
                average_importance_change=0.0,
                consolidation_time_ms=0.0,
                associations_created=0,
                associations_strengthened=0
            )
            
            # Apply importance decay
            importance_changes = []
            for memory in memories:
                old_importance = memory.importance
                new_importance = self._apply_importance_decay(memory)
                memory.importance = new_importance
                importance_changes.append(new_importance - old_importance)
            
            metrics.average_importance_change = sum(importance_changes) / len(importance_changes)
            
            # Apply consolidation strategy
            if strategy == ConsolidationStrategy.IMPORTANCE_BASED:
                consolidated = await self._consolidate_by_importance(memories)
            elif strategy == ConsolidationStrategy.FREQUENCY_BASED:
                consolidated = await self._consolidate_by_frequency(memories)
            elif strategy == ConsolidationStrategy.RECENCY_BASED:
                consolidated = await self._consolidate_by_recency(memories)
            elif strategy == ConsolidationStrategy.ASSOCIATIVE:
                consolidated = await self._consolidate_by_associations(memories)
            else:  # HYBRID
                consolidated = await self._consolidate_hybrid(memories)
            
            metrics.memories_consolidated = len(consolidated)
            
            # Create and strengthen associations
            associations_created, associations_strengthened = await self._update_associations(memories)
            metrics.associations_created = associations_created
            metrics.associations_strengthened = associations_strengthened
            
            # Apply forgetting
            forgotten_memories = await self._apply_forgetting(memories)
            metrics.memories_forgotten = len(forgotten_memories)
            
            # Calculate consolidation time
            end_time = datetime.now()
            metrics.consolidation_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Update statistics
            self.consolidation_stats["total_consolidations"] += metrics.memories_consolidated
            self.consolidation_stats["total_forgettings"] += metrics.memories_forgotten
            self.consolidation_stats["associations_created"] += metrics.associations_created
            self.consolidation_stats["importance_adjustments"] += len(memories)
            
            # Update average consolidation time
            old_avg = self.consolidation_stats["average_consolidation_time"]
            new_avg = (old_avg + metrics.consolidation_time_ms) / 2
            self.consolidation_stats["average_consolidation_time"] = new_avg
            
            log_agent_event(
                self.agent_id,
                "memory_consolidation_completed",
                {
                    "strategy": strategy.value,
                    "memories_processed": metrics.total_memories_processed,
                    "memories_consolidated": metrics.memories_consolidated,
                    "memories_forgotten": metrics.memories_forgotten,
                    "associations_created": metrics.associations_created,
                    "consolidation_time_ms": metrics.consolidation_time_ms
                }
            )
            
            self.logger.info(f"Consolidated {metrics.memories_consolidated} memories using {strategy.value} strategy")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to consolidate memories: {e}")
            raise
    
    async def create_memory_associations(self, memories: List[Memory]) -> int:
        """
        Create associations between related memories.
        
        Args:
            memories: List of memories to analyze for associations
            
        Returns:
            Number of associations created
        """
        try:
            associations_created = 0
            
            # Compare each memory with others to find associations
            for i, memory1 in enumerate(memories):
                for j, memory2 in enumerate(memories[i+1:], i+1):
                    if memory1.memory_id == memory2.memory_id:
                        continue
                    
                    # Calculate association strength
                    strength = self._calculate_association_strength(memory1, memory2)
                    
                    if strength >= self.association_threshold:
                        # Create association
                        association = MemoryAssociation(
                            memory1_id=memory1.memory_id,
                            memory2_id=memory2.memory_id,
                            strength=strength,
                            association_type=self._determine_association_type(memory1, memory2),
                            created_at=datetime.now()
                        )
                        
                        # Store association
                        if memory1.memory_id not in self.associations:
                            self.associations[memory1.memory_id] = []
                        
                        if memory2.memory_id not in self.associations:
                            self.associations[memory2.memory_id] = []
                        
                        self.associations[memory1.memory_id].append(association)
                        self.associations[memory2.memory_id].append(association)
                        
                        # Cache strength
                        self.association_strength_cache[(memory1.memory_id, memory2.memory_id)] = strength
                        self.association_strength_cache[(memory2.memory_id, memory1.memory_id)] = strength
                        
                        associations_created += 1
                        
                        # Limit associations per memory
                        if len(self.associations[memory1.memory_id]) >= self.max_associations_per_memory:
                            break
            
            self.logger.debug(f"Created {associations_created} memory associations")
            
            return associations_created
            
        except Exception as e:
            self.logger.error(f"Failed to create memory associations: {e}")
            return 0
    
    def get_associated_memories(self, memory_id: str, min_strength: float = 0.3) -> List[Tuple[str, float]]:
        """
        Get memories associated with a given memory.
        
        Args:
            memory_id: ID of the memory to find associations for
            min_strength: Minimum association strength
            
        Returns:
            List of tuples (associated_memory_id, strength)
        """
        try:
            if memory_id not in self.associations:
                return []
            
            associated = []
            for association in self.associations[memory_id]:
                if association.strength >= min_strength:
                    other_id = (association.memory2_id if association.memory1_id == memory_id 
                              else association.memory1_id)
                    associated.append((other_id, association.strength))
            
            # Sort by strength (strongest first)
            associated.sort(key=lambda x: x[1], reverse=True)
            
            return associated
            
        except Exception as e:
            self.logger.error(f"Failed to get associated memories for {memory_id}: {e}")
            return []
    
    def calculate_memory_importance_boost(self, memory: Memory) -> float:
        """
        Calculate importance boost based on associations and access patterns.
        
        Args:
            memory: Memory to calculate boost for
            
        Returns:
            Importance boost value (0.0 to 1.0)
        """
        try:
            boost = 0.0
            
            # Association boost
            if memory.memory_id in self.associations:
                association_count = len(self.associations[memory.memory_id])
                avg_strength = sum(a.strength for a in self.associations[memory.memory_id]) / association_count
                boost += min(0.3, association_count * 0.05 + avg_strength * 0.2)
            
            # Recency boost
            days_old = (datetime.now() - memory.timestamp).days
            if days_old < 7:
                boost += 0.2 * (1.0 - days_old / 7.0)
            
            # Type-based boost
            if memory.memory_type == "procedural":
                boost += 0.1  # Procedural memories are often important
            elif memory.memory_type == "episodic" and memory.importance > 0.7:
                boost += 0.15  # Important episodic memories
            
            return min(1.0, boost)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate importance boost for {memory.memory_id}: {e}")
            return 0.0
    
    def get_consolidation_stats(self) -> Dict[str, any]:
        """
        Get consolidation statistics.
        
        Returns:
            Dictionary with consolidation statistics
        """
        return {
            **self.consolidation_stats,
            "total_associations": sum(len(assocs) for assocs in self.associations.values()) // 2,
            "unique_memories_with_associations": len(self.associations),
            "average_associations_per_memory": (
                sum(len(assocs) for assocs in self.associations.values()) / len(self.associations)
                if self.associations else 0
            )
        }
    
    # Private consolidation methods
    
    def _apply_importance_decay(self, memory: Memory) -> float:
        """Apply importance decay based on age and access patterns."""
        try:
            # Calculate age in days
            age_days = (datetime.now() - memory.timestamp).days
            
            # Apply forgetting curve
            if self.forgetting_curve == ForgettingCurve.EXPONENTIAL:
                decay_factor = math.exp(-self.forgetting_rate * age_days)
            elif self.forgetting_curve == ForgettingCurve.POWER_LAW:
                decay_factor = 1.0 / (1.0 + self.forgetting_rate * age_days)
            elif self.forgetting_curve == ForgettingCurve.LINEAR:
                decay_factor = max(0.0, 1.0 - self.forgetting_rate * age_days)
            else:  # LOGARITHMIC
                decay_factor = 1.0 / (1.0 + math.log(1.0 + self.forgetting_rate * age_days))
            
            # Calculate new importance
            base_importance = memory.importance * decay_factor
            
            # Apply importance boost
            importance_boost = self.calculate_memory_importance_boost(memory)
            
            # Combine base importance and boost
            new_importance = min(1.0, base_importance + importance_boost)
            
            # Ensure minimum importance
            new_importance = max(self.minimum_importance, new_importance)
            
            return new_importance
            
        except Exception as e:
            self.logger.error(f"Failed to apply importance decay: {e}")
            return memory.importance
    
    async def _consolidate_by_importance(self, memories: List[Memory]) -> List[Memory]:
        """Consolidate memories based on importance scores."""
        # Sort by importance (highest first)
        memories.sort(key=lambda m: m.importance, reverse=True)
        
        # Consolidate top memories
        consolidation_count = min(len(memories) // 2, self.consolidation_batch_size)
        return memories[:consolidation_count]
    
    async def _consolidate_by_frequency(self, memories: List[Memory]) -> List[Memory]:
        """Consolidate memories based on access frequency."""
        # This would require access count tracking in the main memory system
        # For now, use a simple heuristic based on associations
        memory_scores = []
        
        for memory in memories:
            association_count = len(self.associations.get(memory.memory_id, []))
            score = association_count * memory.importance
            memory_scores.append((memory, score))
        
        # Sort by score (highest first)
        memory_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Consolidate top memories
        consolidation_count = min(len(memories) // 2, self.consolidation_batch_size)
        return [memory for memory, _ in memory_scores[:consolidation_count]]
    
    async def _consolidate_by_recency(self, memories: List[Memory]) -> List[Memory]:
        """Consolidate memories based on recency."""
        # Sort by timestamp (most recent first)
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        
        # Consolidate recent memories
        consolidation_count = min(len(memories) // 3, self.consolidation_batch_size)
        return memories[:consolidation_count]
    
    async def _consolidate_by_associations(self, memories: List[Memory]) -> List[Memory]:
        """Consolidate memories based on associative strength."""
        memory_scores = []
        
        for memory in memories:
            # Calculate total associative strength
            total_strength = 0.0
            if memory.memory_id in self.associations:
                total_strength = sum(a.strength for a in self.associations[memory.memory_id])
            
            score = total_strength * memory.importance
            memory_scores.append((memory, score))
        
        # Sort by associative score (highest first)
        memory_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Consolidate top memories
        consolidation_count = min(len(memories) // 2, self.consolidation_batch_size)
        return [memory for memory, _ in memory_scores[:consolidation_count]]
    
    async def _consolidate_hybrid(self, memories: List[Memory]) -> List[Memory]:
        """Consolidate memories using a hybrid approach."""
        memory_scores = []
        
        for memory in memories:
            # Combine multiple factors
            importance_score = memory.importance * 0.4
            
            # Recency score
            days_old = (datetime.now() - memory.timestamp).days
            recency_score = max(0.0, 1.0 - days_old / 30.0) * 0.3
            
            # Association score
            association_score = 0.0
            if memory.memory_id in self.associations:
                association_count = len(self.associations[memory.memory_id])
                avg_strength = sum(a.strength for a in self.associations[memory.memory_id]) / association_count
                association_score = min(1.0, association_count * 0.1 + avg_strength) * 0.3
            
            total_score = importance_score + recency_score + association_score
            memory_scores.append((memory, total_score))
        
        # Sort by total score (highest first)
        memory_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Consolidate top memories
        consolidation_count = min(len(memories) // 2, self.consolidation_batch_size)
        return [memory for memory, _ in memory_scores[:consolidation_count]]
    
    async def _update_associations(self, memories: List[Memory]) -> Tuple[int, int]:
        """Update memory associations."""
        associations_created = await self.create_memory_associations(memories)
        
        # Strengthen existing associations
        associations_strengthened = 0
        for memory in memories:
            if memory.memory_id in self.associations:
                for association in self.associations[memory.memory_id]:
                    # Strengthen association based on recent access
                    old_strength = association.strength
                    association.strength = min(1.0, association.strength * 1.05)
                    association.reinforcement_count += 1
                    
                    if association.strength > old_strength:
                        associations_strengthened += 1
        
        return associations_created, associations_strengthened
    
    async def _apply_forgetting(self, memories: List[Memory]) -> List[Memory]:
        """Apply forgetting to low-importance memories."""
        forgotten_memories = []
        
        for memory in memories:
            # Check if memory should be forgotten
            if (memory.importance < self.minimum_importance and 
                (datetime.now() - memory.timestamp).days > 7):
                
                # Remove associations
                if memory.memory_id in self.associations:
                    del self.associations[memory.memory_id]
                
                # Remove from cache
                keys_to_remove = [
                    key for key in self.association_strength_cache.keys()
                    if memory.memory_id in key
                ]
                for key in keys_to_remove:
                    del self.association_strength_cache[key]
                
                forgotten_memories.append(memory)
        
        return forgotten_memories
    
    def _calculate_association_strength(self, memory1: Memory, memory2: Memory) -> float:
        """Calculate association strength between two memories."""
        try:
            strength = 0.0
            
            # Content similarity (simple word overlap)
            words1 = set(memory1.content.lower().split())
            words2 = set(memory2.content.lower().split())
            
            if words1 and words2:
                overlap = len(words1.intersection(words2))
                union = len(words1.union(words2))
                content_similarity = overlap / union if union > 0 else 0.0
                strength += content_similarity * 0.4
            
            # Tag similarity
            tags1 = set(memory1.tags)
            tags2 = set(memory2.tags)
            
            if tags1 and tags2:
                tag_overlap = len(tags1.intersection(tags2))
                tag_union = len(tags1.union(tags2))
                tag_similarity = tag_overlap / tag_union if tag_union > 0 else 0.0
                strength += tag_similarity * 0.3
            
            # Temporal proximity
            time_diff = abs((memory1.timestamp - memory2.timestamp).total_seconds())
            max_time_diff = 24 * 3600  # 24 hours
            temporal_proximity = max(0.0, 1.0 - time_diff / max_time_diff)
            strength += temporal_proximity * 0.2
            
            # Type compatibility
            if memory1.memory_type == memory2.memory_type:
                strength += 0.1
            
            return min(1.0, strength)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate association strength: {e}")
            return 0.0
    
    def _determine_association_type(self, memory1: Memory, memory2: Memory) -> str:
        """Determine the type of association between two memories."""
        # Simple heuristic based on content and tags
        if memory1.memory_type == memory2.memory_type:
            return "type_similarity"
        
        # Check for temporal association
        time_diff = abs((memory1.timestamp - memory2.timestamp).total_seconds())
        if time_diff < 3600:  # Within 1 hour
            return "temporal"
        
        # Check for content association
        words1 = set(memory1.content.lower().split())
        words2 = set(memory2.content.lower().split())
        overlap = len(words1.intersection(words2))
        
        if overlap > 2:
            return "content_similarity"
        
        # Check for tag association
        tags1 = set(memory1.tags)
        tags2 = set(memory2.tags)
        
        if tags1.intersection(tags2):
            return "tag_similarity"
        
        return "general"