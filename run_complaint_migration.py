#!/usr/bin/env python3
"""
Script to run the complaint table migration.
This adds org_id and hr_email fields to the complaints table.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def run_migration():
    """Run the complaint table migration."""
    
    # Database connection parameters
    # You may need to adjust these based on your database configuration
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'health_app'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password')
    }
    
    try:
        # Connect to the database
        print("Connecting to database...")
        conn = psycopg2.connect(**db_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Read and execute the migration SQL
        migration_file = os.path.join(os.path.dirname(__file__), 'migrations', 'add_complaint_org_fields.sql')
        
        if not os.path.exists(migration_file):
            print(f"Migration file not found: {migration_file}")
            return False
        
        print("Reading migration file...")
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("Executing migration...")
        cursor.execute(migration_sql)
        
        print("Migration completed successfully!")
        
        # Verify the migration
        print("Verifying migration...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'complaints' 
            AND column_name IN ('org_id', 'hr_email')
            ORDER BY column_name;
        """)
        
        columns = cursor.fetchall()
        if len(columns) == 2:
            print("✅ Migration verification successful!")
            for col_name, data_type, is_nullable in columns:
                print(f"  - {col_name}: {data_type} (nullable: {is_nullable})")
        else:
            print("❌ Migration verification failed!")
            return False
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting complaint table migration...")
    success = run_migration()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now restart your application to use the updated complaint system.")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
