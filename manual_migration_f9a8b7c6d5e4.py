"""
Manual migration script for user_free_service table
This is needed for Neon DB compatibility
"""
from app.database import engine
from sqlalchemy import text

def run_manual_migration():
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # Check if table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_free_service'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                print("Creating user_free_service table...")
                
                # Create table
                conn.execute(text("""
                    CREATE TABLE user_free_service (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                        access_code VARCHAR(20) NOT NULL,
                        subscription_token VARCHAR(255) NOT NULL,
                        plan_type VARCHAR(20) NOT NULL DEFAULT 'basic',
                        has_used BOOLEAN NOT NULL DEFAULT true,
                        generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    );
                """))
                print("✓ Table created successfully")
            else:
                print("✓ Table already exists")
            
            # Check and create indexes
            # Index 1: user_id (unique)
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE indexname = 'ix_user_free_service_user_id'
                );
            """))
            index1_exists = result.scalar()
            
            if not index1_exists:
                print("Creating index: ix_user_free_service_user_id...")
                conn.execute(text("""
                    CREATE UNIQUE INDEX ix_user_free_service_user_id 
                    ON user_free_service (user_id);
                """))
                print("✓ Index ix_user_free_service_user_id created")
            else:
                print("✓ Index ix_user_free_service_user_id already exists")
            
            # Index 2: access_code
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE indexname = 'ix_user_free_service_access_code'
                );
            """))
            index2_exists = result.scalar()
            
            if not index2_exists:
                print("Creating index: ix_user_free_service_access_code...")
                conn.execute(text("""
                    CREATE INDEX ix_user_free_service_access_code 
                    ON user_free_service (access_code);
                """))
                print("✓ Index ix_user_free_service_access_code created")
            else:
                print("✓ Index ix_user_free_service_access_code already exists")
            
            # Index 3: id (primary key creates index automatically)
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE indexname = 'ix_user_free_service_id'
                );
            """))
            index3_exists = result.scalar()
            
            if not index3_exists:
                print("Creating index: ix_user_free_service_id...")
                conn.execute(text("""
                    CREATE INDEX ix_user_free_service_id 
                    ON user_free_service (id);
                """))
                print("✓ Index ix_user_free_service_id created")
            else:
                print("✓ Index ix_user_free_service_id already exists")
            
            # Update alembic version
            print("\nUpdating alembic version...")
            conn.execute(text("""
                UPDATE alembic_version 
                SET version_num = 'f9a8b7c6d5e4' 
                WHERE version_num = 'abdaa4f06ec2';
            """))
            print("✓ Alembic version updated to f9a8b7c6d5e4")
            
            # Commit transaction
            trans.commit()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_manual_migration()


