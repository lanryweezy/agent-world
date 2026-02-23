"""
Unit tests for the service capability registry.
"""

import pytest
from unittest.mock import patch

from autonomous_ai_ecosystem.services.capability_registry import (
    ServiceCapabilityRegistry,
    ServiceCapability,
    ServiceMatch,
    ServiceType,
    ExpertiseLevel,
    CapabilityStatus
)


class TestServiceCapabilityRegistry:
    """Test cases for ServiceCapabilityRegistry."""
    
    @pytest.fixture
    async def registry(self):
        """Create a capability registry for testing."""
        registry = ServiceCapabilityRegistry("test_registry")
        await registry.initialize()
        yield registry
        await registry.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test registry initialization."""
        registry = ServiceCapabilityRegistry("test_registry")
        
        assert registry.agent_id == "test_registry"
        assert registry.capabilities == {}
        assert registry.agent_capabilities == {}
        assert registry.service_requests == {}
        assert len(registry.capabilities_by_service) == len(ServiceType)
        assert len(registry.capabilities_by_expertise) == len(ExpertiseLevel)
        
        await registry.initialize()
        await registry.shutdown()
    
    @pytest.mark.asyncio
    async def test_register_capability(self, registry):
        """Test capability registration."""
        capability_id = await registry.register_capability(
            agent_id="test_agent",
            service_type=ServiceType.RESEARCH,
            name="Web Research",
            description="Comprehensive web research service",
            expertise_level=ExpertiseLevel.INTERMEDIATE,
            specializations=["academic", "technical"],
            max_concurrent_tasks=5
        )
        
        # Verify capability was registered
        assert capability_id != ""
        assert capability_id in registry.capabilities
        
        capability = registry.capabilities[capability_id]
        assert capability.agent_id == "test_agent"
        assert capability.service_type == ServiceType.RESEARCH
        assert capability.name == "Web Research"
        assert capability.expertise_level == ExpertiseLevel.INTERMEDIATE
        assert capability.specializations == ["academic", "technical"]
        assert capability.max_concurrent_tasks == 5
        assert capability.status == CapabilityStatus.ACTIVE
        
        # Verify indexes were updated
        assert capability_id in registry.capabilities_by_service[ServiceType.RESEARCH]
        assert capability_id in registry.capabilities_by_expertise[ExpertiseLevel.INTERMEDIATE]
        assert "test_agent" in registry.agent_capabilities
        assert capability_id in registry.agent_capabilities["test_agent"]
        
        # Verify statistics were updated
        assert registry.stats["total_capabilities"] == 1
        assert registry.stats["active_capabilities"] == 1
        assert registry.stats["capabilities_by_service"][ServiceType.RESEARCH.value] == 1
        assert registry.stats["capabilities_by_expertise"][ExpertiseLevel.INTERMEDIATE.value] == 1
        assert registry.stats["agent_count"] == 1
    
    @pytest.mark.asyncio
    async def test_update_capability(self, registry):
        """Test capability updates."""
        # Register a capability
        capability_id = await registry.register_capability(
            agent_id="test_agent",
            service_type=ServiceType.CODING,
            name="Python Development",
            description="Python coding service",
            expertise_level=ExpertiseLevel.BEGINNER
        )
        
        # Update the capability
        result = await registry.update_capability(
            capability_id,
            expertise_level=ExpertiseLevel.INTERMEDIATE,
            specializations=["web_development", "data_science"],
            max_concurrent_tasks=3
        )
        
        assert result is True
        
        capability = registry.capabilities[capability_id]
        assert capability.expertise_level == ExpertiseLevel.INTERMEDIATE
        assert capability.specializations == ["web_development", "data_science"]
        assert capability.max_concurrent_tasks == 3
        
        # Verify indexes were updated
        assert capability_id not in registry.capabilities_by_expertise[ExpertiseLevel.BEGINNER]
        assert capability_id in registry.capabilities_by_expertise[ExpertiseLevel.INTERMEDIATE]
        
        # Test updating non-existent capability
        result = await registry.update_capability("non_existent", name="New Name")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_deactivate_capability(self, registry):
        """Test capability deactivation."""
        # Register a capability
        capability_id = await registry.register_capability(
            agent_id="test_agent",
            service_type=ServiceType.DATA_ANALYSIS,
            name="Data Analysis",
            description="Statistical data analysis"
        )
        
        # Deactivate the capability
        result = await registry.deactivate_capability(capability_id)
        
        assert result is True
        
        capability = registry.capabilities[capability_id]
        assert capability.status == CapabilityStatus.INACTIVE
        assert registry.stats["active_capabilities"] == 0
        
        # Test deactivating non-existent capability
        result = await registry.deactivate_capability("non_existent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_find_service_providers(self, registry):
        """Test finding service providers."""
        # Register multiple capabilities
        cap1_id = await registry.register_capability(
            agent_id="agent1",
            service_type=ServiceType.RESEARCH,
            name="Basic Research",
            description="Basic research service",
            expertise_level=ExpertiseLevel.BEGINNER,
            specializations=["web"]
        )
        
        cap2_id = await registry.register_capability(
            agent_id="agent2",
            service_type=ServiceType.RESEARCH,
            name="Advanced Research",
            description="Advanced research service",
            expertise_level=ExpertiseLevel.EXPERT,
            specializations=["academic", "technical"]
        )
        
        await registry.register_capability(
            agent_id="agent3",
            service_type=ServiceType.CODING,
            name="Coding Service",
            description="Coding service",
            expertise_level=ExpertiseLevel.INTERMEDIATE
        )
        
        # Update performance metrics for better testing
        await registry.update_capability_performance(cap1_id, True, 1800, 0.6, 3.5)
        await registry.update_capability_performance(cap2_id, True, 3600, 0.9, 4.8)
        
        # Find research providers
        providers = await registry.find_service_providers(
            service_type=ServiceType.RESEARCH,
            required_expertise=ExpertiseLevel.INTERMEDIATE,
            max_results=10
        )
        
        # Should find the expert (agent2) but not the beginner (agent1)
        assert len(providers) == 1
        assert providers[0].agent_id == "agent2"
        assert providers[0].expertise_level == ExpertiseLevel.EXPERT
        
        # Find with specialization requirement
        providers = await registry.find_service_providers(
            service_type=ServiceType.RESEARCH,
            required_expertise=ExpertiseLevel.BEGINNER,
            required_specializations=["academic"],
            max_results=10
        )
        
        # Should find agent2 who has academic specialization
        assert len(providers) == 1
        assert providers[0].agent_id == "agent2"
        
        # Find with exclusion
        providers = await registry.find_service_providers(
            service_type=ServiceType.RESEARCH,
            required_expertise=ExpertiseLevel.BEGINNER,
            exclude_agents=["agent2"],
            max_results=10
        )
        
        # Should find agent1 (beginner level meets requirement)
        assert len(providers) == 1
        assert providers[0].agent_id == "agent1"
    
    @pytest.mark.asyncio
    async def test_match_service_request(self, registry):
        """Test service request matching."""
        # Register capabilities
        cap1_id = await registry.register_capability(
            agent_id="agent1",
            service_type=ServiceType.RESEARCH,
            name="Research Service",
            description="Research service",
            expertise_level=ExpertiseLevel.INTERMEDIATE,
            specializations=["web", "academic"]
        )
        
        cap2_id = await registry.register_capability(
            agent_id="agent2",
            service_type=ServiceType.RESEARCH,
            name="Expert Research",
            description="Expert research service",
            expertise_level=ExpertiseLevel.EXPERT,
            specializations=["academic", "technical"]
        )
        
        # Update performance metrics
        await registry.update_capability_performance(cap1_id, True, 1800, 0.7, 4.0)
        await registry.update_capability_performance(cap2_id, True, 2400, 0.9, 4.5)
        
        # Match a service request
        matches = await registry.match_service_request(
            service_type=ServiceType.RESEARCH,
            description="Need comprehensive academic research on AI ethics",
            required_expertise=ExpertiseLevel.INTERMEDIATE,
            required_specializations=["academic"],
            min_quality_score=0.6,
            priority=8
        )
        
        # Should find both agents, with expert ranked higher
        assert len(matches) == 2
        assert matches[0].agent_id == "agent2"  # Expert should be ranked first
        assert matches[1].agent_id == "agent1"
        
        # Verify match details
        top_match = matches[0]
        assert top_match.service_type == ServiceType.RESEARCH
        assert top_match.expertise_match is True
        assert "academic" in top_match.matching_specializations
        assert top_match.compatibility_score > 0
        assert top_match.confidence_score > 0
        
        # Test with exclusions
        matches = await registry.match_service_request(
            service_type=ServiceType.RESEARCH,
            description="Research request",
            excluded_agents=["agent2"]
        )
        
        assert len(matches) == 1
        assert matches[0].agent_id == "agent1"
    
    @pytest.mark.asyncio
    async def test_update_capability_performance(self, registry):
        """Test updating capability performance metrics."""
        # Register a capability
        capability_id = await registry.register_capability(
            agent_id="test_agent",
            service_type=ServiceType.CODING,
            name="Coding Service",
            description="Coding service"
        )
        
        # Update performance multiple times
        await registry.update_capability_performance(capability_id, True, 1800, 0.8, 4.2)
        await registry.update_capability_performance(capability_id, True, 2400, 0.7, 3.8)
        await registry.update_capability_performance(capability_id, False, 3600, 0.3, 2.0)
        
        capability = registry.capabilities[capability_id]
        
        # Verify metrics were updated
        assert capability.total_requests == 3
        assert capability.completed_requests == 2
        assert capability.failed_requests == 1
        assert capability.success_rate == 2/3
        assert capability.average_completion_time == (1800 + 2400 + 3600) / 3
        assert capability.quality_score == (0.8 + 0.7 + 0.3) / 3
        assert capability.average_rating == (4.2 + 3.8 + 2.0) / 3
        assert capability.last_used is not None
        
        # Test updating non-existent capability
        result = await registry.update_capability_performance("non_existent", True, 1000, 0.5)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_agent_capabilities(self, registry):
        """Test getting capabilities for a specific agent."""
        # Register multiple capabilities for the same agent
        cap1_id = await registry.register_capability(
            agent_id="multi_agent",
            service_type=ServiceType.RESEARCH,
            name="Research Service",
            description="Research service"
        )
        
        cap2_id = await registry.register_capability(
            agent_id="multi_agent",
            service_type=ServiceType.CODING,
            name="Coding Service",
            description="Coding service"
        )
        
        cap3_id = await registry.register_capability(
            agent_id="other_agent",
            service_type=ServiceType.DATA_ANALYSIS,
            name="Analysis Service",
            description="Analysis service"
        )
        
        # Get capabilities for multi_agent
        capabilities = await registry.get_agent_capabilities("multi_agent")
        
        assert len(capabilities) == 2
        capability_ids = [cap.capability_id for cap in capabilities]
        assert cap1_id in capability_ids
        assert cap2_id in capability_ids
        assert cap3_id not in capability_ids
        
        # Test non-existent agent
        capabilities = await registry.get_agent_capabilities("non_existent")
        assert len(capabilities) == 0
    
    @pytest.mark.asyncio
    async def test_get_capability_statistics(self, registry):
        """Test getting capability statistics."""
        # Register and update a capability
        capability_id = await registry.register_capability(
            agent_id="test_agent",
            service_type=ServiceType.RESEARCH,
            name="Research Service",
            description="Research service",
            expertise_level=ExpertiseLevel.INTERMEDIATE,
            specializations=["web", "academic"]
        )
        
        await registry.update_capability_performance(capability_id, True, 1800, 0.8, 4.0)
        
        # Get statistics
        stats = await registry.get_capability_statistics(capability_id)
        
        assert stats["capability_id"] == capability_id
        assert stats["agent_id"] == "test_agent"
        assert stats["service_type"] == ServiceType.RESEARCH.value
        assert stats["expertise_level"] == ExpertiseLevel.INTERMEDIATE.value
        assert stats["overall_score"] > 0
        assert stats["success_rate"] == 1.0
        assert stats["total_requests"] == 1
        assert stats["availability"] is True
        assert stats["specializations"] == ["web", "academic"]
        
        # Test non-existent capability
        stats = await registry.get_capability_statistics("non_existent")
        assert stats == {}
    
    @pytest.mark.asyncio
    async def test_get_service_statistics(self, registry):
        """Test getting service type statistics."""
        # Register multiple capabilities for the same service type
        cap1_id = await registry.register_capability(
            agent_id="agent1",
            service_type=ServiceType.RESEARCH,
            name="Research Service 1",
            description="Research service 1",
            expertise_level=ExpertiseLevel.BEGINNER
        )
        
        cap2_id = await registry.register_capability(
            agent_id="agent2",
            service_type=ServiceType.RESEARCH,
            name="Research Service 2",
            description="Research service 2",
            expertise_level=ExpertiseLevel.EXPERT
        )
        
        # Update performance
        await registry.update_capability_performance(cap1_id, True, 1800, 0.6, 3.5)
        await registry.update_capability_performance(cap2_id, True, 2400, 0.9, 4.5)
        
        # Get service statistics
        stats = await registry.get_service_statistics(ServiceType.RESEARCH)
        
        assert stats["service_type"] == ServiceType.RESEARCH.value
        assert stats["total_providers"] == 2
        assert stats["active_providers"] == 2
        assert stats["average_quality"] == (0.6 + 0.9) / 2
        assert stats["average_success_rate"] == 1.0
        assert stats["total_requests"] == 2
        assert len(stats["top_providers"]) == 2
        assert stats["expertise_distribution"][ExpertiseLevel.BEGINNER.value] == 1
        assert stats["expertise_distribution"][ExpertiseLevel.EXPERT.value] == 1
        
        # Test service type with no providers
        stats = await registry.get_service_statistics(ServiceType.AUTOMATION)
        assert stats["total_providers"] == 0
        assert stats["active_providers"] == 0
    
    def test_service_capability_methods(self):
        """Test ServiceCapability class methods."""
        capability = ServiceCapability(
            capability_id="test_cap",
            agent_id="test_agent",
            service_type=ServiceType.RESEARCH,
            name="Test Capability",
            description="Test capability",
            expertise_level=ExpertiseLevel.INTERMEDIATE,
            success_rate=0.8,
            quality_score=0.7,
            reliability_score=0.9,
            average_rating=4.2,
            max_concurrent_tasks=3,
            current_load=1
        )
        
        # Test overall score calculation
        overall_score = capability.calculate_overall_score()
        assert 0 <= overall_score <= 1
        assert overall_score > 0  # Should be positive with good metrics
        
        # Test availability check
        assert capability.is_available() is True
        
        capability.current_load = 3  # At capacity
        assert capability.is_available() is False
        
        capability.status = CapabilityStatus.INACTIVE
        capability.current_load = 0
        assert capability.is_available() is False
        
        # Test performance update
        capability.status = CapabilityStatus.ACTIVE
        initial_requests = capability.total_requests
        
        capability.update_performance_metrics(
            success=True,
            completion_time=1800,
            quality_score=0.8,
            rating=4.0
        )
        
        assert capability.total_requests == initial_requests + 1
        assert capability.completed_requests == 1
        assert capability.success_rate == 1.0
        assert capability.last_used is not None
    
    def test_service_match_methods(self):
        """Test ServiceMatch class methods."""
        match = ServiceMatch(
            match_id="test_match",
            request_id="test_request",
            capability_id="test_capability",
            agent_id="test_agent",
            compatibility_score=0.8,
            confidence_score=0.7,
            estimated_completion_time=1800,
            estimated_quality=0.9,
            expertise_match=True,
            availability_confirmed=True,
            agent_reputation=0.85,
            past_performance=0.9,
            current_workload=0.3
        )
        
        # Test overall match score calculation
        overall_score = match.calculate_overall_match_score()
        assert 0 <= overall_score <= 1
        assert overall_score > 0.8  # Should be high with good metrics
        
        # Test with poor metrics
        poor_match = ServiceMatch(
            match_id="poor_match",
            request_id="test_request",
            capability_id="test_capability",
            agent_id="test_agent",
            compatibility_score=0.3,
            confidence_score=0.2,
            estimated_completion_time=3600,
            estimated_quality=0.4,
            expertise_match=False,
            availability_confirmed=False,
            agent_reputation=0.3,
            past_performance=0.4,
            current_workload=0.8
        )
        
        poor_score = poor_match.calculate_overall_match_score()
        assert poor_score < overall_score
    
    @pytest.mark.asyncio
    async def test_error_handling(self, registry):
        """Test error handling in various methods."""
        # Test registering capability with invalid data
        with patch.object(registry, 'capabilities', side_effect=Exception("Storage error")):
            capability_id = await registry.register_capability(
                agent_id="test_agent",
                service_type=ServiceType.RESEARCH,
                name="Test Service",
                description="Test description"
            )
            assert capability_id == ""
        
        # Test finding providers with error
        with patch.object(registry, 'capabilities_by_service', side_effect=Exception("Index error")):
            providers = await registry.find_service_providers(ServiceType.RESEARCH)
            assert providers == []
        
        # Test matching with error
        with patch.object(registry, '_create_service_match', side_effect=Exception("Match error")):
            matches = await registry.match_service_request(
                service_type=ServiceType.RESEARCH,
                description="Test request"
            )
            assert matches == []


if __name__ == "__main__":
    pytest.main([__file__])