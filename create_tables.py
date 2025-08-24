#!/usr/bin/env python3
"""
Script to create the new Organization/Employee database tables
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def create_tables():
    """Create the new database tables"""
    from app.database import engine
    from app.models import Base
    from sqlalchemy import text
    
    print("🚀 Creating new database tables...")
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")
        
        # List the tables that were created
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = result.fetchall()
            print(f"📊 Available tables: {[table[0] for table in tables]}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_tables())
