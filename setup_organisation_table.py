#!/usr/bin/env python3
"""
Script to create the organisations table in the database.
Run this script to set up the organisation table manually.
"""

import os
import sys
from sqlalchemy import text
from app.database import engine

def create_organisation_table():
    """Create the organisations table if it doesn't exist."""
    
    # SQL to create the organisations table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS organisations (
        id SERIAL PRIMARY KEY,
        org_id VARCHAR(50) UNIQUE NOT NULL,
        org_name VARCHAR(255) NOT NULL,
        hr_email VARCHAR(255) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # SQL to create indexes
    create_indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_organisations_org_id ON organisations(org_id);
    CREATE INDEX IF NOT EXISTS idx_organisations_hr_email ON organisations(hr_email);
    """
    
    try:
        with engine.connect() as connection:
            # Create table
            connection.execute(text(create_table_sql))
            connection.commit()
            print("✅ Organisations table created successfully!")
            
            # Create indexes
            connection.execute(text(create_indexes_sql))
            connection.commit()
            print("✅ Indexes created successfully!")
            
    except Exception as e:
        print(f"❌ Error creating organisations table: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Setting up organisations table...")
    create_organisation_table()
    print("✅ Setup complete!") 