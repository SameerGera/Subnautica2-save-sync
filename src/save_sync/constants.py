"""Hardcoded constants for the save sync application."""

SAVE_PATTERN = r"^savegame_\d+\.sav$"
LOCK_FILE = "session_lock.json"
METADATA_FILE = "save_metadata.json"
CONFIG_FILE = "config/config.json"
LOG_FILE = "save_sync.log"
DEFAULT_LOCK_TTL = 300
DEFAULT_MAX_RETRIES = 3