#!/usr/bin/env python3
"""
Test script to verify the role system works correctly
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

def test_role_system():
    """Test the role system functionality"""
    
    print("🧪 Testing Role System...")
    print("=" * 50)
    
    # Test 1: Create a test user
    print("\n1. Creating test user...")
    signup_data = {
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}{API_PREFIX}/auth/signup", json=signup_data)
        if response.status_code == 201:
            print("✅ Test user created successfully")
            user_data = response.json()
            print(f"   User ID: {user_data['id']}")
            print(f"   Role: {user_data.get('role', 'Not set')}")
        else:
            print(f"❌ Failed to create test user: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        return
    
    # Test 2: Login with test user
    print("\n2. Logging in with test user...")
    login_data = {
        "username": "testuser@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}{API_PREFIX}/auth/login", data=login_data)
        if response.status_code == 200:
            print("✅ Login successful")
            login_response = response.json()
            token = login_response['access_token']
            user = login_response['user']
            print(f"   Token: {token[:20]}...")
            print(f"   User role: {user.get('role', 'Not set')}")
            print(f"   Privileges: {user.get('privileges', [])}")
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return
    
    # Test 3: Try to access admin endpoint (should fail)
    print("\n3. Testing admin access (should fail)...")
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 403:
            print("✅ Admin access correctly denied for regular user")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing admin access: {e}")
    
    # Test 4: Get user info
    print("\n4. Getting user info...")
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            print("✅ User info retrieved successfully")
            user_info = response.json()
            print(f"   Role: {user_info.get('role', 'Not set')}")
            print(f"   Privileges: {user_info.get('privileges', [])}")
        else:
            print(f"❌ Failed to get user info: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error getting user info: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Role System Test Complete!")
    print("\nNext steps:")
    print("1. Run: python scripts/migrate_to_roles.py")
    print("2. Run: python scripts/make_admin.py testuser@example.com")
    print("3. Test admin functionality")

if __name__ == "__main__":
    test_role_system() 