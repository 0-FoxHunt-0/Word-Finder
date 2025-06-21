"""
Source code package for Word Finder application.

This package contains the main application logic including:
- WordManager: Core word fetching and database management
- WordDisplay: Console-based word display functionality  
- WordDisplayGUI: GUI interface for word browsing
- SignalHandler: Graceful interruption handling
"""

__version__ = "2.0.0"
__author__ = "Word Finder Team"

# Main components
from .word_manager import WordManager
from .word_display import WordDisplay
from .word_display_gui import WordDisplayGUI
from .signal_handler import SignalHandler

__all__ = [
    'WordManager',
    'WordDisplay',
    'WordDisplayGUI',
    'SignalHandler'
]
