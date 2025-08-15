"""
Tests for the shared knowledge dataset management system.
"""

import pytest
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.knowledge.dataset_manager import (
    DatasetManager,
    SharedKnowledgeDataset,
    KnowledgeEntry,
    KnowledgeContribution,
    ValidationResult,
    KnowledgeCategory,
    KnowledgeSource,
    KnowledgeQuality
)


class TestKnowledgeEntry:
    """Test the KnowledgeEntry class."""
    
    def test_entry_creation(self):
        """Test creating a knowledge entry."""
        entry = KnowledgeEntry(
            entry_id="entry_1",
            title="Test Knowledge",
            content="This is test knowledge content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE,
            contributor_id="agent_1"
        )
        
        assert entry.entry_id == "entry_1"
        assert entry.title == "Test Knowledge"
        assert entry.category == KnowledgeCategory.FACTUAL
        assert entry.source == KnowledgeSource.AGENT_EXPERIENCE
        assert entry.contributor_id == "agent_1"
        assert entry.quality_score == 0.5
        assert entry.confidence_level == KnowledgeQuality.UNVERIFIED
        assert entry.content_hash != ""
    
    def test_content_hash_generation(self):
        """Test content hash generation."""
        entry1 = KnowledgeEntry(
            entry_id="entry_1",
            title="Test",
            content="Content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE,
            contributor_id="agent_1"
        )
        
        entry2 = KnowledgeEntry(
            entry_id="entry_2",
            title="Test",
            content="Content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE,
            contributor_id="agent_2"
        )
        
        # Same content should generate same hash
        assert entry1.content_hash == entry2.content_hash
    
    def test_content_update(self):
        """Test updating entry content."""
        entry = KnowledgeEntry(
            entry_id="entry_1",
            title="Original Title",
            content="Original content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE,
            contributor_id="agent_1"
        )
        
        original_hash = entry.content_hash
        original_version = entry.version
        
        entry.update_content("New Title", "New content")
        
        assert entry.title == "New Title"
        assert entry.content == "New content"
        assert entry.version == original_version + 1
        assert entry.content_hash != original_hash
    
    def test_add_validation(self):
        """Test adding validation to an entry."""
        entry = KnowledgeEntry(
            entry_id="entry_1",
            title="Test",
            content="Content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE,
            contributor_id="agent_1"
        )
        
        # Add first validation
        entry.add_validation("validator_1", 0.8, "Good quality")
        
        assert entry.validation_count == 1
        assert entry.validation_score == 0.8
        assert entry.confidence_level == KnowledgeQuality.UNVERIFIED  # Need more validations
        
        # Add more validations
        entry.add_validation("validator_2", 0.9, "Excellent")
        entry.add_validation("validator_3", 0.85, "Very good")
        
        assert entry.validation_count == 3
        assert abs(entry.validation_score - 0.85) < 0.01  # Average of 0.8, 0.9, 0.85
        assert entry.confidence_level == KnowledgeQuality.HIGH_CONFIDENCE


class TestSharedKnowledgeDataset:
    """Test the SharedKnowledgeDataset class."""
    
    def test_dataset_creation(self):
        """Test creating a shared knowledge dataset."""
        dataset = SharedKnowledgeDataset(
            dataset_id="dataset_1",
            name="Test Dataset",
            description="A test dataset",
            created_by="agent_1"
        )
        
        assert dataset.dataset_id == "dataset_1"
        assert dataset.name == "Test Dataset"
        assert dataset.created_by == "agent_1"
        assert dataset.public is True
        assert dataset.total_entries == 0
        assert "agent_1" in dataset.contributors
        assert "agent_1" in dataset.moderators


class TestDatasetManager:
    """Test the DatasetManager class."""
    
    @pytest.fixture
    async def dataset_manager(self):
        """Create a test dataset manager."""
        # Use temporary directory for testing
        temp_dir = tempfile.mkdtemp()
        manager = DatasetManager("test_manager", temp_dir)
        await manager.initialize()
        
        yield manager
        
        # Cleanup
        await manager.shutdown()
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test dataset manager initialization."""
        temp_dir = tempfile.mkdtemp()
        try:
            manager = DatasetManager("test_manager", temp_dir)
            await manager.initialize()
            
            assert len(manager.datasets) == 0
            assert len(manager.knowledge_entries) == 0
            assert manager.stats["total_entries"] == 0
            
            await manager.shutdown()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_create_dataset(self, dataset_manager):
        """Test creating a dataset."""
        result = await dataset_manager.create_dataset(
            creator_id="agent_1",
            name="Test Dataset",
            description="A test dataset for testing",
            public=True
        )
        
        assert result["success"] is True
        assert "dataset_id" in result
        assert result["name"] == "Test Dataset"
        assert result["public"] is True
        
        # Check dataset was stored
        dataset_id = result["dataset_id"]
        assert dataset_id in dataset_manager.datasets
        
        dataset = dataset_manager.datasets[dataset_id]
        assert dataset.name == "Test Dataset"
        assert dataset.created_by == "agent_1"
        assert "agent_1" in dataset.contributors
    
    @pytest.mark.asyncio
    async def test_contribute_knowledge(self, dataset_manager):
        """Test contributing knowledge to a dataset."""
        # First create a dataset
        dataset_result = await dataset_manager.create_dataset(
            creator_id="agent_1",
            name="Test Dataset",
            description="Test dataset"
        )
        dataset_id = dataset_result["dataset_id"]
        
        # Contribute knowledge
        result = await dataset_manager.contribute_knowledge(
            contributor_id="agent_2",
            dataset_id=dataset_id,
            title="Python Programming Basics",
            content="Python is a high-level programming language known for its simplicity and readability.",
            category=KnowledgeCategory.TECHNICAL,
            source=KnowledgeSource.AGENT_EXPERIENCE,
            tags=["python", "programming", "basics"]
        )
        
        assert result["success"] is True
        assert "entry_id" in result
        assert "contribution_id" in result
        assert result["quality_score"] == 0.5  # Default quality score
        
        # Check entry was stored
        entry_id = result["entry_id"]
        assert entry_id in dataset_manager.knowledge_entries
        
        entry = dataset_manager.knowledge_entries[entry_id]
        assert entry.title == "Python Programming Basics"
        assert entry.contributor_id == "agent_2"
        assert entry.category == KnowledgeCategory.TECHNICAL
        assert "python" in entry.tags
    
    @pytest.mark.asyncio
    async def test_contribute_to_nonexistent_dataset(self, dataset_manager):
        """Test contributing to a nonexistent dataset."""
        result = await dataset_manager.contribute_knowledge(
            contributor_id="agent_1",
            dataset_id="nonexistent",
            title="Test",
            content="Test content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE
        )
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_knowledge(self, dataset_manager):
        """Test validating a knowledge entry."""
        # Create dataset and contribute knowledge
        dataset_result = await dataset_manager.create_dataset("agent_1", "Test Dataset", "Test")
        dataset_id = dataset_result["dataset_id"]
        
        contrib_result = await dataset_manager.contribute_knowledge(
            contributor_id="agent_1",
            dataset_id=dataset_id,
            title="Test Knowledge",
            content="Test content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE
        )
        entry_id = contrib_result["entry_id"]
        
        # Validate the knowledge
        result = await dataset_manager.validate_knowledge(
            validator_id="agent_2",
            entry_id=entry_id,
            score=0.8,
            feedback="Good quality content"
        )
        
        assert result["success"] is True
        assert result["validation_score"] == 0.8
        assert result["validation_count"] == 1
        
        # Check validation was stored
        assert entry_id in dataset_manager.validations
        validations = dataset_manager.validations[entry_id]
        assert len(validations) == 1
        assert validations[0].validator_id == "agent_2"
        assert validations[0].score == 0.8
    
    @pytest.mark.asyncio
    async def test_validate_own_contribution(self, dataset_manager):
        """Test that agents cannot validate their own contributions."""
        # Create dataset and contribute knowledge
        dataset_result = await dataset_manager.create_dataset("agent_1", "Test Dataset", "Test")
        dataset_id = dataset_result["dataset_id"]
        
        contrib_result = await dataset_manager.contribute_knowledge(
            contributor_id="agent_1",
            dataset_id=dataset_id,
            title="Test Knowledge",
            content="Test content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE
        )
        entry_id = contrib_result["entry_id"]
        
        # Try to validate own contribution
        result = await dataset_manager.validate_knowledge(
            validator_id="agent_1",  # Same as contributor
            entry_id=entry_id,
            score=0.9
        )
        
        assert result["success"] is False
        assert "Cannot validate your own" in result["error"]
    
    @pytest.mark.asyncio
    async def test_duplicate_validation(self, dataset_manager):
        """Test that agents cannot validate the same entry twice."""
        # Create dataset and contribute knowledge
        dataset_result = await dataset_manager.create_dataset("agent_1", "Test Dataset", "Test")
        dataset_id = dataset_result["dataset_id"]
        
        contrib_result = await dataset_manager.contribute_knowledge(
            contributor_id="agent_1",
            dataset_id=dataset_id,
            title="Test Knowledge",
            content="Test content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE
        )
        entry_id = contrib_result["entry_id"]
        
        # First validation
        await dataset_manager.validate_knowledge("agent_2", entry_id, 0.8)
        
        # Try to validate again
        result = await dataset_manager.validate_knowledge("agent_2", entry_id, 0.9)
        
        assert result["success"] is False
        assert "Already validated" in result["error"]
    
    @pytest.mark.asyncio
    async def test_search_knowledge(self, dataset_manager):
        """Test searching for knowledge entries."""
        # Create dataset and add some knowledge
        dataset_result = await dataset_manager.create_dataset("agent_1", "Test Dataset", "Test")
        dataset_id = dataset_result["dataset_id"]
        
        # Add multiple entries
        await dataset_manager.contribute_knowledge(
            contributor_id="agent_1",
            dataset_id=dataset_id,
            title="Python Programming",
            content="Python is a programming language",
            category=KnowledgeCategory.TECHNICAL,
            source=KnowledgeSource.AGENT_EXPERIENCE,
            tags=["python", "programming"]
        )
        
        await dataset_manager.contribute_knowledge(
            contributor_id="agent_2",
            dataset_id=dataset_id,
            title="JavaScript Basics",
            content="JavaScript is used for web development",
            category=KnowledgeCategory.TECHNICAL,
            source=KnowledgeSource.WEB_SCRAPING,
            tags=["javascript", "web"]
        )
        
        # Search for Python
        results = await dataset_manager.search_knowledge("python")
        
        assert len(results) == 1
        assert results[0]["title"] == "Python Programming"
        assert "python" in results[0]["tags"]
        
        # Search by category
        tech_results = await dataset_manager.search_knowledge(
            query="",
            category=KnowledgeCategory.TECHNICAL
        )
        
        assert len(tech_results) == 2
        
        # Search with quality filter
        high_quality_results = await dataset_manager.search_knowledge(
            query="",
            min_quality=0.8
        )
        
        # Should return no results since default quality is 0.5
        assert len(high_quality_results) == 0
    
    @pytest.mark.asyncio
    async def test_get_knowledge_entry(self, dataset_manager):
        """Test getting a specific knowledge entry."""
        # Create dataset and contribute knowledge
        dataset_result = await dataset_manager.create_dataset("agent_1", "Test Dataset", "Test")
        dataset_id = dataset_result["dataset_id"]
        
        contrib_result = await dataset_manager.contribute_knowledge(
            contributor_id="agent_1",
            dataset_id=dataset_id,
            title="Test Knowledge",
            content="Test content with detailed information",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE,
            tags=["test", "knowledge"]
        )
        entry_id = contrib_result["entry_id"]
        
        # Get the entry
        result = dataset_manager.get_knowledge_entry(entry_id, "agent_2")
        
        # Should be async, let's run it
        result = await asyncio.coroutine(lambda: result)() if asyncio.iscoroutine(result) else result
        
        assert "entry_id" in result
        assert result["title"] == "Test Knowledge"
        assert result["content"] == "Test content with detailed information"
        assert result["category"] == KnowledgeCategory.FACTUAL.value
        assert result["contributor_id"] == "agent_1"
        assert "validations" in result
        assert "related_entries" in result
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_entry(self, dataset_manager):
        """Test getting a nonexistent knowledge entry."""
        result = dataset_manager.get_knowledge_entry("nonexistent", "agent_1")
        
        # Handle both sync and async cases
        if asyncio.iscoroutine(result):
            result = await result
        
        assert "error" in result
    
    def test_get_dataset_info(self, dataset_manager):
        """Test getting dataset information."""
        # This test needs to be run after dataset manager initialization
        asyncio.run(self._test_get_dataset_info_async(dataset_manager))
    
    async def _test_get_dataset_info_async(self, dataset_manager):
        """Async helper for dataset info test."""
        # Create dataset
        dataset_result = await dataset_manager.create_dataset("agent_1", "Test Dataset", "Test dataset")
        dataset_id = dataset_result["dataset_id"]
        
        # Add some knowledge
        await dataset_manager.contribute_knowledge(
            contributor_id="agent_1",
            dataset_id=dataset_id,
            title="Test Entry",
            content="Test content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE
        )
        
        # Get dataset info
        info = dataset_manager.get_dataset_info(dataset_id)
        
        assert "dataset_id" in info
        assert info["name"] == "Test Dataset"
        assert info["created_by"] == "agent_1"
        assert "total_entries" in info
        assert "quality_distribution" in info
        assert "category_distribution" in info
    
    def test_get_agent_contributions(self, dataset_manager):
        """Test getting agent contributions."""
        asyncio.run(self._test_get_agent_contributions_async(dataset_manager))
    
    async def _test_get_agent_contributions_async(self, dataset_manager):
        """Async helper for agent contributions test."""
        # Create dataset and add contributions
        dataset_result = await dataset_manager.create_dataset("agent_1", "Test Dataset", "Test")
        dataset_id = dataset_result["dataset_id"]
        
        await dataset_manager.contribute_knowledge(
            contributor_id="agent_1",
            dataset_id=dataset_id,
            title="First Contribution",
            content="First content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE
        )
        
        await dataset_manager.contribute_knowledge(
            contributor_id="agent_1",
            dataset_id=dataset_id,
            title="Second Contribution",
            content="Second content",
            category=KnowledgeCategory.TECHNICAL,
            source=KnowledgeSource.AGENT_REASONING
        )
        
        # Get contributions
        contributions = dataset_manager.get_agent_contributions("agent_1")
        
        assert "agent_id" in contributions
        assert contributions["total_contributions"] == 2
        assert "average_quality" in contributions
        assert "category_breakdown" in contributions
        assert "recent_contributions" in contributions
        assert len(contributions["recent_contributions"]) == 2
    
    def test_get_system_stats(self, dataset_manager):
        """Test getting system statistics."""
        asyncio.run(self._test_get_system_stats_async(dataset_manager))
    
    async def _test_get_system_stats_async(self, dataset_manager):
        """Async helper for system stats test."""
        # Create some data
        dataset_result = await dataset_manager.create_dataset("agent_1", "Test Dataset", "Test")
        dataset_id = dataset_result["dataset_id"]
        
        await dataset_manager.contribute_knowledge(
            contributor_id="agent_1",
            dataset_id=dataset_id,
            title="Test Entry",
            content="Test content",
            category=KnowledgeCategory.FACTUAL,
            source=KnowledgeSource.AGENT_EXPERIENCE
        )
        
        # Get system stats
        stats = dataset_manager.get_system_stats()
        
        assert "total_datasets" in stats
        assert "total_entries" in stats
        assert "total_contributors" in stats
        assert "quality_distribution" in stats
        assert "category_distribution" in stats
        assert "source_distribution" in stats
        assert "system_stats" in stats
        assert stats["total_datasets"] >= 1
        assert stats["total_entries"] >= 1


class TestValidationResult:
    """Test the ValidationResult class."""
    
    def test_validation_result_creation(self):
        """Test creating a validation result."""
        validation = ValidationResult(
            validator_id="agent_1",
            entry_id="entry_1",
            score=0.85,
            feedback="Excellent quality content",
            validation_criteria={"accuracy": 0.9, "relevance": 0.8}
        )
        
        assert validation.validator_id == "agent_1"
        assert validation.entry_id == "entry_1"
        assert validation.score == 0.85
        assert validation.feedback == "Excellent quality content"
        assert validation.validation_criteria["accuracy"] == 0.9
        assert validation.timestamp is not None


class TestKnowledgeContribution:
    """Test the KnowledgeContribution class."""
    
    def test_contribution_creation(self):
        """Test creating a knowledge contribution."""
        contribution = KnowledgeContribution(
            contribution_id="contrib_1",
            contributor_id="agent_1",
            entry_id="entry_1",
            contribution_type="create",
            description="Created new knowledge entry"
        )
        
        assert contribution.contribution_id == "contrib_1"
        assert contribution.contributor_id == "agent_1"
        assert contribution.entry_id == "entry_1"
        assert contribution.contribution_type == "create"
        assert contribution.status == "pending"
        assert contribution.quality_impact == 0.0


if __name__ == "__main__":
    pytest.main([__file__])