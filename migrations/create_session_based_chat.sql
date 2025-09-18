-- Migration: Create session-based chat system with subscriptions
-- This replaces the user-based chat system with anonymous session-based system

-- 1. Create new conversations table (session-based)
CREATE TABLE IF NOT EXISTS conversations_new (
    id SERIAL PRIMARY KEY,
    session_identifier VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(255) DEFAULT 'New Conversation',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);

-- 2. Create new messages table (session-based)
CREATE TABLE IF NOT EXISTS messages_new (
    id SERIAL PRIMARY KEY,
    session_identifier VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    encrypted_content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (session_identifier) REFERENCES conversations_new(session_identifier)
);

-- 3. Create subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    subscription_token VARCHAR(255) UNIQUE NOT NULL,
    access_code VARCHAR(20) UNIQUE NOT NULL,
    plan_type VARCHAR(20) NOT NULL CHECK (plan_type IN ('free', 'basic', 'premium')),
    message_limit INTEGER,
    price DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);

-- 4. Create conversation usage table
CREATE TABLE IF NOT EXISTS conversation_usage (
    id SERIAL PRIMARY KEY,
    session_identifier VARCHAR(255) NOT NULL,
    subscription_token VARCHAR(255) NOT NULL,
    messages_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    FOREIGN KEY (session_identifier) REFERENCES conversations_new(session_identifier),
    FOREIGN KEY (subscription_token) REFERENCES subscriptions(subscription_token),
    UNIQUE(session_identifier, subscription_token)
);

-- 5. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations_new(session_identifier);
CREATE INDEX IF NOT EXISTS idx_conversations_expires ON conversations_new(expires_at);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages_new(session_identifier);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages_new(created_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_token ON subscriptions(subscription_token);
CREATE INDEX IF NOT EXISTS idx_subscriptions_code ON subscriptions(access_code);
CREATE INDEX IF NOT EXISTS idx_usage_session ON conversation_usage(session_identifier);
CREATE INDEX IF NOT EXISTS idx_usage_subscription ON conversation_usage(subscription_token);

-- 6. Insert default free subscription
INSERT INTO subscriptions (subscription_token, access_code, plan_type, message_limit, price, expires_at)
VALUES ('sub_free_default', 'FREE-DEFAULT', 'free', 5, 0.00, NOW() + INTERVAL '24 hours')
ON CONFLICT (subscription_token) DO NOTHING;

-- 7. Insert basic subscription template
INSERT INTO subscriptions (subscription_token, access_code, plan_type, message_limit, price, expires_at)
VALUES ('sub_basic_template', 'BASIC-TEMPLATE', 'basic', 10, 5.00, NOW() + INTERVAL '30 days')
ON CONFLICT (subscription_token) DO NOTHING;

-- 8. Create function to generate session identifiers
CREATE OR REPLACE FUNCTION generate_session_identifier()
RETURNS TEXT AS $$
BEGIN
    RETURN 'sess_' || substr(md5(random()::text), 1, 12);
END;
$$ LANGUAGE plpgsql;

-- 9. Create function to generate access codes
CREATE OR REPLACE FUNCTION generate_access_code(plan_type TEXT)
RETURNS TEXT AS $$
BEGIN
    CASE plan_type
        WHEN 'free' THEN
            RETURN 'FREE-' || substr(md5(random()::text), 1, 8);
        WHEN 'basic' THEN
            RETURN 'BASIC-' || substr(md5(random()::text), 1, 8);
        WHEN 'premium' THEN
            RETURN 'PREMIUM-' || substr(md5(random()::text), 1, 8);
        ELSE
            RETURN 'SUB-' || substr(md5(random()::text), 1, 12);
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- 10. Create function to check usage limit
CREATE OR REPLACE FUNCTION check_usage_limit(session_id TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    current_usage INTEGER;
    max_limit INTEGER;
BEGIN
    SELECT cu.messages_used, s.message_limit
    INTO current_usage, max_limit
    FROM conversation_usage cu
    JOIN subscriptions s ON cu.subscription_token = s.subscription_token
    WHERE cu.session_identifier = session_id
    AND s.is_active = true
    AND (s.expires_at IS NULL OR s.expires_at > NOW());
    
    -- If no subscription found, return false
    IF current_usage IS NULL THEN
        RETURN false;
    END IF;
    
    -- If no limit (NULL), return true (unlimited)
    IF max_limit IS NULL THEN
        RETURN true;
    END IF;
    
    -- Check if under limit
    RETURN current_usage < max_limit;
END;
$$ LANGUAGE plpgsql;
