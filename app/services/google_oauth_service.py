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
        try:
            # Try to verify the token with any of the allowed client IDs
            idinfo = None
            for client_id in self.client_ids:
                try:
                    idinfo = id_token.verify_oauth2_token(
                        token, 
                        requests.Request(), 
                        client_id
                    )
                    break  # If successful, break out of the loop
                except ValueError:
                    continue  # Try next client ID
            
            if not idinfo:
                logger.error("Token verification failed for all client IDs")
                return None
            
            # Verify the issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                logger.warning(f"Invalid token issuer: {idinfo['iss']}")
                return None
            
            # Extract user information
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
            
            logger.info(f"Successfully verified Google token for user: {user_info['email']}")
            return user_info
            
        except ValueError as e:
            logger.error(f"Invalid Google token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying Google token: {e}")
            return None
    
    def is_email_verified(self, user_info: Dict[str, Any]) -> bool:
        """Check if the email is verified by Google"""
        return user_info.get('email_verified', False)
    
    def get_user_display_name(self, user_info: Dict[str, Any]) -> str:
        """Get user's display name from Google info"""
        return user_info.get('name', '') or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip()
