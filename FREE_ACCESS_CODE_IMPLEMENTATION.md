# Free Access Code Implementation Guide

## 🎯 Overview

This implementation allows logged-in users to generate a **one-time free basic access code** (10 messages) instead of automatically receiving a free plan. The button shows once, and after generation, displays the access code permanently.

---

## 📊 What Changed

### 1. **New Database Table: `user_free_service`**

Tracks which users have generated their free access code.

**Schema:**
```sql
CREATE TABLE user_free_service (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,  -- One per user
    access_code VARCHAR(20) NOT NULL,  -- e.g., BASIC-A1B2C3D4
    subscription_token VARCHAR(255) NOT NULL,
    plan_type VARCHAR(20) DEFAULT 'basic',
    has_used BOOLEAN DEFAULT TRUE,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes:**
- `ix_user_free_service_user_id` (unique) - Fast user lookups
- `ix_user_free_service_access_code` - Fast access code lookups

---

### 2. **Modified Routes**

#### **`POST /api/session-chat/subscribe`** ✅ NOW REQUIRES AUTH
```python
# Before: Anyone could call
# After: Requires authentication

Headers:
  Authorization: Bearer <access_token>
  
Body:
  {
    "plan_type": "free" | "basic" | "premium"
  }
```

#### **`POST /api/session-chat/generate-free-access`** ✨ NEW ROUTE
```python
# Generates one-time free basic access code for logged-in user

Headers:
  Authorization: Bearer <access_token>

Response (First time):
  {
    "success": true,
    "already_generated": false,
    "message": "Free access code generated successfully",
    "access_code": "BASIC-A1B2C3D4",
    "plan_type": "basic",
    "message_limit": 10,
    "generated_at": "2025-10-12T20:00:00Z"
  }

Response (Already generated):
  {
    "success": true,
    "already_generated": true,
    "message": "You already have a free access code",
    "access_code": "BASIC-A1B2C3D4",  // Same code
    "plan_type": "basic",
    "message_limit": 10,
    "generated_at": "2025-10-12T20:00:00Z"
  }
```

---

## 🚀 How to Deploy

### Step 1: Run Migration

```bash
cd backend

# Run the migration to create the table
alembic upgrade head

# Verify migration
alembic current
# Should show: f9a8b7c6d5e4 (head)
```

### Step 2: Restart Backend

```bash
# If using start.sh
./start.sh

# Or manually
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🎨 Frontend Implementation

### **React/TypeScript Example**

```typescript
import { useState, useEffect } from 'react';

interface FreeAccessData {
  success: boolean;
  already_generated: boolean;
  message: string;
  access_code: string;
  plan_type: string;
  message_limit: number;
  generated_at: string;
}

function FreeAccessButton() {
  const [accessData, setAccessData] = useState<FreeAccessData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const token = localStorage.getItem('access_token'); // Your auth token

  const generateFreeAccess = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/session-chat/generate-free-access', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate access code');
      }
      
      const data: FreeAccessData = await response.json();
      setAccessData(data);
      
      // Optionally save to local storage
      localStorage.setItem('user_access_code', data.access_code);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="free-access-container">
      {!accessData ? (
        // Show button if no access code yet
        <button 
          onClick={generateFreeAccess} 
          disabled={loading}
          className="generate-button"
        >
          {loading ? 'Generating...' : 'Generate Free Access Code'}
        </button>
      ) : (
        // Show access code after generation
        <div className="access-code-display">
          <h3>Your Free Access Code:</h3>
          <div className="code-box">
            <code>{accessData.access_code}</code>
            <button onClick={() => navigator.clipboard.writeText(accessData.access_code)}>
              Copy
            </button>
          </div>
          <p>Plan: {accessData.plan_type} ({accessData.message_limit} messages)</p>
          <p className="hint">Use this code to start chatting with Acutie!</p>
        </div>
      )}
      
      {error && <p className="error">{error}</p>}
    </div>
  );
}

export default FreeAccessButton;
```

### **Using the Access Code**

After getting the access code, users need to:

1. **Validate the code:**
```typescript
const validateCode = async (accessCode: string) => {
  const response = await fetch('/api/session-chat/access-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ access_code: accessCode })
  });
  
  const data = await response.json();
  // data.subscription_token needed for next step
  return data;
};
```

2. **Link session to subscription:**
```typescript
const linkSession = async (sessionId: string, subscriptionToken: string) => {
  const response = await fetch('/api/session-chat/link-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_identifier: sessionId,
      subscription_token: subscriptionToken
    })
  });
  
  return await response.json();
};
```

3. **Start chatting with the linked session**

---

## 🔐 Security Features

✅ **Authentication Required:** Only logged-in users can generate codes  
✅ **One Per User:** `user_id` is unique in the table  
✅ **Cannot Regenerate:** Returns existing code on subsequent calls  
✅ **Protected Routes:** `/subscribe` now requires authentication  

---

## 📊 Database Query Examples

### Check if user has generated free access
```sql
SELECT * FROM user_free_service WHERE user_id = 123;
```

### Get all users who generated free access
```sql
SELECT u.email, u.full_name, ufs.access_code, ufs.generated_at
FROM users u
JOIN user_free_service ufs ON u.id = ufs.user_id
ORDER BY ufs.generated_at DESC;
```

### Count total free access codes generated
```sql
SELECT COUNT(*) FROM user_free_service;
```

### Check subscription details for a free access code
```sql
SELECT s.*, ufs.user_id, u.email
FROM subscriptions s
JOIN user_free_service ufs ON s.subscription_token = ufs.subscription_token
JOIN users u ON ufs.user_id = u.id
WHERE ufs.access_code = 'BASIC-A1B2C3D4';
```

---

## 🧪 Testing

### Test 1: Generate Free Access (First Time)
```bash
curl -X POST http://localhost:8000/api/session-chat/generate-free-access \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected:** 
- `"already_generated": false`
- New access code returned
- Entry created in `user_free_service` table

### Test 2: Generate Again (Already Generated)
```bash
# Same request as above
```

**Expected:**
- `"already_generated": true`
- Same access code returned
- No new entry in database

### Test 3: Verify Authentication Required
```bash
curl -X POST http://localhost:8000/api/session-chat/generate-free-access \
  -H "Content-Type: application/json"
```

**Expected:** `401 Unauthorized` error

---

## 🎯 User Flow

```
1. User logs in → Gets access_token
2. Frontend calls /generate-free-access with token
3. Backend checks user_free_service table:
   ├─ If exists → Return existing access code
   └─ If not → Create basic subscription → Save to table → Return new code
4. Frontend displays access code (button disappears)
5. User copies code
6. User validates code → Gets subscription_token
7. User links session to subscription
8. User can chat (10 messages)
```

---

## 🛠️ Rollback (If Needed)

```bash
# Rollback migration
alembic downgrade -1

# This will:
# - Drop user_free_service table
# - Drop indexes
# - Revert to previous state
```

---

## 📝 Notes

1. **Basic Plan:** 10 messages, expires in 30 days
2. **User ID Unique:** One free access per user (enforced by database)
3. **No Auto Free Plans:** Old automatic free plan creation removed
4. **Subscription Reusable:** Access code can be used on multiple devices
5. **Logged in Required:** Anonymous users cannot generate codes

---

## ✅ Files Modified

1. **Migration:** `/backend/alembic/versions/f9a8b7c6d5e4_add_user_free_service_table.py`
2. **Model:** `/backend/app/models.py` (added `UserFreeService`)
3. **Router:** `/backend/app/routers/session_chat.py`
   - Modified `/subscribe` (added auth)
   - Added `/generate-free-access` (new endpoint)

---

## 🎉 Done!

Your implementation is complete. Users can now:
- ✅ Generate one-time free basic access codes
- ✅ See their code instead of a button after generation
- ✅ Use the code to chat (10 messages, 30 days validity)
- ✅ Cannot abuse the system (one per user)

**Next Steps:**
1. Run migration: `alembic upgrade head`
2. Restart backend
3. Implement frontend button
4. Test the flow
5. Deploy to production! 🚀

