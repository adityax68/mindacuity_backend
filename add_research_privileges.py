#!/usr/bin/env python3
"""
Script to add research management privileges to the system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base, User, Role, Privilege, user_privileges, role_privileges

def add_research_privileges():
    """Add research management privileges to the system"""
    
    # Create engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🔧 Adding research management privileges...")
        
        # Create research privileges
        print("📋 Creating research privileges...")
        research_privileges = [
            {"name": "read_researches", "description": "Read research articles", "category": "research"},
            {"name": "manage_researches", "description": "Manage research articles (create, update, delete)", "category": "research"},
        ]
        
        # Create privileges if they don't exist
        for priv_data in research_privileges:
            existing_priv = db.query(Privilege).filter(Privilege.name == priv_data["name"]).first()
            if not existing_priv:
                privilege = Privilege(**priv_data)
                db.add(privilege)
                print(f"  ✅ Created privilege: {priv_data['name']}")
            else:
                print(f"  ℹ️  Privilege already exists: {priv_data['name']}")
        
        db.commit()
        print(f"  📊 Total privileges: {db.query(Privilege).count()}")
        
        # Assign research privileges to admin role
        print("\n🔗 Assigning research privileges to admin role...")
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            # Get the research privileges
            research_privs = db.query(Privilege).filter(
                Privilege.name.in_(["read_researches", "manage_researches"])
            ).all()
            
            # Add them to admin role if not already present
            for privilege in research_privs:
                if privilege not in admin_role.privileges:
                    admin_role.privileges.append(privilege)
                    print(f"  ✅ Added {privilege.name} to admin role")
                else:
                    print(f"  ℹ️  {privilege.name} already assigned to admin role")
            
            db.commit()
            
            # Verify admin privileges
            admin_privileges = [p.name for p in admin_role.privileges]
            print(f"  👑 Admin role now has {len(admin_privileges)} privileges")
            print(f"  📋 Research privileges: {[p for p in admin_privileges if 'research' in p]}")
        else:
            print("  ❌ Admin role not found!")
        
        print("\n✅ Research privileges setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during setup: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_research_privileges()
