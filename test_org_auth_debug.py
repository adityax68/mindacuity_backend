#!/usr/bin/env python3
"""
Debug script for Organization Authentication
"""
import requests
import json

def test_organization_auth():
    """Test organization authentication to identify issues"""
    print("🏢 Testing Organization Authentication")
    print("=" * 50)
    
    # Test 1: Organization Signup
    print("1. Testing Organization Signup...")
    org_data = {
        "company_name": "Test Company Debug",
        "hremail": "debug@testcompany.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/auth/organization/signup", json=org_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Organization signup successful")
            result = response.json()
            print(f"   Token: {result['access_token'][:50]}...")
            print(f"   User: {result['user']}")
        else:
            print("   ❌ Organization signup failed")
            
    except Exception as e:
        print(f"   ❌ Error during signup: {e}")
    
    print("\n2. Testing Organization Login...")
    login_data = {
        "hremail": "debug@testcompany.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/auth/organization/login", data=login_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Organization login successful")
            result = response.json()
            print(f"   Token: {result['access_token'][:50]}...")
        else:
            print("   ❌ Organization login failed")
            
    except Exception as e:
        print(f"   ❌ Error during login: {e}")
    
    print("\n3. Testing with existing organization...")
    existing_login_data = {
        "hremail": "hr@gmail.com",
        "password": "password123"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/auth/organization/login", data=existing_login_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Existing organization login successful")
        else:
            print("   ❌ Existing organization login failed")
            
    except Exception as e:
        print(f"   ❌ Error during existing login: {e}")
    
    print("\n4. Testing GET request to login endpoint (should fail)...")
    try:
        response = requests.get("http://localhost:8000/api/auth/organization/login")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 405:
            print("   ✅ Correctly rejected GET request")
        else:
            print("   ❌ Unexpected response to GET request")
            
    except Exception as e:
        print(f"   ❌ Error during GET test: {e}")
    
    print("\n🔍 Debug Information:")
    print("   - Organization signup endpoint: POST /api/auth/organization/signup")
    print("   - Organization login endpoint: POST /api/auth/organization/login")
    print("   - Expected format: form-encoded data")
    print("   - Required fields: hremail, password")

if __name__ == "__main__":
    test_organization_auth()
