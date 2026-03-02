import sqlite3
import time

DB_PATH = '/root/.openclaw/workspace/crypto_dashboard/quant_ledger.db'

def fix():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("--- 升级 open_positions 表结构 ---")
        columns = [
            ("side", "TEXT DEFAULT 'LONG'"),
            ("size", "REAL DEFAULT 0"),
            ("value_usdt", "REAL DEFAULT 0"),
            ("margin", "REAL DEFAULT 0"),
            ("leverage", "INTEGER DEFAULT 1"),
            ("entry_price", "REAL DEFAULT 0"),
            ("funding_fee_paid", "REAL DEFAULT 0")
        ]
        for col, dtype in columns:
            try:
                cursor.execute(f"ALTER TABLE open_positions ADD COLUMN {col} {dtype}")
                print(f"已添加列: {col}")
            except sqlite3.OperationalError:
                pass

        print("\n--- 清理重复仓位 ---")
        cursor.execute("SELECT symbol, MAX(entry_time) FROM open_positions GROUP BY symbol")
        latest_positions = cursor.fetchall()
        
        times_to_keep = [p[1] for p in latest_positions]
        
        if times_to_keep:
            placeholders = ', '.join(['?'] * len(times_to_keep))
            cursor.execute(f"DELETE FROM open_positions WHERE entry_time NOT IN ({placeholders})", times_to_keep)
            print(f"删除了 {cursor.rowcount} 个冗余仓位")

        cursor.execute("SELECT COUNT(*) FROM open_positions")
        count = cursor.fetchone()[0]
        actual_margin = count * 100.0 # 强制校准
        
        cursor.execute("UPDATE system_state SET margin_used = ? WHERE id = 1", (actual_margin,))
        print(f"已校准 MarginUsed: {actual_margin} (基于 {count} 个仓位)")

        conn.commit()
        conn.close()
        print("\n数据库修复完成！")
    except Exception as e:
        print(f"修复失败: {e}")

if __name__ == "__main__":
    fix()
