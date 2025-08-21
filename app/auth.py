from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User
from app.services.role_service import RoleService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

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

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    email = verify_token(credentials.credentials)
    if email is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# NEW: Get user info with privileges
async def get_user_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user info with role and privileges"""
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