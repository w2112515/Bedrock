"""
Chain Data Interface

Abstract interface for blockchain data providers.
Ensures pluggability and vendor independence.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class ChainDataInterface(ABC):
    """
    Abstract interface for blockchain data providers.
    
    This interface defines the contract for fetching on-chain data from various
    blockchain data providers (Bitquery, The Graph, etc.).
    
    Design Principle: Interface Segregation & Pluggability
    - Easy to swap implementations
    - Testability (mock interfaces)
    - Vendor independence
    """
    
    @abstractmethod
    def get_large_transfers(
        self,
        symbol: str,
        network: str = "eth",
        min_amount: float = 100.0,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get large transfers (whale movements).
        
        Args:
            symbol: Token symbol (e.g., "BTC", "ETH")
            network: Blockchain network (e.g., "eth", "bsc")
            min_amount: Minimum transfer amount to filter (default: 100.0)
            start_time: Start time for data collection
            end_time: End time for data collection
            limit: Maximum number of transfers to fetch
        
        Returns:
            List of large transfer data with structure:
            [
                {
                    "timestamp": 1699488000,
                    "from_address": "0x123...",
                    "to_address": "0x456...",
                    "amount": 1000.0,
                    "amount_usd": 50000.0,
                    "token_symbol": "BTC",
                    "token_address": "0xabc...",
                    "transaction_hash": "0xdef...",
                    "block_number": 12345678
                }
            ]
        """
        pass
    
    @abstractmethod
    def get_smart_money_activity(
        self,
        symbol: str,
        network: str = "eth",
        addresses: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get smart money (known whale/institutional) activity.
        
        Args:
            symbol: Token symbol (e.g., "BTC", "ETH")
            network: Blockchain network (e.g., "eth", "bsc")
            addresses: List of known smart money addresses to track
            start_time: Start time for data collection
            end_time: End time for data collection
            limit: Maximum number of activities to fetch
        
        Returns:
            List of smart money activity data with structure:
            [
                {
                    "timestamp": 1699488000,
                    "address": "0x123...",
                    "action": "buy" | "sell" | "transfer",
                    "amount": 100.0,
                    "amount_usd": 5000.0,
                    "token_symbol": "BTC",
                    "token_address": "0xabc...",
                    "transaction_hash": "0xdef...",
                    "dex_protocol": "uniswap_v3" (if applicable)
                }
            ]
        """
        pass
    
    @abstractmethod
    def get_exchange_netflow(
        self,
        symbol: str,
        network: str = "eth",
        exchange_addresses: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get exchange net flow (inflow - outflow).
        
        Args:
            symbol: Token symbol (e.g., "BTC", "ETH")
            network: Blockchain network (e.g., "eth", "bsc")
            exchange_addresses: List of known exchange addresses
            start_time: Start time for data collection
            end_time: End time for data collection
        
        Returns:
            Exchange net flow data with structure:
            {
                "symbol": "BTC",
                "network": "eth",
                "time_range": {
                    "start": 1699488000,
                    "end": 1699574400
                },
                "inflow": 1000.0,
                "outflow": 800.0,
                "netflow": 200.0,  # positive = net inflow, negative = net outflow
                "inflow_usd": 50000.0,
                "outflow_usd": 40000.0,
                "netflow_usd": 10000.0,
                "transaction_count": 150,
                "unique_addresses": 75
            }
        """
        pass
    
    @abstractmethod
    def get_active_addresses(
        self,
        symbol: str,
        network: str = "eth",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get active addresses count and statistics.
        
        Args:
            symbol: Token symbol (e.g., "BTC", "ETH")
            network: Blockchain network (e.g., "eth", "bsc")
            start_time: Start time for data collection
            end_time: End time for data collection
        
        Returns:
            Active addresses data with structure:
            {
                "symbol": "BTC",
                "network": "eth",
                "time_range": {
                    "start": 1699488000,
                    "end": 1699574400
                },
                "active_addresses": 12345,
                "new_addresses": 567,
                "sending_addresses": 8000,
                "receiving_addresses": 9000,
                "transaction_count": 25000,
                "average_transaction_value": 0.5,
                "average_transaction_value_usd": 25000.0
            }
        """
        pass
    
    @abstractmethod
    def get_dex_trades(
        self,
        network: str = "eth",
        token_address: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get DEX trade data.
        
        Args:
            network: Blockchain network (default: "eth")
            token_address: Token contract address (optional)
            start_time: Start time for data collection
            end_time: End time for data collection
            limit: Maximum number of trades to fetch
        
        Returns:
            List of DEX trade data
        """
        pass
    
    @abstractmethod
    def get_token_transfers(
        self,
        network: str = "eth",
        token_address: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get token transfer data.
        
        Args:
            network: Blockchain network (default: "eth")
            token_address: Token contract address
            start_time: Start time for data collection
            end_time: End time for data collection
            limit: Maximum number of transfers to fetch
        
        Returns:
            List of token transfer data
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test connection to the blockchain data provider.
        
        Returns:
            True if connection is successful, False otherwise
        """
        pass

