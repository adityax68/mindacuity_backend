import boto3
import uuid
from typing import Optional
from fastapi import HTTPException, UploadFile
from botocore.exceptions import ClientError, NoCredentialsError
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.aws_access_key_id = settings.aws_access_key_id
        self.aws_secret_access_key = settings.aws_secret_access_key
        self.aws_region = settings.aws_region
        self.bucket_name = settings.s3_bucket_name
        self.s3_base_url = settings.s3_base_url
        
        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.bucket_name]):
            raise ValueError("Missing required AWS S3 environment variables")
        
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
        except NoCredentialsError:
            raise ValueError("AWS credentials not found")
    
    async def upload_research_thumbnail(self, file: UploadFile, research_id: Optional[int] = None) -> str:
        """
        Upload a research thumbnail image to S3
        
        Args:
            file: The uploaded file
            research_id: Optional research ID for naming
            
        Returns:
            str: The presigned URL of the uploaded image
        """
        try:
            # Validate file type
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Generate unique filename
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
            if research_id:
                filename = f"research-{research_id}-{uuid.uuid4().hex}.{file_extension}"
            else:
                filename = f"research-{uuid.uuid4().hex}.{file_extension}"
            
            # S3 key (path in bucket)
            s3_key = f"research-thumbnails/{filename}"
            
            # Upload file to S3
            file_content = await file.read()
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=file.content_type
            )
            
            # Return the public URL (will work after bucket policy is added)
            public_url = f"{self.s3_base_url}/{s3_key}"
            logger.info(f"Successfully uploaded research thumbnail: {public_url}")
            
            return public_url
            
        except ClientError as e:
            logger.error(f"AWS S3 error: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload image to S3")
        except Exception as e:
            logger.error(f"Unexpected error uploading image: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload image")
    
    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned URL for an existing S3 object
        
        Args:
            s3_key: The S3 key (path) of the object
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: The presigned URL
        """
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            return presigned_url
        except ClientError as e:
            logger.error(f"AWS S3 error generating presigned URL: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate presigned URL")
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate presigned URL")
    
    async def delete_research_thumbnail(self, thumbnail_url: str) -> bool:
        """
        Delete a research thumbnail from S3
        
        Args:
            thumbnail_url: The S3 URL of the image to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Extract S3 key from URL
            if not thumbnail_url.startswith(self.s3_base_url):
                logger.warning(f"URL does not belong to this S3 bucket: {thumbnail_url}")
                return False
            
            s3_key = thumbnail_url.replace(f"{self.s3_base_url}/", "")
            
            # Delete object from S3
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Successfully deleted research thumbnail: {thumbnail_url}")
            return True
            
        except ClientError as e:
            logger.error(f"AWS S3 error deleting image: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting image: {e}")
            return False

# Create a singleton instance
s3_service = S3Service()
