"""Check and fix alembic version"""
from app.database import engine
from sqlalchemy import text

# Check current version
with engine.connect() as conn:
    result = conn.execute(text('SELECT version_num FROM alembic_version'))
    current_version = result.scalar()
    print(f"Current alembic version: {current_version}")

# Update if needed
if current_version != 'f9a8b7c6d5e4':
    print(f"Updating from {current_version} to f9a8b7c6d5e4...")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE alembic_version 
            SET version_num = 'f9a8b7c6d5e4'
        """))
        print("✅ Alembic version updated successfully!")
else:
    print("✅ Alembic version is already correct!")

# Verify table exists
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_name = 'user_free_service'
    """))
    table = result.scalar()
    print(f"\nTable 'user_free_service' exists: {table is not None}")
    
    # Verify indexes
    result = conn.execute(text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'user_free_service'
        ORDER BY indexname
    """))
    indexes = [row[0] for row in result]
    print(f"Indexes: {indexes}")

