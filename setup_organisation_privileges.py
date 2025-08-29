#!/usr/bin/env python3
"""
Script to set up privileges for organisation management.
Run this script to create the required privileges for admin users.
"""

import os
import sys
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Privilege, User
from app.services.role_service import RoleService

async def setup_organisation_privileges():
    """Set up privileges for organisation management."""
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create privileges if they don't exist
        privileges_to_create = [
            {
                "name": "manage_organisations",
                "description": "Create, update, and delete organisations",
                "category": "organisation_management"
            },
            {
                "name": "read_organisations", 
                "description": "View organisation details and lists",
                "category": "organisation_management"
            }
        ]
        
        for priv_data in privileges_to_create:
            existing_privilege = db.query(Privilege).filter(Privilege.name == priv_data["name"]).first()
            if not existing_privilege:
                privilege = Privilege(
                    name=priv_data["name"],
                    description=priv_data["description"],
                    category=priv_data["category"],
                    is_active=True
                )
                db.add(privilege)
                print(f"✅ Created privilege: {priv_data['name']}")
            else:
                print(f"ℹ️  Privilege already exists: {priv_data['name']}")
        
        db.commit()
        
        # Assign privileges to admin role (admin users will inherit these)
        role_service = RoleService(db)
        
        # Get all privileges including the new ones
        all_privileges = db.query(Privilege).filter(Privilege.is_active == True).all()
        privilege_names = [priv.name for priv in all_privileges]
        
        # Assign all privileges to admin role
        await role_service.assign_privileges_to_role("admin", privilege_names)
        print("✅ Added organisation privileges to admin role")
        
        # Count admin users
        admin_users = db.query(User).filter(User.role == "admin").all()
        print(f"ℹ️  {len(admin_users)} admin users will have access to organisation management")
        
        print("✅ Organisation privileges setup complete!")
        
    except Exception as e:
        print(f"❌ Error setting up organisation privileges: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    import asyncio
    print("Setting up organisation privileges...")
    asyncio.run(setup_organisation_privileges()) 