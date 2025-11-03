#!/usr/bin/env python3
"""
Unified Seed System
This script handles all database seeding operations.

Usage:
    python scripts/seed_system.py test-definitions    # Seed test definitions (PHQ-9, GAD-7, PSS-10)
    python scripts/seed_system.py test-user          # Create a test user
    python scripts/seed_system.py all                # Seed everything
"""

import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Base, User, TestDefinition, TestQuestion, TestQuestionOption, TestScoringRange
from app.auth import get_password_hash
from decimal import Decimal

class SeedSystem:
    def __init__(self):
        self.engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
    
    def seed_test_definitions(self):
        """Seed the database with test definitions (PHQ-9, GAD-7, PSS-10)"""
        try:
            print("🌱 Seeding test definitions...")
            
            # Check if test definitions already exist
            existing_tests = self.db.query(TestDefinition).count()
            from app.models import TestQuestion
            existing_questions = self.db.query(TestQuestion).count()
            
            if existing_tests > 0 and existing_questions > 0:
                print(f"  ℹ️  {existing_tests} test definitions and {existing_questions} questions already exist. Skipping...")
                return True
            
            # Get or create PHQ-9 test definition
            phq9 = self.db.query(TestDefinition).filter(TestDefinition.test_code == "phq9").first()
            if not phq9:
                print("  📝 Creating PHQ-9 test definition...")
                phq9 = TestDefinition(
                    test_code="phq9",
                    test_name="PHQ-9",
                    test_category="depression",
                    description="Patient Health Questionnaire-9: A validated tool for assessing depression severity",
                    total_questions=9,
                    is_active=True
                )
                self.db.add(phq9)
                self.db.flush()
            else:
                print(f"  ✅ Using existing PHQ-9 test definition (ID: {phq9.id})...")
            
            # PHQ-9 Questions
            phq9_questions = [
                "Over the last 2 weeks, how often have you had little interest or pleasure in doing things?",
                "Over the last 2 weeks, how often have you felt down, depressed, or hopeless?",
                "Over the last 2 weeks, how often have you had trouble falling or staying asleep, or sleeping too much?",
                "Over the last 2 weeks, how often have you felt tired or had little energy?",
                "Over the last 2 weeks, how often have you had a poor appetite or overeating?",
                "Over the last 2 weeks, how often have you felt bad about yourself - or that you are a failure or have let yourself or your family down?",
                "Over the last 2 weeks, how often have you had trouble concentrating on things, such as reading the newspaper or watching television?",
                "Over the last 2 weeks, how often have you been moving or speaking slowly enough that other people could have noticed. Or the opposite - being so fidgety or restless that you have been moving around a lot more than usual?",
                "Over the last 2 weeks, how often have you had thoughts that you would be better off dead or of hurting yourself in some way?"
            ]
            
            # Check if PHQ-9 questions already exist
            existing_phq9_questions = self.db.query(TestQuestion).filter(
                TestQuestion.test_definition_id == phq9.id
            ).count()
            
            if existing_phq9_questions == 0:
                print(f"  📝 Creating {len(phq9_questions)} PHQ-9 questions...")
            
            for i, question_text in enumerate(phq9_questions, 1):
                question = TestQuestion(
                    test_definition_id=phq9.id,
                    question_number=i,
                    question_text=question_text,
                    is_reverse_scored=False
                )
                self.db.add(question)
                self.db.flush()
                
                # Add response options for PHQ-9
                options = [
                    ("Not at all", 0, 1.0, 1),
                    ("Several days", 1, 1.0, 2),
                    ("More than half the days", 2, 1.0, 3),
                    ("Nearly every day", 3, 1.0, 4)
                ]
                
                for option_text, option_value, weight, display_order in options:
                    option = TestQuestionOption(
                        test_definition_id=phq9.id,
                        question_id=question.id,
                        option_text=option_text,
                        option_value=option_value,
                        weight=Decimal(str(weight)),
                        display_order=display_order
                    )
                    self.db.add(option)
            
            # PHQ-9 Scoring Ranges
            phq9_ranges = [
                (0, 4, "minimal", "Minimal Depression", "No treatment needed", "Continue monitoring mental health", "#10B981", 1),
                (5, 9, "mild", "Mild Depression", "Watchful waiting; repeat PHQ-9", "Consider counseling or therapy", "#F59E0B", 2),
                (10, 14, "moderate", "Moderate Depression", "Treatment plan, counseling, follow-up", "Seek professional help", "#EF4444", 3),
                (15, 19, "moderately_severe", "Moderately Severe Depression", "Active treatment with medication and/or therapy", "Immediate professional consultation", "#DC2626", 4),
                (20, 27, "severe", "Severe Depression", "Immediate treatment, medication and therapy", "Urgent professional intervention", "#991B1B", 5)
            ]
            
            from app.models import TestScoringRange
            existing_phq9_ranges = self.db.query(TestScoringRange).filter(
                TestScoringRange.test_definition_id == phq9.id
            ).count()
            
            if existing_phq9_ranges == 0:
                print(f"  📝 Creating {len(phq9_ranges)} PHQ-9 scoring ranges...")
            
            for min_score, max_score, severity_level, severity_label, interpretation, recommendations, color_code, priority in phq9_ranges:
                range_obj = TestScoringRange(
                    test_definition_id=phq9.id,
                    min_score=min_score,
                    max_score=max_score,
                    severity_level=severity_level,
                    severity_label=severity_label,
                    interpretation=interpretation,
                    recommendations=recommendations,
                    color_code=color_code,
                    priority=priority
                )
                self.db.add(range_obj)
            
            # Get or create GAD-7 test definition
            gad7 = self.db.query(TestDefinition).filter(TestDefinition.test_code == "gad7").first()
            if not gad7:
                print("  📝 Creating GAD-7 test definition...")
                gad7 = TestDefinition(
                    test_code="gad7",
                    test_name="GAD-7",
                    test_category="anxiety",
                    description="Generalized Anxiety Disorder-7: A validated tool for assessing anxiety severity",
                    total_questions=7,
                    is_active=True
                )
                self.db.add(gad7)
                self.db.flush()
            else:
                print(f"  ✅ Using existing GAD-7 test definition (ID: {gad7.id})...")
            
            # GAD-7 Questions
            gad7_questions = [
                "Over the last 2 weeks, how often have you felt nervous, anxious, or on edge?",
                "Over the last 2 weeks, how often have you not been able to stop or control worrying?",
                "Over the last 2 weeks, how often have you worried too much about different things?",
                "Over the last 2 weeks, how often have you had trouble relaxing?",
                "Over the last 2 weeks, how often have you been so restless that it's hard to sit still?",
                "Over the last 2 weeks, how often have you become easily annoyed or irritable?",
                "Over the last 2 weeks, how often have you felt afraid as if something awful might happen?"
            ]
            
            existing_gad7_questions = self.db.query(TestQuestion).filter(
                TestQuestion.test_definition_id == gad7.id
            ).count()
            
            if existing_gad7_questions == 0:
                print(f"  📝 Creating {len(gad7_questions)} GAD-7 questions...")
            
            for i, question_text in enumerate(gad7_questions, 1):
                question = TestQuestion(
                    test_definition_id=gad7.id,
                    question_number=i,
                    question_text=question_text,
                    is_reverse_scored=False
                )
                self.db.add(question)
                self.db.flush()
                
                # Add response options for GAD-7 (same as PHQ-9)
                options = [
                    ("Not at all", 0, 1.0, 1),
                    ("Several days", 1, 1.0, 2),
                    ("More than half the days", 2, 1.0, 3),
                    ("Nearly every day", 3, 1.0, 4)
                ]
                
                for option_text, option_value, weight, display_order in options:
                    option = TestQuestionOption(
                        test_definition_id=gad7.id,
                        question_id=question.id,
                        option_text=option_text,
                        option_value=option_value,
                        weight=Decimal(str(weight)),
                        display_order=display_order
                    )
                    self.db.add(option)
            
            # GAD-7 Scoring Ranges
            gad7_ranges = [
                (0, 4, "minimal", "Minimal Anxiety", "No treatment needed", "Continue monitoring mental health", "#10B981", 1),
                (5, 9, "mild", "Mild Anxiety", "Watchful waiting; repeat GAD-7", "Consider stress management techniques", "#F59E0B", 2),
                (10, 14, "moderate", "Moderate Anxiety", "Treatment plan, counseling, follow-up", "Seek professional help", "#EF4444", 3),
                (15, 21, "severe", "Severe Anxiety", "Active treatment with medication and/or therapy", "Immediate professional consultation", "#DC2626", 4)
            ]
            
            existing_gad7_ranges = self.db.query(TestScoringRange).filter(
                TestScoringRange.test_definition_id == gad7.id
            ).count()
            
            if existing_gad7_ranges == 0:
                print(f"  📝 Creating {len(gad7_ranges)} GAD-7 scoring ranges...")
            
            for min_score, max_score, severity_level, severity_label, interpretation, recommendations, color_code, priority in gad7_ranges:
                range_obj = TestScoringRange(
                    test_definition_id=gad7.id,
                    min_score=min_score,
                    max_score=max_score,
                    severity_level=severity_level,
                    severity_label=severity_label,
                    interpretation=interpretation,
                    recommendations=recommendations,
                    color_code=color_code,
                    priority=priority
                )
                self.db.add(range_obj)
            
            # Get or create PSS-10 test definition
            pss10 = self.db.query(TestDefinition).filter(TestDefinition.test_code == "pss10").first()
            if not pss10:
                print("  📝 Creating PSS-10 test definition...")
                pss10 = TestDefinition(
                    test_code="pss10",
                    test_name="PSS-10",
                    test_category="stress",
                    description="Perceived Stress Scale-10: A validated tool for assessing stress levels",
                    total_questions=10,
                    is_active=True
                )
                self.db.add(pss10)
                self.db.flush()
            else:
                print(f"  ✅ Using existing PSS-10 test definition (ID: {pss10.id})...")
            
            # PSS-10 Questions
            pss10_questions = [
                "In the last month, how often have you been upset because of something that happened unexpectedly?",
                "In the last month, how often have you felt that you were unable to control the important things in your life?",
                "In the last month, how often have you felt nervous and stressed?",
                "In the last month, how often have you felt confident about your ability to handle your personal problems?",
                "In the last month, how often have you felt that things were going your way?",
                "In the last month, how often have you found that you could not cope with all the things that you had to do?",
                "In the last month, how often have you been able to control irritations in your life?",
                "In the last month, how often have you felt that you were on top of things?",
                "In the last month, how often have you been angered because of things that happened that were outside of your control?",
                "In the last month, how often have you felt difficulties were piling up so high that you could not overcome them?"
            ]
            
            # PSS-10 reverse scoring questions (4, 5, 7, 8)
            reverse_scored = [False, False, False, True, True, False, True, True, False, False]
            
            existing_pss10_questions = self.db.query(TestQuestion).filter(
                TestQuestion.test_definition_id == pss10.id
            ).count()
            
            if existing_pss10_questions == 0:
                print(f"  📝 Creating {len(pss10_questions)} PSS-10 questions...")
            
            for i, (question_text, is_reverse) in enumerate(zip(pss10_questions, reverse_scored), 1):
                question = TestQuestion(
                    test_definition_id=pss10.id,
                    question_number=i,
                    question_text=question_text,
                    is_reverse_scored=is_reverse
                )
                self.db.add(question)
                self.db.flush()
                
                # Add response options for PSS-10
                options = [
                    ("Never", 0, 1.0, 1),
                    ("Almost never", 1, 1.0, 2),
                    ("Sometimes", 2, 1.0, 3),
                    ("Fairly often", 3, 1.0, 4),
                    ("Very often", 4, 1.0, 5)
                ]
                
                for option_text, option_value, weight, display_order in options:
                    option = TestQuestionOption(
                        test_definition_id=pss10.id,
                        question_id=question.id,
                        option_text=option_text,
                        option_value=option_value,
                        weight=Decimal(str(weight)),
                        display_order=display_order
                    )
                    self.db.add(option)
            
            # PSS-10 Scoring Ranges
            pss10_ranges = [
                (0, 13, "low", "Low Stress", "Good stress management", "Continue current stress management practices", "#10B981", 1),
                (14, 26, "moderate", "Moderate Stress", "Consider stress management techniques", "Learn and practice stress management techniques", "#F59E0B", 2),
                (27, 40, "high", "High Stress", "Consider professional help for stress management", "Seek professional help for stress management", "#EF4444", 3)
            ]
            
            existing_pss10_ranges = self.db.query(TestScoringRange).filter(
                TestScoringRange.test_definition_id == pss10.id
            ).count()
            
            if existing_pss10_ranges == 0:
                print(f"  📝 Creating {len(pss10_ranges)} PSS-10 scoring ranges...")
            
            for min_score, max_score, severity_level, severity_label, interpretation, recommendations, color_code, priority in pss10_ranges:
                range_obj = TestScoringRange(
                    test_definition_id=pss10.id,
                    min_score=min_score,
                    max_score=max_score,
                    severity_level=severity_level,
                    severity_label=severity_label,
                    interpretation=interpretation,
                    recommendations=recommendations,
                    color_code=color_code,
                    priority=priority
                )
                self.db.add(range_obj)
            
            self.db.commit()
            print("✅ Test definitions seeded successfully!")
            print("   - PHQ-9 (Depression): 9 questions")
            print("   - GAD-7 (Anxiety): 7 questions") 
            print("   - PSS-10 (Stress): 10 questions")
            return True
            
        except Exception as e:
            print(f"❌ Error seeding test definitions: {e}")
            self.db.rollback()
            return False
    
    def seed_test_user(self):
        """Create a test user for development"""
        try:
            print("👤 Creating test user...")
            
            # Check if test user already exists
            existing_user = self.db.query(User).filter(User.email == "test@example.com").first()
            if existing_user:
                print("  ℹ️  Test user already exists. Skipping...")
                return True
            
            # Create test user
            test_user = User(
                email="test@example.com",
                username="testuser",
                hashed_password=get_password_hash("testpassword123"),
                full_name="Test User",
                age=25,
                country="India",
                state="Maharashtra",
                city="Mumbai",
                role="user",
                is_active=True,
                is_verified=True
            )
            
            self.db.add(test_user)
            self.db.commit()
            
            print("✅ Test user created successfully!")
            print("   Email: test@example.com")
            print("   Password: testpassword123")
            print("   Role: user")
            return True
            
        except Exception as e:
            print(f"❌ Error creating test user: {e}")
            self.db.rollback()
            return False
    
    def seed_all(self):
        """Seed everything"""
        print("🌱 Seeding all data...")
        
        success = True
        success &= self.seed_test_definitions()
        success &= self.seed_test_user()
        
        if success:
            print("\n✅ All seeding completed successfully!")
        else:
            print("\n❌ Some seeding operations failed!")
        
        return success

def main():
    parser = argparse.ArgumentParser(description='Unified Seed System')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Test definitions command
    subparsers.add_parser('test-definitions', help='Seed test definitions (PHQ-9, GAD-7, PSS-10)')
    
    # Test user command
    subparsers.add_parser('test-user', help='Create a test user')
    
    # All command
    subparsers.add_parser('all', help='Seed everything')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    with SeedSystem() as seeder:
        if args.command == 'test-definitions':
            seeder.seed_test_definitions()
        elif args.command == 'test-user':
            seeder.seed_test_user()
        elif args.command == 'all':
            seeder.seed_all()

if __name__ == "__main__":
    main()
