"""Tkinter GUI for Subnautica 2 Save Sync."""

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from typing import Optional

from save_sync.config import Config, load_config, save_config
from save_sync.launcher import Launcher
from save_sync.logger import logger


class LogHandler:
    """Custom log handler that sends messages to GUI."""

    def __init__(self, queue: queue.Queue):
        self.queue = queue

    def emit(self, record):
        msg = self.format(record)
        self.queue.put(("log", msg))

    def format(self, record):
        return f"[{record.levelname}] {record.getMessage()}"

    def flush(self):
        pass


class SaveSyncGUI:
    """Main GUI window for the application."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Subnautica 2 Save Sync")
        self.root.geometry("520x480")
        self.root.resizable(True, True)

        self.queue = queue.Queue()
        self.launcher: Optional[Launcher] = None
        self.is_running = False

        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        """Create UI components."""
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            main_frame,
            text="Subnautica 2 Save Sync",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 10))

        form_frame = tk.Frame(main_frame)
        form_frame.pack(fill=tk.X)

        self._create_field(form_frame, "MinIO Server:", "minio_endpoint", width=40)
        self._create_field(form_frame, "Access Key:", "minio_access_key", width=25)
        self._create_field(form_frame, "Secret Key:", "minio_secret_key", width=25, show="*")
        self._create_field(form_frame, "Bucket:", "bucket_name", width=25)
        self._create_field(form_frame, "Player ID:", "player_id", width=20)

        path_frame = tk.Frame(form_frame)
        path_frame.pack(fill=tk.X, pady=2)
        tk.Label(path_frame, text="Game Path:", width=12, anchor="e").grid(row=0, column=0, sticky="e")
        self.game_path_entry = tk.Entry(path_frame, width=35)
        self.game_path_entry.grid(row=0, column=1, padx=5)
        tk.Button(path_frame, text="Browse", command=self._browse_game, width=8).grid(row=0, column=2)

        path_frame2 = tk.Frame(form_frame)
        path_frame2.pack(fill=tk.X, pady=2)
        tk.Label(path_frame2, text="Save Dir:", width=12, anchor="e").grid(row=0, column=0, sticky="e")
        self.save_dir_entry = tk.Entry(path_frame2, width=35)
        self.save_dir_entry.grid(row=0, column=1, padx=5)
        tk.Button(path_frame2, text="Browse", command=self._browse_save_dir, width=8).grid(row=0, column=2)

        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=15)
        self.launch_button = tk.Button(
            button_frame,
            text="LAUNCH GAME",
            font=("Segoe UI", 14, "bold"),
            bg="#4CAF50",
            fg="white",
            width=20,
            height=2,
            command=self._on_launch
        )
        self.launch_button.pack()

        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 5))
        self.status_label = tk.Label(status_frame, text="Status: Ready", font=("Segoe UI", 10))
        self.status_label.pack(side=tk.LEFT)
        self.last_sync_label = tk.Label(status_frame, text="Last Sync: --", font=("Segoe UI", 9), fg="gray")
        self.last_sync_label.pack(side=tk.RIGHT)

        log_frame = tk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(log_frame, text="Log:", font=("Segoe UI", 10)).pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            font=("Consolas", 9),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_field(self, parent, label: str, key: str, width: int = 30, show: str = None):
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        tk.Label(frame, text=label, width=12, anchor="e").grid(row=0, column=0, sticky="e")
        entry = tk.Entry(frame, width=width, show=show)
        entry.grid(row=0, column=1, padx=5)
        setattr(self, f"{key}_entry", entry)

    def _browse_game(self):
        path = filedialog.askopenfilename(
            title="Select Subnautica 2 Executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self.game_path_entry.delete(0, tk.END)
            self.game_path_entry.insert(0, path)

    def _browse_save_dir(self):
        path = filedialog.askdirectory(title="Select Save Games Directory")
        if path:
            self.save_dir_entry.delete(0, tk.END)
            self.save_dir_entry.insert(0, path)

    def _load_config(self):
        """Load config and populate fields."""
        config = load_config()

        self.minio_endpoint_entry.delete(0, tk.END)
        self.minio_endpoint_entry.insert(0, config.minio_endpoint)

        self.minio_access_key_entry.delete(0, tk.END)
        self.minio_access_key_entry.insert(0, config.minio_access_key)

        self.minio_secret_key_entry.delete(0, tk.END)
        self.minio_secret_key_entry.insert(0, config.minio_secret_key)

        self.bucket_name_entry.delete(0, tk.END)
        self.bucket_name_entry.insert(0, config.bucket_name)

        self.player_id_entry.delete(0, tk.END)
        self.player_id_entry.insert(0, config.player_id)

        self.game_path_entry.delete(0, tk.END)
        self.game_path_entry.insert(0, config.game_executable_path)

        self.save_dir_entry.delete(0, tk.END)
        self.save_dir_entry.insert(0, config.save_directory)

    def _get_config_from_ui(self) -> Config:
        """Get config from UI fields."""
        return Config(
            minio_endpoint=self.minio_endpoint_entry.get(),
            minio_access_key=self.minio_access_key_entry.get(),
            minio_secret_key=self.minio_secret_key_entry.get(),
            bucket_name=self.bucket_name_entry.get(),
            player_id=self.player_id_entry.get(),
            game_executable_path=self.game_path_entry.get(),
            save_directory=self.save_dir_entry.get(),
            lock_ttl_seconds=300,
            max_lock_retries=3
        )

    def _save_config(self):
        """Save config from UI."""
        config = self._get_config_from_ui()
        save_config(config)

    def _on_launch(self):
        """Handle Launch button click."""
        if self.is_running:
            return

        config = self._get_config_from_ui()

        if not config.game_executable_path:
            messagebox.showerror("Error", "Please select game executable")
            return

        if not config.save_directory:
            messagebox.showerror("Error", "Please select save directory")
            return

        if not os.path.exists(config.game_executable_path):
            messagebox.showerror("Error", "Game executable not found")
            return

        if not os.path.isdir(config.save_directory):
            messagebox.showerror("Error", "Save directory not found")
            return

        self._save_config()
        self._run_sync(config)

    def _run_sync(self, config: Config):
        """Run sync in background thread."""
        self.is_running = True
        self.launch_button.config(state=tk.DISABLED, bg="#888888")
        self.status_label.config(text="Status: Syncing...")

        thread = threading.Thread(target=self._sync_worker, args=(config,), daemon=True)
        thread.start()

        self.root.after(100, self._check_queue)

    def _sync_worker(self, config: Config):
        """Background sync worker."""
        try:
            launcher = Launcher(config)
            success = launcher.run()
            self.queue.put(("result", success))
        except Exception as e:
            self.queue.put(("error", str(e)))

    def _check_queue(self):
        """Check for messages in queue."""
        try:
            while True:
                msg_type, msg = self.queue.get_nowait()
                if msg_type == "log":
                    self._append_log(msg)
                elif msg_type == "result":
                    self._on_sync_complete(msg)
                elif msg_type == "error":
                    self._on_sync_error(msg)
        except queue.Empty:
            pass

        if self.is_running:
            self.root.after(100, self._check_queue)

    def _append_log(self, message: str):
        """Append message to log text."""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def _on_sync_complete(self, success: bool):
        """Handle sync completion."""
        self.is_running = False
        self.launch_button.config(state=tk.NORMAL, bg="#4CAF50")

        if success:
            self.status_label.config(text="Status: Complete")
            self.last_sync_label.config(text=f"Last Sync: {self._get_time()}")
            messagebox.showinfo("Success", "Save sync completed!")
        else:
            self.status_label.config(text="Status: Failed")
            messagebox.showerror("Error", "Save sync failed. Check log for details.")

    def _on_sync_error(self, error: str):
        """Handle sync error."""
        self.is_running = False
        self.launch_button.config(state=tk.NORMAL, bg="#4CAF50")
        self.status_label.config(text="Status: Error")
        messagebox.showerror("Error", f"Sync error: {error}")

    def _get_time(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")


def main():
    """GUI entry point."""
    root = tk.Tk()
    app = SaveSyncGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()