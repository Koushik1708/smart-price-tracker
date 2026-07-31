import sys
import os
import shutil
import sqlite3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, Base, SQLALCHEMY_DATABASE_URL
from backend.models import Product, PriceSnapshot, AlertThreshold # Ensure models are loaded

def run_migration():
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
    
    # 1. Backup the database
    backup_path = f"{db_path}.bak"
    print(f"Creating backup at {backup_path}...")
    shutil.copy2(db_path, backup_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 2. Rename old table
        print("Renaming 'price_snapshots' to 'price_snapshots_old'...")
        cursor.execute("ALTER TABLE price_snapshots RENAME TO price_snapshots_old")
        
        print("Dropping old index...")
        cursor.execute("DROP INDEX IF EXISTS ix_price_snapshots_id")
        
        # 3. Create the new schema with constraints
        print("Creating new 'price_snapshots' table with CheckConstraints...")
        Base.metadata.create_all(bind=engine)
        
        # 4. Copy data over
        print("Migrating data to the new table...")
        cursor.execute("INSERT INTO price_snapshots SELECT * FROM price_snapshots_old")
        
        # 5. Drop old table
        print("Dropping old table...")
        cursor.execute("DROP TABLE price_snapshots_old")
        
        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        print("Restoring from backup...")
        shutil.copy2(backup_path, db_path)
        print("Restore complete.")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
