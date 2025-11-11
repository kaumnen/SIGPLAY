from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, ProgressBar


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
    """

    def compose(self) -> ComposeResult:
        """Compose the now playing view with track info and progress bar."""
        with Vertical():
            yield Static("♪", classes="music-icon")
            yield Static("Neon Dreams", classes="track-title")
            yield Static("Artist: Synthwave Collective", classes="track-metadata")
            yield Static("Album: Retro Future", classes="track-metadata")
            
            with Container(classes="progress-container"):
                yield ProgressBar(total=252, show_eta=False)
                yield Static("2:34 / 4:12", classes="time-display")

    def on_mount(self) -> None:
        """Initialize the progress bar with sample progress."""
        progress_bar = self.query_one(ProgressBar)
        progress_bar.update(progress=154)
