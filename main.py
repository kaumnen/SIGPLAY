from textual.app import App, ComposeResult
from textual.widgets import Footer, ContentSwitcher
from textual.binding import Binding

from widgets.header import Header
from views.library import LibraryView
from views.now_playing import NowPlayingView
from views.visualizer import VisualizerView
from models.track import ViewState


class SigplayApp(App):
    """A retro-modern terminal music player built with Textual."""
    
    CSS_PATH = "styles/app.tcss"
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("tab", "cycle_view", "Switch View", priority=True),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_view = ViewState.LIBRARY
        self.view_order = [ViewState.LIBRARY, ViewState.NOW_PLAYING, ViewState.VISUALIZER]
    
    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield Header()
        
        with ContentSwitcher(initial="library"):
            yield LibraryView(id="library")
            yield NowPlayingView(id="now_playing")
            yield VisualizerView(id="visualizer")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application with the default view."""
        self.current_view = ViewState.LIBRARY
        switcher = self.query_one(ContentSwitcher)
        switcher.current = "library"
        self._update_footer()
    
    def action_quit(self) -> None:
        """Handle quit action for clean shutdown."""
        self.exit()
    
    def action_cycle_view(self) -> None:
        """Cycle to the next view in sequence."""
        current_index = self.view_order.index(self.current_view)
        next_index = (current_index + 1) % len(self.view_order)
        self.current_view = self.view_order[next_index]
        
        switcher = self.query_one(ContentSwitcher)
        switcher.current = self.current_view.value
        
        self._update_footer()
    
    def _update_footer(self) -> None:
        """Update footer to display current view and keyboard shortcuts."""
        view_names = {
            ViewState.LIBRARY: "Library",
            ViewState.NOW_PLAYING: "Now Playing",
            ViewState.VISUALIZER: "Visualizer"
        }
        
        current_view_name = view_names.get(self.current_view, "Unknown")
        self.sub_title = f"View: {current_view_name}"


def main():
    """Entry point for the SIGPLAY application."""
    app = SigplayApp()
    app.run()


if __name__ == "__main__":
    main()
