-- Add user profile fields to users table
-- Migration: Add age (mandatory), country, state, city, pincode (optional)

-- Add new columns to users table
ALTER TABLE users ADD COLUMN age INTEGER;
ALTER TABLE users ADD COLUMN country VARCHAR(100);
ALTER TABLE users ADD COLUMN state VARCHAR(100);
ALTER TABLE users ADD COLUMN city VARCHAR(100);
ALTER TABLE users ADD COLUMN pincode VARCHAR(20);

-- Update existing users with a default age (you may want to adjust this)
-- This is a temporary solution - in production, you might want to handle this differently
UPDATE users SET age = 25 WHERE age IS NULL;

-- Make age column NOT NULL after setting default values
ALTER TABLE users ALTER COLUMN age SET NOT NULL;

-- Add indexes for better query performance
CREATE INDEX idx_users_country ON users(country);
CREATE INDEX idx_users_state ON users(state);
CREATE INDEX idx_users_city ON users(city);
