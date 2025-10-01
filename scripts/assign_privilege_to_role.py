#!/usr/bin/env python3
"""
Script to assign a privilege to a role
Usage: python assign_privilege_to_role.py --privilege "privilege_name" --role "role_name"
"""

import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Privilege, Role

def assign_privilege_to_role(privilege_name, role_name):
    """Assign a privilege to a role"""
    
    # Create engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print(f"🔗 Assigning privilege '{privilege_name}' to role '{role_name}'")
        
        # Find privilege
        privilege = db.query(Privilege).filter(Privilege.name == privilege_name).first()
        if not privilege:
            print(f"  ❌ Privilege '{privilege_name}' not found")
            return
        
        # Find role
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            print(f"  ❌ Role '{role_name}' not found")
            return
        
        # Check if already assigned
        if privilege in role.privileges:
            print(f"  ℹ️  Privilege '{privilege_name}' already assigned to role '{role_name}'")
            return
        
        # Assign privilege to role
        role.privileges.append(privilege)
        db.commit()
        print(f"  ✅ Successfully assigned '{privilege_name}' to role '{role_name}'")
        
        # Show role's privilege count
        priv_count = len(role.privileges)
        print(f"  📊 Role '{role_name}' now has {priv_count} privileges")
        
    except Exception as e:
        print(f"❌ Error assigning privilege: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description='Assign a privilege to a role')
    parser.add_argument('--privilege', required=True, help='Privilege name')
    parser.add_argument('--role', required=True, help='Role name')
    
    args = parser.parse_args()
    
    assign_privilege_to_role(args.privilege, args.role)

if __name__ == "__main__":
    main()
