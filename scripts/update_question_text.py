#!/usr/bin/env python3
"""
Update Question Text Script
Updates PHQ-9 and GAD-7 question text with "Over the last 2 weeks" prefix
without deleting any existing data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import TestDefinition, TestQuestion

# Updated question texts with "Over the last 2 weeks" prefix
PHQ9_QUESTIONS = [
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

GAD7_QUESTIONS = [
    "Over the last 2 weeks, how often have you felt nervous, anxious, or on edge?",
    "Over the last 2 weeks, how often have you not been able to stop or control worrying?",
    "Over the last 2 weeks, how often have you worried too much about different things?",
    "Over the last 2 weeks, how often have you had trouble relaxing?",
    "Over the last 2 weeks, how often have you been so restless that it's hard to sit still?",
    "Over the last 2 weeks, how often have you become easily annoyed or irritable?",
    "Over the last 2 weeks, how often have you felt afraid as if something awful might happen?"
]

def update_questions():
    """Update question text for PHQ-9 and GAD-7"""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🔄 Updating question texts...")
        
        # Update PHQ-9 questions
        phq9 = db.query(TestDefinition).filter(TestDefinition.test_code == "phq9").first()
        if phq9:
            print(f"\n📝 Updating PHQ-9 questions (ID: {phq9.id})...")
            questions = db.query(TestQuestion).filter(
                TestQuestion.test_definition_id == phq9.id
            ).order_by(TestQuestion.question_number).all()
            
            if len(questions) != len(PHQ9_QUESTIONS):
                print(f"⚠️  Warning: Found {len(questions)} PHQ-9 questions, expected {len(PHQ9_QUESTIONS)}")
            
            for i, question in enumerate(questions):
                if i < len(PHQ9_QUESTIONS):
                    old_text = question.question_text
                    question.question_text = PHQ9_QUESTIONS[i]
                    print(f"  ✅ Q{question.question_number}: Updated")
                    print(f"     Old: {old_text[:60]}...")
                    print(f"     New: {PHQ9_QUESTIONS[i][:60]}...")
                else:
                    print(f"  ⚠️  Q{question.question_number}: Skipped (no new text available)")
        else:
            print("⚠️  PHQ-9 test definition not found")
        
        # Update GAD-7 questions
        gad7 = db.query(TestDefinition).filter(TestDefinition.test_code == "gad7").first()
        if gad7:
            print(f"\n📝 Updating GAD-7 questions (ID: {gad7.id})...")
            questions = db.query(TestQuestion).filter(
                TestQuestion.test_definition_id == gad7.id
            ).order_by(TestQuestion.question_number).all()
            
            if len(questions) != len(GAD7_QUESTIONS):
                print(f"⚠️  Warning: Found {len(questions)} GAD-7 questions, expected {len(GAD7_QUESTIONS)}")
            
            for i, question in enumerate(questions):
                if i < len(GAD7_QUESTIONS):
                    old_text = question.question_text
                    question.question_text = GAD7_QUESTIONS[i]
                    print(f"  ✅ Q{question.question_number}: Updated")
                    print(f"     Old: {old_text[:60]}...")
                    print(f"     New: {GAD7_QUESTIONS[i][:60]}...")
                else:
                    print(f"  ⚠️  Q{question.question_number}: Skipped (no new text available)")
        else:
            print("⚠️  GAD-7 test definition not found")
        
        db.commit()
        print("\n✅ Question texts updated successfully!")
        print("\n💡 Note: You've already deleted the other tables (test_question_options, test_scoring_ranges).")
        print("   If you need those, run: python scripts/seed_system.py test-definitions")
        
    except Exception as e:
        print(f"\n❌ Error updating questions: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_questions()

