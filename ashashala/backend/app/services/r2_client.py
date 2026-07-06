import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageClient:
    """Generic S3-compatible object storage client.

    Supports Cloudflare R2 and any other S3-compatible provider such as Backblaze B2.
    """

    def __init__(self):
        if not all(
            [
                settings.storage_endpoint_url,
                settings.storage_access_key_id,
                settings.storage_secret_access_key,
                settings.storage_bucket_name,
                settings.storage_public_url,
            ]
        ):
            raise RuntimeError("Object storage credentials not fully configured")

        self.bucket = settings.storage_bucket_name
        self.public_url = settings.storage_public_url

        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key_id,
            aws_secret_access_key=settings.storage_secret_access_key,
            config=Config(
                retries={"max_attempts": 3, "mode": "adaptive"},
                connect_timeout=10,
                read_timeout=settings.R2_TIMEOUT,
            ),
            region_name=settings.storage_region,
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
            put_args = {
                "Bucket": self.bucket,
                "Key": key,
                "Body": data,
                "ContentType": content_type,
                "Metadata": metadata or {},
            }
            if settings.R2_ACCOUNT_ID or settings.R2_PUBLIC_URL:
                put_args["ServerSideEncryption"] = "AES256"
            self.client.put_object(**put_args)
            return f"{self.public_url}/{key}" if self.public_url else key
        except ClientError as e:
            logger.error("Failed to upload to storage: %s", e)
            raise
    
    async def delete_object(self, key: str) -> bool:
        """Delete an object from storage."""
        if settings.MOCK_EXTERNAL_SERVICES:
            return True
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            logger.error("Failed to delete from storage: %s", e)
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
            logger.error("Failed to list storage objects: %s", e)
            return []
    
    async def health_check(self) -> bool:
        """Check storage connectivity."""
        if settings.MOCK_EXTERNAL_SERVICES:
            return True
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except ClientError as e:
            logger.error("Storage health check failed: %s", e)
            return False


# Singleton instance
_storage_client: StorageClient | None = None


def get_storage_client() -> StorageClient:
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client


@asynccontextmanager
async def storage_client_context() -> AsyncGenerator[StorageClient, None]:
    """Async context manager for storage client (for dependency injection)."""
    yield get_storage_client()