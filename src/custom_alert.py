import tkinter as tk
from typing import Optional, Dict, Any


class CustomAlert:
    """Custom alert dialog that matches the application theme."""

    def __init__(self, parent, title="Alert", message="", alert_type="info", theme_colors=None):
        """
        Create a custom alert dialog.

        Args:
            parent: Parent window
            title: Dialog title
            message: Message to display
            alert_type: Type of alert ('info', 'success', 'warning', 'error')
            theme_colors: Color scheme dictionary
        """
        self.parent = parent
        self.title = title
        self.message = message
        self.alert_type = alert_type
        self.theme_colors = theme_colors or self._get_default_colors()
        self.dialog = None
        self.result = None

    def _get_default_colors(self):
        """Get default color scheme."""
        return {
            'bg': '#2b2b2b',
            'fg': '#ffffff',
            'button_bg': '#404040',
            'button_fg': '#ffffff',
            'button_active': '#505050',
            'entry_bg': '#404040',
            'entry_fg': '#ffffff'
        }

    def _get_alert_colors(self):
        """Get colors based on alert type."""
        colors = self.theme_colors.copy()

        if self.alert_type == 'success':
            colors['accent'] = '#27ae60'
            colors['icon'] = '✅'
        elif self.alert_type == 'warning':
            colors['accent'] = '#f39c12'
            colors['icon'] = '⚠️'
        elif self.alert_type == 'error':
            colors['accent'] = '#e74c3c'
            colors['icon'] = '❌'
        else:  # info
            colors['accent'] = '#3498db'
            colors['icon'] = 'ℹ️'

        return colors

    def show(self, width=None, height=None):
        """Show the alert dialog."""
        colors = self._get_alert_colors()

        # Calculate appropriate dimensions based on message length
        if width is None:
            # Base width of 400, but expand for longer messages
            message_length = len(self.message)
            if message_length > 200:
                width = min(600, 400 + (message_length - 200) // 3)
            else:
                width = 450  # Slightly wider default

        if height is None:
            # Calculate height based on estimated lines
            estimated_lines = max(3, self.message.count(
                '\n') + len(self.message) // 60)
            height = min(400, 250 + estimated_lines * 20)

        # Create dialog window
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.configure(bg=colors['bg'])
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        # Allow resizing for better user control
        self.dialog.resizable(True, True)
        self.dialog.minsize(400, 200)  # Set minimum size

        # Set initial size
        self.dialog.geometry(f"{width}x{height}")

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Main frame with better padding
        main_frame = tk.Frame(self.dialog, bg=colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=25, pady=20)

        # Icon and title frame
        header_frame = tk.Frame(main_frame, bg=colors['bg'])
        header_frame.pack(fill='x', pady=(0, 15))

        # Icon
        icon_label = tk.Label(header_frame, text=colors['icon'],
                              font=('Arial', 24), bg=colors['bg'], fg=colors['accent'])
        icon_label.pack(side='left', padx=(0, 10))

        # Title
        title_label = tk.Label(header_frame, text=self.title,
                               font=('Arial', 14, 'bold'),
                               bg=colors['bg'], fg=colors['fg'])
        title_label.pack(side='left', anchor='w')

        # Message frame
        message_frame = tk.Frame(main_frame, bg=colors['bg'])
        message_frame.pack(fill='both', expand=True, pady=(0, 20))

        # Message text with proper padding and scrollbar if needed
        text_frame = tk.Frame(message_frame, bg=colors['bg'])
        text_frame.pack(fill='both', expand=True)

        message_text = tk.Text(text_frame, wrap=tk.WORD, font=('Arial', 11),
                               bg=colors['bg'], fg=colors['fg'],
                               relief=tk.FLAT, borderwidth=0,
                               state='normal', cursor='arrow',
                               padx=10, pady=5,  # Add internal padding
                               selectbackground=colors.get('button_bg', '#404040'))

        # Add scrollbar for long messages
        scrollbar = tk.Scrollbar(
            text_frame, orient='vertical', command=message_text.yview)
        message_text.configure(yscrollcommand=scrollbar.set)

        # Pack text widget and scrollbar
        message_text.pack(side='left', fill='both', expand=True)

        # Only show scrollbar if needed (will be determined after text insertion)
        scrollbar.pack(side='right', fill='y')
        scrollbar.pack_forget()  # Hide initially

        # Insert message and make read-only
        message_text.insert('1.0', self.message)
        message_text.config(state='disabled')

        # Check if scrollbar is needed
        self.dialog.update_idletasks()
        if message_text.yview()[1] < 1.0:  # If not all text is visible
            scrollbar.pack(side='right', fill='y')

        # Button frame
        button_frame = tk.Frame(main_frame, bg=colors['bg'])
        button_frame.pack(fill='x')

        # OK button
        ok_button = tk.Button(button_frame, text="OK",
                              command=self._on_ok,
                              bg=colors['accent'], fg='white',
                              font=('Arial', 11, 'bold'),
                              padx=30, pady=8, cursor='hand2',
                              relief='raised', bd=2)
        ok_button.pack(anchor='center')

        # Bind Enter and Escape keys
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        self.dialog.bind('<KP_Enter>', lambda e: self._on_ok())
        self.dialog.bind('<Escape>', lambda e: self._on_ok())

        # Focus on OK button
        ok_button.focus_set()

        # Wait for dialog to close
        self.dialog.wait_window()
        return self.result

    def _on_ok(self):
        """Handle OK button click."""
        self.result = True
        self.dialog.destroy()

    @staticmethod
    def show_info(parent, title="Information", message="", theme_colors=None):
        """Show an info alert."""
        alert = CustomAlert(parent, title, message, "info", theme_colors)
        # Info messages can be longer, so provide adequate space
        return alert.show(width=500, height=300)

    @staticmethod
    def show_success(parent, title="Success", message="", theme_colors=None):
        """Show a success alert."""
        alert = CustomAlert(parent, title, message, "success", theme_colors)
        # Success messages tend to be longer, so provide more space
        return alert.show(width=500, height=300)

    @staticmethod
    def show_warning(parent, title="Warning", message="", theme_colors=None):
        """Show a warning alert."""
        alert = CustomAlert(parent, title, message, "warning", theme_colors)
        return alert.show()

    @staticmethod
    def show_error(parent, title="Error", message="", theme_colors=None):
        """Show an error alert."""
        alert = CustomAlert(parent, title, message, "error", theme_colors)
        return alert.show()
