#!/usr/bin/env python3
"""
Script to restore the privilege system from backup
Usage: python restore_privileges.py --backup_file backup_file.json
"""

import sys
import os
import argparse
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import User, Role, Privilege

def restore_privileges(backup_file):
    """Restore the privilege system from backup file"""
    
    # Create engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print(f"🔄 Restoring privilege system from: {backup_file}")
        
        # Load backup data
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        print(f"  📅 Backup timestamp: {backup_data.get('timestamp', 'Unknown')}")
        
        # Clear existing data (be careful!)
        print("  🗑️  Clearing existing privilege data...")
        db.query(User).update({"role": "user"})  # Reset all users to user role
        db.commit()
        
        # Restore privileges
        print("  📋 Restoring privileges...")
        for priv_data in backup_data["privileges"]:
            existing_priv = db.query(Privilege).filter(Privilege.name == priv_data["name"]).first()
            if not existing_priv:
                privilege = Privilege(
                    name=priv_data["name"],
                    description=priv_data["description"],
                    category=priv_data["category"],
                    is_active=priv_data["is_active"]
                )
                db.add(privilege)
                print(f"    ✅ Restored privilege: {priv_data['name']}")
            else:
                print(f"    ℹ️  Privilege already exists: {priv_data['name']}")
        
        db.commit()
        
        # Restore roles
        print("  👥 Restoring roles...")
        for role_data in backup_data["roles"]:
            existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing_role:
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"],
                    is_active=role_data["is_active"]
                )
                db.add(role)
                print(f"    ✅ Restored role: {role_data['name']}")
            else:
                print(f"    ℹ️  Role already exists: {role_data['name']}")
        
        db.commit()
        
        # Restore role-privilege relationships
        print("  🔗 Restoring role-privilege relationships...")
        for rp_data in backup_data["role_privileges"]:
            role = db.query(Role).filter(Role.name == rp_data["role_name"]).first()
            privilege = db.query(Privilege).filter(Privilege.name == rp_data["privilege_name"]).first()
            
            if role and privilege:
                if privilege not in role.privileges:
                    role.privileges.append(privilege)
                    print(f"    ✅ Assigned {rp_data['privilege_name']} to {rp_data['role_name']}")
                else:
                    print(f"    ℹ️  {rp_data['privilege_name']} already assigned to {rp_data['role_name']}")
        
        db.commit()
        
        # Restore user roles
        print("  👤 Restoring user roles...")
        for user_data in backup_data["users"]:
            user = db.query(User).filter(User.email == user_data["email"]).first()
            if user and user_data["role"]:
                user.role = user_data["role"]
                print(f"    ✅ Restored role for user: {user_data['email']} -> {user_data['role']}")
        
        db.commit()
        
        # Verify restoration
        print("\n🔍 Verifying restoration...")
        total_privileges = db.query(Privilege).count()
        total_roles = db.query(Role).count()
        total_users = db.query(User).count()
        
        print(f"  📊 Total privileges: {total_privileges}")
        print(f"  📊 Total roles: {total_roles}")
        print(f"  📊 Total users: {total_users}")
        
        # Show role privilege counts
        print("\n📋 Role Privilege Summary:")
        roles = db.query(Role).all()
        for role in roles:
            priv_count = len(role.privileges)
            print(f"  {role.name}: {priv_count} privileges")
        
        print(f"\n✅ Privilege system restoration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error restoring backup: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description='Restore the privilege system from backup')
    parser.add_argument('--backup_file', required=True, help='Backup file to restore from')
    
    args = parser.parse_args()
    
    restore_privileges(args.backup_file)

if __name__ == "__main__":
    main()
