#!/usr/bin/env python3
"""
Debug script for login issue
"""
import requests
import json

def test_login_debug():
    """Debug the login issue"""
    print("🔐 Debugging Login Issue")
    print("=" * 30)
    
    print("1. Testing login with existing user...")
    login_data = {
        "username": "logintest@example.com",  # OAuth2 form uses 'username' field
        "password": "testpass123"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/v1/auth/login", data=login_data)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Login successful!")
            result = response.json()
            print(f"   Token: {result.get('access_token', 'N/A')[:50]}...")
            print(f"   User: {result.get('user', 'N/A')}")
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error during login: {e}")

if __name__ == "__main__":
    test_login_debug()
