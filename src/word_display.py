import json
import os
from typing import List, Dict, Any, Optional


class WordDisplay:
    """Handles displaying cached words in various formats using optimized SQL database."""

    def __init__(self, word_manager):
        self.word_manager = word_manager

    def display_cached_words(self, length: int, wait_for_user: bool = True) -> List[Dict[str, Any]]:
        """
        Display all cached words matching the query in alphabetical order using SQL queries.

        Args:
            length: Word length to search for
            wait_for_user: Whether to wait for user input before continuing

        Returns:
            List of cached words matching the query
        """
        print(f"\n{'='*70}")
        print(f"CACHED {length}-LETTER WORDS (SQLite Database)")
        print(f"{'='*70}")

        # Use optimized SQL query to get words by length
        cached_words = self.word_manager.db.get_words_by_length(length)

        if not cached_words:
            print(f"No {length}-letter words found in database cache.")
            print("Starting fresh fetch from API...")
            if wait_for_user:
                input("Press Enter to continue...")
            return []

        # Words are already sorted by points (descending) from SQL query
        # Sort alphabetically for display
        sorted_words = sorted(
            cached_words, key=lambda x: x.get('word', '').lower())

        print(f"Found {len(sorted_words)} cached {length}-letter words:")
        print(f"{'='*70}")

        # Display words in a formatted table
        self._display_words_table(sorted_words)

        # Display summary statistics using optimized SQL queries
        self._display_summary_stats(length)

        if wait_for_user:
            print(f"\n{'='*70}")
            choice = input("Continue with API fetch? (y/n): ").lower().strip()
            if choice in ['n', 'no']:
                print("Exiting without fetching new words.")
                return sorted_words

        return sorted_words

    def _display_words_table(self, words: List[Dict[str, Any]], words_per_page: int = 20) -> None:
        """Display words in a formatted table with pagination."""
        total_words = len(words)
        total_pages = (total_words + words_per_page - 1) // words_per_page

        for page in range(total_pages):
            start_idx = page * words_per_page
            end_idx = min(start_idx + words_per_page, total_words)
            page_words = words[start_idx:end_idx]

            print(
                f"\nPage {page + 1} of {total_pages} (Words {start_idx + 1}-{end_idx})")
            print(f"{'#':<4} {'Word':<12} {'Points':<8} {'Dictionary Matches'}")
            print(f"{'-'*4} {'-'*12} {'-'*8} {'-'*30}")

            for i, word_data in enumerate(page_words, start_idx + 1):
                word = word_data.get('word', 'N/A')
                points = word_data.get('points', 0)
                dict_matches = self._format_dict_matches(
                    word_data.get('dict_matches', {}))

                print(f"{i:<4} {word:<12} {points:<8} {dict_matches}")

            # Show pagination controls if there are more pages
            if page < total_pages - 1:
                print(f"\n{'-'*70}")
                choice = input(
                    "Press Enter for next page, or 'q' to skip to summary: ").lower().strip()
                if choice == 'q':
                    break

    def _format_dict_matches(self, dict_matches: Dict[str, bool]) -> str:
        """Format dictionary matches for display."""
        if not dict_matches:
            return "No data"

        matches = []
        for game, is_match in dict_matches.items():
            if is_match:
                matches.append(game.upper())

        return ", ".join(matches) if matches else "None"

    def _display_summary_stats(self, length: int) -> None:
        """Display summary statistics for the cached words using optimized SQL queries."""
        print(f"\n{'='*70}")
        print(f"SUMMARY STATISTICS FOR {length}-LETTER WORDS (SQL Database)")
        print(f"{'='*70}")

        # Use optimized database statistics
        stats = self.word_manager.get_database_statistics(length)
        top_words = self.word_manager.db.get_top_words(length, limit=5)

        print(f"Total cached words: {stats['total_words']:,}")
        print(f"Average points per word: {stats['average_points']:.2f}")
        print(
            f"Highest scoring word: {stats['highest_word']} ({stats['highest_points']} points)")
        print(f"Lowest scoring word points: {stats['lowest_points']}")
        print(f"Total points across all words: {stats['total_points']:,}")

        print(f"\nTop 5 highest scoring words:")
        print(f"{'Rank':<6} {'Word':<12} {'Points':<8} {'Dict Matches'}")
        print(f"{'-'*6} {'-'*12} {'-'*8} {'-'*20}")

        for i, word_data in enumerate(top_words, 1):
            word = word_data.get('word', 'N/A')
            points = word_data.get('points', 0)
            dict_matches = self._format_dict_matches(
                word_data.get('dict_matches', {}))
            print(f"{i:<6} {word:<12} {points:<8} {dict_matches}")

    def display_all_cached_lengths(self) -> None:
        """Display summary of all cached word lengths using SQL queries."""
        print(f"\n{'='*70}")
        print("CACHED WORDS SUMMARY - ALL LENGTHS (SQLite Database)")
        print(f"{'='*70}")

        # Use optimized database query for length distribution
        length_distribution = self.word_manager.get_length_distribution()
        database_info = self.word_manager.get_database_size_info()

        if not length_distribution:
            print("No cached words found in database.")
            return

        print(
            f"{'Length':<8} {'Words':<10} {'Avg Points':<12} {'Top Word':<15} {'Top Points'}")
        print(f"{'-'*8} {'-'*10} {'-'*12} {'-'*15} {'-'*10}")

        total_words = 0
        for length in sorted(length_distribution.keys()):
            word_count = length_distribution[length]
            total_words += word_count

            # Get stats for this length
            length_stats = self.word_manager.get_database_statistics(length)
            avg_points = length_stats['average_points']
            top_word = length_stats['highest_word']
            top_points = length_stats['highest_points']

            print(
                f"{length:<8} {word_count:<10,} {avg_points:<12.2f} {top_word:<15} {top_points}")

        print(f"\nDatabase Summary:")
        print(f"  Total words across all lengths: {total_words:,}")
        print(f"  Database file size: {database_info['size_formatted']}")
        print(f"  Database location: {database_info['file_path']}")

    def search_cached_words(self, length: int, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for specific words in the cache using optimized SQL queries.

        Args:
            length: Word length to search in
            search_term: Term to search for (supports partial matches)

        Returns:
            List of matching words
        """
        print(f"Searching {length}-letter words containing '{search_term}'...")

        # Use optimized SQL search
        pattern = f"%{search_term.lower()}%"
        matching_words = self.word_manager.db.search_words(
            pattern=pattern,
            contains=search_term.lower()
        )

        # Filter by length
        matching_words = [
            word for word in matching_words if len(word['word']) == length]

        if not matching_words:
            print(f"No {length}-letter words found containing '{search_term}'.")
            return []

        print(f"Found {len(matching_words)} matching words:")
        print(f"{'#':<4} {'Word':<12} {'Points':<8} {'Dictionary Matches'}")
        print(f"{'-'*4} {'-'*12} {'-'*8} {'-'*30}")

        # Sort by points (descending)
        matching_words.sort(key=lambda x: x.get('points', 0), reverse=True)

        for i, word_data in enumerate(matching_words, 1):
            word = word_data.get('word', 'N/A')
            points = word_data.get('points', 0)
            dict_matches = self._format_dict_matches(
                word_data.get('dict_matches', {}))
            print(f"{i:<4} {word:<12} {points:<8} {dict_matches}")

        return matching_words

    def search_by_points(self, length: int, min_points: int = None, max_points: int = None) -> List[Dict[str, Any]]:
        """
        Search for words by point range using optimized SQL queries.

        Args:
            length: Word length to search in
            min_points: Minimum points (inclusive)
            max_points: Maximum points (inclusive)

        Returns:
            List of matching words
        """
        print(f"Searching {length}-letter words ", end="")
        if min_points is not None and max_points is not None:
            print(f"with {min_points}-{max_points} points...")
        elif min_points is not None:
            print(f"with at least {min_points} points...")
        elif max_points is not None:
            print(f"with at most {max_points} points...")
        else:
            print("(no point restrictions)...")

        # Use optimized SQL search
        matching_words = self.word_manager.db.search_words(
            min_points=min_points,
            max_points=max_points
        )

        # Filter by length
        matching_words = [
            word for word in matching_words if len(word['word']) == length]

        if not matching_words:
            print(
                f"No {length}-letter words found with the specified point range.")
            return []

        print(f"Found {len(matching_words)} matching words:")
        self._display_words_table(matching_words, words_per_page=15)

        return matching_words

    def show_database_info(self) -> None:
        """Display comprehensive database information."""
        print(f"\n{'='*70}")
        print("DATABASE INFORMATION (SQLite)")
        print(f"{'='*70}")

        # Get database size and overall statistics
        size_info = self.word_manager.get_database_size_info()
        overall_stats = self.word_manager.get_database_statistics()
        length_distribution = self.word_manager.get_length_distribution()

        print(f"Database file: {size_info['file_path']}")
        print(
            f"Database size: {size_info['size_formatted']} ({size_info['size_bytes']} bytes)")
        print(f"Total words: {overall_stats['total_words']:,}")
        print(f"Average points: {overall_stats['average_points']:.2f}")
        print(
            f"Highest scoring word: {overall_stats['highest_word']} ({overall_stats['highest_points']} points)")
        print(f"Total points sum: {overall_stats['total_points']:,}")

        print(f"\nWord Length Distribution:")
        for length, count in sorted(length_distribution.items()):
            percentage = (count / overall_stats['total_words']) * 100
            print(f"  {length}-letter: {count:,} words ({percentage:.1f}%)")

        print(f"\n{'='*70}")


def main():
    """Demo the WordDisplay functionality with SQL database."""
    from src.word_manager import WordManager

    try:
        word_manager = WordManager(database_file="database/word_database.db")
        display = WordDisplay(word_manager)

        print("Word Display Demo with SQLite Database")
        print("=" * 50)

        # Show database info
        display.show_database_info()

        # Demo length-specific display
        length = 3
        print(f"\nDisplaying {length}-letter words:")
        cached_words = display.display_cached_words(length)

        if cached_words:
            # Demo search functionality
            search_term = input(
                "\nEnter a search term (or press Enter to skip): ").strip()
            if search_term:
                display.search_cached_words(length, search_term)

            # Demo point-based search
            try:
                min_points = input(
                    "Enter minimum points (or press Enter to skip): ").strip()
                min_points = int(min_points) if min_points else None
                max_points = input(
                    "Enter maximum points (or press Enter to skip): ").strip()
                max_points = int(max_points) if max_points else None

                if min_points is not None or max_points is not None:
                    display.search_by_points(length, min_points, max_points)
            except ValueError:
                print("Invalid point values entered.")

        # Close database connection
        word_manager.close_database()

    except Exception as e:
        print(f"Error running demo: {e}")


if __name__ == "__main__":
    main()
