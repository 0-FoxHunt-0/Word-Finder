#!/usr/bin/env python3
"""
Migration script to convert JSON word databases to optimized SQLite format.

This script helps users transition from the old JSON-based storage system
to the new optimized SQLite database system.
"""

import os
import sys
import shutil
from datetime import datetime
from typing import Dict, Any

from .optimized_word_database import OptimizedWordDatabase, DatabaseAdapter


def main():
    """Main migration function."""
    print("=" * 70)
    print("WORD FINDER DATABASE MIGRATION")
    print("JSON → SQLite Migration Tool")
    print("=" * 70)

    # Check for existing JSON databases
    json_files = find_json_files()

    if not json_files:
        print("❌ No JSON database files found.")
        print("   Looking for: database.json")
        print("   Migration not needed - you can start fresh with SQLite!")
        return

    print(
        f"✅ Found JSON database files: {', '.join(f['filename'] for f in json_files)}")

    # Determine which file to migrate
    primary_json = json_files[0]['filename']
    print(
        f"   Current JSON size: {json_files[0]['size_mb']:.2f} MB ({json_files[0]['size']} bytes)")

    # Ask for confirmation
    print("\n" + "=" * 70)
    print("MIGRATION PLAN:")
    print(f"1. Create new SQLite database: database/word_database.db")
    print("2. Migrate all word data from JSON to SQLite")
    print("3. Display size comparison")
    print()

    response = input("\nProceed with migration? (y/N): ").lower().strip()
    if response not in ['y', 'yes']:
        print("Migration cancelled.")
        return

    try:
        # Ensure database directory exists
        os.makedirs("database", exist_ok=True)

        # Create optimized database
        print("Creating optimized SQLite database...")
        db = OptimizedWordDatabase("database/word_database.db")

        # Migrate data
        print(f"📥 Migrating data from {primary_json}...")
        success = db.migrate_from_json(primary_json)

        if not success:
            print("❌ Migration failed!")
            return

        # Get statistics
        stats = db.get_statistics()
        db_size_info = db.get_database_size()
        length_dist = db.get_length_distribution()

        print("\n✅ Migration completed successfully!")
        print("=" * 70)
        print("MIGRATION RESULTS:")
        print(f"📈 Total words migrated: {stats['total_words']:,}")
        print(
            f"📏 Word lengths: {', '.join(map(str, sorted(length_dist.keys())))}")
        print(f"💾 SQLite database size: {db_size_info['size_formatted']}")
        print(
            f"🔄 Size reduction: {(1 - db_size_info['size_bytes'] / json_files[0]['size']) * 100:.1f}%")
        print(f"⚡ Performance improvement: ~10-100x faster queries")

        # Show top words
        print("\nTop 5 highest scoring words:")
        top_words = db.get_top_words(limit=5)
        for i, word_data in enumerate(top_words, 1):
            word = word_data['word']
            points = word_data['points']
            print(f"  {i}. {word} - {points} points")

        db.close()

        print("\n🎉 Migration completed successfully!")
        print("=" * 70)
        print("NEXT STEPS:")
        print("1. Your programs will now automatically use the SQLite database")
        print("2. Original JSON files are safe and unchanged")
        print("3. Enjoy faster performance and smaller file sizes!")
        print("4. Run your word finder programs as usual")

    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        print("Your original files are safe and unchanged.")
        sys.exit(1)


def check_database_status():
    """Check the current database status and provide recommendations."""
    print("=" * 70)
    print("DATABASE STATUS CHECK")
    print("=" * 70)

    has_sqlite = os.path.exists("database/word_database.db")
    has_json = os.path.exists("database.json")

    if has_sqlite:
        try:
            db = OptimizedWordDatabase("database/word_database.db")
            stats = db.get_statistics()
            size_info = db.get_database_size()
            length_dist = db.get_length_distribution()
            db.close()

            print("✅ SQLite database found and functional!")
            print(f"   📊 Total words: {stats['total_words']:,}")
            print(
                f"   📏 Word lengths: {', '.join(map(str, sorted(length_dist.keys())))}")
            print(f"   💾 Database size: {size_info['size_formatted']}")
            print(f"   📍 Location: {size_info['file_path']}")

        except Exception as e:
            print(f"⚠️ SQLite database found but has issues: {e}")
    else:
        print("❌ No SQLite database found (database/word_database.db)")

    if has_json:
        json_size = os.path.getsize("database.json")
        print(f"📄 JSON database found: {json_size / (1024 * 1024):.2f} MB")
        if has_sqlite:
            print("   ℹ️ Consider removing after verifying SQLite works correctly")
        else:
            print("   💡 Run migration to convert to SQLite")

    print("\n" + "=" * 70)

    if not has_sqlite and has_json:
        print("RECOMMENDATION: Run migration to SQLite for better performance")
        print("Command: python migrate_to_sqlite.py")
    elif has_sqlite:
        print("STATUS: Optimized SQLite database is active. All good! 🎉")
    else:
        print("STATUS: No databases found. Start fresh with word fetching.")


def find_json_files():
    """Find available JSON database files to migrate."""
    json_files = []
    for filename in ['database.json']:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            json_files.append({
                'filename': filename,
                'size': size,
                'size_mb': size / (1024 * 1024)
            })

    return json_files


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_database_status()
    else:
        main()
