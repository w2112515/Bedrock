#!/usr/bin/env python3
"""
补充BTC/ETH缺失的2024-2025年数据

问题: BTC/ETH在2024-2025年只有9,284条记录，应该有16,422条
策略: 重新收集2024-2025年全部数据，数据库会自动去重（UPSERT）
"""

import sys
import time
import requests
from datetime import datetime, date
from typing import Dict, Any

# 配置
DATAHUB_URL = "http://localhost:8001"

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INTERVAL = "1h"
YEARS = [2024, 2025]
REQUEST_DELAY = 2  # 每次请求后延迟秒数

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
    
    print(f"   [{year}-{month:02d}] Collecting {symbol}...")
    
    try:
        response = requests.post(
            f"{DATAHUB_URL}/v1/klines/collect",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            count = result.get("count", 0)
            print(f"             [OK] Collected {count} records")
            return {"success": True, "count": count}
        else:
            print(f"             [FAIL] HTTP {response.status_code}: {response.text}")
            return {"success": False, "count": 0, "error": response.text}
    
    except Exception as e:
        print(f"             [ERROR] {str(e)}")
        return {"success": False, "count": 0, "error": str(e)}

def main():
    """主函数"""
    print("=" * 80)
    print("BTC/ETH Missing Data Collection (2024-2025)")
    print("=" * 80)
    print(f"Problem: BTC/ETH only have 9,284 records in 2024-2025, should have 16,422")
    print(f"Strategy: Re-collect all 2024-2025 data (database will auto-deduplicate)")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Interval: {INTERVAL}")
    print("=" * 80)
    print()
    
    total_collected = 0
    
    for symbol in SYMBOLS:
        print(f"\n{'=' * 80}")
        print(f"[{symbol}] Starting collection")
        print(f"{'=' * 80}")
        
        symbol_total = 0
        
        for year in YEARS:
            # 2025年只收集到11月
            max_month = 11 if year == 2025 else 12
            
            for month in range(1, max_month + 1):
                result = collect_month_data(symbol, year, month)
                
                if result["success"]:
                    symbol_total += result["count"]
                
                # 延迟，避免API限流
                time.sleep(REQUEST_DELAY)
        
        print(f"\n   [{symbol}] Total collected: {symbol_total} records")
        total_collected += symbol_total
    
    print("\n" + "=" * 80)
    print("Collection Summary")
    print("=" * 80)
    print(f"Total records collected: {total_collected}")
    print()
    print("Note: Actual new records may be less due to database deduplication")
    print()
    print("Next step: Run diagnose_cross_pair_data.py to verify data completeness")
    print("=" * 80)

if __name__ == "__main__":
    main()

