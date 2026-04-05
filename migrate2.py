"""Add missing columns to subscriptions and other tables."""
import os
from dotenv import load_dotenv
import pymysql

load_dotenv()

DB = os.environ.get("DB_NAME", "finance_manager")
conn = pymysql.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASSWORD", ""),
    database=DB, charset="utf8mb4",
)
cur = conn.cursor()


def col_exists(table, col):
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (DB, table, col))
    return cur.fetchone()[0] > 0


def add_col(table, col, defn):
    if col_exists(table, col):
        print(f"  – {table}.{col} already exists")
    else:
        cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{col}` {defn}")
        print(f"  ✓ Added {table}.{col}")


# subscriptions
add_col("subscriptions", "created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
add_col("subscriptions", "category",   "VARCHAR(50) DEFAULT 'Other'")
add_col("subscriptions", "notes",      "VARCHAR(255)")
add_col("subscriptions", "is_active",  "TINYINT(1) NOT NULL DEFAULT 1")

# trips
add_col("trips", "notes",   "VARCHAR(255)")
add_col("trips", "status",  "ENUM('planning','active','completed') DEFAULT 'planning'")
add_col("trips", "created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")

# rooms
add_col("rooms", "description", "VARCHAR(255)")
add_col("rooms", "is_active",   "TINYINT(1) NOT NULL DEFAULT 1")
add_col("rooms", "created_at",  "DATETIME DEFAULT CURRENT_TIMESTAMP")

# room_members
add_col("room_members", "contact",    "VARCHAR(120)")
add_col("room_members", "user_id",    "INT NULL")
add_col("room_members", "joined_at",  "DATETIME DEFAULT CURRENT_TIMESTAMP")

# room_expense_participants
add_col("room_expense_participants", "is_settled", "TINYINT(1) NOT NULL DEFAULT 0")

# alerts
add_col("alerts", "is_read", "TINYINT(1) NOT NULL DEFAULT 0")

# expenses
add_col("expenses", "updated_at", "TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
add_col("expenses", "payment_method", "VARCHAR(50) DEFAULT 'Cash'")

# users  
add_col("users", "currency", "VARCHAR(10) DEFAULT '₹'")

conn.commit()
conn.close()
print("\n✓ All columns ensured.")
