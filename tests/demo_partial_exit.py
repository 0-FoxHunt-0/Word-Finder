import sys
import time
import threading
import asyncio
from typing import List, Dict, Any

from signal_handler import SignalHandler
from word_manager import WordManager


def auto_interrupt(signal_handler: SignalHandler, delay: int = 10):
    """Automatically trigger an interrupt after a delay to demonstrate partial exit."""
    time.sleep(delay)
    print(
        f"\n[DEMO] Auto-interrupting after {delay} seconds to demonstrate partial exit...")
    signal_handler.should_exit = True


async def main() -> None:
    """Demonstration of partial exit functionality."""
    print("=== PARTIAL EXIT DEMONSTRATION ===")
    print("This demo will fetch 4-letter words and automatically interrupt after 10 seconds")
    print("to demonstrate the partial exit and database merge functionality.\n")

    # Initialize signal handler and word manager
    signal_handler = SignalHandler()
    word_manager = WordManager(
        signal_handler, database_file="database/word_database.db")

    # Set up graceful exit handling
    signal_handler.setup_signal_handlers()

    # Start auto-interrupt thread for demonstration
    interrupt_thread = threading.Thread(
        target=auto_interrupt, args=(signal_handler, 10))
    interrupt_thread.daemon = True
    interrupt_thread.start()

    all_words = []  # Initialize for proper scope
    try:
        print("Starting to fetch 4-letter words...")
        print(
            "Will auto-interrupt in 10 seconds to demonstrate partial results handling...\n")

        all_words: List[Dict[str, Any]] = await word_manager.fetch_all_words(
            length=4, page_size=50, show_cached=True)

        if all_words:
            # This will be a partial result due to auto-interrupt
            is_partial_result: bool = signal_handler.is_exit_requested()
            filename: str = "demo_partial_4_letter_words.json" if is_partial_result else "demo_all_4_letter_words.json"

            # Save all words to separate file
            word_manager.save_words_to_file(
                all_words, filename, is_partial_result)

            # Show top 10 words by points
            top_words: List[Dict[str, Any]
                            ] = word_manager.get_top_words(all_words, 10)
            result_type: str = "partial" if is_partial_result else "complete"
            print(
                f"\nTop 10 highest scoring 4-letter words ({result_type} results):")
            for i, word_data in enumerate(top_words, 1):
                word: str = word_data['word']
                points: int = word_data['points']
                print(f"{i:2d}. {word:8s} - {points} points")

            # Show statistics
            stats = word_manager.calculate_statistics(all_words)
            print(f"\nStatistics ({result_type} results):")
            print(f"Total words collected: {stats['total_words']:,}")
            print(f"Average points per word: {stats['average_points']:.2f}")
            print(
                f"Highest scoring word: {stats['highest_word']} ({stats['highest_points']} points)")
            print(
                f"Total points across collected words: {stats['total_points']:,}")

            if is_partial_result:
                print(
                    f"\n[DEMO SUCCESS] Partial results have been merged with the database!")
                print(
                    f"The database now contains 4-letter words alongside existing words.")
                print(
                    f"If you run this demo again, it will continue from where it left off.")
            else:
                print(f"\nComplete dataset has been merged with the database.")
        else:
            print("No words were fetched!")

    except Exception as e:
        print(f"Unexpected error in demo: {e}")
    finally:
        print("\n=== DEMO COMPLETED ===")
        print(f"✅ Graceful exit completed!")
        print(f"   📊 Words saved: {len(all_words)}")
        try:
            size_info = word_manager.get_database_size_info()
            print(f"   💾 Database size: {size_info['size_formatted']}")
        except:
            print(f"   💾 Database location: {word_manager.database_file}")
        print(f"   📍 Database file: {word_manager.database_file}")
        print("   🔄 You can resume fetching from where you left off.")
        print("   📈 All data is safely stored in SQLite database.")


if __name__ == "__main__":
    asyncio.run(main())
