#!/usr/bin/env python3
"""
Script to backup the privilege system
Usage: python backup_privileges.py [--output backup_file.json]
"""

import sys
import os
import argparse
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import User, Role, Privilege

def backup_privileges(output_file=None):
    """Backup the privilege system to JSON file"""
    
    # Create engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("💾 Creating privilege system backup...")
        
        # Generate filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"privilege_backup_{timestamp}.json"
        
        # Collect all data
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "privileges": [],
            "roles": [],
            "role_privileges": [],
            "users": []
        }
        
        # Backup privileges
        print("  📋 Backing up privileges...")
        privileges = db.query(Privilege).all()
        for priv in privileges:
            backup_data["privileges"].append({
                "id": priv.id,
                "name": priv.name,
                "description": priv.description,
                "category": priv.category,
                "is_active": priv.is_active,
                "created_at": priv.created_at.isoformat() if priv.created_at else None
            })
        
        # Backup roles
        print("  👥 Backing up roles...")
        roles = db.query(Role).all()
        for role in roles:
            backup_data["roles"].append({
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "is_active": role.is_active,
                "created_at": role.created_at.isoformat() if role.created_at else None
            })
        
        # Backup role-privilege relationships
        print("  🔗 Backing up role-privilege relationships...")
        for role in roles:
            for priv in role.privileges:
                backup_data["role_privileges"].append({
                    "role_id": role.id,
                    "role_name": role.name,
                    "privilege_id": priv.id,
                    "privilege_name": priv.name
                })
        
        # Backup users (basic info only)
        print("  👤 Backing up users...")
        users = db.query(User).all()
        for user in users:
            backup_data["users"].append({
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None
            })
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        print(f"  ✅ Backup saved to: {output_file}")
        print(f"  📊 Backup contains:")
        print(f"     - {len(backup_data['privileges'])} privileges")
        print(f"     - {len(backup_data['roles'])} roles")
        print(f"     - {len(backup_data['role_privileges'])} role-privilege relationships")
        print(f"     - {len(backup_data['users'])} users")
        
        print(f"\n✅ Privilege system backup completed successfully!")
        
    except Exception as e:
        print(f"❌ Error creating backup: {str(e)}")
        raise
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description='Backup the privilege system')
    parser.add_argument('--output', help='Output file name (default: privilege_backup_YYYYMMDD_HHMMSS.json)')
    
    args = parser.parse_args()
    
    backup_privileges(args.output)

if __name__ == "__main__":
    main()
