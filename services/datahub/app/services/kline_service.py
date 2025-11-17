"""
K-Line Data Collection Service

Handles fetching, storing, and querying K-line data.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import asyncio

from services.datahub.app.models.kline import KLine
from services.datahub.app.adapters.binance_adapter import BinanceAdapter
from shared.utils.logger import setup_logging
from shared.utils.redis_client import get_redis_client

logger = setup_logging("kline_service")


class KLineService:
    """
    Service for managing K-line data collection and storage.
    """
    
    def __init__(self, db: Session):
        """
        Initialize K-line service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.binance_adapter = BinanceAdapter()
        self.redis_client = get_redis_client()
    
    def collect_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500
    ) -> int:
        """
        Collect K-line data from Binance and store in database.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            interval: K-line interval (e.g., "1m", "1h", "1d")
            start_time: Start time for data collection
            end_time: End time for data collection
            limit: Maximum number of K-lines to fetch
        
        Returns:
            Number of K-lines stored
        """
        try:
            logger.info(f"Collecting K-lines for {symbol} with interval {interval}")
            
            # Fetch K-lines from Binance
            klines_data = self.binance_adapter.get_klines(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            
            # Store K-lines in database
            stored_count = 0
            for kline_data in klines_data:
                # Check if K-line already exists
                existing = self.db.query(KLine).filter(
                    and_(
                        KLine.symbol == kline_data["symbol"],
                        KLine.interval == kline_data["interval"],
                        KLine.open_time == kline_data["open_time"]
                    )
                ).first()
                
                if existing:
                    # Update existing K-line
                    for key, value in kline_data.items():
                        setattr(existing, key, value)
                else:
                    # Create new K-line
                    kline = KLine(**kline_data)
                    self.db.add(kline)
                
                stored_count += 1
            
            self.db.commit()
            logger.info(f"Successfully stored {stored_count} K-lines for {symbol}")
            
            # Invalidate cache
            cache_key = f"klines:{symbol}:{interval}"
            self.redis_client.delete(cache_key)
            
            return stored_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error collecting K-lines: {e}")
            raise
    
    def collect_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> int:
        """
        Collect historical K-line data (can fetch more than 1000 records).
        
        Args:
            symbol: Trading pair symbol
            interval: K-line interval
            start_time: Start time for data collection
            end_time: End time for data collection
        
        Returns:
            Number of K-lines stored
        """
        try:
            logger.info(f"Collecting historical K-lines for {symbol} from {start_time}")
            
            # Fetch historical K-lines from Binance
            klines_data = self.binance_adapter.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )
            
            # Store K-lines in database (batch insert for efficiency)
            stored_count = 0
            batch_size = 1000
            
            for i in range(0, len(klines_data), batch_size):
                batch = klines_data[i:i + batch_size]
                
                for kline_data in batch:
                    # Check if K-line already exists
                    existing = self.db.query(KLine).filter(
                        and_(
                            KLine.symbol == kline_data["symbol"],
                            KLine.interval == kline_data["interval"],
                            KLine.open_time == kline_data["open_time"]
                        )
                    ).first()
                    
                    if not existing:
                        kline = KLine(**kline_data)
                        self.db.add(kline)
                        stored_count += 1
                
                self.db.commit()
                logger.info(f"Stored batch {i // batch_size + 1}, total: {stored_count}")
            
            logger.info(f"Successfully stored {stored_count} historical K-lines for {symbol}")
            
            # Invalidate cache
            cache_key = f"klines:{symbol}:{interval}"
            self.redis_client.delete(cache_key)
            
            return stored_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error collecting historical K-lines: {e}")
            raise
    
    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
        use_cache: bool = True
    ) -> List[KLine]:
        """
        Get K-lines from database.
        
        Args:
            symbol: Trading pair symbol
            interval: K-line interval
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of K-lines to return
            use_cache: Whether to use Redis cache
        
        Returns:
            List of K-line objects
        """
        try:
            # Try cache first
            if use_cache:
                cache_key = f"klines:{symbol}:{interval}:{start_time}:{end_time}:{limit}"
                cached = self.redis_client.get(cache_key)
                if cached:
                    logger.info(f"Cache hit for K-lines: {cache_key}")
                    # Note: In production, deserialize cached data properly
                    # For now, we'll skip cache and query database
            
            # Query database
            query = self.db.query(KLine).filter(
                and_(
                    KLine.symbol == symbol,
                    KLine.interval == interval
                )
            )
            
            if start_time:
                query = query.filter(KLine.open_time >= int(start_time.timestamp() * 1000))
            
            if end_time:
                query = query.filter(KLine.open_time <= int(end_time.timestamp() * 1000))
            
            klines = query.order_by(desc(KLine.open_time)).limit(limit).all()
            
            logger.info(f"Retrieved {len(klines)} K-lines for {symbol}")
            return klines
            
        except Exception as e:
            logger.error(f"Error retrieving K-lines: {e}")
            raise
    
    def get_latest_kline(self, symbol: str, interval: str) -> Optional[KLine]:
        """
        Get the latest K-line for a symbol and interval.

        Args:
            symbol: Trading pair symbol
            interval: K-line interval

        Returns:
            Latest K-line object or None
        """
        try:
            kline = self.db.query(KLine).filter(
                and_(
                    KLine.symbol == symbol,
                    KLine.interval == interval
                )
            ).order_by(desc(KLine.open_time)).first()

            return kline

        except Exception as e:
            logger.error(f"Error retrieving latest K-line: {e}")
            raise

    async def get_klines_batch(self, queries: List[Any]) -> Dict[str, Any]:
        """
        批量获取K线数据（并发查询）

        设计目的：
        - 为v2.7模型提供高效的批量数据获取能力
        - 使用asyncio.gather()并发查询数据库，提升性能
        - 单个查询失败不影响其他查询（降级策略）

        Args:
            queries: K线查询列表，每个查询包含 symbol, interval, limit

        Returns:
            批量查询结果字典，包含：
            - success: 是否所有查询都成功
            - results: 成功的查询结果 {"{symbol}:{interval}": [KLineData, ...]}
            - errors: 失败的查询错误信息 {"{symbol}:{interval}": "error message"}
            - metadata: 查询元数据（总数、成功数、失败数、K线总数）

        性能优势：
        - 并发查询：7个查询并发执行，总延迟 ≈ 单次查询延迟（~100ms）
        - 相比串行调用7次（~700ms），性能提升7倍
        """
        from services.datahub.app.api.klines import KLineData, BatchKLinesResponse, BatchKLinesMetadata

        # 创建并发任务列表
        tasks = []
        query_keys = []  # 用于记录每个任务对应的key

        for query in queries:
            key = f"{query.symbol}:{query.interval}"
            query_keys.append(key)

            # 创建异步任务（使用run_in_executor在线程池中执行同步数据库查询）
            task = asyncio.get_event_loop().run_in_executor(
                None,  # 使用默认线程池
                self._get_klines_sync,  # 同步查询方法
                query.symbol,
                query.interval,
                query.limit
            )
            tasks.append(task)

        # 并发执行所有查询（return_exceptions=True 确保单个失败不影响其他查询）
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理查询结果
        success_results = {}
        errors = {}
        total_klines = 0

        for key, result in zip(query_keys, results_list):
            if isinstance(result, Exception):
                # 查询失败，记录错误
                error_msg = str(result)
                errors[key] = error_msg
                logger.warning(f"Batch query failed for {key}: {error_msg}")
            else:
                # 查询成功，转换为KLineData格式
                kline_data_list = [KLineData.from_orm(kline) for kline in result]
                success_results[key] = kline_data_list
                total_klines += len(kline_data_list)
                logger.debug(f"Batch query succeeded for {key}: {len(kline_data_list)} klines")

        # 构建响应
        metadata = BatchKLinesMetadata(
            total_queries=len(queries),
            successful_queries=len(success_results),
            failed_queries=len(errors),
            total_klines=total_klines
        )

        response = BatchKLinesResponse(
            success=(len(errors) == 0),  # 所有查询都成功才为True
            results=success_results,
            errors=errors,
            metadata=metadata
        )

        logger.info(
            f"Batch query completed: {metadata.successful_queries}/{metadata.total_queries} succeeded, "
            f"{metadata.total_klines} total klines"
        )

        return response

    def _get_klines_sync(
        self,
        symbol: str,
        interval: str,
        limit: int
    ) -> List[KLine]:
        """
        同步获取K线数据（供批量查询使用）

        为什么需要这个方法：
        - asyncio.gather()需要在线程池中执行同步数据库查询
        - 每个查询使用独立的数据库会话，避免锁竞争

        Args:
            symbol: 交易对符号
            interval: K线时间周期
            limit: K线数量限制

        Returns:
            K线对象列表
        """
        from shared.utils.database import SessionLocal

        # 为每个并发查询创建独立的数据库会话（避免并发冲突）
        db = SessionLocal()
        try:
            # 直接查询数据库，不使用self.db（避免会话共享）
            klines = (
                db.query(KLine)
                .filter(KLine.symbol == symbol, KLine.interval == interval)
                .order_by(KLine.open_time.desc())
                .limit(limit)
                .all()
            )
            return klines
        except Exception as e:
            logger.error(f"Error in _get_klines_sync for {symbol}:{interval}: {e}")
            raise
        finally:
            db.close()  # 确保会话关闭

