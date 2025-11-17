"""
TD-001a: 收集历史K线数据

功能：
- 从Binance API回填2024年全年K线数据
- 币种：BTCUSDT、ETHUSDT、BNBUSDT、SOLUSDT、ADAUSDT
- 粒度：1小时K线
- 支持断点续传
- 数据验证和质量检查
"""
import requests
import psycopg2
import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
import json

class KlineCollector:
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
        self.interval = "1h"
        self.start_date = "2024-01-01 00:00:00"
        self.end_date = "2024-12-31 23:59:59"
        self.batch_size = 1000
        self.rate_limit_delay = 0.5
        
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_user = os.getenv("POSTGRES_USER", "bedrock")
        db_password = os.getenv("POSTGRES_PASSWORD", "bedrock_password")
        db_name = os.getenv("POSTGRES_DB", "bedrock_db")
        
        self.db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        self.progress_file = "/tmp/kline_collection_progress.json"
    
    def get_timestamp_ms(self, date_str: str) -> int:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    
    def load_progress(self) -> Dict[str, int]:
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_progress(self, progress: Dict[str, int]):
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
    
    def fetch_klines(self, symbol: str, start_time: int, end_time: int) -> List[List]:
        url = f"{self.base_url}/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": self.interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": self.batch_size
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"  ❌ API请求失败: {e}")
            return []
    
    def validate_kline(self, kline: List) -> bool:
        try:
            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])
            volume = float(kline[5])
            
            if high_price < low_price:
                return False
            if open_price < 0 or close_price < 0:
                return False
            if volume < 0:
                return False
            if not (low_price <= open_price <= high_price):
                return False
            if not (low_price <= close_price <= high_price):
                return False
            
            return True
        except (ValueError, IndexError):
            return False
    
    def insert_klines(self, conn, symbol: str, klines: List[List]) -> Tuple[int, int]:
        cursor = conn.cursor()
        inserted = 0
        skipped = 0
        
        for kline in klines:
            if not self.validate_kline(kline):
                skipped += 1
                continue
            
            try:
                cursor.execute("""
                    INSERT INTO klines (
                        symbol, interval, open_time, close_time, open_price, high_price,
                        low_price, close_price, volume, quote_volume, trade_count,
                        taker_buy_base_volume, taker_buy_quote_volume, source
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (symbol, interval, open_time) DO UPDATE SET
                        close_time = EXCLUDED.close_time,
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        quote_volume = EXCLUDED.quote_volume,
                        trade_count = EXCLUDED.trade_count,
                        taker_buy_base_volume = EXCLUDED.taker_buy_base_volume,
                        taker_buy_quote_volume = EXCLUDED.taker_buy_quote_volume;
                """, (
                    symbol, self.interval, kline[0], kline[6],
                    kline[1], kline[2], kline[3], kline[4],
                    kline[5], kline[7], kline[8], kline[9], kline[10],
                    'binance'
                ))
                inserted += 1
            except Exception as e:
                print(f"  ⚠️ 插入失败: {e}")
                skipped += 1
        
        conn.commit()
        cursor.close()
        return inserted, skipped

    def collect_symbol(self, symbol: str, conn):
        print(f"\n{'='*60}")
        print(f"开始收集 {symbol} 的K线数据")
        print(f"{'='*60}")

        start_time_ms = self.get_timestamp_ms(self.start_date)
        end_time_ms = self.get_timestamp_ms(self.end_date)

        progress = self.load_progress()
        current_time_ms = progress.get(symbol, start_time_ms)

        if current_time_ms > start_time_ms:
            current_dt = datetime.fromtimestamp(current_time_ms / 1000, tz=timezone.utc)
            print(f"从断点续传: {current_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        total_inserted = 0
        total_skipped = 0
        batch_count = 0

        while current_time_ms < end_time_ms:
            batch_count += 1
            current_dt = datetime.fromtimestamp(current_time_ms / 1000, tz=timezone.utc)
            print(f"\n批次 {batch_count}: {current_dt.strftime('%Y-%m-%d %H:%M:%S')}")

            klines = self.fetch_klines(symbol, current_time_ms, end_time_ms)

            if not klines:
                print(f"  ⚠️ 未获取到数据，跳过")
                break

            inserted, skipped = self.insert_klines(conn, symbol, klines)
            total_inserted += inserted
            total_skipped += skipped

            print(f"  ✅ 插入: {inserted}, 跳过: {skipped}")

            last_kline_time = klines[-1][0]
            current_time_ms = last_kline_time + 1

            progress[symbol] = current_time_ms
            self.save_progress(progress)

            if len(klines) < self.batch_size:
                print(f"  ℹ️ 已到达数据末尾")
                break

            time.sleep(self.rate_limit_delay)

        print(f"\n{symbol} 收集完成:")
        print(f"  - 总插入: {total_inserted}")
        print(f"  - 总跳过: {total_skipped}")
        print(f"  - 总批次: {batch_count}")

        return total_inserted, total_skipped

    def verify_data(self, conn, symbol: str) -> Dict:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_count,
                MIN(to_timestamp(open_time/1000.0)) as min_time,
                MAX(to_timestamp(open_time/1000.0)) as max_time,
                COUNT(DISTINCT DATE(to_timestamp(open_time/1000.0))) as unique_days
            FROM klines
            WHERE symbol = %s AND interval = %s;
        """, (symbol, self.interval))

        result = cursor.fetchone()

        cursor.execute("""
            SELECT to_timestamp(open_time/1000.0), to_timestamp(close_time/1000.0)
            FROM klines
            WHERE symbol = %s AND interval = %s
            ORDER BY open_time;
        """, (symbol, self.interval))

        rows = cursor.fetchall()
        gaps = []

        for i in range(len(rows) - 1):
            current_close = rows[i][1]
            next_open = rows[i + 1][0]
            expected_next = current_close + (rows[i][1] - rows[i][0])

            if next_open > expected_next:
                gap_hours = (next_open - expected_next).total_seconds() / 3600
                if gap_hours > 1:
                    gaps.append({
                        'from': current_close.strftime('%Y-%m-%d %H:%M:%S'),
                        'to': next_open.strftime('%Y-%m-%d %H:%M:%S'),
                        'gap_hours': gap_hours
                    })

        cursor.close()

        return {
            'total_count': result[0],
            'min_time': result[1].strftime('%Y-%m-%d %H:%M:%S') if result[1] else None,
            'max_time': result[2].strftime('%Y-%m-%d %H:%M:%S') if result[2] else None,
            'unique_days': result[3],
            'gaps': gaps
        }

    def run(self):
        print("="*60)
        print("TD-001a: 收集历史K线数据")
        print("="*60)
        print(f"时间范围: {self.start_date} ~ {self.end_date}")
        print(f"币种: {', '.join(self.symbols)}")
        print(f"粒度: {self.interval}")
        print(f"批次大小: {self.batch_size}")
        print("="*60)

        try:
            conn = psycopg2.connect(self.db_url)
            print("\n✅ 数据库连接成功")

            summary = {}

            for symbol in self.symbols:
                inserted, skipped = self.collect_symbol(symbol, conn)
                summary[symbol] = {
                    'inserted': inserted,
                    'skipped': skipped
                }

            print(f"\n{'='*60}")
            print("数据验证")
            print(f"{'='*60}")

            for symbol in self.symbols:
                print(f"\n{symbol}:")
                verification = self.verify_data(conn, symbol)
                print(f"  - 总记录数: {verification['total_count']}")
                print(f"  - 时间范围: {verification['min_time']} ~ {verification['max_time']}")
                print(f"  - 覆盖天数: {verification['unique_days']}")

                if verification['gaps']:
                    print(f"  ⚠️ 发现 {len(verification['gaps'])} 个时间间隙:")
                    for gap in verification['gaps'][:5]:
                        print(f"    - {gap['from']} ~ {gap['to']} (间隔: {gap['gap_hours']:.1f}小时)")
                else:
                    print(f"  ✅ 无时间间隙")

            conn.close()

            print(f"\n{'='*60}")
            print("✅ TD-001a 执行完成")
            print(f"{'='*60}")

            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
                print("✅ 进度文件已清理")

        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    collector = KlineCollector()
    collector.run()


