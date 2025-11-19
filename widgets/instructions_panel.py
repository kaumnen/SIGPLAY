from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import TextArea


class InstructionsPanel(Container):
    """Right panel for mixing instructions."""
    
    instructions: reactive[str] = reactive("")
    
    def compose(self):
        """Yield TextArea widget."""
        pass
        
    def get_instructions(self) -> str:
        """Return current instructions text."""
        return self.instructions
        
    def clear(self) -> None:
        """Clear the text input."""
        self.instructions = ""
