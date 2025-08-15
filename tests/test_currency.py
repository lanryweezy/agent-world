"""
Tests for the virtual currency system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from autonomous_ai_ecosystem.economy.currency import (
    VirtualCurrency,
    Wallet,
    Transaction,
    TransactionType,
    TransactionStatus,
    CurrencyType,
    EconomicTransaction
)


class TestWallet:
    """Test the Wallet class."""
    
    def test_wallet_creation(self):
        """Test creating a wallet."""
        wallet = Wallet(agent_id="test_agent")
        
        assert wallet.agent_id == "test_agent"
        assert len(wallet.balances) == 0
        assert wallet.wallet_address is not None
        assert wallet.private_key is not None
        assert wallet.preferred_currency == CurrencyType.NEURAL_CREDITS
    
    def test_wallet_balance_operations(self):
        """Test wallet balance operations."""
        wallet = Wallet(agent_id="test_agent")
        
        # Test initial balance
        assert wallet.get_balance(CurrencyType.NEURAL_CREDITS) == 0.0
        
        # Add balance
        wallet.balances[CurrencyType.NEURAL_CREDITS] = 100.0
        assert wallet.get_balance(CurrencyType.NEURAL_CREDITS) == 100.0
        
        # Test sufficient balance check
        assert wallet.has_sufficient_balance(CurrencyType.NEURAL_CREDITS, 50.0)
        assert not wallet.has_sufficient_balance(CurrencyType.NEURAL_CREDITS, 150.0)
    
    def test_wallet_total_value(self):
        """Test wallet total value calculation."""
        wallet = Wallet(agent_id="test_agent")
        
        wallet.balances[CurrencyType.NEURAL_CREDITS] = 100.0
        wallet.balances[CurrencyType.KNOWLEDGE_TOKENS] = 50.0
        
        exchange_rates = {
            CurrencyType.NEURAL_CREDITS: 1.0,
            CurrencyType.KNOWLEDGE_TOKENS: 0.8
        }
        
        total_value = wallet.get_total_value(exchange_rates)
        assert total_value == 140.0  # 100 * 1.0 + 50 * 0.8
    
    def test_wallet_transaction_history(self):
        """Test wallet transaction history management."""
        wallet = Wallet(agent_id="test_agent")
        
        # Add transactions
        wallet.add_transaction("tx_1")
        wallet.add_transaction("tx_2")
        
        assert len(wallet.transaction_history) == 2
        assert "tx_1" in wallet.transaction_history
        assert "tx_2" in wallet.transaction_history


class TestTransaction:
    """Test the Transaction class."""
    
    def test_transaction_creation(self):
        """Test creating a transaction."""
        transaction = Transaction(
            transaction_id="test_tx",
            transaction_type=TransactionType.TRANSFER,
            currency_type=CurrencyType.NEURAL_CREDITS,
            amount=100.0,
            sender_id="agent_1",
            recipient_id="agent_2",
            description="Test transfer"
        )
        
        assert transaction.transaction_id == "test_tx"
        assert transaction.transaction_type == TransactionType.TRANSFER
        assert transaction.amount == 100.0
        assert transaction.status == TransactionStatus.PENDING
    
    def test_transaction_hash_generation(self):
        """Test transaction hash generation."""
        transaction = Transaction(
            transaction_id="test_tx",
            transaction_type=TransactionType.TRANSFER,
            currency_type=CurrencyType.NEURAL_CREDITS,
            amount=100.0,
            sender_id="agent_1",
            recipient_id="agent_2"
        )
        
        hash1 = transaction.generate_hash()
        hash2 = transaction.generate_hash()
        
        # Same transaction should generate same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length
    
    def test_transaction_validation(self):
        """Test transaction validation."""
        transaction = Transaction(
            transaction_id="test_tx",
            transaction_type=TransactionType.TRANSFER,
            currency_type=CurrencyType.NEURAL_CREDITS,
            amount=100.0,
            sender_id="agent_1",
            recipient_id="agent_2"
        )
        
        # Without validation hash, should be invalid
        assert not transaction.is_valid()
        
        # With validation hash, should be valid
        transaction.validation_hash = transaction.generate_hash()
        assert transaction.is_valid()
        
        # Zero amount should be invalid
        transaction.amount = 0.0
        assert not transaction.is_valid()
        
        # Self-transfer (non-mining) should be invalid
        transaction.amount = 100.0
        transaction.sender_id = "agent_1"
        transaction.recipient_id = "agent_1"
        assert not transaction.is_valid()


class TestVirtualCurrency:
    """Test the VirtualCurrency class."""
    
    @pytest.fixture
    async def currency_system(self):
        """Create a test currency system."""
        system = VirtualCurrency("test_system")
        await system.initialize()
        return system
    
    @pytest.mark.asyncio
    async def test_currency_system_initialization(self):
        """Test currency system initialization."""
        system = VirtualCurrency("test_system")
        await system.initialize()
        
        assert len(system.wallets) == 0
        assert len(system.transactions) == 0
        assert system.stats["total_transactions"] == 0
        assert len(system.exchange_rates) == len(CurrencyType)
    
    @pytest.mark.asyncio
    async def test_create_wallet(self, currency_system):
        """Test wallet creation."""
        result = await currency_system.create_wallet("agent_1")
        
        assert result["success"] is True
        assert "wallet_address" in result
        assert "initial_balances" in result
        
        # Check wallet was created
        assert "agent_1" in currency_system.wallets
        wallet = currency_system.wallets["agent_1"]
        assert wallet.agent_id == "agent_1"
        
        # Check initial balances
        for currency in CurrencyType:
            assert wallet.get_balance(currency) == currency_system.config["wallet_creation_bonus"]
    
    @pytest.mark.asyncio
    async def test_create_duplicate_wallet(self, currency_system):
        """Test creating a duplicate wallet."""
        await currency_system.create_wallet("agent_1")
        result = await currency_system.create_wallet("agent_1")
        
        assert result["success"] is False
        assert "already exists" in result["error"]
    
    @pytest.mark.asyncio
    async def test_transfer_currency(self, currency_system):
        """Test currency transfer between agents."""
        # Create wallets
        await currency_system.create_wallet("agent_1")
        await currency_system.create_wallet("agent_2")
        
        # Transfer currency
        result = await currency_system.transfer_currency(
            sender_id="agent_1",
            recipient_id="agent_2",
            amount=5.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            description="Test transfer"
        )
        
        assert result["success"] is True
        assert "transaction_id" in result
        assert result["status"] == TransactionStatus.PENDING.value
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check transaction was created
        transaction_id = result["transaction_id"]
        assert transaction_id in currency_system.transactions
        
        transaction = currency_system.transactions[transaction_id]
        assert transaction.amount == 5.0
        assert transaction.sender_id == "agent_1"
        assert transaction.recipient_id == "agent_2"
    
    @pytest.mark.asyncio
    async def test_transfer_insufficient_balance(self, currency_system):
        """Test transfer with insufficient balance."""
        await currency_system.create_wallet("agent_1")
        await currency_system.create_wallet("agent_2")
        
        # Try to transfer more than available
        result = await currency_system.transfer_currency(
            sender_id="agent_1",
            recipient_id="agent_2",
            amount=1000.0,  # More than initial balance
            currency_type=CurrencyType.NEURAL_CREDITS
        )
        
        assert result["success"] is False
        assert "Insufficient balance" in result["error"]
    
    @pytest.mark.asyncio
    async def test_transfer_nonexistent_wallet(self, currency_system):
        """Test transfer with nonexistent wallet."""
        await currency_system.create_wallet("agent_1")
        
        result = await currency_system.transfer_currency(
            sender_id="agent_1",
            recipient_id="nonexistent",
            amount=5.0,
            currency_type=CurrencyType.NEURAL_CREDITS
        )
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_payment(self, currency_system):
        """Test payment processing."""
        await currency_system.create_wallet("agent_1")
        await currency_system.create_wallet("agent_2")
        
        result = await currency_system.process_payment(
            payer_id="agent_1",
            payee_id="agent_2",
            amount=3.0,
            currency_type=CurrencyType.NEURAL_CREDITS,
            service_id="service_123",
            description="Payment for service"
        )
        
        assert result["success"] is True
        assert "transaction_id" in result
        assert result["service_id"] == "service_123"
        
        # Check transaction
        transaction_id = result["transaction_id"]
        transaction = currency_system.transactions[transaction_id]
        assert transaction.transaction_type == TransactionType.PAYMENT
        assert transaction.reference_id == "service_123"
    
    @pytest.mark.asyncio
    async def test_mine_currency(self, currency_system):
        """Test currency mining."""
        await currency_system.create_wallet("agent_1")
        
        result = await currency_system.mine_currency(
            agent_id="agent_1",
            currency_type=CurrencyType.NEURAL_CREDITS,
            work_hours=2.0,
            work_quality=1.5
        )
        
        assert result["success"] is True
        assert "amount_mined" in result
        assert result["work_hours"] == 2.0
        assert result["quality_multiplier"] == 1.5
        
        # Check mining amount calculation
        expected_amount = currency_system.mining_rates[CurrencyType.NEURAL_CREDITS] * 2.0 * 1.5
        assert result["amount_mined"] == expected_amount
        
        # Check transaction
        transaction_id = result["transaction_id"]
        transaction = currency_system.transactions[transaction_id]
        assert transaction.transaction_type == TransactionType.MINING
        assert transaction.status == TransactionStatus.COMPLETED  # Mining is processed immediately
    
    @pytest.mark.asyncio
    async def test_exchange_currency(self, currency_system):
        """Test currency exchange."""
        await currency_system.create_wallet("agent_1")
        
        # Set up initial balance
        wallet = currency_system.wallets["agent_1"]
        wallet.balances[CurrencyType.NEURAL_CREDITS] = 100.0
        
        result = await currency_system.exchange_currency(
            agent_id="agent_1",
            from_currency=CurrencyType.NEURAL_CREDITS,
            to_currency=CurrencyType.KNOWLEDGE_TOKENS,
            amount=50.0
        )
        
        assert result["success"] is True
        assert "amount_received" in result
        assert "exchange_rate" in result
        assert "debit_transaction_id" in result
        assert "credit_transaction_id" in result
        
        # Check exchange calculation
        from_rate = currency_system.exchange_rates[CurrencyType.NEURAL_CREDITS]
        to_rate = currency_system.exchange_rates[CurrencyType.KNOWLEDGE_TOKENS]
        expected_rate = from_rate / to_rate
        expected_received = 50.0 * expected_rate
        
        assert result["exchange_rate"] == expected_rate
        assert result["amount_received"] == expected_received
    
    @pytest.mark.asyncio
    async def test_get_wallet_info(self, currency_system):
        """Test getting wallet information."""
        await currency_system.create_wallet("agent_1")
        
        info = currency_system.get_wallet_info("agent_1")
        
        assert "agent_id" in info
        assert info["agent_id"] == "agent_1"
        assert "balances" in info
        assert "total_value_nc" in info
        assert "wallet_address" in info
        assert "recent_transactions" in info
    
    @pytest.mark.asyncio
    async def test_get_wallet_info_nonexistent(self, currency_system):
        """Test getting info for nonexistent wallet."""
        info = currency_system.get_wallet_info("nonexistent")
        
        assert "error" in info
    
    @pytest.mark.asyncio
    async def test_get_transaction_info(self, currency_system):
        """Test getting transaction information."""
        await currency_system.create_wallet("agent_1")
        await currency_system.create_wallet("agent_2")
        
        # Create a transaction
        result = await currency_system.transfer_currency(
            sender_id="agent_1",
            recipient_id="agent_2",
            amount=5.0,
            currency_type=CurrencyType.NEURAL_CREDITS
        )
        
        transaction_id = result["transaction_id"]
        info = currency_system.get_transaction_info(transaction_id)
        
        assert "transaction_id" in info
        assert info["transaction_id"] == transaction_id
        assert "type" in info
        assert "amount" in info
        assert "sender_id" in info
        assert "recipient_id" in info
        assert "status" in info
    
    @pytest.mark.asyncio
    async def test_get_transaction_info_nonexistent(self, currency_system):
        """Test getting info for nonexistent transaction."""
        info = currency_system.get_transaction_info("nonexistent")
        
        assert "error" in info
    
    @pytest.mark.asyncio
    async def test_get_economic_stats(self, currency_system):
        """Test getting economic statistics."""
        # Create some activity
        await currency_system.create_wallet("agent_1")
        await currency_system.create_wallet("agent_2")
        await currency_system.transfer_currency("agent_1", "agent_2", 5.0, CurrencyType.NEURAL_CREDITS)
        
        stats = currency_system.get_economic_stats()
        
        assert "total_transactions" in stats
        assert "active_wallets" in stats
        assert "currency_distribution" in stats
        assert "exchange_rates" in stats
        assert "mining_rates" in stats
        assert "system_health" in stats
    
    @pytest.mark.asyncio
    async def test_get_agent_transaction_history(self, currency_system):
        """Test getting agent transaction history."""
        await currency_system.create_wallet("agent_1")
        await currency_system.create_wallet("agent_2")
        
        # Create some transactions
        await currency_system.transfer_currency("agent_1", "agent_2", 5.0, CurrencyType.NEURAL_CREDITS)
        await currency_system.mine_currency("agent_1", CurrencyType.NEURAL_CREDITS, 1.0)
        
        history = currency_system.get_agent_transaction_history("agent_1")
        
        assert isinstance(history, list)
        assert len(history) >= 2  # At least the transactions we created
        
        for transaction in history:
            assert "transaction_id" in transaction
            assert "type" in transaction
            assert "amount" in transaction
            assert "is_incoming" in transaction
            assert "net_amount" in transaction
    
    @pytest.mark.asyncio
    async def test_transaction_processing(self, currency_system):
        """Test transaction processing workflow."""
        await currency_system.create_wallet("agent_1")
        await currency_system.create_wallet("agent_2")
        
        initial_balance_1 = currency_system.wallets["agent_1"].get_balance(CurrencyType.NEURAL_CREDITS)
        initial_balance_2 = currency_system.wallets["agent_2"].get_balance(CurrencyType.NEURAL_CREDITS)
        
        # Transfer currency
        result = await currency_system.transfer_currency(
            sender_id="agent_1",
            recipient_id="agent_2",
            amount=5.0,
            currency_type=CurrencyType.NEURAL_CREDITS
        )
        
        transaction_id = result["transaction_id"]
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Check transaction status
        transaction = currency_system.transactions[transaction_id]
        assert transaction.status in [TransactionStatus.COMPLETED, TransactionStatus.PROCESSING]
        
        # If completed, check balances
        if transaction.status == TransactionStatus.COMPLETED:
            final_balance_1 = currency_system.wallets["agent_1"].get_balance(CurrencyType.NEURAL_CREDITS)
            final_balance_2 = currency_system.wallets["agent_2"].get_balance(CurrencyType.NEURAL_CREDITS)
            
            # Account for transaction fee
            expected_cost = 5.0 + transaction.transaction_fee
            assert final_balance_1 == initial_balance_1 - expected_cost
            assert final_balance_2 == initial_balance_2 + 5.0


class TestEconomicTransaction:
    """Test the EconomicTransaction class."""
    
    def test_economic_transaction_creation(self):
        """Test creating an economic transaction."""
        base_transaction = Transaction(
            transaction_id="test_tx",
            transaction_type=TransactionType.TRANSFER,
            currency_type=CurrencyType.NEURAL_CREDITS,
            amount=100.0,
            sender_id="agent_1",
            recipient_id="agent_2"
        )
        
        economic_tx = EconomicTransaction(
            base_transaction=base_transaction,
            market_conditions={"volatility": 0.1},
            exchange_rate=1.2,
            conditions=["service_completed", "quality_approved"]
        )
        
        assert economic_tx.base_transaction == base_transaction
        assert economic_tx.exchange_rate == 1.2
        assert len(economic_tx.conditions) == 2
        assert "volatility" in economic_tx.market_conditions


if __name__ == "__main__":
    pytest.main([__file__])