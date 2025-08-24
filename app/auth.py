from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import get_db
from app.models import User, Organization, Employee
from app.services.role_service import RoleService
from pydantic import BaseModel

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Unified user model for all user types
class UnifiedUser(BaseModel):
    id: Union[int, str]  # int for regular users, str (UUID) for orgs/employees
    email: str
    user_type: str  # "user", "organization_hr", "employee"
    is_active: bool = True
    
    class Config:
        from_attributes = True

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        user_type: str = payload.get("user_type")
        if user_id is None or user_type is None:
            return None
        return {"user_id": user_id, "user_type": user_type}
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)) -> UnifiedUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception
    
    user_id = token_data["user_id"]
    user_type = token_data["user_type"]
    
    try:
        if user_type == "user":
            # Regular user from users table
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if user is None:
                raise credentials_exception
            
            return UnifiedUser(
                id=user.id,
                email=user.email,
                user_type="user",
                is_active=user.is_active
            )
            
        elif user_type == "organization_hr":
            # Organization from organisations table
            import uuid
            result = await db.execute(select(Organization).where(Organization.id == uuid.UUID(user_id)))
            org = result.scalar_one_or_none()
            if org is None:
                raise credentials_exception
            
            return UnifiedUser(
                id=str(org.id),
                email=org.hremail,
                user_type="organization_hr",
                is_active=True
            )
            
        elif user_type == "employee":
            # Employee from employees table
            import uuid
            result = await db.execute(select(Employee).where(Employee.id == uuid.UUID(user_id)))
            emp = result.scalar_one_or_none()
            if emp is None:
                raise credentials_exception
            
            return UnifiedUser(
                id=str(emp.id),
                email=emp.employee_email,
                user_type="employee",
                is_active=True
            )
            
        else:
            raise credentials_exception
            
    except (ValueError, TypeError):
        raise credentials_exception

async def get_current_active_user(current_user: UnifiedUser = Depends(get_current_user)) -> UnifiedUser:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Legacy function for backward compatibility (only for regular users)
async def get_current_regular_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    email = verify_token(credentials.credentials)
    if email is None:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    
    return user

# NEW: Get user info with privileges (for regular users only)
async def get_user_info(current_user: User = Depends(get_current_regular_user), db: AsyncSession = Depends(get_db)):
    """Get current user info with role and privileges (regular users only)"""
    role_service = RoleService(db)
    privileges = await role_service.get_user_privileges(current_user.id)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "privileges": list(privileges),
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }

# NEW: Check if user has specific privilege
async def require_privilege(privilege_name: str):
    """Decorator to require specific privilege"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Get database session
            db = kwargs.get('db')
            if not db:
                raise HTTPException(status_code=500, detail="Database session required")
            
            role_service = RoleService(db)
            has_privilege = await role_service.user_has_privilege(current_user.id, privilege_name)
            if not has_privilege:
                raise HTTPException(status_code=403, detail=f"Privilege required: {privilege_name}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# NEW: Check if user has specific role
def require_role(allowed_roles: list):
    """Decorator to check user role"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            if current_user.role not in allowed_roles:
                raise HTTPException(status_code=403, detail="Insufficient role privileges")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator 