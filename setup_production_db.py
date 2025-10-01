#!/usr/bin/env python3
"""
Production Database Setup Script
Handles both scenarios: sync and out-of-sync
"""

import os
import sys
import argparse
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy import create_engine, text
from app.config import settings
from app.models import Base

def setup_fresh_database():
    """Setup fresh database from models"""
    print("🚀 Setting up fresh database from models...")
    
    engine = create_engine(settings.database_url)
    
    # Create all tables from models
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created from models")
    
    # Run migrations for data, indexes, functions
    print("🔄 Running migration files...")
    os.system("python scripts/run_migrations.py")
    
    print("✅ Database setup complete!")

def setup_with_migrations_only():
    """Setup database using only migration files"""
    print("🚀 Setting up database using migration files...")
    
    # Run all migrations
    os.system("python scripts/run_migrations.py")
    
    print("✅ Database setup complete!")

def check_and_fix_schema():
    """Check schema sync and provide recommendations"""
    print("🔍 Checking schema synchronization...")
    
    # Run schema checker
    result = os.system("python check_schema_sync.py")
    
    if result != 0:
        print("\n❌ Schema mismatch detected!")
        print("\n📋 Recommended actions:")
        print("1. Review the differences above")
        print("2. Update models.py to match database structure")
        print("3. Or create migration files for missing database elements")
        print("4. Re-run this script")
        return False
    else:
        print("✅ Schema is in sync!")
        return True

def main():
    parser = argparse.ArgumentParser(description="Production Database Setup")
    parser.add_argument("--mode", choices=["fresh", "migrations", "check"], 
                       default="check", help="Setup mode")
    parser.add_argument("--force", action="store_true", 
                       help="Force setup even with schema mismatches")
    
    args = parser.parse_args()
    
    print("🏥 Health App Production Database Setup")
    print("=" * 50)
    
    if args.mode == "check":
        # Just check schema sync
        if check_and_fix_schema():
            print("\n✅ Ready for production setup!")
            print("Run: python setup_production_db.py --mode fresh")
        else:
            print("\n❌ Fix schema issues first!")
            return 1
    
    elif args.mode == "fresh":
        # Setup fresh database from models
        if not args.force:
            if not check_and_fix_schema():
                print("\n❌ Schema issues detected. Use --force to proceed anyway.")
                return 1
        
        setup_fresh_database()
    
    elif args.mode == "migrations":
        # Setup using only migrations
        setup_with_migrations_only()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

