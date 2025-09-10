-- Add performance indexes for test-related queries
-- This migration adds critical indexes to improve test API performance

-- Test Definitions table indexes
-- Composite index for main query: is_active + test_category + test_name ordering
CREATE INDEX IF NOT EXISTS idx_test_definitions_active_category_name 
ON test_definitions (is_active, test_category, test_name);

-- Index for category filtering (when is_active is true)
CREATE INDEX IF NOT EXISTS idx_test_definitions_category_active 
ON test_definitions (test_category) WHERE is_active = true;

-- Index for test_name ordering when filtering by category
CREATE INDEX IF NOT EXISTS idx_test_definitions_category_name 
ON test_definitions (test_category, test_name) WHERE is_active = true;

-- Test Questions table indexes
-- Composite index for ordered question queries
CREATE INDEX IF NOT EXISTS idx_test_questions_definition_number 
ON test_questions (test_definition_id, question_number);

-- Test Question Options table indexes
-- Composite index for ordered option queries
CREATE INDEX IF NOT EXISTS idx_test_question_options_question_order 
ON test_question_options (question_id, display_order);

-- Clinical Assessments table indexes
-- Composite index for user assessment history (most common query)
CREATE INDEX IF NOT EXISTS idx_clinical_assessments_user_created 
ON clinical_assessments (user_id, created_at DESC);

-- Index for user-specific test assessments
CREATE INDEX IF NOT EXISTS idx_clinical_assessments_user_test 
ON clinical_assessments (user_id, test_definition_id, created_at DESC);

-- Index for test analytics queries
CREATE INDEX IF NOT EXISTS idx_clinical_assessments_test_created 
ON clinical_assessments (test_definition_id, created_at DESC);

-- Index for severity-based analytics
CREATE INDEX IF NOT EXISTS idx_clinical_assessments_severity_test 
ON clinical_assessments (severity_level, test_definition_id) WHERE severity_level IS NOT NULL;

-- Index for test category analytics
CREATE INDEX IF NOT EXISTS idx_clinical_assessments_category_created 
ON clinical_assessments (test_category, created_at DESC) WHERE test_category IS NOT NULL;

-- Additional performance indexes for common query patterns
-- Index for active test definitions only (most queries filter by is_active)
CREATE INDEX IF NOT EXISTS idx_test_definitions_active_only 
ON test_definitions (test_code, test_name, test_category) WHERE is_active = true;

-- Index for test scoring ranges by priority (for ordered severity queries)
CREATE INDEX IF NOT EXISTS idx_test_scoring_ranges_definition_priority 
ON test_scoring_ranges (test_definition_id, priority, min_score);

-- Index for question options by test definition and display order
CREATE INDEX IF NOT EXISTS idx_test_question_options_definition_order 
ON test_question_options (test_definition_id, question_id, display_order);
