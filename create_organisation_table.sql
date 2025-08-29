-- Create organisations table
CREATE TABLE IF NOT EXISTS organisations (
    id SERIAL PRIMARY KEY,
    org_id VARCHAR(50) UNIQUE NOT NULL,
    org_name VARCHAR(255) NOT NULL,
    hr_email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on org_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_organisations_org_id ON organisations(org_id);

-- Create index on hr_email for faster lookups
CREATE INDEX IF NOT EXISTS idx_organisations_hr_email ON organisations(hr_email); 