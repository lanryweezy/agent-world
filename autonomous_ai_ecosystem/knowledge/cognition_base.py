"""
Cognition Base for the ASI-EVOLVE framework.

Stores human priors, research papers, heuristics, and domain knowledge
to guide the agent's exploration and design phases.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..agents.vector_memory import VectorMemory
from ..core.logger import get_agent_logger

class CognitionBase:
    """
    A repository of knowledge used to steer the evolution process.
    Contains literature-derived priors, known pitfalls, and design principles.
    """

    def __init__(self, agent_id: str, storage_path: str = "data/cognition"):
        self.agent_id = agent_id
        self.storage_path = storage_path
        self.logger = get_agent_logger(agent_id, "cognition_base")
        self.vector_memory = VectorMemory()
        self.metadata = []

        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    async def initialize(self):
        """Initialize the cognition base and load existing data."""
        self.logger.info("Initializing Cognition Base...")
        await self.load_data()

    async def add_knowledge(self, content: str, source: str, category: str, tags: List[str] = None, enable_domain_transfer: bool = True):
        """Add a new piece of knowledge to the cognition base. Supports domain transfer logic."""
        item = {
            "content": content,
            "source": source,
            "category": category,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat()
        }

        if enable_domain_transfer:
            # Simple Domain Transfer: automatically add related domain tags
            transfer_rules = {
                "linear-attention": ["drug-target-interaction", "sequence-modeling"],
                "sinkhorn": ["optimal-transport", "binding-affinity"],
                "grpo": ["reasoning-reinforcement", "stability"],
                "data-curation": ["knowledge-intensive-tasks"]
            }
            new_tags = set(item["tags"])
            for key, related in transfer_rules.items():
                if key in content.lower() or any(key in t.lower() for t in item["tags"]):
                    new_tags.update(related)
            item["tags"] = list(new_tags)

        self.vector_memory.add_document(content)
        self.metadata.append(item)
        await self.save_data()
        self.logger.info(f"Added knowledge from {source} to category {category}. Tags: {item['tags']}")

    async def retrieve_relevant(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge items based on a query."""
        results = self.vector_memory.search(query, k=k)

        # Match back to metadata
        relevant_items = []
        for content in results:
            for item in self.metadata:
                if item["content"] == content:
                    relevant_items.append(item)
                    break
        return relevant_items

    async def save_data(self):
        """Save cognition metadata to disk."""
        save_file = os.path.join(self.storage_path, "cognition_metadata.json")
        with open(save_file, "w") as f:
            json.dump(self.metadata, f, indent=4)

    async def load_data(self):
        """Load cognition metadata from disk."""
        load_file = os.path.join(self.storage_path, "cognition_metadata.json")
        if os.path.exists(load_file):
            with open(load_file, "r") as f:
                self.metadata = json.load(f)
            # Re-index in vector memory
            for item in self.metadata:
                self.vector_memory.add_document(item["content"])
            self.logger.info(f"Loaded {len(self.metadata)} items into Cognition Base")
