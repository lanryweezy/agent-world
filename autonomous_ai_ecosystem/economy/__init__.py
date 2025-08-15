"""
Economic system module for autonomous AI ecosystem.

This module provides virtual currency, transaction processing,
service pricing, and economic interactions between agents.
"""

from .currency import (
    VirtualCurrency,
    Wallet,
    Transaction,
    TransactionType,
    TransactionStatus,
    CurrencyType,
    EconomicTransaction
)

from .marketplace import (
    ServiceMarketplace,
    ServiceCategory,
    ServiceStatus,
    ServiceListing,
    ServiceContract,
    ServiceCapability,
    ServiceReview,
    MarketplaceTransaction,
    ContractStatus,
    QualityRating
)

__all__ = [
    "VirtualCurrency",
    "Wallet",
    "Transaction",
    "TransactionType",
    "TransactionStatus",
    "CurrencyType",
    "EconomicTransaction",
    "ServiceMarketplace",
    "ServiceCategory",
    "ServiceStatus",
    "ServiceListing",
    "ServiceContract",
    "ServiceCapability",
    "ServiceReview",
    "MarketplaceTransaction",
    "ContractStatus",
    "QualityRating"
]