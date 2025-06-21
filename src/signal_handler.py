import signal
from typing import Any, Callable, Optional


class SignalHandler:
    """Handles interrupt signals for graceful application shutdown."""

    def __init__(self):
        self.should_exit: bool = False
        self.shutdown_callback: Optional[Callable] = None

    def set_shutdown_callback(self, callback: Callable) -> None:
        """Set a callback function to be called during shutdown."""
        self.shutdown_callback = callback

    def signal_handler(self, signum: int, frame: Any) -> None:
        """Handle interrupt signals for graceful exit."""
        print(
            f"\n\nReceived interrupt signal ({signum}). Initiating graceful shutdown...")
        print("Finishing current request and saving partial results...")
        self.should_exit = True

        if self.shutdown_callback:
            self.shutdown_callback()

    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful exit."""
        signal.signal(signal.SIGINT, self.signal_handler)  # Ctrl+C
        if hasattr(signal, 'SIGTERM'):
            # Termination signal
            signal.signal(signal.SIGTERM, self.signal_handler)

    def is_exit_requested(self) -> bool:
        """Check if graceful exit has been requested."""
        return self.should_exit

    def reset(self) -> None:
        """Reset the exit flag (useful for testing or reuse)."""
        self.should_exit = False
