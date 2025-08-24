#!/usr/bin/env python3
"""
Simple test script to debug user creation
"""
import asyncio
import requests
import json

async def test_user_creation():
    """Test user creation step by step"""
    print("🧪 Testing User Creation Step by Step")
    print("=" * 50)
    
    # Test 1: Check if server is running
    print("1. Checking server status...")
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"   ✅ Server status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Server error: {e}")
        return
    
    # Test 2: Check if user auth endpoint exists
    print("\n2. Checking user auth endpoint...")
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("   ✅ API docs accessible")
        else:
            print(f"   ❌ API docs error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API docs error: {e}")
    
    # Test 3: Try to create a user with minimal data
    print("\n3. Testing user creation with minimal data...")
    user_data = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "testpass123"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/v1/auth/signup", json=user_data)
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 201:
            print("   ✅ User creation successful!")
        else:
            print(f"   ❌ User creation failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error during user creation: {e}")

if __name__ == "__main__":
    asyncio.run(test_user_creation())
