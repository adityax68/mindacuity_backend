from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, IntegrityError
from datetime import timedelta
import logging

from app.database import get_db
from app.auth import verify_password, create_access_token, get_current_regular_user, get_user_info, get_password_hash
from app.crud import UserCRUD
from app.schemas import UserCreate, User, Token
from app.config import settings
from app.services.role_service import RoleService
from app.models import User as UserModel # Renamed SQLAlchemy User model to UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["user_authentication"])

@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        logger.info(f"Attempting to create user with email: {user.email}")
        
        result = await db.execute(select(UserModel).where(UserModel.email == user.email))
        db_user = result.scalar_one_or_none()
        if db_user:
            logger.info(f"Email already registered: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        result = await db.execute(select(UserModel).where(UserModel.username == user.username))
        db_user = result.scalar_one_or_none()
        if db_user:
            logger.info(f"Username already taken: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        logger.info(f"Creating new user: {user.email}")
        # Temporarily create user directly without role system for now
        hashed_password = get_password_hash(user.password)
        db_user = UserModel(
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            hashed_password=hashed_password,
            role=getattr(user, 'role', 'user')
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        logger.info(f"Successfully created user with ID: {db_user.id}")
        
        # Return a simple user response without privileges for now
        return User(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            full_name=db_user.full_name,
            role=db_user.role,
            privileges=[],  # Empty privileges for now
            is_active=db_user.is_active,
            created_at=db_user.created_at
        )
        
    except HTTPException:
        raise
    except OperationalError as e:
        logger.error(f"Database connection error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error. Please try again in a moment."
        )
    except IntegrityError as e:
        logger.error(f"Database integrity error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already exists"
        )
    except Exception as e:
        logger.error(f"Unexpected error during signup: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(UserModel).where(UserModel.email == form_data.username))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": str(user.id), "user_type": "user"}, expires_delta=access_token_expires
        )
        
        # Create user response without privileges for now
        user_response = User(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            privileges=[],  # Empty privileges for now
            is_active=user.is_active,
            created_at=user.created_at
        )
        
        return {"access_token": access_token, "token_type": "bearer", "user": user_response}
    
    except HTTPException:
        raise
    except OperationalError as e:
        logger.error(f"Database connection error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again in a moment."
        )
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_regular_user)):
    """
    Get current user information.
    Requires authentication.
    """
    # Return user without privileges for now
    return User(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        privileges=[],  # Empty privileges for now
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
