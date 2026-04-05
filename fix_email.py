"""Quick fix: make email column nullable and fix phone column."""
import os
from dotenv import load_dotenv
import pymysql

load_dotenv()
conn = pymysql.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASSWORD", ""),
    database=os.environ.get("DB_NAME", "finance_manager"),
    charset="utf8mb4",
)
cur = conn.cursor()
cur.execute("ALTER TABLE users MODIFY COLUMN email VARCHAR(120) NULL DEFAULT NULL")
cur.execute("ALTER TABLE users MODIFY COLUMN phone VARCHAR(20) NULL DEFAULT NULL")
conn.commit()
conn.close()
print("Fixed: email and phone are now nullable.")
