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
        """Load or generate lyrics for the selected track.
        
        Args:
            track: Track to load lyrics for.
        """
        self.is_loading = True
        self.lyrics = []
        self.active_segment_index = -1
        
        loading_indicator = self.query_one("#lyrics-loading", LoadingIndicator)
        status_label = self.query_one("#lyrics-status", Static)
        
        loading_indicator.display = True
        status_label.update("")
        
        try:
            def progress_callback(message: str) -> None:
                """Update status label from background thread."""
                self.call_from_thread(status_label.update, message)
            
            lyrics = await self._lyrics_service.get_lyrics(
                track.file_path,
                progress_callback=progress_callback
            )
            
            self.lyrics = lyrics
            self._render_lyrics()
            
        except FileNotFoundError as e:
            logger.error(f"Audio file not found: {e}")
            status_label.update("Error: Audio file not found")
            self.notify(
                f"Audio file not found: {track.title}. Please refresh the library.",
                severity="error",
                timeout=5
            )
        except RuntimeError as e:
            logger.error(f"Error loading lyrics: {e}")
            error_msg = str(e)
            if "model" in error_msg.lower():
                status_label.update("Error: Failed to download Whisper model")
                self.notify(
                    "Failed to download Whisper model. Please check your internet connection and try again.",
                    severity="error",
                    timeout=5
                )
            elif "permission" in error_msg.lower():
                status_label.update("Error: Permission denied")
                self.notify(
                    f"Permission denied: Cannot read audio file {track.title}",
                    severity="error",
                    timeout=5
                )
            else:
                status_label.update("Error: Transcription failed")
                self.notify(
                    f"Failed to generate lyrics: {error_msg}",
                    severity="error",
                    timeout=5
                )
        except Exception as e:
            logger.error(f"Unexpected error loading lyrics: {e}", exc_info=True)
            status_label.update(f"Error: {str(e)}")
            self.notify(
                f"Failed to generate lyrics: {str(e)}",
                severity="error",
                timeout=5
            )
        finally:
            self.is_loading = False
            loading_indicator.display = False
            status_label.update("")
    
    def _render_lyrics(self) -> None:
        """Render lyrics segments to the display."""
        content = self.query_one("#lyrics-content", Container)
        content.remove_children()
        
        if not self.lyrics:
            content.mount(Static("Select a track to view lyrics", classes="lyrics-empty"))
            return
        
        for i, segment in enumerate(self.lyrics):
            label = Static(
                segment.text,
                classes="lyric-segment",
                id=f"lyric-{i}"
            )
            content.mount(label)
    
    def _update_active_segment(self) -> None:
        """Update active segment based on playback position."""
        pass
