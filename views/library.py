from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual.containers import Container


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
        ("enter", "select_track", "Play track"),
    ]
    
    def __init__(self, music_library, audio_player, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.music_library = music_library
        self.audio_player = audio_player
        self.tracks = []
    
    def on_mount(self) -> None:
        """Load tracks from music library when view is mounted."""
        self.tracks = self.music_library.get_tracks()
        self._populate_list()
    
    def compose(self) -> ComposeResult:
        """Compose the library view with a list of tracks."""
        yield Label("🎵 Music Library")
        yield ListView(id="track-list")
    
    def _populate_list(self) -> None:
        """Populate ListView with tracks, showing play indicator for current track."""
        list_view = self.query_one("#track-list", ListView)
        current_index = list_view.index
        list_view.clear()
        
        if not self.tracks:
            list_view.append(ListItem(Label("No music files found in ~/Music")))
            return
        
        current_track = self.audio_player.get_current_track()
        
        for track in self.tracks:
            if current_track and track.file_path == current_track.file_path:
                label_text = f"♪ {track.title} - {track.artist} ({track.duration})"
            else:
                label_text = f"  {track.title} - {track.artist} ({track.duration})"
            
            list_view.append(ListItem(Label(label_text)))
        
        if current_index is not None and current_index < len(self.tracks):
            list_view.index = current_index
        elif len(self.tracks) > 0:
            list_view.index = 0
    
    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update display when selection changes to show arrows on both sides."""
        if not self.tracks or event.list_view.index is None:
            return
        
        current_track = self.audio_player.get_current_track()
        
        for i, item in enumerate(event.list_view.children):
            if not isinstance(item, ListItem):
                continue
            
            track = self.tracks[i] if i < len(self.tracks) else None
            if not track:
                continue
            
            label = item.query_one(Label)
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
            
            label.update(f"{prefix} {track.title} - {track.artist} ({track.duration}){suffix}")
    
    def _update_play_indicator(self) -> None:
        """Refresh list display to update play indicator."""
        self._populate_list()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle Enter key press to play selected track.
        
        Displays error notification if track cannot be played.
        """
        if not self.tracks:
            return
        
        selected_index = event.list_view.index
        if selected_index is None or selected_index >= len(self.tracks):
            return
        
        track = self.tracks[selected_index]
        self.audio_player.set_playlist(self.tracks, selected_index)
        
        try:
            self.audio_player.play(track)
            self._update_play_indicator()
            
            from textual.widgets import ContentSwitcher
            switcher = self.app.query_one(ContentSwitcher)
            switcher.current = "now_playing"
            
        except FileNotFoundError:
            self.app.notify(
                f"❌ File not found: {track.title}\n\nThe file may have been moved or deleted.",
                severity="error",
                timeout=5
            )
        except RuntimeError:
            self.app.notify(
                f"❌ Cannot play: {track.title}\n\nThe file may be corrupted or unsupported.",
                severity="error",
                timeout=5
            )
    
    def action_move_down(self) -> None:
        """Move selection down in the list (j key)."""
        list_view = self.query_one("#track-list", ListView)
        list_view.action_cursor_down()
    
    def action_move_up(self) -> None:
        """Move selection up in the list (k key)."""
        list_view = self.query_one("#track-list", ListView)
        list_view.action_cursor_up()
    
    def action_select_track(self) -> None:
        """Play selected track (Enter key)."""
        list_view = self.query_one("#track-list", ListView)
        if list_view.index is not None:
            self.on_list_view_selected(ListView.Selected(list_view, list_view.highlighted_child))

