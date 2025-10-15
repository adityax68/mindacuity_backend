from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import (
    SessionChatMessageRequest, 
    SessionChatResponse, 
    SubscriptionRequest, 
    SubscriptionResponse,
    AccessCodeRequest,
    AccessCodeResponse,
    SessionConversationResponse,
    User
)
from app.services.optimized_session_chat_service import OptimizedSessionChatService as SessionChatService
from app.services.subscription_service import SubscriptionService
from app.auth import get_current_active_user
from app.models import UserFreeService, Subscription

router = APIRouter(prefix="/session-chat", tags=["Session Chat"])

def get_session_chat_service() -> SessionChatService:
    """Dependency to get session chat service instance"""
    try:
        return SessionChatService()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize session chat service: {str(e)}"
        )

def get_subscription_service() -> SubscriptionService:
    """Dependency to get subscription service instance"""
    return SubscriptionService()

@router.post("/send", response_model=SessionChatResponse)
async def send_message(
    chat_request: SessionChatMessageRequest,
    db: Session = Depends(get_db),
    chat_service: SessionChatService = Depends(get_session_chat_service)
):
    """Send a chat message and get AI response"""
    try:
        if not chat_request.message or not chat_request.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        # Process the chat message
        response = await chat_service.process_chat_message(
            db=db,
            session_identifier=chat_request.session_identifier,
            chat_request=chat_request
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}"
        )

@router.post("/subscribe", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_request: SubscriptionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Create a new subscription (requires authentication)"""
    try:
        if subscription_request.plan_type == "free":
            result = subscription_service.create_free_subscription(db)
        elif subscription_request.plan_type == "basic":
            result = subscription_service.create_basic_subscription(db)
        elif subscription_request.plan_type == "premium":
            result = subscription_service.create_premium_subscription(db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan type. Must be 'free', 'basic', or 'premium'"
            )
        
        return SubscriptionResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )

@router.get("/check-free-access")
async def check_free_access(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Check if user already has a free access code (without generating new one)"""
    try:
        # Check if user already has free service
        existing_free_service = db.query(UserFreeService).filter(
            UserFreeService.user_id == current_user.id
        ).first()
        
        if existing_free_service:
            # Return existing access code
            subscription = db.query(Subscription).filter(
                Subscription.subscription_token == existing_free_service.subscription_token
            ).first()
            
            return {
                "has_code": True,
                "access_code": subscription.access_code if subscription else None,
                "plan_type": subscription.plan_type if subscription else None,
                "message_limit": subscription.message_limit if subscription else None,
                "generated_at": existing_free_service.generated_at
            }
        
        return {
            "has_code": False,
            "access_code": None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check free access: {str(e)}"
        )

@router.post("/generate-free-access")
async def generate_free_access(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Generate one-time free basic access code for logged-in user"""
    try:
        # Check if user already used free service
        existing_free_service = db.query(UserFreeService).filter(
            UserFreeService.user_id == current_user.id
        ).first()
        
        if existing_free_service:
            # Return existing access code
            subscription = db.query(Subscription).filter(
                Subscription.subscription_token == existing_free_service.subscription_token
            ).first()
            
            return {
                "success": True,
                "already_generated": True,
                "message": "You already have a free access code",
                "access_code": subscription.access_code,
                "plan_type": subscription.plan_type,
                "message_limit": subscription.message_limit,
                "generated_at": existing_free_service.generated_at
            }
        
        # Create new basic subscription (using existing service method)
        result = subscription_service.create_basic_subscription(db)
        
        # Save to free service table
        free_service = UserFreeService(
            user_id=current_user.id,
            access_code=result["access_code"],
            subscription_token=result["subscription_token"],
            plan_type="basic",
            has_used=True
        )
        db.add(free_service)
        db.commit()
        db.refresh(free_service)
        
        return {
            "success": True,
            "already_generated": False,
            "message": "Free access code generated successfully",
            "access_code": result["access_code"],
            "plan_type": result["plan_type"],
            "message_limit": result["message_limit"],
            "generated_at": free_service.generated_at
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate free access: {str(e)}"
        )

@router.post("/access-code", response_model=AccessCodeResponse)
async def validate_access_code(
    access_request: AccessCodeRequest,
    db: Session = Depends(get_db),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Validate access code and return subscription info"""
    try:
        subscription = subscription_service.get_subscription_by_access_code(
            db, access_request.access_code
        )
        
        if not subscription:
            return AccessCodeResponse(
                success=False,
                message="Invalid or expired access code"
            )
        
        return AccessCodeResponse(
            success=True,
            message="Access code validated successfully",
            subscription_token=subscription.subscription_token,
            plan_type=subscription.plan_type,
            message_limit=subscription.message_limit
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate access code: {str(e)}"
        )

@router.post("/link-session")
async def link_session_to_subscription(
    session_identifier: str,
    subscription_token: str,
    db: Session = Depends(get_db),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    try:
        success = subscription_service.link_session_to_subscription(
            db, session_identifier, subscription_token, allow_reuse=True
        )
        
        if success:
            return {"message": "Session linked to subscription successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to link session to subscription"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link session: {str(e)}"
        )

@router.get("/conversation/{session_identifier}", response_model=SessionConversationResponse)
async def get_conversation(
    session_identifier: str,
    db: Session = Depends(get_db),
    chat_service: SessionChatService = Depends(get_session_chat_service),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Get conversation messages and usage info for a session"""
    try:
        # Get messages
        messages = chat_service.get_conversation_messages(db, session_identifier)
        
        # Get usage info (preserve existing plans for existing sessions)
        usage_info = subscription_service.check_usage_limit(db, session_identifier, allow_orphaned_reuse=False)
        
        # Get conversation details
        from app.models import Conversation
        conversation = db.query(Conversation).filter(
            Conversation.session_identifier == session_identifier
        ).first()
        
        # If no conversation exists, create one (this preserves the session and its plan)
        if not conversation:
            conversation = subscription_service.create_or_get_conversation(db, session_identifier)
        
        return SessionConversationResponse(
            session_identifier=conversation.session_identifier,
            title=conversation.title,
            created_at=conversation.created_at,
            messages=messages,
            usage_info=usage_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )


@router.get("/usage/{session_identifier}")
async def get_usage_info(
    session_identifier: str,
    db: Session = Depends(get_db),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Get usage information for a session"""
    try:
        usage_info = subscription_service.check_usage_limit(db, session_identifier, allow_orphaned_reuse=False)
        return usage_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage info: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check for session chat service"""
    return {
        "status": "healthy",
        "service": "session_chat",
        "message": "Session-based chat service is running"
    }
