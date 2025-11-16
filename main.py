from textual.app import App, ComposeResult
from textual.widgets import Footer, ContentSwitcher
from textual.binding import Binding
import pygame
import asyncio

from widgets.header import Header
from views.library import LibraryView
from views.now_playing import NowPlayingView
from views.visualizer import VisualizerView
from models.track import ViewState
from services.audio_player import AudioPlayer
from services.music_library import MusicLibrary


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
        self.audio_player = AudioPlayer()
        self.music_library = MusicLibrary()
    
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
        self.set_interval(0.1, self._check_pygame_events)
    
    async def _scan_library(self) -> None:
        """Scan music library in background thread."""
        tracks = await asyncio.to_thread(self.music_library.scan)
        
        library_view = self.query_one("#library", LibraryView)
        library_view.tracks = tracks
        library_view._populate_list()
    
    def _check_pygame_events(self) -> None:
        """Check for pygame events, particularly track end events."""
        for event in pygame.event.get():
            if event.type == pygame.USEREVENT:
                self.audio_player.next_track()
    
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
        """Skip to next track."""
        self.audio_player.next_track()
    
    def action_previous_track(self) -> None:
        """Skip to previous track."""
        self.audio_player.previous_track()
    
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
    """Entry point for the SIGPLAY application."""
    try:
        app = SigplayApp()
        app.run()
    except RuntimeError as e:
        print("\n❌ SIGPLAY cannot start\n")
        print(f"{e}\n")
        exit(1)


if __name__ == "__main__":
    main()
