#!/usr/bin/env python3
"""
Script to check current privilege and role status in the database.
Use this to verify the current state before and after running privilege management scripts
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User, Role, Privilege
from app.services.role_service import RoleService

async def check_privileges():
    """Check current privilege and role status"""
    db = SessionLocal()
    try:
        print("🔍 Checking current database state...")
        
        # Check roles
        print("\n📋 ROLES:")
        roles = db.query(Role).all()
        if roles:
            for role in roles:
                print(f"  - {role.name}: {role.description} (Active: {role.is_active})")
                print(f"    Privileges: {len(role.privileges)}")
                for priv in role.privileges:
                    print(f"      - {priv.name} ({priv.category})")
        else:
            print("  ❌ No roles found")
        
        # Check privileges
        print("\n🔐 PRIVILEGES:")
        privileges = db.query(Privilege).all()
        if privileges:
            privileges_by_category = {}
            for priv in privileges:
                category = priv.category or "uncategorized"
                if category not in privileges_by_category:
                    privileges_by_category[category] = []
                privileges_by_category[category].append(priv)
            
            for category, privs in privileges_by_category.items():
                print(f"\n  {category.upper()}:")
                for priv in sorted(privs, key=lambda x: x.name):
                    print(f"    - {priv.name}: {priv.description}")
        else:
            print("  ❌ No privileges found")
        
        # Check users
        print("\n👥 USERS:")
        users = db.query(User).all()
        if users:
            for user in users:
                print(f"  - {user.email}: role={user.role}, active={user.is_active}")
        else:
            print("  ❌ No users found")
        
        # Check admin users specifically
        print("\n👑 ADMIN USERS:")
        admin_users = db.query(User).filter(User.role == 'admin').all()
        if admin_users:
            role_service = RoleService(db)
            for user in admin_users:
                privileges = await role_service.get_user_privileges(user.id)
                print(f"  - {user.email}: {len(privileges)} privileges")
                print(f"    Privileges: {', '.join(sorted(privileges))}")
        else:
            print("  ❌ No admin users found")
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"  - Total roles: {len(roles)}")
        print(f"  - Total privileges: {len(privileges)}")
        print(f"  - Total users: {len(users)}")
        print(f"  - Admin users: {len(admin_users)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(check_privileges())
