#!/usr/bin/env python3
"""
Check organizations in the database
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_organizations():
    """Check what organizations exist in the database"""
    print("🔍 Checking Organizations in Database")
    print("=" * 40)
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")
        
        # Check if organisations table exists
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'organisations')"
        )
        
        if not table_exists:
            print("❌ 'organisations' table does not exist")
            return
        
        print("✅ 'organisations' table exists")
        
        # Get all organizations
        organizations = await conn.fetch("SELECT * FROM organisations")
        
        if not organizations:
            print("📝 No organizations found in database")
        else:
            print(f"📝 Found {len(organizations)} organizations:")
            for org in organizations:
                print(f"   - ID: {org['id']}")
                print(f"     Company: {org['company_name']}")
                print(f"     Email: {org['hremail']}")
                print(f"     Created: {org['created_at']}")
                print(f"     Password Hash: {org['password_hash'][:50]}...")
                print()
        
        # Check if hr@gmail.com exists
        hr_org = await conn.fetchrow(
            "SELECT * FROM organisations WHERE hremail = $1", 
            "hr@gmail.com"
        )
        
        if hr_org:
            print("✅ Organization with hr@gmail.com found:")
            print(f"   - ID: {hr_org['id']}")
            print(f"   - Company: {hr_org['company_name']}")
            print(f"   - Password Hash: {hr_org['password_hash'][:50]}...")
        else:
            print("❌ Organization with hr@gmail.com NOT found")
        
        await conn.close()
        print("✅ Database connection closed")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_organizations())
