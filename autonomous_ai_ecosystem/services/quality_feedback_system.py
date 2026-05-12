"""
Service quality and feedback system.

This module implements service quality scoring, performance tracking,
feedback collection, and service improvement mechanisms.
"""

import asyncio
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class FeedbackType(Enum):
    """Types of feedback that can be provided."""
    RATING = "rating"
    COMMENT = "comment"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    PERFORMANCE_ISSUE = "performance_issue"
    QUALITY_ISSUE = "quality_issue"
    IMPROVEMENT_SUGGESTION = "improvement_suggestion"


class FeedbackSentiment(Enum):
    """Sentiment analysis of feedback."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class QualityMetric(Enum):
    """Quality metrics for services."""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    TIMELINESS = "timeliness"
    RELEVANCE = "relevance"
    USABILITY = "usability"
    RELIABILITY = "reliability"
    EFFICIENCY = "efficiency"
    SATISFACTION = "satisfaction"


@dataclass
class ServiceFeedback:
    """Represents feedback for a service execution."""
    feedback_id: str
    service_execution_id: str
    agent_id: str
    service_type: str
    
    # Feedback content
    feedback_type: FeedbackType
    rating: Optional[float] = None  # 1-5 scale
    comment: str = ""
    
    # Quality ratings
    quality_ratings: Dict[QualityMetric, float] = field(default_factory=dict)
    
    # Feedback analysis
    sentiment: Optional[FeedbackSentiment] = None
    priority: int = 5  # 1-10, 10 being highest
    
    # Context
    provided_by: str = ""
    execution_context: Dict[str, Any] = field(default_factory=dict)
    
    # Processing
    processed: bool = False
    action_taken: bool = False
    response_provided: bool = False
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None

@dataclass
class QualityScore:
    """Represents a quality score for a service or agent."""
    score_id: str
    agent_id: str
    service_type: str
    
    # Overall scores
    overall_quality: float = 0.0
    trend_direction: str = "stable"  # improving, declining, stable
    
    # Detailed quality metrics
    metric_scores: Dict[QualityMetric, float] = field(default_factory=dict)
    
    # Performance indicators
    success_rate: float = 0.0
    average_rating: float = 0.0
    completion_time_score: float = 0.0
    reliability_score: float = 0.0
    
    # Feedback statistics
    total_feedback_count: int = 0
    positive_feedback_ratio: float = 0.0
    recent_feedback_trend: float = 0.0
    
    # Benchmarking
    percentile_rank: float = 0.0  # Compared to other agents
    improvement_potential: float = 0.0
    
    # Metadata
    calculated_at: datetime = field(default_factory=datetime.now)
    calculation_period_days: int = 30
    confidence_level: float = 0.0


@dataclass
class ServiceRecommendation:
    """Represents a recommendation for service improvement."""
    recommendation_id: str
    agent_id: str
    service_type: str
    
    # Recommendation details
    title: str
    description: str
    category: str  # performance, quality, user_experience, etc.
    
    # Impact assessment
    expected_improvement: float = 0.0  # Expected quality score improvement
    implementation_effort: str = "medium"  # low, medium, high
    priority_score: float = 0.0
    
    # Supporting data
    supporting_feedback: List[str] = field(default_factory=list)  # feedback_ids
    data_points: Dict[str, Any] = field(default_factory=dict)
    
    # Implementation
    implemented: bool = False
    implementation_date: Optional[datetime] = None
    effectiveness_score: Optional[float] = None
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "quality_system"


class ServiceQualityFeedbackSystem(AgentModule):
    """
    Service quality and feedback system.
    
    Provides quality scoring, performance tracking, feedback collection,
    and service improvement recommendations.
    """
    
    def __init__(self, agent_id: str = "quality_feedback_system"):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "quality_feedback")
        
        # Core data structures
        self.feedback_entries: Dict[str, ServiceFeedback] = {}
        self.quality_scores: Dict[str, QualityScore] = {}  # agent_id -> quality_score
        self.recommendations: Dict[str, List[ServiceRecommendation]] = {}  # agent_id -> recommendations
        
        # Feedback processing
        self.feedback_queue: asyncio.Queue = asyncio.Queue()
        
        # Configuration
        self.config = {
            "feedback_retention_days": 90,
            "quality_calculation_interval_hours": 6,
            "min_feedback_for_score": 5,
            "recommendation_generation_interval_hours": 24,
            "auto_sentiment_analysis": True,
            "quality_score_weights": {
                QualityMetric.ACCURACY: 0.2,
                QualityMetric.COMPLETENESS: 0.15,
                QualityMetric.TIMELINESS: 0.15,
                QualityMetric.RELEVANCE: 0.15,
                QualityMetric.USABILITY: 0.1,
                QualityMetric.RELIABILITY: 0.15,
                QualityMetric.EFFICIENCY: 0.05,
                QualityMetric.SATISFACTION: 0.05
            },
            "sentiment_keywords": {
                FeedbackSentiment.VERY_POSITIVE: ["excellent", "outstanding", "perfect", "amazing"],
                FeedbackSentiment.POSITIVE: ["good", "great", "helpful", "useful", "satisfied"],
                FeedbackSentiment.NEUTRAL: ["okay", "average", "acceptable", "fine"],
                FeedbackSentiment.NEGATIVE: ["poor", "bad", "disappointing", "unsatisfied"],
                FeedbackSentiment.VERY_NEGATIVE: ["terrible", "awful", "useless", "horrible"]
            }
        }
        
        # Statistics
        self.stats = {
            "total_feedback": 0,
            "feedback_by_type": {fb_type.value: 0 for fb_type in FeedbackType},
            "feedback_by_sentiment": {sentiment.value: 0 for sentiment in FeedbackSentiment},
            "quality_scores_calculated": 0,
            "recommendations_generated": 0,
            "average_rating": 0.0,
            "improvement_actions_taken": 0
        }
        
        # Counters
        self.feedback_counter = 0
        self.score_counter = 0
        self.recommendation_counter = 0
        
        self.logger.info("Service quality and feedback system initialized")
    
    async def initialize(self) -> None:
        """Initialize the quality and feedback system."""
        try:
            # Start background tasks
            asyncio.create_task(self._feedback_processing_loop())
            asyncio.create_task(self._quality_calculation_loop())
            asyncio.create_task(self._recommendation_generation_loop())
            asyncio.create_task(self._cleanup_old_data())
            
            self.logger.info("Quality and feedback system initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize quality and feedback system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the quality and feedback system."""
        try:
            # Process remaining feedback
            await self._process_remaining_feedback()
            
            self.logger.info("Quality and feedback system shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during quality and feedback system shutdown: {e}")
    
    async def submit_feedback(
        self,
        service_execution_id: str,
        agent_id: str,
        service_type: str,
        feedback_type: FeedbackType,
        rating: Optional[float] = None,
        comment: str = "",
        quality_ratings: Optional[Dict[QualityMetric, float]] = None,
        provided_by: str = "user",
        execution_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Submit feedback for a service execution."""
        try:
            # Validate rating
            if rating is not None and not (1.0 <= rating <= 5.0):
                raise ValueError("Rating must be between 1.0 and 5.0")
            
            # Create feedback entry
            self.feedback_counter += 1
            feedback_id = f"feedback_{self.feedback_counter}_{datetime.now().timestamp()}"
            
            feedback = ServiceFeedback(
                feedback_id=feedback_id,
                service_execution_id=service_execution_id,
                agent_id=agent_id,
                service_type=service_type,
                feedback_type=feedback_type,
                rating=rating,
                comment=comment,
                quality_ratings=quality_ratings or {},
                provided_by=provided_by,
                execution_context=execution_context or {}
            )
            
            # Analyze sentiment if comment provided
            if comment and self.config["auto_sentiment_analysis"]:
                feedback.sentiment = self._analyze_sentiment(comment)
            
            # Store feedback
            self.feedback_entries[feedback_id] = feedback
            
            # Queue for processing
            await self.feedback_queue.put(feedback)
            
            # Update statistics
            self.stats["total_feedback"] += 1
            self.stats["feedback_by_type"][feedback_type.value] += 1
            
            if feedback.sentiment:
                self.stats["feedback_by_sentiment"][feedback.sentiment.value] += 1
            
            if rating:
                # Update average rating
                if self.stats["average_rating"] == 0:
                    self.stats["average_rating"] = rating
                else:
                    total_feedback = self.stats["total_feedback"]
                    self.stats["average_rating"] = (
                        (self.stats["average_rating"] * (total_feedback - 1) + rating) / 
                        total_feedback
                    )
            
            log_agent_event(
                agent_id,
                "feedback_submitted",
                {
                    "feedback_id": feedback_id,
                    "feedback_type": feedback_type.value,
                    "rating": rating,
                    "sentiment": feedback.sentiment.value if feedback.sentiment else None
                }
            )
            
            self.logger.info(f"Feedback submitted: {feedback_id} for agent {agent_id}")
            
            return feedback_id
            
        except Exception as e:
            self.logger.error(f"Failed to submit feedback: {e}")
            return ""
    
    async def get_quality_score(self, agent_id: str) -> Optional[QualityScore]:
        """Get the current quality score for an agent."""
        try:
            return self.quality_scores.get(agent_id)
        except Exception as e:
            self.logger.error(f"Failed to get quality score: {e}")
            return None
    
    async def get_agent_feedback(
        self,
        agent_id: str,
        limit: int = 50,
        feedback_type: Optional[FeedbackType] = None,
        min_rating: Optional[float] = None
    ) -> List[ServiceFeedback]:
        """Get feedback for a specific agent."""
        try:
            agent_feedback = [
                feedback for feedback in self.feedback_entries.values()
                if feedback.agent_id == agent_id
            ]
            
            # Apply filters
            if feedback_type:
                agent_feedback = [fb for fb in agent_feedback if fb.feedback_type == feedback_type]
            
            if min_rating:
                agent_feedback = [fb for fb in agent_feedback if fb.rating and fb.rating >= min_rating]
            
            # Sort by creation date (most recent first)
            agent_feedback.sort(key=lambda fb: fb.created_at, reverse=True)
            
            return agent_feedback[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to get agent feedback: {e}")
            return []
    
    async def get_service_recommendations(self, agent_id: str) -> List[ServiceRecommendation]:
        """Get improvement recommendations for an agent."""
        try:
            return self.recommendations.get(agent_id, [])
        except Exception as e:
            self.logger.error(f"Failed to get service recommendations: {e}")
            return []
    
    async def implement_recommendation(
        self,
        recommendation_id: str,
        implementation_notes: str = ""
    ) -> bool:
        """Mark a recommendation as implemented."""
        try:
            # Find the recommendation
            for agent_recommendations in self.recommendations.values():
                for recommendation in agent_recommendations:
                    if recommendation.recommendation_id == recommendation_id:
                        recommendation.implemented = True
                        recommendation.implementation_date = datetime.now()
                        
                        self.stats["improvement_actions_taken"] += 1
                        
                        log_agent_event(
                            recommendation.agent_id,
                            "recommendation_implemented",
                            {
                                "recommendation_id": recommendation_id,
                                "title": recommendation.title,
                                "notes": implementation_notes
                            }
                        )
                        
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to implement recommendation: {e}")
            return False
    
    async def calculate_quality_score(self, agent_id: str) -> Optional[QualityScore]:
        """Calculate comprehensive quality score for an agent."""
        try:
            # Get agent feedback
            agent_feedback = await self.get_agent_feedback(agent_id, limit=1000)
            
            if len(agent_feedback) < self.config["min_feedback_for_score"]:
                return None
            
            # Calculate overall metrics
            ratings = [fb.rating for fb in agent_feedback if fb.rating]
            average_rating = statistics.mean(ratings) if ratings else 0.0
            
            # Calculate quality metric scores
            metric_scores = {}
            for metric in QualityMetric:
                metric_ratings = []
                for feedback in agent_feedback:
                    if metric in feedback.quality_ratings:
                        metric_ratings.append(feedback.quality_ratings[metric])
                
                if metric_ratings:
                    metric_scores[metric] = statistics.mean(metric_ratings)
                else:
                    metric_scores[metric] = average_rating / 5.0  # Normalize to 0-1
            
            # Calculate weighted overall quality score
            overall_quality = sum(
                metric_scores[metric] * self.config["quality_score_weights"][metric]
                for metric in QualityMetric
            )
            
            # Calculate sentiment-based scores
            positive_feedback = len([
                fb for fb in agent_feedback 
                if fb.sentiment in [FeedbackSentiment.POSITIVE, FeedbackSentiment.VERY_POSITIVE]
            ])
            positive_feedback_ratio = positive_feedback / len(agent_feedback)
            
            # Calculate trend
            recent_feedback = [fb for fb in agent_feedback if 
                             (datetime.now() - fb.created_at).days <= 7]
            older_feedback = [fb for fb in agent_feedback if 
                            7 < (datetime.now() - fb.created_at).days <= 30]
            
            trend_direction = "stable"
            recent_feedback_trend = 0.0
            
            if recent_feedback and older_feedback:
                recent_avg = statistics.mean([fb.rating for fb in recent_feedback if fb.rating])
                older_avg = statistics.mean([fb.rating for fb in older_feedback if fb.rating])
                recent_feedback_trend = (recent_avg - older_avg) / older_avg
                
                if recent_feedback_trend > 0.1:
                    trend_direction = "improving"
                elif recent_feedback_trend < -0.1:
                    trend_direction = "declining"
            
            # Create quality score
            self.score_counter += 1
            score_id = f"score_{self.score_counter}_{datetime.now().timestamp()}"
            
            quality_score = QualityScore(
                score_id=score_id,
                agent_id=agent_id,
                service_type="all",  # Could be service-specific
                overall_quality=overall_quality,
                trend_direction=trend_direction,
                metric_scores=metric_scores,
                average_rating=average_rating,
                total_feedback_count=len(agent_feedback),
                positive_feedback_ratio=positive_feedback_ratio,
                recent_feedback_trend=recent_feedback_trend,
                confidence_level=min(1.0, len(agent_feedback) / 50.0)  # More feedback = higher confidence
            )
            
            # Store quality score
            self.quality_scores[agent_id] = quality_score
            self.stats["quality_scores_calculated"] += 1
            
            log_agent_event(
                agent_id,
                "quality_score_calculated",
                {
                    "score_id": score_id,
                    "overall_quality": overall_quality,
                    "trend_direction": trend_direction,
                    "feedback_count": len(agent_feedback)
                }
            )
            
            return quality_score
            
        except Exception as e:
            self.logger.error(f"Failed to calculate quality score: {e}")
            return None
    
    async def generate_recommendations(self, agent_id: str) -> List[ServiceRecommendation]:
        """Generate improvement recommendations for an agent."""
        try:
            quality_score = await self.get_quality_score(agent_id)
            if not quality_score:
                return []
            
            agent_feedback = await self.get_agent_feedback(agent_id, limit=100)
            recommendations = []
            
            # Analyze quality metrics for improvement opportunities
            for metric, score in quality_score.metric_scores.items():
                if score < 0.7:  # Below good threshold
                    recommendation = await self._generate_metric_recommendation(
                        agent_id, metric, score, agent_feedback
                    )
                    if recommendation:
                        recommendations.append(recommendation)
            
            # Analyze feedback patterns
            pattern_recommendations = await self._generate_pattern_recommendations(
                agent_id, agent_feedback
            )
            recommendations.extend(pattern_recommendations)
            
            # Analyze trend-based recommendations
            if quality_score.trend_direction == "declining":
                trend_recommendation = await self._generate_trend_recommendation(
                    agent_id, quality_score, agent_feedback
                )
                if trend_recommendation:
                    recommendations.append(trend_recommendation)
            
            # Sort by priority
            recommendations.sort(key=lambda r: r.priority_score, reverse=True)
            
            # Store recommendations
            self.recommendations[agent_id] = recommendations
            self.stats["recommendations_generated"] += len(recommendations)
            
            log_agent_event(
                agent_id,
                "recommendations_generated",
                {
                    "recommendation_count": len(recommendations),
                    "top_priority": recommendations[0].priority_score if recommendations else 0
                }
            )
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}")
            return []
    
    def _analyze_sentiment(self, comment: str) -> FeedbackSentiment:
        """Analyze sentiment of feedback comment."""
        try:
            comment_lower = comment.lower()
            
            # Count sentiment keywords
            sentiment_scores = {}
            for sentiment, keywords in self.config["sentiment_keywords"].items():
                score = sum(1 for keyword in keywords if keyword in comment_lower)
                sentiment_scores[sentiment] = score
            
            # Return sentiment with highest score
            if sentiment_scores:
                max_sentiment = max(sentiment_scores.items(), key=lambda x: x[1])
                if max_sentiment[1] > 0:
                    return max_sentiment[0]
            
            return FeedbackSentiment.NEUTRAL
            
        except Exception as e:
            self.logger.error(f"Failed to analyze sentiment: {e}")
            return FeedbackSentiment.NEUTRAL
    
    async def _generate_metric_recommendation(
        self,
        agent_id: str,
        metric: QualityMetric,
        score: float,
        feedback: List[ServiceFeedback]
    ) -> Optional[ServiceRecommendation]:
        """Generate recommendation for improving a specific quality metric."""
        try:
            # Get feedback related to this metric
            relevant_feedback = [
                fb for fb in feedback 
                if metric in fb.quality_ratings and fb.quality_ratings[metric] < 0.7
            ]
            
            if not relevant_feedback:
                return None
            
            # Generate recommendation based on metric type
            recommendations_map = {
                QualityMetric.ACCURACY: {
                    "title": "Improve Response Accuracy",
                    "description": "Focus on providing more precise and correct information. Consider additional validation steps.",
                    "category": "accuracy"
                },
                QualityMetric.COMPLETENESS: {
                    "title": "Enhance Response Completeness",
                    "description": "Ensure all aspects of requests are addressed. Add comprehensive coverage checks.",
                    "category": "completeness"
                },
                QualityMetric.TIMELINESS: {
                    "title": "Optimize Response Time",
                    "description": "Improve processing efficiency to deliver results faster. Consider parallel processing.",
                    "category": "performance"
                },
                QualityMetric.RELEVANCE: {
                    "title": "Increase Response Relevance",
                    "description": "Better understand user intent and provide more targeted responses.",
                    "category": "relevance"
                },
                QualityMetric.USABILITY: {
                    "title": "Enhance User Experience",
                    "description": "Improve the clarity and usability of responses. Make outputs more user-friendly.",
                    "category": "user_experience"
                },
                QualityMetric.RELIABILITY: {
                    "title": "Increase Service Reliability",
                    "description": "Reduce errors and improve consistency. Implement better error handling.",
                    "category": "reliability"
                }
            }
            
            rec_template = recommendations_map.get(metric)
            if not rec_template:
                return None
            
            self.recommendation_counter += 1
            recommendation_id = f"rec_{self.recommendation_counter}_{datetime.now().timestamp()}"
            
            recommendation = ServiceRecommendation(
                recommendation_id=recommendation_id,
                agent_id=agent_id,
                service_type="all",
                title=rec_template["title"],
                description=rec_template["description"],
                category=rec_template["category"],
                expected_improvement=0.8 - score,  # Expected improvement to reach good level
                implementation_effort="medium",
                priority_score=(0.8 - score) * 10,  # Higher priority for lower scores
                supporting_feedback=[fb.feedback_id for fb in relevant_feedback[:5]]
            )
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Failed to generate metric recommendation: {e}")
            return None
    
    async def _generate_pattern_recommendations(
        self,
        agent_id: str,
        feedback: List[ServiceFeedback]
    ) -> List[ServiceRecommendation]:
        """Generate recommendations based on feedback patterns."""
        try:
            recommendations = []
            
            # Analyze common complaint patterns
            negative_feedback = [
                fb for fb in feedback 
                if fb.sentiment in [FeedbackSentiment.NEGATIVE, FeedbackSentiment.VERY_NEGATIVE]
            ]
            
            if len(negative_feedback) > len(feedback) * 0.3:  # More than 30% negative
                self.recommendation_counter += 1
                recommendation_id = f"rec_{self.recommendation_counter}_{datetime.now().timestamp()}"
                
                recommendation = ServiceRecommendation(
                    recommendation_id=recommendation_id,
                    agent_id=agent_id,
                    service_type="all",
                    title="Address High Negative Feedback Rate",
                    description="Investigate and address the root causes of negative feedback. Consider user training or service redesign.",
                    category="user_satisfaction",
                    expected_improvement=0.3,
                    implementation_effort="high",
                    priority_score=8.0,
                    supporting_feedback=[fb.feedback_id for fb in negative_feedback[:10]]
                )
                
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate pattern recommendations: {e}")
            return []
    
    async def _generate_trend_recommendation(
        self,
        agent_id: str,
        quality_score: QualityScore,
        feedback: List[ServiceFeedback]
    ) -> Optional[ServiceRecommendation]:
        """Generate recommendation for declining quality trends."""
        try:
            self.recommendation_counter += 1
            recommendation_id = f"rec_{self.recommendation_counter}_{datetime.now().timestamp()}"
            
            recommendation = ServiceRecommendation(
                recommendation_id=recommendation_id,
                agent_id=agent_id,
                service_type="all",
                title="Address Declining Quality Trend",
                description="Quality metrics show a declining trend. Investigate recent changes and implement corrective measures.",
                category="quality_management",
                expected_improvement=abs(quality_score.recent_feedback_trend),
                implementation_effort="medium",
                priority_score=7.0,
                supporting_feedback=[fb.feedback_id for fb in feedback[:5]]
            )
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Failed to generate trend recommendation: {e}")
            return None
    
    async def _feedback_processing_loop(self) -> None:
        """Process feedback entries from the queue."""
        while True:
            try:
                feedback = await asyncio.wait_for(self.feedback_queue.get(), timeout=1.0)
                
                # Process feedback (mark as processed, trigger quality recalculation, etc.)
                feedback.processed = True
                feedback.processed_at = datetime.now()
                
                # Trigger quality score recalculation if significant feedback
                if feedback.rating and (feedback.rating <= 2.0 or feedback.rating >= 4.5):
                    asyncio.create_task(self.calculate_quality_score(feedback.agent_id))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error in feedback processing loop: {e}")
                await asyncio.sleep(1)
    
    async def _quality_calculation_loop(self) -> None:
        """Periodically recalculate quality scores."""
        while True:
            try:
                # Get all agents with feedback
                agents_with_feedback = set(fb.agent_id for fb in self.feedback_entries.values())
                
                for agent_id in agents_with_feedback:
                    await self.calculate_quality_score(agent_id)
                
                # Sleep for configured interval
                await asyncio.sleep(self.config["quality_calculation_interval_hours"] * 3600)
                
            except Exception as e:
                self.logger.error(f"Error in quality calculation loop: {e}")
                await asyncio.sleep(3600)
    
    async def _recommendation_generation_loop(self) -> None:
        """Periodically generate recommendations."""
        while True:
            try:
                # Generate recommendations for all agents with quality scores
                for agent_id in self.quality_scores.keys():
                    await self.generate_recommendations(agent_id)
                
                # Sleep for configured interval
                await asyncio.sleep(self.config["recommendation_generation_interval_hours"] * 3600)
                
            except Exception as e:
                self.logger.error(f"Error in recommendation generation loop: {e}")
                await asyncio.sleep(3600)
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old feedback and recommendations."""
        while True:
            try:
                cutoff_date = datetime.now() - timedelta(days=self.config["feedback_retention_days"])
                
                # Remove old feedback
                old_feedback_ids = [
                    fb_id for fb_id, fb in self.feedback_entries.items()
                    if fb.created_at < cutoff_date
                ]
                
                for fb_id in old_feedback_ids:
                    del self.feedback_entries[fb_id]
                
                if old_feedback_ids:
                    self.logger.info(f"Cleaned up {len(old_feedback_ids)} old feedback entries")
                
                # Sleep for 24 hours
                await asyncio.sleep(86400)
                
            except Exception as e:
                self.logger.error(f"Error in cleanup: {e}")
                await asyncio.sleep(86400)
    
    async def _process_remaining_feedback(self) -> None:
        """Process any remaining feedback in the queue during shutdown."""
        try:
            while not self.feedback_queue.empty():
                try:
                    feedback = self.feedback_queue.get_nowait()
                    feedback.processed = True
                    feedback.processed_at = datetime.now()
                except asyncio.QueueEmpty:
                    break
        except Exception as e:
            self.logger.error(f"Error processing remaining feedback: {e}")