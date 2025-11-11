import random
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


class VisualizerView(Container):
    DEFAULT_CSS = """
    VisualizerView {
        align: center middle;
        background: $surface;
    }
    
    #visualizer-content {
        width: 80;
        height: 20;
        content-align: center middle;
        color: $accent;
        text-style: bold;
    }
    """
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bar_heights = [random.randint(1, 20) for _ in range(40)]
        self.animation_timer = None
    
    def compose(self) -> ComposeResult:
        yield Static(self._generate_visualization(), id="visualizer-content")
    
    def on_mount(self) -> None:
        self.animation_timer = self.set_interval(0.15, self._update_visualization)
    
    def _generate_visualization(self) -> str:
        bars = []
        max_height = 20
        
        for height in self.bar_heights:
            bar_chars = "█" * height
            padding = " " * (max_height - height)
            bars.append(padding + bar_chars)
        
        lines = []
        for row in range(max_height):
            line = ""
            for bar in bars:
                if row < len(bar):
                    line += bar[row]
                else:
                    line += " "
            lines.append(line)
        
        title = "♪ AUDIO VISUALIZER ♪"
        centered_title = title.center(40)
        
        return centered_title + "\n\n" + "\n".join(lines)
    
    def _update_visualization(self) -> None:
        for i in range(len(self.bar_heights)):
            change = random.randint(-3, 3)
            self.bar_heights[i] = max(1, min(20, self.bar_heights[i] + change))
        
        visualizer_widget = self.query_one("#visualizer-content", Static)
        visualizer_widget.update(self._generate_visualization())
