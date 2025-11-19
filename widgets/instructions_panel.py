from __future__ import annotations

from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import TextArea, Label
from textual.app import ComposeResult
import logging

logger = logging.getLogger(__name__)

PLACEHOLDER_TEXT = """Enter your mixing instructions here...

Examples:
• more bass in songs, all in 180 bpm rhythm with gapless play
• smooth transitions between tracks with fade effects
• boost treble and add reverb for ambient feel
• match tempo to 140 bpm and create seamless mix"""


class InstructionsPanel(Container):
    """Right panel for mixing instructions."""
    
    instructions: reactive[str] = reactive("", init=False)
    
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
            self._text_area.text = PLACEHOLDER_TEXT
            self._text_area.focus()
            logger.debug("Instructions panel mounted successfully")
        except Exception as e:
            logger.error(f"Error mounting instructions panel: {e}")
    
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes."""
        if self._text_area:
            text = self._text_area.text
            
            if text == PLACEHOLDER_TEXT:
                self.instructions = ""
            else:
                self.instructions = text
            
            logger.debug(f"Instructions updated: {len(self.instructions)} chars")
    
    def get_instructions(self) -> str:
        """Return current instructions text."""
        if self._text_area:
            text = self._text_area.text
            if text == PLACEHOLDER_TEXT:
                return ""
            return text.strip()
        return self.instructions.strip()
    
    def clear(self) -> None:
        """Clear the text input."""
        if self._text_area:
            self._text_area.text = PLACEHOLDER_TEXT
        self.instructions = ""
        logger.debug("Instructions cleared")
    
    def is_empty(self) -> bool:
        """Check if instructions are empty."""
        text = self.get_instructions()
        return not text or not text.strip()
