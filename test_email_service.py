#!/usr/bin/env python3
"""
Test script for the email service
Run this to test basic email functionality
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from app.services.email_service import EmailService
from app.services.email_utils import email_utils
from app.database import get_db

async def test_basic_email_send():
    """Test basic email sending functionality"""
    print("🧪 Testing basic email sending...")
    
    try:
        email_service = EmailService()
        
        # Test email data
        test_email = os.getenv("TEST_EMAIL", "test@example.com")
        
        result = await email_service.send_email(
            to_emails=[test_email],
            subject="Test Email from Health App",
            html_content="""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">Test Email</h1>
                <p>This is a test email from the Health App email service.</p>
                <p>If you receive this email, the email service is working correctly!</p>
                <br>
                <p>Best regards,<br>Health App Team</p>
            </body>
            </html>
            """,
            text_content="This is a test email from the Health App email service. If you receive this email, the email service is working correctly!",
            template_name="test_email"
        )
        
        print(f"✅ Email send result: {result}")
        return result.get("status") == "success"
        
    except Exception as e:
        print(f"❌ Error testing email send: {e}")
        return False

async def test_welcome_email():
    """Test welcome email utility"""
    print("🧪 Testing welcome email utility...")
    
    try:
        test_email = os.getenv("TEST_EMAIL", "test@example.com")
        
        result = await email_utils.send_welcome_email(
            user_email=test_email,
            user_name="Test User"
        )
        
        print(f"✅ Welcome email result: {result}")
        return result.get("status") == "success"
        
    except Exception as e:
        print(f"❌ Error testing welcome email: {e}")
        return False

async def test_email_stats():
    """Test email statistics"""
    print("🧪 Testing email statistics...")
    
    try:
        db = next(get_db())
        email_service = EmailService()
        
        stats = await email_service.get_email_stats(db, days=7)
        print(f"✅ Email stats: {stats}")
        return True
        
    except Exception as e:
        print(f"❌ Error testing email stats: {e}")
        return False

async def test_unsubscribe():
    """Test unsubscribe functionality"""
    print("🧪 Testing unsubscribe functionality...")
    
    try:
        test_email = os.getenv("TEST_EMAIL", "test@example.com")
        db = next(get_db())
        email_service = EmailService()
        
        result = await email_service.unsubscribe_email(
            email=test_email,
            reason="Test unsubscribe",
            db=db
        )
        
        print(f"✅ Unsubscribe result: {result}")
        return result.get("status") == "success"
        
    except Exception as e:
        print(f"❌ Error testing unsubscribe: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting Email Service Tests")
    print("=" * 50)
    
    # Check required environment variables
    required_vars = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY", 
        "AWS_REGION",
        "SES_FROM_EMAIL"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return
    
    print("✅ All required environment variables are set")
    print()
    
    # Run tests
    tests = [
        ("Basic Email Send", test_basic_email_send),
        ("Welcome Email", test_welcome_email),
        ("Email Statistics", test_email_stats),
        ("Unsubscribe", test_unsubscribe)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"Result: {'✅ PASSED' if result else '❌ FAILED'}")
        except Exception as e:
            print(f"Result: ❌ ERROR - {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("=" * 50)
    print("📊 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Email service is ready to use.")
    else:
        print("⚠️  Some tests failed. Please check the configuration and try again.")

if __name__ == "__main__":
    asyncio.run(main())
