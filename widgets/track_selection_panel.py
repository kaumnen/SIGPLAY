from __future__ import annotations

from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import ListView, ListItem, Label, Static
from textual.app import ComposeResult
from textual import events
from models.track import Track
import logging

logger = logging.getLogger(__name__)


class TrackSelectionPanel(Container):
    """Left panel for track selection."""
    
    selected_tracks: reactive[list[Track]] = reactive([], init=False)
    
    def __init__(self, tracks: list[Track], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracks = tracks
        self._track_items: dict[int, Track] = {}
        self._selected_indices: set[int] = set()
        self._cursor_index: int = 0
    
    def compose(self) -> ComposeResult:
        """Yield ListView with tracks."""
        with Vertical(id="track-selection-container"):
            yield Label("Select Tracks (j/k to navigate, Space to select)", id="track-selection-label")
            yield ListView(id="track-list", classes="scrollable-list")
    
    def on_mount(self) -> None:
        """Populate track list on mount."""
        self._populate_tracks()
    
    def _populate_tracks(self) -> None:
        """Populate the ListView with tracks."""
        try:
            track_list = self.query_one("#track-list", ListView)
            track_list.clear()
            self._track_items.clear()
            
            if not self.tracks:
                no_tracks_item = ListItem(Static("No tracks available"))
                track_list.append(no_tracks_item)
                logger.debug("No tracks to populate")
                return
            
            for idx, track in enumerate(self.tracks):
                self._track_items[idx] = track
                item = ListItem(Static(f"  {track.title} - {track.artist}"))
                track_list.append(item)
            
            if len(self.tracks) > 0:
                track_list.index = 0
                self._cursor_index = 0
                
            logger.debug(f"Populated track list with {len(self.tracks)} tracks")
        except Exception as e:
            logger.error(f"Error populating tracks: {e}")
    
    def on_key(self, event: events.Key) -> None:
        """Handle keyboard navigation."""
        if not self.tracks:
            return
        
        if event.key == "j":
            self._move_cursor_down()
            event.prevent_default()
            event.stop()
        elif event.key == "k":
            self._move_cursor_up()
            event.prevent_default()
            event.stop()
        elif event.key == "space":
            self._toggle_current_track()
            event.prevent_default()
            event.stop()
    
    def _move_cursor_down(self) -> None:
        """Move cursor down in track list."""
        if self._cursor_index < len(self.tracks) - 1:
            self._cursor_index += 1
            try:
                track_list = self.query_one("#track-list", ListView)
                track_list.index = self._cursor_index
                logger.debug(f"Moved cursor to index {self._cursor_index}")
            except Exception as e:
                logger.error(f"Error moving cursor down: {e}")
    
    def _move_cursor_up(self) -> None:
        """Move cursor up in track list."""
        if self._cursor_index > 0:
            self._cursor_index -= 1
            try:
                track_list = self.query_one("#track-list", ListView)
                track_list.index = self._cursor_index
                logger.debug(f"Moved cursor to index {self._cursor_index}")
            except Exception as e:
                logger.error(f"Error moving cursor up: {e}")
    
    def _toggle_current_track(self) -> None:
        """Toggle selection of current track."""
        if self._cursor_index in self._track_items:
            track = self._track_items[self._cursor_index]
            self.toggle_track_selection(track)
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle track selection from ListView."""
        try:
            self._cursor_index = event.list_view.index
            logger.debug(f"ListView selected index {self._cursor_index}")
        except Exception as e:
            logger.error(f"Error handling list view selection: {e}")
    
    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update display when cursor moves to show arrows."""
        if not self.tracks or event.list_view.index is None:
            return
        
        self._cursor_index = event.list_view.index
        self._update_visual_indicators()
        
    def toggle_track_selection(self, track: Track) -> None:
        """Add or remove track from selection."""
        try:
            idx = None
            for i, t in self._track_items.items():
                if t == track:
                    idx = i
                    break
            
            if idx is None:
                logger.warning(f"Track not found in track items: {track.title}")
                return
            
            if idx in self._selected_indices:
                self._selected_indices.remove(idx)
                logger.debug(f"Deselected track: {track.title}")
            else:
                self._selected_indices.add(idx)
                logger.debug(f"Selected track: {track.title}")
            
            self.selected_tracks = [self._track_items[i] for i in sorted(self._selected_indices)]
            self._update_visual_indicators()
            
        except Exception as e:
            logger.error(f"Error toggling track selection: {e}")
    
    def _update_visual_indicators(self) -> None:
        """Update visual indicators for selected tracks and cursor position."""
        try:
            track_list = self.query_one("#track-list", ListView)
            
            for idx, track in self._track_items.items():
                try:
                    if idx < len(track_list.children):
                        item = track_list.children[idx]
                        if isinstance(item, ListItem):
                            static = item.query_one(Static)
                            
                            is_selected = idx in self._selected_indices
                            is_highlighted = idx == self._cursor_index
                            
                            if is_selected and is_highlighted:
                                prefix = "▶ ✓"
                                suffix = " ◀"
                                item.add_class("selected")
                            elif is_selected:
                                prefix = "  ✓"
                                suffix = "  "
                                item.add_class("selected")
                            elif is_highlighted:
                                prefix = "▶  "
                                suffix = " ◀"
                                item.remove_class("selected")
                            else:
                                prefix = "   "
                                suffix = "  "
                                item.remove_class("selected")
                            
                            static.update(f"{prefix} {track.title} - {track.artist}{suffix}")
                except Exception as e:
                    logger.debug(f"Could not update item at index {idx}: {e}")
                    
        except Exception as e:
            logger.error(f"Error updating visual indicators: {e}")
    
    def get_selected_tracks(self) -> list[Track]:
        """Return currently selected tracks."""
        return self.selected_tracks
    
    def clear_selection(self) -> None:
        """Clear all track selections."""
        self._selected_indices.clear()
        self.selected_tracks = []
        self._update_visual_indicators()
        logger.debug("Cleared all track selections")
    
    def refresh_tracks(self, tracks: list[Track]) -> None:
        """Refresh the track list with new tracks."""
        logger.debug(f"Refreshing track list with {len(tracks)} tracks")
        self.tracks = tracks
        self._track_items = {}
        self._selected_indices = set()
        self._cursor_index = 0
        self.selected_tracks = []
        self._populate_tracks()
