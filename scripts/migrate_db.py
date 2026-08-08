import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from sqlalchemy import create_engine, inspect, text
from backend.database import SQLALCHEMY_DATABASE_URL, Base
from backend.models import User
from backend.auth import get_password_hash
from dotenv import load_dotenv
import secrets

def main():
    load_dotenv(os.path.join(project_root, '.env'))
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    # Ensure all tables (including 'users') are created
    Base.metadata.create_all(bind=engine)
    
    inspector = inspect(engine)
    
    if not inspector.has_table("products"):
        print("Table 'products' does not exist. Run application once to create tables.")
        sys.exit(1)
        
    # --- Auth Migration: Setup Admin User ---
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@letsgo.com")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD")
    
    with engine.begin() as conn:
        result = conn.execute(text("SELECT id FROM users WHERE email = :email"), {"email": admin_email}).fetchone()
        if not result:
            if not admin_password:
                admin_password = secrets.token_urlsafe(12)
                print(f"\n=======================================================")
                print(f"SECURITY NOTICE: Generated random admin password: {admin_password}")
                print(f"=======================================================\n")
                
            hashed_pw = get_password_hash(admin_password)
            conn.execute(
                text("INSERT INTO users (name, email, password_hash, created_at) VALUES (:name, :email, :password, CURRENT_TIMESTAMP)"),
                {"name": "Admin", "email": admin_email, "password": hashed_pw}
            )
            print(f"Created default admin user: {admin_email}")
            result = conn.execute(text("SELECT id FROM users WHERE email = :email"), {"email": admin_email}).fetchone()
        
        if result:
            admin_id = result[0]
        else:
            raise Exception("Failed to retrieve admin user ID")
        
    # --- Schema Migration ---
    columns_users = [col['name'] for col in inspector.get_columns("users")]
    columns_products = [col['name'] for col in inspector.get_columns("products")]
    columns_alerts = [col['name'] for col in inspector.get_columns("alert_thresholds")]
    
    added_columns = []
    
    with engine.begin() as conn:
        if 'is_admin' not in columns_users:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0;"))
            added_columns.append('users.is_admin')
            
        if 'failed_login_attempts' not in columns_users:
            conn.execute(text("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;"))
            added_columns.append('users.failed_login_attempts')
            
        if 'locked_until' not in columns_users:
            conn.execute(text("ALTER TABLE users ADD COLUMN locked_until DATETIME;"))
            added_columns.append('users.locked_until')

        if 'image_url' not in columns_products:
            conn.execute(text("ALTER TABLE products ADD COLUMN image_url VARCHAR;"))
            added_columns.append('products.image_url')
            
        if 'brand' not in columns_products:
            conn.execute(text("ALTER TABLE products ADD COLUMN brand VARCHAR;"))
            added_columns.append('products.brand')
            
        if 'category' not in columns_products:
            conn.execute(text("ALTER TABLE products ADD COLUMN category VARCHAR;"))
            added_columns.append('products.category')
            
        if 'retry_count' not in columns_products:
            conn.execute(text("ALTER TABLE products ADD COLUMN retry_count INTEGER DEFAULT 0;"))
            added_columns.append('products.retry_count')
            
        if 'last_failure' not in columns_products:
            conn.execute(text("ALTER TABLE products ADD COLUMN last_failure DATETIME;"))
            added_columns.append('products.last_failure')
            
        if 'last_failure_reason' not in columns_products:
            conn.execute(text("ALTER TABLE products ADD COLUMN last_failure_reason VARCHAR;"))
            added_columns.append('products.last_failure_reason')
            
        if 'user_id' not in columns_products:
            conn.execute(text("ALTER TABLE products ADD COLUMN user_id INTEGER;"))
            added_columns.append('products.user_id')
            
        if 'user_id' not in columns_alerts:
            conn.execute(text("ALTER TABLE alert_thresholds ADD COLUMN user_id INTEGER;"))
            added_columns.append('alert_thresholds.user_id')
            
        # Ensure default admin user is flagged as admin
        conn.execute(text("UPDATE users SET is_admin = 1 WHERE id = :admin_id"), {"admin_id": admin_id})
        
        # Migrate existing rows to admin
        conn.execute(text("UPDATE products SET user_id = :admin_id WHERE user_id IS NULL"), {"admin_id": admin_id})
        conn.execute(text("UPDATE alert_thresholds SET user_id = :admin_id WHERE user_id IS NULL"), {"admin_id": admin_id})
            
    if added_columns:
        print(f"Successfully added columns: {', '.join(added_columns)}")
    else:
        print("Columns already exist. No changes made.")

    # Create indexes idempotently
    indexes_to_create = [
        "CREATE INDEX IF NOT EXISTS idx_products_url ON products (url);",
        "CREATE INDEX IF NOT EXISTS idx_products_status ON products (status);",
        "CREATE INDEX IF NOT EXISTS idx_price_snapshots_product_id ON price_snapshots (product_id);",
        "CREATE INDEX IF NOT EXISTS idx_price_snapshots_timestamp ON price_snapshots (timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_alert_thresholds_product_id ON alert_thresholds (product_id);",
        "CREATE INDEX IF NOT EXISTS idx_alert_thresholds_status ON alert_thresholds (status);"
    ]
    
    with engine.begin() as conn:
        for idx_sql in indexes_to_create:
            try:
                conn.execute(text(idx_sql))
            except Exception as e:
                print(f"Warning: Failed to create index with '{idx_sql}'. Error: {e}")
                
    print("Successfully ensured indexes exist.")

if __name__ == '__main__':
    main()
