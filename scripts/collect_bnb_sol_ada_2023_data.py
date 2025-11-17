#!/usr/bin/env python3
"""
补充BNB/SOL/ADA 2023年历史数据

目标: 将BNB/SOL/ADA的数据量从16,422条增加至25,204条，与BTC/ETH对齐
策略: 收集2023年1月1日至2023年12月31日的1小时K线数据
"""

import sys
import time
import requests
from datetime import datetime, date
from typing import Dict, Any

# 配置
DATAHUB_URL = "http://localhost:8001"

SYMBOLS = ["BNBUSDT", "SOLUSDT", "ADAUSDT"]
INTERVAL = "1h"
YEAR = 2023
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
    print("BNB/SOL/ADA 2023 Historical Data Collection")
    print("=" * 80)
    print(f"Target: Align BNB/SOL/ADA data with BTC/ETH (25,204 records)")
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

