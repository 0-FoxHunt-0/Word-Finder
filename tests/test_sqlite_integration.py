#!/usr/bin/env python3
"""
Test script to verify SQLite database integration is working correctly.
"""

from database.optimized_word_database import OptimizedWordDatabase
import os
import sys
import traceback

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


def test_sqlite_integration():
    """Test the SQLite database integration."""
    print("=" * 60)
    print("TESTING SQLITE DATABASE INTEGRATION")
    print("=" * 60)

    try:
        # Test 1: Database creation
        print("1. Testing database creation...")
        db = OptimizedWordDatabase('test_database.db')
        print("   ✅ Database created successfully")

        # Test 2: Sample data insertion
        print("2. Testing data insertion...")
        sample_words = [
            {
                'word': 'test',
                'points': 10,
                'dict_matches': {
                    'wordle': True,
                    'quordle': False,
                    'sowpods': True,
                    'octordle': False,
                    'otcwl': True,
                    'wwf': False
                }
            },
            {
                'word': 'demo',
                'points': 15,
                'dict_matches': {
                    'wordle': True,
                    'quordle': True,
                    'sowpods': True,
                    'octordle': False,
                    'otcwl': True,
                    'wwf': True
                }
            },
            {
                'word': 'word',
                'points': 8,
                'dict_matches': {
                    'wordle': True,
                    'quordle': True,
                    'sowpods': False,
                    'octordle': True,
                    'otcwl': False,
                    'wwf': True
                }
            }
        ]

        inserted = db.insert_words_batch(sample_words)
        print(f"   ✅ Inserted {inserted} sample words")

        # Test 3: Query by length
        print("3. Testing length-based queries...")
        four_letter_words = db.get_words_by_length(4)
        print(f"   ✅ Retrieved {len(four_letter_words)} 4-letter words")

        # Test 4: Top words query
        print("4. Testing top words query...")
        top_words = db.get_top_words(limit=3)
        print(f"   ✅ Retrieved top {len(top_words)} words")
        for i, word_data in enumerate(top_words, 1):
            print(
                f"      {i}. {word_data['word']} - {word_data['points']} points")

        # Test 5: Statistics
        print("5. Testing statistics...")
        stats = db.get_statistics()
        print(f"   ✅ Total words: {stats['total_words']}")
        print(f"   ✅ Average points: {stats['average_points']:.2f}")
        print(
            f"   ✅ Highest scoring: {stats['highest_word']} ({stats['highest_points']} pts)")

        # Test 6: Search functionality
        print("6. Testing search functionality...")
        search_results = db.search_words(contains='e')
        print(f"   ✅ Found {len(search_results)} words containing 'e'")

        # Test 7: Length distribution
        print("7. Testing length distribution...")
        length_dist = db.get_length_distribution()
        print(f"   ✅ Length distribution: {dict(length_dist)}")

        # Test 8: Database size
        print("8. Testing database size info...")
        size_info = db.get_database_size()
        print(f"   ✅ Database size: {size_info['size_formatted']}")

        # Close database
        db.close()
        print("   ✅ Database closed successfully")

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! SQLite integration is working correctly.")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

    finally:
        # Clean up test database
        if os.path.exists('test_database.db'):
            try:
                os.remove('test_database.db')
                print("🧹 Test database cleaned up")
            except Exception as e:
                print(f"⚠️ Could not clean up test database: {e}")


def test_word_manager_integration():
    """Test the WordManager integration with SQLite."""
    print("\n" + "=" * 60)
    print("TESTING WORD MANAGER INTEGRATION")
    print("=" * 60)

    try:
        from src.word_manager import WordManager

        # Test WordManager initialization
        print("1. Testing WordManager with SQLite...")
        manager = WordManager(database_file="test_word_manager.db")
        print("   ✅ WordManager initialized with SQLite backend")

        # Test database methods
        print("2. Testing enhanced database methods...")
        size_info = manager.get_database_size_info()
        print(f"   ✅ Database size info: {size_info['size_formatted']}")

        # Test statistics (should work even with empty database)
        stats = manager.get_database_statistics()
        print(f"   ✅ Database statistics: {stats['total_words']} words")

        # Test length distribution
        distribution = manager.get_length_distribution()
        print(f"   ✅ Length distribution: {dict(distribution)}")

        # Close database
        manager.close_database()
        print("   ✅ WordManager database closed")

        print("\n🎉 WORD MANAGER INTEGRATION TESTS PASSED!")

        return True

    except Exception as e:
        print(f"\n❌ WORD MANAGER TEST FAILED: {e}")
        traceback.print_exc()
        return False

    finally:
        # Clean up test database
        if os.path.exists('test_word_manager.db'):
            try:
                os.remove('test_word_manager.db')
                print("🧹 WordManager test database cleaned up")
            except Exception as e:
                print(f"⚠️ Could not clean up WordManager test database: {e}")


if __name__ == "__main__":
    print("Word Finder - SQLite Integration Test Suite")
    print("=" * 60)

    # Run tests
    test1_passed = test_sqlite_integration()
    test2_passed = test_word_manager_integration()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(
        f"SQLite Database Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(
        f"WordManager Integration: {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("Your SQLite database implementation is ready to use!")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")

    print("=" * 60)
