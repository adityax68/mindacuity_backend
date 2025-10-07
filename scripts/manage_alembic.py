#!/usr/bin/env python3
"""
Alembic Migration Management System
This script provides a clean interface to Alembic migrations.

Usage:
    python scripts/manage_alembic.py status                 # Show migration status
    python scripts/manage_alembic.py upgrade                # Apply all pending migrations
    python scripts/manage_alembic.py downgrade [revision]   # Downgrade to specific revision
    python scripts/manage_alembic.py history                # Show migration history
    python scripts/manage_alembic.py current                # Show current revision
    python scripts/manage_alembic.py create "message"       # Create new migration
    python scripts/manage_alembic.py reset                  # Reset database (DANGEROUS!)
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

def run_alembic_command(cmd, description):
    """Run an alembic command and return success status"""
    try:
        print(f"🚀 {description}...")
        result = subprocess.run(f"alembic {cmd}", shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Alembic Migration Management System')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show migration status')
    
    # Upgrade command
    subparsers.add_parser('upgrade', help='Apply all pending migrations')
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser('downgrade', help='Downgrade to specific revision')
    downgrade_parser.add_argument('revision', nargs='?', default='-1', help='Revision to downgrade to (default: -1)')
    
    # History command
    subparsers.add_parser('history', help='Show migration history')
    
    # Current command
    subparsers.add_parser('current', help='Show current revision')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument('message', help='Migration message')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset database (DANGEROUS!)')
    reset_parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    
    if args.command == 'status':
        success = run_alembic_command("current", "Checking current migration status")
        if success:
            run_alembic_command("history --verbose", "Showing migration history")
    
    elif args.command == 'upgrade':
        success = run_alembic_command("upgrade head", "Applying all pending migrations")
    
    elif args.command == 'downgrade':
        revision = args.revision
        if revision == '-1':
            success = run_alembic_command("downgrade -1", "Downgrading one revision")
        else:
            success = run_alembic_command(f"downgrade {revision}", f"Downgrading to revision {revision}")
    
    elif args.command == 'history':
        success = run_alembic_command("history --verbose", "Showing migration history")
    
    elif args.command == 'current':
        success = run_alembic_command("current", "Showing current revision")
    
    elif args.command == 'create':
        message = args.message
        success = run_alembic_command(f'revision --autogenerate -m "{message}"', f"Creating new migration: {message}")
    
    elif args.command == 'reset':
        if not args.confirm:
            print("⚠️  WARNING: This will DROP ALL TABLES and reset your database!")
            print("   This action cannot be undone!")
            confirm = input("Are you sure? Type 'yes' to continue: ")
            if confirm.lower() != 'yes':
                print("❌ Database reset cancelled")
                return
        
        print("🔄 Resetting database...")
        # First downgrade to base (removes all tables)
        success1 = run_alembic_command("downgrade base", "Downgrading to base (removing all tables)")
        # Then upgrade to head (recreates all tables)
        success2 = run_alembic_command("upgrade head", "Upgrading to head (recreating all tables)")
        success = success1 and success2
        
        if success:
            print("✅ Database reset completed successfully!")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
