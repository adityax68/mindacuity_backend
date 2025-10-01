#!/usr/bin/env python3
"""
Complete privilege system initialization for AWS migration
This script sets up all roles, privileges, and assignments
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base, User, Role, Privilege, user_privileges, role_privileges
from app.services.role_service import RoleService

def initialize_aws_privileges():
    """Initialize complete privilege system for AWS"""
    
    # Create engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🚀 Initializing AWS Privilege System...")
        
        # Create all tables
        print("📋 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        # Initialize role service
        role_service = RoleService(db)
        
        # Initialize default roles and privileges
        print("🔧 Setting up roles and privileges...")
        asyncio.run(role_service.initialize_default_roles_and_privileges())
        
        # Add additional privileges that might be missing
        print("➕ Adding additional privileges...")
        additional_privileges = [
            # Research privileges
            {"name": "read_researches", "description": "Read research articles", "category": "research"},
            {"name": "manage_researches", "description": "Manage research articles (create, update, delete)", "category": "research"},
            
            # Admin access privilege
            {"name": "admin_access", "description": "Access to admin panel", "category": "system"},
        ]
        
        for priv_data in additional_privileges:
            existing_priv = db.query(Privilege).filter(Privilege.name == priv_data["name"]).first()
            if not existing_priv:
                privilege = Privilege(**priv_data)
                db.add(privilege)
                print(f"  ✅ Created privilege: {priv_data['name']}")
            else:
                print(f"  ℹ️  Privilege already exists: {priv_data['name']}")
        
        db.commit()
        
        # Ensure admin role has ALL privileges
        print("👑 Ensuring admin role has all privileges...")
        all_privileges = db.query(Privilege).filter(Privilege.is_active == True).all()
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        
        if admin_role:
            admin_role.privileges.clear()
            for privilege in all_privileges:
                admin_role.privileges.append(privilege)
            db.commit()
            print(f"  ✅ Admin role now has {len(all_privileges)} privileges")
        
        # Update existing users to have 'user' role if not set
        print("👥 Updating existing users...")
        users_without_role = db.query(User).filter(
            (User.role == None) | (User.role == '')
        ).all()
        
        for user in users_without_role:
            user.role = 'user'
            print(f"  ✅ Updated user {user.email} to role 'user'")
        
        db.commit()
        
        # Verify the setup
        print("\n🔍 Verifying setup...")
        
        # Count roles and privileges
        total_roles = db.query(Role).count()
        total_privileges = db.query(Privilege).count()
        total_users = db.query(User).count()
        admin_users = db.query(User).filter(User.role == "admin").count()
        
        print(f"  📊 Total roles: {total_roles}")
        print(f"  📊 Total privileges: {total_privileges}")
        print(f"  📊 Total users: {total_users}")
        print(f"  📊 Admin users: {admin_users}")
        
        # Show role privilege counts
        print("\n📋 Role Privilege Summary:")
        roles = db.query(Role).all()
        for role in roles:
            priv_count = len(role.privileges)
            print(f"  {role.name}: {priv_count} privileges")
        
        # Show privilege categories
        print("\n📂 Privilege Categories:")
        categories = db.query(Privilege.category).distinct().all()
        for category in categories:
            if category[0]:
                count = db.query(Privilege).filter(Privilege.category == category[0]).count()
                print(f"  {category[0]}: {count} privileges")
        
        print("\n✅ AWS Privilege System initialization completed successfully!")
        print("\n🎯 Next steps:")
        print("  1. Test the system with: python scripts/check_privileges.py")
        print("  2. Create admin users with: python scripts/make_admin.py <email>")
        print("  3. Verify API endpoints are working")
        
    except Exception as e:
        print(f"❌ Error during initialization: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    initialize_aws_privileges()
