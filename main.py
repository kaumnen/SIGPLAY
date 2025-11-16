from textual.app import App, ComposeResult
from textual.widgets import Footer, ContentSwitcher
from textual.binding import Binding
import pygame.mixer
import asyncio
import logging
import sys

from widgets.header import Header
from views.library import LibraryView
from views.now_playing import NowPlayingView
from views.visualizer import VisualizerView
from models.track import ViewState
from services.audio_player import AudioPlayer
from services.music_library import MusicLibrary

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sigplay.log'),
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)


class SigplayApp(App):
    """A retro-modern terminal music player built with Textual."""
    
    CSS_PATH = "styles/app.tcss"
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("tab", "cycle_view", "Switch View", priority=True),
        Binding("space", "play_pause", "Play/Pause"),
        Binding("s", "stop", "Stop"),
        Binding("n", "next_track", "Next"),
        Binding("p", "previous_track", "Prev"),
        Binding("+", "volume_up", "Vol+"),
        Binding("=", "volume_up", "Vol+", show=False),
        Binding("-", "volume_down", "Vol-"),
        Binding("o", "select_device", "Device"),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_view = ViewState.LIBRARY
        self.view_order = [ViewState.LIBRARY, ViewState.NOW_PLAYING, ViewState.VISUALIZER]
        
        logger.info("Starting SIGPLAY application")
        
        try:
            self.audio_player = AudioPlayer()
        except RuntimeError as e:
            logger.critical(f"Failed to initialize audio player: {e}")
            raise
        
        self.music_library = MusicLibrary()
        logger.info("Services initialized successfully")
    
    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield Header()
        
        with ContentSwitcher(initial="library"):
            yield LibraryView(self.music_library, self.audio_player, id="library")
            yield NowPlayingView(self.audio_player, id="now_playing")
            yield VisualizerView(id="visualizer")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application with the default view."""
        self.current_view = ViewState.LIBRARY
        switcher = self.query_one(ContentSwitcher)
        switcher.current = "library"
        self._update_footer()
        
        self.run_worker(self._scan_library, exclusive=True)
        self.set_interval(0.5, self._check_track_end)
    
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
            if self.audio_player.is_playing() and not pygame.mixer.music.get_busy():
                logger.debug("Track ended, advancing to next")
                self.audio_player.next_track()
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
    
    def action_cycle_view(self) -> None:
        """Cycle to the next view in sequence."""
        current_index = self.view_order.index(self.current_view)
        next_index = (current_index + 1) % len(self.view_order)
        self.current_view = self.view_order[next_index]
        
        switcher = self.query_one(ContentSwitcher)
        switcher.current = self.current_view.value
        
        self._update_footer()
    
    def action_play_pause(self) -> None:
        """Toggle play/pause state."""
        if self.audio_player.is_playing():
            self.audio_player.pause()
        else:
            self.audio_player.resume()
    
    def action_stop(self) -> None:
        """Stop playback."""
        self.audio_player.stop()
    
    def action_next_track(self) -> None:
        """Skip to next track.
        
        Displays error notification if track cannot be played.
        """
        try:
            self.audio_player.next_track()
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
    
    def action_volume_down(self) -> None:
        """Decrease volume."""
        self.audio_player.decrease_volume()
    
    def action_select_device(self) -> None:
        """Select audio output device (stub for future feature)."""
        self.notify("Audio device selection coming soon!", severity="information")
    
    def _update_footer(self) -> None:
        """Update footer to display current view and keyboard shortcuts."""
        view_names = {
            ViewState.LIBRARY: "Library",
            ViewState.NOW_PLAYING: "Now Playing",
            ViewState.VISUALIZER: "Visualizer"
        }
        
        current_view_name = view_names.get(self.current_view, "Unknown")
        self.sub_title = f"View: {current_view_name}"


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
        print("Check sigplay.log for more details.\n")
        exit(1)
    except KeyboardInterrupt:
        logger.info("SIGPLAY interrupted by user")
        print("\n\nGoodbye! 👋\n")
        exit(0)
    except Exception as e:
        logger.critical(f"Unexpected fatal error: {type(e).__name__}: {e}", exc_info=True)
        print("\n❌ SIGPLAY encountered an unexpected error\n")
        print(f"{type(e).__name__}: {e}\n")
        print("Check sigplay.log for more details.\n")
        exit(1)


if __name__ == "__main__":
    main()
