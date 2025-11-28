from __future__ import annotations

from textual.containers import Container, Vertical
from textual.widgets import TextArea, Label
from textual.app import ComposeResult
from textual import events
import logging

logger = logging.getLogger(__name__)


class InstructionsPanel(Container):
    """Right panel for mixing instructions."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._text_area: TextArea | None = None
    
    DEFAULT_PLACEHOLDER = """Enter your mixing instructions here...

Examples:
• "Smooth crossfades with bass boost and light reverb"
• "High energy mix with compression and punchy drums"
• "Chill vibes with warm filters and subtle delay"
• "Build tension with filter sweeps and rising energy"
"""
    
    def compose(self) -> ComposeResult:
        """Yield TextArea widget."""
        with Vertical(id="instructions-container"):
            yield Label("Floppy Mix Instructions", id="instructions-label")
            yield TextArea(
                text="",
                language="markdown",
                id="instructions-input"
            )
    
    def on_mount(self) -> None:
        """Set up the text area on mount."""
        try:
            self._text_area = self.query_one("#instructions-input", TextArea)
            self._show_placeholder()
            logger.debug("Instructions panel mounted successfully")
        except Exception as e:
            logger.error(f"Error mounting instructions panel: {e}")
    
    def _show_placeholder(self) -> None:
        """Show placeholder text in the text area."""
        if self._text_area and not self._text_area.text:
            self._text_area.text = self.DEFAULT_PLACEHOLDER
            self._text_area.add_class("placeholder")
    
    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        """Clear placeholder when text area gains focus."""
        if self._text_area and self._text_area.has_class("placeholder"):
            self._text_area.text = ""
            self._text_area.remove_class("placeholder")
    
    def get_instructions(self) -> str:
        """Return current instructions text, excluding placeholder."""
        if self._text_area:
            text = self._text_area.text.strip()
            if self._text_area.has_class("placeholder") or text == self.DEFAULT_PLACEHOLDER.strip():
                return ""
            return text
        return ""
    
    def clear(self) -> None:
        """Clear the text input and show placeholder."""
        if self._text_area:
            self._text_area.text = ""
            self._show_placeholder()
        logger.debug("Instructions cleared")
    
    def is_empty(self) -> bool:
        """Check if instructions are empty or just placeholder."""
        text = self.get_instructions()
        return not text
    
    def set_instructions(self, text: str) -> None:
        """Set instructions text programmatically."""
        if self._text_area:
            self._text_area.remove_class("placeholder")
            self._text_area.text = text
            logger.debug(f"Instructions set: {text[:50]}...")
