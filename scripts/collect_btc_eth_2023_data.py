#!/usr/bin/env python3
"""
补充BTC/ETH 2023年历史数据

目标: 将BTC/ETH的数据量从9,284条增加至16,422条，与BNB/SOL/ADA对齐
策略: 收集2023年1月1日至2023年12月31日的1小时K线数据
"""

import sys
import time
import requests
from datetime import datetime, date
from typing import Dict, Any
import psycopg2

# 配置
DATAHUB_URL = "http://localhost:8001"
DATABASE_URL = "postgresql://bedrock:bedrock_password@localhost:5432/bedrock_db"

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INTERVAL = "1h"
YEAR = 2023
REQUEST_DELAY = 2  # 每次请求后延迟秒数

def check_existing_data(symbol: str, year: int) -> int:
    """检查数据库中已有的数据量"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 计算年份的时间戳范围（毫秒）
        start_ts = int(datetime(year, 1, 1).timestamp() * 1000)
        end_ts = int(datetime(year + 1, 1, 1).timestamp() * 1000)
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM klines 
            WHERE symbol = %s 
              AND interval = %s 
              AND open_time >= %s 
              AND open_time < %s
        """, (symbol, INTERVAL, start_ts, end_ts))
        
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return count
    except Exception as e:
        print(f"   [WARN] Failed to check existing data: {e}")
        return 0

def collect_month_data(symbol: str, year: int, month: int) -> Dict[str, Any]:
    """收集指定月份的K线数据"""
    # 计算月份的开始和结束日期
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    # 转换为datetime（UTC时间）
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.min.time())
    
    payload = {
        "symbol": symbol,
        "interval": INTERVAL,
        "start_time": start_datetime.isoformat() + "Z",
        "end_time": end_datetime.isoformat() + "Z",
        "limit": 1000
    }
    
    print(f"   [{month:02d}] Collecting {symbol} {year}-{month:02d}...")
    
    try:
        response = requests.post(
            f"{DATAHUB_URL}/v1/klines/collect",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            count = result.get("count", 0)
            print(f"        [OK] Collected {count} records")
            return {"success": True, "count": count}
        else:
            print(f"        [FAIL] HTTP {response.status_code}: {response.text}")
            return {"success": False, "count": 0, "error": response.text}
    
    except Exception as e:
        print(f"        [ERROR] {str(e)}")
        return {"success": False, "count": 0, "error": str(e)}

def main():
    """主函数"""
    print("=" * 80)
    print("BTC/ETH 2023 Historical Data Collection")
    print("=" * 80)
    print(f"Target: Align BTC/ETH data with BNB/SOL/ADA (16,422 records)")
    print(f"Strategy: Collect 2023 full year data")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Interval: {INTERVAL}")
    print("=" * 80)
    print()
    
    total_collected = 0
    
    for symbol in SYMBOLS:
        print(f"\n{'=' * 80}")
        print(f"[{symbol}] Starting collection")
        print(f"{'=' * 80}")
        
        # 检查现有数据
        existing_count = check_existing_data(symbol, YEAR)
        print(f"   Existing {YEAR} data: {existing_count} records")
        
        if existing_count > 8000:
            print(f"   [SKIP] {symbol} {YEAR} data already exists ({existing_count} records)")
            continue
        
        # 按月收集
        symbol_total = 0
        for month in range(1, 13):
            result = collect_month_data(symbol, YEAR, month)
            
            if result["success"]:
                symbol_total += result["count"]
            
            # 延迟，避免API限流
            if month < 12 or symbol != SYMBOLS[-1]:
                time.sleep(REQUEST_DELAY)
        
        print(f"\n   [{symbol}] Total collected: {symbol_total} records")
        total_collected += symbol_total
    
    print("\n" + "=" * 80)
    print("Collection Summary")
    print("=" * 80)
    print(f"Total records collected: {total_collected}")
    print()
    print("Next step: Run diagnose_cross_pair_data.py to verify data completeness")
    print("=" * 80)

if __name__ == "__main__":
    main()

