-- Add chat_attachments table
CREATE TABLE IF NOT EXISTS chat_attachments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    upload_url VARCHAR(500),
    is_processed BOOLEAN DEFAULT FALSE,
    processed_content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Add attachment_id column to chat_messages table
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS attachment_id INTEGER REFERENCES chat_attachments(id) ON DELETE SET NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_attachments_user_id ON chat_attachments(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_attachments_expires_at ON chat_attachments(expires_at);
CREATE INDEX IF NOT EXISTS idx_chat_attachments_filename ON chat_attachments(filename);
CREATE INDEX IF NOT EXISTS idx_chat_messages_attachment_id ON chat_messages(attachment_id);
