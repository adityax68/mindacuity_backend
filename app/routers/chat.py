from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.auth import get_current_user, UnifiedUser
from app.models import User
from app.schemas import ChatMessageRequest, ChatResponse, ChatConversationResponse
from app.services.chat_service import ChatService
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["Chat"])

def get_chat_service() -> ChatService:
    """Dependency to get chat service instance"""
    try:
        return ChatService()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize chat service: {str(e)}"
        )

@router.post("/send", response_model=ChatResponse)
async def send_message(
    chat_request: ChatMessageRequest,
    current_user: UnifiedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Send a chat message and get AI response"""
    try:
        if not chat_request.message or not chat_request.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty"
            )
        
        # Convert UnifiedUser to user_id for chat service
        # For regular users, id is int; for orgs/employees, id is str (UUID)
        user_id = current_user.id if isinstance(current_user.id, int) else int(current_user.id, 16) % 1000000
        
        # Process the chat message
        response = await chat_service.process_chat_message(
            db=db,
            user_id=user_id,
            chat_request=chat_request
        )
        
        return response
        
    except ValueError as e:
        # Rate limit or validation errors
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS if "Rate limit" in str(e) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}"
        )

@router.get("/conversations", response_model=List[ChatConversationResponse])
async def get_conversations(
    current_user: UnifiedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get all conversations for the current user"""
    try:
        # Convert UnifiedUser to user_id for chat service
        user_id = current_user.id if isinstance(current_user.id, int) else int(current_user.id, 16) % 1000000
        
        conversations = await chat_service.get_user_conversations(db, user_id)
        return conversations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversations: {str(e)}"
        )

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    current_user: UnifiedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get all messages for a specific conversation"""
    try:
        # Convert UnifiedUser to user_id for chat service
        user_id = current_user.id if isinstance(current_user.id, int) else int(current_user.id, 16) % 1000000
        
        messages = await chat_service.get_conversation_messages(db, conversation_id, user_id)
        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at
                }
                for msg in messages
            ]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation messages: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: UnifiedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    try:
        # Verify user owns this conversation
        from app.models import ChatConversation
        from sqlalchemy import select
        
        result = await db.execute(
            select(ChatConversation).where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == (current_user.id if isinstance(current_user.id, int) else int(current_user.id, 16) % 1000000)
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or access denied"
            )
        
        # Delete conversation (messages will be deleted due to cascade)
        await db.delete(conversation)
        await db.commit()
        
        return {"message": "Conversation deleted successfully"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )

@router.get("/health")
async def chat_health_check(
    current_user: UnifiedUser = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Health check for chat service"""
    try:
        # Simple health check - if we can create the service, it's healthy
        return {
            "status": "healthy",
            "service": "chat",
            "rate_limit": f"{chat_service.max_messages_per_minute} messages per minute",
            "user_id": current_user.id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chat service is not available: {str(e)}"
        )

@router.get("/public-health")
async def public_chat_health_check():
    """Public health check for chat service (no auth required)"""
    try:
        return {
            "status": "healthy",
            "service": "chat",
            "message": "Chat service is running",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chat service is not available: {str(e)}"
        ) 