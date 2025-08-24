#!/usr/bin/env python3
"""
Script to check and fix admin privileges
"""
import asyncio
from app.database import SessionLocal
from app.models import User
from app.services.role_service import RoleService

async def check_and_fix_admin_privileges():
    db = SessionLocal()
    try:
        role_service = RoleService(db)
        
        # Get all admin users
        admin_users = db.query(User).filter(User.role == 'admin').all()
        print(f"Found {len(admin_users)} admin users:")
        
        for user in admin_users:
            print(f"\nUser: {user.email} (ID: {user.id})")
            
            # Check current privileges
            privileges = await role_service.get_user_privileges(user.id)
            print(f"Current privileges: {list(privileges)}")
            
            # Check if admin_access privilege exists
            if 'admin_access' not in privileges:
                print("❌ Missing admin_access privilege - adding it...")
                
                # Add admin_access privilege
                await role_service.add_user_privilege(user.id, 'admin_access')
                print("✅ Added admin_access privilege")
                
                # Verify it was added
                new_privileges = await role_service.get_user_privileges(user.id)
                print(f"Updated privileges: {list(new_privileges)}")
            else:
                print("✅ admin_access privilege already exists")
        
        print("\n🎉 Admin privileges check complete!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(check_and_fix_admin_privileges()) 