#!/usr/bin/env python3
"""
Unified User Management System
This script consolidates all user-related operations into one clean interface.

Usage:
    python scripts/manage_users.py make-admin <email>           # Make user admin
    python scripts/manage_users.py update-role --email <email> --role <role>  # Update user role
    python scripts/manage_users.py list                         # List all users
    python scripts/manage_users.py info <email>                 # Show user info
"""

import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import User, Role, Privilege
from app.services.role_service import RoleService

class UserManager:
    def __init__(self):
        self.engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()
        self.role_service = RoleService(self.db)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
    
    def make_admin(self, email):
        """Make a user an admin by email"""
        try:
            print(f"🔍 Looking for user with email: {email}")
            
            # Find user by email
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                print(f"❌ User with email {email} not found")
                return False
            
            print(f"✅ Found user: {user.full_name} ({user.username})")
            print(f"   Current role: {user.role}")
            
            # Update role to admin
            user.role = "admin"
            self.db.commit()
            
            print(f"🎉 Successfully made {user.full_name} an admin!")
            print(f"   New role: {user.role}")
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.db.rollback()
            return False
    
    def update_role(self, email, role):
        """Update a user's role"""
        try:
            print(f"🔍 Looking for user with email: {email}")
            
            # Find user by email
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                print(f"❌ User with email {email} not found")
                return False
            
            # Check if role exists
            role_obj = self.db.query(Role).filter(Role.name == role).first()
            if not role_obj:
                print(f"❌ Role '{role}' not found")
                return False
            
            print(f"✅ Found user: {user.full_name} ({user.username})")
            print(f"   Current role: {user.role}")
            
            # Update role
            user.role = role
            self.db.commit()
            
            print(f"🎉 Successfully updated {user.full_name}'s role!")
            print(f"   New role: {user.role}")
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.db.rollback()
            return False
    
    def list_users(self):
        """List all users with their roles"""
        try:
            print("👥 All Users")
            print("=" * 80)
            
            users = self.db.query(User).all()
            
            if not users:
                print("No users found.")
                return
            
            print(f"{'Email':<30} {'Username':<20} {'Full Name':<25} {'Role':<10}")
            print("-" * 80)
            
            for user in users:
                print(f"{user.email:<30} {user.username:<20} {user.full_name or 'N/A':<25} {user.role or 'N/A':<10}")
            
            print(f"\n📊 Total users: {len(users)}")
            
            # Show role distribution
            role_counts = {}
            for user in users:
                role = user.role or 'unassigned'
                role_counts[role] = role_counts.get(role, 0) + 1
            
            print("\n📋 Role Distribution:")
            for role, count in role_counts.items():
                print(f"  {role}: {count} users")
            
        except Exception as e:
            print(f"❌ Error listing users: {str(e)}")
    
    def show_user_info(self, email):
        """Show detailed information about a user"""
        try:
            print(f"🔍 Looking for user with email: {email}")
            
            # Find user by email
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                print(f"❌ User with email {email} not found")
                return False
            
            print(f"\n👤 User Information")
            print("=" * 50)
            print(f"  ID: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  Username: {user.username}")
            print(f"  Full Name: {user.full_name or 'N/A'}")
            print(f"  Role: {user.role or 'N/A'}")
            print(f"  Age: {user.age}")
            print(f"  Country: {user.country or 'N/A'}")
            print(f"  State: {user.state or 'N/A'}")
            print(f"  City: {user.city or 'N/A'}")
            print(f"  Pincode: {user.pincode or 'N/A'}")
            print(f"  Is Active: {user.is_active}")
            print(f"  Is Verified: {user.is_verified}")
            print(f"  Created At: {user.created_at}")
            
            # Show user privileges
            if user.role:
                print(f"\n🔐 User Privileges (via role '{user.role}'):")
                try:
                    import asyncio
                    privileges = asyncio.run(self.role_service.get_user_privileges(user.id))
                    if privileges:
                        for priv in sorted(privileges):
                            print(f"  • {priv}")
                    else:
                        print("  No privileges assigned")
                except Exception as e:
                    print(f"  Error fetching privileges: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Unified User Management System')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Make admin command
    make_admin_parser = subparsers.add_parser('make-admin', help='Make user admin')
    make_admin_parser.add_argument('email', help='User email')
    
    # Update role command
    update_role_parser = subparsers.add_parser('update-role', help='Update user role')
    update_role_parser.add_argument('--email', required=True, help='User email')
    update_role_parser.add_argument('--role', required=True, help='New role')
    
    # List command
    subparsers.add_parser('list', help='List all users')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show user information')
    info_parser.add_argument('email', help='User email')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    with UserManager() as manager:
        if args.command == 'make-admin':
            manager.make_admin(args.email)
        elif args.command == 'update-role':
            manager.update_role(args.email, args.role)
        elif args.command == 'list':
            manager.list_users()
        elif args.command == 'info':
            manager.show_user_info(args.email)

if __name__ == "__main__":
    main()
