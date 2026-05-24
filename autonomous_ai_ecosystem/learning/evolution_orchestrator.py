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
from ..agents.brain import ThoughtType
from ..knowledge.cognition_base import CognitionBase
from ..core.skills import SkillInput, SkillOutput

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
        self._register_discussion_templates()
        self.analyzer.register_template()
        await self.cognition_base.initialize()
        await self.load_state()

    def _register_discussion_templates(self):
        """Register Idea Proposal and Consensus templates with the brain."""
        from ..agents.brain import PromptTemplate

        if "idea_proposal" not in self.researcher.brain.prompt_templates:
            self.researcher.brain.prompt_templates["idea_proposal"] = PromptTemplate(
                template_id="idea_proposal",
                name="Research Idea Proposal",
                template="""
You are a creative Research Scientist. Task: {task}
Cognition: {cognition}
History: {history}

Propose a novel idea to improve the system. Format your response as JSON with key "proposal".
""",
                variables=["task", "cognition", "history"],
                thought_type=ThoughtType.CREATIVITY
            )

        if "idea_consensus" not in self.researcher.brain.prompt_templates:
            self.researcher.brain.prompt_templates["idea_consensus"] = PromptTemplate(
                template_id="idea_consensus",
                name="Research Idea Consensus",
                template="""
Task: {task}
Proposals: {proposals}

Synthesize these proposals into a single best idea. Format your response as JSON with key "consensus".
""",
                variables=["task", "proposals"],
                thought_type=ThoughtType.ANALYSIS
            )

    async def start_evolution(self, target_file: str, task_description: str, max_rounds: int = 5, parallelism: int = 3, mode: str = "explore"):
        """Start the evolution loop with support for different research modes: explore, reproduce."""
        self.is_evolving = True
        self.logger.info(f"Starting evolution loop (Mode: {mode}) for {target_file} using {self.sampling_strategy} (Parallelism: {parallelism})...")

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

                if mode == "reproduce":
                    # Reproduction Mode: focused on faithfully recreating an existing outcome
                    tasks.append(self._execute_evolution_round(target_file, f"REPRODUCE: {task_description}"))
                else:
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
            """Execute a single evolution round using the Claw AI Lab multi-layered architecture."""
            self.evolution_rounds += 1
            round_id = self.evolution_rounds
            current_island = self.islands[self.current_island_index]
            self.logger.info(f"--- Evolution Round {round_id} (Layered Architecture) ---")

            # 1. IDEA LAYER: multi-agent discussion and retrieval
            cognition = await self.cognition_base.retrieve_relevant(task_description)
            parent_nodes = self._sample_parents(count=3)
            historical_context = [{"motivation": n.motivation, "score": n.score} for n in parent_nodes]

            # Collaborative Discussion for Idea Refinement
            idea_context = await self._perform_idea_discussion(task_description, cognition, historical_context)

            # 2. PLANNING LAYER: Decompose ideas into concrete tasks
            steering_context = self.hitl_feedback.get(self.current_island_index, "")
            effective_task = task_description + (f"\n[STEERING]: {steering_context}" if steering_context else "")

            plan = await self.planner.generate_plan(
                task_description=f"{effective_task}\n[DISCUSSED IDEAS]: {idea_context}",
                cognition_context=cognition,
                historical_experience=historical_context
            )

            # 3. CODING LAYER: Implement, debug, and leverage tools
            design_result = await self.researcher.design_modification(
                target_file=target_file,
                task_description=f"{effective_task}\n[PLAN]: {plan}",
                cognition_context=cognition,
                historical_experience=historical_context
            )

            # Pre-experiment Review (Validation Loop)
            review_result = await self.reviewer.review_design(
                proposed_code=design_result["proposed_code"],
                motivation=design_result["motivation"],
                task_description=task_description
            )

            if not review_result.get("should_proceed", False):
                self.logger.warning(f"Round {round_id} BLOCKED. Reason: {review_result.get('critique')}")
                return None

            # 4. EXPERIMENT LAYER: Run on server, collect metrics and logs
            test_results = await self.engineer.execute_code(code=design_result["proposed_code"])

            # Distill insights (Post-experiment summary)
            analysis = await self.analyzer.analyze_experiment(
                program_code=design_result["proposed_code"],
                execution_result=test_results.__dict__,
                context={"round": round_id, "plan": plan}
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

                # ASI-EVOLVE: Export successful evolution as a HarnessAPI Skill folder
                if "capability" in task_description.lower() or "service" in task_description.lower():
                    await self._export_as_skill(round_id, design_result, analysis)
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

    async def _export_as_skill(self, round_id: int, design: Dict[str, Any], analysis: Dict[str, Any]):
        """Export a successfully evolved capability as a HarnessAPI skill folder."""
        skill_name = f"evolved_service_{round_id}"
        skill_dir = os.path.join("skills", skill_name)
        os.makedirs(skill_dir, exist_ok=True)

        self.logger.info(f"Exporting evolved capability as Skill: {skill_name}")

        # 1. Write models.py
        models_code = (
            "from pydantic import Field\n"
            "from autonomous_ai_ecosystem.core.skills import SkillInput, SkillOutput\n\n"
            "class Input(SkillInput):\n"
            "    text: str = Field(..., description='Input text for the service')\n\n"
            "class Output(SkillOutput):\n"
            "    result: str = Field(..., description='Processed result')\n"
        )
        with open(os.path.join(skill_dir, "models.py"), "w") as f:
            f.write(models_code)

        # 2. Write handler.py
        with open(os.path.join(skill_dir, "handler.py"), "w") as f:
            f.write(design["proposed_code"])

        # 3. Write skill.toml
        import toml
        skill_config = {
            "skill": {
                "name": skill_name,
                "description": design.get("motivation", "Evolved autonomous service"),
                "is_mcp": True,
                "tags": ["evolved", "autonomous"],
                "timeout_secs": 60
            }
        }
        with open(os.path.join(skill_dir, "skill.toml"), "w") as f:
            toml.dump(skill_config, f)

    async def _perform_idea_discussion(self, task: str, cognition: List[Dict], history: List[Dict]) -> str:
        """Simulate a multi-agent debate to refine the research idea."""
        self.logger.info("Initiating multi-agent idea discussion...")

        # We use different temperature settings to simulate "different perspectives" from the brain
        perspectives = []
        for temp in [0.9, 0.4]: # Creative vs Conservative
             thought = await self.researcher.brain.think(
                 thought_type=ThoughtType.CREATIVITY,
                 input_data={"task": task, "cognition": cognition, "history": history},
                 template_id="idea_proposal"
             )
             perspectives.append(thought.output.get("proposal", ""))

        # Consensus/Synthesis
        consensus_thought = await self.researcher.brain.think(
            thought_type=ThoughtType.ANALYSIS,
            input_data={"proposals": perspectives, "task": task},
            template_id="idea_consensus"
        )
        return consensus_thought.output.get("consensus", "No consensus reached.")

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
