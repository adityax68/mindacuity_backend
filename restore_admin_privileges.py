#!/usr/bin/env python3
"""
Comprehensive script to restore all admin privileges after database reset.
This script will:
1. Initialize all default roles and privileges
2. Assign all privileges to admin role
3. Verify admin users have proper access
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User, Role, Privilege
from app.services.role_service import RoleService

async def restore_admin_privileges():
    """Restore all admin privileges after database reset"""
    db = SessionLocal()
    try:
        print("🚀 Starting comprehensive admin privilege restoration...")
        
        # Initialize role service
        role_service = RoleService(db)
        
        # Step 1: Initialize all default roles and privileges
        print("\n📋 Step 1: Initializing default roles and privileges...")
        await role_service.initialize_default_roles_and_privileges()
        print("✅ Default roles and privileges initialized")
        
        # Step 2: Get all privileges and assign them to admin role
        print("\n🔧 Step 2: Assigning all privileges to admin role...")
        all_privileges = db.query(Privilege).filter(Privilege.is_active == True).all()
        privilege_names = [priv.name for priv in all_privileges]
        
        await role_service.assign_privileges_to_role("admin", privilege_names)
        print(f"✅ Assigned {len(privilege_names)} privileges to admin role")
        
        # Step 3: Verify admin role has all privileges
        print("\n🔍 Step 3: Verifying admin role privileges...")
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            admin_privileges = [priv.name for priv in admin_role.privileges]
            print(f"Admin role has {len(admin_privileges)} privileges:")
            for priv in sorted(admin_privileges):
                print(f"  - {priv}")
        else:
            print("❌ Admin role not found!")
            return False
        
        # Step 4: Check admin users
        print("\n👥 Step 4: Checking admin users...")
        admin_users = db.query(User).filter(User.role == 'admin').all()
        
        if not admin_users:
            print("⚠️  No admin users found. You may need to create admin users first.")
            print("   Use: python scripts/make_admin.py <email>")
        else:
            print(f"Found {len(admin_users)} admin users:")
            for user in admin_users:
                privileges = await role_service.get_user_privileges(user.id)
                print(f"  - {user.email}: {len(privileges)} privileges")
                
                # Check for key admin privileges
                key_privileges = [
                    "admin_access", "read_users", "update_users", "manage_roles", 
                    "view_analytics", "manage_organisations", "read_organisations",
                    "manage_employees", "manage_complaints", "read_all_assessments"
                ]
                
                missing_privileges = []
                for key_priv in key_privileges:
                    if key_priv not in privileges:
                        missing_privileges.append(key_priv)
                
                if missing_privileges:
                    print(f"    ⚠️  Missing key privileges: {', '.join(missing_privileges)}")
                else:
                    print(f"    ✅ All key admin privileges present")
        
        # Step 5: List all available privileges by category
        print("\n📊 Step 5: Privilege summary by category...")
        privileges_by_category = {}
        for priv in all_privileges:
            category = priv.category or "uncategorized"
            if category not in privileges_by_category:
                privileges_by_category[category] = []
            privileges_by_category[category].append(priv.name)
        
        for category, privs in privileges_by_category.items():
            print(f"\n{category.upper()}:")
            for priv in sorted(privs):
                print(f"  - {priv}")
        
        print(f"\n🎉 Admin privilege restoration complete!")
        print(f"   - Total privileges: {len(all_privileges)}")
        print(f"   - Admin users: {len(admin_users)}")
        print(f"   - Categories: {len(privileges_by_category)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

async def verify_admin_access():
    """Verify that admin access is working properly"""
    db = SessionLocal()
    try:
        print("\n🔍 Verifying admin access...")
        
        role_service = RoleService(db)
        admin_users = db.query(User).filter(User.role == 'admin').all()
        
        if not admin_users:
            print("❌ No admin users found for verification")
            return False
        
        # Test key admin privileges
        test_privileges = [
            "admin_access", "read_users", "update_users", "manage_roles",
            "view_analytics", "manage_organisations", "read_organisations",
            "manage_employees", "manage_complaints", "read_all_assessments"
        ]
        
        for user in admin_users:
            print(f"\nTesting user: {user.email}")
            user_privileges = await role_service.get_user_privileges(user.id)
            
            all_present = True
            for test_priv in test_privileges:
                has_priv = test_priv in user_privileges
                status = "✅" if has_priv else "❌"
                print(f"  {status} {test_priv}")
                if not has_priv:
                    all_present = False
            
            if all_present:
                print(f"  🎉 User {user.email} has all required admin privileges!")
            else:
                print(f"  ⚠️  User {user.email} is missing some admin privileges")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("ADMIN PRIVILEGE RESTORATION SCRIPT")
    print("=" * 60)
    
    # Run the restoration
    success = asyncio.run(restore_admin_privileges())
    
    if success:
        # Run verification
        asyncio.run(verify_admin_access())
        print("\n✅ Script completed successfully!")
    else:
        print("\n❌ Script failed. Please check the errors above.")
        sys.exit(1)
