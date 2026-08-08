import sqlite3

def migrate():
    conn = sqlite3.connect('price_tracker.db')
    cursor = conn.cursor()
    
    print("Dropping old index ix_products_url if exists...")
    cursor.execute("DROP INDEX IF EXISTS ix_products_url")
    
    print("Creating composite unique index ix_products_user_url...")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_products_user_url ON products(user_id, url)")
    
    # Also recreate a normal index on url just in case
    print("Creating normal index on url...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_url ON products(url)")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
