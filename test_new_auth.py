#!/usr/bin/env python3
"""
Test script for the new Organization/Employee authentication system
"""
import asyncio
import requests
import json
from datetime import datetime

# Base URL for the API
BASE_URL = "http://localhost:8000"

def test_organization_signup():
    """Test organization signup"""
    print("🧪 Testing Organization Signup...")
    
    url = f"{BASE_URL}/api/auth/organization/signup"
    data = {
        "company_name": "New Test Corp",
        "hremail": "hr@newtestcorp.com",
        "password": "securepass123"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Organization signup successful!")
            print(f"Company ID: {result['user']['id']}")
            print(f"Access Token: {result['access_token'][:50]}...")
            return result
        else:
            print(f"❌ Organization signup failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error during organization signup: {e}")
        return None

def test_organization_login():
    """Test organization login"""
    print("\n🧪 Testing Organization Login...")
    
    url = f"{BASE_URL}/api/auth/organization/login"
    data = {
        "hremail": "hr@newtestcorp.com",
        "password": "securepass123"
    }
    
    try:
        response = requests.post(url, data=data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Organization login successful!")
            print(f"Company ID: {result['user']['id']}")
            print(f"Access Token: {result['access_token'][:50]}...")
            return result
        else:
            print(f"❌ Organization login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error during organization login: {e}")
        return None

def test_employee_signup(company_id):
    """Test employee signup"""
    print(f"\n🧪 Testing Employee Signup for Company {company_id}...")
    
    url = f"{BASE_URL}/api/auth/employee/signup"
    data = {
        "company_id": company_id,
        "employee_email": "jane@newtestcorp.com",
        "password": "securepass123",
        "name": "Jane Doe",
        "dob": "1992-01-01",
        "phone_number": "+1987654321",
        "joining_date": "2024-02-01"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Employee signup successful!")
            print(f"Employee ID: {result['user']['id']}")
            print(f"Access Token: {result['access_token'][:50]}...")
            return result
        else:
            print(f"❌ Employee signup failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error during employee signup: {e}")
        return None

def test_employee_login(company_id):
    """Test employee login"""
    print(f"\n🧪 Testing Employee Login for Company {company_id}...")
    
    url = f"{BASE_URL}/api/auth/employee/login"
    data = {
        "company_id": company_id,
        "employee_email": "jane@newtestcorp.com",
        "password": "securepass123"
    }
    
    try:
        response = requests.post(url, data=data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Employee login successful!")
            print(f"Employee ID: {result['user']['id']}")
            print(f"Access Token: {result['access_token'][:50]}...")
            return result
        else:
            print(f"❌ Employee login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error during employee login: {e}")
        return None

def test_protected_endpoint(token):
    """Test accessing a protected endpoint"""
    print(f"\n🧪 Testing Protected Endpoint...")
    
    url = f"{BASE_URL}/api/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Protected endpoint access successful!")
            print(f"User Info: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Protected endpoint access failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing protected endpoint: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing New Organization/Employee Authentication System")
    print("=" * 60)
    
    # Test organization signup
    org_result = test_organization_signup()
    if not org_result:
        print("❌ Cannot continue without successful organization signup")
        return
    
    company_id = org_result['user']['id']
    
    # Test organization login
    org_login_result = test_organization_login()
    if not org_login_result:
        print("❌ Organization login failed")
        return
    
    # Test protected endpoint with organization token
    test_protected_endpoint(org_login_result['access_token'])
    
    # Test employee signup
    emp_result = test_employee_signup(company_id)
    if not emp_result:
        print("❌ Employee signup failed")
        return
    
    # Test employee login
    emp_login_result = test_employee_login(company_id)
    if not emp_login_result:
        print("❌ Employee login failed")
        return
    
    # Test protected endpoint with employee token
    test_protected_endpoint(emp_login_result['access_token'])
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed!")
    print("✅ Organization/Employee authentication system is working!")

if __name__ == "__main__":
    main()
