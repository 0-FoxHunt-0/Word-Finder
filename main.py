import sys
import asyncio
from typing import List, Dict, Any

from src.signal_handler import SignalHandler
from src.word_manager import WordManager


async def main() -> None:
    """Main application entry point."""
    # Initialize signal handler and word manager with SQLite database integration
    signal_handler = SignalHandler()
    word_manager = WordManager(
        signal_handler, database_file="database/word_database.db")

    # Set up graceful exit handling
    signal_handler.setup_signal_handlers()

    try:
        # Always show the GUI first, let user decide what to do
        print("Starting Word Finder GUI...")

        from src.word_display_gui import WordDisplayGUI
        display = WordDisplayGUI(word_manager)

        # Show GUI with all cached words (or empty if no words exist)
        # The GUI will provide options to fetch new words if needed
        cached_words = display.create_window(length=None, wait_for_user=True)

        print("GUI closed by user.")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    except Exception as e:
        print(f"Unexpected error in main: {e}")
    finally:
        # Close database connection properly
        word_manager.close_database()
        print("Program finished.")

        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
