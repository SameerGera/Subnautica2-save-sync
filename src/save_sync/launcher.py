"""CLI launcher - orchestrates full sync flow."""

import sys
from typing import Optional

from save_sync.config import Config, load_config, save_config
from save_sync.lock_manager import LockManager
from save_sync.logger import logger
from save_sync.minio_client import MinIOClient
from save_sync.process_manager import ProcessManager
from save_sync.save_manager import SaveManager


class Launcher:
    """Orchestrates the save sync workflow."""

    def __init__(self, config: Config):
        self.config = config
        self.client: Optional[MinIOClient] = None
        self.lock_manager: Optional[LockManager] = None
        self.save_manager: Optional[SaveManager] = None
        self.process_manager: Optional[ProcessManager] = None

    def initialize(self) -> bool:
        """Initialize all managers and connections."""
        try:
            logger.info("initializing", player_id=self.config.player_id)

            self.client = MinIOClient(
                endpoint=self.config.minio_endpoint,
                access_key=self.config.minio_access_key,
                secret_key=self.config.minio_secret_key,
                bucket_name=self.config.bucket_name
            )

            self.lock_manager = LockManager(
                client=self.client,
                ttl_seconds=self.config.lock_ttl_seconds
            )

            self.save_manager = SaveManager(
                client=self.client,
                save_directory=self.config.save_directory
            )

            self.process_manager = ProcessManager(
                game_executable=self.config.game_executable_path
            )

            logger.info("initialization_complete")
            return True

        except Exception as e:
            logger.error("initialization_failed", error=str(e))
            return False

    def run(self) -> bool:
        """Execute full sync workflow."""
        if not self.initialize():
            return False

        logger.info("sync_workflow_started")

        logger.step("pulling_from_cloud")
        if not self.save_manager.sync_from_cloud(self.config.player_id):
            logger.warning("sync_from_cloud_skipped_or_failed")

        logger.step("acquiring_lock")
        if not self.lock_manager.acquire_lock(
            self.config.player_id,
            self.config.max_lock_retries
        ):
            logger.error("lock_acquisition_failed")
            return False

        logger.step("launching_game")
        try:
            game_process = self.process_manager.launch_game()
            if not self.process_manager.wait_for_game_start():
                logger.warning("game_start_detection_timeout")

            exit_code = self.process_manager.monitor_process(game_process)
            logger.info("game_session_ended", exit_code=exit_code)

        except Exception as e:
            logger.error("game_launch_failed", error=str(e))
            self.lock_manager.release_lock(self.config.player_id)
            return False

        logger.step("pushing_to_cloud")
        if not self.save_manager.sync_to_cloud(self.config.player_id):
            logger.warning("sync_to_cloud_failed")

        logger.step("releasing_lock")
        self.lock_manager.release_lock(self.config.player_id)

        logger.info("sync_workflow_complete")
        return True


def main():
    """CLI entry point."""
    config = load_config()

    if not config.game_executable_path or not config.save_directory:
        logger.error("config_not_configured")
        print("ERROR: Please configure game executable path and save directory")
        print("Edit config/config.json to add:")
        print("  - game_executable_path")
        print("  - save_directory")
        sys.exit(1)

    launcher = Launcher(config)
    success = launcher.run()

    if success:
        print("\n=== Sync Complete ===")
        sys.exit(0)
    else:
        print("\n=== Sync Failed ===")
        sys.exit(1)


if __name__ == "__main__":
    main()