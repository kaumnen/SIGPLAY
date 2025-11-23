from __future__ import annotations

import logging
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static, ListView, ListItem, Label, LoadingIndicator
from textual.timer import Timer

from models.track import Track
from models.lyrics import LyricSegment
from services.audio_player import AudioPlayer
from services.music_library import MusicLibrary
from services.lyrics_service import LyricsService

logger = logging.getLogger(__name__)


class LyricsView(Container):
    """Full-screen view displaying track library and synchronized lyrics."""
    
    current_track: reactive[Track | None] = reactive(None)
    lyrics: reactive[list[LyricSegment]] = reactive([])
    active_segment_index: reactive[int] = reactive(-1)
    is_loading: reactive[bool] = reactive(False)
    status_message: reactive[str] = reactive("")
    
    def __init__(
        self,
        music_library: MusicLibrary,
        audio_player: AudioPlayer,
        lyrics_service: LyricsService,
        **kwargs
    ) -> None:
        """Initialize LyricsView with required dependencies.
        
        Args:
            music_library: MusicLibrary service for accessing tracks.
            audio_player: AudioPlayer service for playback control.
            lyrics_service: LyricsService for lyrics generation and caching.
        """
        super().__init__(**kwargs)
        self._music_library = music_library
        self._audio_player = audio_player
        self._lyrics_service = lyrics_service
        self._update_timer: Timer | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the lyrics view layout."""
        with Horizontal(id="lyrics-container"):
            with Container(id="lyrics-library-panel"):
                yield Static("🎵 Track Library", id="lyrics-library-title")
                yield ListView(id="lyrics-track-list")
            
            with Container(id="lyrics-display-panel"):
                yield Static("📝 Lyrics", id="lyrics-panel-title")
                yield LoadingIndicator(id="lyrics-loading")
                yield Static("", id="lyrics-status")
                with VerticalScroll(id="lyrics-scroll"):
                    yield Container(id="lyrics-content")
    
    def on_mount(self) -> None:
        """Initialize view on mount."""
        self._refresh_track_list()
        self._update_timer = self.set_interval(0.5, self._update_active_segment)
        loading_indicator = self.query_one("#lyrics-loading", LoadingIndicator)
        loading_indicator.display = False
    
    def on_show(self) -> None:
        """Called when view becomes visible."""
        self._refresh_track_list()
        if self.current_track:
            self._load_lyrics_for_track(self.current_track)
    
    def _refresh_track_list(self) -> None:
        """Populate track list from music library."""
        track_list = self.query_one("#lyrics-track-list", ListView)
        track_list.clear()
        
        tracks = self._music_library.get_tracks()
        
        if not tracks:
            item = ListItem(Label("No music files found"))
            track_list.append(item)
            return
        
        for track in tracks:
            label_text = f"{track.title} - {track.artist or 'Unknown'}"
            item = ListItem(Label(label_text))
            item.track = track
            track_list.append(item)
    
    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle track selection."""
        if hasattr(event.item, 'track'):
            track = event.item.track
            self.current_track = track
            
            self._audio_player.play(track)
            
            await self._load_lyrics_for_track(track)
    
    async def _load_lyrics_for_track(self, track: Track) -> None:
        """Load or generate lyrics for the selected track."""
        pass
    
    def _update_active_segment(self) -> None:
        """Update active segment based on playback position."""
        pass
