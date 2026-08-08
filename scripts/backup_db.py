import sqlite3
import os
import datetime

DB_PATH = "price_tracker.db"
BACKUP_DIR = "backups"

def backup_db():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file '{DB_PATH}' not found.")
        return
        
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"price_tracker_backup_{timestamp}.db")
    
    print(f"Starting database backup from {DB_PATH} to {backup_file}...")
    
    try:
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(backup_file)
        
        with dst:
            src.backup(dst)
            
        dst.close()
        src.close()
        print(f"Backup completed successfully: {backup_file}")
    except Exception as e:
        print(f"Backup failed: {e}")

if __name__ == "__main__":
    backup_db()
