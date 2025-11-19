from textual.containers import Container
from textual.reactive import reactive


class MixProgressPanel(Container):
    """Bottom panel for progress and controls."""
    
    status_message: reactive[str] = reactive("")
    show_controls: reactive[bool] = reactive(False)
    
    def update_status(self, message: str) -> None:
        """Update the status message."""
        self.status_message = message
        
    def show_preview_controls(self) -> None:
        """Display save/discard buttons."""
        self.show_controls = True
        
    def hide_preview_controls(self) -> None:
        """Hide save/discard buttons."""
        self.show_controls = False
