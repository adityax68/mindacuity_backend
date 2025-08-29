#!/usr/bin/env python3
"""
Script to fix the organisations table updated_at column.
"""

import os
import sys
from sqlalchemy import text
from app.database import engine

def fix_organisation_table():
    """Fix the updated_at column in organisations table."""
    
    # SQL to fix the updated_at column
    fix_sql = """
    ALTER TABLE organisations 
    ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
    """
    
    # SQL to update existing NULL records
    update_sql = """
    UPDATE organisations 
    SET updated_at = created_at 
    WHERE updated_at IS NULL;
    """
    
    try:
        with engine.connect() as connection:
            # Fix the column default
            connection.execute(text(fix_sql))
            connection.commit()
            print("✅ Fixed updated_at column default value!")
            
            # Update existing NULL records
            result = connection.execute(text(update_sql))
            connection.commit()
            print(f"✅ Updated {result.rowcount} existing records!")
            
    except Exception as e:
        print(f"❌ Error fixing organisation table: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Fixing organisation table updated_at column...")
    fix_organisation_table()
    print("✅ Fix complete!") 