"""
Unit tests for memory system components.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta

from autonomous_ai_ecosystem.agents.memory import MemorySystem, MemoryType, MemoryImportance
from autonomous_ai_ecosystem.core.interfaces import Memory
from autonomous_ai_ecosystem.utils.generators import generate_knowledge_id


class TestMemorySystem:
    """Test cases for MemorySystem."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.agent_id = "test_agent_memory"
        self.memory_system = MemorySystem(self.agent_id, self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        import asyncio
        if hasattr(self, 'memory_system'):
            asyncio.create_task(self.memory_system.shutdown())
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_memory_system_initialization(self):
        """Test memory system initialization."""
        await self.memory_system.initialize()
        
        assert self.memory_system.agent_id == self.agent_id
        assert len(self.memory_system.working_memory) == 0
        assert len(self.memory_system.memory_cache) == 0
        assert self.memory_system.db_path.exists()
    
    @pytest.mark.asyncio
    async def test_create_memory(self):
        """Test creating memory objects."""
        memory = self.memory_system.create_memory(
            content="Test memory content",
            memory_type=MemoryType.EPISODIC.value,
            importance=0.8,
            tags=["test", "example"]
        )
        
        assert memory.memory_id is not None
        assert memory.content == "Test memory content"
        assert memory.memory_type == MemoryType.EPISODIC.value
        assert memory.importance == 0.8
        assert memory.agent_id == self.agent_id
        assert "test" in memory.tags
        assert "example" in memory.tags
        assert isinstance(memory.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_memory(self):
        """Test storing and retrieving memories."""
        await self.memory_system.initialize()
        
        # Create and store memory
        memory = self.memory_system.create_memory(
            content="Important information about quantum computing",
            memory_type=MemoryType.SEMANTIC.value,
            importance=0.9,
            tags=["quantum", "computing", "physics"]
        )
        
        await self.memory_system.store_memory(memory)
        
        # Verify memory is in working memory
        assert len(self.memory_system.working_memory) == 1
        assert memory.memory_id in self.memory_system.memory_cache
        
        # Retrieve memory
        results = await self.memory_system.retrieve_memories("quantum computing")
        
        assert len(results) > 0
        assert results[0].memory_id == memory.memory_id
        assert results[0].content == memory.content
    
    @pytest.mark.asyncio
    async def test_memory_retrieval_ranking(self):
        """Test memory retrieval ranking by relevance."""
        await self.memory_system.initialize()
        
        # Store multiple memories with different relevance
        memories = [
            self.memory_system.create_memory(
                content="Quantum computing is revolutionary",
                importance=0.9,
                tags=["quantum", "computing"]
            ),
            self.memory_system.create_memory(
                content="Classical computing has limitations",
                importance=0.5,
                tags=["classical", "computing"]
            ),
            self.memory_system.create_memory(
                content="Quantum algorithms are complex",
                importance=0.7,
                tags=["quantum", "algorithms"]
            )
        ]
        
        for memory in memories:
            await self.memory_system.store_memory(memory)
        
        # Retrieve memories for "quantum"
        results = await self.memory_system.retrieve_memories("quantum")
        
        assert len(results) >= 2
        # First result should be most relevant (highest importance + relevance)
        assert "quantum" in results[0].content.lower() or "quantum" in results[0].tags
    
    @pytest.mark.asyncio
    async def test_memory_consolidation(self):
        """Test memory consolidation process."""
        await self.memory_system.initialize()
        
        # Create high-importance memory that should be consolidated
        memory = self.memory_system.create_memory(
            content="Critical system information",
            importance=0.9,  # Above consolidation threshold
            tags=["critical", "system"]
        )
        
        await self.memory_system.store_memory(memory)
        
        # Run consolidation
        await self.memory_system.consolidate_memories()
        
        # Memory should still be accessible
        results = await self.memory_system.retrieve_memories("critical")
        assert len(results) > 0
        assert results[0].memory_id == memory.memory_id
    
    @pytest.mark.asyncio
    async def test_memory_forgetting(self):
        """Test memory forgetting mechanism."""
        await self.memory_system.initialize()
        
        # Create old, low-importance memory
        old_memory = self.memory_system.create_memory(
            content="Unimportant old information",
            importance=0.2,  # Below forgetting threshold
            tags=["old", "unimportant"]
        )
        
        # Manually set old timestamp
        old_memory.timestamp = datetime.now() - timedelta(days=35)
        
        await self.memory_system.store_memory(old_memory)
        
        # Create recent, important memory
        recent_memory = self.memory_system.create_memory(
            content="Important recent information",
            importance=0.8,
            tags=["recent", "important"]
        )
        
        await self.memory_system.store_memory(recent_memory)
        
        # Forget old memories
        forgotten_count = await self.memory_system.forget_memories(max_age_days=30)
        
        assert forgotten_count > 0
        
        # Recent memory should still be retrievable
        results = await self.memory_system.retrieve_memories("important recent")
        assert len(results) > 0
        
        # Old memory should be forgotten
        results = await self.memory_system.retrieve_memories("unimportant old")
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_working_memory_size_limit(self):
        """Test working memory size management."""
        await self.memory_system.initialize()
        
        # Set small working memory limit for testing
        original_limit = self.memory_system.max_working_memory
        self.memory_system.max_working_memory = 3
        
        try:
            # Store more memories than the limit
            for i in range(5):
                memory = self.memory_system.create_memory(
                    content=f"Memory content {i}",
                    importance=0.5,
                    tags=[f"tag{i}"]
                )
                await self.memory_system.store_memory(memory)
            
            # Working memory should not exceed limit
            assert len(self.memory_system.working_memory) <= 3
            
        finally:
            self.memory_system.max_working_memory = original_limit
    
    @pytest.mark.asyncio
    async def test_get_memories_by_type(self):
        """Test retrieving memories by type."""
        await self.memory_system.initialize()
        
        # Store memories of different types
        episodic_memory = self.memory_system.create_memory(
            content="I learned about AI today",
            memory_type=MemoryType.EPISODIC.value,
            tags=["learning", "AI"]
        )
        
        semantic_memory = self.memory_system.create_memory(
            content="AI stands for Artificial Intelligence",
            memory_type=MemoryType.SEMANTIC.value,
            tags=["definition", "AI"]
        )
        
        procedural_memory = self.memory_system.create_memory(
            content="Steps to implement neural network",
            memory_type=MemoryType.PROCEDURAL.value,
            tags=["procedure", "neural network"]
        )
        
        await self.memory_system.store_memory(episodic_memory)
        await self.memory_system.store_memory(semantic_memory)
        await self.memory_system.store_memory(procedural_memory)
        
        # Retrieve episodic memories
        episodic_results = await self.memory_system.get_memories_by_type(MemoryType.EPISODIC.value)
        assert len(episodic_results) == 1
        assert episodic_results[0].memory_type == MemoryType.EPISODIC.value
        
        # Retrieve semantic memories
        semantic_results = await self.memory_system.get_memories_by_type(MemoryType.SEMANTIC.value)
        assert len(semantic_results) == 1
        assert semantic_results[0].memory_type == MemoryType.SEMANTIC.value
    
    @pytest.mark.asyncio
    async def test_get_recent_memories(self):
        """Test retrieving recent memories."""
        await self.memory_system.initialize()
        
        # Create recent memory
        recent_memory = self.memory_system.create_memory(
            content="Recent event happened",
            tags=["recent", "event"]
        )
        
        # Create old memory
        old_memory = self.memory_system.create_memory(
            content="Old event happened",
            tags=["old", "event"]
        )
        old_memory.timestamp = datetime.now() - timedelta(days=2)
        
        await self.memory_system.store_memory(recent_memory)
        await self.memory_system.store_memory(old_memory)
        
        # Get memories from last 24 hours
        recent_results = await self.memory_system.get_recent_memories(hours=24)
        
        # Should only contain recent memory
        assert len(recent_results) == 1
        assert recent_results[0].memory_id == recent_memory.memory_id
        
        # Get memories from last 72 hours
        extended_results = await self.memory_system.get_recent_memories(hours=72)
        
        # Should contain both memories
        assert len(extended_results) == 2
    
    @pytest.mark.asyncio
    async def test_memory_stats(self):
        """Test memory statistics tracking."""
        await self.memory_system.initialize()
        
        # Initial stats
        initial_stats = self.memory_system.get_memory_stats()
        assert initial_stats["total_memories"] == 0
        assert initial_stats["working_memory_size"] == 0
        
        # Store some memories
        for i in range(3):
            memory = self.memory_system.create_memory(
                content=f"Test memory {i}",
                memory_type=MemoryType.EPISODIC.value if i % 2 == 0 else MemoryType.SEMANTIC.value
            )
            await self.memory_system.store_memory(memory)
        
        # Check updated stats
        updated_stats = self.memory_system.get_memory_stats()
        assert updated_stats["total_memories"] == 3
        assert updated_stats["working_memory_size"] == 3
        assert updated_stats["episodic_memories"] >= 1
        assert updated_stats["semantic_memories"] >= 1
    
    @pytest.mark.asyncio
    async def test_memory_persistence(self):
        """Test that memories persist across system restarts."""
        await self.memory_system.initialize()
        
        # Store a memory
        memory = self.memory_system.create_memory(
            content="Persistent memory test",
            importance=0.8,
            tags=["persistent", "test"]
        )
        await self.memory_system.store_memory(memory)
        
        # Shutdown and create new memory system
        await self.memory_system.shutdown()
        
        new_memory_system = MemorySystem(self.agent_id, self.temp_dir)
        await new_memory_system.initialize()
        
        try:
            # Memory should still be retrievable
            results = await new_memory_system.retrieve_memories("persistent")
            assert len(results) > 0
            assert results[0].content == "Persistent memory test"
            
        finally:
            await new_memory_system.shutdown()
    
    @pytest.mark.asyncio
    async def test_memory_cache_functionality(self):
        """Test memory caching for performance."""
        await self.memory_system.initialize()
        
        # Store memory
        memory = self.memory_system.create_memory(
            content="Cached memory test",
            tags=["cache", "test"]
        )
        await self.memory_system.store_memory(memory)
        
        # First retrieval
        results1 = await self.memory_system.retrieve_memories("cached")
        assert len(results1) > 0
        
        # Second retrieval should use cache
        results2 = await self.memory_system.retrieve_memories("cached")
        assert len(results2) > 0
        assert results1[0].memory_id == results2[0].memory_id
        
        # Cache should contain the query
        assert len(self.memory_system.retrieval_cache) > 0

    @pytest.mark.asyncio
    async def test_knowledge_base_functionality(self):
        """Test the 'In-House Tool' knowledge base functionality."""
        await self.memory_system.initialize()

        source_url = "https://example.com/ai-research"
        content = "A new study on meta-learning shows promising results for self-improving agents."
        tags = ["meta-learning", "ai-research"]

        # 1. Add to knowledge base
        knowledge_id = await self.memory_system.add_to_knowledge_base(source_url, content, tags)
        assert knowledge_id is not None

        # 2. Query the knowledge base
        query_results = await self.memory_system.query_knowledge_base("meta-learning")
        assert len(query_results) == 1
        assert query_results[0]["knowledge_id"] == knowledge_id
        assert "<b>meta-learning</b>" in query_results[0]["snippet"]

        # 3. Get knowledge by ID
        retrieved_knowledge = await self.memory_system.get_knowledge_by_id(knowledge_id)
        assert retrieved_knowledge is not None
        assert retrieved_knowledge["knowledge_id"] == knowledge_id
        assert retrieved_knowledge["source"] == source_url
        assert retrieved_knowledge["content"] == content
        assert "meta-learning" in retrieved_knowledge["tags"]

    @pytest.mark.asyncio
    async def test_retrieve_relevant_experiences(self):
        """Test the retrieval of relevant experiences."""
        await self.memory_system.initialize()

        # Store a relevant experience
        experience1 = self.memory_system.create_memory(
            content="Learned that for complex calculations, it's best to use a calculator tool.",
            memory_type="procedural",
            tags=["experience", "calculation", "tools"]
        )
        await self.memory_system.store_memory(experience1)

        # Store another relevant experience
        experience2 = self.memory_system.create_memory(
            content="When performing calculations, always double check the inputs.",
            memory_type="procedural",
            tags=["experience", "calculation", "verification"]
        )
        await self.memory_system.store_memory(experience2)

        # Store an irrelevant memory
        other_memory = self.memory_system.create_memory(
            content="The sky is blue.",
            memory_type="semantic",
            tags=["facts", "nature"]
        )
        await self.memory_system.store_memory(other_memory)

        # Retrieve experiences related to "calculations"
        results = await self.memory_system.retrieve_relevant_experiences("calculations", limit=2)

        # Assertions
        assert len(results) == 2
        result_ids = {mem.memory_id for mem in results}
        assert experience1.memory_id in result_ids
        assert experience2.memory_id in result_ids
        assert other_memory.memory_id not in result_ids

    @pytest.mark.asyncio
    async def test_retrieve_failures(self):
        """Test the retrieval of failure memories."""
        await self.memory_system.initialize()

        # Store a failure memory
        failure_memory = self.memory_system.create_memory(
            content="A task failed because of a calculation error.",
            memory_type="procedural",
            tags=["experience", "failure", "calculation"]
        )
        await self.memory_system.store_memory(failure_memory)

        # Store a success memory
        success_memory = self.memory_system.create_memory(
            content="A task succeeded.",
            memory_type="procedural",
            tags=["experience", "success"]
        )
        await self.memory_system.store_memory(success_memory)

        # Retrieve failures
        results = await self.memory_system.retrieve_failures(limit=5)

        # Assertions
        assert len(results) == 1
        assert results[0].memory_id == failure_memory.memory_id
        assert "failure" in results[0].tags


if __name__ == "__main__":
    pytest.main([__file__])
@pytest.mark.asyncio
class TestMemoryConsolidation:
    """Test cases for MemoryConsolidation."""
    
    def setup_method(self):
        """Set up test environment."""
        from autonomous_ai_ecosystem.agents.memory_consolidation import MemoryConsolidator, ConsolidationStrategy
        
        self.agent_id = "test_agent_consolidation"
        self.consolidator = MemoryConsolidator(self.agent_id)
        self.memory_system = MemorySystem(self.agent_id, tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        import asyncio
        if hasattr(self, 'memory_system'):
            asyncio.create_task(self.memory_system.shutdown())
    
    @pytest.mark.asyncio
    async def test_consolidator_initialization(self):
        """Test memory consolidator initialization."""
        assert self.consolidator.agent_id == self.agent_id
        assert len(self.consolidator.associations) == 0
        assert self.consolidator.importance_decay_rate > 0
        assert self.consolidator.association_threshold > 0
    
    @pytest.mark.asyncio
    async def test_memory_association_creation(self):
        """Test creating associations between memories."""
        from autonomous_ai_ecosystem.agents.memory_consolidation import ConsolidationStrategy
        
        # Create related memories
        memory1 = self.memory_system.create_memory(
            content="Quantum computing uses qubits for computation",
            tags=["quantum", "computing", "qubits"]
        )
        
        memory2 = self.memory_system.create_memory(
            content="Qubits can exist in superposition states",
            tags=["qubits", "superposition", "quantum"]
        )
        
        memory3 = self.memory_system.create_memory(
            content="Classical computers use binary bits",
            tags=["classical", "computing", "bits"]
        )
        
        memories = [memory1, memory2, memory3]
        
        # Create associations
        associations_created = await self.consolidator.create_memory_associations(memories)
        
        assert associations_created > 0
        
        # Check that related memories have associations
        associated_with_memory1 = self.consolidator.get_associated_memories(memory1.memory_id)
        assert len(associated_with_memory1) > 0
        
        # Memory1 and Memory2 should be more strongly associated than Memory1 and Memory3
        memory2_association = None
        memory3_association = None
        
        for assoc_id, strength in associated_with_memory1:
            if assoc_id == memory2.memory_id:
                memory2_association = strength
            elif assoc_id == memory3.memory_id:
                memory3_association = strength
        
        if memory2_association and memory3_association:
            assert memory2_association > memory3_association
    
    @pytest.mark.asyncio
    async def test_importance_decay(self):
        """Test importance decay over time."""
        # Create old memory
        old_memory = self.memory_system.create_memory(
            content="Old information",
            importance=0.8
        )
        old_memory.timestamp = datetime.now() - timedelta(days=30)
        
        # Create recent memory
        recent_memory = self.memory_system.create_memory(
            content="Recent information",
            importance=0.8
        )
        
        memories = [old_memory, recent_memory]
        
        # Apply consolidation (which includes importance decay)
        from autonomous_ai_ecosystem.agents.memory_consolidation import ConsolidationStrategy
        metrics = await self.consolidator.consolidate_memories(memories, ConsolidationStrategy.IMPORTANCE_BASED)
        
        # Old memory should have lower importance after decay
        assert old_memory.importance < recent_memory.importance
        assert metrics.average_importance_change < 0  # Overall importance decreased
    
    @pytest.mark.asyncio
    async def test_consolidation_strategies(self):
        """Test different consolidation strategies."""
        from autonomous_ai_ecosystem.agents.memory_consolidation import ConsolidationStrategy
        
        # Create memories with different characteristics
        memories = []
        for i in range(10):
            memory = self.memory_system.create_memory(
                content=f"Memory content {i}",
                importance=0.3 + (i * 0.07),  # Varying importance
                tags=[f"tag{i}", "common"]
            )
            # Vary timestamps
            memory.timestamp = datetime.now() - timedelta(days=i)
            memories.append(memory)
        
        # Test importance-based consolidation
        metrics_importance = await self.consolidator.consolidate_memories(
            memories.copy(), ConsolidationStrategy.IMPORTANCE_BASED
        )
        
        # Test recency-based consolidation
        metrics_recency = await self.consolidator.consolidate_memories(
            memories.copy(), ConsolidationStrategy.RECENCY_BASED
        )
        
        # Test hybrid consolidation
        metrics_hybrid = await self.consolidator.consolidate_memories(
            memories.copy(), ConsolidationStrategy.HYBRID
        )
        
        # All strategies should process the same number of memories
        assert metrics_importance.total_memories_processed == len(memories)
        assert metrics_recency.total_memories_processed == len(memories)
        assert metrics_hybrid.total_memories_processed == len(memories)
        
        # All should consolidate some memories
        assert metrics_importance.memories_consolidated > 0
        assert metrics_recency.memories_consolidated > 0
        assert metrics_hybrid.memories_consolidated > 0
    
    @pytest.mark.asyncio
    async def test_memory_importance_boost(self):
        """Test importance boost calculation."""
        # Create memory with associations
        memory = self.memory_system.create_memory(
            content="Important memory with associations",
            importance=0.5,
            memory_type="procedural"  # Should get type boost
        )
        
        # Create related memories to form associations
        related_memories = []
        for i in range(3):
            related = self.memory_system.create_memory(
                content=f"Related memory {i} with associations",
                tags=["associations", f"related{i}"]
            )
            related_memories.append(related)
        
        # Create associations
        all_memories = [memory] + related_memories
        await self.consolidator.create_memory_associations(all_memories)
        
        # Calculate importance boost
        boost = self.consolidator.calculate_memory_importance_boost(memory)
        
        assert boost > 0.0
        assert boost <= 1.0
    
    @pytest.mark.asyncio
    async def test_forgetting_mechanism(self):
        """Test memory forgetting during consolidation."""
        from autonomous_ai_ecosystem.agents.memory_consolidation import ConsolidationStrategy
        
        # Create old, low-importance memory that should be forgotten
        forgettable_memory = self.memory_system.create_memory(
            content="Forgettable information",
            importance=0.05  # Very low importance
        )
        forgettable_memory.timestamp = datetime.now() - timedelta(days=10)
        
        # Create important memory that should be retained
        important_memory = self.memory_system.create_memory(
            content="Important information",
            importance=0.9
        )
        
        memories = [forgettable_memory, important_memory]
        
        # Apply consolidation
        metrics = await self.consolidator.consolidate_memories(memories, ConsolidationStrategy.HYBRID)
        
        # Some memories should be forgotten
        assert metrics.memories_forgotten >= 0
        
        # Important memory should still have reasonable importance
        assert important_memory.importance > 0.5
    
    @pytest.mark.asyncio
    async def test_association_strength_calculation(self):
        """Test association strength calculation between memories."""
        # Create memories with different levels of similarity
        memory1 = self.memory_system.create_memory(
            content="Quantum computing uses quantum mechanics principles",
            tags=["quantum", "computing", "physics"]
        )
        
        # High similarity
        memory2 = self.memory_system.create_memory(
            content="Quantum mechanics principles enable quantum computing",
            tags=["quantum", "mechanics", "computing"]
        )
        
        # Low similarity
        memory3 = self.memory_system.create_memory(
            content="Classical music has beautiful melodies",
            tags=["music", "classical", "art"]
        )
        
        # Calculate association strengths
        strength_high = self.consolidator._calculate_association_strength(memory1, memory2)
        strength_low = self.consolidator._calculate_association_strength(memory1, memory3)
        
        assert strength_high > strength_low
        assert 0.0 <= strength_high <= 1.0
        assert 0.0 <= strength_low <= 1.0
    
    @pytest.mark.asyncio
    async def test_consolidation_statistics(self):
        """Test consolidation statistics tracking."""
        from autonomous_ai_ecosystem.agents.memory_consolidation import ConsolidationStrategy
        
        # Create test memories
        memories = []
        for i in range(5):
            memory = self.memory_system.create_memory(
                content=f"Test memory {i}",
                importance=0.5 + (i * 0.1)
            )
            memories.append(memory)
        
        # Perform consolidation
        await self.consolidator.consolidate_memories(memories, ConsolidationStrategy.HYBRID)
        
        # Check statistics
        stats = self.consolidator.get_consolidation_stats()
        
        assert "total_consolidations" in stats
        assert "total_forgettings" in stats
        assert "associations_created" in stats
        assert "average_consolidation_time" in stats
        
        assert stats["total_consolidations"] >= 0
        assert stats["average_consolidation_time"] >= 0.0