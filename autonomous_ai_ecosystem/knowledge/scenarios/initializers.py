"""
Scenario-specific cognition initializers for the ASI-EVOLVE framework.

Initializes the CognitionBase with domain-specific knowledge for different
AI development tasks.
"""

from typing import List, Dict, Any
from ..cognition_base import CognitionBase

class CognitionInitializer:
    """
    Utility to seed the CognitionBase with expert priors for specific scenarios.
    """

    @staticmethod
    async def seed_neural_architecture(cognition_base: CognitionBase):
        """Seed knowledge for neural architecture design."""
        priors = [
            ("Linear Attention mechanisms achieve O(N) complexity by decomposing attention computations.", "Architecture Prior"),
            ("Delta rule updates in linear transformers help in maintaining compressed memory states.", "Architecture Prior"),
            ("Standard quadratic attention (O(N^2)) is a major bottleneck for long sequences.", "Problem Statement"),
            ("Adaptive routing and multi-scale processing are effective for efficient modeling.", "Design Principle"),
            ("Hierarchical gating can balance local and contextual processing budget.", "Design Principle")
        ]
        for content, cat in priors:
            await cognition_base.add_knowledge(content, source="Initial Seed", category=cat, tags=["architecture", "linear-attention"])

    @staticmethod
    async def seed_data_curation(cognition_base: CognitionBase):
        """Seed knowledge for pretraining data curation."""
        priors = [
            ("Cleaning-focused approaches (HTML removal, de-duplication) significantly boost model quality.", "Data Prior"),
            ("Domain-aware preservation rules prevent over-aggressive filtering of valuable edge cases.", "Data Prior"),
            ("MMLU and knowledge-intensive benchmarks are highly sensitive to data quality.", "Benchmark Insight"),
            ("Identifying domain-specific noise patterns (e.g., code fragments in text) is crucial.", "Methodology")
        ]
        for content, cat in priors:
            await cognition_base.add_knowledge(content, source="Initial Seed", category=cat, tags=["data", "pretraining", "curation"])

    @staticmethod
    async def seed_rl_algorithms(cognition_base: CognitionBase):
        """Seed knowledge for reinforcement learning algorithm design."""
        priors = [
            ("GRPO (Group Relative Policy Optimization) is a strong baseline for mathematical reasoning.", "RL Prior"),
            ("Variance reduction techniques and KL-penalty modifications are key levers for RL stability.", "RL Prior"),
            ("Asymmetric clipping mechanisms can stabilize training on noisy reward signals.", "Design Principle"),
            ("Advantage calculation using percentile-based normalization improves convergence.", "Methodology")
        ]
        for content, cat in priors:
            await cognition_base.add_knowledge(content, source="Initial Seed", category=cat, tags=["rl", "algorithm", "grpo"])
