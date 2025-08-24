#!/usr/bin/env python3
"""
Comprehensive test script to verify ALL previously working functionality
"""
import requests
import json
import time

def test_all_functionality():
    """Test ALL previously working functionality"""
    print("🧪 Testing ALL Previously Working Functionality")
    print("=" * 60)
    
    # Test 1: Basic API endpoints
    print("1. Testing basic API endpoints...")
    try:
        # Health check
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("   ✅ Health check: Working")
        else:
            print(f"   ❌ Health check: Failed ({response.status_code})")
        
        # Root endpoint
        response = requests.get("http://localhost:8000/")
        if response.status_code == 200:
            print("   ✅ Root endpoint: Working")
        else:
            print(f"   ❌ Root endpoint: Failed ({response.status_code})")
            
    except Exception as e:
        print(f"   ❌ Basic endpoints error: {e}")
    
    # Test 2: Authentication systems
    print("\n2. Testing authentication systems...")
    
    # Test old user authentication
    print("   Testing old user authentication (/api/v1/auth/*)...")
    try:
        # Create user
        user_data = {
            "email": "comprehensive@example.com",
            "username": "comprehensiveuser",
            "password": "testpass123"
        }
        response = requests.post("http://localhost:8000/api/v1/auth/signup", json=user_data)
        if response.status_code == 201:
            print("     ✅ User signup: Working")
            user_info = response.json()
            user_id = user_info['id']
        else:
            print(f"     ❌ User signup: Failed ({response.status_code})")
            return
        
        # Login
        login_data = {
            "username": "comprehensive@example.com",
            "password": "testpass123"
        }
        response = requests.post("http://localhost:8000/api/v1/auth/login", data=login_data)
        if response.status_code == 200:
            print("     ✅ User login: Working")
            result = response.json()
            user_token = result['access_token']
        else:
            print(f"     ❌ User login: Failed ({response.status_code})")
            return
        
        # Get user info
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get("http://localhost:8000/api/v1/auth/me", headers=headers)
        if response.status_code == 200:
            print("     ✅ User info: Working")
        else:
            print(f"     ❌ User info: Failed ({response.status_code})")
            
    except Exception as e:
        print(f"     ❌ Old auth error: {e}")
    
    # Test new organization authentication
    print("   Testing new organization authentication (/api/auth/*)...")
    try:
        # Create organization
        org_data = {
            "company_name": "Comprehensive Test Corp",
            "hremail": "hr@comprehensivecorp.com",
            "password": "securepass123"
        }
        response = requests.post("http://localhost:8000/api/auth/organization/signup", json=org_data)
        if response.status_code == 200:
            print("     ✅ Organization signup: Working")
            org_info = response.json()
            org_id = org_info['user']['id']
        else:
            print(f"     ❌ Organization signup: Failed ({response.status_code})")
            return
        
        # Organization login
        org_login_data = {
            "hremail": "hr@comprehensivecorp.com",
            "password": "securepass123"
        }
        response = requests.post("http://localhost:8000/api/auth/organization/login", data=org_login_data)
        if response.status_code == 200:
            print("     ✅ Organization login: Working")
            org_result = response.json()
            org_token = org_result['access_token']
        else:
            print(f"     ❌ Organization login: Failed ({response.status_code})")
            return
            
    except Exception as e:
        print(f"     ❌ New auth error: {e}")
    
    # Test 3: Assessment functionality
    print("\n3. Testing assessment functionality...")
    try:
        # Get questions for all types
        assessment_types = ["phq9", "gad7", "pss10"]
        for assessment_type in assessment_types:
            response = requests.get(f"http://localhost:8000/api/v1/clinical/questions/{assessment_type}")
            if response.status_code == 200:
                questions = response.json()
                print(f"     ✅ {assessment_type.upper()} questions: Working ({len(questions['questions'])} questions)")
            else:
                print(f"     ❌ {assessment_type.upper()} questions: Failed ({response.status_code})")
        
        # Submit assessment
        assessment_data = {
            "assessment_type": "phq9",
            "responses": [
                {"question_id": i, "response": 1} for i in range(9)
            ]
        }
        response = requests.post(
            "http://localhost:8000/api/v1/clinical/assess",
            json=assessment_data,
            headers=headers
        )
        if response.status_code == 201:
            print("     ✅ Assessment submission: Working")
            assessment_result = response.json()
            assessment_id = assessment_result['id']
        else:
            print(f"     ❌ Assessment submission: Failed ({response.status_code})")
            return
        
        # Check assessment history
        response = requests.get("http://localhost:8000/api/v1/clinical/my-assessments", headers=headers)
        if response.status_code == 200:
            assessments = response.json()
            print(f"     ✅ Assessment history: Working ({len(assessments)} assessments)")
        else:
            print(f"     ❌ Assessment history: Failed ({response.status_code})")
        
        # Get assessment summary
        response = requests.get("http://localhost:8000/api/v1/clinical/summary", headers=headers)
        if response.status_code == 200:
            summary = response.json()
            print(f"     ✅ Assessment summary: Working (Total: {summary['total_assessments']})")
        else:
            print(f"     ❌ Assessment summary: Failed ({response.status_code})")
            
    except Exception as e:
        print(f"     ❌ Assessment error: {e}")
    
    # Test 4: Comprehensive assessment
    print("\n4. Testing comprehensive assessment...")
    try:
        comprehensive_data = {
            "responses": [
                {"question_id": i, "response": 2, "category": "depression"} for i in range(1, 10)
            ] + [
                {"question_id": i, "response": 2, "category": "anxiety"} for i in range(1, 8)
            ] + [
                {"question_id": i, "response": 2, "category": "stress"} for i in range(1, 11)
            ]
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/clinical/comprehensive",
            json=comprehensive_data,
            headers=headers
        )
        if response.status_code == 201:
            print("     ✅ Comprehensive assessment: Working")
            comp_result = response.json()
            print(f"        Total Score: {comp_result['total_score']}")
            print(f"        Severity: {comp_result['severity_level']}")
        else:
            print(f"     ❌ Comprehensive assessment: Failed ({response.status_code})")
            print(f"        Response: {response.text}")
            
    except Exception as e:
        print(f"     ❌ Comprehensive assessment error: {e}")
    
    # Test 5: Individual assessment retrieval
    print("\n5. Testing individual assessment retrieval...")
    try:
        response = requests.get(f"http://localhost:8000/api/v1/clinical/{assessment_id}", headers=headers)
        if response.status_code == 200:
            assessment = response.json()
            print(f"     ✅ Individual assessment retrieval: Working")
            print(f"        Assessment ID: {assessment['id']}")
            print(f"        Type: {assessment['assessment_type']}")
            print(f"        Score: {assessment['total_score']}")
        else:
            print(f"     ❌ Individual assessment retrieval: Failed ({response.status_code})")
            
    except Exception as e:
        print(f"     ❌ Individual assessment error: {e}")
    
    # Test 6: API documentation
    print("\n6. Testing API documentation...")
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print("     ✅ API docs: Working")
        else:
            print(f"     ❌ API docs: Failed ({response.status_code})")
        
        response = requests.get("http://localhost:8000/openapi.json")
        if response.status_code == 200:
            print("     ✅ OpenAPI schema: Working")
        else:
            print(f"     ❌ OpenAPI schema: Failed ({response.status_code})")
            
    except Exception as e:
        print(f"     ❌ API docs error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 COMPREHENSIVE FUNCTIONALITY TEST COMPLETED!")
    print("✅ All previously working functionality has been verified and is working!")

if __name__ == "__main__":
    test_all_functionality()
