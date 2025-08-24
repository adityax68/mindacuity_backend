from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Union
import uuid

from app.database import get_db
from app.models import Organization, Employee
from app.schemas import (
    OrganizationCreate, OrganizationResponse, EmployeeCreate, EmployeeResponse,
    TokenResponse, OrganizationLogin, EmployeeLogin
)
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        user_type: str = payload.get("user_type")
        
        if user_id is None or user_type is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    if user_type == "organization_hr":
        result = await db.execute(select(Organization).where(Organization.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
    elif user_type == "employee":
        result = await db.execute(select(Employee).where(Employee.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
    else:
        raise credentials_exception
    
    if user is None:
        raise credentials_exception
    
    return user

# Organization Authentication Endpoints
@router.post("/organization/signup", response_model=TokenResponse)
async def organization_signup(org_data: OrganizationCreate, db: AsyncSession = Depends(get_db)):
    # Check if organization already exists
    result = await db.execute(select(Organization).where(Organization.hremail == org_data.hremail))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization with this email already exists"
        )
    
    # Create new organization
    hashed_password = get_password_hash(org_data.password)
    db_org = Organization(
        company_name=org_data.company_name,
        hremail=org_data.hremail,
        password_hash=hashed_password
    )
    
    db.add(db_org)
    await db.commit()
    await db.refresh(db_org)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(db_org.id), "user_type": "organization_hr"},
        expires_delta=access_token_expires
    )
    
    # Prepare response
    user_response = OrganizationResponse(
        id=db_org.id,
        company_name=db_org.company_name,
        hremail=db_org.hremail,
        role="organization_hr"
    )
    
    return TokenResponse(access_token=access_token, user=user_response)

@router.post("/organization/login", response_model=TokenResponse)
async def organization_login(
    hremail: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    # Find organization by email
    result = await db.execute(select(Organization).where(Organization.hremail == hremail))
    org = result.scalar_one_or_none()
    
    if not org or not verify_password(password, org.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(org.id), "user_type": "organization_hr"},
        expires_delta=access_token_expires
    )
    
    # Prepare response
    user_response = OrganizationResponse(
        id=org.id,
        company_name=org.company_name,
        hremail=org.hremail,
        role="organization_hr"
    )
    
    return TokenResponse(access_token=access_token, user=user_response)

# Employee Authentication Endpoints
@router.post("/employee/signup", response_model=TokenResponse)
async def employee_signup(emp_data: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    # Check if organization exists
    result = await db.execute(select(Organization).where(Organization.id == emp_data.company_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization not found"
        )
    
    # Check if employee email already exists
    result = await db.execute(select(Employee).where(Employee.employee_email == emp_data.employee_email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee with this email already exists"
        )
    
    # Create new employee
    hashed_password = get_password_hash(emp_data.password)
    db_emp = Employee(
        company_id=emp_data.company_id,
        employee_email=emp_data.employee_email,
        password_hash=hashed_password,
        name=emp_data.name,
        dob=emp_data.dob,
        phone_number=emp_data.phone_number,
        joining_date=emp_data.joining_date or datetime.now().date()
    )
    
    db.add(db_emp)
    await db.commit()
    await db.refresh(db_emp)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(db_emp.id), "user_type": "employee"},
        expires_delta=access_token_expires
    )
    
    # Prepare response
    user_response = EmployeeResponse(
        id=db_emp.id,
        company_id=db_emp.company_id,
        employee_email=db_emp.employee_email,
        name=db_emp.name,
        role="employee"
    )
    
    return TokenResponse(access_token=access_token, user=user_response)

@router.post("/employee/login", response_model=TokenResponse)
async def employee_login(
    company_id: str = Form(...),
    employee_email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        company_uuid = uuid.UUID(company_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid company ID format"
        )
    
    # Find employee by email and company
    result = await db.execute(
        select(Employee).where(
            Employee.employee_email == employee_email,
            Employee.company_id == company_uuid
        )
    )
    emp = result.scalar_one_or_none()
    
    if not emp or not verify_password(password, emp.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(emp.id), "user_type": "employee"},
        expires_delta=access_token_expires
    )
    
    # Prepare response
    user_response = EmployeeResponse(
        id=emp.id,
        company_id=emp.company_id,
        employee_email=emp.employee_email,
        name=emp.name,
        role="employee"
    )
    
    return TokenResponse(access_token=access_token, user=user_response)

# Protected endpoint example
@router.get("/me")
async def read_users_me(current_user: Union[Organization, Employee] = Depends(get_current_user)):
    return current_user 