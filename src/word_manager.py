import json
import httpx
import asyncio
import time
import shutil
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

# Import the optimized database components
from database.optimized_word_database import OptimizedWordDatabase, DatabaseAdapter


class WordManager:
    """Manages word fetching, processing, and file operations using optimized SQLite database."""

    def __init__(self, signal_handler=None, database_file: str = "database/word_database.db"):
        self.signal_handler = signal_handler
        self.partial_words: List[Dict[str, Any]] = []
        self.base_url: str = "https://fly.wordfinderapi.com/api/search"

        # Use optimized database instead of JSON
        self.database_file = database_file

        # Ensure the database directory exists
        db_dir = os.path.dirname(self.database_file)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # Initialize the optimized database and adapter
        self.db = OptimizedWordDatabase(database_file)
        self.db_adapter = DatabaseAdapter(database_file)

        # Migrate from JSON if it exists
        self._migrate_from_json_if_exists()

    def _migrate_from_json_if_exists(self):
        """Migrate from old JSON database if it exists."""
        json_database_file = "database.json"
        if os.path.exists(json_database_file):
            print(f"Found existing JSON database. Migrating to SQLite...")
            success = self.db.migrate_from_json(json_database_file)
            if success:
                print("Migration completed successfully!")
                print(
                    f"JSON database backed up as {json_database_file}.backup")
                shutil.move(json_database_file, f"{json_database_file}.backup")
            else:
                print("Migration failed. Continuing with empty database.")

    def load_database(self) -> Dict[str, Any]:
        """Load the existing database or return empty structure (compatibility method)."""
        return self.db_adapter.load_database()

    def _create_empty_database_structure(self) -> Dict[str, Any]:
        """Create an empty database structure (compatibility method)."""
        return {
            "request": {
                "letters": "", "starts_with": "", "ends_with": "",
                "shorter_than": 0, "longer_than": 0, "length": 0,
                "must_contain": "", "must_not_contain": "", "must_contain_multiple": "",
                "must_contain_char1": "", "must_contain_char2": "", "contains": "",
                "not_contains": "", "include_letters": "", "exclude_letters": "",
                "contains_multiple": "", "contains_char1": "", "contains_char2": "",
                "pattern": "", "regexp": "", "dictionary": "all_en",
                "return_results": True, "pre_defined": False, "is_search": False,
                "group_by_length": True, "page_size": 0, "page_token": 0,
                "sort_alphabet": False, "word_sorting": "points", "letter_limit": 0
            },
            "letters_for_search": "", "search_results": 0, "search_duration": 0,
            "filter_results": 0, "filter_duration": 0, "word_pages": [],
            "returned_results": 0, "pagination_duration": 0,
            "dict_matches": {
                "octordle": False, "otcwl": False, "quordle": False,
                "sowpods": False, "wordle": False, "wwf": False
            },
            "has_dict_match": False,
            "last_updated": datetime.now().isoformat(),
            "version": "2.0_sqlite"
        }

    def _ensure_word_has_dict_matches(self, word_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure a word has the dictionary matches structure."""
        if 'dict_matches' not in word_data or not word_data['dict_matches']:
            word_data['dict_matches'] = {
                "octordle": False, "otcwl": False, "quordle": False,
                "sowpods": False, "wordle": False, "wwf": False
            }
        else:
            default_dicts = {
                "octordle": False, "otcwl": False, "quordle": False,
                "sowpods": False, "wordle": False, "wwf": False
            }
            word_data['dict_matches'] = {
                **default_dicts, **word_data['dict_matches']}
        return word_data

    def extract_words_from_database(self, database: Dict[str, Any] = None, target_length: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract words from the database, using optimized SQL queries."""
        return self.db_adapter.extract_words_from_database(database or {}, target_length)

    def merge_word_data(self, existing_words: List[Dict[str, Any]], new_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge new words with existing words using optimized database operations."""
        return self.db_adapter.merge_word_data(existing_words, new_words)

    def update_database_structure(self, database: Dict[str, Any], merged_words: List[Dict[str, Any]],
                                  length: int, is_partial: bool = False) -> Dict[str, Any]:
        """Update the database structure (compatibility method - SQLite handles this automatically)."""
        # SQLite handles the structure automatically, just return the database dict for compatibility
        database["last_updated"] = datetime.now().isoformat()
        database["request"]["length"] = length

        if is_partial:
            database["partial_update"] = True
            database["partial_update_timestamp"] = datetime.now().isoformat()
            database[f"partial_update_length_{length}"] = True
        else:
            database["partial_update"] = False
            database["complete_update_timestamp"] = datetime.now().isoformat()
            database[f"complete_update_length_{length}"] = True

        return database

    def save_database(self, database: Dict[str, Any]) -> bool:
        """Save the updated database (compatibility method - SQLite auto-saves)."""
        return self.db_adapter.save_database(database)

    def merge_with_database(self, new_words: List[Dict[str, Any]], length: int, is_partial: bool = False) -> bool:
        """Main method to merge new words with existing database using optimized SQL operations."""
        if not new_words:
            print("No new words to merge with database")
            return False

        print(
            f"\nStarting database merge process for {length}-letter words...")
        print(f"New words to process: {len(new_words)}")

        try:
            # Get existing words count for this length
            existing_words = self.db.get_words_by_length(length)
            print(
                f"Existing {length}-letter words in database: {len(existing_words)}")

            # Insert new words using batch operation
            rows_inserted = self.db.insert_words_batch(new_words)
            print(
                f"Database batch insert completed: {rows_inserted} words processed")

            # Get updated count
            updated_words = self.db.get_words_by_length(length)
            print(
                f"Total {length}-letter words after merge: {len(updated_words)}")

            result_type = "partial" if is_partial else "complete"
            print(
                f"Database merge completed successfully for {length}-letter words ({result_type} update)")

            # Display database size info
            size_info = self.db.get_database_size()
            print(f"Database size: {size_info['size_formatted']}")

            return True

        except Exception as e:
            print(f"Error during database merge: {e}")
            return False

    def show_cached_words_before_fetch(self, length: int) -> bool:
        """Display cached words before starting a fetch operation using GUI."""
        try:
            from .word_display_gui import WordDisplayGUI
            display = WordDisplayGUI(self)
            cached_words = display.create_window(length, wait_for_user=True)

            if not cached_words:
                return True

            return display.continue_fetch

        except ImportError:
            print("WordDisplayGUI module not found. Trying console display...")
            try:
                from .word_display import WordDisplay
                display = WordDisplay(self)
                cached_words = display.display_cached_words(
                    length, wait_for_user=True)
                return True
            except ImportError:
                print("No display modules found. Continuing with fetch...")
                return True
        except Exception as e:
            print(f"Error displaying cached words: {e}")
            print("Continuing with fetch...")
            return True

    async def fetch_all_words(self, length: int = 2, page_size: int = 50, show_cached: bool = True) -> List[Dict[str, Any]]:
        """Fetch all words from the WordFinder API for a given length using async requests."""
        # Show cached words first if requested
        if show_cached:
            try:
                from .word_display_gui import WordDisplayGUI
                display = WordDisplayGUI(self)
                cached_words = display.create_window(
                    length, wait_for_user=True)

                if cached_words and not display.continue_fetch:
                    print("User cancelled API fetch. Returning cached words only.")
                    return cached_words

            except ImportError:
                print("WordDisplayGUI module not found. Trying console display...")
                try:
                    from .word_display import WordDisplay
                    display = WordDisplay(self)
                    cached_words = display.display_cached_words(
                        length, wait_for_user=True)
                except ImportError:
                    print("No display modules found. Continuing with fetch...")
            except Exception as e:
                print(f"Error displaying cached words: {e}")
                print("Continuing with fetch...")

        base_params: Dict[str, Any] = {
            "length": length,
            "word_sorting": "points",
            "group_by_length": True,
            "page_size": page_size,
            "dictionary": "all_en"
        }

        all_words: List[Dict[str, Any]] = []
        self.partial_words = all_words

        async with httpx.AsyncClient() as client:
            try:
                print("Making initial request to get pagination info...")
                if self._should_exit():
                    return all_words

                response = await client.get(self.base_url, params=base_params)
                response_data: Dict[str, Any] = response.json()

                word_pages: List[Dict[str, Any]
                                 ] = response_data.get("word_pages", [])
                if not word_pages:
                    print("No word pages found in response")
                    return all_words

                first_page: Dict[str, Any] = word_pages[0]
                total_pages: int = first_page.get("num_pages", 1)
                total_words: int = first_page.get("num_words", 0)

                print(
                    f"Found {total_words} total words across {total_pages} pages")

                first_page_words: List[Dict[str, Any]
                                       ] = first_page.get("word_list", [])
                all_words.extend(first_page_words)
                print(
                    f"Page 1/{total_pages}: Added {len(first_page_words)} words")

                print(
                    "Press Ctrl+C at any time to stop gracefully and save partial results...")

                if self._should_exit():
                    self.merge_with_database(
                        all_words, length, is_partial=True)
                    return all_words

                # Fetch remaining pages
                for page_num in range(2, total_pages + 1):
                    if self._should_exit():
                        print(
                            f"Graceful exit requested. Stopping at page {page_num-1}/{total_pages}")
                        self.merge_with_database(
                            all_words, length, is_partial=True)
                        break

                    try:
                        page_params: Dict[str, Any] = base_params.copy()
                        page_params["page_token"] = page_num - 1

                        print(f"Fetching page {page_num}/{total_pages}...")
                        page_response = await client.get(self.base_url, params=page_params)
                        page_response_data: Dict[str,
                                                 Any] = page_response.json()

                        page_word_pages: List[Dict[str, Any]] = page_response_data.get(
                            "word_pages", [])
                        if page_word_pages:
                            page_words: List[Dict[str, Any]] = page_word_pages[0].get(
                                "word_list", [])
                            all_words.extend(page_words)
                            print(
                                f"Page {page_num}/{total_pages}: Added {len(page_words)} words")
                        else:
                            print(
                                f"Page {page_num}/{total_pages}: No words found")

                        if not self._should_exit():
                            await asyncio.sleep(0.1)

                    except KeyboardInterrupt:
                        print(
                            f"\nKeyboard interrupt detected at page {page_num}")
                        if self.signal_handler:
                            self.signal_handler.should_exit = True
                        self.merge_with_database(
                            all_words, length, is_partial=True)
                        break
                    except Exception as e:
                        print(f"Error fetching page {page_num}: {e}")
                        if self._should_exit():
                            self.merge_with_database(
                                all_words, length, is_partial=True)
                            break

                if self._should_exit():
                    print(
                        f"\nGraceful exit completed. Collected {len(all_words)} words before stopping.")
                else:
                    print(
                        f"\nCompleted! Total words collected: {len(all_words)}")
                    self.merge_with_database(
                        all_words, length, is_partial=False)

            except KeyboardInterrupt:
                print(f"\nKeyboard interrupt detected during initial setup.")
                if self.signal_handler:
                    self.signal_handler.should_exit = True
                if all_words:
                    self.merge_with_database(
                        all_words, length, is_partial=True)
            except Exception as e:
                print(f"Unexpected error: {e}")
                if self.signal_handler:
                    self.signal_handler.should_exit = True
                if all_words:
                    self.merge_with_database(
                        all_words, length, is_partial=True)

        return all_words

    async def fetch_multiple_lengths_concurrent(self, lengths: List[int], page_size: int = 50) -> Dict[int, List[Dict[str, Any]]]:
        """Fetch words for multiple lengths concurrently using async requests."""
        print(f"Starting concurrent fetch for lengths: {lengths}")

        tasks = []
        for length in lengths:
            task = asyncio.create_task(self.fetch_all_words(
                length, page_size, show_cached=False))
            tasks.append((length, task))

        results = {}
        for length, task in tasks:
            try:
                words = await task
                results[length] = words
                print(
                    f"Completed fetching {len(words)} words for length {length}")
            except Exception as e:
                print(f"Error fetching words for length {length}: {e}")
                results[length] = []

        return results

    async def fetch_multiple_lengths_sequential(self, lengths: List[int], page_size: int = 50, progress_callback=None) -> Dict[int, List[Dict[str, Any]]]:
        """Fetch words for multiple lengths sequentially to respect API limits and provide better progress tracking."""
        print(f"Starting sequential fetch for lengths: {lengths}")

        results = {}
        total_lengths = len(lengths)

        for i, length in enumerate(lengths):
            length_prefix = f"[Length {length} ({i+1}/{total_lengths})]"
            print(
                f"Fetching words for length {length} ({i+1}/{total_lengths})...")

            try:
                # Use custom fetch method that provides page-level progress
                words = await self._fetch_single_length_with_progress(
                    length, page_size, progress_callback, length_prefix
                )
                results[length] = words

                print(
                    f"Completed fetching {len(words)} words for length {length}")

                # Add a small delay between requests to be respectful to the API
                if i < total_lengths - 1:  # Don't delay after the last request
                    # 1 second delay between different lengths
                    await asyncio.sleep(1.0)

            except Exception as e:
                print(f"Error fetching words for length {length}: {e}")
                results[length] = []

        total_words = sum(len(words) for words in results.values())
        print(
            f"Sequential fetch completed: {total_words} total words across {len(lengths)} lengths")

        return results

    async def _fetch_single_length_with_progress(self, length: int, page_size: int, progress_callback, length_prefix: str) -> List[Dict[str, Any]]:
        """Fetch words for a single length with detailed page-level progress tracking."""
        import httpx
        import asyncio

        base_params: Dict[str, Any] = {
            "length": length,
            "word_sorting": "points",
            "group_by_length": True,
            "page_size": page_size,
            "dictionary": "all_en"
        }

        all_words: List[Dict[str, Any]] = []
        self.partial_words = all_words

        async with httpx.AsyncClient() as client:
            try:
                if progress_callback:
                    progress_callback(
                        0, 1, f"{length_prefix} Getting pagination info...")

                if self._should_exit():
                    return all_words

                response = await client.get(self.base_url, params=base_params)
                response_data: Dict[str, Any] = response.json()

                word_pages: List[Dict[str, Any]
                                 ] = response_data.get("word_pages", [])
                if not word_pages:
                    print(f"{length_prefix} No word pages found in response")
                    return all_words

                first_page: Dict[str, Any] = word_pages[0]
                total_pages: int = first_page.get("num_pages", 1)
                total_words: int = first_page.get("num_words", 0)

                print(
                    f"{length_prefix} Found {total_words} total words across {total_pages} pages")

                # Add words from first page
                first_page_words: List[Dict[str, Any]
                                       ] = first_page.get("word_list", [])
                all_words.extend(first_page_words)
                print(
                    f"{length_prefix} Page 1/{total_pages}: Added {len(first_page_words)} words")

                if progress_callback:
                    progress_callback(
                        1, total_pages, f"{length_prefix} Page 1/{total_pages} - {len(first_page_words)} words")

                if self._should_exit():
                    self.merge_with_database(
                        all_words, length, is_partial=True)
                    return all_words

                # Fetch remaining pages with progress updates
                for page_num in range(2, total_pages + 1):
                    if self._should_exit():
                        print(
                            f"{length_prefix} Graceful exit requested. Stopping at page {page_num-1}/{total_pages}")
                        self.merge_with_database(
                            all_words, length, is_partial=True)
                        break

                    try:
                        page_params: Dict[str, Any] = base_params.copy()
                        page_params["page_token"] = page_num - 1

                        if progress_callback:
                            progress_callback(
                                page_num-1, total_pages, f"{length_prefix} Fetching page {page_num}/{total_pages}...")

                        print(
                            f"{length_prefix} Fetching page {page_num}/{total_pages}...")
                        page_response = await client.get(self.base_url, params=page_params)
                        page_response_data: Dict[str,
                                                 Any] = page_response.json()

                        page_word_pages: List[Dict[str, Any]] = page_response_data.get(
                            "word_pages", [])
                        if page_word_pages:
                            page_words: List[Dict[str, Any]] = page_word_pages[0].get(
                                "word_list", [])
                            all_words.extend(page_words)
                            print(
                                f"{length_prefix} Page {page_num}/{total_pages}: Added {len(page_words)} words")

                            if progress_callback:
                                progress_callback(
                                    page_num, total_pages, f"{length_prefix} Page {page_num}/{total_pages} - {len(page_words)} words (Total: {len(all_words)})")
                        else:
                            print(
                                f"{length_prefix} Page {page_num}/{total_pages}: No words found")
                            if progress_callback:
                                progress_callback(
                                    page_num, total_pages, f"{length_prefix} Page {page_num}/{total_pages} - No words found")

                        if not self._should_exit():
                            await asyncio.sleep(0.1)

                    except KeyboardInterrupt:
                        print(
                            f"\n{length_prefix} Keyboard interrupt detected at page {page_num}")
                        if self.signal_handler:
                            self.signal_handler.should_exit = True
                        self.merge_with_database(
                            all_words, length, is_partial=True)
                        break
                    except Exception as e:
                        print(
                            f"{length_prefix} Error fetching page {page_num}: {e}")
                        if self._should_exit():
                            self.merge_with_database(
                                all_words, length, is_partial=True)
                            break

                if self._should_exit():
                    print(
                        f"\n{length_prefix} Graceful exit completed. Collected {len(all_words)} words before stopping.")
                else:
                    print(
                        f"\n{length_prefix} Completed! Total words collected: {len(all_words)}")
                    self.merge_with_database(
                        all_words, length, is_partial=False)

                    if progress_callback:
                        progress_callback(
                            total_pages, total_pages, f"{length_prefix} Completed - {len(all_words)} words")

            except KeyboardInterrupt:
                print(
                    f"\n{length_prefix} Keyboard interrupt detected during initial setup.")
                if self.signal_handler:
                    self.signal_handler.should_exit = True
                if all_words:
                    self.merge_with_database(
                        all_words, length, is_partial=True)
            except Exception as e:
                print(f"{length_prefix} Unexpected error: {e}")
                if self.signal_handler:
                    self.signal_handler.should_exit = True
                if all_words:
                    self.merge_with_database(
                        all_words, length, is_partial=True)

        return all_words

    def save_words_to_file(self, words: List[Dict[str, Any]], filename: str = "all_words.json", is_partial: bool = False) -> None:
        """Save all words to a JSON file."""
        try:
            with open(filename, 'w') as f:
                json.dump(words, f, indent=2)

            status: str = "partial" if is_partial else "complete"
            print(f"Saved {len(words)} {status} words to {filename}")
        except Exception as e:
            print(f"Error saving words to file: {e}")

    def get_top_words(self, words: List[Dict[str, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
        """Get the top N words by points."""
        return sorted(words, key=lambda x: x.get('points', 0), reverse=True)[:top_n]

    def calculate_statistics(self, words: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics for the word collection."""
        if not words:
            return {
                'total_words': 0, 'total_points': 0, 'average_points': 0.0,
                'highest_word': '', 'highest_points': 0
            }

        total_points: int = sum(word.get('points', 0) for word in words)
        avg_points: float = total_points / len(words)
        top_words = self.get_top_words(words, 1)

        return {
            'total_words': len(words),
            'total_points': total_points,
            'average_points': avg_points,
            'highest_word': top_words[0]['word'] if top_words else '',
            'highest_points': top_words[0]['points'] if top_words else 0
        }

    def get_partial_words(self) -> List[Dict[str, Any]]:
        """Get the current partial words collection."""
        return self.partial_words

    def _should_exit(self) -> bool:
        """Check if we should exit based on signal handler."""
        return self.signal_handler.is_exit_requested() if self.signal_handler else False

    # New methods for enhanced SQL database functionality
    def get_database_statistics(self, length: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive database statistics using optimized SQL queries."""
        return self.db.get_statistics(length)

    def get_length_distribution(self) -> Dict[int, int]:
        """Get word count distribution by length."""
        return self.db.get_length_distribution()

    def search_words(self, pattern: str = None, min_points: int = None,
                     max_points: int = None, contains: str = None) -> List[Dict[str, Any]]:
        """Advanced word search with multiple filters."""
        return self.db.search_words(pattern, min_points, max_points, contains)

    def get_database_size_info(self) -> Dict[str, Any]:
        """Get database size information."""
        return self.db.get_database_size()

    def close_database(self):
        """Close the database connection."""
        if hasattr(self, 'db') and self.db:
            self.db.close()

    def __del__(self):
        """Cleanup database connection when object is destroyed."""
        self.close_database()
