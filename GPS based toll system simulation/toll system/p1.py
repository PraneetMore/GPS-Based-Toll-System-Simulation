import sqlite3

def check_transactions():
    conn = sqlite3.connect('database.db')  # Ensure the path is correct
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions')
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    conn.close()

check_transactions()