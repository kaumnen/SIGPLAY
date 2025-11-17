import numpy as np
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static
from rich.text import Text
from services.audio_player import AudioPlayer


class NowPlayingView(Container):
    """Widget displaying currently playing track information."""

    def __init__(self, audio_player: AudioPlayer, **kwargs):
        """Initialize NowPlayingView with audio player reference."""
        super().__init__(**kwargs)
        self.audio_player = audio_player
        self._update_timer = None
        self._vu_timer = None
        self.vu_peak_left = 0.0
        self.vu_peak_right = 0.0
        self.vu_peak_decay = 0.95

    def compose(self) -> ComposeResult:
        """Compose the now playing view with track info."""
        with Vertical():
            yield Static("♪", classes="music-icon")
            yield Static("No track playing", id="np-title", classes="track-title")
            yield Static("Artist: Unknown", id="np-artist", classes="track-metadata")
            yield Static("Album: Unknown", id="np-album", classes="track-metadata")
            
            with Container(classes="progress-container"):
                yield Static("0:00 / 0:00", id="np-time", classes="time-display")
                yield Static(self._render_volume_bar(0.7), id="np-volume", classes="volume-display")
                yield Static("State: Stopped", id="np-state", classes="state-display")
            
            yield Static(self._render_vu_meters(0.0, 0.0), id="np-vu-meters")

    def on_mount(self) -> None:
        """Start update timer for real-time progress updates."""
        self._update_timer = self.set_interval(1.0, self._update_progress)
        self._vu_timer = self.set_interval(1.0 / 60, self._update_vu_meters)
        self._update_progress()
    
    def _update_progress(self) -> None:
        """Update all display widgets with current playback information."""
        current_track = self.audio_player.get_current_track()
        current_position = self.audio_player.get_position()
        volume_level = self.audio_player.get_volume()
        playback_state = self.audio_player.get_state()
        
        if current_track:
            title_widget = self.query_one("#np-title", Static)
            title_widget.update(current_track.title)
            
            artist_widget = self.query_one("#np-artist", Static)
            artist_widget.update(f"Artist: {current_track.artist}")
            
            album_widget = self.query_one("#np-album", Static)
            album_widget.update(f"Album: {current_track.album}")
            
            total_duration = current_track.duration_seconds
            
            current_time_str = self._format_time(current_position)
            total_time_str = self._format_time(total_duration)
            time_widget = self.query_one("#np-time", Static)
            time_widget.update(f"{current_time_str} / {total_time_str}")
        else:
            title_widget = self.query_one("#np-title", Static)
            title_widget.update("No track playing")
            
            artist_widget = self.query_one("#np-artist", Static)
            artist_widget.update("Artist: Unknown")
            
            album_widget = self.query_one("#np-album", Static)
            album_widget.update("Album: Unknown")
            
            time_widget = self.query_one("#np-time", Static)
            time_widget.update("0:00 / 0:00")
        
        volume_widget = self.query_one("#np-volume", Static)
        volume_widget.update(self._render_volume_bar(volume_level))
        
        state_widget = self.query_one("#np-state", Static)
        state_widget.update(f"State: {playback_state.value.capitalize()}")
    
    def _render_volume_bar(self, volume_level: float) -> Text:
        """Render a visual volume bar.
        
        Args:
            volume_level: Volume level from 0.0 to 1.0
            
        Returns:
            Rich Text object with volume bar visualization
        """
        result = Text()
        
        bar_width = 30
        filled_bars = int(volume_level * bar_width)
        percentage = int(volume_level * 100)
        
        result.append("Volume: ", style="#888888")
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
        result.append(f"{percentage}%", style="#ff8c00 bold")
        
        return result
    
    def _format_time(self, seconds: float) -> str:
        """Convert seconds to MM:SS format.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string in MM:SS format
        """
        if seconds < 0:
            seconds = 0
        
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def _calculate_rms(self, audio_data: np.ndarray) -> tuple[float, float]:
        """Calculate RMS levels for left and right channels."""
        if audio_data is None or len(audio_data) == 0:
            return 0.0, 0.0
        
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        if len(audio_data) % 2 != 0:
            audio_data = audio_data[:-1]
        
        stereo = audio_data.reshape(-1, 2)
        left = stereo[:, 0]
        right = stereo[:, 1]
        
        rms_left = np.sqrt(np.mean(left ** 2))
        rms_right = np.sqrt(np.mean(right ** 2))
        
        rms_left = min(1.0, rms_left * 3.0)
        rms_right = min(1.0, rms_right * 3.0)
        
        return rms_left, rms_right
    
    def _render_vu_meters(self, left_level: float, right_level: float) -> Text:
        """Render horizontal VU meters with peak hold."""
        result = Text()
        
        meter_width = 40
        
        left_bars = int(left_level * meter_width)
        right_bars = int(right_level * meter_width)
        
        peak_left_pos = int(self.vu_peak_left * meter_width)
        peak_right_pos = int(self.vu_peak_right * meter_width)
        
        result.append("L │", style="#888888")
        for i in range(meter_width):
            if i < left_bars:
                if i < meter_width * 0.7:
                    result.append("█", style="#cc5500")
                elif i < meter_width * 0.85:
                    result.append("█", style="#ff8c00")
                else:
                    result.append("█", style="#ffb347")
            elif i == peak_left_pos:
                result.append("│", style="#ffffff")
            else:
                result.append("─", style="#333333")
        result.append(f"│ {int(left_level * 100):3d}%\n", style="#888888")
        
        result.append("R │", style="#888888")
        for i in range(meter_width):
            if i < right_bars:
                if i < meter_width * 0.7:
                    result.append("█", style="#cc5500")
                elif i < meter_width * 0.85:
                    result.append("█", style="#ff8c00")
                else:
                    result.append("█", style="#ffb347")
            elif i == peak_right_pos:
                result.append("│", style="#ffffff")
            else:
                result.append("─", style="#333333")
        result.append(f"│ {int(right_level * 100):3d}%", style="#888888")
        
        return result
    
    def _update_vu_meters(self) -> None:
        """Update VU meters display."""
        try:
            if self.audio_player.is_playing():
                audio_buffer = self.audio_player.get_latest_audio_buffer()
                
                if audio_buffer is not None:
                    left_level, right_level = self._calculate_rms(audio_buffer)
                    
                    self.vu_peak_left = max(left_level, self.vu_peak_left * self.vu_peak_decay)
                    self.vu_peak_right = max(right_level, self.vu_peak_right * self.vu_peak_decay)
                    
                    vu_display = self._render_vu_meters(left_level, right_level)
                else:
                    self.vu_peak_left *= self.vu_peak_decay
                    self.vu_peak_right *= self.vu_peak_decay
                    vu_display = self._render_vu_meters(0.0, 0.0)
            else:
                self.vu_peak_left = 0.0
                self.vu_peak_right = 0.0
                vu_display = self._render_vu_meters(0.0, 0.0)
            
            vu_widget = self.query_one("#np-vu-meters", Static)
            vu_widget.update(vu_display)
        except Exception:
            pass
