#!/usr/bin/env python3
"""
Script to properly initialize roles and privileges system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base, User, Role, Privilege, user_privileges, role_privileges

def initialize_roles_and_privileges():
    """Initialize the roles and privileges system"""
    
    # Create engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🔧 Initializing roles and privileges system...")
        
        # Create default privileges
        print("📋 Creating default privileges...")
        default_privileges = [
            # Assessment privileges
            {"name": "take_assessment", "description": "Take mental health assessments", "category": "assessment"},
            {"name": "read_own_assessments", "description": "Read own assessment results", "category": "assessment"},
            {"name": "create_assessment", "description": "Create new assessments", "category": "assessment"},
            {"name": "read_all_assessments", "description": "Read all user assessments", "category": "assessment"},
            {"name": "delete_assessment", "description": "Delete assessments", "category": "assessment"},
            
            # User management privileges
            {"name": "read_users", "description": "Read user information", "category": "user_management"},
            {"name": "create_users", "description": "Create new users", "category": "user_management"},
            {"name": "update_users", "description": "Update user information", "category": "user_management"},
            {"name": "delete_users", "description": "Delete users", "category": "user_management"},
            
            # System privileges
            {"name": "system_config", "description": "Configure system settings", "category": "system"},
            {"name": "view_analytics", "description": "View system analytics", "category": "system"},
            {"name": "manage_roles", "description": "Manage user roles and privileges", "category": "system"},
        ]
        
        # Create privileges if they don't exist
        for priv_data in default_privileges:
            existing_priv = db.query(Privilege).filter(Privilege.name == priv_data["name"]).first()
            if not existing_priv:
                privilege = Privilege(**priv_data)
                db.add(privilege)
                print(f"  ✅ Created privilege: {priv_data['name']}")
            else:
                print(f"  ℹ️  Privilege already exists: {priv_data['name']}")
        
        db.commit()
        print(f"  📊 Total privileges: {db.query(Privilege).count()}")
        
        # Create default roles
        print("\n👥 Creating default roles...")
        user_role = db.query(Role).filter(Role.name == "user").first()
        if not user_role:
            user_role = Role(name="user", description="Regular user with basic access")
            db.add(user_role)
            print("  ✅ Created user role")
        else:
            print("  ℹ️  User role already exists")
        
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator with full access")
            db.add(admin_role)
            print("  ✅ Created admin role")
        else:
            print("  ℹ️  Admin role already exists")
        
        db.commit()
        print(f"  📊 Total roles: {db.query(Role).count()}")
        
        # Assign privileges to roles
        print("\n🔗 Assigning privileges to roles...")
        
        # User role gets basic privileges
        user_privileges = ["take_assessment", "read_own_assessments"]
        user_role = db.query(Role).filter(Role.name == "user").first()
        if user_role:
            user_role.privileges.clear()
            for priv_name in user_privileges:
                privilege = db.query(Privilege).filter(Privilege.name == priv_name).first()
                if privilege:
                    user_role.privileges.append(privilege)
            print(f"  ✅ Assigned {len(user_privileges)} privileges to user role")
        
        # Admin role gets all privileges
        all_privileges = db.query(Privilege).filter(Privilege.is_active == True).all()
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            admin_role.privileges.clear()
            for privilege in all_privileges:
                admin_role.privileges.append(privilege)
            print(f"  ✅ Assigned {len(all_privileges)} privileges to admin role")
        
        db.commit()
        
        # Verify the setup
        print("\n🔍 Verifying setup...")
        user_role = db.query(Role).filter(Role.name == "user").first()
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        
        if user_role:
            print(f"  👤 User role privileges: {[p.name for p in user_role.privileges]}")
        if admin_role:
            print(f"  👑 Admin role privileges: {[p.name for p in admin_role.privileges]}")
        
        print("\n✅ Role system initialization completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during initialization: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    initialize_roles_and_privileges() 