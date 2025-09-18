# Chat System Setup Guide

## Environment Variables Required

Add these to your `.env` file:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Encryption Key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-encryption-key-here
```

## Generate Encryption Key

Run this command to generate a secure encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Database Migration

The chat system will automatically create the required tables when you start the application.

## Features

- **Rate Limiting**: 20 messages per minute per user
- **Message Encryption**: All messages are encrypted using AES-256
- **Conversation Management**: Users can have multiple conversations
- **Context Awareness**: AI remembers conversation context
- **Empathy-Focused**: AI is programmed to provide emotional support

## API Endpoints

- `POST /api/v1/chat/send` - Send a message
- `GET /api/v1/chat/conversations` - Get user conversations
- `GET /api/v1/chat/conversations/{id}/messages` - Get conversation messages
- `DELETE /api/v1/chat/conversations/{id}` - Delete conversation
- `GET /api/v1/chat/health` - Health check

## Testing

1. Start the backend server
2. Sign in to the frontend
3. Click the chat icon (bottom-right)
4. Start chatting with the AI companion

## Rate Limits

- **Messages per minute**: 20
- **Rate limit window**: 1 minute
- **Storage**: PostgreSQL with encryption 