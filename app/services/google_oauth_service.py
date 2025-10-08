from google.auth.transport import requests
from google.oauth2 import id_token
from typing import Optional, Dict, Any
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class GoogleOAuthService:
    """Service for handling Google OAuth authentication"""
    
    def __init__(self):
        self.client_ids = [
            settings.google_client_id,
            settings.google_android_client_id,
            settings.google_ios_client_id
        ]
        # Filter out empty client IDs
        self.client_ids = [cid for cid in self.client_ids if cid]
    
    async def verify_google_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google ID token and return user info
        
        Args:
            token: Google ID token from frontend
            
        Returns:
            Dict containing user info if valid, None if invalid
        """
        logger.info("=== GOOGLE TOKEN VERIFICATION STARTED ===")
        logger.info(f"Token length: {len(token)}")
        logger.info(f"Token preview: {token[:50]}...")
        logger.info(f"Available client IDs: {len(self.client_ids)}")
        
        try:
            # Try to verify the token with any of the allowed client IDs
            idinfo = None
            successful_client_id = None
            
            for i, client_id in enumerate(self.client_ids):
                logger.info(f"Trying client ID {i+1}/{len(self.client_ids)}: {client_id[:20]}...")
                try:
                    idinfo = id_token.verify_oauth2_token(
                        token, 
                        requests.Request(), 
                        client_id
                    )
                    successful_client_id = client_id
                    logger.info(f"Token verification successful with client ID {i+1}")
                    break  # If successful, break out of the loop
                except ValueError as e:
                    logger.warning(f"Token verification failed with client ID {i+1}: {str(e)}")
                    continue  # Try next client ID
            
            if not idinfo:
                logger.error("Token verification failed for all client IDs")
                logger.error("Possible causes:")
                logger.error("1. Token is malformed or corrupted")
                logger.error("2. Token has expired")
                logger.error("3. Token was issued for a different audience")
                logger.error("4. All client IDs are misconfigured")
                return None
            
            logger.info(f"Token verified successfully with client ID: {successful_client_id[:20]}...")
            
            # Verify the issuer
            logger.info(f"Verifying token issuer: {idinfo['iss']}")
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                logger.error(f"Invalid token issuer: {idinfo['iss']}")
                logger.error("Expected: accounts.google.com or https://accounts.google.com")
                return None
            
            logger.info("Token issuer verification successful")
            
            # Extract user information
            logger.info("Extracting user information from token...")
            user_info = {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'email_verified': idinfo.get('email_verified', False),
                'name': idinfo.get('name', ''),
                'given_name': idinfo.get('given_name', ''),
                'family_name': idinfo.get('family_name', ''),
                'picture': idinfo.get('picture', ''),
                'locale': idinfo.get('locale', 'en')
            }
            
            logger.info("=== GOOGLE TOKEN VERIFICATION SUCCESSFUL ===")
            logger.info(f"User email: {user_info['email']}")
            logger.info(f"Google ID: {user_info['google_id']}")
            logger.info(f"Email verified: {user_info['email_verified']}")
            logger.info(f"Name: {user_info['name']}")
            logger.info(f"Locale: {user_info['locale']}")
            
            return user_info
            
        except ValueError as e:
            logger.error("=== GOOGLE TOKEN VERIFICATION FAILED (ValueError) ===")
            logger.error(f"Invalid Google token: {e}")
            logger.error("This usually means the token format is invalid or expired")
            return None
        except Exception as e:
            logger.error("=== GOOGLE TOKEN VERIFICATION FAILED (Unexpected Error) ===")
            logger.error(f"Error verifying Google token: {e}")
            logger.error("Full traceback:", exc_info=True)
            return None
    
    def is_email_verified(self, user_info: Dict[str, Any]) -> bool:
        """Check if the email is verified by Google"""
        return user_info.get('email_verified', False)
    
    def get_user_display_name(self, user_info: Dict[str, Any]) -> str:
        """Get user's display name from Google info"""
        return user_info.get('name', '') or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip()
