"""
Database package for Word Finder application.

This package contains database-related functionality including:
- OptimizedWordDatabase: SQLite database implementation with performance optimizations
- DatabaseAdapter: Compatibility layer for existing code
- Migration tools: Scripts for transitioning from JSON to SQLite
"""

__version__ = "2.0.0"
__author__ = "Word Finder Team"

# Database components
from .optimized_word_database import OptimizedWordDatabase, DatabaseAdapter

__all__ = [
    'OptimizedWordDatabase',
    'DatabaseAdapter'
]
