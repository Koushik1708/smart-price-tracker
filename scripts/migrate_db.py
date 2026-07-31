import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from sqlalchemy import create_engine, inspect, text
from backend.database import SQLALCHEMY_DATABASE_URL

def main():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    inspector = inspect(engine)
    
    if not inspector.has_table("products"):
        print("Table 'products' does not exist. Run application once to create tables.")
        sys.exit(1)
        
    columns = [col['name'] for col in inspector.get_columns("products")]
    
    added_columns = []
    
    with engine.begin() as conn:
        if 'image_url' not in columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN image_url VARCHAR;"))
            added_columns.append('image_url')
            
        if 'brand' not in columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN brand VARCHAR;"))
            added_columns.append('brand')
            
        if 'category' not in columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN category VARCHAR;"))
            added_columns.append('category')
            
        if 'retry_count' not in columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN retry_count INTEGER DEFAULT 0;"))
            added_columns.append('retry_count')
            
        if 'last_failure' not in columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN last_failure DATETIME;"))
            added_columns.append('last_failure')
            
        if 'last_failure_reason' not in columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN last_failure_reason VARCHAR;"))
            added_columns.append('last_failure_reason')
            
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
