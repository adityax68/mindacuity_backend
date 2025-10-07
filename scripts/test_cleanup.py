#!/usr/bin/env python3
"""
Test script to verify the cleanup worked correctly
This script tests that all the unified scripts work properly.
"""

import sys
import os
import subprocess
from pathlib import Path

def test_script(script_name, command, description):
    """Test a script command"""
    try:
        print(f"🧪 Testing {description}...")
        script_path = Path(__file__).parent / script_name
        cmd = f"python {script_path} {command}"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"  ✅ {description} - SUCCESS")
            return True
        else:
            print(f"  ❌ {description} - FAILED")
            if result.stderr:
                print(f"     Error: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ⏰ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"  ❌ {description} - ERROR: {e}")
        return False

def main():
    print("🧪 Testing Cleanup - Verifying All Scripts Work")
    print("=" * 60)
    
    tests = [
        # Migration tests
        ("manage_migrations.py", "status", "Migration Status Check"),
        
        # Privilege tests
        ("manage_privileges.py", "status", "Privilege Status Check"),
        ("manage_privileges.py", "list", "Privilege List"),
        
        # User tests
        ("manage_users.py", "list", "User List"),
        
        # Seed tests (these might fail if already seeded, which is OK)
        ("seed_system.py", "test-definitions", "Test Definitions Seed"),
    ]
    
    passed = 0
    total = len(tests)
    
    for script, command, description in tests:
        if test_script(script, command, description):
            passed += 1
        print()  # Add spacing
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Cleanup was successful!")
        return True
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
