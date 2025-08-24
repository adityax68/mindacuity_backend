#!/usr/bin/env python3
"""
Script to add admin_access privilege and assign it to admin users
"""
import asyncio
from app.database import SessionLocal
from app.models import User, Role, Privilege
from app.services.role_service import RoleService

async def add_admin_access_privilege():
    db = SessionLocal()
    try:
        # Check if admin_access privilege exists
        admin_access_priv = db.query(Privilege).filter(Privilege.name == "admin_access").first()
        
        if not admin_access_priv:
            print("Creating admin_access privilege...")
            admin_access_priv = Privilege(
                name="admin_access",
                description="Access to admin panel",
                category="system"
            )
            db.add(admin_access_priv)
            db.commit()
            print("✅ Created admin_access privilege")
        else:
            print("✅ admin_access privilege already exists")
        
        # Get admin role
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            # Add admin_access privilege to admin role
            if admin_access_priv not in admin_role.privileges:
                admin_role.privileges.append(admin_access_priv)
                db.commit()
                print("✅ Added admin_access privilege to admin role")
            else:
                print("✅ admin_access privilege already assigned to admin role")
        
        # Verify admin users have the privilege
        role_service = RoleService(db)
        admin_users = db.query(User).filter(User.role == 'admin').all()
        
        print(f"\nChecking {len(admin_users)} admin users:")
        for user in admin_users:
            privileges = await role_service.get_user_privileges(user.id)
            has_admin_access = 'admin_access' in privileges
            print(f"User: {user.email} - admin_access: {'✅' if has_admin_access else '❌'}")
        
        print("\n🎉 Admin access setup complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(add_admin_access_privilege()) 