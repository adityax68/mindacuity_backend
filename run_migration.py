#!/usr/bin/env python3

from app.database import engine
from sqlalchemy import text

def run_migration():
    try:
        with engine.connect() as conn:
            # Read the migration file
            with open('migrations/add_refresh_tokens.sql', 'r') as f:
                migration_sql = f.read()
            
            # Execute the migration
            conn.execute(text(migration_sql))
            conn.commit()
            print('Migration completed successfully')
    except Exception as e:
        print(f'Migration failed: {e}')

if __name__ == '__main__':
    run_migration()
