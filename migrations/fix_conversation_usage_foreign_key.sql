-- Fix foreign key constraint to allow conversation deletion while preserving usage records
-- Drop the existing foreign key constraint
ALTER TABLE conversation_usage 
DROP CONSTRAINT IF EXISTS conversation_usage_session_identifier_fkey;

-- Add a new foreign key constraint with ON DELETE SET NULL
-- This will set session_identifier to NULL when conversation is deleted
-- but preserve the usage record and subscription data
ALTER TABLE conversation_usage 
ADD CONSTRAINT conversation_usage_session_identifier_fkey 
FOREIGN KEY (session_identifier) 
REFERENCES conversations_new(session_identifier) 
ON DELETE SET NULL;

-- Update the conversation_usage table to allow NULL session_identifier
ALTER TABLE conversation_usage 
ALTER COLUMN session_identifier DROP NOT NULL;
