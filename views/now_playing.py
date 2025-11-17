import numpy as np
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static
from rich.text import Text
from services.audio_player import AudioPlayer
from models.track import format_time

PROGRESS_UPDATE_INTERVAL = 1.0
VU_METER_UPDATE_FPS = 60
VU_METER_WIDTH = 40
VU_PEAK_DECAY = 0.95
RMS_AMPLIFICATION = 3.0


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
        self.vu_peak_decay = VU_PEAK_DECAY

    def compose(self) -> ComposeResult:
        """Compose the now playing view with track info."""
        with Vertical():
            yield Static("♪", classes="music-icon")
            yield Static("No track playing", id="np-title", classes="track-title")
            yield Static("Artist: Unknown", id="np-artist", classes="track-metadata")
            yield Static("Album: Unknown", id="np-album", classes="track-metadata")
            yield Static("0:00 / 0:00", id="np-time", classes="time-display")
            yield Static("State: Stopped", id="np-state", classes="state-display")
            yield Static(self._render_vu_meters(0.0, 0.0), id="np-vu-meters")

    def on_mount(self) -> None:
        """Start update timer for real-time progress updates."""
        self._update_timer = self.set_interval(PROGRESS_UPDATE_INTERVAL, self._update_progress)
        self._vu_timer = self.set_interval(1.0 / VU_METER_UPDATE_FPS, self._update_vu_meters)
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
            
            current_time_str = format_time(current_position)
            total_time_str = format_time(total_duration)
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
        
        state_widget = self.query_one("#np-state", Static)
        state_widget.update(f"State: {playback_state.value.capitalize()}")
    
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
        
        rms_left = min(1.0, rms_left * RMS_AMPLIFICATION)
        rms_right = min(1.0, rms_right * RMS_AMPLIFICATION)
        
        return rms_left, rms_right
    
    def _render_vu_meters(self, left_level: float, right_level: float) -> Text:
        """Render horizontal VU meters with peak hold."""
        result = Text()
        
        left_bars = int(left_level * VU_METER_WIDTH)
        right_bars = int(right_level * VU_METER_WIDTH)
        
        peak_left_pos = int(self.vu_peak_left * VU_METER_WIDTH)
        peak_right_pos = int(self.vu_peak_right * VU_METER_WIDTH)
        
        result.append("L │", style="#888888")
        for i in range(VU_METER_WIDTH):
            if i < left_bars:
                if i < VU_METER_WIDTH * 0.7:
                    result.append("█", style="#cc5500")
                elif i < VU_METER_WIDTH * 0.85:
                    result.append("█", style="#ff8c00")
                else:
                    result.append("█", style="#ffb347")
            elif i == peak_left_pos:
                result.append("│", style="#ffffff")
            else:
                result.append("─", style="#333333")
        result.append(f"│ {int(left_level * 100):3d}%\n", style="#888888")
        
        result.append("R │", style="#888888")
        for i in range(VU_METER_WIDTH):
            if i < right_bars:
                if i < VU_METER_WIDTH * 0.7:
                    result.append("█", style="#cc5500")
                elif i < VU_METER_WIDTH * 0.85:
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
