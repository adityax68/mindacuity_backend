import os
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import Subscription, Conversation, ConversationUsage
import logging

logger = logging.getLogger(__name__)

class SubscriptionService:
    def __init__(self):
        self.free_plan_limit = 5
        self.basic_plan_limit = 10
        self.premium_plan_limit = 20  # 20 messages
    
    def generate_session_identifier(self) -> str:
        """Generate a unique session identifier"""
        return f"sess_{secrets.token_urlsafe(12)}"
    
    def generate_subscription_token(self) -> str:
        """Generate a unique subscription token"""
        return f"sub_{secrets.token_urlsafe(16)}"
    
    def generate_access_code(self, plan_type: str) -> str:
        """Generate a unique access code based on plan type"""
        random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        
        if plan_type == "free":
            return f"FREE-{random_part}"
        elif plan_type == "basic":
            return f"BASIC-{random_part}"
        elif plan_type == "premium":
            return f"PREMIUM-{random_part}"
        else:
            return f"SUB-{random_part}"
    
    def create_free_subscription(self, db: Session) -> Dict[str, Any]:
        """Create a free subscription for new users"""
        try:
            subscription_token = self.generate_subscription_token()
            access_code = self.generate_access_code("free")
            
            subscription = Subscription(
                subscription_token=subscription_token,
                access_code=access_code,
                plan_type="free",
                message_limit=self.free_plan_limit,
                price=0.00,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24)  # Free expires in 24 hours
            )
            
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            
            logger.info(f"Created free subscription: {subscription_token}")
            
            return {
                "subscription_token": subscription_token,
                "access_code": access_code,
                "plan_type": "free",
                "message_limit": self.free_plan_limit,
                "price": 0.00
            }
            
        except Exception as e:
            logger.error(f"Failed to create free subscription: {e}")
            db.rollback()
            raise
    
    def create_basic_subscription(self, db: Session) -> Dict[str, Any]:
        """Create a basic subscription (for testing)"""
        try:
            subscription_token = self.generate_subscription_token()
            access_code = self.generate_access_code("basic")
            
            subscription = Subscription(
                subscription_token=subscription_token,
                access_code=access_code,
                plan_type="basic",
                message_limit=self.basic_plan_limit,
                price=5.00,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30)
            )
            
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            
            logger.info(f"Created basic subscription: {subscription_token}")
            
            return {
                "subscription_token": subscription_token,
                "access_code": access_code,
                "plan_type": "basic",
                "message_limit": self.basic_plan_limit,
                "price": 5.00
            }
            
        except Exception as e:
            logger.error(f"Failed to create basic subscription: {e}")
            db.rollback()
            raise
    
    def create_premium_subscription(self, db: Session) -> Dict[str, Any]:
        """Create a premium subscription (unlimited)"""
        try:
            subscription_token = self.generate_subscription_token()
            access_code = self.generate_access_code("premium")
            
            subscription = Subscription(
                subscription_token=subscription_token,
                access_code=access_code,
                plan_type="premium",
                message_limit=self.premium_plan_limit,  # 20 messages
                price=15.00,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30)
            )
            
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            
            logger.info(f"Created premium subscription: {subscription_token}")
            
            return {
                "subscription_token": subscription_token,
                "access_code": access_code,
                "plan_type": "premium",
                "message_limit": self.premium_plan_limit,
                "price": 15.00
            }
            
        except Exception as e:
            logger.error(f"Failed to create premium subscription: {e}")
            db.rollback()
            raise
    
    def get_subscription_by_access_code(self, db: Session, access_code: str) -> Optional[Subscription]:
        """Get subscription by access code"""
        try:
            subscription = db.query(Subscription).filter(
                Subscription.access_code == access_code,
                Subscription.is_active == True
            ).first()
            
            if subscription and subscription.expires_at and subscription.expires_at < datetime.now(timezone.utc):
                logger.warning(f"Subscription {access_code} has expired")
                return None
                
            return subscription
            
        except Exception as e:
            logger.error(f"Failed to get subscription by access code {access_code}: {e}")
            # CRITICAL: Rollback the transaction to prevent invalid transaction state
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")
            return None
    
    def create_or_get_conversation(self, db: Session, session_identifier: str) -> Conversation:
        """Create or get existing conversation for session"""
        try:
            conversation = db.query(Conversation).filter(
                Conversation.session_identifier == session_identifier,
                Conversation.is_active == True
            ).first()
            
            if not conversation:
                conversation = Conversation(
                    session_identifier=session_identifier,
                    title="New Conversation",
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
                )
                db.add(conversation)
                db.commit()
                db.refresh(conversation)
                logger.info(f"Created new conversation: {session_identifier}")
            
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to create/get conversation {session_identifier}: {e}")
            db.rollback()
            raise
    
    def link_session_to_subscription(self, db: Session, session_identifier: str, subscription_token: str, allow_reuse: bool = False) -> bool:
        """Link a session to a subscription
        
        Args:
            db: Database session
            session_identifier: Session identifier
            subscription_token: Subscription token
            allow_reuse: If True, allows reusing existing usage records (for access code scenarios)
                        If False, always creates fresh usage record (for new subscriptions)
        """
        try:
            # First, ensure conversation exists
            conversation = self.create_or_get_conversation(db, session_identifier)
            
            # Unlink current session from any existing subscription first
            self.unlink_session_from_subscription(db, session_identifier)
            
            if allow_reuse:
                # Check if there's already ANY usage record for this subscription (active or orphaned)
                existing_subscription_usage = db.query(ConversationUsage).filter(
                    ConversationUsage.subscription_token == subscription_token
                ).first()
                
                if existing_subscription_usage:
                    # If there's an existing usage record, unlink it from its current session and link to new session
                    if existing_subscription_usage.session_identifier:
                        # Unlink the existing session
                        existing_subscription_usage.session_identifier = None
                        db.commit()
                        logger.info(f"Unlinked existing session {existing_subscription_usage.session_identifier} from subscription {subscription_token}")
                    
                    # Link the existing usage record to this session (preserves message count)
                    existing_subscription_usage.session_identifier = session_identifier
                    db.commit()
                    logger.info(f"Linked existing subscription usage to session {session_identifier} with {existing_subscription_usage.messages_used} messages used")
                    return True
            
            # Create new usage record starting from 0 (new subscription or when reuse not allowed)
            usage = ConversationUsage(
                session_identifier=session_identifier,
                subscription_token=subscription_token,
                messages_used=0
            )
            
            db.add(usage)
            db.commit()
            logger.info(f"Created new usage record for session {session_identifier} and subscription {subscription_token}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to link session {session_identifier} to subscription {subscription_token}: {e}")
            db.rollback()
            return False
    
    def unlink_session_from_subscription(self, db: Session, session_identifier: str) -> bool:
        """Unlink a session from its current subscription, making usage record orphaned for other devices"""
        try:
            # Find current usage record for this session
            usage = db.query(ConversationUsage).filter(
                ConversationUsage.session_identifier == session_identifier
            ).first()
            
            if usage:
                # Make the usage record orphaned (session_identifier = NULL) so other devices can pick it up
                usage.session_identifier = None
                db.commit()
                logger.info(f"Unlinked session {session_identifier} from subscription {usage.subscription_token}, usage record now orphaned with {usage.messages_used} messages used")
                return True
            else:
                logger.info(f"No usage record found for session {session_identifier} to unlink")
                return False
            
        except Exception as e:
            logger.error(f"Failed to unlink session {session_identifier}: {e}")
            db.rollback()
            return False
    
    def check_usage_limit(self, db: Session, session_identifier: str, allow_orphaned_reuse: bool = False) -> Dict[str, Any]:
        """Check if session has reached usage limit
        
        Args:
            db: Database session
            session_identifier: Session identifier
            allow_orphaned_reuse: If True, allows re-linking orphaned usage records (for access code usage)
                                 If False, always creates fresh free plan for new sessions
        """
        try:
            # Get usage record for this session
            usage = db.query(ConversationUsage).filter(
                ConversationUsage.session_identifier == session_identifier
            ).first()
            
            logger.info(f"Checking usage for session {session_identifier}: found usage = {usage is not None}")
            if usage:
                logger.info(f"Usage record: subscription_token={usage.subscription_token}, messages_used={usage.messages_used}")
            else:
                logger.info(f"No usage record found for session {session_identifier}")
            
            if not usage:
                # Only check for orphaned usage if explicitly allowed (access code scenarios)
                if allow_orphaned_reuse:
                    # Check if there's an existing usage record that got orphaned (session_identifier = NULL)
                    # This can happen when conversation is deleted but usage record should be preserved
                    orphaned_usage = db.query(ConversationUsage).filter(
                        ConversationUsage.session_identifier.is_(None)
                    ).first()
                    
                    if orphaned_usage:
                        # Re-link the orphaned usage record to this session (preserves current plan)
                        conversation = self.create_or_get_conversation(db, session_identifier)
                        orphaned_usage.session_identifier = session_identifier
                        db.commit()
                        logger.info(f"Re-linked orphaned usage to session {session_identifier} with {orphaned_usage.messages_used} messages used")
                        usage = orphaned_usage
                
                # If no usage found (either no orphaned records or not allowed to reuse), return none plan
                if not usage:
                    # No automatic free subscription - user must generate access code
                    logger.info(f"No usage found for session {session_identifier}, returning 'none' plan")
                    
                    return {
                        "can_send": False,
                        "messages_used": 0,
                        "message_limit": 0,
                        "plan_type": "none",
                        "error": "No subscription found. Please use an access code to continue."
                    }
            
            # Get subscription details
            subscription = db.query(Subscription).filter(
                Subscription.subscription_token == usage.subscription_token,
                Subscription.is_active == True
            ).first()
            
            if not subscription:
                return {
                    "can_send": False,
                    "messages_used": usage.messages_used,
                    "message_limit": 0,
                    "plan_type": "none",
                    "error": "Subscription not found or inactive"
                }
            
            # Check if expired
            if subscription.expires_at and subscription.expires_at < datetime.now(timezone.utc):
                return {
                    "can_send": False,
                    "messages_used": usage.messages_used,
                    "message_limit": subscription.message_limit or 0,
                    "plan_type": subscription.plan_type,
                    "error": "Subscription has expired"
                }
            
            # Check limit
            if subscription.message_limit is None:  # Unlimited
                can_send = True
            else:
                can_send = usage.messages_used < subscription.message_limit
            
            return {
                "can_send": can_send,
                "messages_used": usage.messages_used,
                "message_limit": subscription.message_limit,
                "plan_type": subscription.plan_type,
                "subscription_token": subscription.subscription_token,
                "access_code": subscription.access_code
            }
            
        except Exception as e:
            logger.error(f"Failed to check usage limit for session {session_identifier}: {e}")
            # CRITICAL: Rollback the transaction to prevent invalid transaction state
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")
            
            return {
                "can_send": False,
                "messages_used": 0,
                "message_limit": 0,
                "plan_type": "none",
                "error": f"Error checking usage: {str(e)}"
            }
    
    def increment_usage(self, db: Session, session_identifier: str) -> bool:
        """Increment usage counter for session"""
        try:
            usage = db.query(ConversationUsage).filter(
                ConversationUsage.session_identifier == session_identifier
            ).first()
            
            if usage:
                usage.messages_used += 1
                usage.last_used_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Incremented usage for session {session_identifier}: {usage.messages_used}")
                return True
            
            logger.warning(f"No usage record found for session {session_identifier}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to increment usage for session {session_identifier}: {e}")
            db.rollback()
            return False
