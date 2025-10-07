#!/usr/bin/env python3
"""
Unified Privilege Management System
This script consolidates all privilege-related operations into one clean interface.

Usage:
    python scripts/manage_privileges.py init                    # Initialize privilege system
    python scripts/manage_privileges.py add --name "priv_name" --description "Description" --category "category"
    python scripts/manage_privileges.py assign --privilege "priv_name" --role "role_name"
    python scripts/manage_privileges.py list                    # List all privileges
    python scripts/manage_privileges.py status                  # Show system status
    python scripts/manage_privileges.py backup [--output file]  # Backup privilege system
    python scripts/manage_privileges.py restore --backup file   # Restore from backup
"""

import sys
import os
import argparse
import asyncio
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base, User, Role, Privilege, user_privileges, role_privileges
from app.services.role_service import RoleService

class PrivilegeManager:
    def __init__(self):
        self.engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()
        self.role_service = RoleService(self.db)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
    
    def init_system(self):
        """Initialize the complete privilege system"""
        try:
            print("🚀 Initializing Privilege System...")
            
            # Create all tables
            print("📋 Creating database tables...")
            Base.metadata.create_all(bind=self.engine)
            
            # Initialize default roles and privileges
            print("🔧 Setting up roles and privileges...")
            asyncio.run(self.role_service.initialize_default_roles_and_privileges())
            
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
                existing_priv = self.db.query(Privilege).filter(Privilege.name == priv_data["name"]).first()
                if not existing_priv:
                    privilege = Privilege(**priv_data)
                    self.db.add(privilege)
                    print(f"  ✅ Created privilege: {priv_data['name']}")
                else:
                    print(f"  ℹ️  Privilege already exists: {priv_data['name']}")
            
            self.db.commit()
            
            # Ensure admin role has ALL privileges
            print("👑 Ensuring admin role has all privileges...")
            all_privileges = self.db.query(Privilege).filter(Privilege.is_active == True).all()
            admin_role = self.db.query(Role).filter(Role.name == "admin").first()
            
            if admin_role:
                admin_role.privileges.clear()
                for privilege in all_privileges:
                    admin_role.privileges.append(privilege)
                self.db.commit()
                print(f"  ✅ Admin role now has {len(all_privileges)} privileges")
            
            # Update existing users to have 'user' role if not set
            print("👥 Updating existing users...")
            users_without_role = self.db.query(User).filter(
                (User.role == None) | (User.role == '')
            ).all()
            
            for user in users_without_role:
                user.role = 'user'
                print(f"  ✅ Updated user {user.email} to role 'user'")
            
            self.db.commit()
            
            # Show final status
            self.show_status()
            
            print("\n✅ Privilege System initialization completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during initialization: {str(e)}")
            self.db.rollback()
            raise
    
    def add_privilege(self, name, description, category, assign_to_admin=True):
        """Add a new privilege to the system"""
        try:
            print(f"🔧 Adding new privilege: {name}")
            
            # Check if privilege already exists
            existing_priv = self.db.query(Privilege).filter(Privilege.name == name).first()
            if existing_priv:
                print(f"  ℹ️  Privilege '{name}' already exists")
                return
            
            # Create new privilege
            privilege = Privilege(
                name=name,
                description=description,
                category=category,
                is_active=True
            )
            self.db.add(privilege)
            self.db.commit()
            print(f"  ✅ Created privilege: {name}")
            
            # Assign to admin role if requested
            if assign_to_admin:
                print("  👑 Assigning to admin role...")
                admin_role = self.db.query(Role).filter(Role.name == "admin").first()
                if admin_role:
                    admin_role.privileges.append(privilege)
                    self.db.commit()
                    print(f"  ✅ Added {name} to admin role")
                else:
                    print("  ❌ Admin role not found!")
            
            print(f"\n✅ Successfully added privilege: {name}")
            
        except Exception as e:
            print(f"❌ Error adding privilege: {str(e)}")
            self.db.rollback()
            raise
    
    def assign_privilege(self, privilege_name, role_name):
        """Assign a privilege to a role"""
        try:
            print(f"🔗 Assigning privilege '{privilege_name}' to role '{role_name}'")
            
            # Find privilege
            privilege = self.db.query(Privilege).filter(Privilege.name == privilege_name).first()
            if not privilege:
                print(f"  ❌ Privilege '{privilege_name}' not found")
                return
            
            # Find role
            role = self.db.query(Role).filter(Role.name == role_name).first()
            if not role:
                print(f"  ❌ Role '{role_name}' not found")
                return
            
            # Check if already assigned
            if privilege in role.privileges:
                print(f"  ℹ️  Privilege '{privilege_name}' already assigned to role '{role_name}'")
                return
            
            # Assign privilege to role
            role.privileges.append(privilege)
            self.db.commit()
            print(f"  ✅ Successfully assigned '{privilege_name}' to role '{role_name}'")
            
        except Exception as e:
            print(f"❌ Error assigning privilege: {str(e)}")
            self.db.rollback()
            raise
    
    def list_privileges(self):
        """List all privileges by category"""
        try:
            print("📋 All Privileges by Category")
            print("=" * 50)
            
            privileges = self.db.query(Privilege).filter(Privilege.is_active == True).all()
            categories = {}
            
            for priv in privileges:
                category = priv.category or "uncategorized"
                if category not in categories:
                    categories[category] = []
                categories[category].append(priv)
            
            for category, privs in categories.items():
                print(f"\n📂 {category.upper()} ({len(privs)} privileges)")
                for priv in sorted(privs, key=lambda x: x.name):
                    print(f"  • {priv.name}: {priv.description}")
            
            print(f"\n📊 Total: {len(privileges)} active privileges")
            
        except Exception as e:
            print(f"❌ Error listing privileges: {str(e)}")
    
    def show_status(self):
        """Show privilege system status"""
        try:
            print("\n📊 Privilege System Status")
            print("=" * 40)
            
            # Count roles and privileges
            total_roles = self.db.query(Role).count()
            total_privileges = self.db.query(Privilege).count()
            total_users = self.db.query(User).count()
            admin_users = self.db.query(User).filter(User.role == "admin").count()
            
            print(f"  📊 Total roles: {total_roles}")
            print(f"  📊 Total privileges: {total_privileges}")
            print(f"  📊 Total users: {total_users}")
            print(f"  📊 Admin users: {admin_users}")
            
            # Show role privilege counts
            print("\n📋 Role Privilege Summary:")
            roles = self.db.query(Role).all()
            for role in roles:
                priv_count = len(role.privileges)
                print(f"  {role.name}: {priv_count} privileges")
            
            # Show privilege categories
            print("\n📂 Privilege Categories:")
            categories = self.db.query(Privilege.category).distinct().all()
            for category in categories:
                if category[0]:
                    count = self.db.query(Privilege).filter(Privilege.category == category[0]).count()
                    print(f"  {category[0]}: {count} privileges")
            
        except Exception as e:
            print(f"❌ Error showing status: {str(e)}")
    
    def backup_privileges(self, output_file=None):
        """Create a backup of the privilege system"""
        try:
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"privilege_backup_{timestamp}.json"
            
            print(f"💾 Creating privilege system backup: {output_file}")
            
            # Collect all data
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "roles": [],
                "privileges": [],
                "role_privileges": []
            }
            
            # Backup roles
            roles = self.db.query(Role).all()
            for role in roles:
                backup_data["roles"].append({
                    "name": role.name,
                    "description": role.description,
                    "is_active": role.is_active
                })
            
            # Backup privileges
            privileges = self.db.query(Privilege).all()
            for priv in privileges:
                backup_data["privileges"].append({
                    "name": priv.name,
                    "description": priv.description,
                    "category": priv.category,
                    "is_active": priv.is_active
                })
            
            # Backup role-privilege relationships
            for role in roles:
                for priv in role.privileges:
                    backup_data["role_privileges"].append({
                        "role": role.name,
                        "privilege": priv.name
                    })
            
            # Write to file
            with open(output_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            print(f"✅ Backup created successfully: {output_file}")
            print(f"   📊 {len(backup_data['roles'])} roles")
            print(f"   📊 {len(backup_data['privileges'])} privileges")
            print(f"   📊 {len(backup_data['role_privileges'])} relationships")
            
        except Exception as e:
            print(f"❌ Error creating backup: {str(e)}")
    
    def restore_privileges(self, backup_file):
        """Restore privilege system from backup"""
        try:
            print(f"🔄 Restoring privilege system from: {backup_file}")
            
            # Read backup file
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Clear existing data
            print("🗑️  Clearing existing privilege data...")
            self.db.query(role_privileges).delete()
            self.db.query(user_privileges).delete()
            self.db.query(Privilege).delete()
            self.db.query(Role).delete()
            self.db.commit()
            
            # Restore roles
            print("👥 Restoring roles...")
            for role_data in backup_data["roles"]:
                role = Role(**role_data)
                self.db.add(role)
            self.db.commit()
            
            # Restore privileges
            print("🔐 Restoring privileges...")
            for priv_data in backup_data["privileges"]:
                privilege = Privilege(**priv_data)
                self.db.add(privilege)
            self.db.commit()
            
            # Restore relationships
            print("🔗 Restoring role-privilege relationships...")
            for rel_data in backup_data["role_privileges"]:
                role = self.db.query(Role).filter(Role.name == rel_data["role"]).first()
                privilege = self.db.query(Privilege).filter(Privilege.name == rel_data["privilege"]).first()
                if role and privilege:
                    role.privileges.append(privilege)
            self.db.commit()
            
            print("✅ Privilege system restored successfully!")
            self.show_status()
            
        except Exception as e:
            print(f"❌ Error restoring backup: {str(e)}")
            self.db.rollback()
            raise

def main():
    parser = argparse.ArgumentParser(description='Unified Privilege Management System')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    subparsers.add_parser('init', help='Initialize privilege system')
    
    # Add privilege command
    add_parser = subparsers.add_parser('add', help='Add new privilege')
    add_parser.add_argument('--name', required=True, help='Privilege name')
    add_parser.add_argument('--description', required=True, help='Privilege description')
    add_parser.add_argument('--category', required=True, help='Privilege category')
    add_parser.add_argument('--no-admin', action='store_true', help='Do not assign to admin role')
    
    # Assign privilege command
    assign_parser = subparsers.add_parser('assign', help='Assign privilege to role')
    assign_parser.add_argument('--privilege', required=True, help='Privilege name')
    assign_parser.add_argument('--role', required=True, help='Role name')
    
    # List command
    subparsers.add_parser('list', help='List all privileges')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Backup privilege system')
    backup_parser.add_argument('--output', help='Output file path')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('--backup', required=True, help='Backup file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    with PrivilegeManager() as manager:
        if args.command == 'init':
            manager.init_system()
        elif args.command == 'add':
            manager.add_privilege(
                name=args.name,
                description=args.description,
                category=args.category,
                assign_to_admin=not args.no_admin
            )
        elif args.command == 'assign':
            manager.assign_privilege(args.privilege, args.role)
        elif args.command == 'list':
            manager.list_privileges()
        elif args.command == 'status':
            manager.show_status()
        elif args.command == 'backup':
            manager.backup_privileges(args.output)
        elif args.command == 'restore':
            manager.restore_privileges(args.backup)

if __name__ == "__main__":
    main()
