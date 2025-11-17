"""
On-Chain Data Collection Service

Business logic for collecting and managing on-chain metrics data.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from shared.utils.logger import setup_logging
from shared.utils.redis_client import get_redis_client, publish_event
from services.datahub.app.models.onchain import OnChainMetrics
from services.datahub.app.adapters.chain_data_interface import ChainDataInterface

logger = setup_logging("onchain_service")


class OnChainService:
    """
    Service for managing on-chain data collection and storage.
    
    Responsibilities:
    - Collect on-chain metrics from blockchain data providers
    - Store metrics in database with upsert logic
    - Query metrics with filters
    - Publish events to Redis for downstream services
    """
    
    def __init__(self, db: Session, chain_adapter: ChainDataInterface):
        """
        Initialize OnChainService.
        
        Args:
            db: Database session
            chain_adapter: Chain data adapter (e.g., BitqueryAdapter)
        """
        self.db = db
        self.chain_adapter = chain_adapter
        self.redis_client = get_redis_client()
    
    def collect_large_transfers(
        self,
        symbol: str,
        network: str = "eth",
        min_amount: float = 100.0,
        hours: int = 24,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Collect large transfer data and store in database.
        
        Args:
            symbol: Token symbol (e.g., "BTC", "ETH")
            network: Blockchain network (e.g., "eth", "bsc")
            min_amount: Minimum transfer amount
            hours: Hours of historical data to collect
            limit: Maximum number of transfers to fetch
        
        Returns:
            Collection result with count and sample data
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            logger.info(f"Collecting large transfers for {symbol} on {network} (last {hours}h)")
            
            # Fetch data from chain adapter
            transfers = self.chain_adapter.get_large_transfers(
                symbol=symbol,
                network=network,
                min_amount=min_amount,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            
            # Store in database
            stored_count = 0
            for transfer in transfers:
                # FIXED: Use correct field names from OnChainMetrics model
                # FIXED: timestamp should be Unix timestamp (int), not datetime
                metrics = OnChainMetrics(
                    symbol=symbol,
                    network=network,
                    contract_address=transfer.get("token_address"),
                    timestamp=transfer["timestamp"],  # Already Unix timestamp (int)
                    transaction_count=1,
                    transaction_volume=transfer["amount"],
                    transaction_volume_usd=transfer.get("amount_usd"),
                    additional_metrics={
                        "type": "large_transfer",
                        "from_address": transfer["from_address"],
                        "to_address": transfer["to_address"],
                        "transaction_hash": transfer["transaction_hash"],
                        "block_number": transfer["block_number"]
                    }
                )
                
                # Upsert logic: check if record exists
                # FIXED: Use proper JSON query syntax with cast
                from sqlalchemy import cast, String
                existing = self.db.query(OnChainMetrics).filter(
                    and_(
                        OnChainMetrics.symbol == symbol,
                        OnChainMetrics.network == network,
                        cast(OnChainMetrics.additional_metrics['transaction_hash'], String) == transfer["transaction_hash"]
                    )
                ).first()
                
                if not existing:
                    self.db.add(metrics)
                    stored_count += 1
            
            self.db.commit()
            
            # Invalidate Redis cache
            cache_key = f"onchain:large_transfers:{symbol}:{network}"
            self.redis_client.delete(cache_key)
            
            # Publish event
            publish_event("onchain.large_transfers.collected", {
                "symbol": symbol,
                "network": network,
                "count": stored_count,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Successfully stored {stored_count} large transfers for {symbol}")
            
            return {
                "symbol": symbol,
                "network": network,
                "collected_count": len(transfers),
                "stored_count": stored_count,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "sample_data": transfers[:5] if transfers else []
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error collecting large transfers: {e}")
            raise
    
    def collect_smart_money_activity(
        self,
        symbol: str,
        network: str = "eth",
        addresses: Optional[List[str]] = None,
        hours: int = 24,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Collect smart money activity data and store in database.
        
        Args:
            symbol: Token symbol
            network: Blockchain network
            addresses: List of smart money addresses to track
            hours: Hours of historical data to collect
            limit: Maximum number of activities to fetch
        
        Returns:
            Collection result
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            logger.info(f"Collecting smart money activity for {symbol} on {network}")
            
            # Fetch data from chain adapter
            activities = self.chain_adapter.get_smart_money_activity(
                symbol=symbol,
                network=network,
                addresses=addresses,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            
            # Store in database
            stored_count = 0
            for activity in activities:
                # FIXED: Use correct field names and timestamp format
                metrics = OnChainMetrics(
                    symbol=symbol,
                    network=network,
                    contract_address=activity.get("token_address"),
                    timestamp=activity["timestamp"],  # Already Unix timestamp (int)
                    transaction_count=1,
                    transaction_volume=activity["amount"],
                    transaction_volume_usd=activity.get("amount_usd"),
                    dex_volume_usd=activity.get("amount_usd"),  # Use DEX metrics instead
                    dex_trade_count=1,
                    additional_metrics={
                        "type": "smart_money_activity",
                        "address": activity["address"],
                        "action": activity["action"],
                        "transaction_hash": activity["transaction_hash"],
                        "dex_protocol": activity.get("dex_protocol")
                    }
                )
                
                # Upsert logic
                # FIXED: Use proper JSON query syntax with cast
                from sqlalchemy import cast, String
                existing = self.db.query(OnChainMetrics).filter(
                    and_(
                        OnChainMetrics.symbol == symbol,
                        OnChainMetrics.network == network,
                        cast(OnChainMetrics.additional_metrics['transaction_hash'], String) == activity["transaction_hash"]
                    )
                ).first()
                
                if not existing:
                    self.db.add(metrics)
                    stored_count += 1
            
            self.db.commit()
            
            # Invalidate cache
            cache_key = f"onchain:smart_money:{symbol}:{network}"
            self.redis_client.delete(cache_key)
            
            # Publish event
            publish_event("onchain.smart_money.collected", {
                "symbol": symbol,
                "network": network,
                "count": stored_count,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Successfully stored {stored_count} smart money activities")
            
            return {
                "symbol": symbol,
                "network": network,
                "collected_count": len(activities),
                "stored_count": stored_count,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "sample_data": activities[:5] if activities else []
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error collecting smart money activity: {e}")
            raise
    
    def collect_exchange_netflow(
        self,
        symbol: str,
        network: str = "eth",
        exchange_addresses: Optional[List[str]] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Collect exchange netflow data and store in database.
        
        Args:
            symbol: Token symbol
            network: Blockchain network
            exchange_addresses: List of exchange addresses
            hours: Hours of historical data to collect
        
        Returns:
            Collection result with netflow data
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            logger.info(f"Collecting exchange netflow for {symbol} on {network}")
            
            # Fetch data from chain adapter
            netflow_data = self.chain_adapter.get_exchange_netflow(
                symbol=symbol,
                network=network,
                exchange_addresses=exchange_addresses,
                start_time=start_time,
                end_time=end_time
            )
            
            # Store aggregated metrics
            # FIXED: Use correct field names and timestamp format
            metrics = OnChainMetrics(
                symbol=symbol,
                network=network,
                contract_address=None,  # Aggregated data
                timestamp=int(end_time.timestamp()),  # Convert to Unix timestamp
                transaction_count=netflow_data["transaction_count"],
                transaction_volume=netflow_data.get("inflow", 0) + netflow_data.get("outflow", 0),
                active_addresses=netflow_data.get("unique_addresses", 0),
                additional_metrics={
                    "type": "exchange_netflow",
                    "inflow": netflow_data.get("inflow", 0),
                    "outflow": netflow_data.get("outflow", 0),
                    "netflow": netflow_data.get("netflow", 0),
                    "time_range": netflow_data.get("time_range", {})
                }
            )
            
            self.db.add(metrics)
            self.db.commit()
            
            # Invalidate cache
            cache_key = f"onchain:netflow:{symbol}:{network}"
            self.redis_client.delete(cache_key)
            
            # Publish event
            publish_event("onchain.exchange_netflow.collected", {
                "symbol": symbol,
                "network": network,
                "netflow": netflow_data["netflow"],
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Successfully stored exchange netflow: {netflow_data['netflow']:.2f}")
            
            return {
                "symbol": symbol,
                "network": network,
                "netflow_data": netflow_data,
                "stored": True
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error collecting exchange netflow: {e}")
            raise

    def collect_active_addresses(
        self,
        symbol: str,
        network: str = "eth",
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Collect active addresses statistics and store in database.

        Args:
            symbol: Token symbol
            network: Blockchain network
            hours: Hours of historical data to collect

        Returns:
            Collection result with active addresses data
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            logger.info(f"Collecting active addresses for {symbol} on {network}")

            # Fetch data from chain adapter
            active_data = self.chain_adapter.get_active_addresses(
                symbol=symbol,
                network=network,
                start_time=start_time,
                end_time=end_time
            )

            # Store aggregated metrics
            # FIXED: Convert timestamp to Unix timestamp (int)
            metrics = OnChainMetrics(
                symbol=symbol,
                network=network,
                contract_address=None,  # Aggregated data
                timestamp=int(end_time.timestamp()),  # Convert to Unix timestamp
                transaction_count=active_data.get("transaction_count", 0),
                active_addresses=active_data.get("active_addresses", 0),
                new_addresses=active_data.get("new_addresses", 0),
                additional_metrics={
                    "type": "active_addresses",
                    "sending_addresses": active_data.get("sending_addresses", 0),
                    "receiving_addresses": active_data.get("receiving_addresses", 0),
                    "average_transaction_value": active_data.get("average_transaction_value", 0),
                    "time_range": active_data.get("time_range", {})
                }
            )

            self.db.add(metrics)
            self.db.commit()

            # Invalidate cache
            cache_key = f"onchain:active_addresses:{symbol}:{network}"
            self.redis_client.delete(cache_key)

            # Publish event
            publish_event("onchain.active_addresses.collected", {
                "symbol": symbol,
                "network": network,
                "active_addresses": active_data["active_addresses"],
                "timestamp": datetime.utcnow().isoformat()
            })

            logger.info(f"Successfully stored active addresses: {active_data['active_addresses']}")

            return {
                "symbol": symbol,
                "network": network,
                "active_data": active_data,
                "stored": True
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error collecting active addresses: {e}")
            raise

    def get_metrics(
        self,
        symbol: str,
        network: str = "eth",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[OnChainMetrics]:
        """
        Query on-chain metrics from database.

        Args:
            symbol: Token symbol
            network: Blockchain network
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of records

        Returns:
            List of OnChainMetrics records
        """
        try:
            query = self.db.query(OnChainMetrics).filter(
                OnChainMetrics.symbol == symbol,
                OnChainMetrics.network == network
            )

            if start_time:
                query = query.filter(OnChainMetrics.timestamp >= start_time)
            if end_time:
                query = query.filter(OnChainMetrics.timestamp <= end_time)

            metrics = query.order_by(desc(OnChainMetrics.timestamp)).limit(limit).all()

            logger.info(f"Retrieved {len(metrics)} on-chain metrics for {symbol}")
            return metrics

        except Exception as e:
            logger.error(f"Error querying on-chain metrics: {e}")
            raise

    def get_latest_metrics(
        self,
        symbol: str,
        network: str = "eth",
        metric_type: Optional[str] = None
    ) -> Optional[OnChainMetrics]:
        """
        Get the latest on-chain metrics for a symbol.

        Args:
            symbol: Token symbol
            network: Blockchain network
            metric_type: Filter by metric type (e.g., "exchange_netflow", "active_addresses")

        Returns:
            Latest OnChainMetrics record or None
        """
        try:
            query = self.db.query(OnChainMetrics).filter(
                OnChainMetrics.symbol == symbol,
                OnChainMetrics.network == network
            )

            if metric_type:
                query = query.filter(
                    OnChainMetrics.additional_metrics["type"].astext == metric_type
                )

            metrics = query.order_by(desc(OnChainMetrics.timestamp)).first()

            if metrics:
                logger.info(f"Retrieved latest on-chain metrics for {symbol}")
            else:
                logger.warning(f"No on-chain metrics found for {symbol}")

            return metrics

        except Exception as e:
            logger.error(f"Error querying latest on-chain metrics: {e}")
            raise

