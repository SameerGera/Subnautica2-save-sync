"""Game process launch and monitoring."""

import os
import subprocess
import time
from typing import Optional

import psutil

from .logger import logger


class ProcessManager:
    """Manages game process launching and monitoring."""

    def __init__(self, game_executable: str):
        self.game_executable = game_executable

    def is_game_running(self, game_name: str = None) -> Optional[psutil.Process]:
        """Check if game process is currently running."""
        if game_name is None:
            game_name = os.path.basename(self.game_executable)

        for proc in psutil.process_iter(["name", "exe"]):
            try:
                if proc.info["name"] and game_name.lower() in proc.info["name"].lower():
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def launch_game(self) -> subprocess.Popen:
        """Launch the game executable."""
        if not os.path.exists(self.game_executable):
            raise FileNotFoundError(f"Game executable not found: {self.game_executable}")

        logger.info("launching_game", executable=self.game_executable)

        process = subprocess.Popen(
            [self.game_executable],
            cwd=os.path.dirname(self.game_executable),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        )

        logger.info("game_started", pid=process.pid)
        return process

    def monitor_process(self, process: subprocess.Popen, poll_interval: float = 1.0) -> int:
        """Monitor process until exit, return exit code."""
        logger.info("monitoring_process", pid=process.pid)

        while True:
            retcode = process.poll()
            if retcode is not None:
                logger.info("process_exited", pid=process.pid, exit_code=retcode)
                return retcode
            time.sleep(poll_interval)

    def wait_for_game_start(self, game_name: str = None, timeout: int = 30) -> bool:
        """Wait for game process to appear in process list."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_game_running(game_name):
                logger.info("game_process_detected")
                return True
            time.sleep(0.5)
        logger.warning("game_process_not_detected", timeout=timeout)
        return False