"""
Evolution Orchestrator for the ASI-EVOLVE framework.

Coordinates the Learn-Design-Experiment-Analyze cycle to achieve
continuous autonomous self-improvement of the AI ecosystem.
"""

import asyncio
import math
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from ..agents.code_modifier import CodeModifier
from ..agents.sandbox import CodeSandbox
from ..agents.analyzer import StructuredAnalyzer
from ..agents.reviewer import CritiqueReviewer
from ..knowledge.cognition_base import CognitionBase

@dataclass
class EvolutionNode:
    """A node in the evolution history representing a trial."""
    node_id: str
    motivation: str
    code: str
    execution_result: Dict[str, Any]
    analysis: Dict[str, Any]
    score: float
    timestamp: datetime = field(default_factory=datetime.now)
    visit_count: int = 0
    features: Dict[str, float] = field(default_factory=dict) # For MAP-Elites

class EvolutionOrchestrator(AgentModule):
    """
    Orchestrates the end-to-end evolution loop with advanced sampling (UCB1, MAP-Elites).
    """

    def __init__(
        self,
        agent_id: str,
        code_modifier: CodeModifier,
        sandbox: CodeSandbox,
        analyzer: StructuredAnalyzer,
        reviewer: CritiqueReviewer,
        cognition_base: CognitionBase,
        sampling_strategy: str = "ucb1" # random, ucb1, map_elites
    ):
        super().__init__(agent_id)
        self.code_modifier = code_modifier
        self.sandbox = sandbox
        self.analyzer = analyzer
        self.reviewer = reviewer
        self.cognition_base = cognition_base
        self.sampling_strategy = sampling_strategy
        self.logger = get_agent_logger(agent_id, "evolution_orchestrator")

        self.is_evolving = False
        self.evolution_rounds = 0
        self.database: List[EvolutionNode] = []

        # MAP-Elites archive: grid of niches
        # Key: (feature1_bin, feature2_bin)
        self.map_elites_archive: Dict[Tuple[int, int], EvolutionNode] = {}
        self.num_bins = 10

        # Islands: List of separate evolution histories
        self.islands: List[List[EvolutionNode]] = [[] for _ in range(5)]
        self.current_island_index = 0

    async def initialize(self):
        """Initialize the evolution orchestrator."""
        self.logger.info("Initializing Evolution Orchestrator...")
        self.analyzer.register_template()
        await self.cognition_base.initialize()

    async def start_evolution(self, target_file: str, task_description: str, max_rounds: int = 5):
        """Start the evolution loop."""
        self.is_evolving = True
        self.logger.info(f"Starting evolution loop for {target_file} using {self.sampling_strategy} across {len(self.islands)} islands...")

        for r in range(max_rounds):
            # Rotate current island
            self.current_island_index = r % len(self.islands)
            current_island = self.islands[self.current_island_index]
            self.logger.info(f"--- Evolution Round {self.evolution_rounds + 1} (Island {self.current_island_index}) ---")

            # Periodic Migration between islands
            if r > 0 and r % 10 == 0:
                self._perform_migration()
            if not self.is_evolving:
                break

            self.evolution_rounds += 1
            self.logger.info(f"--- Evolution Round {self.evolution_rounds} ---")

            # 1. LEARN: Sample parent nodes and retrieve cognition
            parent_nodes = self._sample_parents(count=3)
            historical_context = [
                {
                    "motivation": node.motivation,
                    "analysis": node.analysis["analysis"],
                    "score": node.score
                } for node in parent_nodes
            ]

            cognition = await self.cognition_base.retrieve_relevant(task_description)

            # 2. DESIGN: Propose a modification
            design_result = await self.code_modifier.design_modification(
                target_file=target_file,
                task_description=task_description,
                cognition_context=cognition,
                historical_experience=historical_context
            )

            # 2.5 REVIEW: Critique the design before execution
            review_result = await self.reviewer.review_design(
                proposed_code=design_result["proposed_code"],
                motivation=design_result["motivation"],
                task_description=task_description
            )

            if not review_result.get("should_proceed", False):
                self.logger.warning(f"Round {self.evolution_rounds} BLOCKED by reviewer. Reason: {review_result.get('critique')}")
                continue

            # 3. EXPERIMENT: Test in sandbox
            test_results = await self.sandbox.execute_code(
                code=design_result["proposed_code"]
            )

            # 4. ANALYZE: Distill insights
            analysis = await self.analyzer.analyze_experiment(
                program_code=design_result["proposed_code"],
                execution_result=test_results.__dict__,
                context={"round": self.evolution_rounds, "task": task_description}
            )

            # Calculate fitness score (0.0 to 1.0)
            score = self._calculate_score(test_results, analysis)

            # Extract features for MAP-Elites (e.g. complexity, diversity)
            features = self._extract_features(design_result["proposed_code"], analysis)

            # Store in database and current island
            node = EvolutionNode(
                node_id=f"node_{self.evolution_rounds}",
                motivation=design_result["motivation"],
                code=design_result["proposed_code"],
                execution_result=test_results.__dict__,
                analysis=analysis,
                score=score,
                features=features
            )
            self.database.append(node)
            current_island.append(node)
            self._update_map_elites(node)

            # Update parent visit counts
            for p in parent_nodes:
                p.visit_count += 1

            # 5. EVOLVE COGNITION: Feed lessons back into Cognition Base
            for lesson in analysis.get("lessons_learned", []):
                await self.cognition_base.add_knowledge(
                    content=lesson,
                    source=f"evolution_round_{self.evolution_rounds}",
                    category="experimental_lesson",
                    tags=[task_description, "lesson"]
                )

            # Apply if successful and high score
            if score > 0.8:
                self.logger.info(f"Round {self.evolution_rounds} SUCCESS (Score: {score:.2f}). Applying modification.")
                await self.code_modifier.apply_modification(design_result["modification_id"])
            else:
                self.logger.warning(f"Round {self.evolution_rounds} sub-optimal (Score: {score:.2f}). Skipping application.")

            log_agent_event(
                self.agent_id,
                "evolution_round_completed",
                {
                    "round": self.evolution_rounds,
                    "status": test_results.status.value,
                    "score": score,
                    "confidence": analysis["confidence"]
                }
            )

        self.is_evolving = False
        self.logger.info("Evolution loop finished.")

    def _sample_parents(self, count: int = 3) -> List[EvolutionNode]:
        """Sample parent nodes using chosen strategy, prioritizing current island."""
        current_island = self.islands[self.current_island_index]

        # If island is empty, use global database
        pool = current_island if current_island else self.database

        if not pool:
            return []

        if self.sampling_strategy == "random":
            return random.sample(pool, min(count, len(pool)))

        elif self.sampling_strategy == "ucb1":
            # UCB1 = score + sqrt(2 * log(total_rounds) / visit_count)
            total_visits = sum(node.visit_count for node in pool) + 1
            scored_nodes = []
            for node in pool:
                exploration_bonus = math.sqrt(2 * math.log(total_visits) / (node.visit_count + 1))
                ucb_score = node.score + exploration_bonus
                scored_nodes.append((ucb_score, node))

            scored_nodes.sort(key=lambda x: x[0], reverse=True)
            return [node for _, node in scored_nodes[:count]]

        elif self.sampling_strategy == "map_elites":
            # Sample from the archive of diverse successful niches
            if not self.map_elites_archive:
                return random.sample(self.database, min(count, len(self.database)))

            archive_nodes = list(self.map_elites_archive.values())
            return random.sample(archive_nodes, min(count, len(archive_nodes)))

        return random.sample(self.database, min(count, len(self.database)))

    def _calculate_score(self, test_results: Any, analysis: Dict[str, Any]) -> float:
        """Calculate a scalar fitness score."""
        score = 0.0
        if test_results.status.value == "success":
            score += 0.5

        # Add score based on analyzer confidence and insights
        score += analysis.get("confidence", 0.0) * 0.3

        if len(analysis.get("lessons_learned", [])) > 0:
            score += 0.2

        return min(1.0, score)

    def _extract_features(self, code: str, analysis: Dict[str, Any]) -> Dict[str, float]:
        """Extract behavioral features for MAP-Elites."""
        # Simple features: Code complexity (len) and Insight density
        complexity = min(1.0, len(code) / 5000.0)
        insights = min(1.0, len(analysis.get("insights", [])) / 5.0)
        return {"complexity": complexity, "insight_density": insights}

    def _perform_migration(self):
        """Migrate top-performing nodes between islands."""
        self.logger.info("Performing island migration...")
        for i in range(len(self.islands)):
            island = self.islands[i]
            if not island:
                continue

            # Get best node from this island
            best_node = max(island, key=lambda x: x.score)

            # Migrate to next island (round robin)
            next_island_index = (i + 1) % len(self.islands)
            if best_node not in self.islands[next_island_index]:
                self.islands[next_island_index].append(best_node)
                self.logger.debug(f"Migrated node {best_node.node_id} from Island {i} to {next_island_index}")

    def _update_map_elites(self, node: EvolutionNode):
        """Update MAP-Elites archive with new node."""
        f1 = node.features.get("complexity", 0.5)
        f2 = node.features.get("insight_density", 0.5)

        bin1 = min(self.num_bins - 1, int(f1 * self.num_bins))
        bin2 = min(self.num_bins - 1, int(f2 * self.num_bins))

        niche = (bin1, bin2)
        if niche not in self.map_elites_archive or node.score > self.map_elites_archive[niche].score:
            self.map_elites_archive[niche] = node

    async def stop_evolution(self):
        """Stop the evolution loop."""
        self.is_evolving = False
        self.logger.info("Evolution loop stop requested.")

    async def shutdown(self):
        """Shutdown the evolution orchestrator."""
        await self.stop_evolution()
        await self.cognition_base.save_data()
        self.logger.info("Evolution Orchestrator shutdown.")
