"""
Tests for the service marketplace system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.economy.marketplace import (
    ServiceMarketplace,
    ServiceListing,
    ServiceContract,
    ServiceCapability,
    ServiceReview,
    ServiceCategory,
    ServiceStatus,
    ContractStatus,
    QualityRating,
    MarketplaceTransaction
)
from autonomous_ai_ecosystem.economy.currency import VirtualCurrency, CurrencyType


class TestServiceCapability:
    """Test the ServiceCapability class."""
    
    def test_capability_creation(self):
        """Test creating a service capability."""
        capability = ServiceCapability(
            capability_id="cap_1",
            name="Data Analysis",
            description="Advanced data analysis and visualization",
            category=ServiceCategory.ANALYSIS,
            skill_level=0.8
        )
        
        assert capability.capability_id == "cap_1"
        assert capability.name == "Data Analysis"
        assert capability.category == ServiceCategory.ANALYSIS
        assert capability.skill_level == 0.8
        assert capability.experience_points == 0
        assert capability.success_rate == 1.0
    
    def test_expertise_level_calculation(self):
        """Test expertise level calculation."""
        capability = ServiceCapability(
            capability_id="cap_1",
            name="Test Skill",
            description="Test skill",
            category=ServiceCategory.COMPUTATIONAL,
            skill_level=0.95
        )
        
        assert capability.get_expertise_level() == "Expert"
        
        capability.skill_level = 0.75
        assert capability.get_expertise_level() == "Advanced"
        
        capability.skill_level = 0.55
        assert capability.get_expertise_level() == "Intermediate"
        
        capability.skill_level = 0.35
        assert capability.get_expertise_level() == "Beginner"
        
        capability.skill_level = 0.15
        assert capability.get_expertise_level() == "Novice"


class TestServiceListing:
    """Test the ServiceListing class."""
    
    def test_listing_creation(self):
        """Test creating a service listing."""
        listing = ServiceListing(
            listing_id="listing_1",
            provider_id="agent_1",
            service_name="Data Analysis Service",
            description="Professional data analysis",
            category=ServiceCategory.ANALYSIS,
            base_price=50.0,
            currency_type=CurrencyType.NEURAL_CREDITS
        )
        
        assert listing.listing_id == "listing_1"
        assert listing.provider_id == "agent_1"
        assert listing.service_name == "Data Analysis Service"
        assert listing.category == ServiceCategory.ANALYSIS
        assert listing.base_price == 50.0
        assert listing.status == ServiceStatus.AVAILABLE
        assert listing.rating == 5.0
    
    def test_availability_check(self):
        """Test service availability checking."""
        listing = ServiceListing(
            listing_id="listing_1",
            provider_id="agent_1",
            service_name="Test Service",
            description="Test service",
            category=ServiceCategory.COMPUTATIONAL,
            base_price=10.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            max_concurrent_jobs=2
        )
        
        # Should be available initially
        assert listing.is_available()
        
        # Add active contracts
        listing.active_contracts.add("contract_1")
        assert listing.is_available()  # Still under limit
        
        listing.active_contracts.add("contract_2")
        assert not listing.is_available()  # At capacity
        
        # Change status
        listing.active_contracts.clear()
        listing.status = ServiceStatus.OFFLINE
        assert not listing.is_available()
    
    def test_dynamic_pricing(self):
        """Test dynamic pricing calculation."""
        listing = ServiceListing(
            listing_id="listing_1",
            provider_id="agent_1",
            service_name="Test Service",
            description="Test service",
            category=ServiceCategory.COMPUTATIONAL,
            base_price=100.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            rating=4.0
        )
        
        # Base price with no demand
        price = listing.calculate_dynamic_price(demand_factor=1.0)
        assert price > 100.0  # Should be higher due to quality premium
        
        # High demand
        high_demand_price = listing.calculate_dynamic_price(demand_factor=2.0)
        assert high_demand_price > price
        
        # Low rating should reduce price
        listing.rating = 2.0
        low_rating_price = listing.calculate_dynamic_price(demand_factor=1.0)
        assert low_rating_price < 100.0


class TestServiceContract:
    """Test the ServiceContract class."""
    
    def test_contract_creation(self):
        """Test creating a service contract."""
        contract = ServiceContract(
            contract_id="contract_1",
            listing_id="listing_1",
            provider_id="agent_1",
            client_id="agent_2",
            service_description="Data analysis task",
            agreed_price=75.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            estimated_duration=2.0
        )
        
        assert contract.contract_id == "contract_1"
        assert contract.provider_id == "agent_1"
        assert contract.client_id == "agent_2"
        assert contract.agreed_price == 75.0
        assert contract.status == ContractStatus.PROPOSED
        assert contract.progress_percentage == 0.0
    
    def test_overdue_check(self):
        """Test contract overdue checking."""
        contract = ServiceContract(
            contract_id="contract_1",
            listing_id="listing_1",
            provider_id="agent_1",
            client_id="agent_2",
            service_description="Test task",
            agreed_price=50.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            estimated_duration=1.0,
            deadline=datetime.now() - timedelta(hours=1)  # Past deadline
        )
        
        assert contract.is_overdue()
        
        # Future deadline
        contract.deadline = datetime.now() + timedelta(hours=1)
        assert not contract.is_overdue()
        
        # Completed contract should not be overdue
        contract.deadline = datetime.now() - timedelta(hours=1)
        contract.status = ContractStatus.COMPLETED
        assert not contract.is_overdue()
    
    def test_duration_calculation(self):
        """Test contract duration calculation."""
        contract = ServiceContract(
            contract_id="contract_1",
            listing_id="listing_1",
            provider_id="agent_1",
            client_id="agent_2",
            service_description="Test task",
            agreed_price=50.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            estimated_duration=1.0
        )
        
        # No start time
        assert contract.get_duration_so_far() == 0.0
        
        # With start time
        contract.started_at = datetime.now() - timedelta(hours=2)
        duration = contract.get_duration_so_far()
        assert 1.9 < duration < 2.1  # Approximately 2 hours
        
        # With completion time
        contract.completed_at = datetime.now() - timedelta(hours=1)
        duration = contract.get_duration_so_far()
        assert 0.9 < duration < 1.1  # Approximately 1 hour


class TestServiceMarketplace:
    """Test the ServiceMarketplace class."""
    
    @pytest.fixture
    async def marketplace(self):
        """Create a test marketplace."""
        # Create mock currency system
        currency_system = Mock(spec=VirtualCurrency)
        currency_system.process_payment = AsyncMock(return_value={"success": True, "transaction_id": "tx_123"})
        
        marketplace = ServiceMarketplace("test_marketplace", currency_system)
        await marketplace.initialize()
        return marketplace
    
    @pytest.mark.asyncio
    async def test_marketplace_initialization(self):
        """Test marketplace initialization."""
        currency_system = Mock(spec=VirtualCurrency)
        marketplace = ServiceMarketplace("test_marketplace", currency_system)
        await marketplace.initialize()
        
        assert len(marketplace.service_listings) == 0
        assert len(marketplace.service_contracts) == 0
        assert marketplace.market_stats["total_listings"] == 0
    
    @pytest.mark.asyncio
    async def test_register_service_capability(self, marketplace):
        """Test registering a service capability."""
        result = await marketplace.register_service_capability(
            agent_id="agent_1",
            name="Data Analysis",
            description="Advanced data analysis",
            category=ServiceCategory.ANALYSIS,
            skill_level=0.8
        )
        
        assert result["success"] is True
        assert "capability_id" in result
        assert result["expertise_level"] == "Advanced"
        
        # Check capability was stored
        assert "agent_1" in marketplace.agent_capabilities
        capabilities = marketplace.agent_capabilities["agent_1"]
        assert len(capabilities) == 1
        assert capabilities[0].name == "Data Analysis"
    
    @pytest.mark.asyncio
    async def test_create_service_listing(self, marketplace):
        """Test creating a service listing."""
        # First register a capability
        await marketplace.register_service_capability(
            agent_id="agent_1",
            name="Data Analysis",
            description="Advanced data analysis",
            category=ServiceCategory.ANALYSIS,
            skill_level=0.8
        )
        
        capability_id = marketplace.agent_capabilities["agent_1"][0].capability_id
        
        result = await marketplace.create_service_listing(
            provider_id="agent_1",
            service_name="Professional Data Analysis",
            description="High-quality data analysis service",
            category=ServiceCategory.ANALYSIS,
            base_price=100.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            capabilities=[capability_id]
        )
        
        assert result["success"] is True
        assert "listing_id" in result
        assert result["status"] == ServiceStatus.AVAILABLE.value
        
        # Check listing was stored
        listing_id = result["listing_id"]
        assert listing_id in marketplace.service_listings
        
        listing = marketplace.service_listings[listing_id]
        assert listing.service_name == "Professional Data Analysis"
        assert listing.provider_id == "agent_1"
        assert listing.base_price == 100.0
    
    @pytest.mark.asyncio
    async def test_create_listing_invalid_capability(self, marketplace):
        """Test creating listing with invalid capability."""
        result = await marketplace.create_service_listing(
            provider_id="agent_1",
            service_name="Test Service",
            description="Test service",
            category=ServiceCategory.ANALYSIS,
            base_price=50.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            capabilities=["invalid_capability"]
        )
        
        assert result["success"] is False
        assert "Invalid capabilities" in result["error"]
    
    @pytest.mark.asyncio
    async def test_create_listing_invalid_price(self, marketplace):
        """Test creating listing with invalid price."""
        result = await marketplace.create_service_listing(
            provider_id="agent_1",
            service_name="Test Service",
            description="Test service",
            category=ServiceCategory.ANALYSIS,
            base_price=0.5,  # Below minimum
            currency_type=CurrencyType.NEURAL_CREDITS,
            capabilities=[]
        )
        
        assert result["success"] is False
        assert "Price outside allowed range" in result["error"]
    
    @pytest.mark.asyncio
    async def test_search_services(self, marketplace):
        """Test searching for services."""
        # Create some test listings
        await marketplace.register_service_capability(
            agent_id="agent_1",
            name="Data Analysis",
            description="Data analysis",
            category=ServiceCategory.ANALYSIS,
            skill_level=0.8
        )
        
        capability_id = marketplace.agent_capabilities["agent_1"][0].capability_id
        
        await marketplace.create_service_listing(
            provider_id="agent_1",
            service_name="Data Analysis Service",
            description="Professional data analysis",
            category=ServiceCategory.ANALYSIS,
            base_price=100.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            capabilities=[capability_id]
        )
        
        await marketplace.create_service_listing(
            provider_id="agent_1",
            service_name="Research Service",
            description="Research assistance",
            category=ServiceCategory.RESEARCH,
            base_price=75.0,
            currency_type=CurrencyType.KNOWLEDGE_TOKENS,
            capabilities=[]
        )
        
        # Search all services
        results = await marketplace.search_services()
        assert len(results) == 2
        
        # Search by category
        analysis_results = await marketplace.search_services(category=ServiceCategory.ANALYSIS)
        assert len(analysis_results) == 1
        assert analysis_results[0]["service_name"] == "Data Analysis Service"
        
        # Search by max price
        cheap_results = await marketplace.search_services(max_price=80.0)
        assert len(cheap_results) == 1
        assert cheap_results[0]["service_name"] == "Research Service"
        
        # Search by keywords
        keyword_results = await marketplace.search_services(keywords=["data"])
        assert len(keyword_results) == 1
        assert keyword_results[0]["service_name"] == "Data Analysis Service"
    
    @pytest.mark.asyncio
    async def test_request_service(self, marketplace):
        """Test requesting a service."""
        # Create a test listing
        await marketplace.register_service_capability(
            agent_id="agent_1",
            name="Analysis",
            description="Analysis capability",
            category=ServiceCategory.ANALYSIS,
            skill_level=0.8
        )
        
        capability_id = marketplace.agent_capabilities["agent_1"][0].capability_id
        
        listing_result = await marketplace.create_service_listing(
            provider_id="agent_1",
            service_name="Test Service",
            description="Test service",
            category=ServiceCategory.ANALYSIS,
            base_price=50.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            capabilities=[capability_id]
        )
        
        listing_id = listing_result["listing_id"]
        
        # Request the service
        request_result = await marketplace.request_service(
            client_id="agent_2",
            listing_id=listing_id,
            service_description="Need data analysis",
            proposed_price=50.0
        )
        
        assert request_result["success"] is True
        assert "contract_id" in request_result
        assert request_result["status"] == ContractStatus.ACCEPTED.value  # Auto-accepted due to matching price
        
        # Check contract was created
        contract_id = request_result["contract_id"]
        assert contract_id in marketplace.service_contracts
        
        contract = marketplace.service_contracts[contract_id]
        assert contract.client_id == "agent_2"
        assert contract.provider_id == "agent_1"
        assert contract.agreed_price == 50.0
    
    @pytest.mark.asyncio
    async def test_request_nonexistent_service(self, marketplace):
        """Test requesting a nonexistent service."""
        result = await marketplace.request_service(
            client_id="agent_1",
            listing_id="nonexistent",
            service_description="Test request"
        )
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_start_contract_work(self, marketplace):
        """Test starting work on a contract."""
        # Create and accept a contract
        await self._create_test_contract(marketplace)
        
        # Get the contract
        contract_id = list(marketplace.service_contracts.keys())[0]
        contract = marketplace.service_contracts[contract_id]
        contract.status = ContractStatus.ACCEPTED  # Ensure it's accepted
        
        # Start work
        result = await marketplace.start_contract_work(contract_id, "agent_1")
        
        assert result["success"] is True
        assert result["status"] == ContractStatus.IN_PROGRESS.value
        
        # Check contract status
        assert contract.status == ContractStatus.IN_PROGRESS
        assert contract.started_at is not None
    
    @pytest.mark.asyncio
    async def test_start_work_unauthorized(self, marketplace):
        """Test starting work on contract without authorization."""
        await self._create_test_contract(marketplace)
        
        contract_id = list(marketplace.service_contracts.keys())[0]
        
        result = await marketplace.start_contract_work(contract_id, "unauthorized_agent")
        
        assert result["success"] is False
        assert "Not authorized" in result["error"]
    
    @pytest.mark.asyncio
    async def test_complete_contract(self, marketplace):
        """Test completing a contract."""
        await self._create_test_contract(marketplace)
        
        contract_id = list(marketplace.service_contracts.keys())[0]
        contract = marketplace.service_contracts[contract_id]
        contract.status = ContractStatus.IN_PROGRESS
        contract.started_at = datetime.now() - timedelta(hours=1)
        
        deliverables = [
            {"type": "report", "description": "Analysis report", "file": "report.pdf"}
        ]
        
        result = await marketplace.complete_contract(
            contract_id=contract_id,
            provider_id="agent_1",
            deliverables=deliverables,
            completion_notes="Work completed successfully"
        )
        
        assert result["success"] is True
        assert result["status"] == ContractStatus.COMPLETED.value
        
        # Check contract status
        assert contract.status == ContractStatus.COMPLETED
        assert contract.completed_at is not None
        assert contract.progress_percentage == 100.0
        assert len(contract.deliverables) == 1
    
    @pytest.mark.asyncio
    async def test_submit_review(self, marketplace):
        """Test submitting a review."""
        await self._create_test_contract(marketplace)
        
        contract_id = list(marketplace.service_contracts.keys())[0]
        contract = marketplace.service_contracts[contract_id]
        contract.status = ContractStatus.COMPLETED
        
        result = await marketplace.submit_review(
            reviewer_id="agent_2",  # Client
            contract_id=contract_id,
            rating=QualityRating.EXCELLENT,
            title="Great service",
            comment="Very satisfied with the work"
        )
        
        assert result["success"] is True
        assert "review_id" in result
        assert result["rating"] == QualityRating.EXCELLENT.value
        
        # Check review was stored
        review_id = result["review_id"]
        assert review_id in marketplace.service_reviews
        
        review = marketplace.service_reviews[review_id]
        assert review.reviewer_id == "agent_2"
        assert review.rating == QualityRating.EXCELLENT
        assert review.verified is True
    
    @pytest.mark.asyncio
    async def test_submit_duplicate_review(self, marketplace):
        """Test submitting duplicate review."""
        await self._create_test_contract(marketplace)
        
        contract_id = list(marketplace.service_contracts.keys())[0]
        contract = marketplace.service_contracts[contract_id]
        contract.status = ContractStatus.COMPLETED
        
        # Submit first review
        await marketplace.submit_review(
            reviewer_id="agent_2",
            contract_id=contract_id,
            rating=QualityRating.GOOD,
            title="Good service",
            comment="Satisfied"
        )
        
        # Try to submit duplicate
        result = await marketplace.submit_review(
            reviewer_id="agent_2",
            contract_id=contract_id,
            rating=QualityRating.EXCELLENT,
            title="Updated review",
            comment="Even better"
        )
        
        assert result["success"] is False
        assert "already submitted" in result["error"]
    
    @pytest.mark.asyncio
    async def test_report_dispute(self, marketplace):
        """Test reporting a dispute."""
        await self._create_test_contract(marketplace)
        
        contract_id = list(marketplace.service_contracts.keys())[0]
        contract = marketplace.service_contracts[contract_id]
        contract.status = ContractStatus.IN_PROGRESS
        
        result = await marketplace.report_dispute(
            reporter_id="agent_2",  # Client
            contract_id=contract_id,
            dispute_reason="Work not meeting requirements",
            evidence=[{"type": "message", "content": "Provider not responding"}]
        )
        
        assert result["success"] is True
        assert result["status"] == ContractStatus.DISPUTED.value
        assert "mediator_id" in result
        
        # Check contract status
        assert contract.status == ContractStatus.DISPUTED
        assert contract.dispute_reason == "Work not meeting requirements"
        assert contract.mediator_id is not None
    
    def test_get_agent_listings(self, marketplace):
        """Test getting agent listings."""
        # This test needs to be run after marketplace initialization
        asyncio.run(self._test_get_agent_listings_async(marketplace))
    
    async def _test_get_agent_listings_async(self, marketplace):
        """Async helper for agent listings test."""
        await self._create_test_listing(marketplace)
        
        listings = marketplace.get_agent_listings("agent_1")
        
        assert len(listings) == 1
        listing = listings[0]
        assert listing["service_name"] == "Test Service"
        assert listing["status"] == ServiceStatus.AVAILABLE.value
    
    def test_get_agent_contracts(self, marketplace):
        """Test getting agent contracts."""
        asyncio.run(self._test_get_agent_contracts_async(marketplace))
    
    async def _test_get_agent_contracts_async(self, marketplace):
        """Async helper for agent contracts test."""
        await self._create_test_contract(marketplace)
        
        # Get contracts as provider
        provider_contracts = marketplace.get_agent_contracts("agent_1", role="provider")
        assert len(provider_contracts) == 1
        assert provider_contracts[0]["agent_role"] == "provider"
        
        # Get contracts as client
        client_contracts = marketplace.get_agent_contracts("agent_2", role="client")
        assert len(client_contracts) == 1
        assert client_contracts[0]["agent_role"] == "client"
    
    def test_get_marketplace_stats(self, marketplace):
        """Test getting marketplace statistics."""
        asyncio.run(self._test_get_marketplace_stats_async(marketplace))
    
    async def _test_get_marketplace_stats_async(self, marketplace):
        """Async helper for marketplace stats test."""
        await self._create_test_contract(marketplace)
        
        stats = marketplace.get_marketplace_stats()
        
        assert "total_listings" in stats
        assert "total_contracts" in stats
        assert "category_statistics" in stats
        assert "total_providers" in stats
        assert stats["total_listings"] >= 1
        assert stats["total_contracts"] >= 1
    
    def test_get_trending_services(self, marketplace):
        """Test getting trending services."""
        asyncio.run(self._test_get_trending_services_async(marketplace))
    
    async def _test_get_trending_services_async(self, marketplace):
        """Async helper for trending services test."""
        await self._create_test_listing(marketplace)
        
        trending = marketplace.get_trending_services(limit=5)
        
        # Should return available services
        assert isinstance(trending, list)
        # Trending calculation requires recent contracts, so might be empty
    
    # Helper methods
    
    async def _create_test_listing(self, marketplace):
        """Helper to create a test listing."""
        await marketplace.register_service_capability(
            agent_id="agent_1",
            name="Test Capability",
            description="Test capability",
            category=ServiceCategory.ANALYSIS,
            skill_level=0.8
        )
        
        capability_id = marketplace.agent_capabilities["agent_1"][0].capability_id
        
        return await marketplace.create_service_listing(
            provider_id="agent_1",
            service_name="Test Service",
            description="Test service",
            category=ServiceCategory.ANALYSIS,
            base_price=50.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            capabilities=[capability_id]
        )
    
    async def _create_test_contract(self, marketplace):
        """Helper to create a test contract."""
        listing_result = await self._create_test_listing(marketplace)
        listing_id = listing_result["listing_id"]
        
        return await marketplace.request_service(
            client_id="agent_2",
            listing_id=listing_id,
            service_description="Test request"
        )


class TestServiceReview:
    """Test the ServiceReview class."""
    
    def test_review_creation(self):
        """Test creating a service review."""
        review = ServiceReview(
            review_id="review_1",
            contract_id="contract_1",
            listing_id="listing_1",
            reviewer_id="agent_1",
            provider_id="agent_2",
            rating=QualityRating.EXCELLENT,
            title="Great service",
            comment="Very satisfied with the quality of work"
        )
        
        assert review.review_id == "review_1"
        assert review.rating == QualityRating.EXCELLENT
        assert review.title == "Great service"
        assert review.verified is False  # Default
        assert review.helpful_votes == 0


if __name__ == "__main__":
    pytest.main([__file__])