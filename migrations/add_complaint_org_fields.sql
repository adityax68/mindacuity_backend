-- Migration: Add org_id and hr_email fields to complaints table
-- Date: 2024-01-XX
-- Description: Add organization ID and HR email fields to complaints table for efficient querying

-- Add new columns to complaints table
ALTER TABLE complaints 
ADD COLUMN org_id VARCHAR(255) NULL,
ADD COLUMN hr_email VARCHAR(255) NULL;

-- Create indexes for efficient querying
CREATE INDEX idx_complaints_org_id ON complaints(org_id);
CREATE INDEX idx_complaints_hr_email ON complaints(hr_email);

-- Update existing complaints with org_id and hr_email from employee records
UPDATE complaints 
SET 
    org_id = e.org_id,
    hr_email = e.hr_email
FROM employees e
WHERE complaints.employee_id = e.id 
AND complaints.employee_id IS NOT NULL;

-- For anonymous complaints (employee_id IS NULL), we'll leave org_id and hr_email as NULL
-- These will be handled by the application logic
