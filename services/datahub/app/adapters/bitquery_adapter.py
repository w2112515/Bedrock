"""
Bitquery API Adapter

Provides interface to fetch on-chain data from Bitquery Streaming API.
Implements ChainDataInterface for pluggability.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from shared.utils.logger import setup_logging
from .chain_data_interface import ChainDataInterface

# Load environment variables
load_dotenv()

logger = setup_logging("bitquery_adapter")


class BitqueryAdapter(ChainDataInterface):
    """
    Adapter for Bitquery Streaming API to fetch on-chain data.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize Bitquery adapter.
        
        Args:
            api_key: Bitquery API key (optional, defaults to env var)
            api_url: Bitquery API URL (optional, defaults to env var)
        """
        self.api_key = api_key or os.getenv("BITQUERY_API_KEY")
        self.api_url = api_url or os.getenv("BITQUERY_API_URL", "https://streaming.bitquery.io/graphql")
        
        if not self.api_key:
            logger.warning("Bitquery API key not configured")
        else:
            logger.info("Bitquery adapter initialized successfully")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=30))
    def _execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query against Bitquery API.
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
        
        Returns:
            Query response data
        
        Raises:
            ValueError: If API key is not configured
            httpx.HTTPError: If API request fails
        """
        if not self.api_key:
            raise ValueError("Bitquery API key not configured")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                if "errors" in data:
                    logger.error(f"Bitquery API errors: {data['errors']}")
                    raise ValueError(f"Bitquery API errors: {data['errors']}")
                
                return data.get("data", {})
                
        except httpx.HTTPError as e:
            logger.error(f"Bitquery API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing Bitquery query: {e}")
            raise
    
    def get_dex_trades(
        self,
        network: str = "eth",
        token_address: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get DEX trade data for a token.
        
        Args:
            network: Blockchain network (default: "eth")
            token_address: Token contract address (optional)
            limit: Maximum number of trades to fetch
        
        Returns:
            List of DEX trade data
        """
        query = """
        query GetDEXTrades($network: evm_network, $tokenAddress: String, $limit: Int) {
          EVM(network: $network) {
            DEXTrades(
              limit: {count: $limit}
              orderBy: {descending: Block_Time}
              where: {
                Trade: {
                  Buy: {
                    Currency: {
                      SmartContract: {is: $tokenAddress}
                    }
                  }
                }
              }
            ) {
              Block {
                Time
                Number
              }
              Transaction {
                Hash
              }
              Trade {
                Buy {
                  Amount
                  AmountInUSD
                  Price
                  PriceInUSD
                  Currency {
                    Name
                    Symbol
                    SmartContract
                  }
                }
                Sell {
                  Amount
                  AmountInUSD
                  Price
                  PriceInUSD
                  Currency {
                    Name
                    Symbol
                    SmartContract
                  }
                }
                Dex {
                  ProtocolName
                  ProtocolVersion
                  SmartContract
                }
              }
            }
          }
        }
        """
        
        variables = {
            "network": network,
            "tokenAddress": token_address,
            "limit": limit
        }
        
        try:
            logger.info(f"Fetching DEX trades for token {token_address} on {network}")
            data = self._execute_query(query, variables)
            
            trades = data.get("EVM", {}).get("DEXTrades", [])
            logger.info(f"Successfully fetched {len(trades)} DEX trades")
            
            return trades
            
        except Exception as e:
            logger.error(f"Error fetching DEX trades: {e}")
            raise
    
    def get_token_transfers(
        self,
        network: str = "eth",
        token_address: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get token transfer data.
        
        Args:
            network: Blockchain network (default: "eth")
            token_address: Token contract address
            limit: Maximum number of transfers to fetch
        
        Returns:
            List of token transfer data
        """
        query = """
        query GetTokenTransfers($network: evm_network, $tokenAddress: String, $limit: Int) {
          EVM(network: $network) {
            Transfers(
              limit: {count: $limit}
              orderBy: {descending: Block_Time}
              where: {
                Transfer: {
                  Currency: {
                    SmartContract: {is: $tokenAddress}
                  }
                }
              }
            ) {
              Block {
                Time
                Number
              }
              Transaction {
                Hash
              }
              Transfer {
                Amount
                Sender
                Receiver
                Currency {
                  Name
                  Symbol
                  SmartContract
                }
              }
            }
          }
        }
        """
        
        variables = {
            "network": network,
            "tokenAddress": token_address,
            "limit": limit
        }
        
        try:
            logger.info(f"Fetching token transfers for {token_address} on {network}")
            data = self._execute_query(query, variables)
            
            transfers = data.get("EVM", {}).get("Transfers", [])
            logger.info(f"Successfully fetched {len(transfers)} token transfers")
            
            return transfers
            
        except Exception as e:
            logger.error(f"Error fetching token transfers: {e}")
            raise
    
    def get_latest_blocks(
        self,
        network: str = "eth",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get latest blocks from blockchain.
        
        Args:
            network: Blockchain network (default: "eth")
            limit: Maximum number of blocks to fetch
        
        Returns:
            List of block data
        """
        query = """
        query GetLatestBlocks($network: evm_network, $limit: Int) {
          EVM(network: $network, dataset: archive) {
            Blocks(
              limit: {count: $limit}
              orderBy: {descending: Block_Number}
            ) {
              Block {
                Time
                Date
                Number
                Hash
              }
            }
          }
        }
        """
        
        variables = {
            "network": network,
            "limit": limit
        }
        
        try:
            logger.info(f"Fetching latest {limit} blocks from {network}")
            data = self._execute_query(query, variables)
            
            blocks = data.get("EVM", {}).get("Blocks", [])
            logger.info(f"Successfully fetched {len(blocks)} blocks")
            
            return blocks
            
        except Exception as e:
            logger.error(f"Error fetching latest blocks: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test connection to Bitquery API.

        Returns:
            True if connection is successful, False otherwise
        """
        if not self.api_key:
            return False

        try:
            # Simple query to test connection
            blocks = self.get_latest_blocks(limit=1)
            logger.info("Bitquery API connection test successful")
            return len(blocks) > 0
        except Exception as e:
            logger.error(f"Bitquery API connection test failed: {e}")
            return False

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
            List of large transfer data
        """
        # Default time range: last 24 hours
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)

        query = """
        query GetLargeTransfers(
            $network: evm_network,
            $minAmount: String,
            $startTime: DateTime,
            $endTime: DateTime,
            $limit: Int
        ) {
          EVM(network: $network) {
            Transfers(
              limit: {count: $limit}
              orderBy: {descending: Block_Time}
              where: {
                Transfer: {
                  Amount: {ge: $minAmount}
                }
                Block: {
                  Time: {since: $startTime, till: $endTime}
                }
              }
            ) {
              Block {
                Time
                Number
              }
              Transaction {
                Hash
              }
              Transfer {
                Amount
                Sender
                Receiver
                Currency {
                  Name
                  Symbol
                  SmartContract
                }
              }
            }
          }
        }
        """

        variables = {
            "network": network,
            "minAmount": str(min_amount),
            "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": limit
        }

        try:
            logger.info(f"Fetching large transfers (>{min_amount}) for {symbol} on {network}")
            data = self._execute_query(query, variables)

            transfers = data.get("EVM", {}).get("Transfers", [])

            # Transform to standard format
            result = []
            for transfer in transfers:
                result.append({
                    "timestamp": int(datetime.fromisoformat(transfer["Block"]["Time"].replace("Z", "+00:00")).timestamp()),
                    "from_address": transfer["Transfer"]["Sender"],
                    "to_address": transfer["Transfer"]["Receiver"],
                    "amount": float(transfer["Transfer"]["Amount"]),
                    "amount_usd": None,  # Would need price data to calculate
                    "token_symbol": transfer["Transfer"]["Currency"]["Symbol"],
                    "token_address": transfer["Transfer"]["Currency"]["SmartContract"],
                    "transaction_hash": transfer["Transaction"]["Hash"],
                    "block_number": int(transfer["Block"]["Number"])
                })

            logger.info(f"Successfully fetched {len(result)} large transfers")
            return result

        except Exception as e:
            logger.error(f"Error fetching large transfers: {e}")
            raise

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
            List of smart money activity data
        """
        # Default time range: last 24 hours
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)

        # If no addresses provided, use a default list of known smart money addresses
        if not addresses:
            # These are example addresses - in production, maintain a curated list
            addresses = [
                "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance Hot Wallet
                "0x21a31ee1afc51d94c2efccaa2092ad1028285549",  # Binance 14
                "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",  # Binance 15
            ]

        query = """
        query GetSmartMoneyActivity(
            $network: evm_network,
            $addresses: [String!],
            $startTime: DateTime,
            $endTime: DateTime,
            $limit: Int
        ) {
          EVM(network: $network) {
            DEXTrades(
              limit: {count: $limit}
              orderBy: {descending: Block_Time}
              where: {
                Trade: {
                  Sender: {in: $addresses}
                }
                Block: {
                  Time: {since: $startTime, till: $endTime}
                }
              }
            ) {
              Block {
                Time
                Number
              }
              Transaction {
                Hash
              }
              Trade {
                Sender
                Buy {
                  Amount
                  AmountInUSD
                  Currency {
                    Symbol
                    SmartContract
                  }
                }
                Sell {
                  Amount
                  AmountInUSD
                  Currency {
                    Symbol
                    SmartContract
                  }
                }
                Dex {
                  ProtocolName
                  ProtocolVersion
                }
              }
            }
          }
        }
        """

        variables = {
            "network": network,
            "addresses": addresses,
            "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": limit
        }

        try:
            logger.info(f"Fetching smart money activity for {len(addresses)} addresses on {network}")
            data = self._execute_query(query, variables)

            trades = data.get("EVM", {}).get("DEXTrades", [])

            # Transform to standard format
            result = []
            for trade in trades:
                # Determine action based on buy/sell
                buy_symbol = trade["Trade"]["Buy"]["Currency"]["Symbol"]
                sell_symbol = trade["Trade"]["Sell"]["Currency"]["Symbol"]

                # If buying the target symbol, it's a buy action
                action = "buy" if buy_symbol == symbol else "sell" if sell_symbol == symbol else "transfer"

                result.append({
                    "timestamp": int(datetime.fromisoformat(trade["Block"]["Time"].replace("Z", "+00:00")).timestamp()),
                    "address": trade["Trade"]["Sender"],
                    "action": action,
                    "amount": float(trade["Trade"]["Buy"]["Amount"]) if action == "buy" else float(trade["Trade"]["Sell"]["Amount"]),
                    "amount_usd": float(trade["Trade"]["Buy"]["AmountInUSD"] or 0) if action == "buy" else float(trade["Trade"]["Sell"]["AmountInUSD"] or 0),
                    "token_symbol": buy_symbol if action == "buy" else sell_symbol,
                    "token_address": trade["Trade"]["Buy"]["Currency"]["SmartContract"] if action == "buy" else trade["Trade"]["Sell"]["Currency"]["SmartContract"],
                    "transaction_hash": trade["Transaction"]["Hash"],
                    "dex_protocol": f"{trade['Trade']['Dex']['ProtocolName']}_{trade['Trade']['Dex']['ProtocolVersion']}" if trade["Trade"]["Dex"]["ProtocolVersion"] else trade["Trade"]["Dex"]["ProtocolName"]
                })

            logger.info(f"Successfully fetched {len(result)} smart money activities")
            return result

        except Exception as e:
            logger.error(f"Error fetching smart money activity: {e}")
            raise

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
            Exchange net flow data
        """
        # Default time range: last 24 hours
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)

        # If no addresses provided, use a default list of known exchange addresses
        if not exchange_addresses:
            # These are example addresses - in production, maintain a curated list
            exchange_addresses = [
                "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance Hot Wallet
                "0x21a31ee1afc51d94c2efccaa2092ad1028285549",  # Binance 14
                "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",  # Binance 15
                "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",  # Binance 16
            ]

        # Query for inflows (transfers TO exchange addresses)
        inflow_query = """
        query GetExchangeInflow(
            $network: evm_network,
            $addresses: [String!],
            $startTime: DateTime,
            $endTime: DateTime
        ) {
          EVM(network: $network) {
            Transfers(
              where: {
                Transfer: {
                  Receiver: {in: $addresses}
                }
                Block: {
                  Time: {since: $startTime, till: $endTime}
                }
              }
            ) {
              Transfer {
                Amount
                Currency {
                  Symbol
                }
              }
            }
          }
        }
        """

        # Query for outflows (transfers FROM exchange addresses)
        outflow_query = """
        query GetExchangeOutflow(
            $network: evm_network,
            $addresses: [String!],
            $startTime: DateTime,
            $endTime: DateTime
        ) {
          EVM(network: $network) {
            Transfers(
              where: {
                Transfer: {
                  Sender: {in: $addresses}
                }
                Block: {
                  Time: {since: $startTime, till: $endTime}
                }
              }
            ) {
              Transfer {
                Amount
                Sender
                Receiver
                Currency {
                  Symbol
                }
              }
            }
          }
        }
        """

        variables = {
            "network": network,
            "addresses": exchange_addresses,
            "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        try:
            logger.info(f"Fetching exchange netflow for {symbol} on {network}")

            # Fetch inflows
            inflow_data = self._execute_query(inflow_query, variables)
            inflows = inflow_data.get("EVM", {}).get("Transfers", [])

            # Fetch outflows
            outflow_data = self._execute_query(outflow_query, variables)
            outflows = outflow_data.get("EVM", {}).get("Transfers", [])

            # Calculate totals
            total_inflow = sum(float(t["Transfer"]["Amount"]) for t in inflows if t["Transfer"]["Currency"]["Symbol"] == symbol)
            total_outflow = sum(float(t["Transfer"]["Amount"]) for t in outflows if t["Transfer"]["Currency"]["Symbol"] == symbol)
            netflow = total_inflow - total_outflow

            # Count unique addresses
            unique_senders = set()
            unique_receivers = set()
            for t in outflows:
                if t["Transfer"]["Currency"]["Symbol"] == symbol:
                    unique_senders.add(t["Transfer"]["Sender"])
                    unique_receivers.add(t["Transfer"]["Receiver"])

            result = {
                "symbol": symbol,
                "network": network,
                "time_range": {
                    "start": int(start_time.timestamp()),
                    "end": int(end_time.timestamp())
                },
                "inflow": total_inflow,
                "outflow": total_outflow,
                "netflow": netflow,
                "inflow_usd": None,  # Would need price data
                "outflow_usd": None,
                "netflow_usd": None,
                "transaction_count": len(inflows) + len(outflows),
                "unique_addresses": len(unique_senders | unique_receivers)
            }

            logger.info(f"Successfully calculated exchange netflow: {netflow:.2f} {symbol}")
            return result

        except Exception as e:
            logger.error(f"Error fetching exchange netflow: {e}")
            raise

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
            Active addresses data
        """
        # Default time range: last 24 hours
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)

        query = """
        query GetActiveAddresses(
            $network: evm_network,
            $startTime: DateTime,
            $endTime: DateTime
        ) {
          EVM(network: $network) {
            Transfers(
              where: {
                Block: {
                  Time: {since: $startTime, till: $endTime}
                }
              }
            ) {
              Transfer {
                Amount
                Sender
                Receiver
                Currency {
                  Symbol
                }
              }
            }
          }
        }
        """

        variables = {
            "network": network,
            "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        try:
            logger.info(f"Fetching active addresses for {symbol} on {network}")
            data = self._execute_query(query, variables)

            transfers = data.get("EVM", {}).get("Transfers", [])

            # Filter transfers for the target symbol
            symbol_transfers = [t for t in transfers if t["Transfer"]["Currency"]["Symbol"] == symbol]

            # Calculate statistics
            sending_addresses = set()
            receiving_addresses = set()
            total_amount = 0.0

            for transfer in symbol_transfers:
                sender = transfer["Transfer"]["Sender"]
                receiver = transfer["Transfer"]["Receiver"]
                amount = float(transfer["Transfer"]["Amount"])

                sending_addresses.add(sender)
                receiving_addresses.add(receiver)
                total_amount += amount

            # Active addresses = unique senders + receivers
            active_addresses = sending_addresses | receiving_addresses

            # New addresses = addresses that appear for the first time (simplified: all receivers)
            new_addresses = receiving_addresses - sending_addresses

            # Calculate average transaction value
            transaction_count = len(symbol_transfers)
            avg_tx_value = total_amount / transaction_count if transaction_count > 0 else 0.0

            result = {
                "symbol": symbol,
                "network": network,
                "time_range": {
                    "start": int(start_time.timestamp()),
                    "end": int(end_time.timestamp())
                },
                "active_addresses": len(active_addresses),
                "new_addresses": len(new_addresses),
                "sending_addresses": len(sending_addresses),
                "receiving_addresses": len(receiving_addresses),
                "transaction_count": transaction_count,
                "average_transaction_value": avg_tx_value,
                "average_transaction_value_usd": None  # Would need price data
            }

            logger.info(f"Successfully fetched active addresses: {len(active_addresses)} for {symbol}")
            return result

        except Exception as e:
            logger.error(f"Error fetching active addresses: {e}")
            raise

