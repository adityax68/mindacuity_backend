#!/usr/bin/env python3
"""
Script to check database tables and their structure
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_database():
    """Check database tables and structure"""
    from app.database import engine
    from sqlalchemy import text
    
    print("🔍 Checking Database Tables and Structure")
    print("=" * 50)
    
    try:
        async with engine.begin() as conn:
            # Check what tables exist
            print("1. Checking existing tables...")
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
            tables = result.fetchall()
            print(f"   📊 Found {len(tables)} tables:")
            for table in tables:
                print(f"      - {table[0]}")
            
            # Check User table structure
            print("\n2. Checking User table structure...")
            if any('users' in table[0] for table in tables):
                result = await conn.execute(text("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position"))
                columns = result.fetchall()
                print("   📋 User table columns:")
                for col in columns:
                    print(f"      - {col[0]}: {col[1]} (nullable: {col[1]})")
            else:
                print("   ❌ User table not found!")
            
            # Check if there are any users in the table
            print("\n3. Checking User table data...")
            if any('users' in table[0] for table in tables):
                result = await conn.execute(text("SELECT COUNT(*) FROM users"))
                count = result.scalar()
                print(f"   👥 Found {count} users in the table")
                
                if count > 0:
                    result = await conn.execute(text("SELECT id, email, username, role FROM users LIMIT 3"))
                    users = result.fetchall()
                    print("   📝 Sample users:")
                    for user in users:
                        print(f"      - ID: {user[0]}, Email: {user[1]}, Username: {user[2]}, Role: {user[3]}")
            else:
                print("   ❌ Cannot check user data - table doesn't exist")
                
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_database())
