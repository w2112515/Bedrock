"""
诊断跨币种特征所需的数据完整性和对齐情况
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from datetime import datetime
import pandas as pd

# Database connection
DATABASE_URL = "postgresql://bedrock:bedrock_password@localhost:5432/bedrock_db"

def diagnose_cross_pair_data():
    engine = create_engine(DATABASE_URL)
    
    print("=" * 80)
    print("Cross-Pair Feature Data Diagnosis")
    print("=" * 80)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
    
    # Step 1: Check data availability for each symbol
    print("\n[1] Data Availability Check (1h timeframe)")
    print("-" * 80)
    
    symbol_stats = {}
    for symbol in symbols:
        query = text("""
            SELECT
                COUNT(*) as total_records,
                to_timestamp(MIN(open_time)/1000) as earliest,
                to_timestamp(MAX(open_time)/1000) as latest,
                COUNT(DISTINCT DATE(to_timestamp(open_time/1000))) as unique_days
            FROM klines
            WHERE symbol = :symbol AND interval = '1h'
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"symbol": symbol}).fetchone()
            symbol_stats[symbol] = {
                'total': result[0],
                'earliest': result[1],
                'latest': result[2],
                'unique_days': result[3]
            }
            
            print(f"\n{symbol}:")
            print(f"  Total records: {result[0]:,}")
            print(f"  Date range: {result[1]} to {result[2]}")
            print(f"  Unique days: {result[3]}")
    
    # Step 2: Check timestamp alignment
    print("\n" + "=" * 80)
    print("[2] Timestamp Alignment Analysis")
    print("-" * 80)
    
    # Get all unique timestamps across all symbols
    query = text("""
        SELECT DISTINCT open_time
        FROM klines
        WHERE interval = '1h'
        ORDER BY open_time
    """)
    
    with engine.connect() as conn:
        all_timestamps = pd.read_sql(query, conn)['open_time'].tolist()
    
    print(f"\nTotal unique timestamps: {len(all_timestamps):,}")
    
    # Check coverage for each symbol
    print("\nTimestamp coverage per symbol:")
    for symbol in symbols:
        query = text("""
            SELECT open_time
            FROM klines
            WHERE symbol = :symbol AND interval = '1h'
            ORDER BY open_time
        """)
        
        with engine.connect() as conn:
            symbol_timestamps = set(pd.read_sql(query, conn, params={"symbol": symbol})['open_time'])
        
        coverage = len(symbol_timestamps) / len(all_timestamps) * 100
        missing = len(all_timestamps) - len(symbol_timestamps)
        missing_pct = missing / len(all_timestamps) * 100
        
        print(f"\n{symbol}:")
        print(f"  Coverage: {coverage:.2f}% ({len(symbol_timestamps):,}/{len(all_timestamps):,})")
        print(f"  Missing: {missing:,} timestamps ({missing_pct:.2f}%)")
        
        if missing_pct > 10:
            print(f"  [WARN] Missing data > 10%, may need to exclude this symbol")
        elif missing_pct > 5:
            print(f"  [WARN] Missing data > 5%, consider forward fill")
        else:
            print(f"  [OK] Missing data < 5%, acceptable")
    
    # Step 3: Check for gaps in data
    print("\n" + "=" * 80)
    print("[3] Data Gap Analysis")
    print("-" * 80)
    
    for symbol in symbols:
        query = text("""
            WITH time_diffs AS (
                SELECT
                    open_time,
                    LEAD(open_time) OVER (ORDER BY open_time) as next_time,
                    (LEAD(open_time) OVER (ORDER BY open_time) - open_time) / 3600000.0 as hour_diff
                FROM klines
                WHERE symbol = :symbol AND interval = '1h'
            )
            SELECT COUNT(*) as gap_count
            FROM time_diffs
            WHERE hour_diff > 1.5
        """)
        
        with engine.connect() as conn:
            gap_count = conn.execute(query, {"symbol": symbol}).fetchone()[0]
        
        print(f"\n{symbol}: {gap_count} gaps (>1.5 hours)")
    
    # Step 4: Final recommendation
    print("\n" + "=" * 80)
    print("[4] Final Recommendation")
    print("-" * 80)
    
    all_ok = True
    for symbol in symbols:
        query = text("""
            SELECT COUNT(*) FROM klines WHERE symbol = :symbol AND interval = '1h'
        """)
        with engine.connect() as conn:
            count = conn.execute(query, {"symbol": symbol}).fetchone()[0]
        
        expected = len(all_timestamps)
        missing_pct = (expected - count) / expected * 100
        
        if missing_pct > 10:
            print(f"\n[EXCLUDE] {symbol}: Missing {missing_pct:.2f}% of data")
            all_ok = False
        else:
            print(f"\n[INCLUDE] {symbol}: Missing only {missing_pct:.2f}% of data")
    
    if all_ok:
        print("\n[OK] All 5 symbols can be used for cross-pair features")
        print("Strategy: Use forward fill for missing timestamps")
    else:
        print("\n[WARN] Some symbols should be excluded")
        print("Strategy: Only use symbols with <10% missing data")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    diagnose_cross_pair_data()

