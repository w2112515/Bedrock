"""
分析5个币种的数据重叠情况，确定最佳策略
"""
import psycopg2
from datetime import datetime

DATABASE_URL = "postgresql://bedrock:bedrock_password@localhost:5432/bedrock_db"

def analyze_overlap():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
    
    print("=" * 80)
    print("Data Overlap Analysis")
    print("=" * 80)
    
    # 获取每个币种的时间范围
    print("\n[1] Time Range per Symbol")
    print("-" * 80)
    
    time_ranges = {}
    for symbol in symbols:
        cur.execute("""
            SELECT 
                to_timestamp(MIN(open_time)/1000) as earliest,
                to_timestamp(MAX(open_time)/1000) as latest,
                COUNT(*) as total
            FROM klines
            WHERE symbol = %s AND interval = '1h'
        """, (symbol,))
        
        result = cur.fetchone()
        time_ranges[symbol] = {
            'earliest': result[0],
            'latest': result[1],
            'total': result[2]
        }
        
        print(f"\n{symbol}:")
        print(f"  Earliest: {result[0]}")
        print(f"  Latest:   {result[1]}")
        print(f"  Total:    {result[2]:,} records")
    
    # 找到所有币种的共同时间范围
    print("\n" + "=" * 80)
    print("[2] Common Time Range (Intersection)")
    print("-" * 80)
    
    common_start = max(tr['earliest'] for tr in time_ranges.values())
    common_end = min(tr['latest'] for tr in time_ranges.values())
    
    print(f"\nCommon start: {common_start}")
    print(f"Common end:   {common_end}")
    
    # 计算每个币种在共同时间范围内的数据量
    print("\n" + "=" * 80)
    print("[3] Records in Common Time Range")
    print("-" * 80)
    
    common_start_ts = int(common_start.timestamp() * 1000)
    common_end_ts = int(common_end.timestamp() * 1000)
    
    total_in_common = 0
    for symbol in symbols:
        cur.execute("""
            SELECT COUNT(*)
            FROM klines
            WHERE symbol = %s 
              AND interval = '1h'
              AND open_time >= %s
              AND open_time <= %s
        """, (symbol, common_start_ts, common_end_ts))
        
        count = cur.fetchone()[0]
        total_in_common += count
        
        print(f"\n{symbol}: {count:,} records")
    
    avg_in_common = total_in_common // len(symbols)
    print(f"\nAverage per symbol: {avg_in_common:,} records")
    
    # 策略对比
    print("\n" + "=" * 80)
    print("[4] Strategy Comparison")
    print("-" * 80)
    
    print("\nStrategy A: Use common time range (2024-01-01 to 2025-11-15)")
    print(f"  Pros: All 5 symbols have complete data")
    print(f"  Cons: Lose 2023 data for BTC/ETH")
    print(f"  Sample size: ~{avg_in_common:,} records per symbol")
    print(f"  Total samples: ~{avg_in_common * len(symbols):,} records")
    
    print("\nStrategy B: Collect 2023 data for BNB/SOL/ADA")
    print(f"  Pros: Use full 2023-2025 data for all symbols")
    print(f"  Cons: Need additional 30-60 minutes to collect data")
    print(f"  Sample size: ~18,000 records per symbol")
    print(f"  Total samples: ~90,000 records")
    
    # 推荐
    print("\n" + "=" * 80)
    print("[5] Recommendation")
    print("-" * 80)
    
    if avg_in_common >= 15000:
        print("\n[RECOMMEND] Strategy A: Use common time range")
        print(f"Reason: {avg_in_common:,} samples per symbol is sufficient for training")
        print("Action: Filter data to 2024-01-01 onwards in data loader")
    else:
        print("\n[RECOMMEND] Strategy B: Collect 2023 data for BNB/SOL/ADA")
        print(f"Reason: {avg_in_common:,} samples may be insufficient, need more data")
        print("Action: Run collect_bnb_sol_ada_2023_data.py")
    
    print("\n" + "=" * 80)
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    analyze_overlap()

