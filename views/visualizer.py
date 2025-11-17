import numpy as np
import time
import logging
import psutil
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual.reactive import var
from rich.text import Text

from services.audio_player import AudioPlayer
from services.spectrum_analyzer import SpectrumAnalyzer
from models.frequency import FrequencyBands, VisualizerConfig, PerformanceMetrics

logger = logging.getLogger(__name__)


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
        
        self.performance_metrics = PerformanceMetrics()
        self._frame_times = []
        self._last_frame_time = time.time()
        self._process = psutil.Process()
        self._cpu_check_interval = 1.0
        self._last_cpu_check = time.time()
        self._current_update_rate = self.config.update_rate
        
        self._calculate_bar_counts()
    
    def compose(self) -> ComposeResult:
        yield Static(self._render_baseline_only(), id="visualizer-content")
    
    def on_mount(self) -> None:
        self.spectrum_analyzer.start()
        
        update_interval = 1.0 / self._current_update_rate
        self.animation_timer = self.set_interval(update_interval, self._update_visualization)
        
        self.terminal_width = self.size.width
        
        self.set_interval(self._cpu_check_interval, self._monitor_performance)
    
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
    
    def _measure_frame_time(self) -> float:
        """Measure time taken for current frame.
        
        Returns:
            Frame processing time in seconds
        """
        current_time = time.time()
        frame_time = current_time - self._last_frame_time
        self._last_frame_time = current_time
        
        self._frame_times.append(frame_time)
        if len(self._frame_times) > 30:
            self._frame_times.pop(0)
        
        return frame_time
    
    def _calculate_frame_rate(self) -> float:
        """Calculate current frame rate from recent frame times.
        
        Returns:
            Current frames per second
        """
        if not self._frame_times:
            return 0.0
        
        avg_frame_time = sum(self._frame_times) / len(self._frame_times)
        if avg_frame_time > 0:
            return 1.0 / avg_frame_time
        return 0.0
    
    def _monitor_performance(self) -> None:
        """Monitor CPU usage and adjust frame rate if needed.
        
        Checks CPU usage and reduces frame rate if it exceeds 20%.
        Logs performance metrics for monitoring.
        """
        try:
            cpu_percent = self._process.cpu_percent(interval=None)
            
            self.performance_metrics.cpu_percent = cpu_percent
            self.performance_metrics.frame_rate = self._calculate_frame_rate()
            self.performance_metrics.last_update = time.time()
            
            if cpu_percent > 20.0 and self._current_update_rate > 15:
                old_rate = self._current_update_rate
                self._current_update_rate = max(15, self._current_update_rate - 5)
                
                if self.animation_timer:
                    self.animation_timer.stop()
                
                update_interval = 1.0 / self._current_update_rate
                self.animation_timer = self.set_interval(update_interval, self._update_visualization)
                
                logger.warning(
                    f"High CPU usage detected ({cpu_percent:.1f}%). "
                    f"Reducing frame rate from {old_rate} to {self._current_update_rate} FPS"
                )
            
            elif cpu_percent < 10.0 and self._current_update_rate < self.config.update_rate:
                old_rate = self._current_update_rate
                self._current_update_rate = min(self.config.update_rate, self._current_update_rate + 5)
                
                if self.animation_timer:
                    self.animation_timer.stop()
                
                update_interval = 1.0 / self._current_update_rate
                self.animation_timer = self.set_interval(update_interval, self._update_visualization)
                
                logger.info(
                    f"CPU usage normalized ({cpu_percent:.1f}%). "
                    f"Increasing frame rate from {old_rate} to {self._current_update_rate} FPS"
                )
            
            if self.performance_metrics.frame_rate < 15 or self.performance_metrics.frame_rate > 30:
                logger.debug(
                    f"Performance metrics - CPU: {cpu_percent:.1f}%, "
                    f"FPS: {self.performance_metrics.frame_rate:.1f}, "
                    f"Target: {self._current_update_rate}"
                )
            
        except Exception as e:
            logger.error(f"Error monitoring performance: {e}")
    
    def _update_visualization(self) -> None:
        """Update visualization based on playback state."""
        try:
            if self.audio_player.is_playing() and self.spectrum_analyzer.is_active():
                audio_buffer = self.audio_player.get_latest_audio_buffer()
                bands = self.spectrum_analyzer.get_frequency_bands(audio_buffer)
                visualization = self._render_bars(bands)
            else:
                visualization = self._render_baseline_only()
            
            visualizer_widget = self.query_one("#visualizer-content", Static)
            visualizer_widget.update(visualization)
            
        except Exception as e:
            logger.error(f"Error updating visualization: {e}")
        
        finally:
            self._measure_frame_time()
