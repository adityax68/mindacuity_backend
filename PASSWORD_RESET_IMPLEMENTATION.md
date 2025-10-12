# Password Reset Implementation Guide

## 🎉 Implementation Complete!

The password reset functionality is now fully implemented and ready to use!

## 📋 What Was Implemented

### 1. **Database Schema** ✅
Added 4 new fields to the `users` table:
- `password_reset_token` - Stores the unique reset token
- `password_reset_expires_at` - Token expiration timestamp (1 hour)
- `password_reset_attempts` - Rate limiting counter
- `last_reset_attempt` - Timestamp of last attempt

**Migration:** `abdaa4f06ec2_add_password_reset_fields.py`

### 2. **Pydantic Schemas** ✅
Added to `backend/app/schemas.py`:
- `ForgotPasswordRequest` - Email input
- `ForgotPasswordResponse` - Success/error message
- `ResetPasswordRequest` - Token + new password
- `ResetPasswordResponse` - Success confirmation

### 3. **CRUD Operations** ✅
Added to `backend/app/crud.py`:
- `set_password_reset_token()` - Generate and store token
- `get_user_by_reset_token()` - Validate token and check expiration
- `reset_user_password()` - Update password and clear token
- `clear_password_reset_token()` - Clear token manually

### 4. **API Endpoints** ✅
Added to `backend/app/routers/auth.py`:

#### `POST /api/v1/auth/forgot-password`
- Accepts email address
- Generates secure token (expires in 1 hour)
- Sends password reset email
- Rate limited: 3 attempts per hour
- **Security:** Always returns success to prevent email enumeration

#### `POST /api/v1/auth/reset-password`
- Accepts token + new_password
- Validates token (checks expiration)
- Updates user password
- Clears reset token
- Returns success/error message

### 5. **Email Template** ✅
Updated `backend/app/services/email_utils.py`:
- Uses configurable frontend URL from settings
- Beautiful HTML email template
- Includes reset link with token
- Clear expiration notice (1 hour)

### 6. **Configuration** ✅
Added to `backend/app/config.py`:
- `FRONTEND_URL` environment variable
- Default: `http://localhost:5173`
- Production: Set in `.env` file

---

## 🚀 How to Use

### For Users (Frontend Flow)

1. **Click "Forgot Password"** on login page
2. **Enter email address**
3. **Check email** for reset link
4. **Click link** → Redirected to `/reset-password?token=...`
5. **Enter new password** (with confirmation)
6. **Submit** → Password updated!
7. **Login** with new password

### For Developers (API Usage)

#### Step 1: Request Password Reset
```bash
POST /api/v1/auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "If an account with that email exists, a password reset link has been sent."
}
```

#### Step 2: Reset Password
```bash
POST /api/v1/auth/reset-password
Content-Type: application/json

{
  "token": "abc123def456...",
  "new_password": "newSecurePassword123"
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Password has been reset successfully. You can now login with your new password."
}
```

**Error Response:**
```json
{
  "detail": "Invalid or expired password reset token. Please request a new password reset link."
}
```

---

## 🔒 Security Features

1. **Token Security**
   - 32-byte cryptographically secure random tokens
   - Tokens expire after 1 hour
   - Tokens are single-use (cleared after password reset)

2. **Rate Limiting**
   - Maximum 3 reset attempts per hour per user
   - Prevents brute force attacks

3. **Email Enumeration Protection**
   - Always returns success message
   - No indication whether email exists or not

4. **Password Validation**
   - 1-72 characters (bcrypt limitation)
   - Hashed with bcrypt before storage

5. **Account Status Checks**
   - Only active accounts can reset passwords
   - Inactive accounts receive generic message

---

## 🔧 Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Frontend URL for password reset links
FRONTEND_URL=https://yourdomain.com

# For development
FRONTEND_URL=http://localhost:5173
```

### Email Service

The email service uses AWS SES. Ensure these are configured:
```bash
SES_FROM_EMAIL=noreply@yourdomain.com
SES_FROM_NAME=Your App Name
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

---

## 📧 Email Template

The password reset email includes:
- Personalized greeting with user's name
- Clear subject: "Reset Your Password - Health App"
- Button with reset link
- Text version of link (for accessibility)
- Expiration warning (1 hour)
- Security notice (ignore if not requested)

Example:
```
Subject: Reset Your Password - Health App

Hello John Doe,

We received a request to reset your password for your Health App account.

[Reset Password Button]

This link will expire in 1 hour.

If you didn't request this password reset, please ignore this email.
```

---

## 🧪 Testing

### Test Forgot Password Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

### Test Reset Password Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your_reset_token_here",
    "new_password": "newPassword123"
  }'
```

### Manual Testing Steps

1. Start backend: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to login page
4. Click "Forgot Password?"
5. Enter email and submit
6. Check email inbox
7. Click reset link
8. Enter new password
9. Verify login works with new password

---

## 🐛 Troubleshooting

### Issue: Email not received
**Solutions:**
- Check spam folder
- Verify SES configuration
- Check backend logs for email service errors
- Ensure email address is verified in SES (for development)

### Issue: Token expired
**Solution:**
- Request a new password reset link
- Tokens expire after 1 hour

### Issue: Too many attempts
**Solution:**
- Wait 1 hour before trying again
- Rate limit: 3 attempts per hour

### Issue: Migration failed
**Solution:**
- Already fixed! Migration `abdaa4f06ec2` was applied successfully
- If you need to re-run: `alembic upgrade head`

---

## 📊 Database Changes

The migration added these columns to the `users` table:

```sql
ALTER TABLE users 
  ADD COLUMN password_reset_token VARCHAR,
  ADD COLUMN password_reset_expires_at TIMESTAMP WITH TIME ZONE,
  ADD COLUMN password_reset_attempts INTEGER DEFAULT 0,
  ADD COLUMN last_reset_attempt TIMESTAMP WITH TIME ZONE;

CREATE INDEX ix_users_password_reset_token ON users(password_reset_token);
```

---

## 🎨 Frontend Integration

The frontend is already fully integrated! Components exist:

1. **`ForgotPasswordForm.tsx`** - Email input form
2. **`ResetPasswordForm.tsx`** - New password form
3. **`AuthPage.tsx`** - Routing handler
4. **`App.tsx`** - Routes configured

Routes:
- `/forgot-password` - Enter email
- `/reset-password?token=...` - Set new password

---

## ✨ Next Steps

The password reset system is **ready to use**! 

### Optional Enhancements (Future):

1. **Email Templates in Database**
   - Store templates in `email_templates` table
   - Allow customization without code changes

2. **Password Strength Meter**
   - Add visual feedback in frontend
   - Require minimum complexity

3. **Multi-language Support**
   - Translate email templates
   - Support multiple languages

4. **Audit Logging**
   - Log all password reset attempts
   - Track suspicious activity

5. **2FA Integration**
   - Require 2FA verification for password reset
   - Enhanced security

---

## 📝 Summary

✅ Database schema updated and migrated  
✅ Backend endpoints implemented with security best practices  
✅ Email service integrated with configurable URLs  
✅ Frontend already implemented and ready  
✅ Rate limiting and token expiration in place  
✅ Comprehensive error handling  

**The password reset feature is now live and fully functional!** 🎉

---

## 🔗 Related Files

- `backend/app/models.py` - User model with new fields
- `backend/app/schemas.py` - Request/response schemas
- `backend/app/crud.py` - Database operations
- `backend/app/routers/auth.py` - API endpoints
- `backend/app/services/email_utils.py` - Email templates
- `backend/app/config.py` - Configuration
- `backend/alembic/versions/abdaa4f06ec2_add_password_reset_fields.py` - Migration
- `frontend/src/components/auth/ForgotPasswordForm.tsx` - Frontend form
- `frontend/src/components/auth/ResetPasswordForm.tsx` - Frontend form

---

**Questions or Issues?** Check the logs or reach out for support!





