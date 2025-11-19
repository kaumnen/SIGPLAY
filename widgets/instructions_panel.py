from __future__ import annotations

from textual.containers import Container, Vertical
from textual.widgets import TextArea, Label
from textual.app import ComposeResult
import logging

logger = logging.getLogger(__name__)


class InstructionsPanel(Container):
    """Right panel for mixing instructions."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._text_area: TextArea | None = None
    
    def compose(self) -> ComposeResult:
        """Yield TextArea widget."""
        with Vertical(id="instructions-container"):
            yield Label("Mixing Instructions (natural language)", id="instructions-label")
            yield TextArea(
                text="",
                language="markdown",
                id="instructions-input"
            )
    
    def on_mount(self) -> None:
        """Set up the text area on mount."""
        try:
            self._text_area = self.query_one("#instructions-input", TextArea)
            logger.debug("Instructions panel mounted successfully")
        except Exception as e:
            logger.error(f"Error mounting instructions panel: {e}")
    
    def get_instructions(self) -> str:
        """Return current instructions text."""
        if self._text_area:
            return self._text_area.text.strip()
        return ""
    
    def clear(self) -> None:
        """Clear the text input."""
        if self._text_area:
            self._text_area.text = ""
        logger.debug("Instructions cleared")
    
    def is_empty(self) -> bool:
        """Check if instructions are empty."""
        text = self.get_instructions()
        return not text or not text.strip()
