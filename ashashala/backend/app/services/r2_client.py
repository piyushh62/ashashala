import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class R2Client:
    """Cloudflare R2 client for object storage.
    
    Uses boto3 with S3-compatible API.
    Features:
    - Presigned URLs for direct browser uploads
    - Server-side encryption
    - Multipart upload support for large files
    """
    
    def __init__(self):
        if not all([settings.R2_ACCOUNT_ID, settings.R2_ACCESS_KEY_ID, settings.R2_SECRET_ACCESS_KEY, settings.R2_BUCKET_NAME]):
            raise RuntimeError("R2 credentials not fully configured")

        self.bucket = settings.R2_BUCKET_NAME
        self.public_url = settings.R2_PUBLIC_URL
        
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(
                retries={"max_attempts": 3, "mode": "adaptive"},
                connect_timeout=10,
                read_timeout=30,
            ),
            region_name="auto",
        )
    
    def generate_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 3600,
        max_size_mb: int = 100,
    ) -> dict[str, str]:
        """Generate presigned POST URL for direct browser upload.
        
        Returns:
            Dict with 'url' and 'fields' for form-data POST
        """
        conditions = [
            {"bucket": self.bucket},
            ["starts-with", "$key", key],
            {"Content-Type": content_type},
            ["content-length-range", 0, max_size_mb * 1024 * 1024],
        ]
        
        try:
            response = self.client.generate_presigned_post(
                Bucket=self.bucket,
                Key=key,
                Fields={"Content-Type": content_type},
                Conditions=conditions,
                ExpiresIn=expires_in,
            )
            return response
        except ClientError as e:
            logger.error("Failed to generate presigned upload URL: %s", e)
            raise
    
    def generate_presigned_download_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned GET URL for download."""
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            logger.error("Failed to generate presigned download URL: %s", e)
            raise
    
    async def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload bytes directly (for small files < 5MB)."""
        if settings.MOCK_EXTERNAL_SERVICES:
            return f"{self.public_url}/{key}" if self.public_url else key
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                Metadata=metadata or {},
                ServerSideEncryption="AES256",
            )
            return f"{self.public_url}/{key}" if self.public_url else key
        except ClientError as e:
            logger.error("Failed to upload to R2: %s", e)
            raise
    
    async def delete_object(self, key: str) -> bool:
        """Delete an object from R2."""
        if settings.MOCK_EXTERNAL_SERVICES:
            return True
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            logger.error("Failed to delete from R2: %s", e)
            return False
    
    async def list_objects(self, prefix: str, max_keys: int = 1000) -> list[dict]:
        """List objects with prefix."""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            return response.get("Contents", [])
        except ClientError as e:
            logger.error("Failed to list R2 objects: %s", e)
            return []
    
    async def health_check(self) -> bool:
        """Check R2 connectivity."""
        if settings.MOCK_EXTERNAL_SERVICES:
            return True
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except ClientError as e:
            logger.error("R2 health check failed: %s", e)
            return False


# Singleton instance
_r2_client: R2Client | None = None


def get_r2_client() -> R2Client:
    global _r2_client
    if _r2_client is None:
        _r2_client = R2Client()
    return _r2_client


@asynccontextmanager
async def r2_client_context() -> AsyncGenerator[R2Client, None]:
    """Async context manager for R2 client (for dependency injection)."""
    yield get_r2_client()