"""
migrate_v3.py — FinanceOS Phase 1 Schema Migration
====================================================
Safe, idempotent migration that:
  1. Adds 6 new tables required by the import pipeline
  2. Adds 6 new columns to the existing `expenses` table

All operations use IF NOT EXISTS / IF NOT EXISTS COLUMN guards so this
script is completely safe to re-run on an already-migrated database.

Usage:
    cd "E:\\expence manager\\finance-web"
    .venv\\Scripts\\python migrate_v3.py
"""
import os
import sys
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB = {
    "host":   os.environ.get("DB_HOST", "localhost"),
    "port":   int(os.environ.get("DB_PORT", 3306)),
    "user":   os.environ.get("DB_USER", "root"),
    "passwd": os.environ.get("DB_PASSWORD", ""),
    "db":     os.environ.get("DB_NAME", "finance_manager"),
    "charset": "utf8mb4",
}
SCHEMA = DB["db"]


def connect():
    return pymysql.connect(**DB)


def col_exists(cur, table, col):
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (SCHEMA, table, col),
    )
    return cur.fetchone()[0] > 0


def table_exists(cur, table):
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
        (SCHEMA, table),
    )
    return cur.fetchone()[0] > 0


def add_col(cur, table, col, definition, after=None):
    if col_exists(cur, table, col):
        print(f"    – {table}.{col} already exists")
        return
    after_clause = f" AFTER `{after}`" if after else ""
    cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{col}` {definition}{after_clause}")
    print(f"    + Added {table}.{col}")


def create_table(cur, name, ddl):
    if table_exists(cur, name):
        print(f"  - Table `{name}` already exists")
        return
    cur.execute(ddl)
    print(f"  + Created table `{name}`")


def run():
    print("\n=== FinanceOS - migrate_v3.py ===\n")

    conn = connect()
    cur  = conn.cursor()

    # ── 1. import_history (must exist before imported_transactions FK) ─────
    print("-> Creating new tables...")
    create_table(cur, "import_history", """
        CREATE TABLE `import_history` (
          `id`              INT AUTO_INCREMENT PRIMARY KEY,
          `user_id`         INT NOT NULL,
          `filename`        VARCHAR(255) NOT NULL,
          `file_type`       ENUM('csv','xlsx','pdf','sms') NOT NULL DEFAULT 'csv',
          `bank_detected`   VARCHAR(50),
          `imported_count`  INT DEFAULT 0,
          `success_count`   INT DEFAULT 0,
          `failed_count`    INT DEFAULT 0,
          `duplicate_count` INT DEFAULT 0,
          `error_summary`   TEXT,
          `created_at`      DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
          INDEX idx_ih_user (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── 2. imported_transactions ───────────────────────────────────────────
    create_table(cur, "imported_transactions", """
        CREATE TABLE `imported_transactions` (
          `id`                     INT AUTO_INCREMENT PRIMARY KEY,
          `user_id`                INT NOT NULL,
          `source_type`            ENUM('manual','sms','statement','ocr') NOT NULL DEFAULT 'statement',
          `import_batch_id`        INT,
          `raw_text`               TEXT,
          `merchant`               VARCHAR(255),
          `normalized_merchant`    VARCHAR(255),
          `amount`                 DECIMAL(12,2) NOT NULL,
          `transaction_direction`  ENUM('debit','credit') NOT NULL DEFAULT 'debit',
          `transaction_date`       DATE NOT NULL,
          `category`               VARCHAR(50) DEFAULT 'Other',
          `payment_method`         VARCHAR(50) DEFAULT 'Other',
          `description`            VARCHAR(255),
          `confidence_score`       FLOAT DEFAULT 0.0,
          `transaction_hash`       VARCHAR(64),
          `status`                 ENUM('pending','confirmed','rejected','duplicate') NOT NULL DEFAULT 'pending',
          `confirmed_expense_id`   INT,
          `created_at`             DATETIME DEFAULT CURRENT_TIMESTAMP,
          `updated_at`             DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          FOREIGN KEY (`user_id`)            REFERENCES `users`(`id`)            ON DELETE CASCADE,
          FOREIGN KEY (`import_batch_id`)    REFERENCES `import_history`(`id`)   ON DELETE SET NULL,
          FOREIGN KEY (`confirmed_expense_id`) REFERENCES `expenses`(`id`)       ON DELETE SET NULL,
          INDEX idx_it_user   (`user_id`),
          INDEX idx_it_status (`status`),
          INDEX idx_it_hash   (`transaction_hash`),
          INDEX idx_it_batch  (`import_batch_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── 3. audit_logs ──────────────────────────────────────────────────────
    create_table(cur, "audit_logs", """
        CREATE TABLE `audit_logs` (
          `id`            INT AUTO_INCREMENT PRIMARY KEY,
          `user_id`       INT,
          `action`        VARCHAR(50) NOT NULL,
          `entity_type`   VARCHAR(50),
          `entity_id`     INT,
          `metadata_json` TEXT,
          `ip_address`    VARCHAR(45),
          `created_at`    DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL,
          INDEX idx_al_user   (`user_id`),
          INDEX idx_al_action (`action`),
          INDEX idx_al_ts     (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── 4. registered_devices ─────────────────────────────────────────────
    create_table(cur, "registered_devices", """
        CREATE TABLE `registered_devices` (
          `id`               INT AUTO_INCREMENT PRIMARY KEY,
          `user_id`          INT NOT NULL,
          `device_id`        VARCHAR(255) NOT NULL UNIQUE,
          `device_name`      VARCHAR(120),
          `device_type`      ENUM('android','ios','other') NOT NULL DEFAULT 'android',
          `last_sync_at`     DATETIME,
          `total_synced`     INT DEFAULT 0,
          `auth_token_ref`   VARCHAR(255),
          `status`           ENUM('active','revoked') NOT NULL DEFAULT 'active',
          `created_at`       DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
          INDEX idx_rd_user   (`user_id`),
          INDEX idx_rd_status (`status`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── 5. financial_goals ────────────────────────────────────────────────
    create_table(cur, "financial_goals", """
        CREATE TABLE `financial_goals` (
          `id`              INT AUTO_INCREMENT PRIMARY KEY,
          `user_id`         INT NOT NULL,
          `name`            VARCHAR(120) NOT NULL,
          `description`     VARCHAR(255),
          `category`        VARCHAR(50) DEFAULT 'Other',
          `target_amount`   DECIMAL(12,2) NOT NULL,
          `current_amount`  DECIMAL(12,2) DEFAULT 0,
          `deadline`        DATE,
          `status`          ENUM('active','achieved','cancelled') NOT NULL DEFAULT 'active',
          `created_at`      DATETIME DEFAULT CURRENT_TIMESTAMP,
          `updated_at`      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
          INDEX idx_fg_user (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── 6. budgets ────────────────────────────────────────────────────────
    create_table(cur, "budgets", """
        CREATE TABLE `budgets` (
          `id`            INT AUTO_INCREMENT PRIMARY KEY,
          `user_id`       INT NOT NULL,
          `category`      VARCHAR(50) NOT NULL,
          `monthly_limit` DECIMAL(12,2) NOT NULL,
          `month`         VARCHAR(7) NOT NULL COMMENT 'YYYY-MM',
          `created_at`    DATETIME DEFAULT CURRENT_TIMESTAMP,
          `updated_at`    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
          UNIQUE KEY uq_budget_user_cat_month (`user_id`, `category`, `month`),
          INDEX idx_b_user  (`user_id`),
          INDEX idx_b_month (`month`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── 7. Extend expenses table ───────────────────────────────────────────
    print("\n-> Extending `expenses` table...")
    add_col(cur, "expenses", "transaction_source",
            "ENUM('manual','sms','statement','ocr') NOT NULL DEFAULT 'manual'",
            after="entry_type")
    add_col(cur, "expenses", "external_reference",
            "VARCHAR(255) NULL",
            after="transaction_source")
    add_col(cur, "expenses", "import_batch_id",
            "INT NULL",
            after="external_reference")
    add_col(cur, "expenses", "is_auto_generated",
            "TINYINT(1) NOT NULL DEFAULT 0",
            after="import_batch_id")
    add_col(cur, "expenses", "transaction_direction",
            "ENUM('debit','credit') NULL",
            after="is_auto_generated")
    add_col(cur, "expenses", "transaction_hash",
            "VARCHAR(64) NULL",
            after="transaction_direction")

    conn.commit()
    cur.close()
    conn.close()

    print("\n=== Migration complete - no data was lost. ===\n")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"\n[ERROR] Migration failed: {exc}")
        sys.exit(1)
