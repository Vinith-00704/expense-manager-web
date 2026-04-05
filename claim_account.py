"""
claim_account.py — Fix old Tkinter app data conflict.

The old app left a user row with your email but a dummy auto-username.
This script lets you either:
  A) Claim the old account (set a proper username + new password)
  B) Delete the old orphan row so you can register fresh

Run: .venv\Scripts\python claim_account.py
"""
import os, sys
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

# Show all users
cur.execute("SELECT id, username, email, full_name FROM users ORDER BY id")
rows = cur.fetchall()
print("\nCurrent users in database:")
print("-" * 60)
for r in rows:
    print(f"  id={r[0]}  username={r[1]}  email={r[2]}  name={r[3]}")
print("-" * 60)

print("\nWhat would you like to do?")
print("  1) Delete an old user row (so you can re-register with its email)")
print("  2) Update an old user row's username (claim the account)")
print("  3) Exit")

choice = input("\nEnter 1, 2, or 3: ").strip()

if choice == "1":
    uid = input("Enter the user ID to DELETE: ").strip()
    confirm = input(f"Are you sure you want to delete user id={uid}? (yes/no): ").strip()
    if confirm.lower() == "yes":
        cur.execute("DELETE FROM users WHERE id = %s", (uid,))
        conn.commit()
        print(f"✓ User id={uid} deleted. You can now register with that email.")
    else:
        print("Cancelled.")

elif choice == "2":
    uid = input("Enter the user ID to update: ").strip()
    new_username = input("New username: ").strip().lower()
    # Check uniqueness
    cur.execute("SELECT id FROM users WHERE username = %s AND id != %s", (new_username, uid))
    if cur.fetchone():
        print("✗ That username is already taken.")
    else:
        cur.execute("UPDATE users SET username = %s WHERE id = %s", (new_username, uid))
        conn.commit()
        print(f"✓ User id={uid} username updated to '{new_username}'.")
        print("  You can now sign in with that username (use forgotten password or ask admin to reset).")
else:
    print("Exiting.")

conn.close()
