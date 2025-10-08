#!/usr/bin/env python3
"""
Test script to verify logging configuration and Google OAuth endpoint logging
"""

import sys
import os
import requests
import json

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from logging_config import setup_logging
import logging

def test_logging_setup():
    """Test if logging is working correctly"""
    print("Setting up logging...")
    setup_logging()
    
    logger = logging.getLogger(__name__)
    logger.info("=== LOGGING TEST STARTED ===")
    logger.info("This is an INFO level message")
    logger.warning("This is a WARNING level message")
    logger.error("This is an ERROR level message")
    logger.debug("This is a DEBUG level message")
    logger.info("=== LOGGING TEST COMPLETED ===")
    
    print("Logging test completed. Check the log files:")
    print("- app.log")
    print("- google_oauth.log")
    print("- errors.log")

def test_google_oauth_endpoint():
    """Test the Google OAuth endpoint with a dummy request"""
    print("\nTesting Google OAuth endpoint...")
    
    # Test with invalid token to see error logging
    test_data = {
        "google_token": "invalid_token_for_testing"
    }
    
    try:
        # Make request to the Google OAuth endpoint
        response = requests.post(
            "http://localhost:8000/api/v1/auth/google",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
    except requests.exceptions.ConnectionError:
        print("Could not connect to the server. Make sure the backend is running on localhost:8000")
    except Exception as e:
        print(f"Error making request: {e}")

def test_request_logging():
    """Test if request logging middleware is working"""
    print("\nTesting request logging...")
    
    try:
        # Make a simple request to the health endpoint
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Health check response: {response.status_code}")
        
        # Make a request to a non-existent endpoint
        response = requests.get("http://localhost:8000/nonexistent", timeout=5)
        print(f"Non-existent endpoint response: {response.status_code}")
        
    except requests.exceptions.ConnectionError:
        print("Could not connect to the server. Make sure the backend is running on localhost:8000")
    except Exception as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    print("=== LOGGING AND API TEST SCRIPT ===")
    print("This script will test:")
    print("1. Logging configuration")
    print("2. Google OAuth endpoint logging")
    print("3. Request logging middleware")
    print()
    
    # Test logging setup
    test_logging_setup()
    
    # Test API endpoints (only if server is running)
    test_google_oauth_endpoint()
    test_request_logging()
    
    print("\n=== TEST COMPLETED ===")
    print("Check the log files for detailed information:")
    print("- app.log: All application logs")
    print("- google_oauth.log: Google OAuth specific logs")
    print("- errors.log: Error logs only")
