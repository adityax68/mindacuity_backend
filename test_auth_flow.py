#!/usr/bin/env python3
"""
Test script to verify the authentication flow works correctly
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_auth_flow():
    """Test the complete authentication flow"""
    print("🔐 Testing Authentication Flow")
    print("=" * 40)
    
    # Test user registration
    print("1. Testing user registration...")
    user_data = {
        "email": "authflow2@example.com",
        "username": "authflowuser2",
        "password": "testpassword123",
        "full_name": "Auth Flow User 2"
    }
    
    response = requests.post(f"{API_BASE}/auth/signup", json=user_data)
    if response.status_code == 201:
        print("✅ Registration successful")
        user = response.json()
        print(f"   User ID: {user['id']}")
        print(f"   Email: {user['email']}")
    else:
        print(f"❌ Registration failed: {response.status_code} - {response.text}")
        return
    
    print()
    
    # Test user login
    print("2. Testing user login...")
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    
    response = requests.post(f"{API_BASE}/auth/login", data=login_data)
    if response.status_code == 200:
        result = response.json()
        print("✅ Login successful")
        print(f"   Token: {result['access_token'][:20]}...")
        print(f"   Token Type: {result['token_type']}")
        print(f"   User ID: {result['user']['id']}")
        print(f"   User Email: {result['user']['email']}")
        
        token = result['access_token']
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return
    
    print()
    
    # Test token validation
    print("3. Testing token validation...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{API_BASE}/auth/me", headers=headers)
    if response.status_code == 200:
        user_info = response.json()
        print("✅ Token validation successful")
        print(f"   User ID: {user_info['id']}")
        print(f"   Email: {user_info['email']}")
        print(f"   Full Name: {user_info['full_name']}")
    else:
        print(f"❌ Token validation failed: {response.status_code} - {response.text}")
    
    print()
    print("=" * 40)
    print("✅ Authentication flow test completed!")

if __name__ == "__main__":
    test_auth_flow() 