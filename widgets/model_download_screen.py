from __future__ import annotations

import logging
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, LoadingIndicator, Static

logger = logging.getLogger(__name__)


class ModelDownloadScreen(ModalScreen[bool]):
    """Modal screen showing model download progress."""

    def __init__(self, model_name: str, model_description: str) -> None:
        """Initialize download screen.

        Args:
            model_name: Name of the model being downloaded.
            model_description: Human-readable description of the model.
        """
        super().__init__()
        self.model_name = model_name
        self.model_description = model_description
        self.download_complete = False

    def compose(self) -> ComposeResult:
        """Compose the download screen."""
        with Container(id="model-download-container"):
            yield Label("⬇ Downloading Whisper Model", id="model-download-title")
            yield Static(
                f"Model: {self.model_description}\n\n"
                "This may take a few minutes depending on your connection.\n"
                "Please wait...",
                id="model-download-info",
            )
            yield LoadingIndicator(id="model-download-loading")
            yield Static("Initializing download...", id="model-download-status")
            yield Button(
                "Cancel", id="model-download-cancel", variant="default", disabled=False
            )

    def on_mount(self) -> None:
        """Start download on mount."""
        loading = self.query_one("#model-download-loading", LoadingIndicator)
        loading.display = True

    def update_progress(self, message: str) -> None:
        """Update progress message.

        Args:
            message: Progress message to display.
        """
        try:
            status = self.query_one("#model-download-status", Static)
            status.update(message)

            if message.startswith("✓"):
                self.download_complete = True
                loading = self.query_one("#model-download-loading", LoadingIndicator)
                loading.display = False

                cancel_btn = self.query_one("#model-download-cancel", Button)
                cancel_btn.label = "Continue"
                cancel_btn.variant = "success"

        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "model-download-cancel":
            if self.download_complete:
                self.dismiss(True)
            else:
                self.dismiss(False)
