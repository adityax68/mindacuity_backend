#!/usr/bin/env python3
"""
Get all company IDs and information
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def get_company_ids():
    """Get all company IDs and information"""
    print("🏢 Company IDs and Information")
    print("=" * 50)
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")
        
        # Get all organizations
        organizations = await conn.fetch("SELECT * FROM organisations ORDER BY created_at DESC")
        
        if not organizations:
            print("📝 No organizations found in database")
        else:
            print(f"📝 Found {len(organizations)} organizations:")
            print()
            
            for i, org in enumerate(organizations, 1):
                print(f"{i}. Company: {org['company_name']}")
                print(f"   📧 Email: {org['hremail']}")
                print(f"   🆔 Company ID: {org['id']}")
                print(f"   📅 Created: {org['created_at']}")
                print(f"   🔑 Password Hash: {org['password_hash'][:30]}...")
                print()
        
        # Also show employees if any exist
        employees = await conn.fetch("SELECT * FROM employees ORDER BY created_at DESC")
        
        if employees:
            print(f"👥 Found {len(employees)} employees:")
            print()
            
            for i, emp in enumerate(employees, 1):
                print(f"{i}. Employee: {emp['name']}")
                print(f"   📧 Email: {emp['employee_email']}")
                print(f"   🏢 Company ID: {emp['company_id']}")
                print(f"   📅 Joined: {emp['joining_date']}")
                print()
        
        await conn.close()
        print("✅ Database connection closed")
        
        print("\n💡 How to use Company IDs:")
        print("   - For employee signup: Use the Company ID in the employee_signup endpoint")
        print("   - For employee login: Use the Company ID in the employee_login endpoint")
        print("   - Example: POST /api/auth/employee/signup with company_id field")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(get_company_ids())
