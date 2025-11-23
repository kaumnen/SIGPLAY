from __future__ import annotations

import logging
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static, ListView, LoadingIndicator

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
