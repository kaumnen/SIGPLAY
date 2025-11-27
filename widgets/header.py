from textual.widgets import Static
from textual.reactive import reactive
from textual.containers import Vertical
from textual.app import ComposeResult
from rich.text import Text

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
            result.append("Volume ", style="#888888")
            result.append("│", style="#888888")
            
            for i in range(VOLUME_BAR_WIDTH):
                result.append("─", style="#333333")
            
            result.append("│ ", style="#888888")
            result.append("MUTED", style="#888888 bold")
        else:
            filled_bars = int((self.volume_level / 100) * VOLUME_BAR_WIDTH)
            
            result.append("Volume ", style="#888888")
            result.append("│", style="#888888")
            
            for i in range(VOLUME_BAR_WIDTH):
                if i < filled_bars:
                    if i < VOLUME_BAR_WIDTH * 0.5:
                        result.append("█", style="#cc5500")
                    elif i < VOLUME_BAR_WIDTH * 0.75:
                        result.append("█", style="#ff8c00")
                    else:
                        result.append("█", style="#ffb347")
                else:
                    result.append("─", style="#333333")
            
            result.append("│ ", style="#888888")
            result.append(f"{self.volume_level}%", style="#ff8c00 bold")
        
        result.append("    │    Shuffle ", style="#888888")
        if self.is_shuffle:
            result.append("ON", style="#ff8c00 bold")
        else:
            result.append("OFF", style="#555555")
        
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
