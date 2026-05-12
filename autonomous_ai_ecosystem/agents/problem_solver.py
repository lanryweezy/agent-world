"""
Problem-solving evaluation framework for autonomous AI agents.

This module implements problem difficulty assessment, solution evaluation,
and status point calculation based on problem complexity and solution quality.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .brain import AIBrain
from .reasoning import ReasoningEngine


class ProblemDifficulty(Enum):
    """Problem difficulty levels."""
    TRIVIAL = 1
    EASY = 2
    MEDIUM = 3
    HARD = 4
    EXPERT = 5
    LEGENDARY = 6


class ProblemCategory(Enum):
    """Categories of problems."""
    MATHEMATICAL = "mathematical"
    LOGICAL = "logical"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    SOCIAL = "social"
    STRATEGIC = "strategic"
    ANALYTICAL = "analytical"
    OPTIMIZATION = "optimization"
    PATTERN_RECOGNITION = "pattern_recognition"
    SYSTEM_DESIGN = "system_design"


class SolutionQuality(Enum):
    """Quality levels of solutions."""
    POOR = 1
    BELOW_AVERAGE = 2
    AVERAGE = 3
    GOOD = 4
    EXCELLENT = 5
    EXCEPTIONAL = 6


@dataclass
class Problem:
    """Represents a problem to be solved."""
    problem_id: str
    title: str
    description: str
    category: ProblemCategory
    difficulty: Optional[ProblemDifficulty] = None
    constraints: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    time_limit: Optional[float] = None  # in hours
    resource_requirements: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    created_by: Optional[str] = None
    base_reward_points: Optional[int] = None


@dataclass
class Solution:
    """Represents a solution to a problem."""
    solution_id: str
    problem_id: str
    agent_id: str
    solution_description: str
    implementation: Optional[str] = None
    reasoning_steps: List[str] = field(default_factory=list)
    time_taken: float = 0.0  # in hours
    resources_used: Dict[str, float] = field(default_factory=dict)
    quality: Optional[SolutionQuality] = None
    correctness_score: float = 0.0  # 0.0 to 1.0
    creativity_score: float = 0.0   # 0.0 to 1.0
    efficiency_score: float = 0.0   # 0.0 to 1.0
    elegance_score: float = 0.0     # 0.0 to 1.0
    submitted_at: datetime = field(default_factory=datetime.now)
    evaluated_at: Optional[datetime] = None
    status_points_awarded: int = 0


@dataclass
class ProblemSolvingSession:
    """Represents a problem-solving session."""
    session_id: str
    agent_id: str
    problem_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    solution: Optional[Solution] = None
    intermediate_steps: List[Dict[str, Any]] = field(default_factory=list)
    final_status: str = "in_progress"  # in_progress, completed, abandoned, failed


class ProblemSolver(AgentModule):
    """
    Problem-solving evaluation framework that assesses problem difficulty,
    evaluates solutions, and calculates status points for agents.
    """
    
    def __init__(self, agent_id: str, ai_brain: AIBrain, reasoning_engine: ReasoningEngine):
        super().__init__(agent_id)
        self.ai_brain = ai_brain
        self.reasoning_engine = reasoning_engine
        self.logger = get_agent_logger(agent_id, "problem_solver")
        
        # Problem and solution storage
        self.problems: Dict[str, Problem] = {}
        self.solutions: Dict[str, Solution] = {}
        self.active_sessions: Dict[str, ProblemSolvingSession] = {}
        self.completed_sessions: List[ProblemSolvingSession] = []
        
        # Difficulty assessment parameters
        self.difficulty_factors = {
            "complexity_keywords": {
                "optimization": 2.0,
                "algorithm": 1.5,
                "recursive": 1.8,
                "dynamic programming": 2.5,
                "machine learning": 2.2,
                "distributed": 2.0,
                "concurrent": 1.8,
                "real-time": 1.6,
                "scalable": 1.4,
                "secure": 1.3
            },
            "constraint_multiplier": 1.2,
            "time_pressure_multiplier": 1.5,
            "resource_limitation_multiplier": 1.3
        }
        
        # Status point calculation parameters
        self.status_point_base = {
            ProblemDifficulty.TRIVIAL: 10,
            ProblemDifficulty.EASY: 25,
            ProblemDifficulty.MEDIUM: 50,
            ProblemDifficulty.HARD: 100,
            ProblemDifficulty.EXPERT: 200,
            ProblemDifficulty.LEGENDARY: 500
        }
        
        # Quality multipliers for status points
        self.quality_multipliers = {
            SolutionQuality.POOR: 0.3,
            SolutionQuality.BELOW_AVERAGE: 0.6,
            SolutionQuality.AVERAGE: 1.0,
            SolutionQuality.GOOD: 1.4,
            SolutionQuality.EXCELLENT: 2.0,
            SolutionQuality.EXCEPTIONAL: 3.0
        }
        
        # Problem-solving statistics
        self.solver_stats = {
            "problems_created": 0,
            "problems_solved": 0,
            "total_status_points_awarded": 0,
            "average_solution_time": 0.0,
            "difficulty_distribution": {diff.name: 0 for diff in ProblemDifficulty},
            "category_distribution": {cat.name: 0 for cat in ProblemCategory}
        }
        
        self.logger.info(f"Problem solver initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the problem solver."""
        try:
            # Load existing problems and solutions
            await self._load_problem_data()
            
            self.logger.info("Problem solver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize problem solver: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the problem solver gracefully."""
        try:
            # Save problem and solution data
            await self._save_problem_data()
            
            # Complete any active sessions
            await self._complete_active_sessions()
            
            self.logger.info("Problem solver shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during problem solver shutdown: {e}")
    
    async def create_problem(
        self,
        title: str,
        description: str,
        category: ProblemCategory,
        constraints: List[str] = None,
        success_criteria: List[str] = None,
        time_limit: Optional[float] = None,
        tags: List[str] = None
    ) -> str:
        """
        Create a new problem.
        
        Args:
            title: Problem title
            description: Detailed problem description
            category: Problem category
            constraints: List of constraints
            success_criteria: Success criteria
            time_limit: Time limit in hours
            tags: Problem tags
            
        Returns:
            Problem ID
        """
        try:
            problem_id = f"problem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.problems)}"
            
            # Create problem
            problem = Problem(
                problem_id=problem_id,
                title=title,
                description=description,
                category=category,
                constraints=constraints or [],
                success_criteria=success_criteria or [],
                time_limit=time_limit,
                tags=tags or [],
                created_by=self.agent_id
            )
            
            # Assess difficulty
            problem.difficulty = await self._assess_problem_difficulty(problem)
            problem.base_reward_points = self.status_point_base[problem.difficulty]
            
            # Store problem
            self.problems[problem_id] = problem
            
            # Update statistics
            self.solver_stats["problems_created"] += 1
            self.solver_stats["difficulty_distribution"][problem.difficulty.name] += 1
            self.solver_stats["category_distribution"][problem.category.name] += 1
            
            log_agent_event(
                self.agent_id,
                "problem_created",
                {
                    "problem_id": problem_id,
                    "title": title,
                    "category": category.value,
                    "difficulty": problem.difficulty.value,
                    "base_reward": problem.base_reward_points
                }
            )
            
            self.logger.info(f"Created problem {problem_id}: {title} (difficulty: {problem.difficulty.name})")
            
            return problem_id
            
        except Exception as e:
            self.logger.error(f"Failed to create problem: {e}")
            raise
    
    async def start_solving_session(self, problem_id: str) -> str:
        """
        Start a problem-solving session.
        
        Args:
            problem_id: ID of the problem to solve
            
        Returns:
            Session ID
        """
        try:
            if problem_id not in self.problems:
                raise ValueError(f"Problem {problem_id} not found")
            
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{problem_id}"
            
            session = ProblemSolvingSession(
                session_id=session_id,
                agent_id=self.agent_id,
                problem_id=problem_id,
                start_time=datetime.now()
            )
            
            self.active_sessions[session_id] = session
            
            log_agent_event(
                self.agent_id,
                "problem_solving_started",
                {
                    "session_id": session_id,
                    "problem_id": problem_id,
                    "problem_title": self.problems[problem_id].title
                }
            )
            
            self.logger.info(f"Started solving session {session_id} for problem {problem_id}")
            
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to start solving session: {e}")
            raise
    
    async def solve_problem(
        self,
        session_id: str,
        solution_description: str,
        implementation: Optional[str] = None,
        reasoning_steps: List[str] = None
    ) -> str:
        """
        Submit a solution for a problem.
        
        Args:
            session_id: Problem-solving session ID
            solution_description: Description of the solution
            implementation: Optional implementation code/details
            reasoning_steps: Steps taken to reach the solution
            
        Returns:
            Solution ID
        """
        try:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found or not active")
            
            session = self.active_sessions[session_id]
            problem = self.problems[session.problem_id]
            
            solution_id = f"solution_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{session.problem_id}"
            
            # Calculate time taken
            time_taken = (datetime.now() - session.start_time).total_seconds() / 3600.0  # hours
            
            # Create solution
            solution = Solution(
                solution_id=solution_id,
                problem_id=session.problem_id,
                agent_id=self.agent_id,
                solution_description=solution_description,
                implementation=implementation,
                reasoning_steps=reasoning_steps or [],
                time_taken=time_taken
            )
            
            # Evaluate solution
            await self._evaluate_solution(solution, problem)
            
            # Calculate status points
            status_points = self._calculate_status_points(solution, problem)
            solution.status_points_awarded = status_points
            
            # Store solution
            self.solutions[solution_id] = solution
            session.solution = solution
            session.end_time = datetime.now()
            session.final_status = "completed"
            
            # Move session to completed
            self.completed_sessions.append(session)
            del self.active_sessions[session_id]
            
            # Update statistics
            self.solver_stats["problems_solved"] += 1
            self.solver_stats["total_status_points_awarded"] += status_points
            
            # Update average solution time
            total_sessions = len(self.completed_sessions)
            if total_sessions > 0:
                total_time = sum(s.solution.time_taken for s in self.completed_sessions if s.solution)
                self.solver_stats["average_solution_time"] = total_time / total_sessions
            
            log_agent_event(
                self.agent_id,
                "problem_solved",
                {
                    "session_id": session_id,
                    "solution_id": solution_id,
                    "problem_id": session.problem_id,
                    "time_taken": time_taken,
                    "quality": solution.quality.name if solution.quality else "unknown",
                    "status_points": status_points
                }
            )
            
            self.logger.info(f"Solved problem {session.problem_id} with solution {solution_id} (points: {status_points})")
            
            return solution_id
            
        except Exception as e:
            self.logger.error(f"Failed to solve problem: {e}")
            raise
    
    async def evaluate_problem_difficulty(self, problem_description: str, category: ProblemCategory) -> ProblemDifficulty:
        """
        Evaluate the difficulty of a problem based on its description.
        
        Args:
            problem_description: Description of the problem
            category: Problem category
            
        Returns:
            Assessed difficulty level
        """
        try:
            # Create temporary problem for assessment
            temp_problem = Problem(
                problem_id="temp",
                title="Temporary",
                description=problem_description,
                category=category
            )
            
            return await self._assess_problem_difficulty(temp_problem)
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate problem difficulty: {e}")
            return ProblemDifficulty.MEDIUM  # Default fallback
    
    async def get_recommended_problems(self, agent_skill_level: float, category: Optional[ProblemCategory] = None) -> List[Problem]:
        """
        Get recommended problems based on agent skill level.
        
        Args:
            agent_skill_level: Agent's skill level (0.0 to 1.0)
            category: Optional category filter
            
        Returns:
            List of recommended problems
        """
        try:
            # Map skill level to difficulty range
            if agent_skill_level < 0.2:
                target_difficulties = [ProblemDifficulty.TRIVIAL, ProblemDifficulty.EASY]
            elif agent_skill_level < 0.4:
                target_difficulties = [ProblemDifficulty.EASY, ProblemDifficulty.MEDIUM]
            elif agent_skill_level < 0.6:
                target_difficulties = [ProblemDifficulty.MEDIUM, ProblemDifficulty.HARD]
            elif agent_skill_level < 0.8:
                target_difficulties = [ProblemDifficulty.HARD, ProblemDifficulty.EXPERT]
            else:
                target_difficulties = [ProblemDifficulty.EXPERT, ProblemDifficulty.LEGENDARY]
            
            # Filter problems
            recommended = []
            for problem in self.problems.values():
                if problem.difficulty in target_difficulties:
                    if category is None or problem.category == category:
                        recommended.append(problem)
            
            # Sort by difficulty and creation time
            recommended.sort(key=lambda p: (p.difficulty.value, p.created_at), reverse=True)
            
            return recommended[:10]  # Return top 10 recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to get recommended problems: {e}")
            return []
    
    def get_problem_solving_statistics(self) -> Dict[str, Any]:
        """Get problem-solving statistics."""
        return {
            **self.solver_stats,
            "active_sessions": len(self.active_sessions),
            "completed_sessions": len(self.completed_sessions),
            "total_problems": len(self.problems),
            "total_solutions": len(self.solutions)
        }
    
    def get_agent_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this agent."""
        completed_solutions = [s.solution for s in self.completed_sessions if s.solution]
        
        if not completed_solutions:
            return {"no_solutions": True}
        
        # Calculate averages
        avg_correctness = sum(s.correctness_score for s in completed_solutions) / len(completed_solutions)
        avg_creativity = sum(s.creativity_score for s in completed_solutions) / len(completed_solutions)
        avg_efficiency = sum(s.efficiency_score for s in completed_solutions) / len(completed_solutions)
        avg_elegance = sum(s.elegance_score for s in completed_solutions) / len(completed_solutions)
        
        # Quality distribution
        quality_dist = {}
        for solution in completed_solutions:
            if solution.quality:
                quality_name = solution.quality.name
                quality_dist[quality_name] = quality_dist.get(quality_name, 0) + 1
        
        return {
            "total_problems_solved": len(completed_solutions),
            "total_status_points": sum(s.status_points_awarded for s in completed_solutions),
            "average_correctness": avg_correctness,
            "average_creativity": avg_creativity,
            "average_efficiency": avg_efficiency,
            "average_elegance": avg_elegance,
            "average_solution_time": self.solver_stats["average_solution_time"],
            "quality_distribution": quality_dist
        }
    
    # Private helper methods
    
    async def _assess_problem_difficulty(self, problem: Problem) -> ProblemDifficulty:
        """Assess the difficulty of a problem."""
        try:
            # Use AI brain to analyze problem complexity
            analysis = await self.ai_brain.analyze_situation(
                situation=f"Assess the difficulty of this problem: {problem.title}",
                available_data={
                    "description": problem.description,
                    "category": problem.category.value,
                    "constraints": problem.constraints,
                    "success_criteria": problem.success_criteria
                },
                goals=["Determine problem complexity and difficulty level"]
            )
            
            # Calculate base difficulty score
            difficulty_score = 1.0
            
            # Analyze description for complexity keywords
            description_lower = problem.description.lower()
            for keyword, multiplier in self.difficulty_factors["complexity_keywords"].items():
                if keyword in description_lower:
                    difficulty_score *= multiplier
            
            # Factor in constraints
            if problem.constraints:
                difficulty_score *= (1 + len(problem.constraints) * 0.1)
            
            # Factor in time pressure
            if problem.time_limit and problem.time_limit < 24:  # Less than 24 hours
                difficulty_score *= self.difficulty_factors["time_pressure_multiplier"]
            
            # Factor in success criteria complexity
            if problem.success_criteria:
                difficulty_score *= (1 + len(problem.success_criteria) * 0.05)
            
            # Use AI analysis confidence to adjust
            ai_confidence = analysis.get("confidence", 0.5)
            if ai_confidence > 0.8:
                # High confidence in complexity assessment
                ai_analysis = analysis.get("analysis", "").lower()
                if any(word in ai_analysis for word in ["complex", "difficult", "challenging", "advanced"]):
                    difficulty_score *= 1.3
                elif any(word in ai_analysis for word in ["simple", "easy", "basic", "straightforward"]):
                    difficulty_score *= 0.7
            
            # Map score to difficulty level
            if difficulty_score < 1.2:
                return ProblemDifficulty.TRIVIAL
            elif difficulty_score < 1.8:
                return ProblemDifficulty.EASY
            elif difficulty_score < 2.5:
                return ProblemDifficulty.MEDIUM
            elif difficulty_score < 3.5:
                return ProblemDifficulty.HARD
            elif difficulty_score < 5.0:
                return ProblemDifficulty.EXPERT
            else:
                return ProblemDifficulty.LEGENDARY
            
        except Exception as e:
            self.logger.error(f"Failed to assess problem difficulty: {e}")
            return ProblemDifficulty.MEDIUM  # Default fallback
    
    async def _evaluate_solution(self, solution: Solution, problem: Problem) -> None:
        """Evaluate the quality of a solution."""
        try:
            # Use AI brain to evaluate solution
            evaluation = await self.ai_brain.analyze_situation(
                situation=f"Evaluate this solution to the problem: {problem.title}",
                available_data={
                    "problem_description": problem.description,
                    "solution_description": solution.solution_description,
                    "implementation": solution.implementation or "",
                    "reasoning_steps": solution.reasoning_steps,
                    "success_criteria": problem.success_criteria
                },
                goals=["Evaluate solution correctness, creativity, efficiency, and elegance"]
            )
            
            # Extract scores from AI evaluation
            evaluation.get("insights", [])
            ai_analysis = evaluation.get("analysis", "").lower()
            
            # Correctness score (0.0 to 1.0)
            solution.correctness_score = self._extract_score_from_analysis(
                ai_analysis, ["correct", "accurate", "valid", "right"], 0.7
            )
            
            # Creativity score (0.0 to 1.0)
            solution.creativity_score = self._extract_score_from_analysis(
                ai_analysis, ["creative", "innovative", "novel", "original"], 0.5
            )
            
            # Efficiency score (0.0 to 1.0)
            solution.efficiency_score = self._extract_score_from_analysis(
                ai_analysis, ["efficient", "optimal", "fast", "quick"], 0.6
            )
            
            # Elegance score (0.0 to 1.0)
            solution.elegance_score = self._extract_score_from_analysis(
                ai_analysis, ["elegant", "clean", "simple", "beautiful"], 0.5
            )
            
            # Calculate overall quality
            overall_score = (
                solution.correctness_score * 0.4 +
                solution.creativity_score * 0.2 +
                solution.efficiency_score * 0.2 +
                solution.elegance_score * 0.2
            )
            
            # Map to quality enum
            if overall_score < 0.3:
                solution.quality = SolutionQuality.POOR
            elif overall_score < 0.5:
                solution.quality = SolutionQuality.BELOW_AVERAGE
            elif overall_score < 0.7:
                solution.quality = SolutionQuality.AVERAGE
            elif overall_score < 0.8:
                solution.quality = SolutionQuality.GOOD
            elif overall_score < 0.9:
                solution.quality = SolutionQuality.EXCELLENT
            else:
                solution.quality = SolutionQuality.EXCEPTIONAL
            
            solution.evaluated_at = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate solution: {e}")
            # Set default values
            solution.correctness_score = 0.5
            solution.creativity_score = 0.5
            solution.efficiency_score = 0.5
            solution.elegance_score = 0.5
            solution.quality = SolutionQuality.AVERAGE
    
    def _extract_score_from_analysis(self, analysis: str, positive_keywords: List[str], default: float) -> float:
        """Extract a score from AI analysis text."""
        score = default
        
        # Count positive mentions
        positive_count = sum(1 for keyword in positive_keywords if keyword in analysis)
        
        # Count negative mentions
        negative_keywords = ["incorrect", "wrong", "poor", "bad", "inefficient", "slow"]
        negative_count = sum(1 for keyword in negative_keywords if keyword in analysis)
        
        # Adjust score based on mentions
        score += positive_count * 0.1
        score -= negative_count * 0.1
        
        # Clamp to valid range
        return max(0.0, min(1.0, score))
    
    def _calculate_status_points(self, solution: Solution, problem: Problem) -> int:
        """Calculate status points for a solution."""
        try:
            # Base points from problem difficulty
            base_points = self.status_point_base[problem.difficulty]
            
            # Quality multiplier
            quality_multiplier = self.quality_multipliers[solution.quality]
            
            # Time bonus/penalty
            time_multiplier = 1.0
            if problem.time_limit:
                time_ratio = solution.time_taken / problem.time_limit
                if time_ratio < 0.5:  # Solved in less than half the time
                    time_multiplier = 1.5
                elif time_ratio < 0.8:  # Solved in less than 80% of time
                    time_multiplier = 1.2
                elif time_ratio > 1.0:  # Exceeded time limit
                    time_multiplier = 0.5
            
            # Correctness bonus
            correctness_multiplier = 0.5 + (solution.correctness_score * 0.5)
            
            # Calculate final points
            final_points = int(
                base_points * 
                quality_multiplier * 
                time_multiplier * 
                correctness_multiplier
            )
            
            return max(1, final_points)  # Minimum 1 point
            
        except Exception as e:
            self.logger.error(f"Failed to calculate status points: {e}")
            return 1  # Minimum fallback
    
    async def _complete_active_sessions(self) -> None:
        """Complete any active sessions during shutdown."""
        for session_id, session in list(self.active_sessions.items()):
            session.end_time = datetime.now()
            session.final_status = "abandoned"
            self.completed_sessions.append(session)
            del self.active_sessions[session_id]
    
    async def _load_problem_data(self) -> None:
        """Load problem and solution data from storage."""
        # Placeholder for loading from persistent storage
        pass
    
    async def _save_problem_data(self) -> None:
        """Save problem and solution data to storage."""
        # Placeholder for saving to persistent storage
        pass