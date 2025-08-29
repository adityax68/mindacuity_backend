#!/usr/bin/env python3
"""
Test script for access request functionality.
This script helps verify that the organisation table has data and the access request system works.
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_access_request():
    """Test the access request functionality."""
    
    # Test data
    test_user = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    print("=== Testing Access Request System ===\n")
    
    # 1. Create a test user
    print("1. Creating test user...")
    try:
        response = requests.post(f"{API_BASE}/auth/signup", json=test_user)
        if response.status_code == 201:
            print("✅ User created successfully")
        elif response.status_code == 400 and "already registered" in response.json().get("detail", ""):
            print("ℹ️  User already exists, continuing...")
        else:
            print(f"❌ Failed to create user: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return
    
    # 2. Login to get token
    print("\n2. Logging in...")
    try:
        login_data = {
            "username": test_user["email"],
            "password": test_user["password"]
        }
        response = requests.post(f"{API_BASE}/auth/login", data=login_data)
        if response.status_code == 200:
            token = response.json()["access_token"]
            print("✅ Login successful")
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"❌ Error logging in: {e}")
        return
    
    # 3. Test HR access request (should fail if email not in organisation table)
    print("\n3. Testing HR access request...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{API_BASE}/access/request?access_type=hr", headers=headers)
        if response.status_code == 403:
            print("✅ HR access correctly denied (email not in organisation table)")
        elif response.status_code == 200:
            print("✅ HR access granted (email found in organisation table)")
        else:
            print(f"❌ Unexpected response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error testing HR access: {e}")
    
    # 4. Test Employee access request (should succeed)
    print("\n4. Testing Employee access request...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{API_BASE}/access/request?access_type=employee", headers=headers)
        if response.status_code == 200:
            print("✅ Employee access granted successfully")
            result = response.json()
            print(f"   New role: {result.get('new_role')}")
        else:
            print(f"❌ Employee access failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error testing employee access: {e}")
    
    # 5. Test Counsellor access request (should succeed)
    print("\n5. Testing Counsellor access request...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{API_BASE}/access/request?access_type=counsellor", headers=headers)
        if response.status_code == 200:
            print("✅ Counsellor access granted successfully")
            result = response.json()
            print(f"   New role: {result.get('new_role')}")
        else:
            print(f"❌ Counsellor access failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error testing counsellor access: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_access_request() 