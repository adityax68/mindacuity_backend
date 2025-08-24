#!/usr/bin/env python3
"""
Debug script for API endpoint
"""
import requests
import json

def test_api_debug():
    """Debug the API endpoint"""
    print("🐛 Debugging API Endpoint")
    print("=" * 30)
    
    # Test 1: Check if endpoint exists
    print("1. Checking if endpoint exists...")
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("   ✅ API docs accessible")
        else:
            print(f"   ❌ API docs error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API docs error: {e}")
    
    # Test 2: Try to get the OpenAPI schema
    print("\n2. Checking OpenAPI schema...")
    try:
        response = requests.get("http://localhost:8000/openapi.json")
        if response.status_code == 200:
            schema = response.json()
            paths = schema.get('paths', {})
            auth_paths = [path for path in paths.keys() if 'auth' in path]
            print(f"   ✅ Found {len(auth_paths)} auth paths:")
            for path in auth_paths:
                print(f"      - {path}")
        else:
            print(f"   ❌ OpenAPI schema error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ OpenAPI schema error: {e}")
    
    # Test 3: Try a simple GET request to the auth endpoint
    print("\n3. Testing auth endpoint GET...")
    try:
        response = requests.get("http://localhost:8000/api/v1/auth/signup")
        print(f"   GET response: {response.status_code}")
        print(f"   GET body: {response.text}")
    except Exception as e:
        print(f"   ❌ GET request error: {e}")
    
    # Test 4: Try POST with minimal data and check response headers
    print("\n4. Testing POST with detailed error info...")
    user_data = {
        "email": "debug@example.com",
        "username": "debuguser",
        "password": "debugpass123"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/v1/auth/signup", json=user_data)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code != 201:
            print(f"   ❌ Expected 201, got {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error during POST: {e}")

if __name__ == "__main__":
    test_api_debug()
