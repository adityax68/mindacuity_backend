#!/usr/bin/env python3
"""
Add Sample Tests Script

This script adds a few more test categories to demonstrate the categorization feature.
"""

from app.database import SessionLocal
from app.models import TestDefinition, TestQuestion, TestQuestionOption, TestScoringRange
from decimal import Decimal

def add_sample_tests():
    """Add sample tests for different categories."""
    db = SessionLocal()
    
    try:
        print("🌱 Adding sample tests for categorization demo...")
        
        # Check if tests already exist
        existing_tests = db.query(TestDefinition).filter(
            TestDefinition.test_code.in_(['audit', 'dass21', 'who5'])
        ).all()
        
        if existing_tests:
            print("Sample tests already exist, skipping...")
            return
        
        # Create AUDIT test (Alcohol Use Disorders Identification Test) - Addiction category
        audit = TestDefinition(
            test_code="audit",
            test_name="AUDIT",
            test_category="addiction",
            description="Alcohol Use Disorders Identification Test: A screening tool for alcohol use disorders",
            total_questions=10,
            is_active=True
        )
        db.add(audit)
        db.flush()
        
        # AUDIT Questions (simplified)
        audit_questions = [
            "How often do you have a drink containing alcohol?",
            "How many drinks containing alcohol do you have on a typical day when you are drinking?",
            "How often do you have six or more drinks on one occasion?",
            "How often during the last year have you found that you were not able to stop drinking once you had started?",
            "How often during the last year have you failed to do what was normally expected from you because of drinking?",
            "How often during the last year have you needed a first drink in the morning to get yourself going after a heavy drinking session?",
            "How often during the last year have you had a feeling of guilt or remorse after drinking?",
            "How often during the last year have you been unable to remember what happened the night before because you had been drinking?",
            "Have you or someone else been injured as a result of your drinking?",
            "Has a relative or friend, doctor or other health worker been concerned about your drinking or suggested you cut down?"
        ]
        
        for i, question_text in enumerate(audit_questions, 1):
            question = TestQuestion(
                test_definition_id=audit.id,
                question_number=i,
                question_text=question_text,
                is_reverse_scored=False
            )
            db.add(question)
            db.flush()
            
            # Add response options for AUDIT (simplified)
            if i <= 3:  # First 3 questions have different options
                options = [
                    ("Never", 0, 1.0, 1),
                    ("Monthly or less", 1, 1.0, 2),
                    ("2-4 times a month", 2, 1.0, 3),
                    ("2-3 times a week", 3, 1.0, 4),
                    ("4 or more times a week", 4, 1.0, 5)
                ]
            else:  # Questions 4-10 have yes/no options
                options = [
                    ("Never", 0, 1.0, 1),
                    ("Less than monthly", 1, 1.0, 2),
                    ("Monthly", 2, 1.0, 3),
                    ("Weekly", 3, 1.0, 4),
                    ("Daily or almost daily", 4, 1.0, 5)
                ]
            
            for option_text, option_value, weight, display_order in options:
                option = TestQuestionOption(
                    test_definition_id=audit.id,
                    question_id=question.id,
                    option_text=option_text,
                    option_value=option_value,
                    weight=Decimal(str(weight)),
                    display_order=display_order
                )
                db.add(option)
        
        # AUDIT Scoring Ranges
        audit_ranges = [
            (0, 7, "low_risk", "Low Risk", "Low risk of alcohol problems", "Continue current drinking patterns", "#10B981", 1),
            (8, 15, "hazardous", "Hazardous Drinking", "Hazardous drinking pattern", "Consider reducing alcohol consumption", "#F59E0B", 2),
            (16, 19, "harmful", "Harmful Drinking", "Harmful drinking pattern", "Seek professional help for alcohol use", "#EF4444", 3),
            (20, 40, "dependent", "Alcohol Dependence", "Likely alcohol dependence", "Immediate professional intervention", "#DC2626", 4)
        ]
        
        for min_score, max_score, severity_level, severity_label, interpretation, recommendations, color_code, priority in audit_ranges:
            range_obj = TestScoringRange(
                test_definition_id=audit.id,
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
        
        # Create DASS-21 test (Depression, Anxiety, Stress Scale) - Multiple categories
        dass21 = TestDefinition(
            test_code="dass21",
            test_name="DASS-21",
            test_category="cognitive",
            description="Depression, Anxiety, Stress Scale-21: A comprehensive assessment of emotional states",
            total_questions=21,
            is_active=True
        )
        db.add(dass21)
        db.flush()
        
        # DASS-21 Questions (simplified - first 7 questions)
        dass21_questions = [
            "I found it hard to wind down",
            "I was aware of dryness of my mouth",
            "I couldn't seem to experience any positive feeling at all",
            "I experienced breathing difficulty (e.g., excessively rapid breathing, breathlessness in the absence of physical exertion)",
            "I found it difficult to work up the initiative to do things",
            "I tended to over-react to situations",
            "I experienced trembling (e.g., in the hands)"
        ]
        
        for i, question_text in enumerate(dass21_questions, 1):
            question = TestQuestion(
                test_definition_id=dass21.id,
                question_number=i,
                question_text=question_text,
                is_reverse_scored=False
            )
            db.add(question)
            db.flush()
            
            # Add response options for DASS-21
            options = [
                ("Did not apply to me at all", 0, 1.0, 1),
                ("Applied to me to some degree, or some of the time", 1, 1.0, 2),
                ("Applied to me to a considerable degree, or a good part of the time", 2, 1.0, 3),
                ("Applied to me very much, or most of the time", 3, 1.0, 4)
            ]
            
            for option_text, option_value, weight, display_order in options:
                option = TestQuestionOption(
                    test_definition_id=dass21.id,
                    question_id=question.id,
                    option_text=option_text,
                    option_value=option_value,
                    weight=Decimal(str(weight)),
                    display_order=display_order
                )
                db.add(option)
        
        # DASS-21 Scoring Ranges (simplified)
        dass21_ranges = [
            (0, 9, "normal", "Normal", "Normal levels of depression, anxiety, and stress", "Continue current lifestyle", "#10B981", 1),
            (10, 13, "mild", "Mild", "Mild levels of depression, anxiety, and stress", "Consider stress management techniques", "#F59E0B", 2),
            (14, 20, "moderate", "Moderate", "Moderate levels of depression, anxiety, and stress", "Seek professional help", "#EF4444", 3),
            (21, 27, "severe", "Severe", "Severe levels of depression, anxiety, and stress", "Immediate professional intervention", "#DC2626", 4)
        ]
        
        for min_score, max_score, severity_level, severity_label, interpretation, recommendations, color_code, priority in dass21_ranges:
            range_obj = TestScoringRange(
                test_definition_id=dass21.id,
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
        
        # Create WHO-5 test (World Health Organization Well-Being Index) - Social category
        who5 = TestDefinition(
            test_code="who5",
            test_name="WHO-5",
            test_category="social",
            description="World Health Organization Well-Being Index: A measure of psychological well-being",
            total_questions=5,
            is_active=True
        )
        db.add(who5)
        db.flush()
        
        # WHO-5 Questions
        who5_questions = [
            "I have felt cheerful and in good spirits",
            "I have felt calm and relaxed",
            "I have felt active and vigorous",
            "I woke up feeling fresh and rested",
            "My daily life has been filled with things that interest me"
        ]
        
        for i, question_text in enumerate(who5_questions, 1):
            question = TestQuestion(
                test_definition_id=who5.id,
                question_number=i,
                question_text=question_text,
                is_reverse_scored=False
            )
            db.add(question)
            db.flush()
            
            # Add response options for WHO-5
            options = [
                ("All of the time", 5, 1.0, 1),
                ("Most of the time", 4, 1.0, 2),
                ("More than half of the time", 3, 1.0, 3),
                ("Less than half of the time", 2, 1.0, 4),
                ("Some of the time", 1, 1.0, 5),
                ("At no time", 0, 1.0, 6)
            ]
            
            for option_text, option_value, weight, display_order in options:
                option = TestQuestionOption(
                    test_definition_id=who5.id,
                    question_id=question.id,
                    option_text=option_text,
                    option_value=option_value,
                    weight=Decimal(str(weight)),
                    display_order=display_order
                )
                db.add(option)
        
        # WHO-5 Scoring Ranges
        who5_ranges = [
            (0, 12, "poor", "Poor Well-being", "Poor psychological well-being", "Consider lifestyle changes and support", "#EF4444", 1),
            (13, 17, "below_average", "Below Average", "Below average well-being", "Focus on self-care and stress management", "#F59E0B", 2),
            (18, 22, "average", "Average", "Average psychological well-being", "Continue current practices", "#10B981", 3),
            (23, 25, "good", "Good", "Good psychological well-being", "Maintain current lifestyle", "#059669", 4)
        ]
        
        for min_score, max_score, severity_level, severity_label, interpretation, recommendations, color_code, priority in who5_ranges:
            range_obj = TestScoringRange(
                test_definition_id=who5.id,
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
        print("✅ Sample tests added successfully!")
        print("   - AUDIT (Addiction): 10 questions")
        print("   - DASS-21 (Cognitive): 7 questions") 
        print("   - WHO-5 (Social): 5 questions")
        
    except Exception as e:
        print(f"❌ Error adding sample tests: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_sample_tests()
