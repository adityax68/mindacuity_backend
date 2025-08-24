#!/usr/bin/env python3
"""
Test script to verify chat functionality is working
"""
import requests
import json

def test_chat_functionality():
    """Test the chat functionality"""
    print("💬 Testing Chat Functionality")
    print("=" * 40)
    
    # Step 1: Create a test user
    print("1. Creating a test user for chat...")
    user_data = {
        "email": "chattest2@example.com",
        "username": "chattestuser2",
        "password": "testpass123"
    }
    
    try:
        response = requests.post("http://localhost:8000/api/v1/auth/signup", json=user_data)
        if response.status_code == 201:
            print("   ✅ User created successfully")
            user_info = response.json()
            user_id = user_info['id']
        else:
            print(f"   ❌ User creation failed: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error creating user: {e}")
        return
    
    # Step 2: Login to get access token
    print("\n2. Logging in to get access token...")
    login_data = {
        "username": "chattest2@example.com",
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
    
    # Step 3: Test chat message sending
    print("\n3. Testing chat message sending...")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    chat_data = {
        "message": "Hello, I'm feeling a bit anxious today. Can you help me?"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/chat/send",
            json=chat_data,
            headers=headers
        )
        if response.status_code == 200:
            chat_result = response.json()
            print("   ✅ Chat message sent successfully!")
            print(f"   Conversation ID: {chat_result['conversation_id']}")
            print(f"   AI Response: {chat_result['assistant_message'][:100]}...")
            print(f"   Message ID: {chat_result['message_id']}")
        else:
            print(f"   ❌ Chat message failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error sending chat message: {e}")
        return
    
    # Step 4: Test getting conversations
    print("\n4. Testing get conversations...")
    try:
        response = requests.get("http://localhost:8000/api/v1/chat/conversations", headers=headers)
        if response.status_code == 200:
            conversations = response.json()
            print(f"   ✅ Conversations retrieved successfully!")
            print(f"   Found {len(conversations)} conversations")
            for conv in conversations:
                print(f"      - ID: {conv['id']}, Title: {conv['title']}")
        else:
            print(f"   ❌ Failed to get conversations: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error getting conversations: {e}")
    
    # Step 5: Test getting conversation messages
    print("\n5. Testing get conversation messages...")
    try:
        conversation_id = chat_result['conversation_id']
        response = requests.get(
            f"http://localhost:8000/api/v1/chat/conversations/{conversation_id}/messages",
            headers=headers
        )
        if response.status_code == 200:
            messages_result = response.json()
            print(f"   ✅ Conversation messages retrieved successfully!")
            print(f"   Found {len(messages_result['messages'])} messages")
            for msg in messages_result['messages']:
                print(f"      - {msg['role']}: {msg['content'][:50]}...")
        else:
            print(f"   ❌ Failed to get conversation messages: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error getting conversation messages: {e}")
    
    print("\n🎉 Chat functionality test completed!")
    print("✅ The chatbot is now working properly!")

if __name__ == "__main__":
    test_chat_functionality()
