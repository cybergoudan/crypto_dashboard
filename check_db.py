import sqlite3
import json

try:
    conn = sqlite3.connect('/root/.openclaw/workspace/crypto_dashboard/quant_ledger.db')
    cursor = conn.cursor()
    
    print("--- open_positions 表内容 ---")
    cursor.execute("SELECT * FROM open_positions")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    print("\n--- system_state 表内容 ---")
    cursor.execute("SELECT * FROM system_state")
    row = cursor.fetchone()
    if row:
        print(f"ID: {row[0]}, Balance: {row[1]}, MarginUsed: {row[2]}")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
