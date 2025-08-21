#!/usr/bin/env python3
"""
Migration script to add role and privilege system to existing database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base, User, Role, Privilege, user_privileges, role_privileges
from app.services.role_service import RoleService

def migrate_to_roles():
    """Migrate existing database to include roles and privileges"""
    
    # Create engine using settings from config
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🚀 Starting migration to role-based system...")
        
        # Create new tables
        print("📋 Creating new tables...")
        Base.metadata.create_all(bind=engine)
        
        # Check if users table needs to be updated
        print("🔍 Checking existing users table...")
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        
        # Add missing columns to users table
        with engine.connect() as conn:
            if 'role' not in existing_columns:
                print("  - Adding 'role' column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))
                conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("  ✅ Added missing columns")
            else:
                print("  ✅ Users table already has required columns")
        
        # Initialize role service
        role_service = RoleService(db)
        
        # Initialize default roles and privileges
        print("🔧 Initializing default roles and privileges...")
        role_service.initialize_default_roles_and_privileges()
        
        # Update existing users to have 'user' role
        print("👥 Updating existing users...")
        existing_users = db.query(User).all()
        for user in existing_users:
            if not hasattr(user, 'role') or not user.role:
                user.role = 'user'
                print(f"  - Updated user {user.email} to role 'user'")
        
        db.commit()
        
        print("✅ Migration completed successfully!")
        print(f"  - {len(existing_users)} users updated")
        print("  - Role system initialized")
        print("  - Privileges configured")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_to_roles() 