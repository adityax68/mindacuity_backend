-- Fix the updated_at column to have a default value
ALTER TABLE organisations 
ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;

-- Update existing records that have NULL updated_at
UPDATE organisations 
SET updated_at = created_at 
WHERE updated_at IS NULL; 