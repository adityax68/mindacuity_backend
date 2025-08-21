#!/usr/bin/env python3
"""
Test script to verify admin access works correctly
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

def test_admin_access():
    """Test admin access functionality"""
    
    print("🧪 Testing Admin Access...")
    print("=" * 50)
    
    # Test 1: Try to access admin endpoint without auth (should fail)
    print("\n1. Testing admin access without authentication (should fail)...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/admin/users")
        if response.status_code == 403:
            print("✅ Admin access correctly denied for unauthenticated requests")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing admin access: {e}")
    
    # Test 2: Check if admin endpoint is accessible
    print("\n2. Checking admin endpoint availability...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/admin/users")
        print(f"   Status: {response.status_code}")
        if response.status_code == 403:
            print("   ✅ Endpoint is accessible but requires authentication")
        else:
            print(f"   Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Admin Access Test Complete!")
    print("\nNext steps:")
    print("1. Login to your frontend with aditya@gmail.com")
    print("2. Click on Admin Panel tab")
    print("3. You should now have access to admin features")

if __name__ == "__main__":
    test_admin_access() 