#!/usr/bin/env python3
"""
Physical Media TUI Editor
A fast Terminal User Interface for editing markdown tables.

Usage: python media_tui.py [filename.md]
"""

import sys
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    DataTable, Footer, Header, Static, Input, Label,
    Button, DirectoryTree, ListView, ListItem
)
from textual.screen import Screen, ModalScreen
from textual.message import Message
from textual import events
from textual.reactive import reactive
from textual.coordinate import Coordinate


class AddEntryScreen(ModalScreen[Optional[Tuple[str, str]]]):
    """Modal screen for adding new entries."""

    def __init__(self, field1_name: str = "Field 1", field2_name: str = "Field 2"):
        super().__init__()
        self.field1_name = field1_name
        self.field2_name = field2_name

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"Add New Entry", classes="dialog-title"),
            Label(f"{self.field1_name}:"),
            Input(placeholder=f"Enter {self.field1_name.lower()}...", id="field1"),
            Label(f"{self.field2_name}:"),
            Input(placeholder=f"Enter {self.field2_name.lower()}...", id="field2"),
            Horizontal(
                Button("Add", variant="primary", id="add"),
                Button("Cancel", variant="default", id="cancel"),
                classes="dialog-buttons"
            ),
            classes="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            field1 = self.query_one("#field1", Input).value.strip()
            field2 = self.query_one("#field2", Input).value.strip()

            if field1 and field2:
                self.dismiss((field1, field2))
            else:
                self.notify("Please fill in both fields", severity="warning")
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "field1":
            self.query_one("#field2", Input).focus()
        elif event.input.id == "field2":
            # Trigger add button
            self.query_one("#add", Button).press()


class FilePickerScreen(ModalScreen[Optional[str]]):
    """Modal screen for picking markdown files."""

    def __init__(self, directory: str = "."):
        super().__init__()
        self.directory = directory
        self.md_files = []

    def compose(self) -> ComposeResult:
        # Find all .md files
        try:
            for file_path in Path(self.directory).glob("*.md"):
                if file_path.is_file():
                    self.md_files.append(file_path.name)
        except Exception:
            pass

        self.md_files.sort()

        yield Container(
            Static("Select Markdown File", classes="dialog-title"),
            ListView(
                *[ListItem(Label(filename), name=filename) for filename in self.md_files],
                id="file-list"
            ),
            Horizontal(
                Button("Open", variant="primary", id="open"),
                Button("Cancel", variant="default", id="cancel"),
                classes="dialog-buttons"
            ),
            classes="dialog file-picker"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open":
            file_list = self.query_one("#file-list", ListView)
            if file_list.highlighted_child and file_list.highlighted_child.name:
                filename = file_list.highlighted_child.name
                self.dismiss(filename)
            else:
                self.notify("Please select a file", severity="warning")
        else:
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item.name:
            filename = event.item.name
            self.dismiss(filename)


class MediaEditor(App[None]):
    """Main TUI application for editing markdown tables."""

    TITLE = "Physical Media Editor"
    CSS = """
    .dialog {
        align: center middle;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
        width: 60%;
        height: auto;
    }

    .file-picker {
        height: 70%;
    }

    .dialog-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .dialog-buttons {
        align: center middle;
        margin-top: 1;
    }

    .dialog-buttons Button {
        margin: 0 1;
    }

    #status-bar {
        background: $primary;
        color: $text;
        padding: 0 1;
        dock: bottom;
        height: 1;
    }

    #main-container {
        padding: 1;
    }

    DataTable {
        margin: 1 0;
    }

    .info-bar {
        background: $surface;
        color: $text;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    DataTable > .datatable--header {
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $accent 20%;
    }
    """

    BINDINGS = [
        ("ctrl+o", "open_file", "Open File"),
        ("ctrl+s", "save_file", "Save"),
        ("a", "add_entry", "Add Entry"),
        ("d", "delete_entry", "Delete"),
        ("ctrl+q", "quit", "Quit"),
        ("r", "reload_file", "Reload"),
        ("?", "show_help", "Help"),
        ("1", "sort_column_1", "Sort Col 1"),
        ("2", "sort_column_2", "Sort Col 2"),
        ("3", "sort_column_3", "Sort Col 3"),
        ("4", "sort_column_4", "Sort Col 4"),
    ]

    current_file: reactive[str] = reactive("")
    headers: reactive[List[str]] = reactive([])
    data: reactive[List[List[str]]] = reactive([])
    sort_column: reactive[int] = reactive(-1)
    sort_reverse: reactive[bool] = reactive(False)
    modified: reactive[bool] = reactive(False)

    def __init__(self, filename: Optional[str] = None):
        super().__init__()
        self.initial_file = filename
        self.original_data = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            yield Static("No file loaded. Press Ctrl+O to open a file.", id="info-bar", classes="info-bar")
            yield DataTable(id="data-table")
        yield Static("Ready", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        if self.initial_file:
            self.load_file(self.initial_file)
        else:
            self.action_open_file()

    def action_open_file(self) -> None:
        """Open file picker."""
        def on_file_selected(filename: Optional[str]) -> None:
            if filename:
                self.load_file(filename)

        current_dir = Path(self.current_file).parent if self.current_file else Path.cwd()
        self.push_screen(FilePickerScreen(str(current_dir)), on_file_selected)

    def action_save_file(self) -> None:
        """Save current file."""
        if not self.current_file:
            self.notify("No file loaded", severity="error")
            return

        if not self.modified:
            self.notify("No changes to save", severity="information")
            return

        try:
            self.save_file()
            self.notify(f"Saved {Path(self.current_file).name}", severity="success")
        except Exception as e:
            self.notify(f"Error saving: {str(e)}", severity="error")

    def action_add_entry(self) -> None:
        """Add new entry."""
        if not self.headers:
            self.notify("No file loaded", severity="error")
            return

        def on_entry_added(entry: Optional[Tuple[str, str]]) -> None:
            if entry:
                self.add_entry(entry[0], entry[1])

        field1 = self.headers[0] if len(self.headers) > 0 else "Field 1"
        field2 = self.headers[1] if len(self.headers) > 1 else "Field 2"
        self.push_screen(AddEntryScreen(field1, field2), on_entry_added)

    def action_delete_entry(self) -> None:
        """Delete selected entry."""
        table = self.query_one("#data-table", DataTable)
        cursor_coord = table.cursor_coordinate

        if cursor_coord is None or cursor_coord.row < 0:
            self.notify("No row selected", severity="warning")
            return

        row_index = cursor_coord.row
        if row_index < len(self.data):
            # Get the values for confirmation
            row = self.data[row_index]
            preview = " | ".join(row[:2])  # Show first two columns
            if len(preview) > 40:
                preview = preview[:37] + "..."

            # Simple confirmation by deleting directly
            # You could add a confirmation modal here if desired
            self.delete_entry(row_index)
            self.notify(f"Deleted: {preview}", severity="success")

    def action_reload_file(self) -> None:
        """Reload current file."""
        if self.current_file:
            self.load_file(self.current_file)
            self.notify("File reloaded", severity="success")

    def action_show_help(self) -> None:
        """Show help message."""
        help_text = [
            "Ctrl+O: Open file",
            "Ctrl+S: Save file",
            "A: Add entry",
            "D: Delete row",
            "1-4: Sort by column",
            "R: Reload",
            "Ctrl+Q: Quit"
        ]
        self.notify(" | ".join(help_text), timeout=10)

    def action_sort_column_1(self) -> None:
        """Sort by first column."""
        self.sort_by_column_index(0)

    def action_sort_column_2(self) -> None:
        """Sort by second column."""
        self.sort_by_column_index(1)

    def action_sort_column_3(self) -> None:
        """Sort by third column."""
        self.sort_by_column_index(2)

    def action_sort_column_4(self) -> None:
        """Sort by fourth column."""
        self.sort_by_column_index(3)

    def sort_by_column_index(self, column_index: int) -> None:
        """Sort by specific column index."""
        if column_index >= len(self.headers):
            self.notify(f"Column {column_index + 1} doesn't exist")
            return

        if self.sort_column == column_index:
            # Toggle direction
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column_index
            self.sort_reverse = False

        self.sort_data()
        direction = "Z-A" if self.sort_reverse else "A-Z"
        self.notify(f"Sorting by {self.headers[column_index]} ({direction})")

    def load_file(self, filename: str) -> None:
        """Load a markdown file."""
        try:
            file_path = Path(filename)
            if not file_path.exists():
                self.notify(f"File not found: {filename}", severity="error")
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.parse_markdown_table(content)
            self.current_file = str(file_path)
            self.original_data = [row[:] for row in self.data]  # Deep copy
            self.modified = False
            self.sort_column = -1
            self.sort_reverse = False

            self.update_table()
            self.update_info_bar()

            self.notify(f"Loaded {file_path.name} ({len(self.data)} entries)", severity="success")

        except Exception as e:
            self.notify(f"Error loading file: {str(e)}", severity="error")

    def parse_markdown_table(self, content: str) -> None:
        """Parse markdown table from content."""
        lines = content.strip().split('\n')

        # Find header line
        header_line_idx = -1
        for i, line in enumerate(lines):
            if '|' in line and not re.match(r'^[\s\-|:]+$', line.strip()):
                header_line_idx = i
                break

        if header_line_idx == -1:
            raise ValueError("No table header found")

        # Parse headers
        header_line = lines[header_line_idx].strip()
        raw_headers = [h.strip() for h in header_line.split('|')]
        self.headers = [h for h in raw_headers if h]  # Remove empty headers

        if len(self.headers) < 2:
            raise ValueError("Table must have at least 2 columns")

        # Find data start (skip separator line)
        data_start = header_line_idx + 1
        while data_start < len(lines) and re.match(r'^[\s\-|:]+$', lines[data_start].strip()):
            data_start += 1

        # Parse data rows
        self.data = []
        for i in range(data_start, len(lines)):
            line = lines[i].strip()
            if line and '|' in line and not re.match(r'^[\s\-|:]+$', line):
                raw_cells = [c.strip() for c in line.split('|')]
                cells = [c for c in raw_cells if c or raw_cells.index(c) not in [0, len(raw_cells)-1]]

                # Pad or trim to match header count
                while len(cells) < len(self.headers):
                    cells.append('')
                cells = cells[:len(self.headers)]

                if any(cells):  # Only add non-empty rows
                    self.data.append(cells)

    def update_table(self) -> None:
        """Update the DataTable widget."""
        table = self.query_one("#data-table", DataTable)
        table.clear(columns=True)

        if not self.headers:
            return

        # Add columns with sort indicators
        for i, header in enumerate(self.headers):
            label = header
            if self.sort_column == i:
                label += " ↓" if self.sort_reverse else " ↑"
            table.add_column(label, key=str(i))

        # Add rows
        if self.data:
            for row in self.data:
                # Ensure row has enough columns
                padded_row = row + [''] * (len(self.headers) - len(row))
                table.add_row(*padded_row[:len(self.headers)])

    def update_info_bar(self) -> None:
        """Update the info bar."""
        info_bar = self.query_one("#info-bar", Static)

        if not self.current_file:
            info_bar.update("No file loaded. Press Ctrl+O to open a file.")
            return

        filename = Path(self.current_file).name
        status = " (modified)" if self.modified else ""
        sort_info = ""

        if self.sort_column >= 0 and self.sort_column < len(self.headers):
            direction = "Z-A" if self.sort_reverse else "A-Z"
            sort_info = f" | Sorted by {self.headers[self.sort_column]} ({direction})"

        info_text = f"File: {filename}{status} | {len(self.data)} entries{sort_info}"
        info_bar.update(info_text)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handle column header clicks for sorting."""
        column_index = int(event.column_key)

        if self.sort_column == column_index:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column_index
            self.sort_reverse = False

        self.sort_data()

    def sort_data(self) -> None:
        """Sort data by current sort column."""
        if self.sort_column < 0 or self.sort_column >= len(self.headers):
            return

        def sort_key(row):
            value = row[self.sort_column] if self.sort_column < len(row) else ""
            # Try to convert to number for numeric sorting
            try:
                return float(value)
            except (ValueError, TypeError):
                return value.lower()

        self.data.sort(key=sort_key, reverse=self.sort_reverse)
        self.update_table()
        self.update_info_bar()

    def add_entry(self, field1: str, field2: str) -> None:
        """Add new entry to the table."""
        new_row = [field1, field2]
        # Pad to match header count
        while len(new_row) < len(self.headers):
            new_row.append('')

        self.data.append(new_row)
        self.modified = True

        # Re-sort if we have an active sort
        if self.sort_column >= 0:
            self.sort_data()
        else:
            self.update_table()

        self.update_info_bar()

    def delete_entry(self, row_index: int) -> None:
        """Delete entry at given index."""
        if 0 <= row_index < len(self.data):
            del self.data[row_index]
            self.modified = True
            self.update_table()
            self.update_info_bar()

    def save_file(self) -> None:
        """Save current data back to markdown file."""
        if not self.current_file or not self.headers:
            return

        # Generate markdown
        markdown = '\n'

        # Headers
        markdown += '| ' + ' | '.join(self.headers) + ' |\n'

        # Separator
        separators = ['-' * max(3, len(h)) for h in self.headers]
        markdown += '| ' + ' | '.join(separators) + ' |\n'

        # Data rows - use original order for saving
        save_data = self.original_data[:]

        # Update original data with current data
        # This is a simple approach - in practice you might want more sophisticated merging
        self.original_data = [row[:] for row in self.data]

        for row in self.original_data:
            padded_row = row + [''] * (len(self.headers) - len(row))
            markdown += '| ' + ' | '.join(padded_row[:len(self.headers)]) + ' |\n'

        # Write file
        with open(self.current_file, 'w', encoding='utf-8') as f:
            f.write(markdown)

        self.modified = False
        self.update_info_bar()

    def watch_modified(self, modified: bool) -> None:
        """React to modification state changes."""
        self.update_info_bar()


def main():
    """Main entry point."""
    filename = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]

    app = MediaEditor(filename)
    app.run()


if __name__ == "__main__":
    main()