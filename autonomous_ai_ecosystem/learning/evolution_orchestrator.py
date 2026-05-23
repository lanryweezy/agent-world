"""
Evolution Orchestrator for the ASI-EVOLVE framework.

Coordinates the Learn-Design-Experiment-Analyze cycle to achieve
continuous autonomous self-improvement of the AI ecosystem.
"""

import asyncio
import math
import random
import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from ..agents.code_modifier import CodeModifier
from ..agents.sandbox import CodeSandbox
from ..agents.analyzer import StructuredAnalyzer
from ..agents.reviewer import CritiqueReviewer
from ..agents.planner import ResearchPlanner
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
    Orchestrates the end-to-end evolution loop using a Multi-Agent Research Team.
    """

    def __init__(
        self,
        agent_id: str,
        planner: ResearchPlanner,
        researcher: CodeModifier,
        engineer: CodeSandbox,
        analyzer: StructuredAnalyzer,
        reviewer: CritiqueReviewer,
        cognition_base: CognitionBase,
        sampling_strategy: str = "ucb1" # random, ucb1, map_elites
    ):
        super().__init__(agent_id)
        self.planner = planner
        self.researcher = researcher
        self.engineer = engineer
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

        # Human-in-the-Loop constraints/feedback
        self.hitl_feedback: Dict[int, str] = {} # island_index -> feedback string

    async def initialize(self):
        """Initialize the evolution orchestrator."""
        self.logger.info("Initializing Evolution Orchestrator...")
        self.analyzer.register_template()
        await self.cognition_base.initialize()
        await self.load_state()

    async def start_evolution(self, target_file: str, task_description: str, max_rounds: int = 5, parallelism: int = 3):
        """Start the evolution loop with distributed experimentation support."""
        self.is_evolving = True
        self.logger.info(f"Starting evolution loop for {target_file} using {self.sampling_strategy} (Parallelism: {parallelism})...")

        for r in range(0, max_rounds, parallelism):
            if not self.is_evolving:
                break

            # Rotation and Migration
            self.current_island_index = (r // parallelism) % len(self.islands)
            if r > 0 and r % 10 == 0:
                self._perform_migration()

            # Parallel Step Execution
            tasks = []
            for p in range(parallelism):
                if r + p >= max_rounds:
                    break
                tasks.append(self._execute_evolution_round(target_file, task_description))

            # Execute batch of rounds concurrently
            results = await asyncio.gather(*tasks)
            self.logger.info(f"Batch of {len(results)} rounds completed.")

        self.is_evolving = False
        self.logger.info("Evolution loop finished.")

    def inject_hitl_feedback(self, island_index: int, feedback: str):
        """Allow humans to steer a specific evolution island."""
        self.hitl_feedback[island_index] = feedback
        self.logger.info(f"Injected human steering into Island {island_index}: {feedback[:50]}...")

    async def _execute_evolution_round(self, target_file: str, task_description: str) -> Optional[EvolutionNode]:
            """Execute a single evolution round (LDEA cycle)."""
            self.evolution_rounds += 1
            round_id = self.evolution_rounds
            current_island = self.islands[self.current_island_index]
            self.logger.info(f"--- Evolution Round {round_id} (Island {self.current_island_index}) ---")

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

            # HITL Steering: Combine task with human feedback if available
            steering_context = self.hitl_feedback.get(self.current_island_index, "")
            effective_task = task_description
            if steering_context:
                effective_task += f"\n[HUMAN STEERING]: {steering_context}"

            # 1.5 PLAN: ResearchPlanner generates a blueprint (PES paradigm)
            plan = await self.planner.generate_plan(
                task_description=effective_task,
                cognition_context=cognition,
                historical_experience=historical_context
            )

            # 2. DESIGN: Researcher proposes a modification based on the plan
            design_result = await self.researcher.design_modification(
                target_file=target_file,
                task_description=f"{effective_task}\n[STRATEGIC PLAN]: {plan}",
                cognition_context=cognition,
                historical_experience=historical_context
            )

            # 2.5 REVIEW: Reviewer critiques the design before execution
            review_result = await self.reviewer.review_design(
                proposed_code=design_result["proposed_code"],
                motivation=design_result["motivation"],
                task_description=task_description
            )

            if not review_result.get("should_proceed", False):
                self.logger.warning(f"Round {round_id} BLOCKED by reviewer. Reason: {review_result.get('critique')}")
                return None

            # 3. EXPERIMENT: Engineer tests in sandbox
            test_results = await self.engineer.execute_code(
                code=design_result["proposed_code"]
            )

            # 4. ANALYZE: Distill insights
            analysis = await self.analyzer.analyze_experiment(
                program_code=design_result["proposed_code"],
                execution_result=test_results.__dict__,
                context={"round": round_id, "task": task_description}
            )

            # Calculate fitness score (0.0 to 1.0)
            score = self._calculate_score(test_results, analysis)

            # Extract features for MAP-Elites (e.g. complexity, diversity)
            features = self._extract_features(design_result["proposed_code"], analysis)

            # Store in database and current island
            node = EvolutionNode(
                node_id=f"node_{round_id}",
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
                    source=f"evolution_round_{round_id}",
                    category="experimental_lesson",
                    tags=[task_description, "lesson"]
                )

            # Apply if successful and high score
            if score > 0.8:
                self.logger.info(f"Round {round_id} SUCCESS (Score: {score:.2f}). Applying modification.")
                await self.researcher.apply_modification(design_result["modification_id"])
            else:
                self.logger.warning(f"Round {round_id} sub-optimal (Score: {score:.2f}). Skipping application.")

            log_agent_event(
                self.agent_id,
                "evolution_round_completed",
                {
                    "round": round_id,
                    "status": test_results.status.value,
                    "score": score,
                    "confidence": analysis["confidence"]
                }
            )
            return node

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

    async def save_state(self, storage_path: str = "data/evolution/evolution_state.json"):
        """Save the evolution state to disk."""
        state = {
            "evolution_rounds": self.evolution_rounds,
            "database": [asdict(node) for node in self.database],
            "map_elites_archive": {f"{k[0]}_{k[1]}": asdict(v) for k, v in self.map_elites_archive.items()},
            "islands": [[asdict(node) for node in island] for island in self.islands],
            "sampling_strategy": self.sampling_strategy
        }
        # Ensure timestamp and other non-serializable objects are handled
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

        with open(storage_path, "w") as f:
            json.dump(state, f, indent=4, default=default_serializer)
        self.logger.info(f"Evolution state saved to {storage_path}")

    async def load_state(self, storage_path: str = "data/evolution/evolution_state.json"):
        """Load the evolution state from disk."""
        if not os.path.exists(storage_path):
            return

        with open(storage_path, "r") as f:
            state = json.load(f)

        self.evolution_rounds = state.get("evolution_rounds", 0)
        self.sampling_strategy = state.get("sampling_strategy", self.sampling_strategy)

        # Helper to reconstruct nodes
        def reconstruct_node(d):
            if isinstance(d["timestamp"], str):
                d["timestamp"] = datetime.fromisoformat(d["timestamp"])
            return EvolutionNode(**d)

        self.database = [reconstruct_node(d) for d in state.get("database", [])]

        archive_raw = state.get("map_elites_archive", {})
        for k, v in archive_raw.items():
            b1, b2 = map(int, k.split("_"))
            self.map_elites_archive[(b1, b2)] = reconstruct_node(v)

        self.islands = [[reconstruct_node(d) for d in island] for island in state.get("islands", [])]

        self.logger.info(f"Evolution state loaded from {storage_path}. Rounds: {self.evolution_rounds}")

    async def shutdown(self):
        """Shutdown the evolution orchestrator."""
        await self.stop_evolution()
        await self.save_state()
        await self.cognition_base.save_data()
        self.logger.info("Evolution Orchestrator shutdown.")
