import numpy as np
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual.reactive import var
from rich.text import Text

from services.audio_player import AudioPlayer
from services.spectrum_analyzer import SpectrumAnalyzer
from models.frequency import FrequencyBands, VisualizerConfig


class VisualizerView(Container):
    
    terminal_width = var(0)
    
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
        
        self._calculate_bar_counts()
    
    def compose(self) -> ComposeResult:
        yield Static(self._render_baseline_only(), id="visualizer-content")
    
    def on_mount(self) -> None:
        try:
            self.spectrum_analyzer.start()
        except RuntimeError:
            pass
        
        update_interval = 1.0 / self.config.update_rate
        self.animation_timer = self.set_interval(update_interval, self._update_visualization)
        
        self.terminal_width = self.size.width
    
    def on_unmount(self) -> None:
        self.spectrum_analyzer.stop()
    
    def watch_terminal_width(self, new_width: int) -> None:
        """React to terminal width changes and recalculate bar count.
        
        Ensures minimum of 20 bars and maximum based on available width.
        Re-renders visualization with new bar count.
        
        Args:
            new_width: New terminal width in characters
        """
        if new_width <= 0:
            return
        
        self.bar_count = max(20, min(new_width - 4, 120))
        self._calculate_bar_counts()
    
    def on_resize(self) -> None:
        """Handle terminal resize events."""
        self.terminal_width = self.size.width
    
    def _calculate_bar_counts(self) -> None:
        """Calculate how many bars represent each frequency range.
        
        Distributes bars proportionally based on the number of frequency bins
        in each range (bass, mid, high).
        """
        bass_bin_count = self.spectrum_analyzer._bass_bins[1] - self.spectrum_analyzer._bass_bins[0]
        mid_bin_count = self.spectrum_analyzer._mid_bins[1] - self.spectrum_analyzer._mid_bins[0]
        high_bin_count = self.spectrum_analyzer._high_bins[1] - self.spectrum_analyzer._high_bins[0]
        
        total_bins = bass_bin_count + mid_bin_count + high_bin_count
        
        self.bass_bar_count = int((bass_bin_count / total_bins) * self.bar_count)
        self.mid_bar_count = int((mid_bin_count / total_bins) * self.bar_count)
        self.high_bar_count = self.bar_count - self.bass_bar_count - self.mid_bar_count
    
    def _apply_frequency_colors(self, bar_line: str) -> Text:
        """Apply color gradient based on frequency range.
        
        Colors bars according to their frequency range:
        - Bass (darker orange): #cc5500
        - Mid (medium orange): #ff8c00
        - High (lighter amber): #ffb347
        
        Args:
            bar_line: String of bar characters to colorize
            
        Returns:
            Rich Text object with colored bars
        """
        text = Text()
        
        for i, char in enumerate(bar_line):
            if i < self.bass_bar_count:
                color = "#cc5500"
            elif i < self.bass_bar_count + self.mid_bar_count:
                color = "#ff8c00"
            else:
                color = "#ffb347"
            
            text.append(char, style=color)
        
        return text
    
    def _render_bars(self, bands: FrequencyBands) -> Text:
        """Render frequency bars with baseline and color gradients.
        
        Args:
            bands: Frequency band amplitudes
            
        Returns:
            Rich Text representation of visualization with colors
        """
        all_amplitudes = bands.get_all_bands()
        
        bar_amplitudes = np.interp(
            np.linspace(0, len(all_amplitudes) - 1, self.bar_count),
            np.arange(len(all_amplitudes)),
            all_amplitudes
        )
        
        bar_heights = (bar_amplitudes * self.max_bar_height).astype(int)
        
        result = Text()
        
        for row in range(self.max_bar_height, 0, -1):
            line = ""
            for height in bar_heights:
                if height >= row:
                    line += "█"
                else:
                    line += " "
            
            colored_line = self._apply_frequency_colors(line)
            result.append_text(colored_line)
            result.append("\n")
        
        baseline = "─" * self.bar_count
        colored_baseline = self._apply_frequency_colors(baseline)
        result.append_text(colored_baseline)
        
        return result
    
    def _render_baseline_only(self) -> Text:
        """Render baseline with minimal bars when not playing.
        
        Returns:
            Rich Text representation of baseline visualization with colors
        """
        result = Text()
        
        for row in range(self.max_bar_height, 0, -1):
            result.append(" " * self.bar_count)
            result.append("\n")
        
        baseline = "─" * self.bar_count
        colored_baseline = self._apply_frequency_colors(baseline)
        result.append_text(colored_baseline)
        
        return result
    
    def _update_visualization(self) -> None:
        """Update visualization based on playback state."""
        if self.audio_player.is_playing() and self.spectrum_analyzer.is_active():
            bands = self.spectrum_analyzer.get_frequency_bands()
            visualization = self._render_bars(bands)
        else:
            visualization = self._render_baseline_only()
        
        visualizer_widget = self.query_one("#visualizer-content", Static)
        visualizer_widget.update(visualization)
