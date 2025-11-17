#!/usr/bin/env python3
"""
批量历史K线数据收集脚本

功能:
- 收集多个交易对的历史K线数据
- 按月分批收集，避免API限流
- 自动重试失败任务
- 实时进度跟踪
- 数据完整性验证
- 生成收集报告

使用方法:
    python scripts/collect_historical_data_batch.py
"""

import sys
import os
import time
import json
import requests
from datetime import datetime, date
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import psycopg2
from psycopg2.extras import RealDictCursor

# 配置
DATAHUB_URL = "http://localhost:8001"
DATABASE_URL = "postgresql://bedrock:bedrock_password@localhost:5432/bedrock_db"

# 收集配置
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
INTERVAL = "1h"
YEARS = [2024, 2025]
REQUEST_DELAY = 2  # 每次请求后延迟秒数
MAX_RETRIES = 3    # 最大重试次数

# 跳过已有数据的配置（设置为True可以跳过已有完整数据的交易对）
SKIP_EXISTING = {
    ("BTCUSDT", 2024): True,  # 已有8776条
    ("BTCUSDT", 2025): True,  # 已有508条
    ("ETHUSDT", 2024): True,  # 已有8776条
    ("ETHUSDT", 2025): True,  # 已有508条
}


@dataclass
class CollectionTask:
    """数据收集任务"""
    symbol: str
    interval: str
    year: int
    month: int
    status: str = "PENDING"  # PENDING, SUCCESS, FAILED
    records_collected: int = 0
    error_message: Optional[str] = None
    attempts: int = 0


@dataclass
class CollectionReport:
    """数据收集报告"""
    start_time: str
    end_time: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_records: int = 0
    tasks: List[Dict] = None
    
    def __post_init__(self):
        if self.tasks is None:
            self.tasks = []


class DataCollector:
    """数据收集器"""
    
    def __init__(self, datahub_url: str):
        self.datahub_url = datahub_url
        self.session = requests.Session()
    
    def collect_month(self, symbol: str, interval: str, year: int, month: int) -> Dict:
        """
        收集单个月份的数据
        
        Args:
            symbol: 交易对符号
            interval: K线间隔
            year: 年份
            month: 月份
        
        Returns:
            收集结果字典
        """
        # 计算月份的开始和结束日期
        start_date = date(year, month, 1)
        
        # 计算下个月的第一天
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        
        # 结束日期是下个月第一天的前一天
        from datetime import timedelta
        end_date = next_month - timedelta(days=1)
        
        # 如果是未来日期，使用今天作为结束日期
        today = date.today()
        if end_date > today:
            end_date = today
        
        # 如果开始日期在未来，跳过
        if start_date > today:
            return {
                "success": True,
                "records_collected": 0,
                "message": "Future date, skipped"
            }
        
        # 调用DataHub API
        url = f"{self.datahub_url}/v1/klines/collect"

        # 转换日期为datetime（使用UTC时间）
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        payload = {
            "symbol": symbol,
            "interval": interval,
            "start_time": start_datetime.isoformat() + "Z",
            "end_time": end_datetime.isoformat() + "Z",
            "limit": 1000  # 使用最大限制
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "records_collected": result.get("records_collected", 0),
                "message": result.get("message", "Success")
            }
        
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "records_collected": 0,
                "message": str(e)
            }


class DataValidator:
    """数据验证器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
    
    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(self.database_url)
    
    def validate_symbol_data(self, symbol: str, interval: str, year: int) -> Dict:
        """
        验证交易对数据完整性
        
        Args:
            symbol: 交易对符号
            interval: K线间隔
            year: 年份
        
        Returns:
            验证结果字典
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # 计算年份的时间戳范围
            start_ts = int(datetime(year, 1, 1).timestamp() * 1000)
            end_ts = int(datetime(year + 1, 1, 1).timestamp() * 1000)

            # 查询记录数和时间范围
            query = """
                SELECT
                    COUNT(*) as total_records,
                    MIN(open_time) as earliest_ts,
                    MAX(open_time) as latest_ts
                FROM klines
                WHERE symbol = %s
                  AND interval = %s
                  AND open_time >= %s
                  AND open_time < %s
            """

            cursor.execute(query, (symbol, interval, start_ts, end_ts))
            result = cursor.fetchone()

            if result['total_records'] == 0:
                return {
                    "symbol": symbol,
                    "interval": interval,
                    "year": year,
                    "total_records": 0,
                    "earliest": None,
                    "latest": None,
                    "status": "NO_DATA"
                }

            earliest = datetime.fromtimestamp(result['earliest_ts'] / 1000)
            latest = datetime.fromtimestamp(result['latest_ts'] / 1000)

            return {
                "symbol": symbol,
                "interval": interval,
                "year": year,
                "total_records": result['total_records'],
                "earliest": earliest.isoformat(),
                "latest": latest.isoformat(),
                "status": "OK"
            }

        finally:
            cursor.close()
            conn.close()


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, total_tasks: int):
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.start_time = datetime.now()

    def update(self, task: CollectionTask):
        """更新进度"""
        if task.status == "SUCCESS":
            self.completed_tasks += 1
        elif task.status == "FAILED":
            self.failed_tasks += 1

        # 计算进度百分比
        progress = (self.completed_tasks + self.failed_tasks) / self.total_tasks * 100

        # 计算预估剩余时间
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if self.completed_tasks > 0:
            avg_time_per_task = elapsed / (self.completed_tasks + self.failed_tasks)
            remaining_tasks = self.total_tasks - self.completed_tasks - self.failed_tasks
            eta_seconds = avg_time_per_task * remaining_tasks
            eta_minutes = eta_seconds / 60
        else:
            eta_minutes = 0

        # 打印进度
        status_icon = "✅" if task.status == "SUCCESS" else "❌"
        print(f"{status_icon} [{progress:5.1f}%] {task.symbol} {task.year}-{task.month:02d} | "
              f"Records: {task.records_collected:4d} | "
              f"ETA: {eta_minutes:.1f}min | "
              f"Success: {self.completed_tasks}/{self.total_tasks} | "
              f"Failed: {self.failed_tasks}")

        if task.status == "FAILED":
            print(f"   ⚠️  Error: {task.error_message}")


def main():
    """主函数"""
    print("=" * 80)
    print("批量历史K线数据收集脚本")
    print("=" * 80)
    print()

    # 初始化
    collector = DataCollector(DATAHUB_URL)
    validator = DataValidator(DATABASE_URL)

    # 生成任务列表
    tasks: List[CollectionTask] = []
    for symbol in SYMBOLS:
        for year in YEARS:
            # 跳过已有数据的交易对
            if SKIP_EXISTING.get((symbol, year), False):
                print(f"⏭️  跳过 {symbol} {year}（数据已存在）")
                continue

            for month in range(1, 13):
                tasks.append(CollectionTask(
                    symbol=symbol,
                    interval=INTERVAL,
                    year=year,
                    month=month
                ))

    print(f"📋 总任务数: {len(tasks)}")
    print(f"📊 交易对: {', '.join(SYMBOLS)}")
    print(f"📅 时间范围: {YEARS[0]}-{YEARS[-1]}")
    print(f"⏱️  时间粒度: {INTERVAL}")
    print(f"🔄 重试次数: {MAX_RETRIES}")
    print(f"⏳ 请求延迟: {REQUEST_DELAY}秒")
    print()
    print("开始收集数据...")
    print()

    # 初始化进度跟踪器
    tracker = ProgressTracker(len(tasks))

    # 初始化报告
    report = CollectionReport(
        start_time=datetime.now().isoformat(),
        total_tasks=len(tasks)
    )

    # 执行任务
    for task in tasks:
        # 重试逻辑
        for attempt in range(MAX_RETRIES):
            task.attempts = attempt + 1

            # 收集数据
            result = collector.collect_month(
                symbol=task.symbol,
                interval=task.interval,
                year=task.year,
                month=task.month
            )

            if result["success"]:
                task.status = "SUCCESS"
                task.records_collected = result["records_collected"]
                break
            else:
                task.error_message = result["message"]

                if attempt < MAX_RETRIES - 1:
                    # 等待后重试
                    time.sleep(5)
                else:
                    # 最后一次尝试失败
                    task.status = "FAILED"

        # 更新进度
        tracker.update(task)

        # 延迟，避免API限流
        if task != tasks[-1]:  # 最后一个任务不需要延迟
            time.sleep(REQUEST_DELAY)

    # 完成收集
    report.end_time = datetime.now().isoformat()
    report.completed_tasks = tracker.completed_tasks
    report.failed_tasks = tracker.failed_tasks
    report.total_records = sum(t.records_collected for t in tasks)
    report.tasks = [asdict(t) for t in tasks]

    # 打印摘要
    print()
    print("=" * 80)
    print("数据收集完成")
    print("=" * 80)
    print(f"✅ 成功任务: {report.completed_tasks}/{report.total_tasks}")
    print(f"❌ 失败任务: {report.failed_tasks}/{report.total_tasks}")
    print(f"📊 总记录数: {report.total_records:,}")

    elapsed = (datetime.fromisoformat(report.end_time) -
               datetime.fromisoformat(report.start_time)).total_seconds()
    print(f"⏱️  总耗时: {elapsed/60:.1f}分钟")
    print()

    # 保存报告
    report_path = "scripts/data_collection_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False)
    print(f"📄 报告已保存: {report_path}")
    print()

    # 数据验证
    print("=" * 80)
    print("数据完整性验证")
    print("=" * 80)
    print()

    validation_results = []
    for symbol in SYMBOLS:
        for year in YEARS:
            result = validator.validate_symbol_data(symbol, INTERVAL, year)
            validation_results.append(result)

            if result["status"] == "OK":
                print(f"✅ {symbol} {year}: {result['total_records']:,}条记录 | "
                      f"{result['earliest'][:10]} ~ {result['latest'][:10]}")
            elif result["status"] == "NO_DATA":
                print(f"⚠️  {symbol} {year}: 无数据")

    print()

    # 保存验证报告
    validation_report_path = "scripts/data_validation_report.json"
    with open(validation_report_path, "w", encoding="utf-8") as f:
        json.dump(validation_results, f, indent=2, ensure_ascii=False)
    print(f"📄 验证报告已保存: {validation_report_path}")
    print()

    # 失败任务摘要
    if report.failed_tasks > 0:
        print("=" * 80)
        print("失败任务详情")
        print("=" * 80)
        print()

        failed_tasks = [t for t in tasks if t.status == "FAILED"]
        for task in failed_tasks:
            print(f"❌ {task.symbol} {task.year}-{task.month:02d}")
            print(f"   错误: {task.error_message}")
            print(f"   尝试次数: {task.attempts}")
            print()

    # 返回状态码
    return 0 if report.failed_tasks == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

