import sqlite3

def check():
    conn = sqlite3.connect('price_tracker.db')
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='products'").fetchone()
    if row:
        print(row[0])
    
    # Also check indexes for unique constraints
    indexes = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='products'").fetchall()
    for idx in indexes:
        print(f"Index: {idx[0]} - SQL: {idx[1]}")

if __name__ == "__main__":
    check()
