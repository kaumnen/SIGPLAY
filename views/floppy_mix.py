from __future__ import annotations

from textual.containers import Container, Vertical, Horizontal
from textual.reactive import reactive
from textual import events
from textual.app import ComposeResult
from textual.widgets import Label, Input, Button, Static, LoadingIndicator
from textual.screen import ModalScreen
from models.track import Track, format_time
from pathlib import Path
import logging
import shutil
import re

from widgets.track_selection_panel import TrackSelectionPanel
from widgets.instructions_panel import InstructionsPanel

logger = logging.getLogger(__name__)


class FloppyMixView(Container):
    """Full-screen view for Floppy Mix interface."""
    
    mixing_state: reactive[str] = reactive("idle")
    
    def __init__(self, audio_player, music_library, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio_player = audio_player
        self.music_library = music_library
        self._mix_file_path: str | None = None
        self._mix_statistics: dict | None = None
        
        self._track_panel: TrackSelectionPanel | None = None
        self._instructions_panel: InstructionsPanel | None = None
        self._loading_indicator: LoadingIndicator | None = None
        self._status_display: Static | None = None
        self._statistics_display: Static | None = None
        self._controls_container: Horizontal | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the view layout."""
        with Vertical(id="floppy-mix-container"):
            with Vertical(id="floppy-mix-header"):
                with Horizontal(id="floppy-mix-title-row"):
                    yield Label("💾 Floppy Mix", id="floppy-mix-title")
                    yield Button("🎵 Start Mix", id="start-mix-button", variant="primary")
                with Horizontal(id="floppy-mix-status-row"):
                    yield LoadingIndicator(id="progress-spinner")
                    yield Static("Select tracks (Space), add instructions (Tab to switch), then select Start Mix.", id="status-display")
                yield Static("", id="statistics-display")
                with Horizontal(id="floppy-mix-controls-row"):
                    yield Button("💾 Save Mix", id="save-button", variant="success")
                    yield Button("🗑️  Discard Mix", id="discard-button", variant="error")
            
            with Horizontal(id="floppy-mix-main-content"):
                yield TrackSelectionPanel([], id="track-panel")
                yield InstructionsPanel(id="instructions-panel")
    
    def on_mount(self) -> None:
        """Set up panel references on mount."""
        try:
            self._track_panel = self.query_one("#track-panel", TrackSelectionPanel)
            self._instructions_panel = self.query_one("#instructions-panel", InstructionsPanel)
            self._loading_indicator = self.query_one("#progress-spinner", LoadingIndicator)
            self._status_display = self.query_one("#status-display", Static)
            self._statistics_display = self.query_one("#statistics-display", Static)
            self._controls_container = self.query_one("#floppy-mix-controls-row", Horizontal)
            
            self._loading_indicator.display = False
            self._statistics_display.display = False
            self._controls_container.display = False
            
            logger.debug("Floppy Mix view panels mounted successfully")
        except Exception as e:
            logger.error(f"Error mounting view panels: {e}")
    
    def on_show(self) -> None:
        """Called when view becomes visible."""
        logger.debug("Showing Floppy Mix view")
        
        if self._track_panel:
            tracks = self.music_library.get_tracks()
            logger.debug(f"Loading {len(tracks)} tracks into Floppy Mix view")
            self._track_panel.refresh_tracks(tracks)
        
        self._update_status("Select tracks (Space), add instructions (Tab to switch), then select Start Mix.")
        
        self.call_after_refresh(self._set_initial_focus)
    
    def _set_initial_focus(self) -> None:
        """Set focus to track list after view is fully rendered."""
        try:
            track_list = self.query_one("#track-list")
            track_list.focus()
            logger.debug("Set initial focus to track list")
        except Exception as e:
            logger.error(f"Failed to set initial focus: {e}")
        
    def cleanup(self) -> None:
        """Cleanup resources when view is hidden."""
        logger.debug("Cleaning up Floppy Mix view")
        
        if self._mix_file_path and self.mixing_state == "previewing":
            logger.debug("Cleaning up mix preview")
            self._stop_preview_playback()
            self._delete_temp_mix_file()
        
        self.mixing_state = "idle"
        self._mix_file_path = None
        self._mix_statistics = None
        
        if self._track_panel:
            self._track_panel.clear_selection()
        self._hide_preview_controls()
        self._hide_statistics()
        self._update_status("Ready to mix")
    
    def _stop_preview_playback(self) -> None:
        """Stop playback of the mix preview."""
        current_track = self.audio_player.get_current_track()
        
        if current_track and self._mix_file_path:
            if current_track.file_path == self._mix_file_path:
                logger.debug("Stopping mix preview playback")
                self.audio_player.stop()
    
    def _delete_temp_mix_file(self) -> None:
        """Delete the temporary mix file if it exists."""
        if self._mix_file_path:
            try:
                mix_path = Path(self._mix_file_path)
                if mix_path.exists():
                    mix_path.unlink()
                    logger.debug(f"Deleted temporary mix file: {self._mix_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary mix file: {e}")
        
    def on_key(self, event: events.Key) -> None:
        """Handle keyboard events (Escape only - Space handled by global binding)."""
        if event.key == "escape":
            logger.debug("Escape key pressed, returning to main view")
            self.app.action_back_to_main()
            event.prevent_default()
            event.stop()
    
    def _toggle_preview_playback(self) -> None:
        """Toggle play/pause for the mix preview."""
        if self.audio_player.is_playing():
            self.audio_player.pause()
            logger.debug("Paused mix preview")
        else:
            self.audio_player.resume()
            logger.debug("Resumed mix preview")
        
    async def start_mixing(self) -> None:
        """Initiate the mixing process with selected tracks and instructions."""
        logger.info("Starting mixing process")
        
        if self.mixing_state != "idle":
            logger.warning("Cannot start mixing: already in progress")
            self.app.notify("Mix already in progress", severity="warning")
            return
        
        validation_error = self._validate_inputs()
        if validation_error:
            logger.warning(f"Validation failed: {validation_error}")
            self.app.notify(validation_error, severity="error", timeout=5)
            return
        
        self.mixing_state = "mixing"
        
        self._update_status("Preparing mix request...")
        self._show_loading()
        
        self.app.notify("🎵 Starting mix...", severity="information")
        
        try:
            from services.dj_agent_client import DJAgentClient
            
            selected_tracks = self._track_panel.get_selected_tracks()
            instructions = self._instructions_panel.get_instructions()
            
            logger.info(f"Creating mix with {len(selected_tracks)} tracks")
            
            client = DJAgentClient()
            
            def progress_update(status: str) -> None:
                """Update status display with agent status."""
                self._update_status(status)
            
            mix_file_path, statistics = await client.create_mix(
                tracks=selected_tracks,
                instructions=instructions,
                progress_callback=progress_update
            )
            
            self.on_mix_complete(mix_file_path, statistics)
            
        except Exception as e:
            logger.exception(f"Mix failed: {e}")
            self.on_mix_error(str(e))
        
    def _validate_inputs(self) -> str | None:
        """Validate user inputs before starting mix.
        
        Returns:
            Error message if validation fails, None if valid.
        """
        if not self._track_panel or not self._instructions_panel:
            return "View not properly initialized"
        
        selected_tracks = self._track_panel.get_selected_tracks()
        if not selected_tracks:
            return "❌ Please select at least one track to mix"
        
        if self._instructions_panel.is_empty():
            return "❌ Please enter mixing instructions"
        
        instructions = self._instructions_panel.get_instructions()
        logger.debug(f"Validation passed: {len(selected_tracks)} tracks, {len(instructions)} chars")
        return None
        
    def on_mix_complete(self, mix_file_path: str, statistics: dict) -> None:
        """Handle successful mix completion."""
        logger.info(f"Mix completed successfully: {mix_file_path}")
        logger.info(f"Statistics: {statistics}")
        self._mix_file_path = mix_file_path
        self._mix_statistics = statistics
        self.mixing_state = "previewing"
        
        self._hide_loading()
        self._update_status("✓ Mix complete! Playing preview...")
        self._show_statistics(statistics)
        self._show_preview_controls()
        
        self._start_preview_playback()
        
        self.call_after_refresh(self._focus_save_button)
    
    def _focus_save_button(self) -> None:
        """Focus the save button after mix completes."""
        try:
            save_button = self.query_one("#save-button", Button)
            save_button.focus()
            logger.debug("Focused save button after mix completion")
        except Exception as e:
            logger.error(f"Failed to focus save button: {e}")
    
    def _start_preview_playback(self) -> None:
        """Load and automatically play the generated mix file."""
        if not self._mix_file_path:
            logger.error("Cannot start preview: no mix file path")
            return
        
        try:
            mix_path = Path(self._mix_file_path)
            if not mix_path.exists():
                logger.error(f"Mix file not found: {self._mix_file_path}")
                self.app.notify("❌ Mix file not found", severity="error")
                return
            
            mix_track = Track(
                title="Floppy Mix Preview",
                artist="AI DJ",
                album="Generated Mix",
                duration=format_time(0),
                file_path=str(mix_path),
                duration_seconds=0
            )
            
            logger.info(f"Loading mix preview: {self._mix_file_path}")
            self.audio_player.play(mix_track)
            
            self.app.notify("🎵 Mix preview playing! Press Space to pause.", severity="information")
            
        except Exception as e:
            logger.error(f"Failed to start mix preview: {e}")
            self.app.notify(f"❌ Failed to play mix: {str(e)}", severity="error")
        
    def on_mix_error(self, error: str) -> None:
        """Handle mixing errors."""
        logger.error(f"Mix error: {error}")
        self.mixing_state = "idle"
        
        self._hide_loading()
        self._update_status(f"❌ Mix failed: {error}")
        
        self.app.notify(f"❌ Mix failed: {error}", severity="error", timeout=8)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "start-mix-button":
            logger.debug("Start mix button pressed")
            self.app.call_later(self.start_mixing)
            event.prevent_default()
            event.stop()
        elif event.button.id == "save-button":
            logger.info("Save mix requested")
            self._save_mix()
            event.prevent_default()
            event.stop()
        elif event.button.id == "discard-button":
            logger.info("Discard mix requested")
            self._discard_mix()
            event.prevent_default()
            event.stop()
    
    def _save_mix(self) -> None:
        """Save the generated mix to the Music Library directory."""
        if not self._mix_file_path:
            logger.error("Cannot save: no mix file path")
            self.app.notify("❌ No mix file to save", severity="error")
            return
        
        if self.mixing_state != "previewing":
            logger.error("Cannot save: not in preview state")
            self.app.notify("❌ No mix to save", severity="error")
            return
        
        self.app.push_screen(
            FilenamePromptScreen(),
            callback=self._handle_filename_input
        )
    
    def _handle_filename_input(self, filename: str | None) -> None:
        """Handle filename input from prompt screen."""
        if not filename:
            logger.debug("Save cancelled by user")
            return
        
        if not self._mix_file_path:
            logger.error("Mix file path lost during save")
            self.app.notify("❌ Mix file not found", severity="error")
            return
        
        validated_filename = self._validate_filename(filename)
        if not validated_filename:
            self.app.notify(
                "❌ Invalid filename. Please use only alphanumeric characters, spaces, hyphens, and underscores",
                severity="error",
                timeout=5
            )
            return
        
        if not validated_filename.endswith('.wav'):
            validated_filename += '.wav'
        
        try:
            music_dir = self.music_library.music_dir
            destination = music_dir / validated_filename
            
            if destination.exists():
                self.app.notify(
                    f"❌ File '{validated_filename}' already exists. Please choose a different name.",
                    severity="error",
                    timeout=5
                )
                return
            
            source = Path(self._mix_file_path)
            if not source.exists():
                logger.error(f"Source mix file not found: {self._mix_file_path}")
                self.app.notify("❌ Mix file not found", severity="error")
                return
            
            shutil.copy2(source, destination)
            logger.info(f"Mix saved successfully to: {destination}")
            
            self.app.notify(
                f"✓ Mix saved successfully!\n📁 {destination}",
                severity="information",
                timeout=5
            )
            
            self._stop_preview_playback()
            
            self._delete_temp_mix_file()
            
            self._mix_file_path = None
            self._mix_statistics = None
            self.mixing_state = "idle"
            
            if self._track_panel:
                self._track_panel.clear_selection()
            if self._instructions_panel:
                self._instructions_panel.clear()
            self._hide_preview_controls()
            self._hide_statistics()
            
            self.app.run_worker(self._refresh_library_after_save, exclusive=False)
            
            self.app.action_back_to_main()
            
        except PermissionError as e:
            logger.error(f"Permission denied saving mix: {e}")
            self.app.notify(
                f"❌ Cannot save mix: Permission denied\n\nPlease check directory permissions for {music_dir}",
                severity="error",
                timeout=8
            )
        except OSError as e:
            logger.error(f"OS error saving mix: {e}")
            self.app.notify(
                f"❌ Cannot save mix: {str(e)}\n\nPlease check disk space and permissions",
                severity="error",
                timeout=8
            )
        except Exception as e:
            logger.error(f"Unexpected error saving mix: {e}")
            self.app.notify(
                f"❌ Failed to save mix: {str(e)}",
                severity="error",
                timeout=8
            )
    
    def _validate_filename(self, filename: str) -> str | None:
        """Validate and sanitize filename.
        
        Args:
            filename: User-provided filename
            
        Returns:
            Sanitized filename or None if invalid
        """
        if not filename or not filename.strip():
            return None
        
        filename = filename.strip()
        
        if filename.endswith('.wav'):
            filename = filename[:-4]
        
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', filename):
            return None
        
        filename = re.sub(r'\s+', '_', filename)
        
        return filename
    
    async def _refresh_library_after_save(self) -> None:
        """Rescan music library and refresh both views after saving a mix."""
        try:
            logger.info("Rescanning music library after mix save")
            
            import asyncio
            tracks = await asyncio.to_thread(self.music_library.scan)
            
            library_view = self.app.query_one("#library")
            library_view.tracks = tracks
            library_view._populate_list()
            
            if self._track_panel:
                self._track_panel.refresh_tracks(tracks)
            
            logger.info(f"Library refreshed with {len(tracks)} tracks")
            
        except Exception as e:
            logger.error(f"Error refreshing library after save: {e}")
    
    def _discard_mix(self) -> None:
        """Discard the generated mix and reset view."""
        if not self._mix_file_path:
            logger.debug("No mix to discard")
            return
        
        if self.mixing_state != "previewing":
            logger.debug("Not in preview state, nothing to discard")
            return
        
        logger.info("Discarding mix")
        
        self._stop_preview_playback()
        
        self._delete_temp_mix_file()
        
        self.mixing_state = "idle"
        self._mix_file_path = None
        self._mix_statistics = None
        
        if self._track_panel:
            self._track_panel.clear_selection()
        if self._instructions_panel:
            self._instructions_panel.clear()
        self._hide_preview_controls()
        self._hide_statistics()
        self._update_status("Ready to mix")
        
        self.app.notify("Mix discarded", severity="information")
        logger.debug("Mix discarded and view reset")
    
    def _update_status(self, message: str) -> None:
        """Update the status message."""
        if self._status_display:
            self._status_display.update(message)
        logger.debug(f"Status updated: {message}")
    
    def _show_statistics(self, stats: dict) -> None:
        """Display mix statistics."""
        if not self._statistics_display:
            return
        
        time_str = f"{stats.get('time_seconds', 0):.1f}s"
        tokens_str = f"{stats.get('tokens_used', 0):,}" if stats.get('tokens_used', 0) > 0 else "N/A"
        tool_calls_str = str(stats.get('tool_calls', 0))
        file_size_str = f"{stats.get('file_size_mb', 0):.1f}MB"
        
        stats_text = (
            f"⏱️  Time: {time_str}  |  "
            f"🔧 Tool Calls: {tool_calls_str}  |  "
            f"🪙 Tokens: {tokens_str}  |  "
            f"💾 Size: {file_size_str}"
        )
        
        self._statistics_display.update(stats_text)
        self._statistics_display.display = True
        logger.debug(f"Statistics displayed: {stats}")
    
    def _show_preview_controls(self) -> None:
        """Display save/discard buttons."""
        if self._controls_container:
            self._controls_container.display = True
        if self._loading_indicator:
            self._loading_indicator.display = False
        logger.debug("Showing preview controls")
    
    def _hide_preview_controls(self) -> None:
        """Hide save/discard buttons."""
        if self._controls_container:
            self._controls_container.display = False
        logger.debug("Hiding preview controls")
    
    def _hide_statistics(self) -> None:
        """Hide statistics display."""
        if self._statistics_display:
            self._statistics_display.display = False
            self._statistics_display.update("")
    
    def _show_loading(self) -> None:
        """Show loading indicator."""
        if self._loading_indicator:
            self._loading_indicator.display = True
    
    def _hide_loading(self) -> None:
        """Hide loading indicator."""
        if self._loading_indicator:
            self._loading_indicator.display = False


class FilenamePromptScreen(ModalScreen[str | None]):
    """Modal screen to prompt user for filename."""
    
    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the filename prompt."""
        with Container(id="filename-prompt-container"):
            yield Label("💾 Save Mix", id="filename-prompt-title")
            yield Label("Enter a name for your mix:", id="filename-prompt-label")
            yield Input(
                value="",
                placeholder="my_awesome_mix",
                id="filename-input",
                disabled=False
            )
            with Horizontal(id="filename-prompt-buttons"):
                yield Button("Save", id="save-confirm-button", variant="success")
                yield Button("Cancel", id="cancel-button", variant="default")
    
    def on_mount(self) -> None:
        """Focus input on mount."""
        self.call_after_refresh(self._focus_input)
    
    def _focus_input(self) -> None:
        """Focus the input after screen is fully rendered."""
        input_widget = self.query_one("#filename-input", Input)
        input_widget.focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-confirm-button":
            input_widget = self.query_one("#filename-input", Input)
            filename = input_widget.value.strip()
            self.dismiss(filename if filename else None)
        elif event.button.id == "cancel-button":
            self.dismiss(None)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        filename = event.value.strip()
        self.dismiss(filename if filename else None)
