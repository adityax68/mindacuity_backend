#!/usr/bin/env python3
"""
Test script for the Clinical Mental Health Assessment API
This script demonstrates the clinical assessment functionality of the API
"""

import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_get_questions():
    """Test getting questions for different assessment types"""
    print("📋 Testing get questions...")
    
    assessment_types = ["phq9", "gad7", "pss10"]
    
    for assessment_type in assessment_types:
        print(f"\n--- {assessment_type.upper()} Questions ---")
        
        response = requests.get(f"{API_BASE}/clinical/questions/{assessment_type}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Found {len(result['questions'])} questions")
            print(f"Response options: {result['response_options']}")
            for i, question in enumerate(result['questions'], 1):
                print(f"  {i}. {question}")
        else:
            print(f"❌ Failed to get questions: {response.status_code} - {response.text}")
    
    print()

def test_anonymous_clinical_assessment():
    """Test anonymous clinical assessment"""
    print("🏥 Testing anonymous clinical assessment...")
    
    # Test PHQ-9 assessment
    phq9_responses = [
        {"question_id": 1, "response": 2},  # Moderate depression symptoms
        {"question_id": 2, "response": 1},  # Mild depression symptoms
        {"question_id": 3, "response": 3},  # Severe sleep problems
        {"question_id": 4, "response": 2},  # Moderate fatigue
        {"question_id": 5, "response": 1},  # Mild appetite changes
        {"question_id": 6, "response": 0},  # No self-esteem issues
        {"question_id": 7, "response": 2},  # Moderate concentration problems
        {"question_id": 8, "response": 1},  # Mild psychomotor changes
        {"question_id": 9, "response": 0}   # No suicidal thoughts
    ]
    
    response = requests.post(
        f"{API_BASE}/clinical/assess-anonymous",
        json={
            "assessment_type": "phq9",
            "responses": phq9_responses
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Anonymous PHQ-9 assessment completed")
        print(f"Total Score: {result['total_score']}/{result['max_score']}")
        print(f"Severity Level: {result['severity_level']}")
        print(f"Interpretation: {result['interpretation']}")
    else:
        print(f"❌ Anonymous assessment failed: {response.status_code} - {response.text}")
    
    print()

def test_user_registration():
    """Test user registration"""
    print("👤 Testing user registration...")
    
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    response = requests.post(
        f"{API_BASE}/auth/signup",
        json=user_data
    )
    
    if response.status_code == 201:
        print("✅ User registered successfully")
        return user_data
    else:
        print(f"❌ Registration failed: {response.status_code} - {response.text}")
        return None

def test_user_login(user_data):
    """Test user login"""
    print("🔐 Testing user login...")
    
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    
    response = requests.post(
        f"{API_BASE}/auth/login",
        data=login_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Login successful")
        return result["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def test_authenticated_clinical_assessment(token):
    """Test authenticated clinical assessment"""
    print("🔒 Testing authenticated clinical assessment...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test GAD-7 assessment
    gad7_responses = [
        {"question_id": 1, "response": 2},  # Moderate anxiety
        {"question_id": 2, "response": 1},  # Mild worry control issues
        {"question_id": 3, "response": 3},  # Severe worry about different things
        {"question_id": 4, "response": 2},  # Moderate trouble relaxing
        {"question_id": 5, "response": 1},  # Mild restlessness
        {"question_id": 6, "response": 0},  # No irritability
        {"question_id": 7, "response": 2}   # Moderate fear
    ]
    
    response = requests.post(
        f"{API_BASE}/clinical/assess",
        headers=headers,
        json={
            "assessment_type": "gad7",
            "responses": gad7_responses
        }
    )
    
    if response.status_code == 201:
        result = response.json()
        print("✅ Authenticated GAD-7 assessment completed and saved")
        print(f"Assessment ID: {result['id']}")
        print(f"Total Score: {result['total_score']}/{result['max_score']}")
        print(f"Severity Level: {result['severity_level']}")
        print(f"Interpretation: {result['interpretation']}")
        return result['id']
    else:
        print(f"❌ Authenticated assessment failed: {response.status_code} - {response.text}")
        return None

def test_get_clinical_assessments(token):
    """Test getting user's clinical assessments"""
    print("📊 Testing get clinical assessments...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{API_BASE}/clinical/my-assessments",
        headers=headers
    )
    
    if response.status_code == 200:
        assessments = response.json()
        print(f"✅ Found {len(assessments)} clinical assessments")
        for assessment in assessments:
            print(f"  - ID: {assessment['id']}, Type: {assessment['assessment_type']}, Score: {assessment['total_score']}/{assessment['max_score']}, Severity: {assessment['severity_level']}")
    else:
        print(f"❌ Failed to get assessments: {response.status_code} - {response.text}")

def test_get_clinical_summary(token):
    """Test getting clinical assessment summary"""
    print("📈 Testing get clinical summary...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{API_BASE}/clinical/summary",
        headers=headers
    )
    
    if response.status_code == 200:
        summary = response.json()
        print("✅ Clinical summary retrieved")
        print(f"Total Assessments: {summary['total_assessments']}")
        print(f"Overall Risk Level: {summary['overall_risk_level']}")
        print(f"Recommendations: {summary['recommendations']}")
        if summary['assessments']:
            print("Recent Assessments:")
            for assessment in summary['assessments'][:3]:  # Show last 3
                print(f"  - {assessment['assessment_type']}: {assessment['total_score']}/{assessment['max_score']} ({assessment['severity_level']})")
    else:
        print(f"❌ Failed to get summary: {response.status_code} - {response.text}")

def main():
    """Run all tests"""
    print("🚀 Starting Clinical Mental Health Assessment API Tests")
    print("=" * 60)
    
    # Test health check
    test_health_check()
    
    # Test getting questions
    test_get_questions()
    
    # Test anonymous clinical assessment
    test_anonymous_clinical_assessment()
    
    # Test user registration and login for authenticated assessments
    user_data = test_user_registration()
    if user_data:
        token = test_user_login(user_data)
        if token:
            # Test authenticated clinical assessment
            assessment_id = test_authenticated_clinical_assessment(token)
            
            # Test getting assessments
            test_get_clinical_assessments(token)
            
            # Test getting summary
            test_get_clinical_summary(token)
    
    print("=" * 60)
    print("✅ All clinical assessment tests completed!")

if __name__ == "__main__":
    main() 