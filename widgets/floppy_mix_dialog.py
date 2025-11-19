from __future__ import annotations

from textual.containers import Container, Vertical, Horizontal
from textual.reactive import reactive
from textual import events
from textual.app import ComposeResult
from textual.widgets import Label, Input, Button
from textual.screen import ModalScreen
from models.mix_request import MixRequest
from models.track import Track
from pathlib import Path
import logging
import shutil
import re

from .track_selection_panel import TrackSelectionPanel
from .instructions_panel import InstructionsPanel
from .mix_progress_panel import MixProgressPanel

logger = logging.getLogger(__name__)


class FloppyMixDialog(Container):
    """Modal dialog for Floppy Mix interface."""
    
    is_visible: reactive[bool] = reactive(False)
    mixing_state: reactive[str] = reactive("idle")
    
    def __init__(self, audio_player, music_library, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio_player = audio_player
        self.music_library = music_library
        self._mix_file_path: str | None = None
        self._was_playing_before_dialog: bool = False
        self._previous_track = None
        
        self._track_panel: TrackSelectionPanel | None = None
        self._instructions_panel: InstructionsPanel | None = None
        self._progress_panel: MixProgressPanel | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the dialog layout."""
        with Vertical(id="dialog-container"):
            yield Label("💾 Floppy Mix", id="dialog-title")
            
            with Horizontal(id="dialog-main-content"):
                tracks = self.music_library.get_tracks()
                yield TrackSelectionPanel(tracks, id="track-panel")
                yield InstructionsPanel(id="instructions-panel")
            
            yield MixProgressPanel(id="progress-panel")
    
    def on_mount(self) -> None:
        """Set up panel references on mount."""
        try:
            self._track_panel = self.query_one("#track-panel", TrackSelectionPanel)
            self._instructions_panel = self.query_one("#instructions-panel", InstructionsPanel)
            self._progress_panel = self.query_one("#progress-panel", MixProgressPanel)
            logger.debug("Dialog panels mounted successfully")
        except Exception as e:
            logger.error(f"Error mounting dialog panels: {e}")
    
    def show(self) -> None:
        """Display the dialog as modal overlay."""
        logger.debug("Showing Floppy Mix dialog")
        
        self._was_playing_before_dialog = self.audio_player.is_playing()
        self._previous_track = self.audio_player.get_current_track()
        
        self.is_visible = True
        self.display = True
        
        if self._instructions_panel:
            self._instructions_panel.focus()
        
    def hide(self) -> None:
        """Close the dialog and cleanup."""
        logger.debug("Hiding Floppy Mix dialog")
        self.is_visible = False
        self.display = False
        self._cleanup()
        
    def _cleanup(self) -> None:
        """Cleanup resources when dialog closes."""
        if self._mix_file_path and self.mixing_state == "previewing":
            logger.debug("Cleaning up mix preview")
            self._stop_preview_playback()
            self._delete_temp_mix_file()
        
        self.mixing_state = "idle"
        self._mix_file_path = None
        
        if self._track_panel:
            self._track_panel.clear_selection()
        if self._instructions_panel:
            self._instructions_panel.clear()
        if self._progress_panel:
            self._progress_panel.hide_preview_controls()
            self._progress_panel.update_status("Ready to mix")
    
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
        """Handle keyboard events (Escape, Enter, Space)."""
        if event.key == "escape":
            logger.debug("Escape key pressed, closing dialog")
            self.hide()
            event.prevent_default()
            event.stop()
        elif event.key == "enter" and self.mixing_state == "idle":
            logger.debug("Enter key pressed, starting mix")
            self.app.call_later(self.start_mixing)
            event.prevent_default()
            event.stop()
        elif event.key == "space" and self.mixing_state == "previewing":
            logger.debug("Space key pressed during preview, toggling playback")
            self._toggle_preview_playback()
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
        
        if self._progress_panel:
            self._progress_panel.update_status("Validating mix request...")
            self._progress_panel.show_loading()
        
        self.app.notify("Mix started! Agent integration coming in task 4.", severity="information")
        
    def _validate_inputs(self) -> str | None:
        """Validate user inputs before starting mix.
        
        Returns:
            Error message if validation fails, None if valid.
        """
        if not self._track_panel or not self._instructions_panel:
            return "Dialog not properly initialized"
        
        selected_tracks = self._track_panel.get_selected_tracks()
        if not selected_tracks:
            return "❌ Please select at least one track to mix"
        
        instructions = self._instructions_panel.get_instructions()
        if not instructions or not instructions.strip():
            return "❌ Please provide mixing instructions"
        
        logger.debug(f"Validation passed: {len(selected_tracks)} tracks, {len(instructions)} chars")
        return None
    
    def _create_mix_request(self) -> MixRequest | None:
        """Create a MixRequest from current dialog state.
        
        Returns:
            MixRequest object or None if validation fails.
        """
        if not self._track_panel or not self._instructions_panel:
            return None
        
        selected_tracks = self._track_panel.get_selected_tracks()
        instructions = self._instructions_panel.get_instructions()
        
        tracks_data = [
            {
                'path': track.file_path,
                'title': track.title,
                'artist': track.artist,
                'duration': track.duration_seconds
            }
            for track in selected_tracks
        ]
        
        import tempfile
        output_dir = tempfile.gettempdir()
        
        mix_request = MixRequest(
            tracks=tracks_data,
            instructions=instructions,
            output_dir=output_dir
        )
        
        is_valid, error = mix_request.validate()
        if not is_valid:
            logger.error(f"Mix request validation failed: {error}")
            return None
        
        return mix_request
        
    def on_mix_complete(self, mix_file_path: str) -> None:
        """Handle successful mix completion."""
        logger.info(f"Mix completed successfully: {mix_file_path}")
        self._mix_file_path = mix_file_path
        self.mixing_state = "previewing"
        
        if self._progress_panel:
            self._progress_panel.hide_loading()
            self._progress_panel.update_status("✓ Mix complete! Playing preview...")
            self._progress_panel.show_preview_controls()
        
        self._start_preview_playback()
    
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
                duration=Track._format_duration(0),
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
        
        if self._progress_panel:
            self._progress_panel.hide_loading()
            self._progress_panel.update_status(f"❌ Mix failed: {error}")
        
        self.app.notify(f"❌ Mix failed: {error}", severity="error", timeout=8)
    
    def on_mix_progress_panel_save_requested(self, event: MixProgressPanel.SaveRequested) -> None:
        """Handle save button press."""
        logger.info("Save mix requested")
        self._save_mix()
    
    def on_mix_progress_panel_discard_requested(self, event: MixProgressPanel.DiscardRequested) -> None:
        """Handle discard button press."""
        logger.info("Discard mix requested")
        self._discard_mix()
    
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
            
            self._mix_file_path = None
            self.hide()
            
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
    
    def _discard_mix(self) -> None:
        """Discard the generated mix and reset dialog."""
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
        
        if self._track_panel:
            self._track_panel.clear_selection()
        if self._instructions_panel:
            self._instructions_panel.clear()
        if self._progress_panel:
            self._progress_panel.hide_preview_controls()
            self._progress_panel.update_status("Ready to mix")
        
        self.app.notify("Mix discarded", severity="information")
        logger.debug("Mix discarded and dialog reset")
    
    def watch_is_visible(self, visible: bool) -> None:
        """React to visibility changes."""
        if visible:
            self.add_class("visible")
        else:
            self.remove_class("visible")


class FilenamePromptScreen(ModalScreen[str | None]):
    """Modal screen to prompt user for filename."""
    
    def compose(self) -> ComposeResult:
        """Compose the filename prompt."""
        with Container(id="filename-prompt-container"):
            yield Label("💾 Save Mix", id="filename-prompt-title")
            yield Label("Enter a name for your mix:", id="filename-prompt-label")
            yield Input(
                placeholder="my_awesome_mix",
                id="filename-input"
            )
            with Horizontal(id="filename-prompt-buttons"):
                yield Button("Save", id="save-confirm-button", variant="success")
                yield Button("Cancel", id="cancel-button", variant="default")
    
    def on_mount(self) -> None:
        """Focus input on mount."""
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
