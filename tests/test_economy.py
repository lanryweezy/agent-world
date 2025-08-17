"""
Unit tests for the economy system, including currency and marketplace.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from autonomous_ai_ecosystem.economy.currency import VirtualCurrency, CurrencyType
from autonomous_ai_ecosystem.economy.marketplace import ServiceMarketplace, ServiceCategory

@pytest.mark.asyncio
class TestVirtualCurrency:
    """Test cases for the VirtualCurrency system."""

    @pytest.fixture
    async def currency_system(self):
        """Fixture to create a VirtualCurrency instance."""
        system = VirtualCurrency("test_currency_system")
        await system.initialize()
        return system

    async def test_wallet_creation(self, currency_system):
        """Test that a wallet is created successfully for an agent."""
        agent_id = "agent_1"
        result = await currency_system.create_wallet(agent_id)

        assert result["success"]
        assert agent_id in currency_system.wallets

        wallet_info = await currency_system.get_wallet_info(agent_id)
        assert wallet_info["balances"][CurrencyType.NEURAL_CREDITS.value] > 0

    async def test_fund_transfer(self, currency_system):
        """Test transferring funds between two wallets."""
        agent_1 = "agent_1"
        agent_2 = "agent_2"
        await currency_system.create_wallet(agent_1)
        await currency_system.create_wallet(agent_2)

        initial_balance_2 = (await currency_system.get_wallet_info(agent_2))["balances"][CurrencyType.NEURAL_CREDITS.value]

        # Transfer funds
        transfer_amount = 5.0
        await currency_system.transfer_currency(
            sender_id=agent_1,
            recipient_id=agent_2,
            amount=transfer_amount,
            currency_type=CurrencyType.NEURAL_CREDITS
        )

        # Wait for transaction to process (it's async)
        await asyncio.sleep(0.1)

        final_balance_2 = (await currency_system.get_wallet_info(agent_2))["balances"][CurrencyType.NEURAL_CREDITS.value]

        assert final_balance_2 == initial_balance_2 + transfer_amount

@pytest.mark.asyncio
class TestServiceMarketplace:
    """Test cases for the ServiceMarketplace."""

    @pytest.fixture
    async def marketplace(self):
        """Fixture to create a ServiceMarketplace instance with a mock currency system."""
        mock_currency_system = Mock(spec=VirtualCurrency)
        mock_currency_system.process_payment = AsyncMock(return_value={"success": True, "transaction_id": "txn_123"})

        market = ServiceMarketplace("test_marketplace", mock_currency_system)
        await market.initialize()
        return market

    async def test_service_listing(self, marketplace):
        """Test that an agent can list a new service."""
        provider_id = "agent_provider"
        result = await marketplace.create_service_listing(
            provider_id=provider_id,
            service_name="Data Analysis",
            description="Analyzes data sets.",
            category=ServiceCategory.ANALYSIS,
            base_price=100.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            capabilities=[]
        )

        assert result["success"]
        assert result["listing_id"] is not None

        listings = marketplace.get_agent_listings(provider_id)
        assert len(listings) == 1
        assert listings[0]["service_name"] == "Data Analysis"

    async def test_search_services(self, marketplace):
        """Test searching for services."""
        provider_id = "agent_provider"
        await marketplace.create_service_listing(
            provider_id=provider_id,
            service_name="Data Analysis",
            description="Analyzes data sets for research.",
            category=ServiceCategory.ANALYSIS,
            base_price=100.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            capabilities=[]
        )

        results = await marketplace.search_services(keywords=["research"])
        assert len(results) == 1
        assert results[0]["service_name"] == "Data Analysis"

        no_results = await marketplace.search_services(keywords=["art"])
        assert len(no_results) == 0

    async def test_service_purchase(self, marketplace):
        """Test the flow of requesting and purchasing a service."""
        provider_id = "agent_provider"
        client_id = "agent_client"

        # List a service
        listing_result = await marketplace.create_service_listing(
            provider_id=provider_id,
            service_name="Data Analysis",
            description="Analyzes data sets.",
            category=ServiceCategory.ANALYSIS,
            base_price=100.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            capabilities=[]
        )
        listing_id = listing_result["listing_id"]

        # Request the service
        request_result = await marketplace.request_service(
            client_id=client_id,
            listing_id=listing_id,
            service_description="Please analyze my data."
        )

        assert request_result["success"]
        assert request_result["status"] == "accepted" # Auto-accepted for simple case
        contract_id = request_result["contract_id"]

        # Check that a contract was created
        assert contract_id in marketplace.service_contracts
        contract = marketplace.service_contracts[contract_id]
        assert contract.client_id == client_id
        assert contract.provider_id == provider_id
