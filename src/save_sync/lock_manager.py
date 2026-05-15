"""Distributed lock manager using MinIO."""

import json
import time
from typing import Optional

from save_sync.constants import LOCK_FILE
from save_sync.logger import logger
from save_sync.minio_client import MinIOClient


class LockManager:
    """Manages distributed locking for save sync."""

    def __init__(self, client: MinIOClient, ttl_seconds: int = 300):
        self.client = client
        self.ttl_seconds = ttl_seconds

    def is_locked(self) -> Optional[dict]:
        """Check if lock exists and is valid."""
        data = self.client.download_bytes(LOCK_FILE)
        if data is None:
            return None

        try:
            lock = json.loads(data.decode("utf-8"))
            acquired_at = lock.get("acquired_at", 0)
            ttl = lock.get("ttl_seconds", self.ttl_seconds)

            if time.time() - acquired_at > ttl:
                return None
            return lock
        except (json.JSONDecodeError, KeyError):
            return None

    def acquire_lock(self, player_id: str, max_retries: int = 3) -> bool:
        """Acquire the session lock."""
        for attempt in range(max_retries):
            existing = self.is_locked()

            if existing:
                owner = existing.get("owner", "unknown")
                if owner != player_id:
                    logger.warning(
                        "lock_blocked",
                        owner=owner,
                        attempt=attempt + 1,
                        max_retries=max_retries
                    )
                    time.sleep(2 ** attempt)
                    continue

            lock_data = {
                "owner": player_id,
                "acquired_at": time.time(),
                "ttl_seconds": self.ttl_seconds
            }

            try:
                if self.client.file_exists(LOCK_FILE):
                    current = self.is_locked()
                    if current and current.get("owner") != player_id:
                        if time.time() - current.get("acquired_at", 0) < current.get("ttl_seconds", self.ttl_seconds):
                            logger.warning("lock_taken_by_other", owner=current.get("owner"))
                            time.sleep(2 ** attempt)
                            continue
                    self.client.delete_file(LOCK_FILE)

                self.client.upload_bytes(
                    json.dumps(lock_data).encode("utf-8"),
                    LOCK_FILE
                )
                logger.info("lock_acquired", player_id=player_id)
                return True

            except Exception as e:
                logger.error("lock_acquire_failed", error=str(e), attempt=attempt + 1)
                time.sleep(2 ** attempt)

        logger.error("lock_acquire_max_retries", player_id=player_id)
        return False

    def release_lock(self, player_id: str) -> bool:
        """Release the session lock."""
        try:
            current = self.is_locked()
            if current and current.get("owner") == player_id:
                self.client.delete_file(LOCK_FILE)
                logger.info("lock_released", player_id=player_id)
                return True
            else:
                logger.warning("lock_release_not_owner")
                return False
        except Exception as e:
            logger.error("lock_release_failed", error=str(e))
            return False