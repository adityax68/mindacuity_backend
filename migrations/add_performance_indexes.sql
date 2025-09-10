-- Performance Optimization Indexes
-- This migration adds critical indexes for performance without changing business logic

-- =============================================
-- USER PERFORMANCE INDEXES
-- =============================================

-- Optimize user lookups by email (most common query)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active 
ON users(email) 
WHERE is_active = true;

-- Optimize user lookups by role
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role 
ON users(role);

-- Optimize user lookups by creation date (for admin lists)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at 
ON users(created_at DESC);

-- Composite index for user filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role_active_created 
ON users(role, is_active, created_at DESC);

-- =============================================
-- CHAT PERFORMANCE INDEXES
-- =============================================

-- Optimize conversation lookups by user
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_conversations_user_updated 
ON chat_conversations(user_id, updated_at DESC);

-- Optimize message lookups by conversation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_conversation_created 
ON chat_messages(conversation_id, created_at ASC);

-- Optimize message lookups by user
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_messages_user_created 
ON chat_messages(user_id, created_at DESC);

-- Optimize rate limiting queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rate_limits_user_window 
ON rate_limits(user_id, window_start);

-- Optimize attachment lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_attachments_user_created 
ON chat_attachments(user_id, created_at DESC);

-- Optimize attachment processing status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_attachments_processed 
ON chat_attachments(is_processed, created_at);

-- =============================================
-- ROLE & PRIVILEGE PERFORMANCE INDEXES
-- =============================================

-- Optimize role privilege lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_role_privileges_role 
ON role_privileges(role_id);

-- Optimize user privilege lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_privileges_user 
ON user_privileges(user_id);

-- Optimize privilege lookups by name
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_privileges_name_active 
ON privileges(name) 
WHERE is_active = true;

-- =============================================
-- ASSESSMENT PERFORMANCE INDEXES
-- =============================================

-- Optimize clinical assessment lookups by user
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_clinical_assessments_user_created 
ON clinical_assessments(user_id, created_at DESC);

-- Optimize assessment lookups by type
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_clinical_assessments_type_created 
ON clinical_assessments(assessment_type, created_at DESC);

-- =============================================
-- COMPLAINT PERFORMANCE INDEXES
-- =============================================

-- Optimize complaint lookups by employee
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_employee_created 
ON complaints(employee_id, created_at DESC);

-- Optimize complaint lookups by HR
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_hr_created 
ON complaints(hr_email, created_at DESC);

-- Optimize complaint lookups by organization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_org_created 
ON complaints(org_id, created_at DESC);

-- Optimize complaint status filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_status_created 
ON complaints(status, created_at DESC);

-- =============================================
-- EMPLOYEE PERFORMANCE INDEXES
-- =============================================

-- Optimize employee lookups by HR
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_employees_hr_email 
ON employees(hr_email);

-- Optimize employee lookups by organization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_employees_org_id 
ON employees(org_id);

-- Optimize employee lookups by user
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_employees_user_id 
ON employees(user_id);

-- =============================================
-- ORGANIZATION PERFORMANCE INDEXES
-- =============================================

-- Optimize organization lookups by name
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organisations_name 
ON organisations(name);

-- Optimize organization lookups by status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organisations_status_created 
ON organisations(is_active, created_at DESC);

-- =============================================
-- TEST PERFORMANCE INDEXES (if not already added)
-- =============================================

-- Optimize test definition lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_test_definitions_code_active 
ON test_definitions(test_code) 
WHERE is_active = true;

-- Optimize test question lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_test_questions_definition_number 
ON test_questions(test_definition_id, question_number);

-- Optimize test option lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_test_question_options_question_display 
ON test_question_options(question_id, display_order);

-- Optimize test scoring range lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_test_scoring_ranges_definition_priority 
ON test_scoring_ranges(test_definition_id, priority);

-- =============================================
-- ANALYZE TABLES FOR OPTIMIZATION
-- =============================================

-- Update table statistics for better query planning
ANALYZE users;
ANALYZE chat_conversations;
ANALYZE chat_messages;
ANALYZE rate_limits;
ANALYZE chat_attachments;
ANALYZE role_privileges;
ANALYZE user_privileges;
ANALYZE privileges;
ANALYZE clinical_assessments;
ANALYZE complaints;
ANALYZE employees;
ANALYZE organisations;
ANALYZE test_definitions;
ANALYZE test_questions;
ANALYZE test_question_options;
ANALYZE test_scoring_ranges;
