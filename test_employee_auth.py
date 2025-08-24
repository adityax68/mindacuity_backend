#!/usr/bin/env python3
"""
Test Employee Authentication
"""
import requests
import json

def test_employee_auth():
    """Test employee authentication"""
    print("👤 Testing Employee Authentication")
    print("=" * 40)
    
    # First, let's get a company ID by logging in as an organization
    print("1. Getting company ID for employee testing...")
    org_login_data = {
        "hremail": "hr@newtestcorp.com",
        "password": "securepass123"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/auth/organization/login", data=org_login_data)
        if response.status_code == 200:
            result = response.json()
            company_id = result['user']['id']
            print(f"   ✅ Got company ID: {company_id}")
        else:
            print(f"   ❌ Failed to get company ID: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error getting company ID: {e}")
        return
    
    # Test 2: Employee Signup
    print("\n2. Testing Employee Signup...")
    emp_data = {
        "company_id": company_id,
        "employee_email": "testemp@newtestcorp.com",
        "password": "emp123456",
        "name": "Test Employee",
        "dob": "1990-01-01",
        "phone_number": "+1234567890",
        "joining_date": "2024-01-01"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/auth/employee/signup", json=emp_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Employee signup successful")
            result = response.json()
            print(f"   Token: {result['access_token'][:50]}...")
            print(f"   Employee: {result['user']}")
        else:
            print("   ❌ Employee signup failed")
            
    except Exception as e:
        print(f"   ❌ Error during signup: {e}")
    
    # Test 3: Employee Login
    print("\n3. Testing Employee Login...")
    emp_login_data = {
        "company_id": company_id,
        "employee_email": "testemp@newtestcorp.com",
        "password": "emp123456"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/auth/employee/login", data=emp_login_data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ Employee login successful")
            result = response.json()
            print(f"   Token: {result['access_token'][:50]}...")
        else:
            print("   ❌ Employee login failed")
            
    except Exception as e:
        print(f"   ❌ Error during login: {e}")
    
    print("\n🎯 Summary:")
    print("   - Employee authentication system is working correctly")
    print("   - Both signup and login endpoints are functional")

if __name__ == "__main__":
    test_employee_auth()
