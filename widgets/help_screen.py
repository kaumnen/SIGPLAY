from __future__ import annotations

from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual.containers import Container, VerticalScroll
from textual.app import ComposeResult


class HelpScreen(ModalScreen[None]):
    """Modal screen displaying help information."""
    
    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    
    #help-container {
        width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    #help-scroll {
        width: 100%;
        height: auto;
        max-height: 30;
    }
    
    #help-content {
        width: 100%;
        height: auto;
    }
    
    #help-close-button {
        width: 100%;
        margin-top: 1;
    }
    """
    
    def __init__(self, view_type: str = "main") -> None:
        """Initialize help screen.
        
        Args:
            view_type: Either "main" or "floppy_mix" to show appropriate help.
        """
        super().__init__()
        self.view_type = view_type
    
    def compose(self) -> ComposeResult:
        """Compose the help screen."""
        with Container(id="help-container"):
            with VerticalScroll(id="help-scroll"):
                if self.view_type == "main":
                    yield self._compose_main_help()
                else:
                    yield self._compose_floppy_mix_help()
            
            yield Button("Close (Esc)", id="help-close-button", variant="primary")
    
    def _compose_main_help(self) -> Static:
        """Compose help content for main view."""
        help_text = """[bold #ff8c00]🎵 SIGPLAY - Terminal Music Player[/bold #ff8c00]

[bold]NAVIGATION[/bold]
  j/k         Move down/up in track list
  Enter       Play selected track
  
[bold]PLAYBACK CONTROLS[/bold]
  Space       Play/Pause current track
  s           Stop playback
  n           Next track
  p           Previous track
  
[bold]VOLUME CONTROLS[/bold]
  +/=         Increase volume
  -           Decrease volume
  m           Toggle mute
  
[bold]FEATURES[/bold]
  f           Open Floppy Mix (AI DJ mixing)
  d           Return to Default View (Library)
  o           Select audio device (coming soon)
  h/?         Show this help
  q           Quit application

[bold]LIBRARY[/bold]
  • Music files are loaded from ~/Music
  • Supported formats: MP3, WAV, OGG, FLAC
  • ♪ indicates currently playing track
  • ▶ arrows show selected track"""
        
        return Static(help_text, id="help-content")
    
    def _compose_floppy_mix_help(self) -> Static:
        """Compose help content for Floppy Mix view."""
        help_text = """[bold #ff8c00]💾 FLOPPY MIX - AI DJ Mixing[/bold #ff8c00]

[bold]WHAT IS FLOPPY MIX?[/bold]
Create professional DJ mixes using natural language instructions.
An AI agent analyzes your instructions and applies audio effects,
crossfades, and mixing techniques automatically.

[bold]HOW TO USE[/bold]
  1. Select tracks using Space (j/k to navigate)
  2. Tab to instructions panel
  3. Enter mixing instructions in plain English
  4. Click "Start Mix" or press Enter
  5. Preview the generated mix
  6. Save to library or discard

[bold]EXAMPLE INSTRUCTIONS[/bold]
  • "Mix these tracks with smooth 4-second crossfades"
  • "Boost the bass and add some reverb"
  • "Create a high-energy mix with compression"
  • "Blend tracks smoothly with subtle effects"
  • "Add warmth with bass boost and gentle compression"

[bold]AVAILABLE EFFECTS[/bold]
  Bass Boost      Enhance low frequencies
  Treble Boost    Enhance high frequencies
  Reverb          Add space and depth
  Compression     Even out volume levels
  Crossfades      Smooth transitions (2-6 seconds)
  EQ Filters      Shape the frequency spectrum

[bold]KEYBINDINGS[/bold]
  Space       Toggle track selection / Play preview
  j/k         Navigate track list
  Tab         Switch between panels
  Enter       Start mix / Submit
  d           Return to default view
  h/?         Show this help"""
        
        return Static(help_text, id="help-content")
    
    def on_mount(self) -> None:
        """Focus the button when screen mounts."""
        self.call_after_refresh(self._focus_button)
    
    def _focus_button(self) -> None:
        """Set focus to close button."""
        try:
            button = self.query_one("#help-close-button", Button)
            button.focus()
        except Exception:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle close button press."""
        if event.button.id == "help-close-button":
            self.dismiss()
    
    async def on_key(self, event) -> None:
        """Handle key events."""
        if event.key == "escape":
            self.dismiss()
            event.prevent_default()
            event.stop()
        elif event.key == "j":
            scroll = self.query_one("#help-scroll", VerticalScroll)
            scroll.scroll_down()
            event.prevent_default()
            event.stop()
        elif event.key == "k":
            scroll = self.query_one("#help-scroll", VerticalScroll)
            scroll.scroll_up()
            event.prevent_default()
            event.stop()
