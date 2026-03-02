import sqlite3

DB_PATH = '/root/.openclaw/workspace/crypto_dashboard/quant_ledger.db'

def reset_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("--- 正在彻底重建 open_positions 表 ---")
        cursor.execute("DROP TABLE IF EXISTS open_positions")
        
        cursor.execute("""
        CREATE TABLE open_positions (
            symbol TEXT NOT NULL,
            entry_time INTEGER NOT NULL,
            side TEXT,
            size REAL,
            value_usdt REAL,
            margin REAL,
            leverage INTEGER,
            entry_price REAL,
            funding_fee_paid REAL DEFAULT 0,
            estimated_funding_fee REAL DEFAULT 0,
            PRIMARY KEY (symbol, entry_time)
        )
        """)
        
        # 插入两条干净的模拟数据（COS 和 KNC）
        # 时间戳用现在的，防止被旧逻辑干扰
        now = int(time.time())
        # COSUSDT
        cursor.execute("INSERT INTO open_positions (symbol, entry_time, side, size, value_usdt, margin, leverage, entry_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       ('COSUSDT', now - 3600, 'LONG', 10000.0, 1000.0, 100.0, 10, 0.1))
        # KNCUSDT
        cursor.execute("INSERT INTO open_positions (symbol, entry_time, side, size, value_usdt, margin, leverage, entry_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       ('KNCUSDT', now - 1800, 'LONG', 200.0, 1000.0, 100.0, 10, 5.0))
        
        # 校准 system_state
        cursor.execute("UPDATE system_state SET margin_used = 200.0 WHERE id = 1")
        
        conn.commit()
        conn.close()
        print("数据库重置成功！已保留 2 个干净仓位。")
    except Exception as e:
        print(f"重置失败: {e}")

if __name__ == "__main__":
    import time
    reset_db()
