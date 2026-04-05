"""
Migration — safely adds new columns to existing finance_manager tables.
Checks INFORMATION_SCHEMA before each ALTER so it's safe to re-run.
"""
import os
from dotenv import load_dotenv
import pymysql

load_dotenv()

DB = os.environ.get("DB_NAME", "finance_manager")
conn = pymysql.connect(
    host=os.environ.get("DB_HOST", "localhost"),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASSWORD", ""),
    database=DB,
    charset="utf8mb4",
)
cur = conn.cursor()


def col_exists(table, col):
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (DB, table, col),
    )
    return cur.fetchone()[0] > 0


def add_col(table, col, definition):
    if col_exists(table, col):
        print(f"  –  {table}.{col} already exists, skip")
        return
    sql = f"ALTER TABLE `{table}` ADD COLUMN `{col}` {definition}"
    cur.execute(sql)
    print(f"  \u2713  Added {table}.{col}")


print(f"Migrating database: {DB}\n")

# ── users ──────────────────────────────────────────────────────────────
add_col("users", "username",   "VARCHAR(80) UNIQUE AFTER `id`")
add_col("users", "currency",   "VARCHAR(10) DEFAULT '\u20b9'")
add_col("users", "updated_at", "TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")

# Populate username for existing rows
cur.execute("UPDATE users SET username = CONCAT('user_', id) WHERE username IS NULL OR username = ''")
print(f"  \u2713  Populated username for {cur.rowcount} existing user(s)")

# ── subscriptions ──────────────────────────────────────────────────────
add_col("subscriptions", "category",  "VARCHAR(50) DEFAULT 'Other'")
add_col("subscriptions", "notes",     "VARCHAR(255)")
add_col("subscriptions", "is_active", "TINYINT(1) NOT NULL DEFAULT 1")

# ── rooms ─────────────────────────────────────────────────────────────
add_col("rooms", "description", "VARCHAR(255)")
add_col("rooms", "is_active",   "TINYINT(1) NOT NULL DEFAULT 1")

# ── trips ─────────────────────────────────────────────────────────────
add_col("trips", "notes",  "VARCHAR(255)")
add_col("trips", "status", "ENUM('planning','active','completed') DEFAULT 'planning'")

# ── alerts ────────────────────────────────────────────────────────────
add_col("alerts", "is_read", "TINYINT(1) NOT NULL DEFAULT 0")

# ── expenses ──────────────────────────────────────────────────────────
add_col("expenses", "updated_at", "TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")

conn.commit()
conn.close()
print("\nMigration complete \u2713")
