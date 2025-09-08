from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from app.database import get_db
from app.auth import get_current_user
from app.models import User, ChatAttachment
from app.schemas import ChatMessageRequest, ChatResponse, ChatConversationResponse, FileUploadResponse
from app.services.chat_service import ChatService
from app.services.file_cleanup_service import cleanup_service

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
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
            user_id=current_user.id,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get all conversations for the current user"""
    try:
        conversations = chat_service.get_user_conversations(db, current_user.id)
        return conversations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversations: {str(e)}"
        )

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get all messages for a specific conversation"""
    try:
        messages = chat_service.get_conversation_messages(db, conversation_id, current_user.id)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    try:
        # Verify user owns this conversation
        from app.models import ChatConversation
        conversation = db.query(ChatConversation).filter(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or access denied"
            )
        
        # Delete conversation (messages will be deleted due to cascade)
        db.delete(conversation)
        db.commit()
        
        return {"message": "Conversation deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )

@router.get("/health")
async def chat_health_check(
    current_user: User = Depends(get_current_user),
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

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a file for chat attachment (max 10MB)"""
    try:
        # Validate file size (10MB limit)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
        file_content = await file.read()
        
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 10MB limit"
            )
        
        # Validate file type
        ALLOWED_TYPES = {
            # Documents
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            # Images
            'image/jpeg',
            'image/jpg', 
            'image/png',
            'image/gif',
            'image/webp',
            'image/bmp'
        }
        
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not supported. Allowed types: PDF, DOC, DOCX, TXT, JPG, PNG, GIF, WebP, BMP"
            )
        
        # Create temporary directory for uploads
        temp_dir = Path(tempfile.gettempdir()) / "health_app_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{current_user.id}_{uuid.uuid4()}{file_extension}"
        file_path = temp_dir / unique_filename
        
        # Save file to temporary location
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Create database record
        attachment = ChatAttachment(
            user_id=current_user.id,
            filename=unique_filename,
            original_filename=file.filename,
            file_size=len(file_content),
            file_type=file.content_type,
            file_path=str(file_path),
            upload_url=f"/chat/files/{unique_filename}",
            expires_at=datetime.utcnow() + timedelta(hours=24)  # Auto-cleanup after 24 hours
        )
        
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
        
        # Process the document immediately after upload
        try:
            from app.services.chat_service import ChatService
            chat_service = ChatService()
            processed_content = await chat_service._process_attachment_with_gpt4o(db, attachment.id)
            
            # Update attachment with processed content
            attachment.is_processed = True
            attachment.processed_content = processed_content
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to process document during upload: {e}")
            # Don't fail the upload, just mark as not processed
            attachment.is_processed = False
            db.commit()

        return FileUploadResponse(
            file_id=attachment.id,
            filename=attachment.original_filename,
            file_size=attachment.file_size,
            file_type=attachment.file_type,
            upload_url=attachment.upload_url,
            created_at=attachment.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.get("/files/{filename}")
async def get_file(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get uploaded file"""
    try:
        # Find attachment record
        attachment = db.query(ChatAttachment).filter(
            ChatAttachment.filename == filename,
            ChatAttachment.user_id == current_user.id
        ).first()
        
        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied"
            )
        
        # Check if file exists
        file_path = Path(attachment.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File no longer exists"
            )
        
        # Return file
        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(file_path),
            filename=attachment.original_filename,
            media_type=attachment.file_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file: {str(e)}"
        )

@router.post("/cleanup")
async def cleanup_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clean up expired files (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        expired_count = cleanup_service.cleanup_expired_files(db)
        orphaned_count = cleanup_service.cleanup_orphaned_files(db)
        
        return {
            "message": "Cleanup completed",
            "expired_files_cleaned": expired_count,
            "orphaned_files_cleaned": orphaned_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )

@router.get("/storage-stats")
async def get_storage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get storage statistics (admin only)"""
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        stats = cleanup_service.get_storage_stats(db)
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage stats: {str(e)}"
        ) 