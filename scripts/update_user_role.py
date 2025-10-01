#!/usr/bin/env python3
"""
Script to update a user's role
Usage: python update_user_role.py --email "user@example.com" --role "admin"
"""

import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import User, Role

def update_user_role(email, new_role):
    """Update a user's role"""
    
    # Create engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print(f"👤 Updating role for user: {email}")
        
        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"  ❌ User with email '{email}' not found")
            return
        
        # Validate role
        valid_roles = ["user", "admin", "employee", "hr", "counsellor"]
        if new_role not in valid_roles:
            print(f"  ❌ Invalid role '{new_role}'. Valid roles: {valid_roles}")
            return
        
        # Check if role exists in database
        role = db.query(Role).filter(Role.name == new_role).first()
        if not role:
            print(f"  ❌ Role '{new_role}' not found in database")
            return
        
        # Update user role
        old_role = user.role
        user.role = new_role
        db.commit()
        
        print(f"  ✅ Updated user '{email}' from role '{old_role}' to '{new_role}'")
        
        # Show user info
        print(f"  📊 User info:")
        print(f"     Email: {user.email}")
        print(f"     Username: {user.username}")
        print(f"     Full Name: {user.full_name}")
        print(f"     Role: {user.role}")
        print(f"     Active: {user.is_active}")
        
    except Exception as e:
        print(f"❌ Error updating user role: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description='Update a user\'s role')
    parser.add_argument('--email', required=True, help='User email address')
    parser.add_argument('--role', required=True, help='New role (user, admin, employee, hr, counsellor)')
    
    args = parser.parse_args()
    
    update_user_role(args.email, args.role)

if __name__ == "__main__":
    main()
