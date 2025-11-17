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


class Header(Vertical):
    volume_level: reactive[int] = reactive(30)
    
    def compose(self) -> ComposeResult:
        yield Static(SIGPLAY_ASCII, id="header-logo")
        yield Static(self._render_volume_bar(), id="header-volume")
    
    def _render_volume_bar(self) -> Text:
        result = Text()
        
        bar_width = 20
        filled_bars = int((self.volume_level / 100) * bar_width)
        
        result.append("Volume ", style="#888888")
        result.append("│", style="#888888")
        
        for i in range(bar_width):
            if i < filled_bars:
                if i < bar_width * 0.5:
                    result.append("█", style="#cc5500")
                elif i < bar_width * 0.75:
                    result.append("█", style="#ff8c00")
                else:
                    result.append("█", style="#ffb347")
            else:
                result.append("─", style="#333333")
        
        result.append("│ ", style="#888888")
        result.append(f"{self.volume_level}%", style="#ff8c00 bold")
        
        return result
    
    def watch_volume_level(self, new_value: int) -> None:
        try:
            volume_widget = self.query_one("#header-volume", Static)
            volume_widget.update(self._render_volume_bar())
        except Exception:
            pass
