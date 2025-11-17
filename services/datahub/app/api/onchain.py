"""
On-Chain Data API Endpoints

Provides REST API for collecting and querying on-chain metrics.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from shared.utils.database import get_db
from shared.utils.logger import setup_logging
from services.datahub.app.services.onchain_service import OnChainService
from services.datahub.app.adapters.bitquery_adapter import BitqueryAdapter

logger = setup_logging("onchain_api")
router = APIRouter()


# Request/Response Models
class CollectLargeTransfersRequest(BaseModel):
    """Request model for collecting large transfers."""
    symbol: str = Field(..., min_length=1, description="Token symbol (e.g., BTC, ETH)")
    network: str = Field(default="eth", min_length=1, description="Blockchain network")
    min_amount: float = Field(default=100.0, description="Minimum transfer amount")
    hours: int = Field(default=24, description="Hours of historical data")
    limit: int = Field(default=100, description="Maximum transfers to fetch")


class CollectSmartMoneyRequest(BaseModel):
    """Request model for collecting smart money activity."""
    symbol: str = Field(..., min_length=1, description="Token symbol")
    network: str = Field(default="eth", min_length=1, description="Blockchain network")
    addresses: Optional[List[str]] = Field(default=None, description="Smart money addresses to track")
    hours: int = Field(default=24, description="Hours of historical data")
    limit: int = Field(default=100, description="Maximum activities to fetch")


class CollectExchangeNetflowRequest(BaseModel):
    """Request model for collecting exchange netflow."""
    symbol: str = Field(..., min_length=1, description="Token symbol")
    network: str = Field(default="eth", min_length=1, description="Blockchain network")
    exchange_addresses: Optional[List[str]] = Field(default=None, description="Exchange addresses")
    hours: int = Field(default=24, description="Hours of historical data")


class CollectActiveAddressesRequest(BaseModel):
    """Request model for collecting active addresses."""
    symbol: str = Field(..., min_length=1, description="Token symbol")
    network: str = Field(default="eth", min_length=1, description="Blockchain network")
    hours: int = Field(default=24, description="Hours of historical data")


class OnChainMetricsData(BaseModel):
    """Response model for on-chain metrics."""
    id: int
    symbol: str
    network: str
    contract_address: Optional[str] = None
    timestamp: datetime
    transaction_count: Optional[int] = None
    transaction_volume: Optional[float] = None
    active_addresses: Optional[int] = None
    new_addresses: Optional[int] = None
    large_transfer_count: Optional[int] = None
    large_transfer_volume: Optional[float] = None
    exchange_inflow: Optional[float] = None
    exchange_outflow: Optional[float] = None
    exchange_netflow: Optional[float] = None
    smart_money_inflow: Optional[float] = None
    smart_money_outflow: Optional[float] = None
    dex_volume: Optional[float] = None
    dex_trade_count: Optional[int] = None
    liquidity_usd: Optional[float] = None
    price_usd: Optional[float] = None
    additional_metrics: Optional[dict] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """
        Custom from_orm to extract fields from additional_metrics JSON.

        This method extracts large_transfer_count, large_transfer_volume,
        exchange_inflow, exchange_outflow, exchange_netflow, smart_money_inflow,
        smart_money_outflow, and dex_volume from the additional_metrics JSON field
        if they are not present as direct attributes.
        """
        # Get base data from ORM object
        data = {
            'id': obj.id,
            'symbol': obj.symbol,
            'network': obj.network,
            'contract_address': obj.contract_address,
            'timestamp': obj.timestamp,
            'transaction_count': obj.transaction_count,
            'transaction_volume': obj.transaction_volume,
            'active_addresses': obj.active_addresses,
            'new_addresses': obj.new_addresses,
            'dex_trade_count': obj.dex_trade_count,
            'liquidity_usd': obj.liquidity_usd,
            'price_usd': obj.price_usd,
            'additional_metrics': obj.additional_metrics
        }

        # Extract fields from additional_metrics if available
        if obj.additional_metrics:
            # For large transfers
            if 'large_transfer_count' in obj.additional_metrics:
                data['large_transfer_count'] = obj.additional_metrics['large_transfer_count']
            if 'large_transfer_volume' in obj.additional_metrics:
                data['large_transfer_volume'] = obj.additional_metrics['large_transfer_volume']

            # For exchange netflow
            if 'inflow' in obj.additional_metrics:
                data['exchange_inflow'] = obj.additional_metrics['inflow']
            if 'outflow' in obj.additional_metrics:
                data['exchange_outflow'] = obj.additional_metrics['outflow']
            if 'netflow' in obj.additional_metrics:
                data['exchange_netflow'] = obj.additional_metrics['netflow']

            # For smart money
            if 'smart_money_inflow' in obj.additional_metrics:
                data['smart_money_inflow'] = obj.additional_metrics['smart_money_inflow']
            if 'smart_money_outflow' in obj.additional_metrics:
                data['smart_money_outflow'] = obj.additional_metrics['smart_money_outflow']

            # For DEX volume (use dex_volume_usd from database if available)
            if hasattr(obj, 'dex_volume_usd') and obj.dex_volume_usd is not None:
                data['dex_volume'] = obj.dex_volume_usd
            elif 'dex_volume' in obj.additional_metrics:
                data['dex_volume'] = obj.additional_metrics['dex_volume']
        else:
            # If no additional_metrics, try to get dex_volume from dex_volume_usd
            if hasattr(obj, 'dex_volume_usd') and obj.dex_volume_usd is not None:
                data['dex_volume'] = obj.dex_volume_usd

        return cls(**data)


# Dependency: Get OnChainService
def get_onchain_service(db: Session = Depends(get_db)) -> OnChainService:
    """Dependency to get OnChainService instance."""
    chain_adapter = BitqueryAdapter()
    return OnChainService(db, chain_adapter)


# API Endpoints
@router.post("/collect/large-transfers")
async def collect_large_transfers(
    request: CollectLargeTransfersRequest,
    service: OnChainService = Depends(get_onchain_service)
):
    """
    Collect large transfer data (whale movements).

    This endpoint fetches large transfers from the blockchain and stores them
    in the database for analysis.
    """
    result = service.collect_large_transfers(
        symbol=request.symbol,
        network=request.network,
        min_amount=request.min_amount,
        hours=request.hours,
        limit=request.limit
    )
    return result


@router.post("/collect/smart-money")
async def collect_smart_money(
    request: CollectSmartMoneyRequest,
    service: OnChainService = Depends(get_onchain_service)
):
    """
    Collect smart money activity data.

    Tracks transactions from known whale/institutional addresses.
    """
    result = service.collect_smart_money_activity(
        symbol=request.symbol,
        network=request.network,
        addresses=request.addresses,
        hours=request.hours,
        limit=request.limit
    )
    return result


@router.post("/collect/exchange-netflow")
async def collect_exchange_netflow(
    request: CollectExchangeNetflowRequest,
    service: OnChainService = Depends(get_onchain_service)
):
    """
    Collect exchange netflow data.

    Calculates net inflow/outflow to/from exchanges.
    """
    result = service.collect_exchange_netflow(
        symbol=request.symbol,
        network=request.network,
        exchange_addresses=request.exchange_addresses,
        hours=request.hours
    )
    return result


@router.post("/collect/active-addresses")
async def collect_active_addresses(
    request: CollectActiveAddressesRequest,
    service: OnChainService = Depends(get_onchain_service)
):
    """
    Collect active addresses statistics.

    Counts unique active addresses and transaction statistics.
    """
    result = service.collect_active_addresses(
        symbol=request.symbol,
        network=request.network,
        hours=request.hours
    )
    return result


@router.get("/{symbol}/{network}", response_model=List[OnChainMetricsData])
async def get_onchain_metrics(
    symbol: str,
    network: str = "eth",
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(100, description="Maximum records to return"),
    service: OnChainService = Depends(get_onchain_service)
):
    """
    Get on-chain metrics from database.

    Query historical on-chain metrics with optional time filters.
    """
    try:
        metrics = service.get_metrics(
            symbol=symbol,
            network=network,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        return metrics
    except Exception as e:
        logger.error(f"Error querying on-chain metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/{network}/latest", response_model=Optional[OnChainMetricsData])
async def get_latest_metrics(
    symbol: str,
    network: str = "eth",
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    service: OnChainService = Depends(get_onchain_service)
):
    """
    Get the latest on-chain metrics for a symbol.

    Returns the most recent metrics record.
    """
    try:
        metrics = service.get_latest_metrics(
            symbol=symbol,
            network=network,
            metric_type=metric_type
        )
        if not metrics:
            raise HTTPException(status_code=404, detail="No metrics found")
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying latest metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

