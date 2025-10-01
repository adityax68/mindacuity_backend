#!/usr/bin/env python3
"""
Schema Synchronization Checker
Compares SQLAlchemy models with actual database schema
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.schema import CreateTable

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.config import settings
from app.models import Base

def get_model_tables():
    """Get all tables defined in models.py"""
    model_tables = {}
    for table_name, table in Base.metadata.tables.items():
        model_tables[table_name] = {
            'columns': [col.name for col in table.columns],
            'indexes': [idx.name for idx in table.indexes if idx.name],
            'foreign_keys': [fk.name for fk in table.foreign_keys if fk.name]
        }
    return model_tables

def get_database_tables(engine):
    """Get all tables from actual database"""
    inspector = inspect(engine)
    db_tables = {}
    
    for table_name in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        foreign_keys = [fk['name'] for fk in inspector.get_foreign_keys(table_name)]
        
        db_tables[table_name] = {
            'columns': columns,
            'indexes': indexes,
            'foreign_keys': foreign_keys
        }
    
    return db_tables

def compare_schemas():
    """Compare model schema with database schema"""
    print("🔍 Schema Synchronization Checker")
    print("=" * 50)
    
    # Connect to database
    engine = create_engine(settings.database_url)
    
    # Get schemas
    model_tables = get_model_tables()
    db_tables = get_database_tables(engine)
    
    print(f"📊 Model Tables: {len(model_tables)}")
    print(f"📊 Database Tables: {len(db_tables)}")
    print()
    
    # Check for missing tables in database
    missing_in_db = set(model_tables.keys()) - set(db_tables.keys())
    if missing_in_db:
        print("❌ Tables in models but NOT in database:")
        for table in missing_in_db:
            print(f"   - {table}")
        print()
    
    # Check for extra tables in database
    extra_in_db = set(db_tables.keys()) - set(model_tables.keys())
    if extra_in_db:
        print("⚠️  Tables in database but NOT in models:")
        for table in extra_in_db:
            print(f"   - {table}")
        print()
    
    # Check column differences for common tables
    common_tables = set(model_tables.keys()) & set(db_tables.keys())
    column_issues = []
    
    for table in common_tables:
        model_cols = set(model_tables[table]['columns'])
        db_cols = set(db_tables[table]['columns'])
        
        missing_cols = model_cols - db_cols
        extra_cols = db_cols - model_cols
        
        if missing_cols or extra_cols:
            column_issues.append({
                'table': table,
                'missing_in_db': missing_cols,
                'extra_in_db': extra_cols
            })
    
    if column_issues:
        print("🔍 Column Differences:")
        for issue in column_issues:
            print(f"\n   Table: {issue['table']}")
            if issue['missing_in_db']:
                print(f"   ❌ Missing in DB: {list(issue['missing_in_db'])}")
            if issue['extra_in_db']:
                print(f"   ⚠️  Extra in DB: {list(issue['extra_in_db'])}")
        print()
    
    # Summary
    if not missing_in_db and not extra_in_db and not column_issues:
        print("✅ Perfect! Models and database are in sync!")
        return True
    else:
        print("❌ Schema mismatch detected!")
        return False

if __name__ == "__main__":
    compare_schemas()

