#!/usr/bin/env python3
"""
Database Reset Script for Health App

This script will:
1. Drop all existing tables
2. Create all tables from scratch
3. Optionally seed with initial data

Usage:
    python reset_db.py [--seed]
    
Options:
    --seed    Add initial seed data after reset
"""

import sys
import os
import argparse
from sqlalchemy import text
from app.database import engine, Base
from app.models import User, ClinicalAssessment
from app.auth import get_password_hash

def reset_database():
    """Drop all tables and recreate them"""
    print("🔄 Resetting database...")
    
    try:
        # Drop all tables
        print("📥 Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ All tables dropped successfully")
        
        # Create all tables
        print("📤 Creating all tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        return False

def seed_database():
    """Add initial seed data"""
    print("🌱 Seeding database with initial data...")
    
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        
        # Create a test user
        test_user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("testpassword123"),
            full_name="Test User",
            age=25,  # Add required age field
            country="India",  # Add optional profile fields
            state="Maharashtra",
            city="Mumbai",
            is_active=True
        )
        
        db.add(test_user)
        db.commit()
        
        # Create a sample assessment
        sample_assessment = ClinicalAssessment(
            user_id=test_user.id,
            assessment_type="comprehensive",
            total_score=15,
            severity_level="moderate",
            interpretation="Moderate symptoms of depression and anxiety detected. Consider seeking professional help.",
            responses={
                "phq9": {"total": 12, "responses": [2, 1, 2, 1, 2, 1, 1, 1, 1]},
                "gad7": {"total": 8, "responses": [1, 1, 2, 1, 1, 1, 1]},
                "pss10": {"total": 15, "responses": [2, 1, 2, 1, 2, 1, 2, 1, 2, 1]}
            },
            max_score=27,
            assessment_name="Comprehensive Assessment"
        )
        
        db.add(sample_assessment)
        db.commit()
        
        print("✅ Database seeded successfully")
        print(f"   Test user: test@example.com / testpassword123")
        print(f"   User ID: {test_user.id}")
        print(f"   Sample assessment created")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Reset the Health App database")
    parser.add_argument("--seed", action="store_true", help="Seed database with initial data")
    args = parser.parse_args()
    
    print("🏥 Health App Database Reset")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Error: Please run this script from the backend directory")
        sys.exit(1)
    
    # Reset database
    if not reset_database():
        print("❌ Database reset failed")
        sys.exit(1)
    
    # Seed if requested
    if args.seed:
        if not seed_database():
            print("❌ Database seeding failed")
            sys.exit(1)
    
    print("=" * 40)
    print("✅ Database reset completed successfully!")
    
    if args.seed:
        print("\n📝 Test credentials:")
        print("   Email: test@example.com")
        print("   Password: testpassword123")
    
    print("\n🚀 You can now start the application!")

if __name__ == "__main__":
    main() 