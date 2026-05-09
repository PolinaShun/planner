import sqlite3
import json

db_path = r'C:\Users\Polina\flash\квен\планировщик\planner.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Checking BodyMetrics for April 2026...")
cursor.execute("SELECT date, weight, workout_history FROM body_metrics WHERE date LIKE '2026-04%';")
rows = cursor.fetchall()
for row in rows:
    date, weight, history = row
    history_list = json.loads(history) if history else []
    done = sum(1 for x in history_list if x)
    print(f"Date: {date}, Weight: {weight}, History Done: {done}/{len(history_list)}")

if not rows:
    print("No records found for April 2026.")

conn.close()
