"""
Knowledge management module for autonomous AI ecosystem.

This module provides shared knowledge dataset management, knowledge
contribution workflows, and collective learning capabilities.
"""

from .dataset_manager import (
    SharedKnowledgeDataset,
    KnowledgeEntry,
    KnowledgeCategory,
    KnowledgeSource,
    KnowledgeQuality,
    DatasetManager,
    KnowledgeContribution,
    ValidationResult
)

from .model_trainer import (
    ModelTrainer,
    TrainingJob,
    TrainingStatus,
    ModelType,
    TrainingConfig,
    ModelEvaluation
)

__all__ = [
    "SharedKnowledgeDataset",
    "KnowledgeEntry",
    "KnowledgeCategory",
    "KnowledgeSource",
    "KnowledgeQuality",
    "DatasetManager",
    "KnowledgeContribution",
    "ValidationResult",
    "ModelTrainer",
    "TrainingJob",
    "TrainingStatus",
    "ModelType",
    "TrainingConfig",
    "ModelEvaluation"
]