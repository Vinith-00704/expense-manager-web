import os; from dotenv import load_dotenv; load_dotenv()
import pymysql
conn = pymysql.connect(
    host=os.environ['DB_HOST'], user=os.environ['DB_USER'],
    password=os.environ['DB_PASSWORD'], database=os.environ['DB_NAME'], charset='utf8mb4'
)
cur = conn.cursor()

for table in ['subscriptions', 'trips', 'room_expenses', 'rooms', 'travel_expenses']:
    try:
        cur.execute(f"DESCRIBE `{table}`")
        cols = [r[0] for r in cur.fetchall()]
        print(f"\n{table}: {cols}")
    except Exception as e:
        print(f"\n{table}: ERROR - {e}")

conn.close()
