"""
K-Line Data API Endpoints
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from shared.utils.database import get_db
from shared.models.schemas import BaseResponse
from services.datahub.app.services.kline_service import KLineService

router = APIRouter()


# Request/Response Models
class KLineData(BaseModel):
    """K-line data response model"""
    symbol: str
    interval: str
    open_time: int
    close_time: int
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    quote_volume: Optional[float] = None
    trade_count: Optional[int] = None
    taker_buy_base_volume: Optional[float] = None
    taker_buy_quote_volume: Optional[float] = None
    source: str

    class Config:
        from_attributes = True


class FundingRateData(BaseModel):
    """Funding rate data response model"""
    symbol: str
    funding_time: int
    funding_rate: str
    mark_price: str


class CollectKLinesRequest(BaseModel):
    """Request model for collecting K-lines"""
    symbol: str = Field(..., description="Trading pair symbol (e.g., BTCUSDT)")
    interval: str = Field(..., description="K-line interval (e.g., 1m, 1h, 1d)")
    start_time: Optional[datetime] = Field(None, description="Start time for data collection")
    end_time: Optional[datetime] = Field(None, description="End time for data collection")
    limit: int = Field(500, ge=1, le=1000, description="Maximum number of K-lines to fetch")


class CollectKLinesResponse(BaseModel):
    """Response model for K-line collection"""
    success: bool
    message: str
    count: int


@router.post("/collect", response_model=CollectKLinesResponse)
async def collect_klines(
    request: CollectKLinesRequest,
    db: Session = Depends(get_db)
) -> CollectKLinesResponse:
    """
    Collect K-line data from Binance and store in database.

    This endpoint fetches K-line data from Binance API and stores it in the database.
    """
    try:
        service = KLineService(db)
        count = service.collect_klines(
            symbol=request.symbol,
            interval=request.interval,
            start_time=request.start_time,
            end_time=request.end_time,
            limit=request.limit
        )

        return CollectKLinesResponse(
            success=True,
            message=f"Successfully collected {count} K-lines",
            count=count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/{interval}", response_model=List[KLineData])
async def get_klines(
    symbol: str,
    interval: str,
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(500, ge=1, le=1000, description="Maximum number of K-lines"),
    db: Session = Depends(get_db)
) -> List[KLineData]:
    """
    Get K-line data from database.

    Returns K-line data for the specified symbol and interval.
    """
    try:
        service = KLineService(db)
        klines = service.get_klines(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        return [KLineData.from_orm(kline) for kline in klines]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/{interval}/latest", response_model=KLineData)
async def get_latest_kline(
    symbol: str,
    interval: str,
    db: Session = Depends(get_db)
) -> KLineData:
    """
    Get the latest K-line for a symbol and interval.
    """
    try:
        service = KLineService(db)
        kline = service.get_latest_kline(symbol=symbol, interval=interval)

        if not kline:
            raise HTTPException(status_code=404, detail="No K-line data found")

        return KLineData.from_orm(kline)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 批量K线查询接口 (Batch K-Lines Query API)
# 用途：支持v2.7模型的多币种+多时间周期K线数据批量获取
# ============================================================================

class KLineQuery(BaseModel):
    """单个K线查询请求"""
    symbol: str = Field(..., description="交易对符号 (e.g., BTCUSDT)")
    interval: str = Field(..., description="K线时间周期 (e.g., 1h, 4h)")
    limit: int = Field(default=100, ge=1, le=1000, description="K线数量限制")


class BatchKLinesRequest(BaseModel):
    """批量K线查询请求"""
    queries: List[KLineQuery] = Field(..., description="K线查询列表")


class BatchKLinesMetadata(BaseModel):
    """批量查询元数据"""
    total_queries: int = Field(..., description="总查询数")
    successful_queries: int = Field(..., description="成功查询数")
    failed_queries: int = Field(..., description="失败查询数")
    total_klines: int = Field(..., description="返回的K线总数")


class BatchKLinesResponse(BaseModel):
    """批量K线查询响应"""
    success: bool = Field(..., description="整体是否成功（所有查询都成功才为True）")
    results: Dict[str, List[KLineData]] = Field(
        ...,
        description="成功的查询结果，key格式为 '{symbol}:{interval}'"
    )
    errors: Dict[str, str] = Field(
        ...,
        description="失败的查询错误信息，key格式为 '{symbol}:{interval}'"
    )
    metadata: BatchKLinesMetadata = Field(..., description="查询元数据")


@router.post("/batch", response_model=BatchKLinesResponse)
async def get_klines_batch(
    request: BatchKLinesRequest,
    db: Session = Depends(get_db)
) -> BatchKLinesResponse:
    """
    批量获取K线数据（支持多币种+多时间周期）

    设计目的：
    - 为v2.7模型提供高效的数据获取接口
    - 减少网络往返次数（从7次单点调用降低到1次批量调用）
    - 使用asyncio并发查询数据库，提升性能

    降级策略：
    - 如果某个查询失败，不影响其他查询
    - 失败的查询会记录在errors字段中
    - 调用方可以根据errors字段决定是否降级处理

    示例请求：
    {
        "queries": [
            {"symbol": "BTCUSDT", "interval": "1h", "limit": 100},
            {"symbol": "BTCUSDT", "interval": "4h", "limit": 25},
            {"symbol": "ETHUSDT", "interval": "1h", "limit": 100}
        ]
    }

    示例响应：
    {
        "success": true,
        "results": {
            "BTCUSDT:1h": [...],
            "BTCUSDT:4h": [...],
            "ETHUSDT:1h": [...]
        },
        "errors": {},
        "metadata": {
            "total_queries": 3,
            "successful_queries": 3,
            "failed_queries": 0,
            "total_klines": 225
        }
    }
    """
    try:
        service = KLineService(db)

        # 调用批量查询服务
        batch_result = await service.get_klines_batch(request.queries)

        return batch_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funding-rates")
async def get_funding_rates(
    symbol: str = Query(..., description="Trading pair symbol (e.g., BTCUSDT)"),
    start_time: Optional[datetime] = Query(None, description="Start time for data fetch"),
    end_time: Optional[datetime] = Query(None, description="End time for data fetch"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to fetch")
):
    """
    Get funding rate data from Binance Futures API.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        start_time: Start time for data fetch (optional)
        end_time: End time for data fetch (optional)
        limit: Maximum number of records to fetch (default 100, max 1000)

    Returns:
        List of funding rate data
    """
    try:
        from services.datahub.app.adapters.binance_adapter import BinanceAdapter

        adapter = BinanceAdapter()
        funding_rates = adapter.get_funding_rate(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

        return {
            "success": True,
            "data": funding_rates,
            "count": len(funding_rates)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

