# Clinical Mental Health Assessment API

A FastAPI-based backend for clinical mental health assessment using validated scales. This API provides comprehensive mental health evaluation capabilities with user authentication and assessment history tracking.

## Features

- **Clinical Assessment Scales**: Validated scales (PHQ-9, GAD-7, PSS-10) for accurate mental health evaluation
- **User Authentication**: JWT-based authentication with signup/login functionality
- **Assessment History**: Track and analyze mental health trends over time
- **Anonymous Assessment**: Quick assessment without account creation
- **Comprehensive Scoring**: Clinically validated scoring and interpretation
- **RESTful API**: Well-documented endpoints with automatic documentation

## Expected Accuracy

**Clinical Assessment Scales Performance:**
- **PHQ-9 (Depression)**: 88-94% sensitivity and specificity for depression screening
- **GAD-7 (Anxiety)**: 89-92% sensitivity and specificity for anxiety screening
- **PSS-10 (Stress)**: 85-90% reliability for stress assessment
- **Validated Severity Levels**: Clinically validated cut-off scores and interpretations

*Note: This is a screening tool and should not replace professional mental health evaluation.*

## Database Recommendation

**Recommended Database: PostgreSQL**

**Why PostgreSQL:**
- Excellent support for JSON data types (useful for storing analysis metadata)
- Robust indexing for fast user assessment queries
- ACID compliance for data integrity
- Excellent performance for read-heavy workloads
- Rich ecosystem and community support

**Alternative Options:**
- **SQLite**: Good for development/testing, not recommended for production
- **MySQL**: Viable alternative, good performance
- **MongoDB**: If you prefer NoSQL, good for flexible schema

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd stealthbackend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the root directory:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost/mental_health_db

# JWT Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Mental Health Detection API
```

### 5. Database Setup

#### Option A: PostgreSQL (Recommended)

1. Install PostgreSQL
2. Create database:
```sql
CREATE DATABASE mental_health_db;
```

3. Update the `DATABASE_URL` in your `.env` file with your connection string

#### Option B: SQLite (Development)

Update `app/config.py`:
```python
database_url: str = "sqlite:///./mental_health.db"
```

### 6. Run the Application

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 7. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication

- `POST /api/v1/auth/signup` - Create new user account
- `POST /api/v1/auth/login` - Authenticate and get access token
- `GET /api/v1/auth/me` - Get current user information

### Clinical Assessments (Validated Scales)

- `GET /api/v1/clinical/questions/{assessment_type}` - Get questions for PHQ-9, GAD-7, or PSS-10
- `POST /api/v1/clinical/assess` - Perform clinical assessment (requires authentication)
- `POST /api/v1/clinical/assess-anonymous` - Anonymous clinical assessment (no auth required)
- `GET /api/v1/clinical/my-assessments` - Get user's clinical assessment history
- `GET /api/v1/clinical/summary` - Get clinical assessment summary statistics
- `GET /api/v1/clinical/{assessment_id}` - Get specific clinical assessment
- `DELETE /api/v1/clinical/{assessment_id}` - Delete clinical assessment

### Health Check

- `GET /` - API information
- `GET /health` - Health check endpoint

## Usage Examples

### 1. User Registration

```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "username": "testuser",
       "password": "securepassword123",
       "full_name": "Test User"
     }'
```

### 2. User Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=user@example.com&password=securepassword123"
```

### 3. Clinical Assessment

```bash
curl -X POST "http://localhost:8000/api/v1/clinical/assess" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "assessment_type": "phq9",
       "responses": [
         {"question_id": 1, "response": 2},
         {"question_id": 2, "response": 1},
         {"question_id": 3, "response": 3},
         {"question_id": 4, "response": 2},
         {"question_id": 5, "response": 1},
         {"question_id": 6, "response": 0},
         {"question_id": 7, "response": 2},
         {"question_id": 8, "response": 1},
         {"question_id": 9, "response": 0}
       ]
     }'
```

### 4. Anonymous Clinical Assessment

```bash
curl -X POST "http://localhost:8000/api/v1/clinical/assess-anonymous" \
     -H "Content-Type: application/json" \
     -d '{
       "assessment_type": "gad7",
       "responses": [
         {"question_id": 1, "response": 2},
         {"question_id": 2, "response": 1},
         {"question_id": 3, "response": 3},
         {"question_id": 4, "response": 2},
         {"question_id": 5, "response": 1},
         {"question_id": 6, "response": 0},
         {"question_id": 7, "response": 2}
       ]
     }'
```

## Project Structure

```
stealthbackend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication utilities
│   ├── crud.py              # Database operations
│   ├── clinical_assessments.py  # Clinical assessment engine
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # Authentication routes
│       └── clinical.py      # Clinical assessment routes
├── alembic.ini              # Database migration config
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Clinical Assessment Details

The clinical assessment system uses validated scales:

1. **PHQ-9 (Patient Health Questionnaire-9)**: 9-item depression screening tool
2. **GAD-7 (Generalized Anxiety Disorder-7)**: 7-item anxiety screening tool
3. **PSS-10 (Perceived Stress Scale-10)**: 10-item stress assessment tool
4. **Severity Levels**: Clinically validated cut-off scores and interpretations
5. **Scoring Algorithms**: Standardized scoring methods for each scale
6. **Interpretation Guidelines**: Evidence-based interpretation of results

## Security Considerations

- Passwords are hashed using bcrypt
- JWT tokens with configurable expiration
- Input validation and sanitization
- CORS configuration (update for production)
- Environment variable configuration

## Production Deployment

1. **Update CORS settings** in `app/main.py`
2. **Use strong secret keys** in environment variables
3. **Configure proper database connection pooling**
4. **Set up reverse proxy** (nginx/Apache)
5. **Enable HTTPS**
6. **Set up monitoring and logging**
7. **Configure backup strategies**

## Future Enhancements

- Additional clinical scales (BDI, STAI, etc.)
- Machine learning model integration
- Real-time assessment capabilities
- Mobile app support
- Professional consultation booking
- Crisis intervention features
- Multi-language support
- Integration with electronic health records
- Advanced admin dashboard features

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Disclaimer

This API is designed for educational and screening purposes only. It should not be used as a substitute for professional mental health evaluation, diagnosis, or treatment. Always consult with qualified mental health professionals for proper assessment and care. 