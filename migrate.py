import sqlite3
import os

db_path = r"C:\Users\Lodebek\.gemini\antigravity\scratch\ai_dm_assistant\aidm_database.db"

if not os.path.exists(db_path):
    print("DB does not exist, no migration needed.")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE documents ADD COLUMN content_hash VARCHAR")
    cursor.execute("ALTER TABLE documents ADD COLUMN last_synced_at DATETIME")
    conn.commit()
    print("Added columns successfully.")
except Exception as e:
    print(f"Error or columns already exist: {e}")
finally:
    conn.close()
