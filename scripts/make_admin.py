#!/usr/bin/env python3
"""
Script to make an existing user an admin
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import User

def make_user_admin(email: str):
    """Make a user an admin by email"""
    
    # Create engine using settings from config
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print(f"🔍 Looking for user with email: {email}")
        
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ User with email {email} not found")
            return
        
        print(f"✅ Found user: {user.full_name} ({user.username})")
        print(f"   Current role: {user.role}")
        
        # Update role to admin
        user.role = "admin"
        db.commit()
        
        print(f"🎉 Successfully made {user.full_name} an admin!")
        print(f"   New role: {user.role}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py <email>")
        print("Example: python make_admin.py admin@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    make_user_admin(email) 