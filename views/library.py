from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual.containers import Container
from models.track import Track


class LibraryView(Container):
    """Library view displaying a list of music tracks with vim navigation."""
    
    DEFAULT_CSS = """
    LibraryView {
        background: #1a1a1a;
        border: solid #ff8c00;
        padding: 1;
    }
    
    LibraryView > Label {
        color: #ff8c00;
        text-style: bold;
        padding: 0 0 1 0;
    }
    """
    
    BINDINGS = [
        ("j", "move_down", "Move down"),
        ("k", "move_up", "Move up"),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracks = self._generate_placeholder_tracks()
    
    def compose(self) -> ComposeResult:
        """Compose the library view with a list of tracks."""
        yield Label("🎵 Music Library")
        yield ListView(
            *[
                ListItem(Label(f"♪ {track.title} - {track.artist} ({track.album}) [{track.duration}]"))
                for track in self.tracks
            ],
            id="track-list"
        )
    
    def _generate_placeholder_tracks(self) -> list[Track]:
        """Generate placeholder track data for testing."""
        return [
            Track(
                title="Neon Dreams",
                artist="Synthwave Collective",
                album="Retro Future",
                duration="4:23"
            ),
            Track(
                title="Terminal Velocity",
                artist="Code Warriors",
                album="Digital Frontier",
                duration="3:45"
            ),
            Track(
                title="Pixel Paradise",
                artist="8-Bit Heroes",
                album="Arcade Nights",
                duration="5:12"
            ),
            Track(
                title="Cyber Sunset",
                artist="Neon Riders",
                album="Electric Dreams",
                duration="4:01"
            ),
            Track(
                title="Binary Love",
                artist="Data Romance",
                album="Algorithm Hearts",
                duration="3:33"
            ),
            Track(
                title="Quantum Leap",
                artist="Future Sound",
                album="Time Warp",
                duration="4:56"
            ),
            Track(
                title="Retro Wave",
                artist="Vintage Vibes",
                album="Nostalgia Trip",
                duration="3:28"
            ),
            Track(
                title="Digital Rain",
                artist="Matrix Minds",
                album="Code Green",
                duration="5:34"
            ),
        ]
    
    def action_move_down(self) -> None:
        """Move selection down in the list (j key)."""
        list_view = self.query_one("#track-list", ListView)
        list_view.action_cursor_down()
    
    def action_move_up(self) -> None:
        """Move selection up in the list (k key)."""
        list_view = self.query_one("#track-list", ListView)
        list_view.action_cursor_up()

