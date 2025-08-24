#!/usr/bin/env python3
"""
Test script to verify assessment functionality
"""
import requests
import json

def test_assessment_functionality():
    """Test the assessment functionality"""
    print("🧪 Testing Assessment Functionality")
    print("=" * 40)
    
    # Test 1: Get questions for PHQ-9
    print("1. Testing PHQ-9 questions endpoint...")
    try:
        response = requests.get("http://localhost:8000/api/v1/clinical/questions/phq9")
        if response.status_code == 200:
            questions = response.json()
            print(f"   ✅ PHQ-9 questions retrieved successfully")
            print(f"   Questions count: {len(questions['questions'])}")
            print(f"   Response options: {questions['response_options']}")
        else:
            print(f"   ❌ Failed to get PHQ-9 questions: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error getting PHQ-9 questions: {e}")
        return
    
    # Test 2: Get questions for GAD-7
    print("\n2. Testing GAD-7 questions endpoint...")
    try:
        response = requests.get("http://localhost:8000/api/v1/clinical/questions/gad7")
        if response.status_code == 200:
            questions = response.json()
            print(f"   ✅ GAD-7 questions retrieved successfully")
            print(f"   Questions count: {len(questions['questions'])}")
        else:
            print(f"   ❌ Failed to get GAD-7 questions: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error getting GAD-7 questions: {e}")
        return
    
    # Test 3: Get questions for PSS-10
    print("\n3. Testing PSS-10 questions endpoint...")
    try:
        response = requests.get("http://localhost:8000/api/v1/clinical/questions/pss10")
        if response.status_code == 200:
            questions = response.json()
            print(f"   ✅ PSS-10 questions retrieved successfully")
            print(f"   Questions count: {len(questions['questions'])}")
        else:
            print(f"   ❌ Failed to get PSS-10 questions: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error getting PSS-10 questions: {e}")
        return
    
    print("\n✅ All assessment question endpoints are working!")
    print("\n📝 Note: To test assessment submission and history, you need to:")
    print("   1. Create a user account")
    print("   2. Login to get an access token")
    print("   3. Submit an assessment with the token")
    print("   4. Check assessment history")

if __name__ == "__main__":
    test_assessment_functionality()
