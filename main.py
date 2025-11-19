from textual.app import App, ComposeResult
from textual.widgets import Footer, ContentSwitcher, Label, Input, Button
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from textual.screen import ModalScreen
import asyncio
import logging
import os
from pathlib import Path

from widgets import Header, HelpScreen
from views import LibraryView, NowPlayingView, MetersView, FloppyMixView
from services.audio_player import AudioPlayer
from services.music_library import MusicLibrary


class MainViewContainer(Vertical):
    """Container for the main view."""
    
    def __init__(self, music_library, audio_player, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.music_library = music_library
        self.audio_player = audio_player
    
    def compose(self) -> ComposeResult:
        """Compose the main view layout."""
        with Horizontal(id="top-container"):
            yield LibraryView(self.music_library, self.audio_player, id="library")
            yield NowPlayingView(self.audio_player, id="now_playing")
        
        yield MetersView(self.audio_player, id="meters")

TRACK_END_CHECK_INTERVAL = 0.5

log_dir = Path.home() / '.local' / 'share' / 'sigplay'
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / 'sigplay.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file)
    ]
)

logger = logging.getLogger(__name__)


class SigplayApp(App):
    """A retro-modern terminal music player built with Textual."""
    
    CSS_PATH = "styles/app.tcss"
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("space", "play_pause", "Play/Pause"),
        Binding("s", "stop", "Stop", priority=True),
        Binding("n", "next_track", "Next", priority=True),
        Binding("p", "previous_track", "Prev", priority=True),
        Binding("+", "volume_up", "Vol+", priority=True),
        Binding("=", "volume_up", "Vol+", show=False, priority=True),
        Binding("-", "volume_down", "Vol-", priority=True),
        Binding("m", "toggle_mute", "Mute", priority=True),
        Binding("f", "show_floppy_mix", "Floppy Mix Page", priority=True),
        Binding("d", "back_to_main", "Default Page", priority=True),
        Binding("h", "show_help", "Help", priority=True),
        Binding("?", "show_help", "Help", show=False, priority=True),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        logger.info("Starting SIGPLAY application")
        
        try:
            self.audio_player = AudioPlayer()
        except RuntimeError as e:
            logger.critical(f"Failed to initialize audio player: {e}")
            raise
        
        self.music_library = MusicLibrary()
        self._session_openrouter_key: str | None = None
        logger.info("Services initialized successfully")
    
    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield Header()
        
        with ContentSwitcher(id="view-switcher", initial="main-view"):
            yield MainViewContainer(self.music_library, self.audio_player, id="main-view")
            yield FloppyMixView(self.audio_player, self.music_library, id="floppy-mix-view")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application."""
        library_view = self.query_one("#library", LibraryView)
        library_view.focus()
        
        header = self.query_one(Header)
        header.volume_level = int(self.audio_player.get_volume() * 100)
        header.is_muted = self.audio_player.is_muted()
        
        self.run_worker(self._scan_library, exclusive=True)
        self.set_interval(TRACK_END_CHECK_INTERVAL, self._check_track_end)
    
    async def _scan_library(self) -> None:
        """Scan music library in background thread.
        
        Displays user-friendly error messages if scanning fails.
        """
        try:
            logger.info("Starting music library scan")
            tracks = await asyncio.to_thread(self.music_library.scan)
            
            library_view = self.query_one("#library", LibraryView)
            library_view.tracks = tracks
            library_view._populate_list()
            
            if len(tracks) == 0:
                self.notify(
                    "No music files found in ~/Music\n\nAdd some audio files to get started!",
                    severity="warning",
                    timeout=8
                )
            else:
                self.notify(
                    f"✓ Loaded {len(tracks)} tracks",
                    severity="information",
                    timeout=3
                )
                
        except FileNotFoundError as e:
            logger.error(f"Music directory not found: {e}")
            self.notify(
                "❌ Music directory not found\n\n"
                "Please create ~/Music and add some audio files.",
                severity="error",
                timeout=10
            )
            library_view = self.query_one("#library", LibraryView)
            library_view.tracks = []
            library_view._populate_list()
            
        except PermissionError as e:
            logger.error(f"Permission denied accessing music directory: {e}")
            self.notify(
                "❌ Cannot access music directory\n\n"
                "Please check directory permissions for ~/Music",
                severity="error",
                timeout=10
            )
            library_view = self.query_one("#library", LibraryView)
            library_view.tracks = []
            library_view._populate_list()
            
        except Exception as e:
            logger.error(f"Unexpected error during library scan: {type(e).__name__}: {e}")
            self.notify(
                f"❌ Error scanning music library\n\n{type(e).__name__}: {str(e)[:50]}",
                severity="error",
                timeout=10
            )
            library_view = self.query_one("#library", LibraryView)
            library_view.tracks = []
            library_view._populate_list()
    
    def _check_track_end(self) -> None:
        """Check if track has ended and advance to next.
        
        Handles errors during auto-advance gracefully.
        """
        try:
            if self.audio_player.track_ended_naturally():
                current_track = self.audio_player.get_current_track()
                
                if current_track and current_track.title == "Floppy Mix Preview":
                    logger.debug("Mix preview ended, not auto-advancing")
                    return
                
                logger.debug("Track ended naturally, advancing to next")
                self.audio_player.next_track()
                library_view = self.query_one("#library", LibraryView)
                library_view._update_play_indicator()
        except Exception as e:
            logger.error(f"Error during track auto-advance: {e}")
            self.notify(
                "❌ Error advancing to next track",
                severity="error",
                timeout=3
            )
    
    def action_quit(self) -> None:
        """Handle quit action for clean shutdown."""
        self.exit()
    
    def action_play_pause(self) -> None:
        """Toggle play/pause state.
        
        In Floppy Mix view, this only works during preview playback.
        During track selection, space is handled by TrackSelectionPanel.
        """
        try:
            switcher = self.query_one("#view-switcher", ContentSwitcher)
            
            if switcher.current == "floppy-mix-view":
                floppy_mix_view = self.query_one("#floppy-mix-view", FloppyMixView)
                if floppy_mix_view.mixing_state == "previewing":
                    if self.audio_player.is_playing():
                        self.audio_player.pause()
                    else:
                        self.audio_player.resume()
                return
            
            if self.audio_player.is_playing():
                self.audio_player.pause()
            else:
                self.audio_player.resume()
        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
    
    def action_stop(self) -> None:
        """Stop playback."""
        self.audio_player.stop()
    
    def action_next_track(self) -> None:
        """Skip to next track.
        
        Displays error notification if track cannot be played.
        """
        try:
            self.audio_player.next_track()
            library_view = self.query_one("#library", LibraryView)
            library_view._update_play_indicator()
        except Exception as e:
            logger.error(f"Error skipping to next track: {e}")
            self.notify(
                "❌ Cannot play next track",
                severity="error",
                timeout=3
            )
    
    def action_previous_track(self) -> None:
        """Skip to previous track.
        
        Displays error notification if track cannot be played.
        """
        try:
            self.audio_player.previous_track()
            library_view = self.query_one("#library", LibraryView)
            library_view._update_play_indicator()
        except Exception as e:
            logger.error(f"Error skipping to previous track: {e}")
            self.notify(
                "❌ Cannot play previous track",
                severity="error",
                timeout=3
            )
    
    def action_volume_up(self) -> None:
        """Increase volume."""
        self.audio_player.increase_volume()
        volume_pct = int(self.audio_player.get_volume() * 100)
        self.notify(f"🔊 Volume ▲ {volume_pct}%", timeout=1.5)
        
        header = self.query_one(Header)
        header.volume_level = volume_pct
        header.is_muted = self.audio_player.is_muted()
        
        now_playing = self.query_one("#now_playing", NowPlayingView)
        now_playing._update_progress()
    
    def action_volume_down(self) -> None:
        """Decrease volume."""
        self.audio_player.decrease_volume()
        volume_pct = int(self.audio_player.get_volume() * 100)
        mute_icon = "🔇" if volume_pct == 0 else "🔉"
        self.notify(f"{mute_icon} Volume ▼ {volume_pct}%", timeout=1.5)
        
        header = self.query_one(Header)
        header.volume_level = volume_pct
        header.is_muted = self.audio_player.is_muted()
        
        now_playing = self.query_one("#now_playing", NowPlayingView)
        now_playing._update_progress()
    
    def action_toggle_mute(self) -> None:
        """Toggle mute state."""
        self.audio_player.toggle_mute()
        
        header = self.query_one(Header)
        header.is_muted = self.audio_player.is_muted()
        
        if self.audio_player.is_muted():
            self.notify("🔇 Muted", timeout=1.5)
        else:
            volume_pct = int(self.audio_player.get_volume() * 100)
            self.notify(f"🔊 Unmuted {volume_pct}%", timeout=1.5)
        
        now_playing = self.query_one("#now_playing", NowPlayingView)
        now_playing._update_progress()
    
    def action_show_floppy_mix(self) -> None:
        """Show the Floppy Mix view."""
        try:
            if not self._check_openrouter_credentials():
                self.push_screen(
                    OpenRouterKeyPromptScreen(),
                    callback=self._handle_openrouter_key_input
                )
            else:
                self._show_floppy_mix_view()
        except Exception as e:
            logger.error(f"Error showing Floppy Mix view: {e}")
            self.notify("❌ Cannot open Floppy Mix view", severity="error")
    
    def _check_openrouter_credentials(self) -> bool:
        """Check if OpenRouter credentials are available.
        
        Returns:
            True if credentials are set (either in env or session), False otherwise.
        """
        if self._session_openrouter_key:
            return True
        
        return bool(os.environ.get('OPENROUTER_API_KEY'))
    
    def _handle_openrouter_key_input(self, result: tuple[str, str] | None) -> None:
        """Handle API key and model ID input from prompt screen.
        
        Args:
            result: Tuple of (api_key, model_id) entered by user, or None if cancelled.
        """
        if not result:
            logger.debug("OpenRouter configuration prompt cancelled by user")
            self.notify("Floppy Mix requires OpenRouter API key", severity="information")
            return
        
        api_key, model_id = result
        
        self._session_openrouter_key = api_key
        os.environ['OPENROUTER_API_KEY'] = api_key
        os.environ['SIGPLAY_MIX_MODEL_ID'] = model_id
        logger.info(f"Session OpenRouter credentials set: model={model_id}")
        
        self.notify("✓ Configuration set for this session", severity="information", timeout=2)
        self._show_floppy_mix_view()
    
    def _show_floppy_mix_view(self) -> None:
        """Show the Floppy Mix view after credentials are validated."""
        try:
            switcher = self.query_one("#view-switcher", ContentSwitcher)
            switcher.current = "floppy-mix-view"
            
            floppy_mix_view = self.query_one("#floppy-mix-view", FloppyMixView)
            floppy_mix_view.on_show()
        except Exception as e:
            logger.error(f"Error showing Floppy Mix view: {e}")
            self.notify("❌ Cannot open Floppy Mix view", severity="error")
    
    def action_back_to_main(self) -> None:
        """Return to main view from Floppy Mix."""
        try:
            switcher = self.query_one("#view-switcher", ContentSwitcher)
            
            if switcher.current == "floppy-mix-view":
                floppy_mix_view = self.query_one("#floppy-mix-view", FloppyMixView)
                floppy_mix_view.cleanup()
                
                switcher.current = "main-view"
                
                library_view = self.query_one("#library", LibraryView)
                library_view.focus()
        except Exception as e:
            logger.error(f"Error returning to main view: {e}")
    
    def action_show_help(self) -> None:
        """Show help screen based on current view."""
        try:
            switcher = self.query_one("#view-switcher", ContentSwitcher)
            view_type = "floppy_mix" if switcher.current == "floppy-mix-view" else "main"
            self.push_screen(HelpScreen(view_type=view_type))
        except Exception as e:
            logger.error(f"Error showing help screen: {e}")
            self.notify("❌ Cannot show help", severity="error")


class OpenRouterKeyPromptScreen(ModalScreen[tuple[str, str] | None]):
    """Modal screen to prompt user for OpenRouter API key and model ID."""
    
    def compose(self) -> ComposeResult:
        """Compose the API key prompt."""
        with Container(id="openrouter-key-prompt-container"):
            yield Label("🔑 OpenRouter Configuration", id="openrouter-key-prompt-title")
            yield Label(
                "Floppy Mix uses OpenRouter for AI DJ mixing.\nEnter your API key for this session:",
                id="openrouter-key-prompt-label"
            )
            yield Input(
                value="",
                placeholder="Paste your API key here",
                id="openrouter-key-input",
                disabled=False
            )
            yield Label(
                "Model ID (optional):",
                id="openrouter-model-label"
            )
            yield Input(
                value="anthropic/claude-haiku-4.5",
                placeholder="anthropic/claude-haiku-4.5",
                id="openrouter-model-input",
                disabled=False
            )
            yield Label(
                "💡 To generate an API key:\n"
                "1. Go to https://openrouter.ai/keys\n"
                "2. Sign in or create an account\n"
                "3. Generate a new API key\n\n"
                "💡 You can also set these environment variables:\n"
                "   OPENROUTER_API_KEY\n"
                "   SIGPLAY_MIX_MODEL_ID",
                id="openrouter-key-help-text"
            )
            with Horizontal(id="openrouter-key-prompt-buttons"):
                yield Button("Continue", id="openrouter-key-confirm-button", variant="success")
                yield Button("Cancel", id="openrouter-key-cancel-button", variant="default")
    
    def on_mount(self) -> None:
        """Focus input on mount."""
        self.call_after_refresh(self._focus_input)
    
    def _focus_input(self) -> None:
        """Set focus to input after screen is fully rendered."""
        try:
            input_widget = self.query_one("#openrouter-key-input", Input)
            input_widget.focus()
            logger.debug("OpenRouter key input focused")
        except Exception as e:
            logger.error(f"Failed to focus input: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "openrouter-key-confirm-button":
            api_key_input = self.query_one("#openrouter-key-input", Input)
            model_input = self.query_one("#openrouter-model-input", Input)
            
            api_key = api_key_input.value.strip()
            model_id = model_input.value.strip()
            
            if api_key:
                self.dismiss((api_key, model_id if model_id else "anthropic/claude-haiku-4.5"))
            else:
                self.dismiss(None)
        elif event.button.id == "openrouter-key-cancel-button":
            self.dismiss(None)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        if event.input.id == "openrouter-key-input":
            model_input = self.query_one("#openrouter-model-input", Input)
            model_input.focus()
        elif event.input.id == "openrouter-model-input":
            api_key_input = self.query_one("#openrouter-key-input", Input)
            model_input = self.query_one("#openrouter-model-input", Input)
            
            api_key = api_key_input.value.strip()
            model_id = model_input.value.strip()
            
            if api_key:
                self.dismiss((api_key, model_id if model_id else "anthropic/claude-haiku-4.5"))
            else:
                self.dismiss(None)


def main():
    """Entry point for the SIGPLAY application.
    
    Handles initialization errors and provides user-friendly error messages.
    """
    try:
        logger.info("=" * 60)
        logger.info("SIGPLAY starting up")
        logger.info("=" * 60)
        
        app = SigplayApp()
        app.run()
        
        logger.info("SIGPLAY shut down cleanly")
        
    except RuntimeError as e:
        logger.critical(f"Fatal error during startup: {e}")
        print("\n❌ SIGPLAY cannot start\n")
        print(f"{e}\n")
        print(f"Check {log_file} for more details.\n")
        exit(1)
    except KeyboardInterrupt:
        logger.info("SIGPLAY interrupted by user")
        print("\n\nGoodbye! 👋\n")
        exit(0)
    except Exception as e:
        logger.critical(f"Unexpected fatal error: {type(e).__name__}: {e}", exc_info=True)
        print("\n❌ SIGPLAY encountered an unexpected error\n")
        print(f"{type(e).__name__}: {e}\n")
        print(f"Check {log_file} for more details.\n")
        exit(1)


if __name__ == "__main__":
    main()
