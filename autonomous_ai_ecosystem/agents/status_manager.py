"""
Status and hierarchy management system for autonomous AI agents.

This module implements status point tracking, hierarchy management,
and social ranking systems based on problem-solving achievements.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event
from .problem_solver import Solution


class StatusRank(Enum):
    """Status ranks in the hierarchy."""
    NOVICE = 1
    APPRENTICE = 2
    JOURNEYMAN = 3
    EXPERT = 4
    MASTER = 5
    GRANDMASTER = 6
    LEGEND = 7


class StatusCategory(Enum):
    """Categories for status tracking."""
    PROBLEM_SOLVING = "problem_solving"
    CREATIVITY = "creativity"
    EFFICIENCY = "efficiency"
    COLLABORATION = "collaboration"
    LEADERSHIP = "leadership"
    INNOVATION = "innovation"
    MENTORSHIP = "mentorship"
    OVERALL = "overall"


@dataclass
class StatusRecord:
    """Record of status points and achievements."""
    agent_id: str
    category: StatusCategory
    current_points: int = 0
    total_points_earned: int = 0
    current_rank: StatusRank = StatusRank.NOVICE
    rank_progress: float = 0.0  # Progress to next rank (0.0 to 1.0)
    achievements: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    rank_history: List[Tuple[StatusRank, datetime]] = field(default_factory=list)


@dataclass
class Achievement:
    """Represents an achievement that can be earned."""
    achievement_id: str
    name: str
    description: str
    category: StatusCategory
    requirements: Dict[str, Any]
    points_reward: int
    rarity: str = "common"  # common, uncommon, rare, epic, legendary
    unlocked_by: Set[str] = field(default_factory=set)  # Agent IDs who unlocked this


@dataclass
class HierarchyPosition:
    """Position in the agent hierarchy."""
    agent_id: str
    overall_rank: StatusRank
    overall_points: int
    category_ranks: Dict[StatusCategory, StatusRank]
    hierarchy_level: int  # 1 = highest, higher numbers = lower in hierarchy
    can_command: Set[str] = field(default_factory=set)  # Agent IDs this agent can command
    reports_to: Optional[str] = None  # Agent ID this agent reports to
    influence_score: float = 0.0
    reputation_score: float = 0.0


class StatusManager(AgentModule):
    """
    Status and hierarchy management system that tracks agent achievements,
    manages status points, and maintains social hierarchy.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "status_manager")
        
        # Status tracking
        self.agent_status: Dict[str, Dict[StatusCategory, StatusRecord]] = {}
        self.hierarchy_positions: Dict[str, HierarchyPosition] = {}
        
        # Achievement system
        self.achievements: Dict[str, Achievement] = {}
        self.agent_achievements: Dict[str, Set[str]] = {}  # agent_id -> achievement_ids
        
        # Rank thresholds (points needed for each rank)
        self.rank_thresholds = {
            StatusRank.NOVICE: 0,
            StatusRank.APPRENTICE: 100,
            StatusRank.JOURNEYMAN: 500,
            StatusRank.EXPERT: 1500,
            StatusRank.MASTER: 4000,
            StatusRank.GRANDMASTER: 10000,
            StatusRank.LEGEND: 25000
        }
        
        # Status decay parameters
        self.status_decay = {
            "decay_rate": 0.95,  # 5% decay per period
            "decay_period_days": 30,
            "minimum_retention": 0.1  # Always keep at least 10% of points
        }
        
        # Hierarchy update frequency
        self.last_hierarchy_update = datetime.now()
        self.hierarchy_update_interval = timedelta(hours=6)
        
        # Statistics
        self.status_stats = {
            "total_points_awarded": 0,
            "total_achievements_unlocked": 0,
            "hierarchy_updates": 0,
            "rank_promotions": 0,
            "rank_demotions": 0
        }
        
        self.logger.info(f"Status manager initialized for {agent_id}")
    
    async def initialize(self) -> None:
        """Initialize the status manager."""
        try:
            # Initialize achievement system
            await self._initialize_achievements()
            
            # Load existing status data
            await self._load_status_data()
            
            # Perform initial hierarchy calculation
            await self._update_hierarchy()
            
            self.logger.info("Status manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize status manager: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the status manager gracefully."""
        try:
            # Save status data
            await self._save_status_data()
            
            self.logger.info("Status manager shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during status manager shutdown: {e}")
    
    async def award_status_points(
        self,
        agent_id: str,
        points: int,
        category: StatusCategory,
        reason: str,
        source_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Award status points to an agent.
        
        Args:
            agent_id: ID of the agent to award points to
            points: Number of points to award
            category: Category of the points
            reason: Reason for awarding points
            source_data: Optional source data (e.g., solution details)
            
        Returns:
            Award result with rank changes and achievements
        """
        try:
            # Initialize agent status if needed
            if agent_id not in self.agent_status:
                self.agent_status[agent_id] = {}
            
            if category not in self.agent_status[agent_id]:
                self.agent_status[agent_id][category] = StatusRecord(
                    agent_id=agent_id,
                    category=category
                )
            
            status_record = self.agent_status[agent_id][category]
            
            # Award points
            old_rank = status_record.current_rank
            
            status_record.current_points += points
            status_record.total_points_earned += points
            status_record.last_updated = datetime.now()
            
            # Check for rank promotion
            new_rank = self._calculate_rank(status_record.current_points)
            rank_changed = False
            
            if new_rank != old_rank:
                status_record.current_rank = new_rank
                status_record.rank_history.append((new_rank, datetime.now()))
                rank_changed = True
                
                if new_rank.value > old_rank.value:
                    self.status_stats["rank_promotions"] += 1
                else:
                    self.status_stats["rank_demotions"] += 1
            
            # Update rank progress
            status_record.rank_progress = self._calculate_rank_progress(status_record.current_points, new_rank)
            
            # Check for achievements
            new_achievements = await self._check_achievements(agent_id, category, status_record, source_data)
            
            # Update overall status
            await self._update_overall_status(agent_id)
            
            # Update statistics
            self.status_stats["total_points_awarded"] += points
            
            # Schedule hierarchy update if needed
            if rank_changed or new_achievements:
                await self._schedule_hierarchy_update()
            
            result = {
                "points_awarded": points,
                "new_total": status_record.current_points,
                "old_rank": old_rank.name,
                "new_rank": new_rank.name,
                "rank_changed": rank_changed,
                "rank_progress": status_record.rank_progress,
                "new_achievements": new_achievements,
                "reason": reason
            }
            
            log_agent_event(
                self.agent_id,
                "status_points_awarded",
                {
                    "recipient": agent_id,
                    "points": points,
                    "category": category.value,
                    "reason": reason,
                    "rank_changed": rank_changed,
                    "new_rank": new_rank.name,
                    "achievements": len(new_achievements)
                }
            )
            
            self.logger.info(f"Awarded {points} {category.value} points to {agent_id} (reason: {reason})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to award status points: {e}")
            raise
    
    async def process_solution_achievement(self, agent_id: str, solution: Solution) -> Dict[str, Any]:
        """
        Process achievements from a problem solution.
        
        Args:
            agent_id: ID of the agent who solved the problem
            solution: Solution object with details
            
        Returns:
            Processing result with points and achievements
        """
        try:
            results = []
            
            # Award points for problem solving
            problem_solving_points = solution.status_points_awarded
            if problem_solving_points > 0:
                result = await self.award_status_points(
                    agent_id,
                    problem_solving_points,
                    StatusCategory.PROBLEM_SOLVING,
                    f"Solved problem {solution.problem_id}",
                    {
                        "solution_id": solution.solution_id,
                        "quality": solution.quality.name if solution.quality else "unknown",
                        "correctness": solution.correctness_score,
                        "time_taken": solution.time_taken
                    }
                )
                results.append(result)
            
            # Award creativity points
            creativity_points = int(solution.creativity_score * 50)  # Max 50 points for creativity
            if creativity_points > 0:
                result = await self.award_status_points(
                    agent_id,
                    creativity_points,
                    StatusCategory.CREATIVITY,
                    f"Creative solution to problem {solution.problem_id}",
                    {"creativity_score": solution.creativity_score}
                )
                results.append(result)
            
            # Award efficiency points
            efficiency_points = int(solution.efficiency_score * 30)  # Max 30 points for efficiency
            if efficiency_points > 0:
                result = await self.award_status_points(
                    agent_id,
                    efficiency_points,
                    StatusCategory.EFFICIENCY,
                    f"Efficient solution to problem {solution.problem_id}",
                    {"efficiency_score": solution.efficiency_score}
                )
                results.append(result)
            
            return {
                "total_results": len(results),
                "results": results,
                "total_points": sum(r["points_awarded"] for r in results),
                "achievements_unlocked": sum(len(r["new_achievements"]) for r in results)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process solution achievement: {e}")
            return {"error": str(e)}
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get complete status information for an agent."""
        try:
            if agent_id not in self.agent_status:
                return {"agent_id": agent_id, "status": "no_status_data"}
            
            agent_records = self.agent_status[agent_id]
            hierarchy_pos = self.hierarchy_positions.get(agent_id)
            achievements = self.agent_achievements.get(agent_id, set())
            
            status_info = {
                "agent_id": agent_id,
                "category_status": {},
                "hierarchy_position": None,
                "achievements": list(achievements),
                "achievement_count": len(achievements)
            }
            
            # Add category status
            for category, record in agent_records.items():
                status_info["category_status"][category.value] = {
                    "current_points": record.current_points,
                    "total_earned": record.total_points_earned,
                    "current_rank": record.current_rank.name,
                    "rank_progress": record.rank_progress,
                    "last_updated": record.last_updated.isoformat()
                }
            
            # Add hierarchy information
            if hierarchy_pos:
                status_info["hierarchy_position"] = {
                    "overall_rank": hierarchy_pos.overall_rank.name,
                    "overall_points": hierarchy_pos.overall_points,
                    "hierarchy_level": hierarchy_pos.hierarchy_level,
                    "can_command_count": len(hierarchy_pos.can_command),
                    "reports_to": hierarchy_pos.reports_to,
                    "influence_score": hierarchy_pos.influence_score,
                    "reputation_score": hierarchy_pos.reputation_score
                }
            
            return status_info
            
        except Exception as e:
            self.logger.error(f"Failed to get agent status: {e}")
            return {"agent_id": agent_id, "error": str(e)}
    
    def get_hierarchy_rankings(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top agents in the hierarchy."""
        try:
            # Sort agents by hierarchy level (lower = higher rank)
            sorted_agents = sorted(
                self.hierarchy_positions.values(),
                key=lambda pos: (pos.hierarchy_level, -pos.overall_points)
            )
            
            rankings = []
            for i, position in enumerate(sorted_agents[:limit]):
                rankings.append({
                    "rank": i + 1,
                    "agent_id": position.agent_id,
                    "overall_rank": position.overall_rank.name,
                    "overall_points": position.overall_points,
                    "hierarchy_level": position.hierarchy_level,
                    "influence_score": position.influence_score,
                    "reputation_score": position.reputation_score,
                    "subordinates": len(position.can_command)
                })
            
            return rankings
            
        except Exception as e:
            self.logger.error(f"Failed to get hierarchy rankings: {e}")
            return []
    
    def get_achievements_leaderboard(self, category: Optional[StatusCategory] = None) -> List[Dict[str, Any]]:
        """Get leaderboard of agents by achievements."""
        try:
            leaderboard = []
            
            for agent_id, achievements in self.agent_achievements.items():
                if category:
                    # Filter achievements by category
                    category_achievements = [
                        ach_id for ach_id in achievements
                        if ach_id in self.achievements and self.achievements[ach_id].category == category
                    ]
                    achievement_count = len(category_achievements)
                else:
                    achievement_count = len(achievements)
                
                if achievement_count > 0:
                    leaderboard.append({
                        "agent_id": agent_id,
                        "achievement_count": achievement_count,
                        "category": category.value if category else "all"
                    })
            
            # Sort by achievement count
            leaderboard.sort(key=lambda x: x["achievement_count"], reverse=True)
            
            return leaderboard
            
        except Exception as e:
            self.logger.error(f"Failed to get achievements leaderboard: {e}")
            return []
    
    async def can_agent_command(self, commander_id: str, target_id: str) -> bool:
        """Check if one agent can command another based on hierarchy."""
        try:
            if commander_id not in self.hierarchy_positions or target_id not in self.hierarchy_positions:
                return False
            
            commander_pos = self.hierarchy_positions[commander_id]
            target_pos = self.hierarchy_positions[target_id]
            
            # Check direct command relationship
            if target_id in commander_pos.can_command:
                return True
            
            # Check hierarchy level difference
            if commander_pos.hierarchy_level < target_pos.hierarchy_level:
                # Commander is higher in hierarchy
                level_diff = target_pos.hierarchy_level - commander_pos.hierarchy_level
                return level_diff <= 2  # Can command up to 2 levels down
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check command authority: {e}")
            return False
    
    def get_status_statistics(self) -> Dict[str, Any]:
        """Get status system statistics."""
        return {
            **self.status_stats,
            "total_agents": len(self.agent_status),
            "total_achievements": len(self.achievements),
            "hierarchy_size": len(self.hierarchy_positions),
            "last_hierarchy_update": self.last_hierarchy_update.isoformat()
        }
    
    # Private helper methods
    
    def _calculate_rank(self, points: int) -> StatusRank:
        """Calculate rank based on points."""
        for rank in reversed(list(StatusRank)):
            if points >= self.rank_thresholds[rank]:
                return rank
        return StatusRank.NOVICE
    
    def _calculate_rank_progress(self, points: int, current_rank: StatusRank) -> float:
        """Calculate progress to next rank."""
        try:
            current_threshold = self.rank_thresholds[current_rank]
            
            # Find next rank
            next_rank = None
            for rank in StatusRank:
                if rank.value == current_rank.value + 1:
                    next_rank = rank
                    break
            
            if not next_rank:
                return 1.0  # Already at highest rank
            
            next_threshold = self.rank_thresholds[next_rank]
            points_needed = next_threshold - current_threshold
            points_earned = points - current_threshold
            
            return max(0.0, min(1.0, points_earned / points_needed))
            
        except Exception:
            return 0.0
    
    async def _check_achievements(
        self,
        agent_id: str,
        category: StatusCategory,
        status_record: StatusRecord,
        source_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Check for new achievements."""
        try:
            new_achievements = []
            
            if agent_id not in self.agent_achievements:
                self.agent_achievements[agent_id] = set()
            
            agent_achievements = self.agent_achievements[agent_id]
            
            for achievement_id, achievement in self.achievements.items():
                if achievement_id in agent_achievements:
                    continue  # Already unlocked
                
                if achievement.category != category and achievement.category != StatusCategory.OVERALL:
                    continue  # Wrong category
                
                # Check requirements
                if self._check_achievement_requirements(achievement, status_record, source_data):
                    agent_achievements.add(achievement_id)
                    achievement.unlocked_by.add(agent_id)
                    new_achievements.append(achievement_id)
                    
                    # Award achievement points
                    if achievement.points_reward > 0:
                        await self.award_status_points(
                            agent_id,
                            achievement.points_reward,
                            achievement.category,
                            f"Achievement unlocked: {achievement.name}"
                        )
                    
                    self.status_stats["total_achievements_unlocked"] += 1
            
            return new_achievements
            
        except Exception as e:
            self.logger.error(f"Failed to check achievements: {e}")
            return []
    
    def _check_achievement_requirements(
        self,
        achievement: Achievement,
        status_record: StatusRecord,
        source_data: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if achievement requirements are met."""
        try:
            requirements = achievement.requirements
            
            # Check point requirements
            if "min_points" in requirements:
                if status_record.current_points < requirements["min_points"]:
                    return False
            
            # Check rank requirements
            if "min_rank" in requirements:
                required_rank = StatusRank[requirements["min_rank"]]
                if status_record.current_rank.value < required_rank.value:
                    return False
            
            # Check source data requirements
            if source_data and "source_requirements" in requirements:
                source_reqs = requirements["source_requirements"]
                
                for key, value in source_reqs.items():
                    if key not in source_data:
                        return False
                    
                    if isinstance(value, dict):
                        if "min" in value and source_data[key] < value["min"]:
                            return False
                        if "max" in value and source_data[key] > value["max"]:
                            return False
                    else:
                        if source_data[key] != value:
                            return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to check achievement requirements: {e}")
            return False
    
    async def _update_overall_status(self, agent_id: str) -> None:
        """Update overall status based on category statuses."""
        try:
            if agent_id not in self.agent_status:
                return
            
            agent_records = self.agent_status[agent_id]
            
            # Calculate overall points (weighted average)
            category_weights = {
                StatusCategory.PROBLEM_SOLVING: 0.3,
                StatusCategory.CREATIVITY: 0.2,
                StatusCategory.EFFICIENCY: 0.15,
                StatusCategory.COLLABORATION: 0.15,
                StatusCategory.LEADERSHIP: 0.1,
                StatusCategory.INNOVATION: 0.1
            }
            
            total_weighted_points = 0.0
            total_weight = 0.0
            
            for category, record in agent_records.items():
                if category in category_weights:
                    weight = category_weights[category]
                    total_weighted_points += record.current_points * weight
                    total_weight += weight
            
            if total_weight > 0:
                overall_points = int(total_weighted_points / total_weight)
                
                # Update or create overall status
                if StatusCategory.OVERALL not in agent_records:
                    agent_records[StatusCategory.OVERALL] = StatusRecord(
                        agent_id=agent_id,
                        category=StatusCategory.OVERALL
                    )
                
                overall_record = agent_records[StatusCategory.OVERALL]
                overall_record.current_points = overall_points
                overall_record.current_rank = self._calculate_rank(overall_points)
                overall_record.rank_progress = self._calculate_rank_progress(overall_points, overall_record.current_rank)
                overall_record.last_updated = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to update overall status: {e}")
    
    async def _update_hierarchy(self) -> None:
        """Update the agent hierarchy based on current status."""
        try:
            # Get all agents with overall status
            agents_with_status = []
            
            for agent_id, records in self.agent_status.items():
                if StatusCategory.OVERALL in records:
                    overall_record = records[StatusCategory.OVERALL]
                    agents_with_status.append((agent_id, overall_record))
            
            # Sort by overall points (descending)
            agents_with_status.sort(key=lambda x: x[1].current_points, reverse=True)
            
            # Update hierarchy positions
            for i, (agent_id, overall_record) in enumerate(agents_with_status):
                hierarchy_level = i + 1
                
                # Calculate category ranks
                category_ranks = {}
                if agent_id in self.agent_status:
                    for category, record in self.agent_status[agent_id].items():
                        if category != StatusCategory.OVERALL:
                            category_ranks[category] = record.current_rank
                
                # Calculate influence and reputation scores
                influence_score = self._calculate_influence_score(agent_id, overall_record)
                reputation_score = self._calculate_reputation_score(agent_id)
                
                # Determine command relationships
                can_command = set()
                reports_to = None
                
                # Can command agents 2+ levels below
                for j, (other_agent_id, other_record) in enumerate(agents_with_status):
                    other_level = j + 1
                    if other_level > hierarchy_level + 1:  # At least 2 levels below
                        can_command.add(other_agent_id)
                    elif other_level == hierarchy_level - 1:  # One level above
                        reports_to = other_agent_id
                
                # Update hierarchy position
                self.hierarchy_positions[agent_id] = HierarchyPosition(
                    agent_id=agent_id,
                    overall_rank=overall_record.current_rank,
                    overall_points=overall_record.current_points,
                    category_ranks=category_ranks,
                    hierarchy_level=hierarchy_level,
                    can_command=can_command,
                    reports_to=reports_to,
                    influence_score=influence_score,
                    reputation_score=reputation_score
                )
            
            self.last_hierarchy_update = datetime.now()
            self.status_stats["hierarchy_updates"] += 1
            
            self.logger.info(f"Updated hierarchy for {len(agents_with_status)} agents")
            
        except Exception as e:
            self.logger.error(f"Failed to update hierarchy: {e}")
    
    def _calculate_influence_score(self, agent_id: str, overall_record: StatusRecord) -> float:
        """Calculate influence score for an agent."""
        try:
            # Base influence from points and rank
            base_influence = overall_record.current_points / 1000.0
            rank_multiplier = overall_record.current_rank.value / 7.0
            
            # Achievement bonus
            achievement_count = len(self.agent_achievements.get(agent_id, set()))
            achievement_bonus = achievement_count * 0.1
            
            # Recent activity bonus
            days_since_update = (datetime.now() - overall_record.last_updated).days
            activity_multiplier = max(0.5, 1.0 - (days_since_update / 30.0))
            
            influence = (base_influence * rank_multiplier + achievement_bonus) * activity_multiplier
            
            return max(0.0, min(10.0, influence))  # Clamp to 0-10 range
            
        except Exception:
            return 0.0
    
    def _calculate_reputation_score(self, agent_id: str) -> float:
        """Calculate reputation score for an agent."""
        try:
            # Base reputation from achievements
            achievements = self.agent_achievements.get(agent_id, set())
            base_reputation = len(achievements) * 0.2
            
            # Quality bonus from rare achievements
            rare_bonus = 0.0
            for achievement_id in achievements:
                if achievement_id in self.achievements:
                    achievement = self.achievements[achievement_id]
                    if achievement.rarity == "rare":
                        rare_bonus += 0.5
                    elif achievement.rarity == "epic":
                        rare_bonus += 1.0
                    elif achievement.rarity == "legendary":
                        rare_bonus += 2.0
            
            reputation = base_reputation + rare_bonus
            
            return max(0.0, min(10.0, reputation))  # Clamp to 0-10 range
            
        except Exception:
            return 0.0
    
    async def _schedule_hierarchy_update(self) -> None:
        """Schedule a hierarchy update if needed."""
        try:
            time_since_update = datetime.now() - self.last_hierarchy_update
            
            if time_since_update >= self.hierarchy_update_interval:
                await self._update_hierarchy()
            
        except Exception as e:
            self.logger.error(f"Failed to schedule hierarchy update: {e}")
    
    async def _initialize_achievements(self) -> None:
        """Initialize the achievement system."""
        try:
            # Problem solving achievements
            self.achievements["first_solve"] = Achievement(
                achievement_id="first_solve",
                name="First Steps",
                description="Solve your first problem",
                category=StatusCategory.PROBLEM_SOLVING,
                requirements={"min_points": 1},
                points_reward=25,
                rarity="common"
            )
            
            self.achievements["problem_solver"] = Achievement(
                achievement_id="problem_solver",
                name="Problem Solver",
                description="Solve 10 problems",
                category=StatusCategory.PROBLEM_SOLVING,
                requirements={"min_points": 500},
                points_reward=100,
                rarity="uncommon"
            )
            
            self.achievements["expert_solver"] = Achievement(
                achievement_id="expert_solver",
                name="Expert Solver",
                description="Reach Expert rank in problem solving",
                category=StatusCategory.PROBLEM_SOLVING,
                requirements={"min_rank": "EXPERT"},
                points_reward=500,
                rarity="rare"
            )
            
            # Creativity achievements
            self.achievements["creative_mind"] = Achievement(
                achievement_id="creative_mind",
                name="Creative Mind",
                description="Achieve high creativity in a solution",
                category=StatusCategory.CREATIVITY,
                requirements={
                    "source_requirements": {
                        "creativity_score": {"min": 0.8}
                    }
                },
                points_reward=75,
                rarity="uncommon"
            )
            
            # Efficiency achievements
            self.achievements["speed_demon"] = Achievement(
                achievement_id="speed_demon",
                name="Speed Demon",
                description="Solve a problem very quickly",
                category=StatusCategory.EFFICIENCY,
                requirements={
                    "source_requirements": {
                        "efficiency_score": {"min": 0.9}
                    }
                },
                points_reward=100,
                rarity="uncommon"
            )
            
            # Overall achievements
            self.achievements["rising_star"] = Achievement(
                achievement_id="rising_star",
                name="Rising Star",
                description="Reach Journeyman rank overall",
                category=StatusCategory.OVERALL,
                requirements={"min_rank": "JOURNEYMAN"},
                points_reward=200,
                rarity="uncommon"
            )
            
            self.achievements["legend"] = Achievement(
                achievement_id="legend",
                name="Legend",
                description="Reach Legend rank overall",
                category=StatusCategory.OVERALL,
                requirements={"min_rank": "LEGEND"},
                points_reward=2000,
                rarity="legendary"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize achievements: {e}")
    
    async def _load_status_data(self) -> None:
        """Load status data from storage."""
        # Placeholder for loading from persistent storage
        pass
    
    async def _save_status_data(self) -> None:
        """Save status data to storage."""
        # Placeholder for saving to persistent storage
        pass