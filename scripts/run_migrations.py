#!/usr/bin/env python3
"""
Perfect Migration Runner for Health App
This script runs database migrations with proper tracking and safety checks.
"""

import os
import sys
import argparse
import hashlib
from datetime import datetime
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from app.config import settings

class MigrationRunner:
    def __init__(self, database_url=None):
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url)
        self.migrations_dir = Path(__file__).parent.parent / "migrations"
        
    def create_migration_tracking_table(self):
        """Create migration tracking table if it doesn't exist"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS migration_history (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) UNIQUE NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_hash VARCHAR(64) NOT NULL,
                    applied_at TIMESTAMP DEFAULT NOW(),
                    applied_by VARCHAR(255) DEFAULT 'system'
                );
            """))
            conn.commit()
    
    def get_file_hash(self, file_path):
        """Get SHA256 hash of a file"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def get_migration_files(self):
        """Get all migration files sorted by name"""
        if not self.migrations_dir.exists():
            return []
        
        migration_files = []
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            migration_files.append(file_path)
        
        return migration_files
    
    def is_migration_applied(self, migration_name):
        """Check if a migration has already been applied"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 1 FROM migration_history 
                WHERE migration_name = :migration_name
            """), {"migration_name": migration_name})
            return result.fetchone() is not None
    
    def record_migration(self, migration_name, file_path, file_hash):
        """Record that a migration has been applied"""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO migration_history (migration_name, file_path, file_hash, applied_by)
                VALUES (:migration_name, :file_path, :file_hash, :applied_by)
                ON CONFLICT (migration_name) DO NOTHING
            """), {
                "migration_name": migration_name,
                "file_path": str(file_path),
                "file_hash": file_hash,
                "applied_by": os.getenv("USER", "unknown")
            })
            conn.commit()
    
    def run_sql_file(self, file_path):
        """Run a SQL file with proper error handling"""
        try:
            with open(file_path, 'r') as f:
                sql_content = f.read()
            
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            with self.engine.connect() as conn:
                for i, statement in enumerate(statements):
                    if statement:
                        try:
                            conn.execute(text(statement))
                            print(f"  ✅ Statement {i+1}/{len(statements)} executed")
                        except Exception as e:
                            if "already exists" in str(e).lower():
                                print(f"  ⚠️  Statement {i+1} skipped (already exists)")
                            else:
                                raise e
                conn.commit()
            
            return True
        except Exception as e:
            print(f"  ❌ Error executing SQL file: {e}")
            return False
    
    def run_migrations(self, force=False, dry_run=False):
        """Run all pending migrations"""
        print("🚀 Health App Migration Runner")
        print("=" * 50)
        
        # Create tracking table
        print("📋 Setting up migration tracking...")
        self.create_migration_tracking_table()
        
        # Get migration files
        migration_files = self.get_migration_files()
        if not migration_files:
            print("❌ No migration files found in migrations/ directory")
            return False
        
        print(f"📁 Found {len(migration_files)} migration files")
        
        # Check which migrations need to be run
        pending_migrations = []
        for file_path in migration_files:
            migration_name = file_path.stem
            file_hash = self.get_file_hash(file_path)
            
            if self.is_migration_applied(migration_name):
                print(f"⏭️  Skipping {migration_name} (already applied)")
            else:
                pending_migrations.append((file_path, migration_name, file_hash))
        
        if not pending_migrations:
            print("✅ All migrations are up to date!")
            return True
        
        print(f"\n🔄 Found {len(pending_migrations)} pending migrations:")
        for _, name, _ in pending_migrations:
            print(f"  - {name}")
        
        if dry_run:
            print("\n🔍 Dry run mode - no changes will be made")
            return True
        
        # Run pending migrations
        print(f"\n🚀 Running {len(pending_migrations)} migrations...")
        success_count = 0
        
        for file_path, migration_name, file_hash in pending_migrations:
            print(f"\n📄 Running migration: {migration_name}")
            print(f"   File: {file_path}")
            
            if self.run_sql_file(file_path):
                self.record_migration(migration_name, file_path, file_hash)
                print(f"   ✅ {migration_name} applied successfully")
                success_count += 1
            else:
                print(f"   ❌ {migration_name} failed")
                if not force:
                    print("   🛑 Stopping due to migration failure")
                    break
        
        print(f"\n📊 Migration Summary:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Failed: {len(pending_migrations) - success_count}")
        print(f"   📁 Total: {len(pending_migrations)}")
        
        return success_count == len(pending_migrations)
    
    def show_status(self):
        """Show migration status"""
        print("📊 Migration Status")
        print("=" * 30)
        
        # Get all migration files
        migration_files = self.get_migration_files()
        if not migration_files:
            print("❌ No migration files found")
            return
        
        # Get applied migrations
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT migration_name, applied_at, file_hash
                FROM migration_history
                ORDER BY applied_at
            """))
            applied_migrations = {row[0]: (row[1], row[2]) for row in result.fetchall()}
        
        print(f"📁 Total migration files: {len(migration_files)}")
        print(f"✅ Applied migrations: {len(applied_migrations)}")
        print(f"⏳ Pending migrations: {len(migration_files) - len(applied_migrations)}")
        
        print(f"\n📋 Migration Details:")
        for file_path in migration_files:
            migration_name = file_path.stem
            file_hash = self.get_file_hash(file_path)
            
            if migration_name in applied_migrations:
                applied_at, stored_hash = applied_migrations[migration_name]
                status = "✅ Applied"
                if file_hash != stored_hash:
                    status += " ⚠️ (file changed)"
                print(f"  {status} - {migration_name} ({applied_at})")
            else:
                print(f"  ⏳ Pending - {migration_name}")

def main():
    parser = argparse.ArgumentParser(description="Health App Migration Runner")
    parser.add_argument("--database-url", help="Database URL (overrides config)")
    parser.add_argument("--force", action="store_true", help="Continue on migration failure")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    
    args = parser.parse_args()
    
    # Create migration runner
    runner = MigrationRunner(args.database_url)
    
    if args.status:
        runner.show_status()
    else:
        success = runner.run_migrations(force=args.force, dry_run=args.dry_run)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
