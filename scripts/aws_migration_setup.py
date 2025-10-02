#!/usr/bin/env python3
"""
AWS Migration Setup Script
This script helps migrate from Neon to AWS RDS and sets up the privilege system
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base, User, Role, Privilege, user_privileges, role_privileges, Subscription, Conversation, ConversationUsage, Message
from app.services.role_service import RoleService

def check_database_connection():
    """Check if database connection is working"""
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_tables():
    """Create all necessary tables"""
    try:
        engine = create_engine(settings.database_url)
        print("📋 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def check_existing_data():
    """Check what data already exists"""
    try:
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("🔍 Checking existing data...")
        
        # Check users
        user_count = db.query(User).count()
        print(f"  👥 Users: {user_count}")
        
        # Check roles
        role_count = db.query(Role).count()
        print(f"  👥 Roles: {role_count}")
        
        # Check privileges
        privilege_count = db.query(Privilege).count()
        print(f"  🔐 Privileges: {privilege_count}")
        
        # Check session chat tables
        subscription_count = db.query(Subscription).count()
        conversation_count = db.query(Conversation).count()
        print(f"  💬 Subscriptions: {subscription_count}")
        print(f"  💬 Conversations: {conversation_count}")
        
        # Show existing roles
        if role_count > 0:
            roles = db.query(Role).all()
            print("  📋 Existing roles:")
            for role in roles:
                priv_count = len(role.privileges)
                print(f"    - {role.name}: {priv_count} privileges")
        
        # Show existing privileges by category
        if privilege_count > 0:
            privileges = db.query(Privilege).all()
            categories = {}
            for priv in privileges:
                category = priv.category or "uncategorized"
                if category not in categories:
                    categories[category] = []
                categories[category].append(priv.name)
            
            print("  📂 Existing privileges by category:")
            for category, privs in categories.items():
                print(f"    {category}: {len(privs)} privileges")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Failed to check existing data: {e}")
        return False

def migrate_users_table():
    """Add missing columns to users table if needed"""
    try:
        engine = create_engine(settings.database_url)
        inspector = inspect(engine)
        
        print("🔍 Checking users table structure...")
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        
        with engine.connect() as conn:
            # Add missing columns
            if 'role' not in existing_columns:
                print("  ➕ Adding 'role' column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))
                conn.commit()
                print("  ✅ Added 'role' column")
            
            if 'is_verified' not in existing_columns:
                print("  ➕ Adding 'is_verified' column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("  ✅ Added 'is_verified' column")
            
            if 'is_active' not in existing_columns:
                print("  ➕ Adding 'is_active' column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                conn.commit()
                print("  ✅ Added 'is_active' column")
            
            print("✅ Users table migration completed")
            return True
    except Exception as e:
        print(f"❌ Failed to migrate users table: {e}")
        return False

def initialize_privilege_system():
    """Initialize the complete privilege system"""
    try:
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("🔧 Initializing privilege system...")
        role_service = RoleService(db)
        
        # Initialize default roles and privileges
        asyncio.run(role_service.initialize_default_roles_and_privileges())
        
        # Add additional privileges that might be missing
        print("➕ Adding additional privileges...")
        additional_privileges = [
            # Research privileges
            {"name": "read_researches", "description": "Read research articles", "category": "research"},
            {"name": "manage_researches", "description": "Manage research articles (create, update, delete)", "category": "research"},
            
            # Admin access privilege
            {"name": "admin_access", "description": "Access to admin panel", "category": "system"},
        ]
        
        for priv_data in additional_privileges:
            existing_priv = db.query(Privilege).filter(Privilege.name == priv_data["name"]).first()
            if not existing_priv:
                privilege = Privilege(**priv_data)
                db.add(privilege)
                print(f"  ✅ Created privilege: {priv_data['name']}")
            else:
                print(f"  ℹ️  Privilege already exists: {priv_data['name']}")
        
        db.commit()
        
        # Ensure admin role has ALL privileges including research privileges
        print("👑 Ensuring admin role has all privileges...")
        all_privileges = db.query(Privilege).filter(Privilege.is_active == True).all()
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        
        if admin_role:
            admin_role.privileges.clear()
            for privilege in all_privileges:
                admin_role.privileges.append(privilege)
            db.commit()
            print(f"  ✅ Admin role now has {len(all_privileges)} privileges")
        
        # Update existing users to have 'user' role if not set
        print("👥 Updating existing users...")
        users_without_role = db.query(User).filter(
            (User.role == None) | (User.role == '')
        ).all()
        
        for user in users_without_role:
            user.role = 'user'
            print(f"  ✅ Updated user {user.email} to role 'user'")
        
        db.commit()
        
        # Verify setup
        print("\n🔍 Verifying privilege system...")
        total_roles = db.query(Role).count()
        total_privileges = db.query(Privilege).count()
        total_users = db.query(User).count()
        
        print(f"  📊 Total roles: {total_roles}")
        print(f"  📊 Total privileges: {total_privileges}")
        print(f"  📊 Total users: {total_users}")
        
        # Show role privilege counts
        print("\n📋 Role Privilege Summary:")
        roles = db.query(Role).all()
        for role in roles:
            priv_count = len(role.privileges)
            print(f"  {role.name}: {priv_count} privileges")
        
        db.close()
        print("✅ Privilege system initialization completed")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize privilege system: {e}")
        return False

def check_session_chat_tables():
    """Check if session chat tables exist"""
    try:
        engine = create_engine(settings.database_url)
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        required_tables = [
            'subscriptions',
            'conversations_new', 
            'messages_new',
            'conversation_usage'
        ]
        
        missing_tables = []
        for table in required_tables:
            if table not in existing_tables:
                missing_tables.append(table)
        
        print(f"🔍 Session chat tables check:")
        print(f"  📊 Required tables: {required_tables}")
        print(f"  ❌ Missing tables: {missing_tables}")
        
        return missing_tables
    except Exception as e:
        print(f"❌ Failed to check session chat tables: {e}")
        return []

def create_session_chat_tables():
    """Create session-based chat tables"""
    try:
        engine = create_engine(settings.database_url)
        
        print("🚀 Creating session-based chat tables...")
        
        with engine.connect() as conn:
            # Create conversations_new table
            print("  📝 Creating conversations_new table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversations_new (
                    id SERIAL PRIMARY KEY,
                    session_identifier VARCHAR(255) UNIQUE NOT NULL,
                    title VARCHAR(255) DEFAULT 'New Conversation',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN DEFAULT true
                )
            """))
            conn.commit()
            
            # Create messages_new table
            print("  📝 Creating messages_new table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages_new (
                    id SERIAL PRIMARY KEY,
                    session_identifier VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    encrypted_content TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    
                    FOREIGN KEY (session_identifier) REFERENCES conversations_new(session_identifier)
                )
            """))
            conn.commit()
            
            # Create subscriptions table
            print("  📝 Creating subscriptions table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    subscription_token VARCHAR(255) UNIQUE NOT NULL,
                    access_code VARCHAR(20) UNIQUE NOT NULL,
                    plan_type VARCHAR(20) NOT NULL CHECK (plan_type IN ('free', 'basic', 'premium')),
                    message_limit INTEGER,
                    price DECIMAL(10,2) DEFAULT 0.00,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    expires_at TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN DEFAULT true
                )
            """))
            conn.commit()
            
            # Create conversation_usage table
            print("  📝 Creating conversation_usage table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversation_usage (
                    id SERIAL PRIMARY KEY,
                    session_identifier VARCHAR(255) NOT NULL,
                    subscription_token VARCHAR(255) NOT NULL,
                    messages_used INTEGER DEFAULT 0,
                    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    
                    FOREIGN KEY (session_identifier) REFERENCES conversations_new(session_identifier),
                    FOREIGN KEY (subscription_token) REFERENCES subscriptions(subscription_token),
                    UNIQUE(session_identifier, subscription_token)
                )
            """))
            conn.commit()
            
            # Create indexes for performance
            print("  📝 Creating indexes...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations_new(session_identifier)",
                "CREATE INDEX IF NOT EXISTS idx_conversations_expires ON conversations_new(expires_at)",
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages_new(session_identifier)",
                "CREATE INDEX IF NOT EXISTS idx_messages_created ON messages_new(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_subscriptions_token ON subscriptions(subscription_token)",
                "CREATE INDEX IF NOT EXISTS idx_subscriptions_code ON subscriptions(access_code)",
                "CREATE INDEX IF NOT EXISTS idx_usage_session ON conversation_usage(session_identifier)",
                "CREATE INDEX IF NOT EXISTS idx_usage_subscription ON conversation_usage(subscription_token)"
            ]
            
            for index_sql in indexes:
                conn.execute(text(index_sql))
            conn.commit()
            
            # Insert default subscriptions
            print("  📝 Inserting default subscriptions...")
            conn.execute(text("""
                INSERT INTO subscriptions (subscription_token, access_code, plan_type, message_limit, price, expires_at)
                VALUES ('sub_free_default', 'FREE-DEFAULT', 'free', 5, 0.00, NOW() + INTERVAL '24 hours')
                ON CONFLICT (subscription_token) DO NOTHING
            """))
            conn.commit()
            
            conn.execute(text("""
                INSERT INTO subscriptions (subscription_token, access_code, plan_type, message_limit, price, expires_at)
                VALUES ('sub_basic_template', 'BASIC-TEMPLATE', 'basic', 10, 5.00, NOW() + INTERVAL '30 days')
                ON CONFLICT (subscription_token) DO NOTHING
            """))
            conn.commit()
            
            # Fix foreign key constraint to allow conversation deletion while preserving usage records
            print("  📝 Fixing foreign key constraints...")
            conn.execute(text("""
                ALTER TABLE conversation_usage 
                DROP CONSTRAINT IF EXISTS conversation_usage_session_identifier_fkey
            """))
            conn.commit()
            
            conn.execute(text("""
                ALTER TABLE conversation_usage 
                ADD CONSTRAINT conversation_usage_session_identifier_fkey 
                FOREIGN KEY (session_identifier) 
                REFERENCES conversations_new(session_identifier) 
                ON DELETE SET NULL
            """))
            conn.commit()
            
            conn.execute(text("""
                ALTER TABLE conversation_usage 
                ALTER COLUMN session_identifier DROP NOT NULL
            """))
            conn.commit()
        
        print("✅ Session-based chat tables created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create session chat tables: {e}")
        return False

def test_session_chat_functionality():
    """Test if session chat functionality works"""
    try:
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("🧪 Testing session chat functionality...")
        
        # Test subscription queries
        subscription_count = db.query(Subscription).count()
        print(f"  📊 Subscriptions in database: {subscription_count}")
        
        # Test access code lookup
        test_subscription = db.query(Subscription).filter(
            Subscription.access_code == 'FREE-DEFAULT'
        ).first()
        
        if test_subscription:
            print(f"  ✅ Found test subscription: {test_subscription.access_code}")
        else:
            print("  ⚠️  No test subscription found")
        
        # Test conversation table
        conversation_count = db.query(Conversation).count()
        print(f"  📊 Conversations in database: {conversation_count}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to test session chat functionality: {e}")
        return False

def main():
    """Main migration process"""
    print("🚀 Starting AWS Migration Setup...")
    print("=" * 50)
    
    # Step 1: Check database connection
    if not check_database_connection():
        print("❌ Cannot proceed without database connection")
        return
    
    # Step 2: Create tables
    if not create_tables():
        print("❌ Cannot proceed without creating tables")
        return
    
    # Step 3: Check existing data
    check_existing_data()
    
    # Step 4: Migrate users table
    if not migrate_users_table():
        print("❌ Failed to migrate users table")
        return
    
    # Step 5: Initialize privilege system
    if not initialize_privilege_system():
        print("❌ Failed to initialize privilege system")
        return
    
    # Step 6: Check session chat tables
    missing_tables = check_session_chat_tables()
    
    # Step 7: Create session chat tables if missing
    if missing_tables:
        print(f"\n🔧 Creating missing session chat tables: {missing_tables}")
        if not create_session_chat_tables():
            print("❌ Failed to create session chat tables")
            return
    else:
        print("✅ All session chat tables already exist")
    
    # Step 8: Test session chat functionality
    test_session_chat_functionality()
    
    print("\n" + "=" * 50)
    print("✅ AWS Migration Setup Completed Successfully!")
    print("\n🎯 Next steps:")
    print("  1. Test the system: python scripts/check_privileges.py")
    print("  2. Create admin users: python scripts/make_admin.py <email>")
    print("  3. Test API endpoints")
    print("  4. Test access code validation in frontend")
    print("  5. Update your application configuration")

if __name__ == "__main__":
    main()
