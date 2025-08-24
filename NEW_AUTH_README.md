# 🚀 New Organization/Employee Authentication System

This document describes the new authentication system that has been added to the FastAPI backend to support the React frontend.

## 🔐 **Authentication Features**

### **User Types:**
- **Organizations (HR)**: Company accounts that can manage employees
- **Employees**: Individual user accounts linked to organizations

### **Security Features:**
- JWT token-based authentication
- bcrypt password hashing
- Role-based access control
- UUID primary keys for security

## 📊 **Database Schema**

### **Organizations Table**
```sql
CREATE TABLE organisations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(150) NOT NULL,
    hremail VARCHAR(150) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### **Employees Table**
```sql
CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES organisations(id) ON DELETE CASCADE,
    employee_email VARCHAR(150) NOT NULL,
    password_hash TEXT NOT NULL,
    name VARCHAR(100) NOT NULL,
    dob DATE,
    phone_number VARCHAR(20),
    joining_date DATE DEFAULT CURRENT_DATE,
    role VARCHAR(20) DEFAULT 'employee',
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🌐 **API Endpoints**

### **Base URL**: `/api/auth`

| Method | Endpoint | Description | Request Format |
|--------|----------|-------------|----------------|
| `POST` | `/organization/signup` | Create organization account | JSON |
| `POST` | `/organization/login` | Organization login | Form-encoded |
| `POST` | `/employee/signup` | Create employee account | JSON |
| `POST` | `/employee/login` | Employee login | Form-encoded |
| `GET` | `/me` | Get current user info | Bearer token |

## 📝 **Request/Response Formats**

### **Organization Signup**
```json
POST /api/auth/organization/signup
{
    "company_name": "Acme Corp",
    "hremail": "hr@acme.com",
    "password": "securepassword123"
}

Response:
{
    "access_token": "jwt_token_here",
    "user": {
        "id": "uuid",
        "company_name": "Acme Corp",
        "hremail": "hr@acme.com",
        "role": "organization_hr"
    }
}
```

### **Organization Login**
```json
POST /api/auth/organization/login
hremail=hr@acme.com&password=securepassword123

Response:
{
    "access_token": "jwt_token_here",
    "user": {
        "id": "uuid",
        "company_name": "Acme Corp",
        "hremail": "hr@acme.com",
        "role": "organization_hr"
    }
}
```

### **Employee Signup**
```json
POST /api/auth/employee/signup
{
    "company_id": "uuid",
    "employee_email": "john@acme.com",
    "password": "securepassword123",
    "name": "John Doe",
    "dob": "1990-01-01",
    "phone_number": "+1234567890",
    "joining_date": "2024-01-01"
}

Response:
{
    "access_token": "jwt_token_here",
    "user": {
        "id": "uuid",
        "company_id": "uuid",
        "employee_email": "john@acme.com",
        "name": "John Doe",
        "role": "employee"
    }
}
```

### **Employee Login**
```json
POST /api/auth/employee/login
company_id=uuid&employee_email=john@acme.com&password=securepassword123

Response:
{
    "access_token": "jwt_token": "jwt_token_here",
    "user": {
        "id": "uuid",
        "company_id": "uuid",
        "employee_email": "john@acme.com",
        "name": "John Doe",
        "role": "employee"
    }
}
```

## 🛠 **Technical Implementation**

### **Dependencies Added:**
- `asyncpg` - Async PostgreSQL driver for Neon
- Updated SQLAlchemy to use async operations

### **Key Files Modified:**
- `app/models.py` - Added Organization and Employee models
- `app/database.py` - Converted to async SQLAlchemy
- `app/schemas.py` - Added new Pydantic schemas
- `app/routers/auth.py` - Complete rewrite for new auth system
- `app/main.py` - Updated for async operations and CORS

### **Database Changes:**
- Converted from sync to async SQLAlchemy
- Added support for Neon database
- Automatic table creation on startup

## 🚀 **Getting Started**

### **1. Install Dependencies**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### **2. Set Environment Variables**
Create a `.env` file with:
```env
DATABASE_URL=postgresql://username:password@host:port/database
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=true
```

### **3. Create Database Tables**
```bash
python create_tables.py
```

### **4. Start the Server**
```bash
uvicorn app.main:app --reload
```

### **5. Test the System**
```bash
python test_new_auth.py
```

## 🔒 **Security Features**

### **Password Requirements:**
- Minimum 8 characters
- bcrypt hashing with salt

### **JWT Token Security:**
- Configurable expiration time
- User type identification in payload
- Secure secret key requirement

### **Input Validation:**
- Email format validation
- UUID validation for company IDs
- Pydantic model validation

## 🌍 **CORS Configuration**

CORS is enabled for frontend integration:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📱 **Frontend Integration**

The frontend expects these exact API endpoints and response formats. Once implemented:

1. **Organization signup** → Creates company account
2. **Organization login** → Returns JWT token
3. **Employee signup** → Creates employee account
4. **Employee login** → Returns JWT token

## 🧪 **Testing**

Use the provided test script to verify functionality:
```bash
python test_new_auth.py
```

This will test:
- Organization signup and login
- Employee signup and login
- Protected endpoint access
- JWT token validation

## 🚨 **Important Notes**

1. **API Paths Must Match Exactly**: Frontend expects `/api/auth/organization/signup`
2. **Response Format Must Match**: Frontend expects specific JSON structure
3. **CORS Must Be Enabled**: Frontend won't work without it
4. **Database Tables**: Automatically created on startup
5. **Async Operations**: All database operations are now async

## 🔄 **Migration from Old System**

The new system runs alongside the existing authentication system:
- Old endpoints remain at `/api/v1/auth/*`
- New endpoints are at `/api/auth/*`
- Both systems can coexist during transition

## 📞 **Support**

For issues or questions about the new authentication system:
1. Check the test script output
2. Verify environment variables
3. Check database connectivity
4. Review API documentation at `/docs`
