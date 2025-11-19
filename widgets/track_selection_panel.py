from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import ListView
from models import Track


class TrackSelectionPanel(Container):
    """Left panel for track selection."""
    
    selected_tracks: reactive[list[Track]] = reactive([])
    
    def compose(self):
        """Yield ListView with tracks."""
        pass
        
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle track selection."""
        pass
        
    def toggle_track_selection(self, track: Track) -> None:
        """Add or remove track from selection."""
        pass
        
    def get_selected_tracks(self) -> list[Track]:
        """Return currently selected tracks."""
        return self.selected_tracks
