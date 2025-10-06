#!/usr/bin/env python3
"""
Test script for LangChain integration in SessionChatService.
This tests the new LangChain-based conversation management.
"""

import asyncio
import sys
import os
from sqlalchemy.orm import Session

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_db
from app.services.session_chat_service import SessionChatService
from app.schemas import SessionChatMessageRequest

async def test_langchain_integration():
    """Test the LangChain integration with a simple conversation."""
    
    print("🧪 Testing LangChain Integration...")
    print("=" * 50)
    
    try:
        # Get database session
        db = next(get_db())
        
        # Initialize the service
        print("📦 Initializing SessionChatService with LangChain...")
        service = SessionChatService()
        print("✅ Service initialized successfully!")
        
        # Test session identifier (use timestamp to ensure fresh session)
        import time
        session_id = f"test_langchain_session_{int(time.time())}"
        
        # Test message 1
        print(f"\n💬 Test Message 1: 'Hello, I'm feeling anxious today'")
        request1 = SessionChatMessageRequest(
            session_identifier=session_id,
            message="Hello, I'm feeling anxious today"
        )
        
        response1 = await service.process_chat_message(db, session_id, request1)
        print(f"🤖 AI Response 1: {response1.message}")
        print(f"📊 Usage: {response1.messages_used}/{response1.message_limit} ({response1.plan_type})")
        
        # Test message 2 (should have context from message 1)
        print(f"\n💬 Test Message 2: 'What can I do to feel better?'")
        request2 = SessionChatMessageRequest(
            session_identifier=session_id,
            message="What can I do to feel better?"
        )
        
        response2 = await service.process_chat_message(db, session_id, request2)
        print(f"🤖 AI Response 2: {response2.message}")
        print(f"📊 Usage: {response2.messages_used}/{response2.message_limit} ({response2.plan_type})")
        
        # Test getting conversation history
        print(f"\n📜 Getting conversation history...")
        messages = service.get_conversation_messages(db, session_id)
        print(f"📝 Found {len(messages)} messages in conversation:")
        for i, msg in enumerate(messages, 1):
            print(f"  {i}. {msg['role']}: {msg['content'][:100]}...")
        
        print(f"\n✅ LangChain integration test completed successfully!")
        print("🎉 Your session chatbot now uses LangChain for conversation management!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_langchain_integration())

