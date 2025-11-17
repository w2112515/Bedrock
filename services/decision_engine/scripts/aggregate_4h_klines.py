"""
从1小时K线聚合生成4小时K线数据

聚合规则：
- open_price = 第1条的open_price
- high_price = 4条中的最高价
- low_price = 4条中的最低价
- close_price = 第4条的close_price
- volume = 4条的volume总和
- open_time = 第1条的open_time
- close_time = 第4条的close_time
"""
from sqlalchemy import create_engine, text
from datetime import datetime
import sys

db_url = "postgresql://bedrock:bedrock_password@localhost:5432/bedrock_db"
engine = create_engine(db_url)

print("=" * 100)
print("从1小时K线聚合生成4小时K线")
print("=" * 100)

# 获取所有币种
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT DISTINCT symbol FROM klines WHERE interval = '1h' ORDER BY symbol
    """))
    symbols = [row[0] for row in result]
    
    print(f"\n发现{len(symbols)}个币种: {', '.join(symbols)}")
    
    total_inserted = 0
    total_skipped = 0
    
    for symbol in symbols:
        print(f"\n处理 {symbol}...")
        
        # 获取该币种的所有1小时K线，按时间排序
        result = conn.execute(text("""
            SELECT open_time, close_time, open_price, high_price, low_price, 
                   close_price, volume, quote_volume, trade_count, 
                   taker_buy_base_volume, taker_buy_quote_volume, source
            FROM klines
            WHERE symbol = :symbol AND interval = '1h'
            ORDER BY open_time
        """), {"symbol": symbol})
        
        klines_1h = list(result)
        print(f"  找到{len(klines_1h)}条1小时K线")
        
        if len(klines_1h) < 4:
            print(f"  [WARN] 数据不足4条，跳过")
            continue
        
        # 每4条1小时K线聚合为1条4小时K线
        inserted = 0
        skipped = 0
        
        for i in range(0, len(klines_1h) - 3, 4):
            chunk = klines_1h[i:i+4]
            
            # 聚合数据
            aggregated = {
                'symbol': symbol,
                'interval': '4h',
                'open_time': chunk[0][0],  # 第1条的open_time
                'close_time': chunk[3][1],  # 第4条的close_time
                'open_price': chunk[0][2],  # 第1条的open_price
                'high_price': max(k[3] for k in chunk),  # 4条中的最高价
                'low_price': min(k[4] for k in chunk),  # 4条中的最低价
                'close_price': chunk[3][5],  # 第4条的close_price
                'volume': sum(k[6] for k in chunk),  # volume总和
                'quote_volume': sum(k[7] for k in chunk) if all(k[7] is not None for k in chunk) else None,
                'trade_count': sum(k[8] for k in chunk) if all(k[8] is not None for k in chunk) else None,
                'taker_buy_base_volume': sum(k[9] for k in chunk) if all(k[9] is not None for k in chunk) else None,
                'taker_buy_quote_volume': sum(k[10] for k in chunk) if all(k[10] is not None for k in chunk) else None,
                'source': chunk[0][11]  # 使用第1条的source
            }
            
            # 检查是否已存在
            existing = conn.execute(text("""
                SELECT COUNT(*) FROM klines
                WHERE symbol = :symbol AND interval = :interval AND open_time = :open_time
            """), {
                'symbol': aggregated['symbol'],
                'interval': aggregated['interval'],
                'open_time': aggregated['open_time']
            }).scalar()
            
            if existing > 0:
                skipped += 1
                continue
            
            # 插入聚合后的4小时K线
            conn.execute(text("""
                INSERT INTO klines (
                    symbol, interval, open_time, close_time, open_price, high_price, 
                    low_price, close_price, volume, quote_volume, trade_count, 
                    taker_buy_base_volume, taker_buy_quote_volume, source
                ) VALUES (
                    :symbol, :interval, :open_time, :close_time, :open_price, :high_price,
                    :low_price, :close_price, :volume, :quote_volume, :trade_count,
                    :taker_buy_base_volume, :taker_buy_quote_volume, :source
                )
            """), aggregated)
            
            inserted += 1
        
        conn.commit()
        print(f"  [OK] 插入{inserted}条4小时K线，跳过{skipped}条已存在")
        total_inserted += inserted
        total_skipped += skipped

print("\n" + "=" * 100)
print(f"聚合完成！总计插入{total_inserted}条4小时K线，跳过{total_skipped}条已存在")
print("=" * 100)

# 验证结果
print("\n验证聚合结果...")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT symbol, COUNT(*) as count, MIN(open_time) as start_time, MAX(open_time) as end_time
        FROM klines
        WHERE interval = '4h'
        GROUP BY symbol
        ORDER BY symbol
    """))
    
    print(f"\n{'Symbol':<10} {'Count':<10} {'Start Time':<25} {'End Time':<25}")
    print("-" * 80)
    for row in result:
        start_dt = datetime.fromtimestamp(row[2] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        end_dt = datetime.fromtimestamp(row[3] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{row[0]:<10} {row[1]:<10} {start_dt:<25} {end_dt:<25}")

print("\n" + "=" * 100)

