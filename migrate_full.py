"""
Full migration: create all missing tables + fix schema for the web app.
Safe to re-run — checks existence before creating.
"""
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


def table_exists(name):
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
        (os.environ.get("DB_NAME", "finance_manager"), name),
    )
    return cur.fetchone()[0] > 0


def col_exists(table, col):
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (os.environ.get("DB_NAME", "finance_manager"), table, col),
    )
    return cur.fetchone()[0] > 0


def create_if_missing(name, ddl):
    if table_exists(name):
        print(f"  – {name} already exists")
    else:
        cur.execute(ddl)
        print(f"  ✓ Created {name}")


print("=== Full schema migration ===\n")

# ── trip_members ──────────────────────────────────────────────
create_if_missing("trip_members", """
CREATE TABLE trip_members (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  trip_id     INT NOT NULL,
  member_name VARCHAR(120) NOT NULL,
  contact     VARCHAR(120),
  user_id     INT,
  joined_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (trip_id)  REFERENCES trips(id)  ON DELETE CASCADE,
  FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

# ── travel_expenses ───────────────────────────────────────────
create_if_missing("travel_expenses", """
CREATE TABLE travel_expenses (
  id                 INT AUTO_INCREMENT PRIMARY KEY,
  trip_id            INT NOT NULL,
  paid_by_member_id  INT,
  expense_date       DATE NOT NULL,
  description        VARCHAR(120) NOT NULL,
  amount             DECIMAL(12,2) NOT NULL,
  created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (trip_id)           REFERENCES trips(id)        ON DELETE CASCADE,
  FOREIGN KEY (paid_by_member_id) REFERENCES trip_members(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

# ── travel_expense_participants ───────────────────────────────
create_if_missing("travel_expense_participants", """
CREATE TABLE travel_expense_participants (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  travel_expense_id INT NOT NULL,
  member_id         INT NOT NULL,
  share_amount      DECIMAL(12,2) NOT NULL,
  FOREIGN KEY (travel_expense_id) REFERENCES travel_expenses(id) ON DELETE CASCADE,
  FOREIGN KEY (member_id)         REFERENCES trip_members(id)    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

# ── room_members ──────────────────────────────────────────────
create_if_missing("room_members", """
CREATE TABLE room_members (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  room_id     INT NOT NULL,
  user_id     INT,
  member_name VARCHAR(120) NOT NULL,
  joined_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (room_id)  REFERENCES rooms(id)  ON DELETE CASCADE,
  FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

# ── room_expense_participants ─────────────────────────────────
create_if_missing("room_expense_participants", """
CREATE TABLE room_expense_participants (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  room_expense_id INT NOT NULL,
  member_id       INT NOT NULL,
  share_amount    DECIMAL(12,2) NOT NULL DEFAULT 0,
  is_settled      TINYINT(1) NOT NULL DEFAULT 0,
  FOREIGN KEY (room_expense_id) REFERENCES room_expenses(id) ON DELETE CASCADE,
  FOREIGN KEY (member_id)       REFERENCES room_members(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

# ── alerts table ──────────────────────────────────────────────
create_if_missing("alerts", """
CREATE TABLE alerts (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  type       VARCHAR(50) NOT NULL,
  message    VARCHAR(255) NOT NULL,
  severity   VARCHAR(20) NOT NULL DEFAULT 'info',
  is_read    TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

# ── rooms – add owner_id if missing ──────────────────────────
if not col_exists("rooms", "owner_id"):
    cur.execute("ALTER TABLE rooms ADD COLUMN owner_id INT REFERENCES users(id)")
    print("  ✓ Added rooms.owner_id")

conn.commit()
conn.close()
print("\n✓ Migration complete.")
