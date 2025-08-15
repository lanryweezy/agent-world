"""
Virtual currency and transaction system for the autonomous AI ecosystem.

This module implements a virtual currency system with wallets, transactions,
and economic interactions between agents.
"""

import asyncio
import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from ..core.interfaces import AgentModule
from ..core.logger import get_agent_logger, log_agent_event


class CurrencyType(Enum):
    """Types of virtual currencies in the ecosystem."""
    NEURAL_CREDITS = "neural_credits"  # Primary currency for computational services
    KNOWLEDGE_TOKENS = "knowledge_tokens"  # Currency for information and learning
    CREATIVITY_COINS = "creativity_coins"  # Currency for creative and artistic services
    COLLABORATION_POINTS = "collaboration_points"  # Earned through teamwork
    REPUTATION_UNITS = "reputation_units"  # Based on agent status and achievements


class TransactionType(Enum):
    """Types of transactions in the system."""
    TRANSFER = "transfer"  # Direct transfer between agents
    PAYMENT = "payment"  # Payment for services
    REWARD = "reward"  # System rewards
    PENALTY = "penalty"  # System penalties
    MINING = "mining"  # Currency generation through work
    EXCHANGE = "exchange"  # Currency exchange between types
    ESCROW = "escrow"  # Held in escrow for contracts
    REFUND = "refund"  # Refund of previous payment


class TransactionStatus(Enum):
    """Status of transactions."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    REFUNDED = "refunded"


@dataclass
class Transaction:
    """Represents a transaction in the virtual currency system."""
    transaction_id: str
    transaction_type: TransactionType
    currency_type: CurrencyType
    amount: float
    sender_id: str
    recipient_id: str
    
    # Transaction details
    description: str = ""
    reference_id: Optional[str] = None  # Reference to service, contract, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Status and timing
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Fees and validation
    transaction_fee: float = 0.0
    gas_fee: float = 0.0  # Computational cost
    validation_hash: Optional[str] = None
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def generate_hash(self) -> str:
        """Generate a validation hash for the transaction."""
        hash_data = f"{self.transaction_id}{self.sender_id}{self.recipient_id}{self.amount}{self.currency_type.value}{self.created_at.isoformat()}"
        return hashlib.sha256(hash_data.encode()).hexdigest()
    
    def is_valid(self) -> bool:
        """Check if the transaction is valid."""
        if self.amount <= 0:
            return False
        if self.sender_id == self.recipient_id and self.transaction_type != TransactionType.MINING:
            return False
        if not self.validation_hash:
            return False
        return self.validation_hash == self.generate_hash()


@dataclass
class Wallet:
    """Represents an agent's wallet with multiple currency balances."""
    agent_id: str
    balances: Dict[CurrencyType, float] = field(default_factory=dict)
    
    # Wallet security
    wallet_address: str = field(default_factory=lambda: str(uuid.uuid4()))
    private_key: str = field(default_factory=lambda: hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest())
    
    # Transaction history
    transaction_history: List[str] = field(default_factory=list)  # transaction_ids
    
    # Wallet settings
    daily_spending_limit: Dict[CurrencyType, float] = field(default_factory=dict)
    auto_exchange_enabled: bool = False
    preferred_currency: CurrencyType = CurrencyType.NEURAL_CREDITS
    
    # Statistics
    total_earned: Dict[CurrencyType, float] = field(default_factory=dict)
    total_spent: Dict[CurrencyType, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def get_balance(self, currency_type: CurrencyType) -> float:
        """Get balance for a specific currency type."""
        return self.balances.get(currency_type, 0.0)
    
    def get_total_value(self, exchange_rates: Dict[CurrencyType, float]) -> float:
        """Get total wallet value in neural credits equivalent."""
        total = 0.0
        for currency_type, balance in self.balances.items():
            rate = exchange_rates.get(currency_type, 1.0)
            total += balance * rate
        return total
    
    def has_sufficient_balance(self, currency_type: CurrencyType, amount: float) -> bool:
        """Check if wallet has sufficient balance for a transaction."""
        return self.get_balance(currency_type) >= amount
    
    def add_transaction(self, transaction_id: str) -> None:
        """Add a transaction to the history."""
        self.transaction_history.append(transaction_id)
        self.last_activity = datetime.now()
        
        # Limit history size
        if len(self.transaction_history) > 1000:
            self.transaction_history = self.transaction_history[-1000:]


@dataclass
class EconomicTransaction:
    """Extended transaction with economic context and smart contract features."""
    base_transaction: Transaction
    
    # Economic context
    market_conditions: Dict[str, float] = field(default_factory=dict)
    exchange_rate: float = 1.0
    inflation_adjustment: float = 1.0
    
    # Smart contract features
    conditions: List[str] = field(default_factory=list)
    auto_execute: bool = False
    execution_time: Optional[datetime] = None
    
    # Multi-party transactions
    involved_parties: List[str] = field(default_factory=list)
    approval_required: bool = False
    approvals: Dict[str, bool] = field(default_factory=dict)
    
    # Escrow features
    escrow_agent: Optional[str] = None
    escrow_conditions: List[str] = field(default_factory=list)
    escrow_timeout: Optional[datetime] = None


class VirtualCurrency(AgentModule):
    """
    Virtual currency system managing wallets, transactions, and economic interactions.
    
    Provides a complete economic framework for agent interactions including
    multiple currency types, transaction processing, and economic incentives.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.logger = get_agent_logger(agent_id, "currency")
        
        # Core data structures
        self.wallets: Dict[str, Wallet] = {}  # agent_id -> Wallet
        self.transactions: Dict[str, Transaction] = {}  # transaction_id -> Transaction
        self.economic_transactions: Dict[str, EconomicTransaction] = {}
        self.pending_transactions: Set[str] = set()
        
        # System configuration
        self.config = {
            "base_transaction_fee": 0.01,
            "gas_fee_multiplier": 0.001,
            "daily_mining_limit": 100.0,
            "exchange_fee_rate": 0.02,
            "inflation_rate": 0.001,  # Daily inflation rate
            "max_transaction_amount": 10000.0,
            "min_transaction_amount": 0.01,
            "transaction_timeout_hours": 24.0,
            "wallet_creation_bonus": 10.0
        }
        
        # Exchange rates (relative to neural_credits)
        self.exchange_rates = {
            CurrencyType.NEURAL_CREDITS: 1.0,
            CurrencyType.KNOWLEDGE_TOKENS: 0.8,
            CurrencyType.CREATIVITY_COINS: 1.2,
            CurrencyType.COLLABORATION_POINTS: 0.6,
            CurrencyType.REPUTATION_UNITS: 2.0
        }
        
        # Mining rates (currency per hour of work)
        self.mining_rates = {
            CurrencyType.NEURAL_CREDITS: 5.0,
            CurrencyType.KNOWLEDGE_TOKENS: 3.0,
            CurrencyType.CREATIVITY_COINS: 2.0,
            CurrencyType.COLLABORATION_POINTS: 8.0,
            CurrencyType.REPUTATION_UNITS: 1.0
        }
        
        # Economic statistics
        self.stats = {
            "total_transactions": 0,
            "total_volume": {currency.value: 0.0 for currency in CurrencyType},
            "active_wallets": 0,
            "failed_transactions": 0,
            "average_transaction_time": 0.0,
            "currency_in_circulation": {currency.value: 0.0 for currency in CurrencyType}
        }
        
        # Transaction processing
        self.transaction_counter = 0
        self.processing_queue = asyncio.Queue()
        
        self.logger.info("Virtual currency system initialized")
    
    async def initialize(self) -> None:
        """Initialize the currency system."""
        try:
            # Start transaction processing
            asyncio.create_task(self._transaction_processor())
            asyncio.create_task(self._economic_updater())
            asyncio.create_task(self._cleanup_processor())
            
            self.logger.info("Currency system initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize currency system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the currency system."""
        try:
            # Process remaining transactions
            while not self.processing_queue.empty():
                await asyncio.sleep(0.1)
            
            # Save system state
            await self._save_system_state()
            
            self.logger.info("Currency system shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during currency system shutdown: {e}")
    
    async def create_wallet(self, agent_id: str) -> Dict[str, Any]:
        """Create a new wallet for an agent."""
        try:
            if agent_id in self.wallets:
                return {"success": False, "error": "Wallet already exists"}
            
            # Create wallet with initial balances
            wallet = Wallet(agent_id=agent_id)
            
            # Initialize with small amounts of each currency
            for currency_type in CurrencyType:
                wallet.balances[currency_type] = self.config["wallet_creation_bonus"]
                wallet.total_earned[currency_type] = self.config["wallet_creation_bonus"]
                wallet.daily_spending_limit[currency_type] = 100.0
                
                # Update circulation
                self.stats["currency_in_circulation"][currency_type.value] += self.config["wallet_creation_bonus"]
            
            self.wallets[agent_id] = wallet
            self.stats["active_wallets"] += 1
            
            log_agent_event(
                self.agent_id,
                "wallet_created",
                {
                    "agent_id": agent_id,
                    "wallet_address": wallet.wallet_address,
                    "initial_balance": self.config["wallet_creation_bonus"]
                }
            )
            
            result = {
                "success": True,
                "wallet_address": wallet.wallet_address,
                "initial_balances": dict(wallet.balances),
                "currencies_supported": [currency.value for currency in CurrencyType]
            }
            
            self.logger.info(f"Created wallet for agent {agent_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create wallet: {e}")
            return {"success": False, "error": str(e)}
    
    async def transfer_currency(
        self,
        sender_id: str,
        recipient_id: str,
        amount: float,
        currency_type: CurrencyType,
        description: str = "",
        reference_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transfer currency between agents."""
        try:
            # Validate inputs
            if amount < self.config["min_transaction_amount"]:
                return {"success": False, "error": "Amount below minimum"}
            
            if amount > self.config["max_transaction_amount"]:
                return {"success": False, "error": "Amount exceeds maximum"}
            
            # Check wallets exist
            if sender_id not in self.wallets:
                return {"success": False, "error": "Sender wallet not found"}
            
            if recipient_id not in self.wallets:
                return {"success": False, "error": "Recipient wallet not found"}
            
            sender_wallet = self.wallets[sender_id]
            
            # Check sufficient balance
            total_cost = amount + self._calculate_transaction_fee(amount, currency_type)
            if not sender_wallet.has_sufficient_balance(currency_type, total_cost):
                return {"success": False, "error": "Insufficient balance"}
            
            # Create transaction
            transaction = await self._create_transaction(
                transaction_type=TransactionType.TRANSFER,
                currency_type=currency_type,
                amount=amount,
                sender_id=sender_id,
                recipient_id=recipient_id,
                description=description,
                reference_id=reference_id
            )
            
            # Queue for processing
            await self.processing_queue.put(transaction.transaction_id)
            
            result = {
                "success": True,
                "transaction_id": transaction.transaction_id,
                "status": transaction.status.value,
                "transaction_fee": transaction.transaction_fee,
                "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat()
            }
            
            self.logger.info(f"Transfer initiated: {amount} {currency_type.value} from {sender_id} to {recipient_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to transfer currency: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_payment(
        self,
        payer_id: str,
        payee_id: str,
        amount: float,
        currency_type: CurrencyType,
        service_id: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """Process a payment for services."""
        try:
            # Validate payment
            if payer_id not in self.wallets or payee_id not in self.wallets:
                return {"success": False, "error": "Wallet not found"}
            
            payer_wallet = self.wallets[payer_id]
            total_cost = amount + self._calculate_transaction_fee(amount, currency_type)
            
            if not payer_wallet.has_sufficient_balance(currency_type, total_cost):
                return {"success": False, "error": "Insufficient balance"}
            
            # Create payment transaction
            transaction = await self._create_transaction(
                transaction_type=TransactionType.PAYMENT,
                currency_type=currency_type,
                amount=amount,
                sender_id=payer_id,
                recipient_id=payee_id,
                description=description or f"Payment for service {service_id}",
                reference_id=service_id
            )
            
            # Queue for processing
            await self.processing_queue.put(transaction.transaction_id)
            
            result = {
                "success": True,
                "transaction_id": transaction.transaction_id,
                "service_id": service_id,
                "amount_charged": total_cost,
                "status": transaction.status.value
            }
            
            self.logger.info(f"Payment processed: {amount} {currency_type.value} for service {service_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process payment: {e}")
            return {"success": False, "error": str(e)}
    
    async def mine_currency(
        self,
        agent_id: str,
        currency_type: CurrencyType,
        work_hours: float,
        work_quality: float = 1.0
    ) -> Dict[str, Any]:
        """Mine currency through work performed by an agent."""
        try:
            if agent_id not in self.wallets:
                return {"success": False, "error": "Wallet not found"}
            
            # Calculate mining reward
            base_rate = self.mining_rates[currency_type]
            quality_multiplier = max(0.1, min(2.0, work_quality))
            mined_amount = base_rate * work_hours * quality_multiplier
            
            # Apply daily mining limit
            daily_limit = self.config["daily_mining_limit"]
            mined_amount = min(mined_amount, daily_limit)
            
            if mined_amount <= 0:
                return {"success": False, "error": "No currency mined"}
            
            # Create mining transaction
            transaction = await self._create_transaction(
                transaction_type=TransactionType.MINING,
                currency_type=currency_type,
                amount=mined_amount,
                sender_id="system",
                recipient_id=agent_id,
                description=f"Mining reward for {work_hours} hours of work",
                metadata={
                    "work_hours": work_hours,
                    "work_quality": work_quality,
                    "base_rate": base_rate
                }
            )
            
            # Process immediately (no fees for mining)
            transaction.transaction_fee = 0.0
            await self._process_transaction(transaction.transaction_id)
            
            result = {
                "success": True,
                "transaction_id": transaction.transaction_id,
                "amount_mined": mined_amount,
                "currency_type": currency_type.value,
                "work_hours": work_hours,
                "quality_multiplier": quality_multiplier
            }
            
            self.logger.info(f"Mined {mined_amount} {currency_type.value} for agent {agent_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to mine currency: {e}")
            return {"success": False, "error": str(e)}
    
    async def exchange_currency(
        self,
        agent_id: str,
        from_currency: CurrencyType,
        to_currency: CurrencyType,
        amount: float
    ) -> Dict[str, Any]:
        """Exchange one currency type for another."""
        try:
            if agent_id not in self.wallets:
                return {"success": False, "error": "Wallet not found"}
            
            wallet = self.wallets[agent_id]
            
            # Check sufficient balance
            exchange_fee = amount * self.config["exchange_fee_rate"]
            total_cost = amount + exchange_fee
            
            if not wallet.has_sufficient_balance(from_currency, total_cost):
                return {"success": False, "error": "Insufficient balance"}
            
            # Calculate exchange amount
            from_rate = self.exchange_rates[from_currency]
            to_rate = self.exchange_rates[to_currency]
            exchange_rate = from_rate / to_rate
            received_amount = amount * exchange_rate
            
            # Create exchange transactions
            debit_transaction = await self._create_transaction(
                transaction_type=TransactionType.EXCHANGE,
                currency_type=from_currency,
                amount=total_cost,
                sender_id=agent_id,
                recipient_id="system",
                description=f"Currency exchange: {from_currency.value} to {to_currency.value}"
            )
            
            credit_transaction = await self._create_transaction(
                transaction_type=TransactionType.EXCHANGE,
                currency_type=to_currency,
                amount=received_amount,
                sender_id="system",
                recipient_id=agent_id,
                description=f"Currency exchange: {from_currency.value} to {to_currency.value}"
            )
            
            # Process both transactions
            await self._process_transaction(debit_transaction.transaction_id)
            await self._process_transaction(credit_transaction.transaction_id)
            
            result = {
                "success": True,
                "from_currency": from_currency.value,
                "to_currency": to_currency.value,
                "amount_exchanged": amount,
                "amount_received": received_amount,
                "exchange_rate": exchange_rate,
                "exchange_fee": exchange_fee,
                "debit_transaction_id": debit_transaction.transaction_id,
                "credit_transaction_id": credit_transaction.transaction_id
            }
            
            self.logger.info(f"Currency exchange: {amount} {from_currency.value} -> {received_amount} {to_currency.value}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to exchange currency: {e}")
            return {"success": False, "error": str(e)}"    

    def get_wallet_info(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed wallet information for an agent."""
        try:
            if agent_id not in self.wallets:
                return {"error": "Wallet not found"}
            
            wallet = self.wallets[agent_id]
            
            # Calculate total value
            total_value = wallet.get_total_value(self.exchange_rates)
            
            # Get recent transactions
            recent_transactions = []
            for transaction_id in wallet.transaction_history[-10:]:  # Last 10 transactions
                if transaction_id in self.transactions:
                    transaction = self.transactions[transaction_id]
                    recent_transactions.append({
                        "transaction_id": transaction.transaction_id,
                        "type": transaction.transaction_type.value,
                        "currency": transaction.currency_type.value,
                        "amount": transaction.amount,
                        "status": transaction.status.value,
                        "created_at": transaction.created_at.isoformat(),
                        "description": transaction.description
                    })
            
            return {
                "agent_id": agent_id,
                "wallet_address": wallet.wallet_address,
                "balances": {currency.value: balance for currency, balance in wallet.balances.items()},
                "total_value_nc": total_value,  # In neural credits equivalent
                "total_earned": {currency.value: earned for currency, earned in wallet.total_earned.items()},
                "total_spent": {currency.value: spent for currency, spent in wallet.total_spent.items()},
                "daily_limits": {currency.value: limit for currency, limit in wallet.daily_spending_limit.items()},
                "preferred_currency": wallet.preferred_currency.value,
                "recent_transactions": recent_transactions,
                "wallet_age_days": (datetime.now() - wallet.created_at).days,
                "last_activity": wallet.last_activity.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get wallet info: {e}")
            return {"error": str(e)}
    
    def get_transaction_info(self, transaction_id: str) -> Dict[str, Any]:
        """Get detailed information about a transaction."""
        try:
            if transaction_id not in self.transactions:
                return {"error": "Transaction not found"}
            
            transaction = self.transactions[transaction_id]
            
            return {
                "transaction_id": transaction.transaction_id,
                "type": transaction.transaction_type.value,
                "currency": transaction.currency_type.value,
                "amount": transaction.amount,
                "sender_id": transaction.sender_id,
                "recipient_id": transaction.recipient_id,
                "description": transaction.description,
                "reference_id": transaction.reference_id,
                "status": transaction.status.value,
                "created_at": transaction.created_at.isoformat(),
                "processed_at": transaction.processed_at.isoformat() if transaction.processed_at else None,
                "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None,
                "transaction_fee": transaction.transaction_fee,
                "gas_fee": transaction.gas_fee,
                "validation_hash": transaction.validation_hash,
                "metadata": transaction.metadata,
                "error_message": transaction.error_message,
                "retry_count": transaction.retry_count,
                "is_valid": transaction.is_valid()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get transaction info: {e}")
            return {"error": str(e)}
    
    def get_economic_stats(self) -> Dict[str, Any]:
        """Get economic system statistics."""
        try:
            # Calculate additional metrics
            active_transactions = len([t for t in self.transactions.values() if t.status == TransactionStatus.PROCESSING])
            failed_rate = (self.stats["failed_transactions"] / max(1, self.stats["total_transactions"])) * 100.0
            
            # Currency distribution
            currency_distribution = {}
            for currency in CurrencyType:
                total_in_wallets = sum(
                    wallet.get_balance(currency) 
                    for wallet in self.wallets.values()
                )
                currency_distribution[currency.value] = {
                    "in_circulation": self.stats["currency_in_circulation"][currency.value],
                    "in_wallets": total_in_wallets,
                    "exchange_rate": self.exchange_rates[currency]
                }
            
            return {
                "total_transactions": self.stats["total_transactions"],
                "active_transactions": active_transactions,
                "failed_transactions": self.stats["failed_transactions"],
                "failure_rate_percent": failed_rate,
                "active_wallets": self.stats["active_wallets"],
                "average_transaction_time_minutes": self.stats["average_transaction_time"],
                "total_volume": self.stats["total_volume"],
                "currency_distribution": currency_distribution,
                "exchange_rates": {currency.value: rate for currency, rate in self.exchange_rates.items()},
                "mining_rates": {currency.value: rate for currency, rate in self.mining_rates.items()},
                "system_health": "healthy" if failed_rate < 5.0 else "degraded"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get economic stats: {e}")
            return {"error": str(e)}
    
    def get_agent_transaction_history(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history for an agent."""
        try:
            if agent_id not in self.wallets:
                return []
            
            wallet = self.wallets[agent_id]
            transactions = []
            
            # Get recent transactions
            for transaction_id in wallet.transaction_history[-limit:]:
                if transaction_id in self.transactions:
                    transaction = self.transactions[transaction_id]
                    transactions.append({
                        "transaction_id": transaction.transaction_id,
                        "type": transaction.transaction_type.value,
                        "currency": transaction.currency_type.value,
                        "amount": transaction.amount,
                        "sender_id": transaction.sender_id,
                        "recipient_id": transaction.recipient_id,
                        "description": transaction.description,
                        "status": transaction.status.value,
                        "created_at": transaction.created_at.isoformat(),
                        "is_incoming": transaction.recipient_id == agent_id,
                        "net_amount": transaction.amount if transaction.recipient_id == agent_id else -transaction.amount
                    })
            
            # Sort by creation time (most recent first)
            transactions.sort(key=lambda t: t["created_at"], reverse=True)
            
            return transactions
            
        except Exception as e:
            self.logger.error(f"Failed to get transaction history: {e}")
            return []
    
    # Private helper methods
    
    async def _create_transaction(
        self,
        transaction_type: TransactionType,
        currency_type: CurrencyType,
        amount: float,
        sender_id: str,
        recipient_id: str,
        description: str = "",
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Transaction:
        """Create a new transaction."""
        self.transaction_counter += 1
        transaction_id = f"tx_{self.transaction_counter}_{datetime.now().timestamp()}"
        
        transaction = Transaction(
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            currency_type=currency_type,
            amount=amount,
            sender_id=sender_id,
            recipient_id=recipient_id,
            description=description,
            reference_id=reference_id,
            metadata=metadata or {}
        )
        
        # Calculate fees
        transaction.transaction_fee = self._calculate_transaction_fee(amount, currency_type)
        transaction.gas_fee = self._calculate_gas_fee(transaction)
        
        # Generate validation hash
        transaction.validation_hash = transaction.generate_hash()
        
        # Store transaction
        self.transactions[transaction_id] = transaction
        self.pending_transactions.add(transaction_id)
        
        return transaction
    
    def _calculate_transaction_fee(self, amount: float, currency_type: CurrencyType) -> float:
        """Calculate transaction fee based on amount and currency type."""
        base_fee = self.config["base_transaction_fee"]
        currency_multiplier = self.exchange_rates[currency_type]
        return base_fee * currency_multiplier * (1 + amount / 1000.0)
    
    def _calculate_gas_fee(self, transaction: Transaction) -> float:
        """Calculate gas fee for transaction processing."""
        base_gas = self.config["gas_fee_multiplier"]
        complexity_factor = 1.0
        
        # More complex transactions cost more gas
        if transaction.transaction_type in [TransactionType.EXCHANGE, TransactionType.ESCROW]:
            complexity_factor = 2.0
        elif transaction.metadata:
            complexity_factor = 1.5
        
        return base_gas * transaction.amount * complexity_factor
    
    async def _process_transaction(self, transaction_id: str) -> bool:
        """Process a single transaction."""
        try:
            if transaction_id not in self.transactions:
                return False
            
            transaction = self.transactions[transaction_id]
            
            # Validate transaction
            if not transaction.is_valid():
                transaction.status = TransactionStatus.FAILED
                transaction.error_message = "Transaction validation failed"
                return False
            
            transaction.status = TransactionStatus.PROCESSING
            transaction.processed_at = datetime.now()
            
            # Process based on transaction type
            if transaction.transaction_type == TransactionType.TRANSFER:
                success = await self._process_transfer(transaction)
            elif transaction.transaction_type == TransactionType.PAYMENT:
                success = await self._process_payment(transaction)
            elif transaction.transaction_type == TransactionType.MINING:
                success = await self._process_mining(transaction)
            elif transaction.transaction_type == TransactionType.EXCHANGE:
                success = await self._process_exchange(transaction)
            else:
                success = await self._process_generic_transaction(transaction)
            
            if success:
                transaction.status = TransactionStatus.COMPLETED
                transaction.completed_at = datetime.now()
                
                # Update statistics
                self.stats["total_transactions"] += 1
                self.stats["total_volume"][transaction.currency_type.value] += transaction.amount
                
                # Calculate average processing time
                if transaction.processed_at and transaction.completed_at:
                    processing_time = (transaction.completed_at - transaction.processed_at).total_seconds() / 60.0
                    current_avg = self.stats["average_transaction_time"]
                    total_tx = self.stats["total_transactions"]
                    self.stats["average_transaction_time"] = ((current_avg * (total_tx - 1)) + processing_time) / total_tx
            else:
                transaction.status = TransactionStatus.FAILED
                self.stats["failed_transactions"] += 1
            
            # Remove from pending
            self.pending_transactions.discard(transaction_id)
            
            # Add to wallet histories
            if transaction.sender_id in self.wallets:
                self.wallets[transaction.sender_id].add_transaction(transaction_id)
            if transaction.recipient_id in self.wallets:
                self.wallets[transaction.recipient_id].add_transaction(transaction_id)
            
            log_agent_event(
                self.agent_id,
                "transaction_processed",
                {
                    "transaction_id": transaction_id,
                    "status": transaction.status.value,
                    "amount": transaction.amount,
                    "currency": transaction.currency_type.value
                }
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error processing transaction {transaction_id}: {e}")
            if transaction_id in self.transactions:
                self.transactions[transaction_id].status = TransactionStatus.FAILED
                self.transactions[transaction_id].error_message = str(e)
            return False
    
    async def _process_transfer(self, transaction: Transaction) -> bool:
        """Process a transfer transaction."""
        try:
            sender_wallet = self.wallets[transaction.sender_id]
            recipient_wallet = self.wallets[transaction.recipient_id]
            
            total_cost = transaction.amount + transaction.transaction_fee
            
            # Check balance again (double-check)
            if not sender_wallet.has_sufficient_balance(transaction.currency_type, total_cost):
                transaction.error_message = "Insufficient balance at processing time"
                return False
            
            # Perform transfer
            sender_wallet.balances[transaction.currency_type] -= total_cost
            recipient_wallet.balances[transaction.currency_type] = recipient_wallet.balances.get(transaction.currency_type, 0) + transaction.amount
            
            # Update spending/earning totals
            sender_wallet.total_spent[transaction.currency_type] = sender_wallet.total_spent.get(transaction.currency_type, 0) + total_cost
            recipient_wallet.total_earned[transaction.currency_type] = recipient_wallet.total_earned.get(transaction.currency_type, 0) + transaction.amount
            
            return True
            
        except Exception as e:
            transaction.error_message = f"Transfer processing error: {e}"
            return False
    
    async def _process_payment(self, transaction: Transaction) -> bool:
        """Process a payment transaction."""
        # Payment processing is similar to transfer but with additional validation
        return await self._process_transfer(transaction)
    
    async def _process_mining(self, transaction: Transaction) -> bool:
        """Process a mining transaction."""
        try:
            recipient_wallet = self.wallets[transaction.recipient_id]
            
            # Add mined currency
            recipient_wallet.balances[transaction.currency_type] = recipient_wallet.balances.get(transaction.currency_type, 0) + transaction.amount
            recipient_wallet.total_earned[transaction.currency_type] = recipient_wallet.total_earned.get(transaction.currency_type, 0) + transaction.amount
            
            # Update circulation
            self.stats["currency_in_circulation"][transaction.currency_type.value] += transaction.amount
            
            return True
            
        except Exception as e:
            transaction.error_message = f"Mining processing error: {e}"
            return False
    
    async def _process_exchange(self, transaction: Transaction) -> bool:
        """Process a currency exchange transaction."""
        try:
            if transaction.sender_id == "system":
                # Credit transaction
                recipient_wallet = self.wallets[transaction.recipient_id]
                recipient_wallet.balances[transaction.currency_type] = recipient_wallet.balances.get(transaction.currency_type, 0) + transaction.amount
                recipient_wallet.total_earned[transaction.currency_type] = recipient_wallet.total_earned.get(transaction.currency_type, 0) + transaction.amount
            else:
                # Debit transaction
                sender_wallet = self.wallets[transaction.sender_id]
                if not sender_wallet.has_sufficient_balance(transaction.currency_type, transaction.amount):
                    transaction.error_message = "Insufficient balance for exchange"
                    return False
                
                sender_wallet.balances[transaction.currency_type] -= transaction.amount
                sender_wallet.total_spent[transaction.currency_type] = sender_wallet.total_spent.get(transaction.currency_type, 0) + transaction.amount
            
            return True
            
        except Exception as e:
            transaction.error_message = f"Exchange processing error: {e}"
            return False
    
    async def _process_generic_transaction(self, transaction: Transaction) -> bool:
        """Process other types of transactions."""
        try:
            # Handle rewards, penalties, refunds, etc.
            if transaction.transaction_type == TransactionType.REWARD:
                recipient_wallet = self.wallets[transaction.recipient_id]
                recipient_wallet.balances[transaction.currency_type] = recipient_wallet.balances.get(transaction.currency_type, 0) + transaction.amount
                recipient_wallet.total_earned[transaction.currency_type] = recipient_wallet.total_earned.get(transaction.currency_type, 0) + transaction.amount
                self.stats["currency_in_circulation"][transaction.currency_type.value] += transaction.amount
                
            elif transaction.transaction_type == TransactionType.PENALTY:
                sender_wallet = self.wallets[transaction.sender_id]
                if sender_wallet.has_sufficient_balance(transaction.currency_type, transaction.amount):
                    sender_wallet.balances[transaction.currency_type] -= transaction.amount
                    sender_wallet.total_spent[transaction.currency_type] = sender_wallet.total_spent.get(transaction.currency_type, 0) + transaction.amount
                    self.stats["currency_in_circulation"][transaction.currency_type.value] -= transaction.amount
                else:
                    transaction.error_message = "Insufficient balance for penalty"
                    return False
            
            elif transaction.transaction_type == TransactionType.REFUND:
                return await self._process_transfer(transaction)
            
            return True
            
        except Exception as e:
            transaction.error_message = f"Generic transaction processing error: {e}"
            return False
    
    async def _transaction_processor(self) -> None:
        """Background task to process transactions."""
        while True:
            try:
                # Get transaction from queue
                transaction_id = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)
                
                # Process the transaction
                await self._process_transaction(transaction_id)
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except asyncio.TimeoutError:
                # No transactions to process, continue
                continue
            except Exception as e:
                self.logger.error(f"Error in transaction processor: {e}")
                await asyncio.sleep(1)
    
    async def _economic_updater(self) -> None:
        """Background task to update economic conditions."""
        while True:
            try:
                await asyncio.sleep(3600)  # Update every hour
                
                # Update exchange rates based on supply/demand (simplified)
                await self._update_exchange_rates()
                
                # Apply inflation
                await self._apply_inflation()
                
                # Update mining difficulty
                await self._update_mining_rates()
                
            except Exception as e:
                self.logger.error(f"Error in economic updater: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_processor(self) -> None:
        """Background task to clean up old transactions and data."""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily
                
                # Clean up old completed transactions (keep for 30 days)
                cutoff_date = datetime.now() - timedelta(days=30)
                old_transactions = [
                    tx_id for tx_id, tx in self.transactions.items()
                    if tx.completed_at and tx.completed_at < cutoff_date
                ]
                
                for tx_id in old_transactions:
                    del self.transactions[tx_id]
                
                # Clean up failed transactions (keep for 7 days)
                failed_cutoff = datetime.now() - timedelta(days=7)
                failed_transactions = [
                    tx_id for tx_id, tx in self.transactions.items()
                    if tx.status == TransactionStatus.FAILED and tx.created_at < failed_cutoff
                ]
                
                for tx_id in failed_transactions:
                    del self.transactions[tx_id]
                
                self.logger.info(f"Cleaned up {len(old_transactions)} old and {len(failed_transactions)} failed transactions")
                
            except Exception as e:
                self.logger.error(f"Error in cleanup processor: {e}")
                await asyncio.sleep(3600)
    
    async def _update_exchange_rates(self) -> None:
        """Update currency exchange rates based on market conditions."""
        try:
            # Simple supply/demand model
            for currency in CurrencyType:
                if currency == CurrencyType.NEURAL_CREDITS:
                    continue  # Base currency
                
                # Calculate supply (total in circulation)
                supply = self.stats["currency_in_circulation"][currency.value]
                
                # Calculate demand (transaction volume)
                demand = self.stats["total_volume"][currency.value]
                
                # Update rate based on supply/demand ratio
                if supply > 0 and demand > 0:
                    supply_demand_ratio = demand / supply
                    rate_adjustment = 1.0 + (supply_demand_ratio - 1.0) * 0.1  # 10% max adjustment
                    self.exchange_rates[currency] *= rate_adjustment
                    
                    # Keep rates within reasonable bounds
                    self.exchange_rates[currency] = max(0.1, min(10.0, self.exchange_rates[currency]))
            
        except Exception as e:
            self.logger.error(f"Error updating exchange rates: {e}")
    
    async def _apply_inflation(self) -> None:
        """Apply inflation to the currency system."""
        try:
            inflation_rate = self.config["inflation_rate"]
            
            # Reduce all balances slightly
            for wallet in self.wallets.values():
                for currency_type in wallet.balances:
                    wallet.balances[currency_type] *= (1 - inflation_rate)
            
            # Reduce circulation
            for currency in CurrencyType:
                self.stats["currency_in_circulation"][currency.value] *= (1 - inflation_rate)
            
        except Exception as e:
            self.logger.error(f"Error applying inflation: {e}")
    
    async def _update_mining_rates(self) -> None:
        """Update mining rates based on economic conditions."""
        try:
            # Adjust mining rates based on circulation
            for currency in CurrencyType:
                circulation = self.stats["currency_in_circulation"][currency.value]
                
                # Reduce mining rate if too much currency in circulation
                if circulation > 10000:  # Arbitrary threshold
                    self.mining_rates[currency] *= 0.99
                elif circulation < 1000:
                    self.mining_rates[currency] *= 1.01
                
                # Keep mining rates within bounds
                self.mining_rates[currency] = max(0.1, min(20.0, self.mining_rates[currency]))
            
        except Exception as e:
            self.logger.error(f"Error updating mining rates: {e}")
    
    async def _save_system_state(self) -> None:
        """Save the current system state."""
        try:
            # In a real implementation, this would save to persistent storage
            self.logger.info(f"Saved state for {len(self.wallets)} wallets and {len(self.transactions)} transactions")
        except Exception as e:
            self.logger.error(f"Error saving system state: {e}")