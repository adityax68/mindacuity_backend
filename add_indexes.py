#!/usr/bin/env python3
"""
Script to add database indexes for search optimization
"""
import asyncio
from sqlalchemy import text
from app.database import SessionLocal

async def add_search_indexes():
    db = SessionLocal()
    try:
        print("Adding database indexes for search optimization...")
        
        # Read the SQL file
        with open('migrations/add_search_indexes.sql', 'r') as f:
            sql_commands = f.read()
        
        # Split commands and execute each one
        commands = [cmd.strip() for cmd in sql_commands.split(';') if cmd.strip()]
        
        for i, command in enumerate(commands):
            if command:
                print(f"Executing command {i+1}/{len(commands)}: {command[:50]}...")
                try:
                    db.execute(text(command))
                    db.commit()
                    print(f"✅ Command {i+1} executed successfully")
                except Exception as e:
                    if "already exists" in str(e):
                        print(f"⚠️  Index already exists, skipping...")
                    else:
                        print(f"❌ Error executing command {i+1}: {e}")
                        db.rollback()
        
        print("\n🎉 Database indexes added successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(add_search_indexes())
