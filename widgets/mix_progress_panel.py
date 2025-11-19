from __future__ import annotations

from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static, Button, LoadingIndicator
from textual.app import ComposeResult
from textual.message import Message
import logging

logger = logging.getLogger(__name__)


class MixProgressPanel(Container):
    """Bottom panel for progress and controls."""
    
    status_message: reactive[str] = reactive("", init=False)
    show_controls: reactive[bool] = reactive(False, init=False)
    
    class SaveRequested(Message):
        """Message sent when save button is pressed."""
        pass
    
    class DiscardRequested(Message):
        """Message sent when discard button is pressed."""
        pass
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loading_indicator: LoadingIndicator | None = None
        self._status_display: Static | None = None
        self._controls_container: Container | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the progress panel layout."""
        with Vertical(id="progress-container"):
            with Horizontal(id="status-row"):
                yield LoadingIndicator(id="progress-spinner")
                yield Static("Ready to mix", id="status-display")
            
            with Horizontal(id="controls-row"):
                yield Button("💾 Save Mix", id="save-button", variant="success")
                yield Button("🗑️  Discard Mix", id="discard-button", variant="error")
    
    def on_mount(self) -> None:
        """Set up references on mount."""
        try:
            self._loading_indicator = self.query_one("#progress-spinner", LoadingIndicator)
            self._status_display = self.query_one("#status-display", Static)
            self._controls_container = self.query_one("#controls-row", Horizontal)
            
            self._loading_indicator.display = False
            self._controls_container.display = False
            
            logger.debug("Mix progress panel mounted successfully")
        except Exception as e:
            logger.error(f"Error mounting progress panel: {e}")
    
    def update_status(self, message: str) -> None:
        """Update the status message."""
        self.status_message = message
        if self._status_display:
            self._status_display.update(message)
        logger.debug(f"Status updated: {message}")
    
    def show_preview_controls(self) -> None:
        """Display save/discard buttons."""
        self.show_controls = True
        if self._controls_container:
            self._controls_container.display = True
        if self._loading_indicator:
            self._loading_indicator.display = False
        logger.debug("Showing preview controls")
    
    def hide_preview_controls(self) -> None:
        """Hide save/discard buttons."""
        self.show_controls = False
        if self._controls_container:
            self._controls_container.display = False
        logger.debug("Hiding preview controls")
    
    def show_loading(self) -> None:
        """Show loading indicator."""
        if self._loading_indicator:
            self._loading_indicator.display = True
    
    def hide_loading(self) -> None:
        """Hide loading indicator."""
        if self._loading_indicator:
            self._loading_indicator.display = False
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-button":
            logger.debug("Save button pressed")
            self.post_message(self.SaveRequested())
        elif event.button.id == "discard-button":
            logger.debug("Discard button pressed")
            self.post_message(self.DiscardRequested())
    
    def watch_status_message(self, message: str) -> None:
        """React to status message changes."""
        if self._status_display:
            self._status_display.update(message)
    
    def watch_show_controls(self, show: bool) -> None:
        """React to show_controls changes."""
        if self._controls_container:
            self._controls_container.display = show
