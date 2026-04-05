"""Delete old Tkinter orphan user row (id=3) so the email can be re-registered."""
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

# Show what we're about to delete
cur.execute("SELECT id, username, email, full_name FROM users WHERE id = 3")
row = cur.fetchone()
if row:
    print(f"Deleting: id={row[0]}  username={row[1]}  email={row[2]}  name={row[3]}")
    cur.execute("DELETE FROM users WHERE id = 3")
    conn.commit()
    print("✓ Old account deleted. You can now register fresh with that email.")
else:
    print("No user with id=3 found (already deleted?).")

# Show remaining users
cur.execute("SELECT id, username, email, full_name FROM users")
print("\nRemaining users:")
for r in cur.fetchall():
    print(f"  id={r[0]}  username={r[1]}  email={r[2]}  name={r[3]}")

conn.close()
