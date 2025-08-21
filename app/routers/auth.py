from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError
from datetime import timedelta
from app.database import get_db
from app.auth import verify_password, create_access_token, get_current_active_user, get_user_info
from app.crud import UserCRUD
from app.schemas import UserCreate, User, Token
from app.config import settings
from app.services.role_service import RoleService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.
    
    - **email**: User's email address (must be unique)
    - **username**: User's username (must be unique)
    - **password**: User's password (will be hashed)
    - **full_name**: User's full name (optional)
    - **role**: User's role (defaults to "user")
    """
    try:
        logger.info(f"Attempting to create user with email: {user.email}")
        
        # Check if user with email already exists
        db_user = UserCRUD.get_user_by_email(db, email=user.email)
        if db_user:
            logger.info(f"Email already registered: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        db_user = UserCRUD.get_user_by_username(db, username=user.username)
        if db_user:
            logger.info(f"Username already taken: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create new user
        logger.info(f"Creating new user: {user.email}")
        new_user = UserCRUD.create_user(db=db, user=user)
        logger.info(f"Successfully created user with ID: {new_user.id}")
        return new_user
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
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
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate user and return access token.
    
    - **username**: User's email address
    - **password**: User's password
    """
    try:
        # Find user by email (username field in OAuth2 form)
        user = UserCRUD.get_user_by_email(db, email=form_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # Get user privileges
        role_service = RoleService(db)
        privileges = await role_service.get_user_privileges(user.id)
        
        # Create user response with privileges
        user_response = User(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            privileges=list(privileges),
            is_active=user.is_active,
            created_at=user.created_at
        )
        
        return {"access_token": access_token, "token_type": "bearer", "user": user_response}
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except OperationalError as e:
        logger.error(f"Database connection error during login: {e}")
        # For database connection issues, we should still try to authenticate
        # If we can't reach the database, we can't verify credentials, so return 503
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
async def read_users_me(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Get current user information with privileges.
    Requires authentication.
    """
    # Get user privileges
    role_service = RoleService(db)
    privileges = await role_service.get_user_privileges(current_user.id)
    
    # Return user with privileges
    return User(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        privileges=list(privileges),
        is_active=current_user.is_active,
        created_at=current_user.created_at
    ) 