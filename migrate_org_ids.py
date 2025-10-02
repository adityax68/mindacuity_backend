#!/usr/bin/env python3
"""
Script to migrate existing organization IDs to 5-character format.
This script should be run after updating the org_id generation logic.
"""

import os
import sys
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import OrganisationCRUD
from app.models import Organisation

def migrate_org_ids():
    """Migrate existing org_ids to 5-character format."""
    db = next(get_db())
    
    try:
        # Get all existing organizations
        organizations = db.query(Organisation).all()
        
        print(f"Found {len(organizations)} organizations to migrate...")
        
        for org in organizations:
            # Skip if already 5 characters
            if len(org.org_id) == 5:
                print(f"✓ {org.org_name} ({org.org_id}) - already 5 characters")
                continue
            
            # Generate new 5-character org_id
            new_org_id = OrganisationCRUD.generate_org_id(db)
            
            print(f"🔄 Migrating {org.org_name}: {org.org_id} -> {new_org_id}")
            
            # Update the org_id
            old_org_id = org.org_id
            org.org_id = new_org_id
            
            # Commit the change
            db.commit()
            print(f"✅ Successfully migrated {org.org_name}")
        
        print("\n🎉 Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting organization ID migration...")
    migrate_org_ids()
