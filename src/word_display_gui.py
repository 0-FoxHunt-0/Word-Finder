import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
import os
import re
from typing import List, Dict, Any, Optional
from threading import Thread
import asyncio
import sys
from io import StringIO

from .custom_alert import CustomAlert


class WordDisplayGUI:
    """GUI application for displaying cached words using optimized SQLite database."""

    def __init__(self, word_manager):
        self.word_manager = word_manager
        self.signal_handler = getattr(word_manager, 'signal_handler', None)
        self.root = None
        self.tree = None
        self.search_var = None
        self.length_filter_var = None
        self.length_var = None
        self.stats_text = None
        self.output_text = None
        self.progress_bar = None  # Progress bar widget
        self.progress_label = None  # Progress label widget
        self.cached_words = []
        self.filtered_words = []
        self.continue_fetch = True  # Flag to track user choice
        self.is_dark_theme = True  # Default to dark theme
        self.theme_colors = self._get_theme_colors()
        self.theme_button = None  # Reference to theme button
        self.fetch_in_progress = False
        self.continue_btn = None
        self.cancel_btn = None
        self.word_length = 4  # Store word length for fetch operations

        # Progress tracking variables
        self.total_pages = 0
        self.current_page = 0
        self.progress_percentage = 0

        # Sorting state
        self.current_sort_column = None
        self.sort_direction = {}  # Track sort direction for each column
        self.sort_states = {'none': 0, 'desc': 1,
                            'asc': 2}  # 0=none, 1=desc, 2=asc

        # Search performance optimization
        self.search_delay_timer = None  # Timer for debounced search
        self.search_delay_ms = 100  # 0.1 second delay
        self.last_search_term = ""  # Track last search to avoid redundant searches
        self.last_length_filter = "All"  # Track last length filter

        # Virtual scrolling / lazy loading
        self.virtual_start_index = 0  # Start index of visible items
        self.virtual_page_size = 100  # Number of items to load per page
        self.virtual_buffer_size = 200  # Buffer size for smooth scrolling
        self.virtual_total_items = 0  # Total number of filtered items
        self.virtual_loaded_items = []  # Currently loaded items for display
        self.virtual_scroll_timer = None  # Timer for delayed scroll processing
        self.last_scroll_position = 0.0  # Track last scroll position
        self.virtual_loaded_count = 0  # Number of items currently loaded in table

    def _get_theme_colors(self):
        """Get colors for current theme."""
        if self.is_dark_theme:
            return {
                'bg': '#2b2b2b',
                'fg': '#ffffff',
                'header_bg': '#1a1a1a',
                'header_fg': '#ffffff',
                'search_bg': '#3c3c3c',
                'search_fg': '#ffffff',
                'button_bg': '#404040',
                'button_fg': '#ffffff',
                'button_active': '#505050',
                'stats_bg': '#3c3c3c',
                'stats_fg': '#ffffff',
                'entry_bg': '#404040',
                'entry_fg': '#ffffff',
                'tree_bg': '#2b2b2b',
                'tree_fg': '#ffffff',
                'tree_select': '#404040',
                'output_bg': '#1e1e1e',
                'output_fg': '#00ff00'
            }
        else:
            return {
                'bg': '#f0f0f0',
                'fg': '#000000',
                'header_bg': '#2c3e50',
                'header_fg': '#ffffff',
                'search_bg': '#ecf0f1',
                'search_fg': '#000000',
                'button_bg': '#ffffff',
                'button_fg': '#000000',
                'button_active': '#e0e0e0',
                'stats_bg': '#ffffff',
                'stats_fg': '#000000',
                'entry_bg': '#ffffff',
                'entry_fg': '#000000',
                'tree_bg': '#ffffff',
                'tree_fg': '#000000',
                'tree_select': '#e0e0e0',
                'output_bg': '#ffffff',
                'output_fg': '#000000'
            }

    def create_window(self, length: int = None, wait_for_user: bool = True) -> List[Dict[str, Any]]:
        """
        Create and display the GUI window with cached words from SQLite database.

        Args:
            length: Word length to search for (None means show all cached words)
            wait_for_user: Whether to wait for user input before continuing

        Returns:
            List of cached words matching the query
        """
        # Store the word length for later use (default to 4 for fetch operations)
        self.word_length = length if length is not None else 4

        # Create the main window first for better user experience
        self.root = tk.Tk()

        # Set up window close protocol for graceful exit
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Set initial title
        self.root.title("Word Finder - Loading...")

        # Set window size - height is screen height - 100px for better fit
        self.root.update_idletasks()  # Ensure window is created
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        # Minimum height of 700px, maximum 90% of screen height
        window_height = max(
            700, min(screen_height - 100, int(screen_height * 0.9)))
        # Max 1200px or 80% of screen width
        window_width = min(1200, int(screen_width * 0.8))
        self.root.geometry(f"{window_width}x{window_height}")

        # Make window resizable
        self.root.minsize(800, 600)  # Set minimum size
        self.root.resizable(True, True)

        # Ensure proper window attributes for focus handling
        self.root.wm_attributes('-topmost', False)  # Not always on top
        self.root.focus_set()  # Set initial focus

        # Set up periodic signal checking
        self._check_signals()

        # Set up keyboard shortcuts
        self.root.bind('<Control-c>', self._handle_keyboard_interrupt)
        self.root.bind('<Control-q>', self._handle_keyboard_interrupt)

        # Add Enter key shortcut for starting API fetch (when Continue button is available)
        def handle_main_window_enter(event):
            # Only trigger if Continue button exists and is enabled
            if hasattr(self, 'continue_btn') and self.continue_btn and not self.fetch_in_progress:
                self._start_fetch_in_background()
                return 'break'

        # Bind only specific keys instead of all keys to avoid conflicts
        self.root.bind('<Return>', handle_main_window_enter)
        self.root.bind('<KP_Enter>', handle_main_window_enter)

        self._apply_theme()

        # Create the GUI elements first
        self._create_header()
        self._create_search_frame()
        self._create_words_table()
        self._create_stats_panel()
        self._create_output_panel()
        self._create_control_buttons(wait_for_user)

        # Show loading message
        self._show_loading_indicator("Loading words from database...")

        # Center the window
        self._center_window()

        # Make window modal if waiting for user
        if wait_for_user:
            self.root.transient()
            self.root.grab_set()

        # Ensure window can be focused and brought to front
        self.root.lift()
        self.root.focus_force()

        # Load data asynchronously to prevent UI freezing
        self.root.after(100, lambda: self._load_data_async(length))

        # Start the GUI
        self.root.mainloop()

        return self.cached_words

    def _load_data_async(self, length: int = None):
        """Load data asynchronously to prevent UI freezing during startup."""
        try:
            print("Loading words from SQLite database...")

            if length is not None:
                # Get words for specific length using optimized query
                self.cached_words = self.word_manager.db.get_words_by_length(
                    length)
            else:
                # Get all words using optimized query with progress updates
                self.cached_words = []
                length_distribution = self.word_manager.get_length_distribution()
                total_lengths = len(length_distribution)

                for i, word_length in enumerate(length_distribution.keys()):
                    # Update progress
                    progress_msg = f"Loading {word_length}-letter words... ({i+1}/{total_lengths})"
                    self._show_loading_indicator(progress_msg)

                    # Load words for this length
                    words_for_length = self.word_manager.db.get_words_by_length(
                        word_length)
                    self.cached_words.extend(words_for_length)

                    # Allow GUI to update every few lengths
                    if i % 3 == 0:
                        self.root.update_idletasks()

            # Sort words alphabetically (limit sorting for very large datasets)
            if len(self.cached_words) <= 100000:
                self.cached_words = sorted(
                    self.cached_words, key=lambda x: x.get('word', '').lower())
            else:
                # For very large datasets, skip initial sorting to improve startup time
                # Sorting will happen when filters are applied
                pass

            self.filtered_words = self.cached_words.copy()

            # Update window title
            if self.cached_words:
                self.root.title(
                    f"Word Finder - {len(self.cached_words):,} words in database")
            else:
                self.root.title("Word Finder - Welcome")

            # Initialize virtual scrolling with all data
            self.filtered_words = self.cached_words.copy()
            self.virtual_total_items = len(self.filtered_words)
            self.virtual_start_index = 0

            # Load first page and update display
            self._load_virtual_page()
            self._update_statistics()

            # Show helpful message if database is empty
            if not self.cached_words:
                self._add_output_message("Welcome to Word Finder!")
                self._add_output_message(
                    "Your database is empty. Click 'Start API Fetch' to begin fetching words.")
                self._add_output_message(
                    "You can fetch multiple word lengths at once (e.g., '2,4,5,6' or '2-6').")

        except Exception as e:
            print(f"Error loading data: {e}")
            self._show_loading_indicator(f"Error loading data: {e}")
            # Initialize empty data to prevent crashes
            self.cached_words = []
            self.filtered_words = []
            self.virtual_total_items = 0
            self.virtual_loaded_items = []
            self._populate_table_virtual()
            self._update_statistics()

    def _apply_theme(self):
        """Apply the current theme to the root window."""
        colors = self._get_theme_colors()
        self.root.configure(bg=colors['bg'])

        # Configure ttk styles for the theme
        style = ttk.Style()
        style.theme_use('clam')

        # Configure treeview style
        style.configure("Treeview",
                        background=colors['tree_bg'],
                        foreground=colors['tree_fg'],
                        fieldbackground=colors['tree_bg'],
                        font=('Arial', 10))
        style.configure("Treeview.Heading",
                        background=colors['button_bg'],
                        foreground=colors['button_fg'],
                        font=('Arial', 10, 'bold'))
        style.map("Treeview",
                  background=[('selected', colors['tree_select'])])

        # Configure combobox style
        style.configure("TCombobox",
                        fieldbackground=colors['entry_bg'],
                        background=colors['button_bg'],
                        foreground=colors['entry_fg'],
                        arrowcolor=colors['entry_fg'],
                        bordercolor=colors['button_bg'],
                        lightcolor=colors['entry_bg'],
                        darkcolor=colors['entry_bg'],
                        insertcolor=colors['entry_fg'])
        style.map("TCombobox",
                  fieldbackground=[('readonly', colors['entry_bg']),
                                   ('focus', colors['entry_bg']),
                                   ('!focus', colors['entry_bg'])],
                  selectbackground=[('readonly', colors['entry_bg'])],
                  selectforeground=[('readonly', colors['entry_fg'])],
                  background=[('readonly', colors['button_bg']),
                              ('focus', colors['button_bg']),
                              ('!focus', colors['button_bg'])],
                  foreground=[('readonly', colors['entry_fg']),
                              ('focus', colors['entry_fg']),
                              ('!focus', colors['entry_fg'])])

        # Configure combobox listbox (dropdown) style
        style.configure("TCombobox.Listbox",
                        background=colors['entry_bg'],
                        foreground=colors['entry_fg'],
                        selectbackground=colors['tree_select'],
                        selectforeground=colors['entry_fg'])

        # Configure progress bar style
        style.configure("Custom.Horizontal.TProgressbar",
                        background='#3498db',  # Blue progress color
                        troughcolor=colors['entry_bg'],  # Background color
                        borderwidth=1,
                        lightcolor='#5dade2',
                        darkcolor='#2980b9')

    def _create_header(self):
        """Create the header section with title and database info."""
        colors = self._get_theme_colors()

        header_frame = tk.Frame(self.root, bg=colors['header_bg'])
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        # Title with database info
        database_info = self.word_manager.get_database_size_info()
        overall_stats = self.word_manager.get_database_statistics()

        title_text = f"Word Finder - SQLite Database"

        # Handle empty database case
        if overall_stats['total_words'] == 0:
            info_text = "(Empty database - ready to fetch words!)"
        else:
            info_text = f"({overall_stats['total_words']:,} words, {database_info['size_formatted']})"

        title_label = tk.Label(header_frame, text=title_text,
                               font=('Arial', 16, 'bold'),
                               bg=colors['header_bg'], fg=colors['header_fg'])
        title_label.pack(side=tk.LEFT)

        info_label = tk.Label(header_frame, text=info_text,
                              font=('Arial', 10),
                              bg=colors['header_bg'], fg=colors['header_fg'])
        info_label.pack(side=tk.LEFT, padx=(10, 0))

        # Add theme toggle button
        self.theme_button = tk.Button(header_frame, text="🌙 Dark" if self.is_dark_theme else "☀️ Light",
                                      command=self._toggle_theme,
                                      bg=colors['button_bg'], fg=colors['button_fg'],
                                      font=('Arial', 10), relief=tk.FLAT)
        self.theme_button.pack(side=tk.RIGHT, padx=5)

        # Add word count label (will be updated by filters)
        self.count_label = tk.Label(header_frame, text="",
                                    font=('Arial', 10, 'italic'),
                                    bg=colors['header_bg'], fg=colors['header_fg'])
        self.count_label.pack(side=tk.RIGHT, padx=(0, 15))

    def _create_search_frame(self):
        """Create the search and filter controls."""
        colors = self._get_theme_colors()
        search_frame = tk.Frame(self.root, bg=colors['search_bg'])
        search_frame.pack(fill='x', padx=10, pady=5)

        # Search label and entry
        search_label = tk.Label(search_frame, text="Search:", font=('Arial', 11, 'bold'),
                                bg=colors['search_bg'], fg=colors['search_fg'])
        search_label.pack(side='left', padx=(5, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search_change)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=('Arial', 11),
                                bg=colors['entry_bg'], fg=colors['entry_fg'],
                                insertbackground=colors['entry_fg'], width=30)
        search_entry.pack(side='left', padx=(0, 5))

        # Add Enter key binding to search entry to trigger search immediately
        def on_search_enter(event):
            # Force immediate search update
            self._apply_filters()
            return 'break'

        search_entry.bind('<Return>', on_search_enter)
        search_entry.bind('<KP_Enter>', on_search_enter)

        # Clear button
        clear_btn = tk.Button(search_frame, text="Clear", command=self._clear_search,
                              bg=colors['button_bg'], fg=colors['button_fg'],
                              font=('Arial', 9), padx=10, pady=2, cursor='hand2')
        clear_btn.pack(side='left', padx=(0, 20))

        # Length filter
        length_label = tk.Label(search_frame, text="Length:", font=('Arial', 11, 'bold'),
                                bg=colors['search_bg'], fg=colors['search_fg'])
        length_label.pack(side='left', padx=(0, 5))

        self.length_filter_var = tk.StringVar(value="All")
        self.length_filter_var.trace('w', self._on_length_filter_change)

        # Create length filter dropdown with common word lengths
        length_options = ["All", "2", "3", "4", "5", "6",
                          "7", "8", "9", "10", "11", "12", "13", "14", "15"]
        length_combo = ttk.Combobox(search_frame, textvariable=self.length_filter_var,
                                    values=length_options, font=('Arial', 11),
                                    width=8, state="readonly")
        length_combo.pack(side='left', padx=(0, 10))

        # Search and sorting instructions
        instructions_frame = tk.Frame(search_frame, bg=colors['search_bg'])
        instructions_frame.pack(side='right', padx=5)

        search_help_label = tk.Label(instructions_frame, text="💡 Wildcards: _ (single char), * (multiple chars) • Prefix: cat* • Suffix: *ing • Combined: c_t* • F5 to test scroll",
                                     font=('Arial', 9, 'italic'), bg=colors['search_bg'], fg=colors['search_fg'])
        search_help_label.pack(anchor='e')

        sort_label = tk.Label(instructions_frame, text="💡 Click column headers to sort (1st click ↓, 2nd click ↑, 3rd click: reset)",
                              font=('Arial', 9, 'italic'), bg=colors['search_bg'], fg=colors['search_fg'])
        sort_label.pack(anchor='e')

    def _create_words_table(self):
        """Create the main table for displaying words with clickable headers."""
        colors = self._get_theme_colors()
        # Frame for the table
        table_frame = tk.Frame(self.root, bg=colors['bg'])
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Create Treeview with columns excluding Dictionary Matches - Allow stretching for full width
        columns = ('Word', 'Length', 'Points')
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show='headings', height=12)

        # Define column headings and widths with proportional stretching
        self.tree.heading('Word', text='Word',
                          command=lambda: self._header_sort('Word'))
        self.tree.heading('Length', text='Length',
                          command=lambda: self._header_sort('Length'))
        self.tree.heading('Points', text='Points',
                          command=lambda: self._header_sort('Points'))

        # Set column widths with proportional stretching to fill full width
        self.tree.column('Word', width=200, anchor='center',
                         minwidth=150, stretch=True)
        self.tree.column('Length', width=100, anchor='center',
                         minwidth=80, stretch=True)
        self.tree.column('Points', width=150, anchor='center',
                         minwidth=100, stretch=True)

        # Initialize sort direction for all columns
        for col in columns:
            self.sort_direction[col] = 0  # Start with no sorting

        # Create only vertical scrollbar (remove horizontal scrollbar)
        self.v_scrollbar = ttk.Scrollbar(
            table_frame, orient='vertical', command=self._on_scrollbar_move)
        self.tree.configure(yscrollcommand=self._on_tree_scroll)

        # Pack the treeview and scrollbar
        self.tree.pack(side='left', fill='both', expand=True)
        self.v_scrollbar.pack(side='right', fill='y')

        # Bind double-click event
        self.tree.bind('<Double-1>', self._on_word_double_click)

        # Bind additional scroll events for better detection
        self.tree.bind('<MouseWheel>', self._on_mouse_wheel)
        self.tree.bind('<Button-4>', self._on_mouse_wheel)  # Linux scroll up
        self.tree.bind('<Button-5>', self._on_mouse_wheel)  # Linux scroll down

        # Bind key for manual virtual scroll testing (F5)
        self.tree.bind('<F5>', self._test_virtual_scroll)

    def _test_virtual_scroll(self, event=None):
        """Test function to manually trigger virtual scroll check."""
        print("=== Manual Virtual Scroll Test ===")
        print(f"Total filtered words: {len(self.filtered_words)}")
        print(f"Virtual start index: {self.virtual_start_index}")
        print(f"Virtual loaded items: {len(self.virtual_loaded_items)}")

        try:
            scroll_top, scroll_bottom = self.tree.yview()
            print(
                f"Scroll position: top={scroll_top:.3f}, bottom={scroll_bottom:.3f}")

            if self.filtered_words:
                total_items = len(self.filtered_words)
                current_top_index = int(scroll_top * total_items)
                current_bottom_index = int(scroll_bottom * total_items)
                print(
                    f"Estimated viewing items: {current_top_index}-{current_bottom_index}")

                loaded_start = self.virtual_start_index
                loaded_end = loaded_start + len(self.virtual_loaded_items)
                print(f"Currently loaded range: {loaded_start}-{loaded_end-1}")

        except Exception as e:
            print(f"Error in test: {e}")

        print("=== Forcing virtual scroll check ===")
        self._check_virtual_scroll_position()

    def _create_stats_panel(self):
        """Create the statistics panel."""
        colors = self._get_theme_colors()
        stats_frame = tk.LabelFrame(self.root, text="Statistics", font=('Arial', 10, 'bold'),
                                    bg=colors['bg'], fg=colors['fg'])
        stats_frame.pack(fill='x', padx=10, pady=5)

        self.stats_text = tk.Text(stats_frame, height=3, font=('Arial', 9),
                                  bg=colors['stats_bg'], fg=colors['stats_fg'], state='disabled')
        self.stats_text.pack(fill='x', padx=5, pady=5)

    def _create_output_panel(self):
        """Create the output panel for fetch progress."""
        colors = self._get_theme_colors()
        output_frame = tk.LabelFrame(self.root, text="Fetch Output", font=('Arial', 10, 'bold'),
                                     bg=colors['bg'], fg=colors['fg'])
        output_frame.pack(fill='x', padx=10, pady=5)

        # Progress bar section
        progress_container = tk.Frame(output_frame, bg=colors['bg'])
        progress_container.pack(fill='x', padx=5, pady=(5, 0))

        # Progress label
        self.progress_label = tk.Label(progress_container, text="Ready to start fetch...",
                                       font=('Arial', 9), bg=colors['bg'], fg=colors['fg'])
        self.progress_label.pack(anchor='w')

        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_container, length=400, mode='determinate',
                                            style='Custom.Horizontal.TProgressbar')
        self.progress_bar.pack(fill='x', pady=(2, 5))
        self.progress_bar['value'] = 0

        # Create text widget with scrollbar
        output_container = tk.Frame(output_frame, bg=colors['bg'])
        output_container.pack(fill='both', expand=True, padx=5, pady=5)

        self.output_text = tk.Text(output_container, height=6, font=('Consolas', 9),
                                   bg=colors['output_bg'], fg=colors['output_fg'],
                                   state='disabled', wrap='word')

        output_scrollbar = ttk.Scrollbar(
            output_container, orient='vertical', command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_scrollbar.set)

        self.output_text.pack(side='left', fill='both', expand=True)
        output_scrollbar.pack(side='right', fill='y')

        # Add initial message
        self._add_output_message("Ready to fetch words from API...")

    def _create_control_buttons(self, wait_for_user: bool):
        """Create the control buttons."""
        colors = self._get_theme_colors()
        button_frame = tk.Frame(self.root, bg=colors['bg'])
        button_frame.pack(fill='x', padx=10, pady=10)

        if wait_for_user:
            # Continue button
            self.continue_btn = tk.Button(
                button_frame,
                text="Start API Fetch",
                command=self._start_fetch_in_background,
                bg='#3498db',
                fg='white',
                font=('Arial', 11, 'bold'),
                padx=20,
                pady=5,
                cursor='hand2'
            )
            self.continue_btn.pack(side='left', padx=5)

            # Cancel button
            self.cancel_btn = tk.Button(
                button_frame,
                text="Use Cached Only",
                command=self._use_cached_only,
                bg='#e74c3c',
                fg='white',
                font=('Arial', 11, 'bold'),
                padx=20,
                pady=5,
                cursor='hand2'
            )
            self.cancel_btn.pack(side='left', padx=5)

        # Export button
        export_btn = tk.Button(
            button_frame,
            text="Export to File",
            command=self._export_words,
            bg='#2ecc71',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=5,
            cursor='hand2'
        )
        export_btn.pack(side='right', padx=5)

        # Close button
        close_btn = tk.Button(
            button_frame,
            text="Close",
            command=self._on_window_close,
            bg='#95a5a6',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=20,
            pady=5,
            cursor='hand2'
        )
        close_btn.pack(side='right', padx=5)

    def _toggle_theme(self):
        """Toggle between dark and light themes."""
        self.is_dark_theme = not self.is_dark_theme
        # Update the button text immediately with consistent sizing
        if self.theme_button:
            new_icon = "🌙 Dark" if self.is_dark_theme else "☀️ Light"
            self.theme_button.config(text=new_icon)
        self._refresh_theme()

    def _refresh_theme(self):
        """Refresh all UI elements with the new theme."""
        if not self.root:
            return

        colors = self._get_theme_colors()

        # Update root window
        self.root.configure(bg=colors['bg'])

        # Update all frames and widgets
        for widget in self.root.winfo_children():
            self._update_widget_theme(widget, colors)

        # Reapply ttk styles
        self._apply_theme()

        # Refresh table display
        self._populate_table()
        self._update_statistics()

    def _update_widget_theme(self, widget, colors):
        """Recursively update widget themes."""
        widget_class = widget.winfo_class()

        try:
            if widget_class == 'Frame':
                if 'header' in str(widget):
                    widget.configure(bg=colors['header_bg'])
                elif 'search' in str(widget):
                    widget.configure(bg=colors['search_bg'])
                else:
                    widget.configure(bg=colors['bg'])
            elif widget_class == 'Label':
                parent_bg = colors['bg']
                if hasattr(widget.master, 'cget') and widget.master.cget('bg') == colors['header_bg']:
                    parent_bg = colors['header_bg']
                    widget.configure(
                        bg=colors['header_bg'], fg=colors['header_fg'])
                elif hasattr(widget.master, 'cget') and widget.master.cget('bg') == colors['search_bg']:
                    parent_bg = colors['search_bg']
                    widget.configure(
                        bg=colors['search_bg'], fg=colors['search_fg'])
                else:
                    widget.configure(bg=colors['bg'], fg=colors['fg'])
            elif widget_class == 'Entry':
                widget.configure(
                    bg=colors['entry_bg'], fg=colors['entry_fg'], insertbackground=colors['entry_fg'])
            elif widget_class == 'Text':
                # Check if it's the output text (has different colors)
                if hasattr(self, 'output_text') and widget == self.output_text:
                    widget.configure(
                        bg=colors['output_bg'], fg=colors['output_fg'])
                else:
                    widget.configure(
                        bg=colors['stats_bg'], fg=colors['stats_fg'])
            elif widget_class == 'Button':
                # Only update theme toggle button appearance, not text
                if widget == self.theme_button:
                    widget.configure(
                        bg=colors['header_bg'], fg=colors['header_fg'])
            elif widget_class == 'Labelframe':
                widget.configure(bg=colors['bg'], fg=colors['fg'])
            elif widget_class == 'TCombobox':
                # TTK combobox styling is handled by the style configuration
                pass
        except tk.TclError:
            pass  # Some widgets might not support certain configurations

        # Update progress bar and label specifically
        if hasattr(self, 'progress_bar') and widget == self.progress_bar:
            # Progress bar theme is handled by ttk styles in _apply_theme
            pass
        elif hasattr(self, 'progress_label') and widget == self.progress_label:
            widget.configure(bg=colors['bg'], fg=colors['fg'])

        # Recursively update children
        for child in widget.winfo_children():
            self._update_widget_theme(child, colors)

    def _add_output_message(self, message: str):
        """Add a message to the output text widget."""
        if self.output_text:
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, f"{message}\n")
            self.output_text.see(tk.END)  # Auto-scroll to bottom
            self.output_text.config(state='disabled')
            self.root.update_idletasks()  # Force GUI update

    def _start_fetch_in_background(self):
        """Start the fetch process in a background thread with parameter dialog."""
        if self.fetch_in_progress:
            messagebox.showwarning("Fetch in Progress",
                                   "A fetch operation is already in progress.")
            return

        # Add message to indicate dialog is opening
        self._add_output_message("Opening fetch configuration dialog...")

        # Show parameter dialog
        fetch_params = self._show_fetch_parameters_dialog()
        if not fetch_params:
            self._add_output_message("Fetch cancelled by user.")
            return  # User cancelled

        # Store all fetch parameters (handle both single and multiple lengths)
        self.fetch_lengths = fetch_params.get('lengths', [])
        self.word_length = fetch_params.get(
            'length', self.fetch_lengths[0] if self.fetch_lengths else 4)
        self.fetch_page_size = fetch_params.get('page_size', 50)
        self.fetch_max_words = fetch_params.get('max_words', None)
        self.fetch_show_cached = fetch_params.get('show_cached', True)
        self.fetch_dictionary = fetch_params.get('dictionary', 'all_en')
        self.fetch_include_dict_matches = fetch_params.get(
            'include_dict_matches', True)

        self.fetch_in_progress = True
        self.continue_btn.config(state='disabled', text="Fetching...")
        self.cancel_btn.config(state='disabled')

        # Reset and initialize progress
        self._reset_progress()
        self._update_progress(0, 1, "Initializing fetch...")

        # Create detailed output message
        max_words_text = f" (max {self.fetch_max_words})" if self.fetch_max_words else " (unlimited)"
        dict_text = f", Dictionary={self.fetch_dictionary}"
        dict_matches_text = f", Dict matches={'ON' if self.fetch_include_dict_matches else 'OFF'}"

        # Show different messages for single vs multiple lengths
        if len(self.fetch_lengths) == 1:
            self._add_output_message(
                f"Starting API fetch for {self.fetch_lengths[0]}-letter words{max_words_text}...")
        else:
            lengths_str = ','.join(map(str, self.fetch_lengths))
            self._add_output_message(
                f"Starting sequential API fetch for lengths: {lengths_str}{max_words_text}...")

        self._add_output_message(
            f"Configuration: Page size={self.fetch_page_size}, Show cached={self.fetch_show_cached}{dict_text}{dict_matches_text}")

        # Start fetch in background thread
        fetch_thread = Thread(target=self._run_fetch_async, daemon=True)
        fetch_thread.start()

    def _show_fetch_parameters_dialog(self):
        """Show dialog to get fetch parameters from user with validation."""
        dialog = tk.Toplevel(self.root)
        dialog.title("API Fetch Configuration")
        dialog.geometry("450x480")
        dialog.transient(self.root)
        dialog.grab_set()
        # Make dialog non-resizable for better control
        dialog.resizable(False, False)

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (480 // 2)
        dialog.geometry(f"450x480+{x}+{y}")

        colors = self._get_theme_colors()
        dialog.configure(bg=colors['bg'])

        result = {}
        validation_errors = []

        # Main content frame
        main_frame = tk.Frame(dialog, bg=colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=15)

        # Title
        tk.Label(main_frame, text="Configure API Fetch Parameters",
                 font=('Arial', 14, 'bold'),
                 bg=colors['bg'], fg=colors['fg']).pack(pady=(0, 15))

        # Word Length field
        length_frame = tk.Frame(main_frame, bg=colors['bg'])
        length_frame.pack(fill='x', pady=5)

        tk.Label(length_frame, text="Word Length(s):", font=('Arial', 11, 'bold'),
                 bg=colors['bg'], fg=colors['fg']).pack(anchor='w')

        length_var = tk.StringVar(value=str(self.word_length))
        length_entry = tk.Entry(length_frame, textvariable=length_var, font=('Arial', 11),
                                bg=colors['entry_bg'], fg=colors['entry_fg'],
                                insertbackground=colors['entry_fg'], width=20)
        length_entry.pack(anchor='w', pady=(2, 0))

        # Updated help text for multiple lengths
        help_text = tk.Text(length_frame, height=3, width=50, font=('Arial', 9),
                            bg=colors['bg'], fg=colors['search_fg'],
                            relief=tk.FLAT, wrap=tk.WORD)
        help_text.insert(
            tk.END, "Examples:\n• Single: 4\n• Multiple: 2,4,5,6\n• Range: 2-4 (fetches 2,3,4)")
        help_text.config(state=tk.DISABLED)
        help_text.pack(anchor='w', pady=(2, 0))

        # Page Size field
        page_size_frame = tk.Frame(main_frame, bg=colors['bg'])
        page_size_frame.pack(fill='x', pady=10)

        tk.Label(page_size_frame, text="Page Size:", font=('Arial', 11, 'bold'),
                 bg=colors['bg'], fg=colors['fg']).pack(anchor='w')

        page_size_var = tk.StringVar(value="50")
        page_size_entry = tk.Entry(page_size_frame, textvariable=page_size_var, font=('Arial', 11),
                                   bg=colors['entry_bg'], fg=colors['entry_fg'],
                                   insertbackground=colors['entry_fg'], width=10)
        page_size_entry.pack(anchor='w', pady=(2, 0))

        tk.Label(page_size_frame, text="(Number of words per API request, 10-200)",
                 font=('Arial', 9, 'italic'),
                 bg=colors['bg'], fg=colors['search_fg']).pack(anchor='w')

        # Max Words field
        max_words_frame = tk.Frame(main_frame, bg=colors['bg'])
        max_words_frame.pack(fill='x', pady=10)

        tk.Label(max_words_frame, text="Maximum Words to Fetch:", font=('Arial', 11, 'bold'),
                 bg=colors['bg'], fg=colors['fg']).pack(anchor='w')

        max_words_var = tk.StringVar(value="")
        max_words_entry = tk.Entry(max_words_frame, textvariable=max_words_var, font=('Arial', 11),
                                   bg=colors['entry_bg'], fg=colors['entry_fg'],
                                   insertbackground=colors['entry_fg'], width=15)
        max_words_entry.pack(anchor='w', pady=(2, 0))

        tk.Label(max_words_frame, text="(Leave empty for unlimited, or specify a number)",
                 font=('Arial', 9, 'italic'),
                 bg=colors['bg'], fg=colors['search_fg']).pack(anchor='w')

        # Dictionary selection field
        dictionary_frame = tk.Frame(main_frame, bg=colors['bg'])
        dictionary_frame.pack(fill='x', pady=10)

        tk.Label(dictionary_frame, text="Dictionary:", font=('Arial', 11, 'bold'),
                 bg=colors['bg'], fg=colors['fg']).pack(anchor='w')

        dictionary_var = tk.StringVar(value="all_en")
        dictionary_combo = ttk.Combobox(dictionary_frame, textvariable=dictionary_var,
                                        font=('Arial', 11), width=20, state="readonly")
        dictionary_combo['values'] = (
            "all_en", "sowpods", "wwf", "wordle", "quordle", "octordle", "otcwl")
        dictionary_combo.pack(anchor='w', pady=(2, 0))

        tk.Label(dictionary_frame, text="(Dictionary to use for word validation and matches)",
                 font=('Arial', 9, 'italic'),
                 bg=colors['bg'], fg=colors['search_fg']).pack(anchor='w')

        # Show Cached checkbox
        show_cached_var = tk.BooleanVar(value=True)
        show_cached_check = tk.Checkbutton(main_frame, text="Show cached words during fetch",
                                           variable=show_cached_var,
                                           bg=colors['bg'], fg=colors['fg'],
                                           selectcolor=colors['button_bg'],
                                           activebackground=colors['bg'],
                                           activeforeground=colors['fg'],
                                           font=('Arial', 10))
        show_cached_check.pack(anchor='w', pady=5)

        # Include Dictionary Matches checkbox (enabled by default)
        include_dict_matches_var = tk.BooleanVar(value=True)
        dict_matches_check = tk.Checkbutton(main_frame, text="Include dictionary matches (recommended)",
                                            variable=include_dict_matches_var,
                                            bg=colors['bg'], fg=colors['fg'],
                                            selectcolor=colors['button_bg'],
                                            activebackground=colors['bg'],
                                            activeforeground=colors['fg'],
                                            font=('Arial', 10))
        dict_matches_check.pack(anchor='w', pady=5)

        # Validation error label
        error_label = tk.Label(main_frame, text="", font=('Arial', 10),
                               bg=colors['bg'], fg='#e74c3c', wraplength=400)
        error_label.pack(pady=5)

        def parse_length_input(length_input: str) -> List[int]:
            """Parse length input supporting single, comma-separated, and range formats."""
            length_input = length_input.strip()
            if not length_input:
                return []

            lengths = []
            parts = [part.strip() for part in length_input.split(',')]

            for part in parts:
                if '-' in part and not part.startswith('-'):
                    # Handle range format (e.g., "2-4")
                    try:
                        start, end = part.split('-', 1)
                        start_val = int(start.strip())
                        end_val = int(end.strip())
                        if start_val <= end_val:
                            lengths.extend(range(start_val, end_val + 1))
                        else:
                            raise ValueError(f"Invalid range: {part}")
                    except ValueError:
                        raise ValueError(f"Invalid range format: {part}")
                else:
                    # Handle single number
                    try:
                        length = int(part)
                        lengths.append(length)
                    except ValueError:
                        raise ValueError(f"Invalid number: {part}")

            # Remove duplicates and sort
            lengths = sorted(list(set(lengths)))
            return lengths

        def validate_inputs():
            """Validate all input fields."""
            validation_errors.clear()

            # Validate word length(s)
            try:
                length_input = length_var.get()
                print(f"DEBUG: Validating length input: '{length_input}'")
                lengths = parse_length_input(length_input)
                print(
                    f"DEBUG: Parsed lengths: {lengths} (count: {len(lengths)})")

                if not lengths:
                    validation_errors.append(
                        "At least one word length must be specified")
                else:
                    invalid_lengths = [l for l in lengths if l < 2 or l > 15]
                    if invalid_lengths:
                        validation_errors.append(
                            f"Invalid word length(s): {invalid_lengths}. Must be between 2 and 15")
                    if len(lengths) > 15:
                        validation_errors.append(
                            "Maximum 15 word lengths allowed at once")
            except ValueError as e:
                print(f"DEBUG: ValueError during parsing: {e}")
                validation_errors.append(f"Word length format error: {str(e)}")

            # Validate page size
            try:
                page_size = int(page_size_var.get())
                if page_size < 10 or page_size > 200:
                    validation_errors.append(
                        "Page size must be between 10 and 200")
            except ValueError:
                validation_errors.append("Page size must be a valid number")

            # Validate max words (optional)
            max_words_text = max_words_var.get().strip()
            if max_words_text:
                try:
                    max_words = int(max_words_text)
                    if max_words < 1:
                        validation_errors.append(
                            "Maximum words must be a positive number")
                except ValueError:
                    validation_errors.append(
                        "Maximum words must be a valid number or empty")

            return len(validation_errors) == 0

        def update_error_display():
            """Update the error display."""
            if validation_errors:
                error_text = "Validation Errors:\n• " + \
                    "\n• ".join(validation_errors)
                error_label.config(text=error_text)
            else:
                error_label.config(text="")

        def on_start_search():
            """Handle start search button click."""
            try:
                # Force update of StringVar values from their widgets (in case of timing issues)
                try:
                    # Get current values directly from widgets and update StringVars
                    current_length = length_entry.get()
                    length_var.set(current_length)

                    current_page_size = page_size_entry.get()
                    page_size_var.set(current_page_size)

                    current_max_words = max_words_entry.get()
                    max_words_var.set(current_max_words)

                    current_dictionary = dictionary_combo.get()
                    dictionary_var.set(current_dictionary)

                    # Force tkinter to process any pending updates
                    dialog.update_idletasks()
                except Exception as e:
                    print(
                        f"Warning: Error updating StringVars in on_start_search: {e}")

                if validate_inputs():
                    lengths = parse_length_input(length_var.get())
                    # Store as list instead of single length
                    result['lengths'] = lengths
                    result['length'] = lengths[0] if len(
                        lengths) == 1 else None  # Keep for backward compatibility
                    result['page_size'] = int(page_size_var.get())
                    max_words_text = max_words_var.get().strip()
                    result['max_words'] = int(
                        max_words_text) if max_words_text else None
                    result['show_cached'] = show_cached_var.get()
                    result['dictionary'] = dictionary_var.get()
                    result['include_dict_matches'] = include_dict_matches_var.get()
                    dialog.destroy()
                else:
                    update_error_display()
                    # Flash the error label to draw attention
                    error_label.config(bg='#ffcccc')
                    dialog.after(
                        200, lambda: error_label.config(bg=colors['bg']))
            except Exception as e:
                validation_errors.append(f"Unexpected error: {str(e)}")
                update_error_display()
                error_label.config(bg='#ffcccc')
                dialog.after(200, lambda: error_label.config(bg=colors['bg']))

        def on_cancel():
            """Handle cancel button click."""
            result.clear()  # Clear result to indicate cancellation
            dialog.destroy()

        # Handle window close button (X)
        def on_dialog_close():
            """Handle dialog close event."""
            result.clear()  # Clear result to indicate cancellation
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)

        # Add a separator line above buttons for better visual separation
        separator = tk.Frame(main_frame, bg=colors['search_fg'], height=1)
        separator.pack(fill='x', pady=(15, 5))

        # Buttons frame - positioned at the bottom
        button_frame = tk.Frame(main_frame, bg=colors['bg'])
        button_frame.pack(fill='x', pady=(10, 0))

        # Start Search button (primary action)
        start_btn = tk.Button(button_frame, text="🚀 Start Search", command=on_start_search,
                              bg='#27ae60', fg='white',
                              font=('Arial', 12, 'bold'), padx=40, pady=12,
                              cursor='hand2', relief='raised', bd=3)
        start_btn.pack(side='left', padx=(0, 20))

        # Cancel button
        cancel_btn = tk.Button(button_frame, text="✕ Cancel", command=on_cancel,
                               bg='#e74c3c', fg='white',
                               font=('Arial', 12, 'bold'), padx=40, pady=12,
                               cursor='hand2', relief='raised', bd=3)
        cancel_btn.pack(side='left')

        # Add Enter key hint
        hint_label = tk.Label(button_frame, text="Press Enter to start search, Escape to cancel",
                              font=('Arial', 9, 'italic'),
                              bg=colors['bg'], fg=colors['search_fg'])
        hint_label.pack(side='right', padx=(20, 0))

        # Simplified and more reliable key binding approach
        def handle_enter_key(event):
            """Handle Enter key press - start search if validation passes."""
            print(f"DEBUG: Enter key pressed, event source: {event.widget}")

            # Force update of all StringVar values from their widgets before validation
            try:
                # Get current values directly from widgets and update StringVars
                current_length = length_entry.get()
                print(f"DEBUG: Current length from entry: '{current_length}'")
                length_var.set(current_length)

                current_page_size = page_size_entry.get()
                page_size_var.set(current_page_size)

                current_max_words = max_words_entry.get()
                max_words_var.set(current_max_words)

                current_dictionary = dictionary_combo.get()
                dictionary_var.set(current_dictionary)

                # Force tkinter to process any pending updates
                dialog.update_idletasks()
                print(
                    f"DEBUG: StringVars updated, length_var now: '{length_var.get()}'")
            except Exception as e:
                print(
                    f"Warning: Error updating StringVars in handle_enter_key: {e}")

            # Now run the search with updated values
            print("DEBUG: Calling on_start_search from handle_enter_key")
            on_start_search()
            return 'break'  # Prevent further event processing

        def handle_escape_key(event):
            """Handle Escape key press - cancel dialog."""
            on_cancel()
            return 'break'

        # More robust key binding approach - bind to all widgets that can receive focus
        def bind_keys_to_widget(widget):
            """Bind keys to a widget safely."""
            try:
                widget.bind('<Return>', handle_enter_key)
                widget.bind('<KP_Enter>', handle_enter_key)
                widget.bind('<Escape>', handle_escape_key)
            except:
                pass  # Some widgets might not support certain bindings

        # Bind to dialog first (highest priority)
        bind_keys_to_widget(dialog)

        # Bind to all input widgets
        bind_keys_to_widget(length_entry)
        bind_keys_to_widget(page_size_entry)
        bind_keys_to_widget(max_words_entry)
        bind_keys_to_widget(dictionary_combo)

        # Bind to buttons
        bind_keys_to_widget(start_btn)
        bind_keys_to_widget(cancel_btn)

        # Bind to frames
        bind_keys_to_widget(main_frame)
        bind_keys_to_widget(button_frame)

        # Additional fallback binding - only active when this dialog has focus
        def dialog_key_handler(event):
            # Only handle if this dialog is the active window
            if dialog.focus_get() is not None:
                if event.keysym in ['Return', 'KP_Enter']:
                    handle_enter_key(event)
                    return 'break'
                elif event.keysym == 'Escape':
                    handle_escape_key(event)
                    return 'break'

        # Bind to dialog with focus check
        dialog.bind('<Key>', dialog_key_handler)

        # Focus on length entry and select all text
        length_entry.focus_set()
        length_entry.select_range(0, tk.END)

        # Ensure the dialog is focused and modal
        dialog.focus_force()
        dialog.lift()  # Bring to front
        dialog.attributes('-topmost', True)  # Keep on top temporarily
        # Remove topmost after a moment to prevent permanent stay-on-top behavior
        dialog.after(100, lambda: dialog.attributes('-topmost', False))

        # More gentle focus handling - only re-focus if dialog still exists and is visible
        def on_focus_out(event):
            if event.widget == dialog and dialog.winfo_exists() and dialog.winfo_viewable():
                # Only re-focus if the focus went to a different application, not within our app
                try:
                    current_focus = dialog.focus_get()
                    if current_focus is None:  # Focus went outside the application
                        dialog.after(50, lambda: dialog.focus_set()
                                     if dialog.winfo_exists() else None)
                except:
                    pass  # Ignore any focus-related errors

        dialog.bind('<FocusOut>', on_focus_out)

        # Make sure dialog can receive key events
        dialog.focus_set()

        dialog.wait_window()
        return result

    def _run_fetch_async(self):
        """Run the async fetch in a separate thread."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Check if we're fetching single or multiple lengths
            if len(self.fetch_lengths) == 1:
                # Single length fetch - use existing method
                new_words = loop.run_until_complete(
                    self._fetch_with_output(self.fetch_lengths[0]))
            else:
                # Multiple lengths fetch - use concurrent method
                new_words = loop.run_until_complete(
                    self._fetch_multiple_lengths_with_output(self.fetch_lengths))

            # Update GUI in main thread
            self.root.after(0, self._fetch_completed, new_words)

        except Exception as e:
            error_msg = f"Error during fetch: {e}"
            print(error_msg)  # Also print to terminal
            self.root.after(0, self._fetch_error, error_msg)
        finally:
            loop.close()

    async def _fetch_multiple_lengths_with_output(self, lengths: List[int]):
        """Fetch words for multiple lengths sequentially with output to both GUI and terminal."""
        # Redirect stdout to capture print statements
        original_stdout = sys.stdout
        captured_output = StringIO()

        class TeeOutput:
            def write(self, text):
                original_stdout.write(text)  # Write to terminal
                captured_output.write(text)  # Capture for GUI
                # Update GUI output (must be called from main thread)
                if hasattr(self, 'root') and self.root:
                    self.root.after(0, lambda: self._add_output_message(
                        text.strip()) if text.strip() else None)

            def flush(self):
                original_stdout.flush()
                captured_output.flush()

        # Temporarily redirect stdout
        tee = TeeOutput()
        sys.stdout = tee

        try:
            # Progress callback to update GUI progress bar with page-level details
            def progress_callback(current_page, total_pages, message):
                self.root.after(0, lambda: self._update_progress(
                    current_page, total_pages, message))

            self.root.after(0, lambda: self._update_progress(
                0, 1, f"Starting sequential fetch for {len(lengths)} lengths..."))

            # Use WordManager's sequential fetch method with page-level progress
            results_dict = await self.word_manager.fetch_multiple_lengths_sequential(
                lengths, self.fetch_page_size, progress_callback)

            # Combine all results into a single list
            all_words = []
            for length, words in results_dict.items():
                all_words.extend(words)
                self.root.after(0, lambda l=length, w=len(words): self._add_output_message(
                    f"Length {l}: Retrieved {w} words"))

            self.root.after(0, lambda: self._update_progress(
                1, 1, f"All lengths completed - {len(all_words)} total words"))

            return all_words

        finally:
            # Restore original stdout
            sys.stdout = original_stdout

    async def _fetch_with_output(self, length: int):
        """Fetch words with output to both GUI and terminal, respecting max_words limit."""
        # Redirect stdout to capture print statements
        original_stdout = sys.stdout
        captured_output = StringIO()

        class TeeOutput:
            def write(self, text):
                original_stdout.write(text)  # Write to terminal
                captured_output.write(text)  # Capture for GUI
                # Update GUI output (must be called from main thread)
                if hasattr(self, 'root') and self.root:
                    self.root.after(0, lambda: self._add_output_message(
                        text.strip()) if text.strip() else None)

            def flush(self):
                original_stdout.flush()
                captured_output.flush()

        # Temporarily redirect stdout
        tee = TeeOutput()
        sys.stdout = tee

        try:
            # Check if we have a max_words limit
            max_words = getattr(self, 'fetch_max_words', None)

            if max_words:
                # Use custom limited fetch
                new_words = await self._fetch_with_limit(length, max_words)
            else:
                # Use standard unlimited fetch with basic progress tracking
                self.root.after(0, lambda: self._update_progress(
                    0, 1, "Starting unlimited fetch..."))

                # Create a custom fetch for unlimited case that uses our dictionary setting
                dictionary = getattr(self, 'fetch_dictionary', 'all_en')
                page_size = getattr(self, 'fetch_page_size', 50)

                # We need to create our own unlimited fetch that respects the dictionary parameter
                new_words = await self._fetch_unlimited_with_dictionary(length, dictionary, page_size)

                # Update progress to show completion for unlimited fetch
                self.root.after(0, lambda: self._update_progress(
                    1, 1, f"Unlimited fetch completed - {len(new_words)} words"))

            return new_words
        finally:
            # Restore original stdout
            sys.stdout = original_stdout

    async def _fetch_unlimited_with_dictionary(self, length: int, dictionary: str, page_size: int):
        """Custom unlimited fetch that respects dictionary parameter."""
        import httpx
        import asyncio

        base_params = {
            "length": length,
            "word_sorting": "points",
            "group_by_length": True,
            "page_size": page_size,
            "dictionary": dictionary
        }

        all_words = []
        self.word_manager.partial_words = all_words

        async with httpx.AsyncClient() as client:
            try:
                # First request to get pagination info
                self.root.after(0, lambda: self._add_output_message(
                    "Making initial request to get pagination info..."))

                if self.word_manager._should_exit():
                    return all_words

                response = await client.get(self.word_manager.base_url, params=base_params)
                response_data = response.json()

                # Extract pagination info from first response
                word_pages = response_data.get("word_pages", [])
                if not word_pages:
                    self.root.after(0, lambda: self._add_output_message(
                        "No word pages found in response"))
                    return all_words

                first_page = word_pages[0]
                total_pages = first_page.get("num_pages", 1)
                total_words = first_page.get("num_words", 0)

                self.root.after(0, lambda: self._add_output_message(
                    f"Found {total_words} total words across {total_pages} pages"))

                # Initialize progress
                self.root.after(0, lambda: self._update_progress(
                    0, total_pages, "Starting unlimited fetch..."))

                # Add words from first page
                first_page_words = first_page.get("word_list", [])
                all_words.extend(first_page_words)

                # Update progress for first page
                self.root.after(0, lambda: self._update_progress(
                    1, total_pages, f"Added {len(first_page_words)} words"))
                self.root.after(0, lambda: self._add_output_message(
                    f"Page 1/{total_pages}: Added {len(first_page_words)} words"))

                if self.word_manager._should_exit():
                    self.word_manager.merge_with_database(
                        all_words, length, is_partial=True)
                    return all_words

                # Fetch remaining pages
                for page_num in range(2, total_pages + 1):
                    if self.word_manager._should_exit():
                        self.root.after(0, lambda: self._add_output_message(
                            f"Graceful exit requested. Stopping at page {page_num-1}/{total_pages}"))
                        self.word_manager.merge_with_database(
                            all_words, length, is_partial=True)
                        break

                    try:
                        # Add page_token parameter for subsequent pages
                        page_params = base_params.copy()
                        page_params["page_token"] = page_num - 1

                        # Update progress before fetching
                        self.root.after(0, lambda p=page_num, t=total_pages:
                                        self._update_progress(p-1, t, f"Fetching page {p}/{t}..."))
                        self.root.after(0, lambda p=page_num, t=total_pages: self._add_output_message(
                            f"Fetching page {p}/{t}..."))

                        page_response = await client.get(self.word_manager.base_url, params=page_params)
                        page_response_data = page_response.json()

                        # Extract words from this page
                        page_word_pages = page_response_data.get(
                            "word_pages", [])
                        if page_word_pages:
                            page_words = page_word_pages[0].get(
                                "word_list", [])
                            all_words.extend(page_words)

                            # Update progress after adding words
                            self.root.after(0, lambda p=page_num, t=total_pages, w=len(page_words):
                                            self._update_progress(p, t, f"Added {w} words (Total: {len(all_words)})"))
                            self.root.after(0, lambda p=page_num, t=total_pages, w=len(page_words):
                                            self._add_output_message(f"Page {p}/{t}: Added {w} words"))
                        else:
                            self.root.after(0, lambda p=page_num, t=total_pages:
                                            self._update_progress(p, t, "No words found"))
                            self.root.after(0, lambda p=page_num, t=total_pages:
                                            self._add_output_message(f"Page {p}/{t}: No words found"))

                        # Small delay to be respectful to the API
                        if not self.word_manager._should_exit():
                            await asyncio.sleep(0.1)

                    except KeyboardInterrupt:
                        self.root.after(0, lambda p=page_num: self._add_output_message(
                            f"\nKeyboard interrupt detected at page {p}"))
                        if self.word_manager.signal_handler:
                            self.word_manager.signal_handler.should_exit = True
                        self.word_manager.merge_with_database(
                            all_words, length, is_partial=True)
                        break
                    except Exception as e:
                        self.root.after(0, lambda p=page_num, err=str(e): self._add_output_message(
                            f"Error fetching page {p}: {err}"))
                        if self.word_manager._should_exit():
                            self.word_manager.merge_with_database(
                                all_words, length, is_partial=True)
                            break

                if self.word_manager._should_exit():
                    self.root.after(0, lambda: self._add_output_message(
                        f"\nGraceful exit completed. Collected {len(all_words)} words before stopping."))
                    self.root.after(0, lambda: self._update_progress(
                        total_pages, total_pages, "Stopped by user"))
                else:
                    self.root.after(0, lambda: self._add_output_message(
                        f"\nCompleted! Total words collected: {len(all_words)}"))
                    self.root.after(0, lambda: self._update_progress(
                        total_pages, total_pages, "Fetch completed"))
                    # Merge complete results with database
                    self.word_manager.merge_with_database(
                        all_words, length, is_partial=False)

            except KeyboardInterrupt:
                self.root.after(0, lambda: self._add_output_message(
                    f"\nKeyboard interrupt detected during initial setup."))
                if self.word_manager.signal_handler:
                    self.word_manager.signal_handler.should_exit = True
                if all_words:
                    self.word_manager.merge_with_database(
                        all_words, length, is_partial=True)
            except Exception as e:
                self.root.after(0, lambda err=str(
                    e): self._add_output_message(f"Unexpected error: {err}"))
                if self.word_manager.signal_handler:
                    self.word_manager.signal_handler.should_exit = True
                if all_words:
                    self.word_manager.merge_with_database(
                        all_words, length, is_partial=True)

        return all_words

    async def _fetch_with_limit(self, length: int, max_words: int):
        """Custom fetch method that stops when max_words limit is reached."""
        import httpx
        import asyncio

        page_size = getattr(self, 'fetch_page_size', 50)
        dictionary = getattr(self, 'fetch_dictionary', 'all_en')

        base_params = {
            "length": length,
            "word_sorting": "points",
            "group_by_length": True,
            "page_size": page_size,
            "dictionary": dictionary
        }

        all_words = []
        self.word_manager.partial_words = all_words  # Reference for signal handler

        async with httpx.AsyncClient() as client:
            try:
                # First request to get pagination info
                self.root.after(0, lambda: self._add_output_message(
                    "Making initial request to get pagination info..."))
                self.root.after(0, lambda: self._update_progress(
                    0, 1, "Getting pagination info..."))

                if self.word_manager._should_exit():
                    return all_words

                response = await client.get(self.word_manager.base_url, params=base_params)
                response_data = response.json()

                # Extract pagination info from first response
                word_pages = response_data.get("word_pages", [])
                if not word_pages:
                    self.root.after(0, lambda: self._add_output_message(
                        "No word pages found in response"))
                    return all_words

                first_page = word_pages[0]
                total_pages = first_page.get("num_pages", 1)
                total_words = first_page.get("num_words", 0)

                # Adjust total pages if we have a limit
                actual_pages_to_fetch = total_pages
                if max_words and max_words < total_words:
                    estimated_pages = (max_words + page_size - 1) // page_size
                    actual_pages_to_fetch = min(estimated_pages, total_pages)
                    self.root.after(0, lambda: self._add_output_message(
                        f"Found {total_words} total words, limiting to {max_words} words ({actual_pages_to_fetch} pages)"))
                else:
                    self.root.after(0, lambda: self._add_output_message(
                        f"Found {total_words} total words across {total_pages} pages"))

                # Initialize progress with actual pages to fetch
                self.root.after(0, lambda: self._update_progress(
                    0, actual_pages_to_fetch, "Starting fetch..."))

                # Add words from first page
                first_page_words = first_page.get("word_list", [])
                words_to_add = min(len(first_page_words), max_words) if max_words else len(
                    first_page_words)
                all_words.extend(first_page_words[:words_to_add])

                # Update progress for first page
                self.root.after(0, lambda: self._update_progress(
                    1, actual_pages_to_fetch, f"Added {words_to_add} words"))
                self.root.after(0, lambda: self._add_output_message(
                    f"Page 1/{total_pages}: Added {words_to_add} words"))

                # Check if we've reached the limit
                if max_words and len(all_words) >= max_words:
                    self.root.after(0, lambda: self._add_output_message(
                        f"Reached maximum word limit of {max_words}. Stopping fetch."))
                    self.root.after(0, lambda: self._update_progress(
                        actual_pages_to_fetch, actual_pages_to_fetch, "Limit reached"))
                    # Merge with database before returning
                    self.word_manager.merge_with_database(
                        all_words, length, is_partial=True)
                    return all_words

                if self.word_manager._should_exit():
                    self.word_manager.merge_with_database(
                        all_words, length, is_partial=True)
                    return all_words

                # Fetch remaining pages
                pages_fetched = 1
                for page_num in range(2, total_pages + 1):
                    if self.word_manager._should_exit():
                        self.root.after(0, lambda: self._add_output_message(
                            f"Graceful exit requested. Stopping at page {page_num-1}/{total_pages}"))
                        self.root.after(0, lambda pf=pages_fetched, ap=actual_pages_to_fetch:
                                        self._update_progress(pf, ap, "Stopped by user"))
                        self.word_manager.merge_with_database(
                            all_words, length, is_partial=True)
                        break

                    try:
                        # Add page_token parameter for subsequent pages
                        page_params = base_params.copy()
                        page_params["page_token"] = page_num - \
                            1  # API uses 0-based page tokens

                        # Update progress before fetching
                        self.root.after(0, lambda p=page_num, t=total_pages, pf=pages_fetched, ap=actual_pages_to_fetch:
                                        self._update_progress(pf, ap, f"Fetching page {p}/{t}..."))
                        self.root.after(0, lambda p=page_num, t=total_pages: self._add_output_message(
                            f"Fetching page {p}/{t}..."))

                        page_response = await client.get(self.word_manager.base_url, params=page_params)
                        page_response_data = page_response.json()

                        # Extract words from this page
                        page_word_pages = page_response_data.get(
                            "word_pages", [])
                        if page_word_pages:
                            page_words = page_word_pages[0].get(
                                "word_list", [])

                            # Check how many words we can add without exceeding limit
                            if max_words:
                                remaining_slots = max_words - len(all_words)
                                words_to_add = min(
                                    len(page_words), remaining_slots)
                                all_words.extend(page_words[:words_to_add])

                                pages_fetched += 1
                                self.root.after(0, lambda pf=pages_fetched, ap=actual_pages_to_fetch, w=words_to_add:
                                                self._update_progress(pf, ap, f"Added {w} words (Total: {len(all_words)})"))
                                self.root.after(0, lambda p=page_num, t=total_pages, w=words_to_add:
                                                self._add_output_message(f"Page {p}/{t}: Added {w} words"))

                                # Check if we've reached the limit
                                if len(all_words) >= max_words:
                                    self.root.after(0, lambda: self._add_output_message(
                                        f"Reached maximum word limit of {max_words}. Stopping fetch."))
                                    self.root.after(0, lambda pf=pages_fetched, ap=actual_pages_to_fetch:
                                                    self._update_progress(pf, ap, "Limit reached"))
                                    break
                            else:
                                all_words.extend(page_words)
                                pages_fetched += 1
                                self.root.after(0, lambda pf=pages_fetched, ap=actual_pages_to_fetch, w=len(page_words):
                                                self._update_progress(pf, ap, f"Added {w} words (Total: {len(all_words)})"))
                                self.root.after(0, lambda p=page_num, t=total_pages, w=len(page_words):
                                                self._add_output_message(f"Page {p}/{t}: Added {w} words"))
                        else:
                            pages_fetched += 1
                            self.root.after(0, lambda pf=pages_fetched, ap=actual_pages_to_fetch:
                                            self._update_progress(pf, ap, "No words found"))
                            self.root.after(0, lambda p=page_num, t=total_pages:
                                            self._add_output_message(f"Page {p}/{t}: No words found"))

                        # Check if we've fetched enough pages for the limit
                        if max_words and pages_fetched >= actual_pages_to_fetch:
                            break

                        # Small delay to be respectful to the API
                        if not self.word_manager._should_exit():
                            await asyncio.sleep(0.1)

                    except KeyboardInterrupt:
                        self.root.after(0, lambda p=page_num: self._add_output_message(
                            f"\nKeyboard interrupt detected at page {p}"))
                        self.root.after(0, lambda pf=pages_fetched, ap=actual_pages_to_fetch:
                                        self._update_progress(pf, ap, "Interrupted"))
                        if self.word_manager.signal_handler:
                            self.word_manager.signal_handler.should_exit = True
                        self.word_manager.merge_with_database(
                            all_words, length, is_partial=True)
                        break
                    except Exception as e:
                        self.root.after(0, lambda p=page_num, err=str(e): self._add_output_message(
                            f"Error fetching page {p}: {err}"))
                        self.root.after(0, lambda pf=pages_fetched, ap=actual_pages_to_fetch:
                                        self._update_progress(pf, ap, "Error occurred"))
                        if self.word_manager._should_exit():
                            self.word_manager.merge_with_database(
                                all_words, length, is_partial=True)
                            break

                # Determine if this is a partial or complete result
                is_partial = (max_words and len(all_words) >=
                              max_words) or self.word_manager._should_exit()

                if is_partial:
                    self.root.after(0, lambda: self._update_progress(
                        pages_fetched, actual_pages_to_fetch, "Limited fetch completed"))
                    self.root.after(0, lambda: self._add_output_message(
                        f"\nLimited fetch completed. Collected {len(all_words)} words."))
                else:
                    self.root.after(0, lambda: self._update_progress(
                        actual_pages_to_fetch, actual_pages_to_fetch, "Fetch completed"))
                    self.root.after(0, lambda: self._add_output_message(
                        f"\nCompleted! Total words collected: {len(all_words)}"))

                # Merge with database
                self.word_manager.merge_with_database(
                    all_words, length, is_partial=is_partial)

            except KeyboardInterrupt:
                self.root.after(0, lambda: self._add_output_message(
                    f"\nKeyboard interrupt detected during initial setup."))
                self.root.after(
                    0, lambda: self._update_progress(0, 1, "Interrupted"))
                if self.word_manager.signal_handler:
                    self.word_manager.signal_handler.should_exit = True
                if all_words:
                    self.word_manager.merge_with_database(
                        all_words, length, is_partial=True)
            except Exception as e:
                self.root.after(0, lambda err=str(
                    e): self._add_output_message(f"Unexpected error: {err}"))
                self.root.after(0, lambda: self._update_progress(
                    0, 1, "Error occurred"))
                if self.word_manager.signal_handler:
                    self.word_manager.signal_handler.should_exit = True
                if all_words:
                    self.word_manager.merge_with_database(
                        all_words, length, is_partial=True)

        return all_words

    def _fetch_completed(self, new_words):
        """Handle successful fetch completion."""
        self.fetch_in_progress = False
        self.continue_btn.config(state='normal', text="Start API Fetch")
        self.cancel_btn.config(state='normal')

        # Complete the progress bar
        self._update_progress(self.total_pages or 1,
                              self.total_pages or 1, "Processing results...")

        # Store the word count before processing to calculate actual new words
        words_before_fetch = len(self.cached_words)

        self._add_output_message(
            f"Fetch completed! Retrieved {len(new_words)} words from API.")

        # Add message about database unification
        self._add_output_message(
            "Unifying database and updating with recent results...")

        # Reload words directly from SQLite database instead of using the compatibility adapter
        try:
            # Get ALL words from all lengths using the optimized database
            length_distribution = self.word_manager.get_length_distribution()
            updated_words = []

            for word_length in length_distribution.keys():
                words_for_length = self.word_manager.db.get_words_by_length(
                    word_length)
                updated_words.extend(words_for_length)

            if updated_words:
                self.cached_words = sorted(
                    updated_words, key=lambda x: x.get('word', '').lower())
                self.filtered_words = self.cached_words.copy()
                self._populate_table()
                self._update_statistics()

                # Update header count
                self._update_header_count()

                # Calculate actual new words added to database
                words_after_fetch = len(self.cached_words)
                actual_new_words = words_after_fetch - words_before_fetch
                existing_words = len(new_words) - actual_new_words

                # Create detailed completion message
                if actual_new_words > 0:
                    self._add_output_message(
                        f"Database update complete! Added {actual_new_words} new words, {existing_words} already existed.")
                else:
                    self._add_output_message(
                        f"Database update complete! All {len(new_words)} words already existed in database.")

                self._add_output_message(
                    f"Now displaying {len(self.cached_words)} total words (all lengths).")
            else:
                # Fallback to new words if database extraction fails
                self.cached_words = new_words
                self.filtered_words = sorted(
                    new_words, key=lambda x: x.get('word', '').lower())
                self._populate_table()
                self._update_statistics()
                self._update_header_count()

                self._add_output_message("Using fetched words for display.")

        except Exception as e:
            self._add_output_message(f"Error updating from database: {e}")
            # Fallback to new words
            if new_words:
                self.cached_words = new_words
                self.filtered_words = sorted(
                    new_words, key=lambda x: x.get('word', '').lower())
                self._populate_table()
                self._update_statistics()
                self._update_header_count()

        # Calculate final statistics for completion dialog
        words_after_fetch = len(self.cached_words)
        actual_new_words = max(0, words_after_fetch - words_before_fetch)
        existing_words = len(new_words) - actual_new_words

        # Final progress update
        self._update_progress(self.total_pages or 1, self.total_pages or 1,
                              f"Complete! {len(self.cached_words)} total words")

        # Create detailed completion dialog message using custom alert
        if actual_new_words > 0:
            completion_msg = (
                f"Fetch completed successfully!\n\n"
                f"📊 Summary:\n"
                f"  • New words added: {actual_new_words:,}\n"
                f"  • Words already existed: {existing_words:,}\n"
                f"  • Total words fetched: {len(new_words):,}\n\n"
                f"🗄️ Database Status:\n"
                f"  • Total words in database: {len(self.cached_words):,} (all lengths)\n\n"
                f"The new words have been successfully added to your local database and are now available for searching."
            )

            CustomAlert.show_success(
                self.root,
                title="Fetch Complete - Success!",
                message=completion_msg,
                theme_colors=self._get_theme_colors()
            )
        else:
            completion_msg = (
                f"Fetch completed successfully!\n\n"
                f"📊 Summary:\n"
                f"  • No new words were added\n"
                f"  • All {len(new_words):,} words already existed in the database\n\n"
                f"🗄️ Database Status:\n"
                f"  • Total words in database: {len(self.cached_words):,} (all lengths)\n\n"
                f"This means your database is already up-to-date with the available words for your search criteria."
            )

            CustomAlert.show_info(
                self.root,
                title="Fetch Complete - No New Words",
                message=completion_msg,
                theme_colors=self._get_theme_colors()
            )

    def _update_header_count(self):
        """Update the word count in the header."""
        if hasattr(self, 'root') and self.root:
            # More reliable way to find the header count label
            def find_count_label(widget):
                if isinstance(widget, tk.Label):
                    text = widget.cget('text')
                    if text.startswith('Total Words:'):
                        widget.config(
                            text=f"Total Words: {len(self.cached_words)}")
                        return True
                # Recursively search in child widgets
                for child in widget.winfo_children():
                    if find_count_label(child):
                        return True
                return False

            find_count_label(self.root)

    def _fetch_error(self, error_msg):
        """Handle fetch error."""
        self.fetch_in_progress = False
        self.continue_btn.config(state='normal', text="Start API Fetch")
        self.cancel_btn.config(state='normal')

        # Update progress to show error
        self._update_progress(0, 1, "Fetch failed")

        self._add_output_message(f"Fetch failed: {error_msg}")

        # Use custom alert for error
        error_message = (
            f"Failed to fetch words from the API.\n\n"
            f"❌ Error Details:\n"
            f"  {error_msg}\n\n"
            f"💡 Troubleshooting:\n"
            f"  • Check your internet connection\n"
            f"  • Try reducing the page size\n"
            f"  • Verify the API service is available\n"
            f"  • Check if your search parameters are valid"
        )

        CustomAlert.show_error(
            self.root,
            title="Fetch Error",
            message=error_message,
            theme_colors=self._get_theme_colors()
        )

    def _use_cached_only(self):
        """Use only cached words without fetching."""
        self.continue_fetch = False
        self._add_output_message(
            "Using cached words only. No API fetch performed.")

        # Use custom alert for cached words only message
        cached_message = (
            f"Using cached words only.\n\n"
            f"📋 Current Database Status:\n"
            f"  • Total words in database: {len(self.cached_words):,}\n"
            f"  • No new words will be fetched from the API\n\n"
            f"You can browse and search through your existing cached words, "
            f"or restart the fetch process later if needed."
        )

        CustomAlert.show_info(
            self.root,
            title="Cached Words Only",
            message=cached_message,
            theme_colors=self._get_theme_colors()
        )

    def _populate_table(self):
        """Populate the table with word data."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add words to the table
        for word_data in self.filtered_words:
            word = word_data.get('word', 'N/A')
            length = len(word) if word != 'N/A' else 0
            points = word_data.get('points', 0)

            self.tree.insert('', 'end', values=(
                word, length, points))

    def _on_search_change(self, *args):
        """Handle search text changes with debounced delay."""
        # Cancel any pending search
        if self.search_delay_timer:
            self.root.after_cancel(self.search_delay_timer)

        # Schedule new search after delay
        self.search_delay_timer = self.root.after(
            self.search_delay_ms, self._apply_filters)

    def _on_length_filter_change(self, *args):
        """Handle length filter changes with debounced delay."""
        # Cancel any pending search
        if self.search_delay_timer:
            self.root.after_cancel(self.search_delay_timer)

        # Schedule new search after delay
        self.search_delay_timer = self.root.after(
            self.search_delay_ms, self._apply_filters)

    def _apply_filters(self):
        """Apply search and length filters with length-based optimization and lazy loading."""
        search_term = self.search_var.get()
        length_filter = self.length_filter_var.get()

        # Avoid redundant searches
        if search_term == self.last_search_term and length_filter == self.last_length_filter:
            return

        self.last_search_term = search_term
        self.last_length_filter = length_filter

        # Show loading indicator for large datasets
        if len(self.cached_words) > 50000:
            self._show_loading_indicator("Filtering...")

        # Start with all cached words - NO DATABASE QUERIES, only in-memory filtering
        filtered_words = []

        # Determine target length for optimization
        target_length = None
        if length_filter != "All":
            try:
                target_length = int(length_filter)
            except ValueError:
                target_length = None

        # If we have a search term, determine minimum length for optimization
        search_min_length = len(search_term) if search_term else 0

        # Optimize by filtering length first, then content
        for word_data in self.cached_words:
            word = word_data.get('word', '')
            word_length = len(word)

            # Apply length filter first (most restrictive)
            if target_length is not None and word_length != target_length:
                continue

            # Apply search filter if we have a search term
            if search_term:
                # Check if this should be treated as a pattern search (contains _ or * and length > 1)
                if ('_' in search_term or '*' in search_term) and len(search_term) > 1:
                    # Handle special cases for prefix/suffix searches first (more efficient)
                    if search_term.startswith('*') and not search_term.endswith('*'):
                        # Suffix search: *word -> ends with "word"
                        suffix = search_term[1:]  # Remove leading *
                        if suffix and word.lower().endswith(suffix.lower()):
                            filtered_words.append(word_data)
                    elif search_term.endswith('*') and not search_term.startswith('*'):
                        # Prefix search: word* -> starts with "word"
                        prefix = search_term[:-1]  # Remove trailing *
                        if prefix and word.lower().startswith(prefix.lower()):
                            filtered_words.append(word_data)
                    else:
                        # General pattern search with both _ and * wildcards
                        # Replace wildcards with placeholders, escape the rest, then replace placeholders with regex
                        underscore_placeholder = "___UNDERSCORE_PLACEHOLDER___"
                        asterisk_placeholder = "___ASTERISK_PLACEHOLDER___"

                        temp_term = search_term.replace(
                            '_', underscore_placeholder)
                        temp_term = temp_term.replace(
                            '*', asterisk_placeholder)
                        escaped_term = re.escape(temp_term)
                        regex_pattern = escaped_term.replace(
                            underscore_placeholder, '.')
                        regex_pattern = regex_pattern.replace(
                            asterisk_placeholder, '.*')

                        try:
                            # Compile the regex pattern
                            pattern = re.compile(
                                f'^{regex_pattern}$', re.IGNORECASE)
                            if pattern.match(word):
                                filtered_words.append(word_data)
                        except re.error:
                            # If regex compilation fails, fall back to simple substring search
                            if search_term.lower() in word.lower():
                                filtered_words.append(word_data)
                else:
                    # Regular substring search
                    if search_term.lower() in word.lower():
                        filtered_words.append(word_data)
            else:
                # No search term, just add the word (length filter already applied above)
                filtered_words.append(word_data)

        # Store all filtered results (no artificial cap)
        self.filtered_words = filtered_words
        self.virtual_total_items = len(filtered_words)

        # Reset virtual scrolling
        self.virtual_start_index = 0

        # Hide loading indicator
        if len(self.cached_words) > 50000:
            self._hide_loading_indicator()

        # Load first page of results
        self._load_virtual_page()
        self._update_statistics()

    def _show_loading_indicator(self, message="Loading..."):
        """Show a loading indicator in the stats panel."""
        if self.stats_text:
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(tk.END, f"⏳ {message}")
            self.stats_text.config(state=tk.DISABLED)
            self.root.update_idletasks()

    def _hide_loading_indicator(self):
        """Hide the loading indicator."""
        # This will be handled by _update_stats() call after filtering
        pass

    def _clear_search(self):
        """Clear the search field and length filter."""
        self.search_var.set('')
        self.length_filter_var.set('All')

    def _header_sort(self, column):
        """Handle header click sorting with 3-state cycle: none -> desc -> asc -> none."""
        # Reset other columns to no sorting
        for col in self.sort_direction:
            if col != column:
                self.sort_direction[col] = 0
                self.tree.heading(col, text=col)  # Remove sort indicators

        # Cycle through sort states for clicked column
        current_state = self.sort_direction[column]
        next_state = (current_state + 1) % 3
        self.sort_direction[column] = next_state

        # Update header text with sort indicators
        if next_state == 0:  # No sorting
            self.tree.heading(column, text=column)
            self.current_sort_column = None
            # Reset to original order (alphabetical by word)
            self.filtered_words.sort(key=lambda x: x.get('word', '').lower())
        elif next_state == 1:  # Descending
            self.tree.heading(column, text=f"{column} ↓")
            self.current_sort_column = column
            self._sort_by_column(column, reverse=True)
        else:  # Ascending
            self.tree.heading(column, text=f"{column} ↑")
            self.current_sort_column = column
            self._sort_by_column(column, reverse=False)

        # Update header colors
        self._update_header_colors()

        # Reset virtual scrolling to top and reload
        self.virtual_start_index = 0
        self._load_virtual_page()
        self._update_statistics()

    def _sort_by_column(self, column, reverse=False):
        """Sort filtered words by the specified column."""
        if column == 'Word':
            self.filtered_words.sort(key=lambda x: x.get(
                'word', '').lower(), reverse=reverse)
        elif column == 'Length':
            self.filtered_words.sort(key=lambda x: len(
                x.get('word', '')), reverse=reverse)
        elif column == 'Points':
            self.filtered_words.sort(
                key=lambda x: x.get('points', 0), reverse=reverse)

    def _update_header_colors(self):
        """Update header colors - keep default colors and rely on text indicators for sorting."""
        style = ttk.Style()
        colors = self._get_theme_colors()

        # Always use default header colors - don't change colors based on sorting
        # The sort indicators (↓, ↑) in the text are sufficient visual feedback
        style.configure("Treeview.Heading",
                        background=colors['button_bg'],
                        foreground=colors['button_fg'],
                        font=('Arial', 10, 'bold'))

    def _on_word_double_click(self, event):
        """Handle double-click on a word."""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            word = item['values'][0]
            length = item['values'][1]
            points = item['values'][2]

            messagebox.showinfo(
                f"Word Details: {word}",
                f"Word: {word}\nLength: {length}\nPoints: {points}"
            )

    def _on_window_close(self):
        """Handle window close event with proper signal integration."""
        if self.fetch_in_progress:
            result = messagebox.askyesno(
                "Fetch in Progress",
                "A fetch operation is in progress. Do you want to stop it and close?\n\n"
                "This will trigger graceful shutdown and save partial results."
            )
            if result:
                # Signal graceful exit to any running operations
                if self.signal_handler:
                    self.signal_handler.should_exit = True
                self._close_window()
        else:
            self._close_window()

    def _close_window(self):
        """Close the window and cleanup."""
        try:
            # Signal graceful exit
            if self.signal_handler:
                self.signal_handler.should_exit = True

            # Stop the GUI
            if self.root:
                self.root.quit()
                self.root.destroy()
        except Exception as e:
            print(f"Error during window close: {e}")

    def _check_signals(self):
        """Periodically check for exit signals and handle them gracefully."""
        if self.signal_handler and self.signal_handler.is_exit_requested():
            self._add_output_message(
                "Graceful exit requested. Closing application...")

            if self.fetch_in_progress:
                self._add_output_message(
                    "Stopping fetch operation and saving partial results...")
                # The fetch operations will handle the graceful exit themselves

            # Close the window after a brief delay to allow messages to display
            self.root.after(1000, self._close_window)
            return

        # Schedule next check in 100ms
        if self.root:
            self.root.after(100, self._check_signals)

    def _handle_keyboard_interrupt(self, event=None):
        """Handle keyboard interrupt (Ctrl+C or Ctrl+Q) for graceful exit."""
        if self.signal_handler:
            self.signal_handler.should_exit = True

        self._add_output_message(
            "Keyboard interrupt detected. Initiating graceful shutdown...")

        if self.fetch_in_progress:
            self._add_output_message(
                "Stopping fetch operation and saving partial results...")

        # Close the window after a brief delay
        self.root.after(500, self._close_window)

    def _export_words(self):
        """Export filtered words to a file."""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"),
                           ("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Words"
            )

            if filename:
                if filename.endswith('.json'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.filtered_words, f,
                                  indent=2, ensure_ascii=False)
                elif filename.endswith('.csv'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write("Word,Length,Points\n")
                        for word_data in self.filtered_words:
                            word = word_data.get('word', 'N/A')
                            length = len(word) if word != 'N/A' else 0
                            points = word_data.get('points', 0)
                            f.write(f'"{word}",{length},{points}\n')
                else:  # Text file
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(
                            f"Exported Words ({len(self.filtered_words)} total)\n")
                        f.write("=" * 50 + "\n\n")
                        for word_data in self.filtered_words:
                            word = word_data.get('word', 'N/A')
                            length = len(word) if word != 'N/A' else 0
                            points = word_data.get('points', 0)
                            f.write(f"{word:<15} {length:<8} {points}\n")

                messagebox.showinfo("Export Successful",
                                    f"Words exported to {filename}")
        except Exception as e:
            messagebox.showerror(
                "Export Error", f"Failed to export words: {e}")

    def _center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _update_progress(self, current_page: int, total_pages: int, additional_info: str = ""):
        """Update the progress bar and label."""
        if self.progress_bar and self.progress_label:
            self.current_page = current_page
            self.total_pages = total_pages

            if total_pages > 0:
                self.progress_percentage = (current_page / total_pages) * 100
                self.progress_bar['value'] = self.progress_percentage

                progress_text = f"Progress: {current_page}/{total_pages} pages ({self.progress_percentage:.1f}%)"
                if additional_info:
                    progress_text += f" - {additional_info}"

                self.progress_label.config(text=progress_text)
            else:
                self.progress_bar['value'] = 0
                self.progress_label.config(text="Initializing...")

            # Force GUI update
            self.root.update_idletasks()

    def _reset_progress(self):
        """Reset the progress bar to initial state."""
        if self.progress_bar and self.progress_label:
            self.progress_bar['value'] = 0
            self.progress_label.config(text="Ready to start fetch...")
            self.total_pages = 0
            self.current_page = 0
            self.progress_percentage = 0
            self.root.update_idletasks()

    def _load_virtual_page(self):
        """Load initial page of results for infinite scrolling."""
        if not self.filtered_words:
            self.virtual_loaded_items = []
            self.virtual_loaded_count = 0
            self._populate_table_virtual()
            self._update_statistics()
            return

        # Load initial page
        initial_load = min(self.virtual_page_size, len(self.filtered_words))
        self.virtual_loaded_items = self.filtered_words[:initial_load]
        self.virtual_loaded_count = initial_load

        # Populate table with initial items
        self._populate_table_virtual()
        self._update_statistics()

        print(
            f"Loaded initial page: {initial_load} items of {len(self.filtered_words)} total")

    def _load_next_page(self):
        """Load the next page of items and append to table - infinite scrolling."""
        if self.virtual_loaded_count >= len(self.filtered_words):
            return  # Already loaded everything

        # Calculate next batch
        start_idx = self.virtual_loaded_count
        end_idx = min(len(self.filtered_words),
                      start_idx + self.virtual_page_size)

        # Get next batch of items
        next_batch = self.filtered_words[start_idx:end_idx]

        # Append to loaded items (don't replace)
        self.virtual_loaded_items.extend(next_batch)
        self.virtual_loaded_count = len(self.virtual_loaded_items)

        # Append new items to table (don't clear existing)
        self._append_items_to_table(next_batch)
        self._update_statistics()

        print(
            f"Loaded next page: items {start_idx}-{end_idx-1}, total loaded: {self.virtual_loaded_count}/{len(self.filtered_words)}")

    def _load_all_items(self):
        """Load all items when total count is small."""
        self.virtual_loaded_items = self.filtered_words.copy()
        self.virtual_loaded_count = len(self.virtual_loaded_items)
        self._populate_table_virtual()
        self._update_statistics()

    def _populate_table_virtual(self):
        """Populate the table with all currently loaded items (initial load or reset)."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add all loaded items to the table
        for word_data in self.virtual_loaded_items:
            word = word_data.get('word', 'N/A')
            length = len(word) if word != 'N/A' else 0
            points = word_data.get('points', 0)
            self.tree.insert('', 'end', values=(word, length, points))

    def _append_items_to_table(self, new_items):
        """Append new items to the existing table without clearing."""
        for word_data in new_items:
            word = word_data.get('word', 'N/A')
            length = len(word) if word != 'N/A' else 0
            points = word_data.get('points', 0)
            self.tree.insert('', 'end', values=(word, length, points))

    def _on_tree_scroll(self, *args):
        """Handle treeview scroll events and update scrollbar."""
        # Update scrollbar first
        if hasattr(self, 'v_scrollbar'):
            self.v_scrollbar.set(*args)

        # Debounce scroll checking to avoid excessive calls
        if self.virtual_scroll_timer:
            self.root.after_cancel(self.virtual_scroll_timer)
        self.virtual_scroll_timer = self.root.after(
            50, self._check_virtual_scroll_position)

    def _on_scrollbar_move(self, action, position, *args):
        """Handle scrollbar movement."""
        # Update the tree view
        self.tree.yview(action, position, *args)

        # Debounce scroll checking
        if self.virtual_scroll_timer:
            self.root.after_cancel(self.virtual_scroll_timer)
        self.virtual_scroll_timer = self.root.after(
            50, self._check_virtual_scroll_position)

    def _on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling."""
        # Debounce scroll checking
        if self.virtual_scroll_timer:
            self.root.after_cancel(self.virtual_scroll_timer)
        self.virtual_scroll_timer = self.root.after(
            100, self._check_virtual_scroll_position)

    def _check_virtual_scroll_position(self):
        """Check if we need to load more data based on scroll position - infinite scrolling."""
        try:
            if not self.filtered_words:
                return

            total_items = len(self.filtered_words)

            # If we have fewer items than one page, load all and no scrolling needed
            if total_items <= self.virtual_page_size:
                if self.virtual_loaded_count != total_items:
                    self._load_all_items()
                return

            # Get current scroll position
            try:
                scroll_top, scroll_bottom = self.tree.yview()
            except:
                return

            # Check if scroll position changed significantly
            if abs(scroll_bottom - self.last_scroll_position) < 0.01:
                return  # Not enough change to warrant update

            self.last_scroll_position = scroll_bottom

            # Check if we're near the bottom and need to load more items
            # Load more when we're 80% down the currently loaded items
            if scroll_bottom > 0.8 and self.virtual_loaded_count < total_items:
                self._load_next_page()
                print(
                    f"Infinite scroll triggered: scroll_bottom={scroll_bottom:.3f}, loaded={self.virtual_loaded_count}/{total_items}")

        except Exception as e:
            print(f"Virtual scroll error: {e}")

    def _update_statistics(self):
        """Update the statistics display."""
        if not self.filtered_words:
            stats_text = "No words found"
        else:
            total_count = len(self.filtered_words)
            loaded_count = self.virtual_loaded_count

            # Show loaded vs total for infinite scrolling
            if loaded_count < total_count:
                stats_text = f"Showing {loaded_count:,} of {total_count:,} words (scroll for more)"
            else:
                stats_text = f"Showing all {total_count:,} words"

            # Add performance tip for large result sets
            if total_count > 5000:
                stats_text += " • Use more specific search terms for better performance"

        # Update the stats display using the correct text widget
        if self.stats_text:
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(tk.END, stats_text)
            self.stats_text.config(state=tk.DISABLED)


def main():
    """Test the GUI interface with sample data."""
    from src.word_manager import WordManager
    from src.signal_handler import SignalHandler

    # Initialize components
    signal_handler = SignalHandler()
    word_manager = WordManager(
        signal_handler, database_file="database/word_database.db")
    word_display_gui = WordDisplayGUI(word_manager)

    # Create window with sample length
    length = 4
    cached_words = word_display_gui.create_window(length, wait_for_user=False)

    print(f"Displayed {len(cached_words)} cached {length}-letter words in GUI")


if __name__ == "__main__":
    main()
