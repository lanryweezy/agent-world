"""
Shared knowledge dataset management system for the autonomous AI ecosystem.

This module implements distributed knowledge storage, contribution workflows,
data quality assessment, and collective knowledge building.
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
import os

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class KnowledgeCategory(Enum):
    """Categories of knowledge in the dataset."""
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    CONCEPTUAL = "conceptual"
    EXPERIENTIAL = "experiential"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    SOCIAL = "social"
    PROBLEM_SOLVING = "problem_solving"
    LINGUISTIC = "linguistic"
    DOMAIN_SPECIFIC = "domain_specific"


class KnowledgeSource(Enum):
    """Sources of knowledge entries."""
    AGENT_EXPERIENCE = "agent_experience"
    WEB_SCRAPING = "web_scraping"
    HUMAN_INPUT = "human_input"
    AGENT_REASONING = "agent_reasoning"
    COLLABORATIVE_WORK = "collaborative_work"
    EXPERIMENT_RESULT = "experiment_result"
    LITERATURE_REVIEW = "literature_review"
    PEER_SHARING = "peer_sharing"


class KnowledgeQuality(Enum):
    """Quality levels for knowledge entries."""
    UNVERIFIED = 1
    LOW_CONFIDENCE = 2
    MODERATE_CONFIDENCE = 3
    HIGH_CONFIDENCE = 4
    VERIFIED = 5


@dataclass
class KnowledgeEntry:
    """Represents a single knowledge entry in the dataset."""
    entry_id: str
    title: str
    content: str
    category: KnowledgeCategory
    source: KnowledgeSource
    
    # Metadata
    contributor_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Quality and validation
    quality_score: float = 0.5  # 0.0 to 1.0
    confidence_level: KnowledgeQuality = KnowledgeQuality.UNVERIFIED
    validation_count: int = 0
    validation_score: float = 0.0
    
    # Content structure
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    related_entries: List[str] = field(default_factory=list)  # entry_ids
    
    # Usage statistics
    access_count: int = 0
    citation_count: int = 0
    usefulness_score: float = 0.0
    
    # Versioning
    version: int = 1
    parent_entry_id: Optional[str] = None
    
    # Content hash for deduplication
    content_hash: str = field(default="")
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate content hash after initialization."""
        if not self.content_hash:
            self.content_hash = self._generate_content_hash()
    
    def _generate_content_hash(self) -> str:
        """Generate a hash of the content for deduplication."""
        content_str = f"{self.title}|{self.content}|{self.category.value}"
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def update_content(self, new_title: str, new_content: str) -> None:
        """Update the content and regenerate hash."""
        self.title = new_title
        self.content = new_content
        self.updated_at = datetime.now()
        self.version += 1
        self.content_hash = self._generate_content_hash()
    
    def add_validation(self, validator_id: str, score: float, feedback: str = "") -> None:
        """Add a validation score from another agent."""
        self.validation_count += 1
        # Update running average
        total_score = self.validation_score * (self.validation_count - 1) + score
        self.validation_score = total_score / self.validation_count
        
        # Update confidence level based on validation
        if self.validation_count >= 3:
            if self.validation_score >= 0.9:
                self.confidence_level = KnowledgeQuality.VERIFIED
            elif self.validation_score >= 0.7:
                self.confidence_level = KnowledgeQuality.HIGH_CONFIDENCE
            elif self.validation_score >= 0.5:
                self.confidence_level = KnowledgeQuality.MODERATE_CONFIDENCE
            else:
                self.confidence_level = KnowledgeQuality.LOW_CONFIDENCE


@dataclass
class KnowledgeContribution:
    """Represents a contribution to the knowledge dataset."""
    contribution_id: str
    contributor_id: str
    entry_id: str
    contribution_type: str  # create, update, validate, tag, relate
    
    # Contribution details
    description: str
    changes: Dict[str, Any] = field(default_factory=dict)
    
    # Status and timing
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime = field(default_factory=datetime.now)
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None
    
    # Quality assessment
    quality_impact: float = 0.0
    reviewer_feedback: str = ""


@dataclass
class ValidationResult:
    """Result of knowledge entry validation."""
    validator_id: str
    entry_id: str
    score: float  # 0.0 to 1.0
    feedback: str
    validation_criteria: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SharedKnowledgeDataset:
    """Represents a shared knowledge dataset."""
    dataset_id: str
    name: str
    description: str
    
    # Dataset metadata
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Access control
    public: bool = True
    contributors: Set[str] = field(default_factory=set)
    moderators: Set[str] = field(default_factory=set)
    
    # Dataset statistics
    total_entries: int = 0
    total_contributors: int = 0
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    category_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Configuration
    min_validation_count: int = 2
    auto_approve_threshold: float = 0.8
    quality_threshold: float = 0.6


class DatasetManager(AgentModule):
    """
    Manages shared knowledge datasets for the autonomous AI ecosystem.
    
    Provides distributed knowledge storage, contribution workflows,
    quality assessment, and collective knowledge building capabilities.
    """
    
    def __init__(self, agent_id: str, storage_path: str = "knowledge_datasets"):
        super().__init__(agent_id)
        self.storage_path = storage_path
        self.logger = get_agent_logger(agent_id, "dataset_manager")
        
        # Core data structures
        self.datasets: Dict[str, SharedKnowledgeDataset] = {}
        self.knowledge_entries: Dict[str, KnowledgeEntry] = {}
        self.contributions: Dict[str, KnowledgeContribution] = {}
        self.validations: Dict[str, List[ValidationResult]] = {}  # entry_id -> validations
        
        # Content indices for fast search
        self.content_hash_index: Dict[str, str] = {}  # hash -> entry_id
        self.keyword_index: Dict[str, Set[str]] = {}  # keyword -> entry_ids
        self.category_index: Dict[KnowledgeCategory, Set[str]] = {}  # category -> entry_ids
        self.contributor_index: Dict[str, Set[str]] = {}  # contributor_id -> entry_ids
        
        # System configuration
        self.config = {
            "max_entries_per_dataset": 100000,
            "max_content_length": 50000,
            "min_quality_score": 0.3,
            "duplicate_threshold": 0.95,
            "validation_reward": 5.0,
            "contribution_reward": 10.0,
            "auto_cleanup_days": 90,
            "backup_interval_hours": 24,
            "max_related_entries": 10
        }
        
        # Statistics
        self.stats = {
            "total_entries": 0,
            "total_contributions": 0,
            "total_validations": 0,
            "quality_improvements": 0,
            "duplicate_detections": 0,
            "knowledge_queries": 0
        }
        
        # Counters
        self.entry_counter = 0
        self.contribution_counter = 0
        self.dataset_counter = 0
        
        # Database connection
        self.db_path = os.path.join(storage_path, "knowledge.db")
        self.db_connection = None
        
        self.logger.info("Dataset manager initialized")
    
    async def initialize(self) -> None:
        """Initialize the dataset manager."""
        try:
            # Create storage directory
            os.makedirs(self.storage_path, exist_ok=True)
            
            # Initialize database
            await self._initialize_database()
            
            # Load existing data
            await self._load_datasets()
            
            # Start background processes
            asyncio.create_task(self._quality_monitor())
            asyncio.create_task(self._cleanup_processor())
            asyncio.create_task(self._backup_processor())
            
            self.logger.info("Dataset manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize dataset manager: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the dataset manager."""
        try:
            # Save all data
            await self._save_datasets()
            
            # Close database connection
            if self.db_connection:
                self.db_connection.close()
            
            self.logger.info("Dataset manager shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during dataset manager shutdown: {e}")
    
    async def create_dataset(
        self,
        creator_id: str,
        name: str,
        description: str,
        public: bool = True
    ) -> Dict[str, Any]:
        """Create a new shared knowledge dataset."""
        try:
            self.dataset_counter += 1
            dataset_id = f"dataset_{self.dataset_counter}_{datetime.now().timestamp()}"
            
            dataset = SharedKnowledgeDataset(
                dataset_id=dataset_id,
                name=name,
                description=description,
                created_by=creator_id,
                public=public
            )
            
            # Add creator as contributor and moderator
            dataset.contributors.add(creator_id)
            dataset.moderators.add(creator_id)
            
            self.datasets[dataset_id] = dataset
            
            # Save to database
            await self._save_dataset_to_db(dataset)
            
            log_agent_event(
                self.agent_id,
                "dataset_created",
                {
                    "dataset_id": dataset_id,
                    "creator_id": creator_id,
                    "name": name,
                    "public": public
                }
            )
            
            result = {
                "success": True,
                "dataset_id": dataset_id,
                "name": name,
                "public": public
            }
            
            self.logger.info(f"Created dataset: {name} by {creator_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create dataset: {e}")
            return {"success": False, "error": str(e)}
    
    async def contribute_knowledge(
        self,
        contributor_id: str,
        dataset_id: str,
        title: str,
        content: str,
        category: KnowledgeCategory,
        source: KnowledgeSource,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Contribute new knowledge to a dataset."""
        try:
            if dataset_id not in self.datasets:
                return {"success": False, "error": "Dataset not found"}
            
            dataset = self.datasets[dataset_id]
            
            # Check permissions
            if not dataset.public and contributor_id not in dataset.contributors:
                return {"success": False, "error": "Not authorized to contribute to this dataset"}
            
            # Check dataset limits
            if dataset.total_entries >= self.config["max_entries_per_dataset"]:
                return {"success": False, "error": "Dataset at maximum capacity"}
            
            # Validate content
            if len(content) > self.config["max_content_length"]:
                return {"success": False, "error": "Content too long"}
            
            # Create knowledge entry
            self.entry_counter += 1
            entry_id = f"entry_{self.entry_counter}_{datetime.now().timestamp()}"
            
            entry = KnowledgeEntry(
                entry_id=entry_id,
                title=title,
                content=content,
                category=category,
                source=source,
                contributor_id=contributor_id,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            # Check for duplicates
            duplicate_entry_id = await self._check_for_duplicates(entry, dataset_id)
            if duplicate_entry_id:
                return {
                    "success": False,
                    "error": "Similar content already exists",
                    "duplicate_entry_id": duplicate_entry_id
                }
            
            # Extract keywords
            entry.keywords = await self._extract_keywords(content)
            
            # Store entry
            self.knowledge_entries[entry_id] = entry
            
            # Update indices
            await self._update_indices(entry)
            
            # Update dataset statistics
            dataset.total_entries += 1
            dataset.updated_at = datetime.now()
            
            if contributor_id not in dataset.contributors:
                dataset.contributors.add(contributor_id)
                dataset.total_contributors += 1
            
            # Update category distribution
            category_key = category.value
            dataset.category_distribution[category_key] = dataset.category_distribution.get(category_key, 0) + 1
            
            # Create contribution record
            contribution = await self._create_contribution_record(
                contributor_id, entry_id, "create", "New knowledge entry created"
            )
            
            # Save to database
            await self._save_entry_to_db(entry, dataset_id)
            
            # Update statistics
            self.stats["total_entries"] += 1
            self.stats["total_contributions"] += 1
            
            log_agent_event(
                self.agent_id,
                "knowledge_contributed",
                {
                    "entry_id": entry_id,
                    "contributor_id": contributor_id,
                    "dataset_id": dataset_id,
                    "category": category.value,
                    "title": title
                }
            )
            
            result = {
                "success": True,
                "entry_id": entry_id,
                "contribution_id": contribution.contribution_id,
                "quality_score": entry.quality_score,
                "content_hash": entry.content_hash
            }
            
            self.logger.info(f"Knowledge contributed: {title} by {contributor_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to contribute knowledge: {e}")
            return {"success": False, "error": str(e)}
    
    async def validate_knowledge(
        self,
        validator_id: str,
        entry_id: str,
        score: float,
        feedback: str = "",
        criteria: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Validate a knowledge entry."""
        try:
            if entry_id not in self.knowledge_entries:
                return {"success": False, "error": "Knowledge entry not found"}
            
            entry = self.knowledge_entries[entry_id]
            
            # Prevent self-validation
            if validator_id == entry.contributor_id:
                return {"success": False, "error": "Cannot validate your own contributions"}
            
            # Check if already validated by this agent
            existing_validations = self.validations.get(entry_id, [])
            if any(v.validator_id == validator_id for v in existing_validations):
                return {"success": False, "error": "Already validated by this agent"}
            
            # Validate score range
            score = max(0.0, min(1.0, score))
            
            # Create validation result
            validation = ValidationResult(
                validator_id=validator_id,
                entry_id=entry_id,
                score=score,
                feedback=feedback,
                validation_criteria=criteria or {}
            )
            
            # Store validation
            if entry_id not in self.validations:
                self.validations[entry_id] = []
            self.validations[entry_id].append(validation)
            
            # Update entry with validation
            entry.add_validation(validator_id, score, feedback)
            
            # Create contribution record
            await self._create_contribution_record(
                validator_id, entry_id, "validate", f"Validation score: {score}"
            )
            
            # Update statistics
            self.stats["total_validations"] += 1
            if score > entry.quality_score:
                self.stats["quality_improvements"] += 1
            
            # Save to database
            await self._save_validation_to_db(validation)
            await self._update_entry_in_db(entry)
            
            log_agent_event(
                self.agent_id,
                "knowledge_validated",
                {
                    "entry_id": entry_id,
                    "validator_id": validator_id,
                    "score": score,
                    "new_confidence": entry.confidence_level.value
                }
            )
            
            result = {
                "success": True,
                "validation_score": score,
                "entry_quality_score": entry.quality_score,
                "confidence_level": entry.confidence_level.value,
                "validation_count": entry.validation_count
            }
            
            self.logger.info(f"Knowledge validated: {entry_id} by {validator_id} (score: {score})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to validate knowledge: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_knowledge(
        self,
        query: str,
        dataset_id: Optional[str] = None,
        category: Optional[KnowledgeCategory] = None,
        min_quality: float = 0.0,
        max_results: int = 50,
        include_content: bool = True
    ) -> List[Dict[str, Any]]:
        """Search for knowledge entries."""
        try:
            self.stats["knowledge_queries"] += 1
            
            # Get candidate entries
            candidate_entries = []
            
            if dataset_id:
                # Search within specific dataset
                dataset_entries = await self._get_dataset_entries(dataset_id)
                candidate_entries = [self.knowledge_entries[eid] for eid in dataset_entries if eid in self.knowledge_entries]
            else:
                # Search all entries
                candidate_entries = list(self.knowledge_entries.values())
            
            # Apply filters
            filtered_entries = []
            query_lower = query.lower()
            
            for entry in candidate_entries:
                # Category filter
                if category and entry.category != category:
                    continue
                
                # Quality filter
                if entry.quality_score < min_quality:
                    continue
                
                # Text search
                if query:
                    searchable_text = f"{entry.title} {entry.content} {' '.join(entry.tags)} {' '.join(entry.keywords)}".lower()
                    if query_lower not in searchable_text:
                        continue
                
                filtered_entries.append(entry)
            
            # Sort by relevance and quality
            scored_entries = []
            for entry in filtered_entries:
                relevance_score = await self._calculate_relevance_score(entry, query)
                quality_score = entry.quality_score
                combined_score = (relevance_score * 0.7) + (quality_score * 0.3)
                scored_entries.append((entry, combined_score))
            
            # Sort by combined score
            scored_entries.sort(key=lambda x: x[1], reverse=True)
            
            # Format results
            results = []
            for entry, score in scored_entries[:max_results]:
                result = {
                    "entry_id": entry.entry_id,
                    "title": entry.title,
                    "category": entry.category.value,
                    "source": entry.source.value,
                    "contributor_id": entry.contributor_id,
                    "quality_score": entry.quality_score,
                    "confidence_level": entry.confidence_level.value,
                    "tags": entry.tags,
                    "keywords": entry.keywords,
                    "created_at": entry.created_at.isoformat(),
                    "access_count": entry.access_count,
                    "relevance_score": score
                }
                
                if include_content:
                    result["content"] = entry.content
                
                results.append(result)
                
                # Update access count
                entry.access_count += 1
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search knowledge: {e}")
            return []
    
    async def get_knowledge_entry(self, entry_id: str, requester_id: str) -> Dict[str, Any]:
        """Get a specific knowledge entry."""
        try:
            if entry_id not in self.knowledge_entries:
                return {"error": "Knowledge entry not found"}
            
            entry = self.knowledge_entries[entry_id]
            
            # Update access statistics
            entry.access_count += 1
            
            # Get validations
            validations = self.validations.get(entry_id, [])
            validation_summary = {
                "count": len(validations),
                "average_score": sum(v.score for v in validations) / len(validations) if validations else 0.0,
                "recent_feedback": [v.feedback for v in validations[-3:] if v.feedback]
            }
            
            # Get related entries
            related_entries = []
            for related_id in entry.related_entries[:5]:  # Limit to 5 most related
                if related_id in self.knowledge_entries:
                    related = self.knowledge_entries[related_id]
                    related_entries.append({
                        "entry_id": related.entry_id,
                        "title": related.title,
                        "category": related.category.value,
                        "quality_score": related.quality_score
                    })
            
            result = {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "content": entry.content,
                "category": entry.category.value,
                "source": entry.source.value,
                "contributor_id": entry.contributor_id,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
                "quality_score": entry.quality_score,
                "confidence_level": entry.confidence_level.value,
                "validation_count": entry.validation_count,
                "validation_score": entry.validation_score,
                "tags": entry.tags,
                "keywords": entry.keywords,
                "access_count": entry.access_count,
                "citation_count": entry.citation_count,
                "version": entry.version,
                "metadata": entry.metadata,
                "validations": validation_summary,
                "related_entries": related_entries
            }
            
            log_agent_event(
                self.agent_id,
                "knowledge_accessed",
                {
                    "entry_id": entry_id,
                    "requester_id": requester_id,
                    "access_count": entry.access_count
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get knowledge entry: {e}")
            return {"error": str(e)} 
   
    def get_dataset_info(self, dataset_id: str) -> Dict[str, Any]:
        """Get information about a dataset."""
        try:
            if dataset_id not in self.datasets:
                return {"error": "Dataset not found"}
            
            dataset = self.datasets[dataset_id]
            
            # Calculate quality distribution
            quality_dist = {}
            for quality in KnowledgeQuality:
                quality_dist[quality.name] = 0
            
            # Get entries for this dataset
            dataset_entries = []
            for entry in self.knowledge_entries.values():
                # In a full implementation, we'd track which dataset each entry belongs to
                # For now, we'll include all entries
                dataset_entries.append(entry)
                quality_dist[entry.confidence_level.name] += 1
            
            # Calculate average quality
            avg_quality = sum(entry.quality_score for entry in dataset_entries) / max(1, len(dataset_entries))
            
            # Get top contributors
            contributor_stats = {}
            for entry in dataset_entries:
                contributor_id = entry.contributor_id
                if contributor_id not in contributor_stats:
                    contributor_stats[contributor_id] = {"entries": 0, "avg_quality": 0.0}
                contributor_stats[contributor_id]["entries"] += 1
                contributor_stats[contributor_id]["avg_quality"] += entry.quality_score
            
            # Calculate averages
            for stats in contributor_stats.values():
                stats["avg_quality"] /= stats["entries"]
            
            # Sort by contribution count
            top_contributors = sorted(
                contributor_stats.items(),
                key=lambda x: x[1]["entries"],
                reverse=True
            )[:10]
            
            return {
                "dataset_id": dataset.dataset_id,
                "name": dataset.name,
                "description": dataset.description,
                "created_by": dataset.created_by,
                "created_at": dataset.created_at.isoformat(),
                "updated_at": dataset.updated_at.isoformat(),
                "public": dataset.public,
                "total_entries": len(dataset_entries),
                "total_contributors": len(dataset.contributors),
                "average_quality": avg_quality,
                "quality_distribution": quality_dist,
                "category_distribution": dataset.category_distribution,
                "top_contributors": [
                    {"contributor_id": cid, "entries": stats["entries"], "avg_quality": stats["avg_quality"]}
                    for cid, stats in top_contributors
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get dataset info: {e}")
            return {"error": str(e)}
    
    def get_agent_contributions(self, agent_id: str) -> Dict[str, Any]:
        """Get an agent's contributions to knowledge datasets."""
        try:
            # Get entries contributed by agent
            agent_entries = [
                entry for entry in self.knowledge_entries.values()
                if entry.contributor_id == agent_id
            ]
            
            # Get validations performed by agent
            agent_validations = []
            for entry_id, validations in self.validations.items():
                for validation in validations:
                    if validation.validator_id == agent_id:
                        agent_validations.append(validation)
            
            # Calculate statistics
            total_entries = len(agent_entries)
            avg_quality = sum(entry.quality_score for entry in agent_entries) / max(1, total_entries)
            total_validations = len(agent_validations)
            avg_validation_score = sum(v.score for v in agent_validations) / max(1, total_validations)
            
            # Category breakdown
            category_breakdown = {}
            for entry in agent_entries:
                cat = entry.category.value
                category_breakdown[cat] = category_breakdown.get(cat, 0) + 1
            
            # Recent contributions
            recent_entries = sorted(agent_entries, key=lambda e: e.created_at, reverse=True)[:10]
            recent_contributions = [
                {
                    "entry_id": entry.entry_id,
                    "title": entry.title,
                    "category": entry.category.value,
                    "quality_score": entry.quality_score,
                    "created_at": entry.created_at.isoformat()
                }
                for entry in recent_entries
            ]
            
            return {
                "agent_id": agent_id,
                "total_contributions": total_entries,
                "average_quality": avg_quality,
                "total_validations": total_validations,
                "average_validation_score": avg_validation_score,
                "category_breakdown": category_breakdown,
                "recent_contributions": recent_contributions,
                "reputation_score": (avg_quality * 0.6) + (avg_validation_score * 0.4)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get agent contributions: {e}")
            return {"error": str(e)}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide knowledge management statistics."""
        try:
            # Calculate quality distribution
            quality_dist = {}
            for quality in KnowledgeQuality:
                quality_dist[quality.name] = 0
            
            for entry in self.knowledge_entries.values():
                quality_dist[entry.confidence_level.name] += 1
            
            # Calculate category distribution
            category_dist = {}
            for category in KnowledgeCategory:
                category_dist[category.value] = 0
            
            for entry in self.knowledge_entries.values():
                category_dist[entry.category.value] += 1
            
            # Calculate source distribution
            source_dist = {}
            for source in KnowledgeSource:
                source_dist[source.value] = 0
            
            for entry in self.knowledge_entries.values():
                source_dist[entry.source.value] += 1
            
            # Calculate average metrics
            total_entries = len(self.knowledge_entries)
            avg_quality = sum(entry.quality_score for entry in self.knowledge_entries.values()) / max(1, total_entries)
            avg_validations = sum(entry.validation_count for entry in self.knowledge_entries.values()) / max(1, total_entries)
            
            # Get top performing entries
            top_entries = sorted(
                self.knowledge_entries.values(),
                key=lambda e: e.quality_score * (1 + e.validation_count * 0.1),
                reverse=True
            )[:10]
            
            top_entries_info = [
                {
                    "entry_id": entry.entry_id,
                    "title": entry.title,
                    "quality_score": entry.quality_score,
                    "validation_count": entry.validation_count,
                    "access_count": entry.access_count
                }
                for entry in top_entries
            ]
            
            return {
                "total_datasets": len(self.datasets),
                "total_entries": total_entries,
                "total_contributors": len(set(entry.contributor_id for entry in self.knowledge_entries.values())),
                "average_quality": avg_quality,
                "average_validations_per_entry": avg_validations,
                "quality_distribution": quality_dist,
                "category_distribution": category_dist,
                "source_distribution": source_dist,
                "top_entries": top_entries_info,
                "system_stats": self.stats
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system stats: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _initialize_database(self) -> None:
        """Initialize the SQLite database for persistent storage."""
        try:
            self.db_connection = sqlite3.connect(self.db_path)
            cursor = self.db_connection.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS datasets (
                    dataset_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    public BOOLEAN NOT NULL,
                    data TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    entry_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source TEXT NOT NULL,
                    contributor_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    quality_score REAL NOT NULL,
                    confidence_level INTEGER NOT NULL,
                    validation_count INTEGER NOT NULL,
                    validation_score REAL NOT NULL,
                    content_hash TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS validations (
                    validation_id TEXT PRIMARY KEY,
                    validator_id TEXT NOT NULL,
                    entry_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    feedback TEXT,
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contributions (
                    contribution_id TEXT PRIMARY KEY,
                    contributor_id TEXT NOT NULL,
                    entry_id TEXT NOT NULL,
                    contribution_type TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            ''')
            
            # Create indices
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_contributor ON knowledge_entries(contributor_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_category ON knowledge_entries(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_hash ON knowledge_entries(content_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_validations_entry ON validations(entry_id)')
            
            self.db_connection.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _load_datasets(self) -> None:
        """Load existing datasets from database."""
        try:
            if not self.db_connection:
                return
            
            cursor = self.db_connection.cursor()
            
            # Load datasets
            cursor.execute('SELECT * FROM datasets')
            for row in cursor.fetchall():
                dataset_data = json.loads(row[7])  # data column
                dataset = SharedKnowledgeDataset(**dataset_data)
                self.datasets[dataset.dataset_id] = dataset
            
            # Load knowledge entries
            cursor.execute('SELECT * FROM knowledge_entries')
            for row in cursor.fetchall():
                entry_data = json.loads(row[13])  # data column
                entry = KnowledgeEntry(**entry_data)
                self.knowledge_entries[entry.entry_id] = entry
                await self._update_indices(entry)
            
            # Load validations
            cursor.execute('SELECT * FROM validations')
            for row in cursor.fetchall():
                validation_data = json.loads(row[6])  # data column
                validation = ValidationResult(**validation_data)
                entry_id = validation.entry_id
                if entry_id not in self.validations:
                    self.validations[entry_id] = []
                self.validations[entry_id].append(validation)
            
            # Update statistics
            self.stats["total_entries"] = len(self.knowledge_entries)
            self.stats["total_validations"] = sum(len(vals) for vals in self.validations.values())
            
            self.logger.info(f"Loaded {len(self.datasets)} datasets and {len(self.knowledge_entries)} entries")
            
        except Exception as e:
            self.logger.error(f"Failed to load datasets: {e}")
    
    async def _save_datasets(self) -> None:
        """Save all datasets to database."""
        try:
            if not self.db_connection:
                return
            
            self.db_connection.cursor()
            
            # Save datasets
            for dataset in self.datasets.values():
                await self._save_dataset_to_db(dataset)
            
            # Save knowledge entries
            for entry in self.knowledge_entries.values():
                await self._update_entry_in_db(entry)
            
            self.db_connection.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to save datasets: {e}")
    
    async def _save_dataset_to_db(self, dataset: SharedKnowledgeDataset) -> None:
        """Save a dataset to database."""
        try:
            cursor = self.db_connection.cursor()
            
            # Convert dataset to dict for JSON serialization
            dataset_dict = {
                "dataset_id": dataset.dataset_id,
                "name": dataset.name,
                "description": dataset.description,
                "created_by": dataset.created_by,
                "created_at": dataset.created_at.isoformat(),
                "updated_at": dataset.updated_at.isoformat(),
                "public": dataset.public,
                "contributors": list(dataset.contributors),
                "moderators": list(dataset.moderators),
                "total_entries": dataset.total_entries,
                "total_contributors": dataset.total_contributors,
                "quality_distribution": dataset.quality_distribution,
                "category_distribution": dataset.category_distribution,
                "min_validation_count": dataset.min_validation_count,
                "auto_approve_threshold": dataset.auto_approve_threshold,
                "quality_threshold": dataset.quality_threshold
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO datasets 
                (dataset_id, name, description, created_by, created_at, updated_at, public, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dataset.dataset_id,
                dataset.name,
                dataset.description,
                dataset.created_by,
                dataset.created_at.isoformat(),
                dataset.updated_at.isoformat(),
                dataset.public,
                json.dumps(dataset_dict)
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to save dataset to DB: {e}")
    
    async def _save_entry_to_db(self, entry: KnowledgeEntry, dataset_id: str) -> None:
        """Save a knowledge entry to database."""
        try:
            cursor = self.db_connection.cursor()
            
            # Convert entry to dict for JSON serialization
            entry_dict = {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "content": entry.content,
                "category": entry.category.value,
                "source": entry.source.value,
                "contributor_id": entry.contributor_id,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
                "quality_score": entry.quality_score,
                "confidence_level": entry.confidence_level.value,
                "validation_count": entry.validation_count,
                "validation_score": entry.validation_score,
                "tags": entry.tags,
                "keywords": entry.keywords,
                "related_entries": entry.related_entries,
                "access_count": entry.access_count,
                "citation_count": entry.citation_count,
                "usefulness_score": entry.usefulness_score,
                "version": entry.version,
                "parent_entry_id": entry.parent_entry_id,
                "content_hash": entry.content_hash,
                "metadata": entry.metadata
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO knowledge_entries 
                (entry_id, dataset_id, title, content, category, source, contributor_id, 
                 created_at, updated_at, quality_score, confidence_level, validation_count, 
                 validation_score, content_hash, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.entry_id,
                dataset_id,
                entry.title,
                entry.content,
                entry.category.value,
                entry.source.value,
                entry.contributor_id,
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
                entry.quality_score,
                entry.confidence_level.value,
                entry.validation_count,
                entry.validation_score,
                entry.content_hash,
                json.dumps(entry_dict)
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to save entry to DB: {e}")
    
    async def _update_entry_in_db(self, entry: KnowledgeEntry) -> None:
        """Update a knowledge entry in database."""
        try:
            # For now, just save it (which does INSERT OR REPLACE)
            # In a full implementation, we'd determine the dataset_id
            await self._save_entry_to_db(entry, "default")
            
        except Exception as e:
            self.logger.error(f"Failed to update entry in DB: {e}")
    
    async def _save_validation_to_db(self, validation: ValidationResult) -> None:
        """Save a validation to database."""
        try:
            cursor = self.db_connection.cursor()
            
            validation_dict = {
                "validator_id": validation.validator_id,
                "entry_id": validation.entry_id,
                "score": validation.score,
                "feedback": validation.feedback,
                "validation_criteria": validation.validation_criteria,
                "timestamp": validation.timestamp.isoformat()
            }
            
            validation_id = f"val_{validation.validator_id}_{validation.entry_id}_{validation.timestamp.timestamp()}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO validations 
                (validation_id, validator_id, entry_id, score, feedback, timestamp, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                validation_id,
                validation.validator_id,
                validation.entry_id,
                validation.score,
                validation.feedback,
                validation.timestamp.isoformat(),
                json.dumps(validation_dict)
            ))
            
        except Exception as e:
            self.logger.error(f"Failed to save validation to DB: {e}")
    
    async def _check_for_duplicates(self, entry: KnowledgeEntry, dataset_id: str) -> Optional[str]:
        """Check for duplicate content in the dataset."""
        try:
            # Check exact hash match
            if entry.content_hash in self.content_hash_index:
                existing_entry_id = self.content_hash_index[entry.content_hash]
                self.stats["duplicate_detections"] += 1
                return existing_entry_id
            
            # Check for similar content (simplified)
            # In a full implementation, this would use more sophisticated similarity measures
            for existing_entry in self.knowledge_entries.values():
                if existing_entry.category == entry.category:
                    # Simple similarity check based on title and keywords
                    title_similarity = await self._calculate_text_similarity(entry.title, existing_entry.title)
                    if title_similarity > self.config["duplicate_threshold"]:
                        return existing_entry.entry_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking for duplicates: {e}")
            return None
    
    async def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content."""
        try:
            # Simple keyword extraction (in practice, would use NLP libraries)
            words = content.lower().split()
            
            # Remove common stop words
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
            }
            
            # Filter and count words
            word_freq = {}
            for word in words:
                # Clean word
                word = ''.join(c for c in word if c.isalnum()).lower()
                if len(word) > 3 and word not in stop_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Return top keywords
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            return [word for word, freq in keywords[:10]]
            
        except Exception as e:
            self.logger.error(f"Error extracting keywords: {e}")
            return []
    
    async def _update_indices(self, entry: KnowledgeEntry) -> None:
        """Update search indices with new entry."""
        try:
            # Content hash index
            self.content_hash_index[entry.content_hash] = entry.entry_id
            
            # Keyword index
            for keyword in entry.keywords:
                if keyword not in self.keyword_index:
                    self.keyword_index[keyword] = set()
                self.keyword_index[keyword].add(entry.entry_id)
            
            # Category index
            if entry.category not in self.category_index:
                self.category_index[entry.category] = set()
            self.category_index[entry.category].add(entry.entry_id)
            
            # Contributor index
            if entry.contributor_id not in self.contributor_index:
                self.contributor_index[entry.contributor_id] = set()
            self.contributor_index[entry.contributor_id].add(entry.entry_id)
            
        except Exception as e:
            self.logger.error(f"Error updating indices: {e}")
    
    async def _calculate_relevance_score(self, entry: KnowledgeEntry, query: str) -> float:
        """Calculate relevance score for search query."""
        try:
            if not query:
                return 1.0
            
            query_lower = query.lower()
            score = 0.0
            
            # Title match (highest weight)
            if query_lower in entry.title.lower():
                score += 0.5
            
            # Content match
            if query_lower in entry.content.lower():
                score += 0.3
            
            # Tag match
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 0.1
            
            # Keyword match
            for keyword in entry.keywords:
                if query_lower in keyword.lower():
                    score += 0.1
            
            return min(1.0, score)
            
        except Exception as e:
            self.logger.error(f"Error calculating relevance score: {e}")
            return 0.0
    
    async def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        try:
            # Simple Jaccard similarity
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            if not union:
                return 0.0
            
            return len(intersection) / len(union)
            
        except Exception as e:
            self.logger.error(f"Error calculating text similarity: {e}")
            return 0.0
    
    async def _create_contribution_record(
        self,
        contributor_id: str,
        entry_id: str,
        contribution_type: str,
        description: str
    ) -> KnowledgeContribution:
        """Create a contribution record."""
        try:
            self.contribution_counter += 1
            contribution_id = f"contrib_{self.contribution_counter}_{datetime.now().timestamp()}"
            
            contribution = KnowledgeContribution(
                contribution_id=contribution_id,
                contributor_id=contributor_id,
                entry_id=entry_id,
                contribution_type=contribution_type,
                description=description,
                status="approved"  # Auto-approve for now
            )
            
            self.contributions[contribution_id] = contribution
            
            return contribution
            
        except Exception as e:
            self.logger.error(f"Error creating contribution record: {e}")
            raise
    
    async def _get_dataset_entries(self, dataset_id: str) -> List[str]:
        """Get all entry IDs for a dataset."""
        try:
            # In a full implementation, we'd track dataset membership properly
            # For now, return all entries
            return list(self.knowledge_entries.keys())
            
        except Exception as e:
            self.logger.error(f"Error getting dataset entries: {e}")
            return []
    
    async def _quality_monitor(self) -> None:
        """Background task to monitor and improve knowledge quality."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Find entries that need more validation
                for entry in self.knowledge_entries.values():
                    if (entry.validation_count < 3 and 
                        entry.confidence_level == KnowledgeQuality.UNVERIFIED and
                        (datetime.now() - entry.created_at).days > 1):
                        
                        # In a full implementation, we'd notify agents to validate
                        self.logger.info(f"Entry {entry.entry_id} needs validation")
                
                # Update quality scores based on usage
                for entry in self.knowledge_entries.values():
                    if entry.access_count > 0:
                        usage_bonus = min(0.1, entry.access_count / 100.0)
                        entry.quality_score = min(1.0, entry.quality_score + usage_bonus * 0.01)
                
            except Exception as e:
                self.logger.error(f"Error in quality monitor: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_processor(self) -> None:
        """Background task to clean up old data."""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily
                
                # Clean up old low-quality entries
                cutoff_date = datetime.now() - timedelta(days=self.config["auto_cleanup_days"])
                
                entries_to_remove = []
                for entry_id, entry in self.knowledge_entries.items():
                    if (entry.created_at < cutoff_date and
                        entry.quality_score < self.config["min_quality_score"] and
                        entry.access_count == 0):
                        entries_to_remove.append(entry_id)
                
                # Remove low-quality entries
                for entry_id in entries_to_remove:
                    del self.knowledge_entries[entry_id]
                    if entry_id in self.validations:
                        del self.validations[entry_id]
                
                if entries_to_remove:
                    self.logger.info(f"Cleaned up {len(entries_to_remove)} low-quality entries")
                
            except Exception as e:
                self.logger.error(f"Error in cleanup processor: {e}")
                await asyncio.sleep(3600)
    
    async def _backup_processor(self) -> None:
        """Background task to create backups."""
        while True:
            try:
                await asyncio.sleep(self.config["backup_interval_hours"] * 3600)
                
                # Create backup
                backup_path = os.path.join(self.storage_path, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                
                if self.db_connection and os.path.exists(self.db_path):
                    # Simple file copy for backup
                    import shutil
                    shutil.copy2(self.db_path, backup_path)
                    self.logger.info(f"Created backup: {backup_path}")
                
                # Clean up old backups (keep last 7)
                backup_files = [f for f in os.listdir(self.storage_path) if f.startswith("backup_") and f.endswith(".db")]
                backup_files.sort(reverse=True)
                
                for old_backup in backup_files[7:]:
                    os.remove(os.path.join(self.storage_path, old_backup))
                
            except Exception as e:
                self.logger.error(f"Error in backup processor: {e}")
                await asyncio.sleep(3600)