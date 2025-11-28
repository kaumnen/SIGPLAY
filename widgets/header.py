from textual.widgets import Static
from textual.reactive import reactive
from textual.containers import Vertical
from textual.app import ComposeResult
from rich.text import Text
from styles import COLOR_BASS, COLOR_PRIMARY, COLOR_HIGHLIGHT, COLOR_MUTED, COLOR_DIM, COLOR_INACTIVE

SIGPLAY_ASCII = """
 ███████╗██╗ ██████╗ ██████╗ ██╗      █████╗ ██╗   ██╗
 ██╔════╝██║██╔════╝ ██╔══██╗██║     ██╔══██╗╚██╗ ██╔╝
 ███████╗██║██║  ███╗██████╔╝██║     ███████║ ╚████╔╝ 
 ╚════██║██║██║   ██║██╔═══╝ ██║     ██╔══██║  ╚██╔╝  
 ███████║██║╚██████╔╝██║     ███████╗██║  ██║   ██║   
 ╚══════╝╚═╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   
"""

VOLUME_BAR_WIDTH = 20
DEFAULT_VOLUME_LEVEL = 30


class Header(Vertical):
    volume_level: reactive[int] = reactive(DEFAULT_VOLUME_LEVEL)
    is_muted: reactive[bool] = reactive(False)
    is_shuffle: reactive[bool] = reactive(False)
    
    def compose(self) -> ComposeResult:
        yield Static(SIGPLAY_ASCII, id="header-logo")
        yield Static("─" * 80, id="header-divider")
        yield Static(self._render_volume_bar(), id="header-volume")
    
    def _render_volume_bar(self) -> Text:
        result = Text()
        
        if self.is_muted:
            result.append("Volume ", style=COLOR_MUTED)
            result.append("│", style=COLOR_MUTED)
            
            for i in range(VOLUME_BAR_WIDTH):
                result.append("─", style=COLOR_INACTIVE)
            
            result.append("│ ", style=COLOR_MUTED)
            result.append("MUTED", style=f"{COLOR_MUTED} bold")
        else:
            filled_bars = int((self.volume_level / 100) * VOLUME_BAR_WIDTH)
            
            result.append("Volume ", style=COLOR_MUTED)
            result.append("│", style=COLOR_MUTED)
            
            for i in range(VOLUME_BAR_WIDTH):
                if i < filled_bars:
                    if i < VOLUME_BAR_WIDTH * 0.5:
                        result.append("█", style=COLOR_BASS)
                    elif i < VOLUME_BAR_WIDTH * 0.75:
                        result.append("█", style=COLOR_PRIMARY)
                    else:
                        result.append("█", style=COLOR_HIGHLIGHT)
                else:
                    result.append("─", style=COLOR_INACTIVE)
            
            result.append("│ ", style=COLOR_MUTED)
            result.append(f"{self.volume_level}%", style=f"{COLOR_PRIMARY} bold")
        
        result.append("    │    Shuffle ", style=COLOR_MUTED)
        if self.is_shuffle:
            result.append("ON", style=f"{COLOR_PRIMARY} bold")
        else:
            result.append("OFF", style=COLOR_DIM)
        
        return result
    
    def watch_volume_level(self, new_value: int) -> None:
        try:
            volume_widget = self.query_one("#header-volume", Static)
            volume_widget.update(self._render_volume_bar())
        except Exception:
            pass
    
    def watch_is_muted(self, new_value: bool) -> None:
        try:
            volume_widget = self.query_one("#header-volume", Static)
            volume_widget.update(self._render_volume_bar())
        except Exception:
            pass
    
    def watch_is_shuffle(self, new_value: bool) -> None:
        try:
            volume_widget = self.query_one("#header-volume", Static)
            volume_widget.update(self._render_volume_bar())
        except Exception:
            pass
