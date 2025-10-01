#!/usr/bin/env python3
"""
AWS Migration Setup Script
This script helps migrate from Neon to AWS RDS and sets up the privilege system
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base, User, Role, Privilege, user_privileges, role_privileges
from app.services.role_service import RoleService

def check_database_connection():
    """Check if database connection is working"""
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_tables():
    """Create all necessary tables"""
    try:
        engine = create_engine(settings.database_url)
        print("📋 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def check_existing_data():
    """Check what data already exists"""
    try:
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("🔍 Checking existing data...")
        
        # Check users
        user_count = db.query(User).count()
        print(f"  👥 Users: {user_count}")
        
        # Check roles
        role_count = db.query(Role).count()
        print(f"  👥 Roles: {role_count}")
        
        # Check privileges
        privilege_count = db.query(Privilege).count()
        print(f"  🔐 Privileges: {privilege_count}")
        
        # Show existing roles
        if role_count > 0:
            roles = db.query(Role).all()
            print("  📋 Existing roles:")
            for role in roles:
                priv_count = len(role.privileges)
                print(f"    - {role.name}: {priv_count} privileges")
        
        # Show existing privileges by category
        if privilege_count > 0:
            privileges = db.query(Privilege).all()
            categories = {}
            for priv in privileges:
                category = priv.category or "uncategorized"
                if category not in categories:
                    categories[category] = []
                categories[category].append(priv.name)
            
            print("  📂 Existing privileges by category:")
            for category, privs in categories.items():
                print(f"    {category}: {len(privs)} privileges")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Failed to check existing data: {e}")
        return False

def migrate_users_table():
    """Add missing columns to users table if needed"""
    try:
        engine = create_engine(settings.database_url)
        inspector = inspect(engine)
        
        print("🔍 Checking users table structure...")
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        
        with engine.connect() as conn:
            # Add missing columns
            if 'role' not in existing_columns:
                print("  ➕ Adding 'role' column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))
                conn.commit()
                print("  ✅ Added 'role' column")
            
            if 'is_verified' not in existing_columns:
                print("  ➕ Adding 'is_verified' column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("  ✅ Added 'is_verified' column")
            
            if 'is_active' not in existing_columns:
                print("  ➕ Adding 'is_active' column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                conn.commit()
                print("  ✅ Added 'is_active' column")
            
            print("✅ Users table migration completed")
            return True
    except Exception as e:
        print(f"❌ Failed to migrate users table: {e}")
        return False

def initialize_privilege_system():
    """Initialize the complete privilege system"""
    try:
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("🔧 Initializing privilege system...")
        role_service = RoleService(db)
        
        # Initialize default roles and privileges
        asyncio.run(role_service.initialize_default_roles_and_privileges())
        
        # Update existing users to have 'user' role if not set
        print("👥 Updating existing users...")
        users_without_role = db.query(User).filter(
            (User.role == None) | (User.role == '')
        ).all()
        
        for user in users_without_role:
            user.role = 'user'
            print(f"  ✅ Updated user {user.email} to role 'user'")
        
        db.commit()
        
        # Verify setup
        print("\n🔍 Verifying privilege system...")
        total_roles = db.query(Role).count()
        total_privileges = db.query(Privilege).count()
        total_users = db.query(User).count()
        
        print(f"  📊 Total roles: {total_roles}")
        print(f"  📊 Total privileges: {total_privileges}")
        print(f"  📊 Total users: {total_users}")
        
        # Show role privilege counts
        print("\n📋 Role Privilege Summary:")
        roles = db.query(Role).all()
        for role in roles:
            priv_count = len(role.privileges)
            print(f"  {role.name}: {priv_count} privileges")
        
        db.close()
        print("✅ Privilege system initialization completed")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize privilege system: {e}")
        return False

def main():
    """Main migration process"""
    print("🚀 Starting AWS Migration Setup...")
    print("=" * 50)
    
    # Step 1: Check database connection
    if not check_database_connection():
        print("❌ Cannot proceed without database connection")
        return
    
    # Step 2: Create tables
    if not create_tables():
        print("❌ Cannot proceed without creating tables")
        return
    
    # Step 3: Check existing data
    check_existing_data()
    
    # Step 4: Migrate users table
    if not migrate_users_table():
        print("❌ Failed to migrate users table")
        return
    
    # Step 5: Initialize privilege system
    if not initialize_privilege_system():
        print("❌ Failed to initialize privilege system")
        return
    
    print("\n" + "=" * 50)
    print("✅ AWS Migration Setup Completed Successfully!")
    print("\n🎯 Next steps:")
    print("  1. Test the system: python scripts/check_privileges.py")
    print("  2. Create admin users: python scripts/make_admin.py <email>")
    print("  3. Test API endpoints")
    print("  4. Update your application configuration")

if __name__ == "__main__":
    main()
