from __future__ import annotations

import logging
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListView, ListItem, Static

logger = logging.getLogger(__name__)


class WhisperModelScreen(ModalScreen[str | None]):
    """Modal screen for selecting or downloading a Whisper model."""

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Cancel"),
        Binding("j", "move_down", "Move down", show=False),
        Binding("k", "move_up", "Move up", show=False),
    ]

    def __init__(
        self, downloaded_models: list[str], available_models: list[tuple[str, str]], device_info: str = "CPU - int8"
    ) -> None:
        """Initialize model selection screen.

        Args:
            downloaded_models: List of already downloaded model names.
            available_models: List of (model_name, description) tuples.
            device_info: Device and compute type information.
        """
        super().__init__()
        self.downloaded_models = downloaded_models
        self.available_models = available_models
        self.device_info = device_info

    def compose(self) -> ComposeResult:
        """Compose the model selection screen."""
        with Container(id="whisper-model-container"):
            yield Label("🎤 Whisper Model Selection", id="whisper-model-title")
            
            yield Static(
                f"🖥️  Device: {self.device_info}",
                id="whisper-device-info",
            )

            if self.downloaded_models:
                yield Static(
                    f"✓ Found {len(self.downloaded_models)} downloaded model(s)\n"
                    "Select a model to use for lyrics generation:",
                    id="whisper-model-info",
                )
            else:
                yield Static(
                    "No Whisper models found.\n"
                    "Select a model to download and use for lyrics generation:",
                    id="whisper-model-info",
                )

            with Vertical(id="whisper-model-list-container"):
                yield ListView(id="whisper-model-list")

            yield Static(
                "💡 Tip: Smaller models are faster but less accurate.\n"
                "   First-time use will download the model (~75 MB to 3 GB).",
                id="whisper-model-help",
            )

            with Container(id="whisper-model-buttons"):
                yield Button("Select", id="whisper-select-button", variant="success")
                yield Button("Cancel", id="whisper-cancel-button", variant="default")

    def on_mount(self) -> None:
        """Populate model list on mount."""
        self._populate_model_list()
        self.call_after_refresh(self._set_initial_focus)

    def _populate_model_list(self) -> None:
        """Populate the model list with available models."""
        model_list = self.query_one("#whisper-model-list", ListView)

        for model_name, description in self.available_models:
            is_downloaded = model_name in self.downloaded_models
            prefix = "✓ " if is_downloaded else "⬇ "
            label_text = f"{prefix}{description}"

            item = ListItem(Label(label_text))
            item.model_name = model_name
            model_list.append(item)

        if len(self.available_models) > 0:
            model_list.index = 0

    def _set_initial_focus(self) -> None:
        """Set focus to model list after screen is fully rendered."""
        try:
            model_list = self.query_one("#whisper-model-list", ListView)
            model_list.focus()
        except Exception as e:
            logger.error(f"Failed to focus model list: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "whisper-select-button":
            self._select_model()
        elif event.button.id == "whisper-cancel-button":
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle model selection via Enter key."""
        self._select_model()

    def _select_model(self) -> None:
        """Select the highlighted model."""
        model_list = self.query_one("#whisper-model-list", ListView)

        if model_list.index is not None:
            selected_item = model_list.highlighted_child
            if hasattr(selected_item, "model_name"):
                self.dismiss(selected_item.model_name)
        else:
            self.dismiss(None)

    def action_move_down(self) -> None:
        """Move selection down in the list (j key)."""
        model_list = self.query_one("#whisper-model-list", ListView)
        model_list.action_cursor_down()

    def action_move_up(self) -> None:
        """Move selection up in the list (k key)."""
        model_list = self.query_one("#whisper-model-list", ListView)
        model_list.action_cursor_up()
