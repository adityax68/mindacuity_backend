-- Add indexes for search optimization
-- This will significantly improve search performance

-- User table indexes for email search
CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users (LOWER(email));
CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);

-- Employee table indexes for employee_code search
CREATE INDEX IF NOT EXISTS idx_employees_employee_code_lower ON employees (LOWER(employee_code));
CREATE INDEX IF NOT EXISTS idx_employees_org_id ON employees (org_id);
CREATE INDEX IF NOT EXISTS idx_employees_hr_email_lower ON employees (LOWER(hr_email));
CREATE INDEX IF NOT EXISTS idx_employees_is_active ON employees (is_active);
CREATE INDEX IF NOT EXISTS idx_employees_created_at ON employees (created_at);

-- Organisation table indexes for org_id and hr_email search
CREATE INDEX IF NOT EXISTS idx_organisations_org_id_lower ON organisations (LOWER(org_id));
CREATE INDEX IF NOT EXISTS idx_organisations_hr_email_lower ON organisations (LOWER(hr_email));
CREATE INDEX IF NOT EXISTS idx_organisations_created_at ON organisations (created_at);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_users_role_active ON users (role, is_active);
CREATE INDEX IF NOT EXISTS idx_employees_org_active ON employees (org_id, is_active);
