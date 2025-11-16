from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, ProgressBar
from services.audio_player import AudioPlayer


class NowPlayingView(Container):
    """Widget displaying currently playing track information."""

    DEFAULT_CSS = """
    NowPlayingView {
        align: center middle;
    }

    NowPlayingView Vertical {
        width: 80%;
        height: auto;
        align: center middle;
    }

    NowPlayingView .music-icon {
        text-align: center;
        color: #ff8c00;
        text-style: bold;
        margin-bottom: 1;
    }

    NowPlayingView .track-title {
        text-align: center;
        color: #ff8c00;
        text-style: bold;
        margin-bottom: 1;
    }

    NowPlayingView .track-metadata {
        text-align: center;
        color: #ffb347;
        margin-bottom: 1;
    }

    NowPlayingView .progress-container {
        width: 100%;
        margin-top: 2;
    }

    NowPlayingView ProgressBar {
        width: 100%;
    }

    NowPlayingView .time-display {
        text-align: center;
        color: #fff8dc;
        margin-top: 1;
    }

    NowPlayingView .volume-display {
        text-align: center;
        color: #ffb347;
        margin-top: 1;
    }

    NowPlayingView .state-display {
        text-align: center;
        color: #ff8c00;
        margin-top: 1;
    }
    """

    def __init__(self, audio_player: AudioPlayer, **kwargs):
        """Initialize NowPlayingView with audio player reference."""
        super().__init__(**kwargs)
        self.audio_player = audio_player
        self._update_timer = None

    def compose(self) -> ComposeResult:
        """Compose the now playing view with track info and progress bar."""
        with Vertical():
            yield Static("♪", classes="music-icon")
            yield Static("No track playing", id="np-title", classes="track-title")
            yield Static("Artist: Unknown", id="np-artist", classes="track-metadata")
            yield Static("Album: Unknown", id="np-album", classes="track-metadata")
            
            with Container(classes="progress-container"):
                yield ProgressBar(total=100, show_eta=False, id="np-progress")
                yield Static("0:00 / 0:00", id="np-time", classes="time-display")
                yield Static("Volume: 70%", id="np-volume", classes="volume-display")
                yield Static("State: Stopped", id="np-state", classes="state-display")

    def on_mount(self) -> None:
        """Start update timer for real-time progress updates."""
        self._update_timer = self.set_interval(1.0, self._update_progress)
        self._update_progress()
    
    def _update_progress(self) -> None:
        """Update all display widgets with current playback information."""
        current_track = self.audio_player.get_current_track()
        current_position = self.audio_player.get_position()
        volume_level = self.audio_player.get_volume()
        playback_state = self.audio_player.get_state()
        
        if current_track:
            title_widget = self.query_one("#np-title", Static)
            title_widget.update(current_track.title)
            
            artist_widget = self.query_one("#np-artist", Static)
            artist_widget.update(f"Artist: {current_track.artist}")
            
            album_widget = self.query_one("#np-album", Static)
            album_widget.update(f"Album: {current_track.album}")
            
            total_duration = current_track.duration_seconds
            
            current_time_str = self._format_time(current_position)
            total_time_str = self._format_time(total_duration)
            time_widget = self.query_one("#np-time", Static)
            time_widget.update(f"{current_time_str} / {total_time_str}")
            
            progress_bar = self.query_one("#np-progress", ProgressBar)
            if total_duration > 0:
                percentage = (current_position / total_duration) * 100
                percentage = min(100, max(0, percentage))
                progress_bar.update(progress=percentage)
            else:
                progress_bar.update(progress=0)
        else:
            title_widget = self.query_one("#np-title", Static)
            title_widget.update("No track playing")
            
            artist_widget = self.query_one("#np-artist", Static)
            artist_widget.update("Artist: Unknown")
            
            album_widget = self.query_one("#np-album", Static)
            album_widget.update("Album: Unknown")
            
            time_widget = self.query_one("#np-time", Static)
            time_widget.update("0:00 / 0:00")
            
            progress_bar = self.query_one("#np-progress", ProgressBar)
            progress_bar.update(progress=0)
        
        volume_widget = self.query_one("#np-volume", Static)
        volume_widget.update(f"Volume: {int(volume_level * 100)}%")
        
        state_widget = self.query_one("#np-state", Static)
        state_widget.update(f"State: {playback_state.value.capitalize()}")
    
    def _format_time(self, seconds: float) -> str:
        """Convert seconds to MM:SS format.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string in MM:SS format
        """
        if seconds < 0:
            seconds = 0
        
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
