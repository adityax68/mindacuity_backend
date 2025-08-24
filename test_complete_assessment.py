#!/usr/bin/env python3
"""
Comprehensive test script for the complete assessment flow
"""
import requests
import json

def test_complete_assessment_flow():
    """Test the complete assessment flow"""
    print("🧪 Testing Complete Assessment Flow")
    print("=" * 50)
    
    # Step 1: Create a user account
    print("1. Creating a test user account...")
    user_data = {
        "email": "assessmenttest@example.com",
        "username": "assessmentuser",
        "password": "testpass123"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/v1/auth/signup", json=user_data)
        if response.status_code == 201:
            print("   ✅ User created successfully")
            user_info = response.json()
            print(f"   User ID: {user_info['id']}")
        else:
            print(f"   ❌ User creation failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error creating user: {e}")
        return
    
    # Step 2: Login to get access token
    print("\n2. Logging in to get access token...")
    login_data = {
        "username": "assessmenttest@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/v1/auth/login", data=login_data)
        if response.status_code == 200:
            result = response.json()
            print("   ✅ Login successful")
            access_token = result['access_token']
            print(f"   Token: {access_token[:50]}...")
        else:
            print(f"   ❌ Login failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error during login: {e}")
        return
    
    # Step 3: Submit a PHQ-9 assessment
    print("\n3. Submitting a PHQ-9 assessment...")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create assessment data (all responses set to 1 for testing)
    assessment_data = {
        "assessment_type": "phq9",
        "responses": [
            {"question_id": i, "response": 1} for i in range(9)
        ]
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/clinical/assess",
            json=assessment_data,
            headers=headers
        )
        if response.status_code == 201:
            assessment_result = response.json()
            print("   ✅ Assessment submitted successfully")
            print(f"   Assessment ID: {assessment_result['id']}")
            print(f"   Total Score: {assessment_result['total_score']}")
            print(f"   Severity: {assessment_result['severity_level']}")
        else:
            print(f"   ❌ Assessment submission failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error submitting assessment: {e}")
        return
    
    # Step 4: Check assessment history
    print("\n4. Checking assessment history...")
    try:
        response = requests.get(
            "http://localhost:8000/api/v1/clinical/my-assessments",
            headers=headers
        )
        if response.status_code == 200:
            assessments = response.json()
            print(f"   ✅ Assessment history retrieved successfully")
            print(f"   Found {len(assessments)} assessments")
            for assessment in assessments:
                print(f"      - ID: {assessment['id']}, Type: {assessment['assessment_type']}, Score: {assessment['total_score']}")
        else:
            print(f"   ❌ Failed to get assessment history: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error getting assessment history: {e}")
        return
    
    # Step 5: Get assessment summary
    print("\n5. Getting assessment summary...")
    try:
        response = requests.get(
            "http://localhost:8000/api/v1/clinical/summary",
            headers=headers
        )
        if response.status_code == 200:
            summary = response.json()
            print(f"   ✅ Assessment summary retrieved successfully")
            print(f"   Total assessments: {summary['total_assessments']}")
            print(f"   Overall risk level: {summary['overall_risk_level']}")
        else:
            print(f"   ❌ Failed to get assessment summary: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error getting assessment summary: {e}")
        return
    
    print("\n🎉 Complete assessment flow test successful!")
    print("✅ All assessment functionality is working properly!")

if __name__ == "__main__":
    test_complete_assessment_flow()
