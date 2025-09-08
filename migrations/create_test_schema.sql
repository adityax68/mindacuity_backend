-- Migration: Create new test schema for separate assessments
-- This migration creates the new test structure with separate tests for PHQ-9, GAD-7, and PSS-10

-- Create test_definitions table
CREATE TABLE IF NOT EXISTS test_definitions (
    id SERIAL PRIMARY KEY,
    test_code VARCHAR(50) UNIQUE NOT NULL,
    test_name VARCHAR(100) NOT NULL,
    test_category VARCHAR(50) NOT NULL,
    description TEXT,
    total_questions INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create test_questions table
CREATE TABLE IF NOT EXISTS test_questions (
    id SERIAL PRIMARY KEY,
    test_definition_id INTEGER REFERENCES test_definitions(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    is_reverse_scored BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create test_question_options table
CREATE TABLE IF NOT EXISTS test_question_options (
    id SERIAL PRIMARY KEY,
    test_definition_id INTEGER REFERENCES test_definitions(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES test_questions(id) ON DELETE CASCADE,
    option_text VARCHAR(200) NOT NULL,
    option_value INTEGER NOT NULL,
    weight DECIMAL(3,2) DEFAULT 1.0,
    display_order INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create test_scoring_ranges table
CREATE TABLE IF NOT EXISTS test_scoring_ranges (
    id SERIAL PRIMARY KEY,
    test_definition_id INTEGER REFERENCES test_definitions(id) ON DELETE CASCADE,
    min_score INTEGER NOT NULL,
    max_score INTEGER NOT NULL,
    severity_level VARCHAR(50) NOT NULL,
    severity_label VARCHAR(100) NOT NULL,
    interpretation TEXT NOT NULL,
    recommendations TEXT,
    color_code VARCHAR(7),
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Update existing clinical_assessments table
ALTER TABLE clinical_assessments 
ADD COLUMN IF NOT EXISTS test_definition_id INTEGER REFERENCES test_definitions(id),
ADD COLUMN IF NOT EXISTS test_category VARCHAR(50),
ADD COLUMN IF NOT EXISTS raw_responses JSON,
ADD COLUMN IF NOT EXISTS calculated_score INTEGER,
ADD COLUMN IF NOT EXISTS severity_level VARCHAR(50),
ADD COLUMN IF NOT EXISTS severity_label VARCHAR(100);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_test_questions_test_definition_id ON test_questions(test_definition_id);
CREATE INDEX IF NOT EXISTS idx_test_question_options_test_definition_id ON test_question_options(test_definition_id);
CREATE INDEX IF NOT EXISTS idx_test_question_options_question_id ON test_question_options(question_id);
CREATE INDEX IF NOT EXISTS idx_test_scoring_ranges_test_definition_id ON test_scoring_ranges(test_definition_id);
CREATE INDEX IF NOT EXISTS idx_clinical_assessments_test_definition_id ON clinical_assessments(test_definition_id);
CREATE INDEX IF NOT EXISTS idx_clinical_assessments_test_category ON clinical_assessments(test_category);
