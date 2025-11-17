import numpy as np
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from services.audio_player import AudioPlayer
from services.spectrum_analyzer import SpectrumAnalyzer
from models.frequency import FrequencyBands, VisualizerConfig


class VisualizerView(Container):
    
    def __init__(self, audio_player: AudioPlayer, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.audio_player = audio_player
        self.config = VisualizerConfig()
        self.spectrum_analyzer = SpectrumAnalyzer(
            sample_rate=44100,
            buffer_size=2048,
            config=self.config
        )
        self.bar_count = self.config.bar_count
        self.max_bar_height = self.config.max_bar_height
        self.animation_timer = None
    
    def compose(self) -> ComposeResult:
        yield Static(self._render_baseline_only(), id="visualizer-content")
    
    def on_mount(self) -> None:
        try:
            self.spectrum_analyzer.start()
        except RuntimeError as e:
            pass
        
        update_interval = 1.0 / self.config.update_rate
        self.animation_timer = self.set_interval(update_interval, self._update_visualization)
    
    def on_unmount(self) -> None:
        self.spectrum_analyzer.stop()
    
    def _render_bars(self, bands: FrequencyBands) -> str:
        """Render frequency bars with baseline.
        
        Args:
            bands: Frequency band amplitudes
            
        Returns:
            String representation of visualization
        """
        all_amplitudes = bands.get_all_bands()
        
        bar_amplitudes = np.interp(
            np.linspace(0, len(all_amplitudes) - 1, self.bar_count),
            np.arange(len(all_amplitudes)),
            all_amplitudes
        )
        
        bar_heights = (bar_amplitudes * self.max_bar_height).astype(int)
        
        lines = []
        for row in range(self.max_bar_height, 0, -1):
            line = ""
            for height in bar_heights:
                if height >= row:
                    line += "█"
                else:
                    line += " "
            lines.append(line)
        
        baseline = "─" * self.bar_count
        lines.append(baseline)
        
        return "\n".join(lines)
    
    def _render_baseline_only(self) -> str:
        """Render baseline with minimal bars when not playing.
        
        Returns:
            String representation of baseline visualization
        """
        lines = []
        
        for row in range(self.max_bar_height, 0, -1):
            lines.append(" " * self.bar_count)
        
        baseline = "─" * self.bar_count
        lines.append(baseline)
        
        return "\n".join(lines)
    
    def _update_visualization(self) -> None:
        """Update visualization based on playback state."""
        if self.audio_player.is_playing() and self.spectrum_analyzer.is_active():
            bands = self.spectrum_analyzer.get_frequency_bands()
            visualization = self._render_bars(bands)
        else:
            visualization = self._render_baseline_only()
        
        visualizer_widget = self.query_one("#visualizer-content", Static)
        visualizer_widget.update(visualization)
