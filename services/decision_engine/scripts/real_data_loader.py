"""
Real Data Loader - Load historical K-line data from PostgreSQL database.

This module loads real market data from the DataHub database for ML model training.

Design Principles:
- Single Responsibility: Only responsible for data loading
- Efficiency: Batch loading with sliding window generation
- Memory Optimization: Generator-based approach for large datasets
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from datetime import date, datetime
from typing import List, Dict, Tuple, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import structlog

logger = structlog.get_logger()


class RealDataLoader:
    """
    Real historical K-line data loader.
    
    Loads K-line data from PostgreSQL and generates sliding window samples
    for ML model training.
    
    Example:
        loader = RealDataLoader(db_url="postgresql://...")
        samples = loader.load_klines(
            symbols=["BTCUSDT", "ETHUSDT"],
            interval="1h",
            start_date=date(2024, 1, 1),
            end_date=date(2025, 11, 15),
            lookback_periods=100
        )
    """
    
    def __init__(self, db_url: str):
        """
        Initialize data loader.
        
        Args:
            db_url: PostgreSQL database URL
        """
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        logger.info(
            "real_data_loader_initialized",
            db_url=db_url.split('@')[1] if '@' in db_url else db_url  # Hide credentials
        )
    
    def load_klines(
        self,
        symbols: List[str],
        interval: str,
        start_date: date,
        end_date: date,
        lookback_periods: int = 100
    ) -> List[Tuple[List[Dict], str, datetime, int]]:
        """
        Load K-line data and generate sliding window samples.
        
        Args:
            symbols: List of trading pair symbols (e.g., ["BTCUSDT", "ETHUSDT"])
            interval: K-line interval (e.g., "1h")
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            lookback_periods: Number of K-lines per sample window
        
        Returns:
            List of (klines_window, symbol, timestamp, index) tuples where:
            - klines_window: List of K-line dicts (length = lookback_periods)
            - symbol: Trading pair symbol
            - timestamp: Timestamp of the last K-line in window
            - index: Global index of this sample (for future K-line lookup)
        """
        logger.info(
            "loading_klines",
            symbols=symbols,
            interval=interval,
            start_date=str(start_date),
            end_date=str(end_date),
            lookback_periods=lookback_periods
        )
        
        all_samples = []
        
        for symbol in symbols:
            # Load all K-lines for this symbol
            klines = self._load_symbol_klines(symbol, interval, start_date, end_date)
            
            if len(klines) < lookback_periods:
                logger.warning(
                    "insufficient_klines",
                    symbol=symbol,
                    klines_count=len(klines),
                    required=lookback_periods,
                    message=f"Skipping {symbol} due to insufficient data"
                )
                continue
            
            # Generate sliding window samples
            samples = self._generate_sliding_windows(
                klines=klines,
                symbol=symbol,
                lookback_periods=lookback_periods
            )
            
            all_samples.extend(samples)
            
            logger.info(
                "symbol_loaded",
                symbol=symbol,
                total_klines=len(klines),
                samples_generated=len(samples)
            )
        
        logger.info(
            "loading_complete",
            total_samples=len(all_samples),
            symbols_count=len(symbols)
        )

        return all_samples

    def load_klines_multifreq(
        self,
        symbols: List[str],
        primary_interval: str,
        secondary_interval: str,
        start_date: date,
        end_date: date,
        lookback_periods: int = 100
    ) -> List[Tuple[List[Dict], List[Dict], str, datetime, int]]:
        """
        Load K-line data with multiple time frequencies.

        Args:
            symbols: List of trading pair symbols
            primary_interval: Primary interval (e.g., "1h")
            secondary_interval: Secondary interval for additional features (e.g., "4h")
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            lookback_periods: Number of K-lines per sample window for primary interval

        Returns:
            List of (primary_klines, secondary_klines, symbol, timestamp, index) tuples
        """
        logger.info(
            "loading_klines_multifreq",
            symbols=symbols,
            primary_interval=primary_interval,
            secondary_interval=secondary_interval,
            start_date=str(start_date),
            end_date=str(end_date),
            lookback_periods=lookback_periods
        )

        all_samples = []

        for symbol in symbols:
            # Load primary interval K-lines (e.g., 1h)
            primary_klines = self._load_symbol_klines(symbol, primary_interval, start_date, end_date)

            # Load secondary interval K-lines (e.g., 4h)
            secondary_klines = self._load_symbol_klines(symbol, secondary_interval, start_date, end_date)

            if len(primary_klines) < lookback_periods:
                logger.warning(
                    "insufficient_primary_klines",
                    symbol=symbol,
                    klines_count=len(primary_klines),
                    required=lookback_periods
                )
                continue

            if len(secondary_klines) < 25:  # Need at least 25 4h K-lines for indicators
                logger.warning(
                    "insufficient_secondary_klines",
                    symbol=symbol,
                    klines_count=len(secondary_klines),
                    required=25
                )
                continue

            # Generate sliding window samples with both frequencies
            samples = self._generate_sliding_windows_multifreq(
                primary_klines=primary_klines,
                secondary_klines=secondary_klines,
                symbol=symbol,
                lookback_periods=lookback_periods
            )

            all_samples.extend(samples)

            logger.info(
                "symbol_loaded_multifreq",
                symbol=symbol,
                primary_klines=len(primary_klines),
                secondary_klines=len(secondary_klines),
                samples_generated=len(samples)
            )

        logger.info(
            "loading_complete_multifreq",
            total_samples=len(all_samples),
            symbols_count=len(symbols)
        )

        return all_samples

    def load_klines_crosspair(
        self,
        target_symbols: List[str],
        reference_symbols: List[str],
        primary_interval: str,
        secondary_interval: str,
        start_date: date,
        end_date: date,
        lookback_periods: int = 100
    ) -> List[Tuple[List[Dict], List[Dict], Dict[str, List[Dict]], str, datetime, int]]:
        """
        Load K-line data with cross-pair features support.

        This method loads K-line data for target symbols (used for generating samples)
        and reference symbols (used for calculating cross-pair features like BTC leading indicators).

        Args:
            target_symbols: Target trading pairs (samples generated from these)
            reference_symbols: Reference trading pairs (for cross-pair features)
            primary_interval: Primary interval (e.g., "1h")
            secondary_interval: Secondary interval for additional features (e.g., "4h")
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            lookback_periods: Number of K-lines per sample window for primary interval

        Returns:
            List of tuples, each containing:
            - primary_window: Primary interval K-lines (e.g., 100 1h K-lines)
            - secondary_window: Secondary interval K-lines (e.g., ~25 4h K-lines)
            - reference_windows: Dict of reference symbol K-lines {symbol: [klines]}
            - symbol: Target symbol
            - timestamp: Current timestamp
            - index: Sample index
        """
        logger.info(
            "loading_crosspair_data",
            target_symbols=target_symbols,
            reference_symbols=reference_symbols,
            primary_interval=primary_interval,
            secondary_interval=secondary_interval,
            start_date=str(start_date),
            end_date=str(end_date),
            lookback_periods=lookback_periods
        )

        # Load reference symbols K-lines (full dataset, loaded once)
        reference_klines_full = {}
        for ref_symbol in reference_symbols:
            klines = self._load_symbol_klines(ref_symbol, primary_interval, start_date, end_date)
            reference_klines_full[ref_symbol] = klines
            logger.info(
                "reference_symbol_loaded",
                symbol=ref_symbol,
                klines_count=len(klines)
            )

        all_samples = []

        for symbol in target_symbols:
            # Load primary and secondary K-lines for target symbol
            primary_klines = self._load_symbol_klines(symbol, primary_interval, start_date, end_date)
            secondary_klines = self._load_symbol_klines(symbol, secondary_interval, start_date, end_date)

            if len(primary_klines) < lookback_periods:
                logger.warning(
                    "insufficient_primary_klines",
                    symbol=symbol,
                    klines_count=len(primary_klines),
                    required=lookback_periods,
                    message=f"Skipping {symbol} due to insufficient primary data"
                )
                continue

            # Generate sliding window samples with cross-pair features
            samples = self._generate_sliding_windows_crosspair(
                primary_klines=primary_klines,
                secondary_klines=secondary_klines,
                reference_klines_full=reference_klines_full,
                symbol=symbol,
                lookback_periods=lookback_periods
            )

            all_samples.extend(samples)

            logger.info(
                "symbol_loaded_crosspair",
                symbol=symbol,
                primary_klines=len(primary_klines),
                secondary_klines=len(secondary_klines),
                samples_generated=len(samples)
            )

        logger.info(
            "loading_complete_crosspair",
            total_samples=len(all_samples),
            target_symbols_count=len(target_symbols),
            reference_symbols_count=len(reference_symbols)
        )

        return all_samples

    def _load_symbol_klines(
        self,
        symbol: str,
        interval: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Load all K-lines for a specific symbol."""
        session = self.Session()
        
        try:
            query = text("""
                SELECT
                    open_time,
                    close_time,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume
                FROM klines
                WHERE symbol = :symbol
                  AND interval = :interval
                  AND open_time >= :start_ts
                  AND open_time <= :end_ts
                ORDER BY open_time ASC
            """)

            # Convert dates to timestamps (milliseconds)
            start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1000)
            end_ts = int(datetime.combine(end_date, datetime.max.time()).timestamp() * 1000)

            result = session.execute(
                query,
                {
                    "symbol": symbol,
                    "interval": interval,
                    "start_ts": start_ts,
                    "end_ts": end_ts
                }
            )

            klines = []
            for row in result:
                klines.append({
                    'open_time': row.open_time,
                    'close_time': row.close_time,
                    'open': float(row.open_price),
                    'high': float(row.high_price),
                    'low': float(row.low_price),
                    'close': float(row.close_price),
                    'volume': float(row.volume),
                    'timestamp': datetime.fromtimestamp(row.open_time / 1000)
                })

            return klines

        finally:
            session.close()

    def _generate_sliding_windows(
        self,
        klines: List[Dict],
        symbol: str,
        lookback_periods: int
    ) -> List[Tuple[List[Dict], str, datetime, int]]:
        """
        Generate sliding window samples from K-line data.

        Args:
            klines: List of K-line dicts (sorted by time)
            symbol: Trading pair symbol
            lookback_periods: Window size

        Returns:
            List of (window, symbol, timestamp, index) tuples

        CRITICAL FIX (Look-Ahead Bias):
        - Window contains ONLY historical K-lines [t-99, t-1]
        - Current timestamp is t (NOT included in window)
        - This prevents features from using current K-line data
        """
        samples = []

        # FIXED: Loop until len(klines) - lookback_periods (not +1)
        # This ensures we always have a "current K-line" after the window
        for i in range(len(klines) - lookback_periods):
            # Window: [i, i+lookback_periods-1] = historical K-lines [t-99, t-1]
            window = klines[i:i + lookback_periods]

            # CRITICAL FIX: Current timestamp is the K-line AFTER the window
            # This is time t, while window contains [t-99, t-1]
            current_kline = klines[i + lookback_periods]
            current_timestamp = current_kline['timestamp']

            samples.append((
                window,
                symbol,
                current_timestamp,
                i + lookback_periods  # Global index of current K-line
            ))

        return samples

    def _generate_sliding_windows_multifreq(
        self,
        primary_klines: List[Dict],
        secondary_klines: List[Dict],
        symbol: str,
        lookback_periods: int
    ) -> List[Tuple[List[Dict], List[Dict], str, datetime, int]]:
        """
        Generate sliding window samples with multiple time frequencies.

        For each primary window (e.g., 100 1h K-lines), find the corresponding
        secondary K-lines (e.g., 4h K-lines) that cover the same time period.

        Args:
            primary_klines: Primary interval K-lines (e.g., 1h)
            secondary_klines: Secondary interval K-lines (e.g., 4h)
            symbol: Trading pair symbol
            lookback_periods: Window size for primary interval

        Returns:
            List of (primary_window, secondary_window, symbol, timestamp, index) tuples
        """
        samples = []

        # FIXED: Same look-ahead bias fix as single-frequency version
        for i in range(len(primary_klines) - lookback_periods):
            # Primary window: [t-99, t-1] for 1h K-lines
            primary_window = primary_klines[i:i + lookback_periods]

            # Current timestamp (time t, NOT in window)
            current_kline = primary_klines[i + lookback_periods]
            current_timestamp = current_kline['timestamp']

            # Find secondary K-lines that cover the same time period
            # Window start time
            window_start_time = primary_window[0]['timestamp']
            window_end_time = primary_window[-1]['timestamp']

            # Find all secondary K-lines within [window_start_time, window_end_time]
            secondary_window = [
                kline for kline in secondary_klines
                if window_start_time <= kline['timestamp'] <= window_end_time
            ]

            # Skip if insufficient secondary K-lines
            if len(secondary_window) < 10:  # Need at least 10 4h K-lines for indicators
                continue

            samples.append((
                primary_window,
                secondary_window,
                symbol,
                current_timestamp,
                i + lookback_periods  # Global index of current K-line
            ))

        return samples

    def _generate_sliding_windows_crosspair(
        self,
        primary_klines: List[Dict],
        secondary_klines: List[Dict],
        reference_klines_full: Dict[str, List[Dict]],
        symbol: str,
        lookback_periods: int
    ) -> List[Tuple[List[Dict], List[Dict], Dict[str, List[Dict]], str, datetime, int]]:
        """
        Generate sliding window samples with cross-pair features support.

        For each primary window, extract:
        1. Primary K-lines (e.g., 100 1h K-lines)
        2. Secondary K-lines covering the same time period
        3. Reference symbols K-lines covering the same time period (for cross-pair features)

        Args:
            primary_klines: Primary interval K-lines (e.g., 1h)
            secondary_klines: Secondary interval K-lines (e.g., 4h)
            reference_klines_full: Full K-lines for all reference symbols
            symbol: Target symbol
            lookback_periods: Window size for primary interval

        Returns:
            List of (primary_window, secondary_window, reference_windows, symbol, timestamp, index) tuples
        """
        samples = []

        # Build timestamp index for reference symbols (for fast lookup)
        reference_indices = {}
        for ref_symbol, ref_klines in reference_klines_full.items():
            # Create dict: timestamp -> kline
            reference_indices[ref_symbol] = {
                kline['open_time']: kline for kline in ref_klines
            }

        for i in range(len(primary_klines) - lookback_periods):
            # Extract primary window [i, i+lookback_periods)
            primary_window = primary_klines[i:i + lookback_periods]
            current_timestamp = primary_window[-1]['timestamp']

            # Extract secondary window covering the same time period
            window_start_ts = primary_window[0]['open_time']
            window_end_ts = primary_window[-1]['open_time']

            secondary_window = [
                k for k in secondary_klines
                if window_start_ts <= k['open_time'] <= window_end_ts
            ]

            # Skip if insufficient secondary K-lines
            if len(secondary_window) < 10:
                continue

            # Extract reference windows covering the same time period
            reference_windows = {}
            for ref_symbol, ref_index in reference_indices.items():
                # Extract K-lines in the time window
                ref_window = []
                for ts in range(window_start_ts, window_end_ts + 1, 3600000):  # 1h = 3600000ms
                    if ts in ref_index:
                        ref_window.append(ref_index[ts])
                    elif ref_window:
                        # Forward fill: use last available K-line
                        ref_window.append(ref_window[-1])

                # Ensure we have at least lookback_periods K-lines
                if len(ref_window) >= lookback_periods:
                    reference_windows[ref_symbol] = ref_window[-lookback_periods:]
                else:
                    # Insufficient data, skip this sample
                    reference_windows = None
                    break

            # Skip if any reference symbol has insufficient data
            if reference_windows is None:
                continue

            samples.append((
                primary_window,
                secondary_window,
                reference_windows,
                symbol,
                current_timestamp,
                i + lookback_periods  # Global index of current K-line
            ))

        return samples

    def get_future_klines(
        self,
        symbol: str,
        interval: str,
        start_timestamp: datetime,
        num_periods: int
    ) -> List[Dict]:
        """
        Get future K-lines for label generation.

        Args:
            symbol: Trading pair symbol
            interval: K-line interval
            start_timestamp: Start timestamp (exclusive)
            num_periods: Number of future periods to fetch

        Returns:
            List of K-line dicts
        """
        session = self.Session()

        try:
            query = text("""
                SELECT
                    open_time,
                    close_time,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume
                FROM klines
                WHERE symbol = :symbol
                  AND interval = :interval
                  AND open_time > :start_ts
                ORDER BY open_time ASC
                LIMIT :limit
            """)

            start_ts = int(start_timestamp.timestamp() * 1000)

            result = session.execute(
                query,
                {
                    "symbol": symbol,
                    "interval": interval,
                    "start_ts": start_ts,
                    "limit": num_periods
                }
            )

            klines = []
            for row in result:
                klines.append({
                    'open_time': row.open_time,
                    'close_time': row.close_time,
                    'open': float(row.open_price),
                    'high': float(row.high_price),
                    'low': float(row.low_price),
                    'close': float(row.close_price),
                    'volume': float(row.volume)
                })

            return klines

        finally:
            session.close()


def main():
    """Test data loader."""
    from services.decision_engine.app.core.config import settings

    loader = RealDataLoader(db_url=settings.DATABASE_URL)

    samples = loader.load_klines(
        symbols=["BTCUSDT"],
        interval="1h",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        lookback_periods=100
    )

    print(f"Loaded {len(samples)} samples")
    if samples:
        window, symbol, timestamp, idx = samples[0]
        print(f"First sample: {symbol}, {timestamp}, {len(window)} K-lines")
        print(f"First K-line: {window[0]}")


if __name__ == "__main__":
    main()

