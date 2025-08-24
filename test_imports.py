#!/usr/bin/env python3
"""
Test script to check if all imports are working
"""
import sys
import traceback

def test_imports():
    """Test all the imports needed for the authentication system"""
    print("🧪 Testing Imports")
    print("=" * 30)
    
    try:
        print("1. Testing database imports...")
        from app.database import get_db, engine
        print("   ✅ Database imports successful")
    except Exception as e:
        print(f"   ❌ Database import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("2. Testing model imports...")
        from app.models import User, Organization, Employee
        print("   ✅ Model imports successful")
    except Exception as e:
        print(f"   ❌ Model import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("3. Testing schema imports...")
        from app.schemas import UserCreate, User, Token
        print("   ✅ Schema imports successful")
    except Exception as e:
        print(f"   ❌ Schema import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("4. Testing CRUD imports...")
        from app.crud import UserCRUD
        print("   ✅ CRUD imports successful")
    except Exception as e:
        print(f"   ❌ CRUD import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("5. Testing auth imports...")
        from app.auth import get_password_hash, verify_password
        print("   ✅ Auth imports successful")
    except Exception as e:
        print(f"   ❌ Auth import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("6. Testing role service imports...")
        from app.services.role_service import RoleService
        print("   ✅ Role service imports successful")
    except Exception as e:
        print(f"   ❌ Role service import failed: {e}")
        traceback.print_exc()
        return False
    
    print("\n✅ All imports successful!")
    return True

if __name__ == "__main__":
    test_imports()
