#!/usr/bin/env python3
"""
Test script for the organisation API endpoint.
"""

import requests
import json

def test_organisation_api():
    """Test the organisation API endpoint."""
    
    base_url = "http://localhost:8000/api/v1"
    
    # First, let's try to get a token (you'll need to replace with actual admin credentials)
    print("Testing Organisation API...")
    print("=" * 50)
    
    # Test the endpoint without authentication (should return 401)
    print("1. Testing without authentication...")
    response = requests.post(f"{base_url}/admin/organisations", 
                           json={"org_name": "Test Org", "hr_email": "test@example.com"})
    print(f"   Status: {response.status_code}")
    if response.status_code == 401:
        print("   ✅ Correctly requires authentication")
    else:
        print(f"   ❌ Unexpected response: {response.text}")
    
    print("\n2. Testing GET endpoint without authentication...")
    response = requests.get(f"{base_url}/admin/organisations")
    print(f"   Status: {response.status_code}")
    if response.status_code == 401:
        print("   ✅ Correctly requires authentication")
    else:
        print(f"   ❌ Unexpected response: {response.text}")
    
    print("\n" + "=" * 50)
    print("✅ API endpoint tests completed!")
    print("\nNote: To test with authentication, you need to:")
    print("1. Login as an admin user")
    print("2. Get the JWT token")
    print("3. Include the token in the Authorization header")

if __name__ == "__main__":
    test_organisation_api() 