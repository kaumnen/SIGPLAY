from __future__ import annotations

import asyncio
import logging
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Static, ListView, ListItem, Label, LoadingIndicator
from textual.timer import Timer

from models.track import Track
from models.lyrics import LyricSegment
from models.playback import PlaybackState
from services.audio_player import AudioPlayer
from services.music_library import MusicLibrary
from services.lyrics_service import LyricsService

logger = logging.getLogger(__name__)


class LyricsView(Container):
    """Full-screen view displaying track library and synchronized lyrics."""
    
    BINDINGS = [
        Binding("j", "move_down", "Move down", show=False),
        Binding("k", "move_up", "Move up", show=False),
        Binding("enter", "select_track", "Play"),
    ]
    
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
        self._pending_transcription_task = None
        self._last_playback_state = None
    
    def compose(self) -> ComposeResult:
        """Compose the lyrics view layout."""
        with Horizontal(id="lyrics-container"):
            with Container(id="lyrics-library-panel"):
                yield Static("🎵 Track Library", id="lyrics-library-title")
                yield ListView(id="lyrics-track-list", classes="lyrics-track-list")
            
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
        self._last_playback_state = self._audio_player.get_state()
        loading_indicator = self.query_one("#lyrics-loading", LoadingIndicator)
        loading_indicator.display = False
    
    def on_show(self) -> None:
        """Called when view becomes visible."""
        self._refresh_track_list()
        if self.current_track:
            self._load_lyrics_for_track(self.current_track)
        self.call_after_refresh(self._set_initial_focus)
    
    def _set_initial_focus(self) -> None:
        """Set focus to track list after view is fully rendered."""
        try:
            track_list = self.query_one("#lyrics-track-list", ListView)
            track_list.focus()
        except Exception as e:
            logger.error(f"Failed to focus track list: {e}")
    
    def _refresh_track_list(self) -> None:
        """Populate track list from music library."""
        track_list = self.query_one("#lyrics-track-list", ListView)
        current_index = track_list.index
        track_list.clear()
        
        tracks = self._music_library.get_tracks()
        
        if not tracks:
            item = ListItem(Label("No music files found"))
            track_list.append(item)
            return
        
        current_track = self._audio_player.get_current_track()
        
        for track in tracks:
            is_playing = (current_track and track.file_path == current_track.file_path)
            prefix = "♪ " if is_playing else "  "
            label_text = f"{prefix}{track.title} - {track.artist or 'Unknown'}"
            item = ListItem(Label(label_text))
            item.track = track
            track_list.append(item)
        
        if current_index is not None and current_index < len(tracks):
            track_list.index = current_index
        elif len(tracks) > 0:
            track_list.index = 0
    
    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update display when selection changes to show arrows on both sides."""
        tracks = self._music_library.get_tracks()
        
        if not tracks or event.list_view.index is None:
            return
        
        current_track = self._audio_player.get_current_track()
        
        for i, item in enumerate(event.list_view.children):
            if not isinstance(item, ListItem):
                continue
            
            track = tracks[i] if i < len(tracks) else None
            if not track:
                continue
            
            try:
                label = item.query_one(Label)
            except Exception as e:
                logger.debug(f"Could not query label from list item: {e}")
                continue
            
            is_selected = (i == event.list_view.index)
            is_playing = (current_track and track.file_path == current_track.file_path)
            
            if is_playing and is_selected:
                prefix = "▶ ♪"
                suffix = " ◀"
            elif is_playing:
                prefix = "  ♪"
                suffix = "  "
            elif is_selected:
                prefix = "▶  "
                suffix = " ◀"
            else:
                prefix = "   "
                suffix = "  "
            
            label.update(f"{prefix} {track.title} - {track.artist or 'Unknown'}{suffix}")
    
    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle track selection."""
        if hasattr(event.item, 'track'):
            track = event.item.track
            
            if self._pending_transcription_task and not self._pending_transcription_task.done():
                logger.info("Cancelling pending transcription due to track switch")
                self._pending_transcription_task.cancel()
                try:
                    await self._pending_transcription_task
                except asyncio.CancelledError:
                    logger.debug("Transcription cancelled successfully")
            
            self.current_track = track
            
            self._audio_player.play(track)
            self._refresh_track_list()
            
            await self._load_lyrics_for_track(track)
    
    async def _load_lyrics_for_track(self, track: Track) -> None:
        """Load or generate lyrics for the selected track.
        
        Args:
            track: Track to load lyrics for.
        """
        self.is_loading = True
        self.lyrics = []
        self.active_segment_index = -1
        
        content = self.query_one("#lyrics-content", Container)
        try:
            content.remove_children()
        except Exception as e:
            logger.error(f"Error clearing lyrics content: {e}")
        
        loading_indicator = self.query_one("#lyrics-loading", LoadingIndicator)
        status_label = self.query_one("#lyrics-status", Static)
        
        loading_indicator.display = True
        status_label.update("")
        
        try:
            def progress_callback(message: str) -> None:
                """Update status label."""
                status_label.update(message)
            
            self._pending_transcription_task = asyncio.create_task(
                self._lyrics_service.get_lyrics(
                    track.file_path,
                    progress_callback=progress_callback
                )
            )
            
            lyrics = await self._pending_transcription_task
            
            self.lyrics = lyrics
            self._render_lyrics()
            
        except asyncio.CancelledError:
            logger.info("Lyrics loading cancelled")
            status_label.update("")
            raise
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
            self._pending_transcription_task = None
    
    def _render_lyrics(self) -> None:
        """Render lyrics segments to the display."""
        content = self.query_one("#lyrics-content", Container)
        
        try:
            content.remove_children()
        except Exception as e:
            logger.error(f"Error removing children: {e}")
        
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
        """Update active segment based on playback position.
        
        Called every 0.5 seconds to check playback position and update
        the active segment highlight. Handles playback state changes:
        - STOPPED: Reset active segment to beginning
        - PAUSED: Maintain current highlight
        - PLAYING: Update based on position
        """
        if not self.lyrics:
            return
        
        current_state = self._audio_player.get_state()
        
        if current_state == PlaybackState.STOPPED:
            if self._last_playback_state != PlaybackState.STOPPED:
                logger.debug("Playback stopped, resetting active segment")
                self.active_segment_index = -1
                self._highlight_active_segment()
            self._last_playback_state = current_state
            return
        
        if current_state == PlaybackState.PAUSED:
            self._last_playback_state = current_state
            return
        
        if not self._audio_player.is_playing():
            return
        
        position = self._audio_player.get_position()
        
        new_index = -1
        for i, segment in enumerate(self.lyrics):
            if segment.start <= position < segment.end:
                new_index = i
                break
        
        if new_index != self.active_segment_index:
            self.active_segment_index = new_index
            self._highlight_active_segment()
        
        self._last_playback_state = current_state
    
    def _highlight_active_segment(self) -> None:
        """Highlight the active segment and scroll to it.
        
        Applies 'active' CSS class to the current segment and removes it
        from all others. Auto-scrolls to center the active segment.
        """
        try:
            content = self.query_one("#lyrics-content", Container)
            
            for widget in content.query(".lyric-segment"):
                widget.remove_class("active")
            
            if self.active_segment_index >= 0:
                try:
                    active = content.query_one(f"#lyric-{self.active_segment_index}")
                    active.add_class("active")
                    
                    scroll = self.query_one("#lyrics-scroll", VerticalScroll)
                    scroll.scroll_to_widget(active, animate=True, center=True)
                except Exception as e:
                    logger.debug(f"Error highlighting segment: {e}")
        except Exception as e:
            logger.error(f"Error in _highlight_active_segment: {e}")
    
    def action_move_down(self) -> None:
        """Move selection down in the list (j key)."""
        track_list = self.query_one("#lyrics-track-list", ListView)
        track_list.action_cursor_down()
    
    def action_move_up(self) -> None:
        """Move selection up in the list (k key)."""
        track_list = self.query_one("#lyrics-track-list", ListView)
        track_list.action_cursor_up()
    
    def action_select_track(self) -> None:
        """Play selected track (Enter key)."""
        track_list = self.query_one("#lyrics-track-list", ListView)
        if track_list.index is not None:
            tracks = self._music_library.get_tracks()
            if track_list.index < len(tracks):
                track = tracks[track_list.index]
                
                if self._pending_transcription_task and not self._pending_transcription_task.done():
                    logger.info("Cancelling pending transcription due to track switch")
                    self._pending_transcription_task.cancel()
                
                self.current_track = track
                self._audio_player.play(track)
                self._refresh_track_list()
                
                asyncio.create_task(self._load_lyrics_for_track(track))
    
    def cleanup(self) -> None:
        """Cleanup when view is hidden or app exits.
        
        Stops the update timer and cancels any pending transcription tasks.
        """
        logger.info("Cleaning up LyricsView")
        
        if self._update_timer:
            self._update_timer.stop()
            self._update_timer = None
        
        if self._pending_transcription_task and not self._pending_transcription_task.done():
            logger.info("Cancelling pending transcription during cleanup")
            self._pending_transcription_task.cancel()
