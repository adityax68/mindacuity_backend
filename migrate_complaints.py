#!/usr/bin/env python3
"""
Simple migration script using the existing app infrastructure.
This adds org_id and hr_email fields to the complaints table.
"""

import os
import sys
from sqlalchemy import text

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import engine
from app.models import Base

def run_migration():
    """Run the complaint table migration."""
    
    try:
        print("Starting complaint table migration...")
        
        # Check if columns already exist
        with engine.connect() as conn:
            # Check if org_id column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'complaints' 
                AND column_name = 'org_id'
            """))
            
            org_id_exists = result.fetchone() is not None
            
            # Check if hr_email column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'complaints' 
                AND column_name = 'hr_email'
            """))
            
            hr_email_exists = result.fetchone() is not None
            
            if org_id_exists and hr_email_exists:
                print("✅ Migration already completed - columns exist!")
                return True
            
            # Add org_id column if it doesn't exist
            if not org_id_exists:
                print("Adding org_id column...")
                conn.execute(text("ALTER TABLE complaints ADD COLUMN org_id VARCHAR(255) NULL"))
                conn.commit()
                print("✅ org_id column added")
            
            # Add hr_email column if it doesn't exist
            if not hr_email_exists:
                print("Adding hr_email column...")
                conn.execute(text("ALTER TABLE complaints ADD COLUMN hr_email VARCHAR(255) NULL"))
                conn.commit()
                print("✅ hr_email column added")
            
            # Create indexes
            print("Creating indexes...")
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_complaints_org_id ON complaints(org_id)"))
                conn.commit()
                print("✅ org_id index created")
            except Exception as e:
                print(f"Index creation warning: {e}")
            
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_complaints_hr_email ON complaints(hr_email)"))
                conn.commit()
                print("✅ hr_email index created")
            except Exception as e:
                print(f"Index creation warning: {e}")
            
            # Update existing complaints with org_id and hr_email from employee records
            print("Updating existing complaints...")
            result = conn.execute(text("""
                UPDATE complaints 
                SET 
                    org_id = e.org_id,
                    hr_email = e.hr_email
                FROM employees e
                WHERE complaints.employee_id = e.id 
                AND complaints.employee_id IS NOT NULL
            """))
            conn.commit()
            print(f"✅ Updated {result.rowcount} existing complaints")
            
            # Verify the migration
            print("Verifying migration...")
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'complaints' 
                AND column_name IN ('org_id', 'hr_email')
                ORDER BY column_name
            """))
            
            columns = result.fetchall()
            if len(columns) == 2:
                print("✅ Migration verification successful!")
                for col_name, data_type, is_nullable in columns:
                    print(f"  - {col_name}: {data_type} (nullable: {is_nullable})")
            else:
                print("❌ Migration verification failed!")
                return False
        
        print("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("You can now restart your application to use the updated complaint system.")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
