import sqlite3

def check_db():
    conn = sqlite3.connect('planner.db')
    cursor = conn.cursor()
    tables = ['clients', 'counters', 'body_metrics', 'content_metrics', 'tasks']
    results = {}
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            results[t] = cursor.fetchone()[0]
        except Exception as e:
            results[t] = f"Error: {e}"
    conn.close()
    return results

if __name__ == "__main__":
    print(check_db())
