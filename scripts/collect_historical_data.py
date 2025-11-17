"""
历史K线数据收集脚本
用途：批量收集2024年全年的BTC/USDT和ETH/USDT 1小时K线数据
"""
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any

# 配置
DATAHUB_URL = "http://localhost:8001"
SYMBOLS = ["BTCUSDT", "ETHUSDT"]  # 收集BTC和ETH数据
INTERVAL = "1h"
YEAR = 2024

def collect_monthly_data(symbol: str, year: int, month: int) -> Dict[str, Any]:
    """收集指定月份的K线数据"""
    # 计算月份的开始和结束日期
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

    payload = {
        "symbol": symbol,
        "interval": INTERVAL,
        "start_time": start_date.isoformat(),
        "end_time": end_date.isoformat(),
        "limit": 1000
    }

    print(f"📅 收集 {symbol} {year}-{month:02d} 数据...")
    print(f"   时间范围: {start_date} 到 {end_date}")

    try:
        response = requests.post(
            f"{DATAHUB_URL}/v1/klines/collect",
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 成功: {result['message']}")
            return {"success": True, "count": result.get("count", 0), "month": f"{year}-{month:02d}", "symbol": symbol}
        else:
            print(f"   ❌ 失败: HTTP {response.status_code} - {response.text}")
            return {"success": False, "error": response.text, "month": f"{year}-{month:02d}", "symbol": symbol}

    except Exception as e:
        print(f"   ❌ 异常: {str(e)}")
        return {"success": False, "error": str(e), "month": f"{year}-{month:02d}", "symbol": symbol}

def main():
    """主函数：收集2024年全年数据"""
    print("=" * 60)
    print("🚀 开始收集2024年历史K线数据")
    print(f"   交易对: {', '.join(SYMBOLS)}")
    print(f"   时间间隔: {INTERVAL}")
    print(f"   DataHub URL: {DATAHUB_URL}")
    print("=" * 60)

    all_results = {}
    
    for symbol in SYMBOLS:
        print(f"\n{'=' * 60}")
        print(f"📊 开始收集 {symbol} 数据")
        print(f"{'=' * 60}")
        
        results = []
        total_count = 0

        for month in range(1, 13):
            result = collect_monthly_data(symbol, YEAR, month)
            results.append(result)

            if result["success"]:
                total_count += result.get("count", 0)

            # 避免API限流，每次请求后等待2秒
            if month < 12 or symbol != SYMBOLS[-1]:
                time.sleep(2)

        all_results[symbol] = {
            "results": results,
            "total_count": total_count
        }

        # 打印该交易对的汇总
        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count

        print(f"\n📊 {symbol} 数据收集汇总")
        print(f"   ✅ 成功: {success_count}/12 个月")
        print(f"   ❌ 失败: {fail_count}/12 个月")
        print(f"   📈 总计收集: {total_count} 条K线数据")

        if fail_count > 0:
            print(f"\n   失败的月份:")
            for r in results:
                if not r["success"]:
                    print(f"      - {r['month']}: {r.get('error', 'Unknown error')}")

    # 打印总汇总报告
    print("\n" + "=" * 60)
    print("📊 全部数据收集汇总报告")
    print("=" * 60)
    
    grand_total = 0
    for symbol, data in all_results.items():
        success_count = sum(1 for r in data["results"] if r["success"])
        print(f"{symbol}: {success_count}/12 个月成功, 共 {data['total_count']} 条K线")
        grand_total += data["total_count"]
    
    print(f"\n📈 总计收集: {grand_total} 条K线数据")
    print("=" * 60)

    # 返回状态码
    all_success = all(
        all(r["success"] for r in data["results"])
        for data in all_results.values()
    )
    return 0 if all_success else 1

if __name__ == "__main__":
    exit(main())

