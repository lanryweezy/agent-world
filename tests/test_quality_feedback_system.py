"""
Unit tests for the service quality and feedback system.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from autonomous_ai_ecosystem.services.quality_feedback_system import (
    ServiceQualityFeedbackSystem,
    ServiceFeedback,
    QualityScore,
    ServiceRecommendation,
    FeedbackType,
    FeedbackSentiment,
    QualityMetric
)


class TestServiceQualityFeedbackSystem:
    """Test cases for ServiceQualityFeedbackSystem."""
    
    @pytest.fixture
    async def quality_system(self):
        """Create a quality feedback system for testing."""
        system = ServiceQualityFeedbackSystem("test_quality_system")
        await system.initialize()
        yield system
        await system.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test quality system initialization."""
        system = ServiceQualityFeedbackSystem("test_quality_system")
        
        assert system.agent_id == "test_quality_system"
        assert system.feedback_entries == {}
        assert system.quality_scores == {}
        assert system.recommendations == {}
        assert len(system.config["quality_score_weights"]) == len(QualityMetric)
        
        await system.initialize()
        await system.shutdown()
    
    @pytest.mark.asyncio
    async def test_submit_feedback(self, quality_system):
        """Test feedback submission."""
        feedback_id = await quality_system.submit_feedback(
            service_execution_id="exec_123",
            agent_id="test_agent",
            service_type="research",
            feedback_type=FeedbackType.RATING,
            rating=4.5,
            comment="Great work, very helpful!",
            quality_ratings={
                QualityMetric.ACCURACY: 0.9,
                QualityMetric.COMPLETENESS: 0.8,
                QualityMetric.TIMELINESS: 0.7
            },
            provided_by="user_123"
        )
        
        # Verify feedback was submitted
        assert feedback_id != ""
        assert feedback_id in quality_system.feedback_entries
        
        feedback = quality_system.feedback_entries[feedback_id]
        assert feedback.service_execution_id == "exec_123"
        assert feedback.agent_id == "test_agent"
        assert feedback.service_type == "research"
        assert feedback.feedback_type == FeedbackType.RATING
        assert feedback.rating == 4.5
        assert feedback.comment == "Great work, very helpful!"
        assert feedback.quality_ratings[QualityMetric.ACCURACY] == 0.9
        assert feedback.provided_by == "user_123"
        assert feedback.sentiment == FeedbackSentiment.POSITIVE  # Auto-analyzed
        
        # Verify statistics updated
        assert quality_system.stats["total_feedback"] == 1
        assert quality_system.stats["feedback_by_type"][FeedbackType.RATING.value] == 1
        assert quality_system.stats["feedback_by_sentiment"][FeedbackSentiment.POSITIVE.value] == 1
        assert quality_system.stats["average_rating"] == 4.5
    
    @pytest.mark.asyncio
    async def test_submit_feedback_validation(self, quality_system):
        """Test feedback submission validation."""
        # Test invalid rating
        feedback_id = await quality_system.submit_feedback(
            service_execution_id="exec_123",
            agent_id="test_agent",
            service_type="research",
            feedback_type=FeedbackType.RATING,
            rating=6.0  # Invalid rating > 5.0
        )
        
        # Should return empty string on validation error
        assert feedback_id == ""
        assert len(quality_system.feedback_entries) == 0
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis(self, quality_system):
        """Test automatic sentiment analysis."""
        # Test positive sentiment
        feedback_id = await quality_system.submit_feedback(
            service_execution_id="exec_123",
            agent_id="test_agent",
            service_type="research",
            feedback_type=FeedbackType.COMMENT,
            comment="This is excellent work, outstanding results!"
        )
        
        feedback = quality_system.feedback_entries[feedback_id]
        assert feedback.sentiment == FeedbackSentiment.VERY_POSITIVE
        
        # Test negative sentiment
        feedback_id = await quality_system.submit_feedback(
            service_execution_id="exec_124",
            agent_id="test_agent",
            service_type="research",
            feedback_type=FeedbackType.COMMENT,
            comment="This is terrible work, very disappointing."
        )
        
        feedback = quality_system.feedback_entries[feedback_id]
        assert feedback.sentiment == FeedbackSentiment.VERY_NEGATIVE
        
        # Test neutral sentiment
        feedback_id = await quality_system.submit_feedback(
            service_execution_id="exec_125",
            agent_id="test_agent",
            service_type="research",
            feedback_type=FeedbackType.COMMENT,
            comment="This is okay, nothing special."
        )
        
        feedback = quality_system.feedback_entries[feedback_id]
        assert feedback.sentiment == FeedbackSentiment.NEUTRAL
    
    @pytest.mark.asyncio
    async def test_get_agent_feedback(self, quality_system):
        """Test retrieving feedback for a specific agent."""
        # Submit multiple feedback entries
        await quality_system.submit_feedback(
            service_execution_id="exec_1",
            agent_id="agent_1",
            service_type="research",
            feedback_type=FeedbackType.RATING,
            rating=4.0
        )
        
        await quality_system.submit_feedback(
            service_execution_id="exec_2",
            agent_id="agent_1",
            service_type="coding",
            feedback_type=FeedbackType.COMMENT,
            rating=3.5
        )
        
        await quality_system.submit_feedback(
            service_execution_id="exec_3",
            agent_id="agent_2",
            service_type="research",
            feedback_type=FeedbackType.RATING,
            rating=5.0
        )
        
        # Get feedback for agent_1
        agent_1_feedback = await quality_system.get_agent_feedback("agent_1")
        
        assert len(agent_1_feedback) == 2
        assert all(fb.agent_id == "agent_1" for fb in agent_1_feedback)
        
        # Test filtering by feedback type
        rating_feedback = await quality_system.get_agent_feedback(
            "agent_1", 
            feedback_type=FeedbackType.RATING
        )
        
        assert len(rating_feedback) == 1
        assert rating_feedback[0].feedback_type == FeedbackType.RATING
        
        # Test filtering by minimum rating
        high_rating_feedback = await quality_system.get_agent_feedback(
            "agent_1",
            min_rating=4.0
        )
        
        assert len(high_rating_feedback) == 1
        assert high_rating_feedback[0].rating == 4.0
    
    @pytest.mark.asyncio
    async def test_calculate_quality_score(self, quality_system):
        """Test quality score calculation."""
        agent_id = "test_agent"
        
        # Submit multiple feedback entries with different ratings and quality metrics
        feedback_data = [
            (4.5, {QualityMetric.ACCURACY: 0.9, QualityMetric.COMPLETENESS: 0.8}),
            (4.0, {QualityMetric.ACCURACY: 0.8, QualityMetric.COMPLETENESS: 0.9}),
            (3.5, {QualityMetric.ACCURACY: 0.7, QualityMetric.COMPLETENESS: 0.7}),
            (4.2, {QualityMetric.ACCURACY: 0.85, QualityMetric.COMPLETENESS: 0.75}),
            (3.8, {QualityMetric.ACCURACY: 0.75, QualityMetric.COMPLETENESS: 0.8})
        ]
        
        for i, (rating, quality_ratings) in enumerate(feedback_data):
            await quality_system.submit_feedback(
                service_execution_id=f"exec_{i}",
                agent_id=agent_id,
                service_type="research",
                feedback_type=FeedbackType.RATING,
                rating=rating,
                quality_ratings=quality_ratings
            )
        
        # Calculate quality score
        quality_score = await quality_system.calculate_quality_score(agent_id)
        
        assert quality_score is not None
        assert quality_score.agent_id == agent_id
        assert 0 <= quality_score.overall_quality <= 1
        assert quality_score.total_feedback_count == 5
        assert quality_score.average_rating == sum(rating for rating, _ in feedback_data) / 5
        assert QualityMetric.ACCURACY in quality_score.metric_scores
        assert QualityMetric.COMPLETENESS in quality_score.metric_scores
        assert quality_score.confidence_level > 0
        
        # Verify score was stored
        stored_score = await quality_system.get_quality_score(agent_id)
        assert stored_score is not None
        assert stored_score.score_id == quality_score.score_id
    
    @pytest.mark.asyncio
    async def test_calculate_quality_score_insufficient_feedback(self, quality_system):
        """Test quality score calculation with insufficient feedback."""
        agent_id = "test_agent"
        
        # Submit only 2 feedback entries (below minimum threshold of 5)
        await quality_system.submit_feedback(
            service_execution_id="exec_1",
            agent_id=agent_id,
            service_type="research",
            feedback_type=FeedbackType.RATING,
            rating=4.0
        )
        
        await quality_system.submit_feedback(
            service_execution_id="exec_2",
            agent_id=agent_id,
            service_type="research",
            feedback_type=FeedbackType.RATING,
            rating=3.5
        )
        
        # Should return None due to insufficient feedback
        quality_score = await quality_system.calculate_quality_score(agent_id)
        assert quality_score is None
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(self, quality_system):
        """Test recommendation generation."""
        agent_id = "test_agent"
        
        # Submit feedback with low quality scores to trigger recommendations
        feedback_data = [
            (2.0, {QualityMetric.ACCURACY: 0.4, QualityMetric.COMPLETENESS: 0.3}),
            (2.5, {QualityMetric.ACCURACY: 0.5, QualityMetric.COMPLETENESS: 0.4}),
            (2.2, {QualityMetric.ACCURACY: 0.45, QualityMetric.COMPLETENESS: 0.35}),
            (1.8, {QualityMetric.ACCURACY: 0.3, QualityMetric.COMPLETENESS: 0.25}),
            (2.3, {QualityMetric.ACCURACY: 0.4, QualityMetric.COMPLETENESS: 0.3})
        ]
        
        for i, (rating, quality_ratings) in enumerate(feedback_data):
            await quality_system.submit_feedback(
                service_execution_id=f"exec_{i}",
                agent_id=agent_id,
                service_type="research",
                feedback_type=FeedbackType.RATING,
                rating=rating,
                quality_ratings=quality_ratings,
                comment="Poor quality work, needs improvement"
            )
        
        # Calculate quality score first
        quality_score = await quality_system.calculate_quality_score(agent_id)
        assert quality_score is not None
        
        # Generate recommendations
        recommendations = await quality_system.generate_recommendations(agent_id)
        
        assert len(recommendations) > 0
        
        # Should have recommendations for low-scoring metrics
        accuracy_rec = next((r for r in recommendations if "Accuracy" in r.title), None)
        completeness_rec = next((r for r in recommendations if "Completeness" in r.title), None)
        
        assert accuracy_rec is not None
        assert completeness_rec is not None
        
        # Verify recommendation details
        assert accuracy_rec.agent_id == agent_id
        assert accuracy_rec.expected_improvement > 0
        assert accuracy_rec.priority_score > 0
        assert len(accuracy_rec.supporting_feedback) > 0
        
        # Verify recommendations were stored
        stored_recommendations = await quality_system.get_service_recommendations(agent_id)
        assert len(stored_recommendations) == len(recommendations)
    
    @pytest.mark.asyncio
    async def test_implement_recommendation(self, quality_system):
        """Test recommendation implementation."""
        agent_id = "test_agent"
        
        # Create a test recommendation
        recommendation = ServiceRecommendation(
            recommendation_id="test_rec_123",
            agent_id=agent_id,
            service_type="research",
            title="Test Recommendation",
            description="Test recommendation description",
            category="test"
        )
        
        quality_system.recommendations[agent_id] = [recommendation]
        
        # Implement the recommendation
        result = await quality_system.implement_recommendation(
            "test_rec_123",
            "Implemented successfully"
        )
        
        assert result is True
        assert recommendation.implemented is True
        assert recommendation.implementation_date is not None
        assert quality_system.stats["improvement_actions_taken"] == 1
        
        # Test implementing non-existent recommendation
        result = await quality_system.implement_recommendation("non_existent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_quality_score_trend_calculation(self, quality_system):
        """Test quality score trend calculation."""
        agent_id = "test_agent"
        
        # Submit older feedback (30 days ago)
        old_date = datetime.now() - timedelta(days=25)
        for i in range(3):
            feedback = ServiceFeedback(
                feedback_id=f"old_feedback_{i}",
                service_execution_id=f"old_exec_{i}",
                agent_id=agent_id,
                service_type="research",
                feedback_type=FeedbackType.RATING,
                rating=4.0,
                created_at=old_date
            )
            quality_system.feedback_entries[feedback.feedback_id] = feedback
        
        # Submit recent feedback (within 7 days) with lower ratings
        for i in range(3):
            await quality_system.submit_feedback(
                service_execution_id=f"recent_exec_{i}",
                agent_id=agent_id,
                service_type="research",
                feedback_type=FeedbackType.RATING,
                rating=2.0
            )
        
        # Calculate quality score
        quality_score = await quality_system.calculate_quality_score(agent_id)
        
        assert quality_score is not None
        assert quality_score.trend_direction == "declining"
        assert quality_score.recent_feedback_trend < 0
    
    def test_service_feedback_methods(self):
        """Test ServiceFeedback class methods."""
        feedback = ServiceFeedback(
            feedback_id="test_feedback",
            service_execution_id="exec_123",
            agent_id="test_agent",
            service_type="research",
            feedback_type=FeedbackType.RATING,
            rating=4.5,
            comment="Great work!",
            quality_ratings={QualityMetric.ACCURACY: 0.9},
            sentiment=FeedbackSentiment.POSITIVE
        )
        
        # Test basic properties
        assert feedback.feedback_id == "test_feedback"
        assert feedback.rating == 4.5
        assert feedback.sentiment == FeedbackSentiment.POSITIVE
        assert feedback.processed is False
        assert feedback.action_taken is False
    
    def test_quality_score_methods(self):
        """Test QualityScore class methods."""
        quality_score = QualityScore(
            score_id="test_score",
            agent_id="test_agent",
            service_type="research",
            overall_quality=0.8,
            trend_direction="improving",
            metric_scores={
                QualityMetric.ACCURACY: 0.9,
                QualityMetric.COMPLETENESS: 0.7
            },
            average_rating=4.2,
            total_feedback_count=10,
            positive_feedback_ratio=0.8,
            confidence_level=0.6
        )
        
        # Test basic properties
        assert quality_score.overall_quality == 0.8
        assert quality_score.trend_direction == "improving"
        assert quality_score.metric_scores[QualityMetric.ACCURACY] == 0.9
        assert quality_score.confidence_level == 0.6
    
    def test_service_recommendation_methods(self):
        """Test ServiceRecommendation class methods."""
        recommendation = ServiceRecommendation(
            recommendation_id="test_rec",
            agent_id="test_agent",
            service_type="research",
            title="Improve Accuracy",
            description="Focus on providing more accurate results",
            category="accuracy",
            expected_improvement=0.2,
            implementation_effort="medium",
            priority_score=7.5,
            supporting_feedback=["fb1", "fb2"]
        )
        
        # Test basic properties
        assert recommendation.title == "Improve Accuracy"
        assert recommendation.expected_improvement == 0.2
        assert recommendation.priority_score == 7.5
        assert recommendation.implemented is False
        assert len(recommendation.supporting_feedback) == 2
    
    @pytest.mark.asyncio
    async def test_error_handling(self, quality_system):
        """Test error handling in various methods."""
        # Test submitting feedback with error
        with patch.object(quality_system, 'feedback_entries', side_effect=Exception("Storage error")):
            feedback_id = await quality_system.submit_feedback(
                service_execution_id="exec_123",
                agent_id="test_agent",
                service_type="research",
                feedback_type=FeedbackType.RATING,
                rating=4.0
            )
            assert feedback_id == ""
        
        # Test calculating quality score with error
        with patch.object(quality_system, 'get_agent_feedback', side_effect=Exception("Retrieval error")):
            quality_score = await quality_system.calculate_quality_score("test_agent")
            assert quality_score is None
        
        # Test generating recommendations with error
        with patch.object(quality_system, 'get_quality_score', side_effect=Exception("Score error")):
            recommendations = await quality_system.generate_recommendations("test_agent")
            assert recommendations == []


if __name__ == "__main__":
    pytest.main([__file__])