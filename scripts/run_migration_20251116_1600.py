"""
临时迁移脚本：手动执行20251116_1600迁移
用途：在无法使用alembic的情况下，直接连接数据库执行迁移SQL
"""
import psycopg2
import os
import sys

def main():
    # 从环境变量读取数据库连接信息
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_user = os.getenv("POSTGRES_USER", "bedrock")
    db_password = os.getenv("POSTGRES_PASSWORD", "bedrock_password")
    db_name = os.getenv("POSTGRES_DB", "bedrock_db")
    
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print(f"连接数据库: {db_host}:{db_port}/{db_name}")
    
    try:
        # 连接数据库
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor()
        
        # 检查当前迁移版本
        print("\n检查当前迁移版本...")
        cursor.execute("SELECT version_num FROM alembic_version;")
        current_version = cursor.fetchone()
        if current_version:
            print(f"当前版本: {current_version[0]}")
        else:
            print("警告: 未找到alembic_version记录")
        
        # 检查arbitration_config表是否存在
        print("\n检查arbitration_config表...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'arbitration_config'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("错误: arbitration_config表不存在，请先运行前置迁移")
            sys.exit(1)
        
        # 检查当前配置
        print("\n检查当前配置...")
        cursor.execute("""
            SELECT version, rule_weight, ml_weight, llm_weight, is_active 
            FROM arbitration_config 
            ORDER BY version;
        """)
        configs = cursor.fetchall()
        print("现有配置:")
        for config in configs:
            print(f"  Version {config[0]}: rule={config[1]}, ml={config[2]}, llm={config[3]}, active={config[4]}")
        
        # 检查是否已有正确的权重配置
        cursor.execute("""
            SELECT COUNT(*) FROM arbitration_config
            WHERE rule_weight = 0.55 AND ml_weight = 0.15 AND llm_weight = 0.3;
        """)
        correct_config_exists = cursor.fetchone()[0] > 0

        if correct_config_exists:
            print("\n警告: 正确的权重配置已存在，跳过迁移")
            conn.close()
            return

        # 获取下一个version号
        cursor.execute("SELECT MAX(version) FROM arbitration_config;")
        max_version = cursor.fetchone()[0]
        next_version = (max_version or 0) + 1

        # 执行迁移
        print(f"\n执行迁移（创建version {next_version}）...")

        # 1. 停用旧配置
        print("  1. 停用所有旧配置...")
        cursor.execute("UPDATE arbitration_config SET is_active = false WHERE is_active = true;")

        # 2. 插入新配置
        print(f"  2. 插入version {next_version}配置（rule=0.55, ml=0.15, llm=0.3）...")
        cursor.execute(f"""
            INSERT INTO arbitration_config (
                id, version, rule_weight, ml_weight, llm_weight,
                min_approval_score, adaptive_threshold_enabled, is_active, created_at
            )
            VALUES (
                gen_random_uuid(),
                {next_version},
                0.55,
                0.15,
                0.3,
                70.0,
                false,
                true,
                now()
            );
        """)
        
        # 3. 更新alembic_version表
        print("  3. 更新alembic_version表...")
        cursor.execute("""
            UPDATE alembic_version 
            SET version_num = '20251116_1600';
        """)
        
        # 提交事务
        conn.commit()
        print("\n✅ 迁移成功！")
        
        # 验证结果
        print("\n验证迁移结果...")
        cursor.execute("""
            SELECT version, rule_weight, ml_weight, llm_weight, is_active 
            FROM arbitration_config 
            ORDER BY version;
        """)
        configs = cursor.fetchall()
        print("迁移后配置:")
        for config in configs:
            print(f"  Version {config[0]}: rule={config[1]}, ml={config[2]}, llm={config[3]}, active={config[4]}")
        
        cursor.execute("SELECT version_num FROM alembic_version;")
        new_version = cursor.fetchone()[0]
        print(f"\n当前迁移版本: {new_version}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)

if __name__ == "__main__":
    main()

