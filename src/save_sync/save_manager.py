"""Save file detection and synchronization."""

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from save_sync.constants import METADATA_FILE, SAVE_PATTERN
from save_sync.logger import logger
from save_sync.minio_client import MinIOClient


class SaveMetadata:
    """Save file metadata model."""

    def __init__(self, filename: str, size: int, mtime: float, hash: str, updated_by: str):
        self.filename = filename
        self.size = size
        self.mtime = mtime
        self.hash = hash
        self.updated_by = updated_by
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "size": self.size,
            "mtime": self.mtime,
            "hash": self.hash,
            "updated_by": self.updated_by,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SaveMetadata":
        return cls(
            filename=data.get("filename", ""),
            size=data.get("size", 0),
            mtime=data.get("mtime", 0),
            hash=data.get("hash", ""),
            updated_by=data.get("updated_by", "")
        )


class SaveManager:
    """Manages save file detection and cloud synchronization."""

    def __init__(self, client: MinIOClient, save_directory: str):
        self.client = client
        self.save_directory = Path(save_directory)
        self.pattern = re.compile(SAVE_PATTERN)

    def find_latest_save(self) -> Optional[Path]:
        """Find the latest savegame_N.sav file by modification time."""
        if not self.save_directory.exists():
            logger.error("save_directory_not_found", path=str(self.save_directory))
            return None

        save_files = []
        for item in self.save_directory.iterdir():
            if self.pattern.match(item.name):
                save_files.append(item)

        if not save_files:
            logger.warning("no_save_files_found", directory=str(self.save_directory))
            return None

        latest = max(save_files, key=lambda f: f.stat().st_mtime)
        logger.info("latest_save_found", filename=latest.name, path=str(latest))
        return latest

    def compute_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_local_metadata(self, save_file: Path) -> SaveMetadata:
        """Get metadata for a local save file."""
        stat = save_file.stat()
        return SaveMetadata(
            filename=save_file.name,
            size=stat.st_size,
            mtime=stat.st_mtime,
            hash=self.compute_hash(save_file),
            updated_by="local"
        )

    def get_remote_metadata(self) -> Optional[SaveMetadata]:
        """Get metadata from cloud."""
        data = self.client.download_bytes(METADATA_FILE)
        if data is None:
            return None
        try:
            return SaveMetadata.from_dict(json.loads(data.decode("utf-8")))
        except (json.JSONDecodeError, KeyError):
            return None

    def save_remote_metadata(self, metadata: SaveMetadata) -> bool:
        """Save metadata to cloud."""
        try:
            self.client.upload_bytes(
                json.dumps(metadata.to_dict()).encode("utf-8"),
                METADATA_FILE
            )
            logger.info("metadata_saved", filename=metadata.filename)
            return True
        except Exception as e:
            logger.error("metadata_save_failed", error=str(e))
            return False

    def sync_from_cloud(self, player_id: str) -> bool:
        """Download latest save from cloud if remote is newer."""
        remote_meta = self.get_remote_metadata()
        if remote_meta is None:
            logger.info("no_remote_metadata")
            return False

        local_save = self.find_latest_save()
        needs_download = False

        if local_save is None:
            needs_download = True
        else:
            local_meta = self.get_local_metadata(local_save)
            if remote_meta.mtime > local_meta.mtime:
                needs_download = True
                logger.info("remote_newer", remote_mtime=remote_meta.mtime, local_mtime=local_meta.mtime)

        if needs_download:
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, remote_meta.filename)
            try:
                self.client.download_file(remote_meta.filename, temp_path)
                target_path = self.save_directory / remote_meta.filename

                if local_save and local_save.name != remote_meta.filename:
                    backup = local_save.with_suffix(".sav.backup")
                    shutil.copy2(local_save, backup)
                    logger.info("backup_created", backup=str(backup))

                shutil.copy2(temp_path, target_path)
                logger.info("save_downloaded", filename=remote_meta.filename, target=str(target_path))
                return True
            except Exception as e:
                logger.error("download_failed", error=str(e))
                return False
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        return False

    def sync_to_cloud(self, player_id: str) -> bool:
        """Upload latest save to cloud."""
        local_save = self.find_latest_save()
        if local_save is None:
            logger.error("no_local_save_to_upload")
            return False

        try:
            self.client.upload_file(str(local_save), local_save.name)
            local_meta = self.get_local_metadata(local_save)
            local_meta.updated_by = player_id
            self.save_remote_metadata(local_meta)
            logger.info("save_uploaded", filename=local_save.name)
            return True
        except Exception as e:
            logger.error("upload_failed", error=str(e))
            return False