#!/usr/bin/env python3
"""
Script to add a new privilege to the system
Usage: python add_new_privilege.py --name "privilege_name" --description "Description" --category "category"
"""

import sys
import os
import argparse
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Privilege, Role
from app.services.role_service import RoleService

def add_new_privilege(name, description, category, assign_to_admin=True):
    """Add a new privilege to the system"""
    
    # Create engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print(f"🔧 Adding new privilege: {name}")
        
        # Check if privilege already exists
        existing_priv = db.query(Privilege).filter(Privilege.name == name).first()
        if existing_priv:
            print(f"  ℹ️  Privilege '{name}' already exists")
            return
        
        # Create new privilege
        privilege = Privilege(
            name=name,
            description=description,
            category=category,
            is_active=True
        )
        db.add(privilege)
        db.commit()
        print(f"  ✅ Created privilege: {name}")
        
        # Assign to admin role if requested
        if assign_to_admin:
            print("  👑 Assigning to admin role...")
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            if admin_role:
                admin_role.privileges.append(privilege)
                db.commit()
                print(f"  ✅ Added {name} to admin role")
            else:
                print("  ❌ Admin role not found!")
        
        # Show current privilege count
        total_privileges = db.query(Privilege).count()
        print(f"  📊 Total privileges: {total_privileges}")
        
        print(f"\n✅ Successfully added privilege: {name}")
        print(f"   Description: {description}")
        print(f"   Category: {category}")
        print(f"   Assigned to admin: {'Yes' if assign_to_admin else 'No'}")
        
    except Exception as e:
        print(f"❌ Error adding privilege: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description='Add a new privilege to the system')
    parser.add_argument('--name', required=True, help='Privilege name (e.g., manage_reports)')
    parser.add_argument('--description', required=True, help='Privilege description')
    parser.add_argument('--category', required=True, help='Privilege category (e.g., system, assessment)')
    parser.add_argument('--no-admin', action='store_true', help='Do not assign to admin role')
    
    args = parser.parse_args()
    
    add_new_privilege(
        name=args.name,
        description=args.description,
        category=args.category,
        assign_to_admin=not args.no_admin
    )

if __name__ == "__main__":
    main()
