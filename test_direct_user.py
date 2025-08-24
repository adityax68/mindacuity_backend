#!/usr/bin/env python3
"""
Direct test of user creation without API
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_direct_user_creation():
    """Test user creation directly"""
    print("🧪 Testing Direct User Creation")
    print("=" * 40)
    
    try:
        print("1. Importing required modules...")
        from app.database import get_db
        from app.models import User
        from app.schemas import UserCreate
        from app.crud import UserCRUD
        from app.auth import get_password_hash
        print("   ✅ All modules imported successfully")
        
        print("\n2. Testing database connection...")
        async for db in get_db():
            print("   ✅ Database connection successful")
            
            print("\n3. Testing user creation...")
            user_data = UserCreate(
                email="directtest@example.com",
                username="directtestuser",
                password="testpass123"
            )
            
            print(f"   📝 User data: {user_data}")
            
            # Try to create user
            new_user = await UserCRUD.create_user(db=db, user=user_data)
            print(f"   ✅ User created successfully with ID: {new_user.id}")
            
            # Check if user was actually saved
            result = await db.execute(f"SELECT id, email, username FROM users WHERE id = {new_user.id}")
            saved_user = result.fetchone()
            if saved_user:
                print(f"   ✅ User saved to database: {saved_user}")
            else:
                print("   ❌ User not found in database")
            
            break
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_direct_user_creation())
