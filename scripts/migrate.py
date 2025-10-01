#!/usr/bin/env python3
"""
Simple Migration Manager for Health App
Quick commands for common migration tasks.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def run_command(cmd):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def show_help():
    """Show help information"""
    print("🏥 Health App Migration Manager")
    print("=" * 40)
    print()
    print("Available commands:")
    print("  migrate run          - Run all pending migrations")
    print("  migrate status       - Show migration status")
    print("  migrate dry-run      - Show what would be done")
    print("  migrate force        - Run migrations (continue on error)")
    print("  migrate reset        - Reset database (DANGEROUS!)")
    print("  migrate seed         - Reset and seed database")
    print()
    print("Examples:")
    print("  python scripts/migrate.py run")
    print("  python scripts/migrate.py status")
    print("  python scripts/migrate.py dry-run")

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1]
    script_path = Path(__file__).parent / "run_migrations.py"
    
    if command == "run":
        print("🚀 Running migrations...")
        success = run_command(f"python {script_path}")
        sys.exit(0 if success else 1)
    
    elif command == "status":
        print("📊 Checking migration status...")
        success = run_command(f"python {script_path} --status")
        sys.exit(0 if success else 1)
    
    elif command == "dry-run":
        print("🔍 Dry run mode...")
        success = run_command(f"python {script_path} --dry-run")
        sys.exit(0 if success else 1)
    
    elif command == "force":
        print("🚀 Running migrations (force mode)...")
        success = run_command(f"python {script_path} --force")
        sys.exit(0 if success else 1)
    
    elif command == "reset":
        print("⚠️  WARNING: This will reset your database!")
        confirm = input("Are you sure? Type 'yes' to continue: ")
        if confirm.lower() == 'yes':
            print("🔄 Resetting database...")
            success = run_command("python reset_db.py")
            sys.exit(0 if success else 1)
        else:
            print("❌ Database reset cancelled")
            sys.exit(1)
    
    elif command == "seed":
        print("⚠️  WARNING: This will reset and seed your database!")
        confirm = input("Are you sure? Type 'yes' to continue: ")
        if confirm.lower() == 'yes':
            print("🔄 Resetting and seeding database...")
            success = run_command("python reset_db.py --seed")
            sys.exit(0 if success else 1)
        else:
            print("❌ Database reset cancelled")
            sys.exit(1)
    
    else:
        print(f"❌ Unknown command: {command}")
        show_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
