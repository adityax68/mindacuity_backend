#!/usr/bin/env python3
"""
Seed Test Definitions Script

This script creates the test definitions for PHQ-9, GAD-7, and PSS-10 tests
with all questions, options, and scoring ranges.
"""

from app.database import SessionLocal
from app.models import TestDefinition, TestQuestion, TestQuestionOption, TestScoringRange
from decimal import Decimal

def seed_test_definitions():
    """Seed the database with test definitions."""
    db = SessionLocal()
    
    try:
        print("🌱 Seeding test definitions...")
        
        # Create PHQ-9 test definition
        phq9 = TestDefinition(
            test_code="phq9",
            test_name="PHQ-9",
            test_category="depression",
            description="Patient Health Questionnaire-9: A validated tool for assessing depression severity",
            total_questions=9,
            is_active=True
        )
        db.add(phq9)
        db.flush()  # Get the ID
        
        # PHQ-9 Questions
        phq9_questions = [
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
            "Trouble falling or staying asleep, or sleeping too much",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            "Feeling bad about yourself - or that you are a failure or have let yourself or your family down",
            "Trouble concentrating on things, such as reading the newspaper or watching television",
            "Moving or speaking slowly enough that other people could have noticed. Or the opposite - being so fidgety or restless that you have been moving around a lot more than usual",
            "Thoughts that you would be better off dead or of hurting yourself in some way"
        ]
        
        for i, question_text in enumerate(phq9_questions, 1):
            question = TestQuestion(
                test_definition_id=phq9.id,
                question_number=i,
                question_text=question_text,
                is_reverse_scored=False
            )
            db.add(question)
            db.flush()
            
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
                db.add(option)
        
        # PHQ-9 Scoring Ranges
        phq9_ranges = [
            (0, 4, "minimal", "Minimal Depression", "No treatment needed", "Continue monitoring mental health", "#10B981", 1),
            (5, 9, "mild", "Mild Depression", "Watchful waiting; repeat PHQ-9", "Consider counseling or therapy", "#F59E0B", 2),
            (10, 14, "moderate", "Moderate Depression", "Treatment plan, counseling, follow-up", "Seek professional help", "#EF4444", 3),
            (15, 19, "moderately_severe", "Moderately Severe Depression", "Active treatment with medication and/or therapy", "Immediate professional consultation", "#DC2626", 4),
            (20, 27, "severe", "Severe Depression", "Immediate treatment, medication and therapy", "Urgent professional intervention", "#991B1B", 5)
        ]
        
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
            db.add(range_obj)
        
        # Create GAD-7 test definition
        gad7 = TestDefinition(
            test_code="gad7",
            test_name="GAD-7",
            test_category="anxiety",
            description="Generalized Anxiety Disorder-7: A validated tool for assessing anxiety severity",
            total_questions=7,
            is_active=True
        )
        db.add(gad7)
        db.flush()
        
        # GAD-7 Questions
        gad7_questions = [
            "Feeling nervous, anxious, or on edge",
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it's hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid as if something awful might happen"
        ]
        
        for i, question_text in enumerate(gad7_questions, 1):
            question = TestQuestion(
                test_definition_id=gad7.id,
                question_number=i,
                question_text=question_text,
                is_reverse_scored=False
            )
            db.add(question)
            db.flush()
            
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
                db.add(option)
        
        # GAD-7 Scoring Ranges
        gad7_ranges = [
            (0, 4, "minimal", "Minimal Anxiety", "No treatment needed", "Continue monitoring mental health", "#10B981", 1),
            (5, 9, "mild", "Mild Anxiety", "Watchful waiting; repeat GAD-7", "Consider stress management techniques", "#F59E0B", 2),
            (10, 14, "moderate", "Moderate Anxiety", "Treatment plan, counseling, follow-up", "Seek professional help", "#EF4444", 3),
            (15, 21, "severe", "Severe Anxiety", "Active treatment with medication and/or therapy", "Immediate professional consultation", "#DC2626", 4)
        ]
        
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
            db.add(range_obj)
        
        # Create PSS-10 test definition
        pss10 = TestDefinition(
            test_code="pss10",
            test_name="PSS-10",
            test_category="stress",
            description="Perceived Stress Scale-10: A validated tool for assessing stress levels",
            total_questions=10,
            is_active=True
        )
        db.add(pss10)
        db.flush()
        
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
        
        for i, (question_text, is_reverse) in enumerate(zip(pss10_questions, reverse_scored), 1):
            question = TestQuestion(
                test_definition_id=pss10.id,
                question_number=i,
                question_text=question_text,
                is_reverse_scored=is_reverse
            )
            db.add(question)
            db.flush()
            
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
                db.add(option)
        
        # PSS-10 Scoring Ranges
        pss10_ranges = [
            (0, 13, "low", "Low Stress", "Good stress management", "Continue current stress management practices", "#10B981", 1),
            (14, 26, "moderate", "Moderate Stress", "Consider stress management techniques", "Learn and practice stress management techniques", "#F59E0B", 2),
            (27, 40, "high", "High Stress", "Consider professional help for stress management", "Seek professional help for stress management", "#EF4444", 3)
        ]
        
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
            db.add(range_obj)
        
        db.commit()
        print("✅ Test definitions seeded successfully!")
        print("   - PHQ-9 (Depression): 9 questions")
        print("   - GAD-7 (Anxiety): 7 questions") 
        print("   - PSS-10 (Stress): 10 questions")
        
    except Exception as e:
        print(f"❌ Error seeding test definitions: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_definitions()
