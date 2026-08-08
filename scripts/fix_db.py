import sqlite3

def fix_db():
    conn = sqlite3.connect('price_tracker.db')
    cursor = conn.cursor()
    print("Dropping UNIQUE index ix_products_url...")
    cursor.execute("DROP INDEX IF EXISTS ix_products_url")
    print("Creating non-unique index ix_products_url...")
    cursor.execute("CREATE INDEX ix_products_url ON products (url)")
    conn.commit()
    conn.close()
    print("Database fix applied successfully.")

if __name__ == "__main__":
    fix_db()
