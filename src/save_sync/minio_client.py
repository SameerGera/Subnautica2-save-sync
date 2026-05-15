"""MinIO/S3 client for cloud storage operations."""

import io
import json
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from save_sync.logger import logger


class MinIOClient:
    """S3-compatible storage client for MinIO."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str
    ):
        self.endpoint = endpoint
        self.bucket_name = bucket_name
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4")
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket_name)
                logger.info("bucket_created", bucket=self.bucket_name)
            except ClientError as e:
                logger.error("bucket_creation_failed", error=str(e))
                raise

    def upload_file(self, local_path: str, remote_key: str) -> bool:
        """Upload a local file to the bucket."""
        try:
            self.client.upload_file(local_path, self.bucket_name, remote_key)
            logger.info("file_uploaded", local=local_path, remote=remote_key)
            return True
        except ClientError as e:
            logger.error("upload_failed", error=str(e))
            raise

    def download_file(self, remote_key: str, local_path: str) -> bool:
        """Download a file from the bucket."""
        try:
            self.client.download_file(self.bucket_name, remote_key, local_path)
            logger.info("file_downloaded", remote=remote_key, local=local_path)
            return True
        except ClientError as e:
            logger.error("download_failed", error=str(e))
            raise

    def upload_bytes(self, data: bytes, remote_key: str, content_type: str = "application/json") -> bool:
        """Upload bytes directly to the bucket."""
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=remote_key,
                Body=data,
                ContentType=content_type
            )
            logger.info("bytes_uploaded", remote=remote_key)
            return True
        except ClientError as e:
            logger.error("bytes_upload_failed", error=str(e))
            raise

    def download_bytes(self, remote_key: str) -> Optional[bytes]:
        """Download bytes directly from the bucket."""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=remote_key)
            return response["Body"].read()
        except ClientError:
            return None

    def delete_file(self, remote_key: str) -> bool:
        """Delete a file from the bucket."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=remote_key)
            logger.info("file_deleted", remote=remote_key)
            return True
        except ClientError as e:
            logger.error("delete_failed", error=str(e))
            raise

    def list_files(self, prefix: str = "") -> list:
        """List files in the bucket with optional prefix."""
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]
        except ClientError as e:
            logger.error("list_failed", error=str(e))
            return []

    def file_exists(self, remote_key: str) -> bool:
        """Check if a file exists in the bucket."""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=remote_key)
            return True
        except ClientError:
            return False

    def get_file_metadata(self, remote_key: str) -> Optional[dict]:
        """Get file metadata (size, last_modified)."""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=remote_key)
            return {
                "size": response.get("ContentLength"),
                "last_modified": response.get("LastModified")
            }
        except ClientError:
            return None