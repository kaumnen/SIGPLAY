import logging
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual.reactive import var
from rich.text import Text
import numpy as np

from services.audio_player import AudioPlayer, SAMPLE_RATE, NUM_CHANNELS
from styles import COLOR_BASS, COLOR_PRIMARY, COLOR_HIGHLIGHT, COLOR_MUTED, COLOR_DIM, COLOR_INACTIVE

logger = logging.getLogger(__name__)

BYTE_STREAM_UPDATE_FPS = 60
BYTE_STREAM_NUM_LINES = 6
MIN_DISPLAY_WIDTH = 40
SCROLL_SPEED_MULTIPLIER = 2
BYTES_PER_SAMPLE = 2


class MetersView(Container):
    
    terminal_width = var(0)
    
    def __init__(self, audio_player: AudioPlayer, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.audio_player = audio_player
        self.animation_timer = None
        self.byte_offset = 0
        self.total_bytes_streamed = 0
        self.peak_amplitude = 0
        self.rms_level = 0.0
        self._last_track_path: str | None = None
    
    def reset_stats(self) -> None:
        """Reset all stats for a new track."""
        self.byte_offset = 0
        self.total_bytes_streamed = 0
        self.peak_amplitude = 0
        self.rms_level = 0.0
    
    def compose(self) -> ComposeResult:
        yield Static(self._render_byte_stream(None), id="byte-stream-display")
    
    def on_mount(self) -> None:
        self.terminal_width = self.size.width
        self.animation_timer = self.set_interval(1.0 / BYTE_STREAM_UPDATE_FPS, self._update_byte_stream)
    
    def on_resize(self) -> None:
        self.terminal_width = self.size.width
    
    def _render_byte_stream(self, audio_bytes: bytes | None, audio_array: np.ndarray | None = None) -> Text:
        """Render actual audio bytes as hex stream with real-time stats."""
        result = Text()
        bg_style = "#1a1a1a"
        
        if not audio_bytes or len(audio_bytes) == 0:
            result.append("\n  [ NO AUDIO DATA ]\n", style=COLOR_INACTIVE)
            result.append("  Waiting for playback...\n", style=COLOR_DIM)
            return result
        
        width = max(MIN_DISPLAY_WIDTH, self.terminal_width - 6)
        bytes_per_line = width // 3
        actual_bytes_per_sec = SAMPLE_RATE * NUM_CHANNELS * BYTES_PER_SAMPLE
        
        result.append("\n", style=bg_style)
        
        if audio_array is not None and len(audio_array) > 0:
            result.append("  ", style=bg_style)
            waveform = self._render_waveform(audio_array, width - 4)
            result.append(waveform)
            result.append("\n\n")
        
        left_info = f"Offset: {self.total_bytes_streamed:08X}  │  {SAMPLE_RATE}Hz {NUM_CHANNELS}ch"
        right_info = f"{actual_bytes_per_sec:,} B/s"
        padding = width - len(left_info) - len(right_info)
        
        result.append("  ", style=bg_style)
        result.append(f"Offset: {self.total_bytes_streamed:08X}", style=COLOR_MUTED)
        result.append("  │  ", style=COLOR_DIM)
        result.append(f"{SAMPLE_RATE}Hz {NUM_CHANNELS}ch", style=COLOR_BASS)
        result.append(" " * max(1, padding), style=bg_style)
        result.append(f"{actual_bytes_per_sec:,} B/s", style=COLOR_HIGHLIGHT)
        result.append("\n")
        
        if audio_array is not None and len(audio_array) > 0:
            rms_db = 20 * np.log10(self.rms_level / 32768) if self.rms_level > 0 else -60
            left_stats = f"Peak: {self.peak_amplitude:5d}  │  RMS: {rms_db:+.1f}dB"
            right_stats = f"Buffer: {len(audio_array):,} samples"
            stats_padding = width - len(left_stats) - len(right_stats)
            
            result.append("  ", style=bg_style)
            result.append(f"Peak: {self.peak_amplitude:5d}", style=COLOR_PRIMARY)
            result.append("  │  ", style=COLOR_DIM)
            result.append(f"RMS: {rms_db:+.1f}dB", style=COLOR_HIGHLIGHT)
            result.append(" " * max(1, stats_padding), style=bg_style)
            result.append(f"Buffer: {len(audio_array):,} samples", style=COLOR_BASS)
            result.append("\n")
        
        result.append("  " + "─" * width + "\n", style=COLOR_BASS)
        
        start_idx = self.byte_offset % len(audio_bytes)
        display_bytes = audio_bytes[start_idx:start_idx + bytes_per_line * BYTE_STREAM_NUM_LINES]
        
        if len(display_bytes) < bytes_per_line * BYTE_STREAM_NUM_LINES:
            display_bytes += audio_bytes[:bytes_per_line * BYTE_STREAM_NUM_LINES - len(display_bytes)]
        
        for line_idx in range(BYTE_STREAM_NUM_LINES):
            result.append("  ", style=bg_style)
            line_start = line_idx * bytes_per_line
            line_end = line_start + bytes_per_line
            line_bytes = display_bytes[line_start:line_end]
            
            for i, byte in enumerate(line_bytes):
                hex_str = f"{byte:02X}"
                
                intensity = byte / 255.0
                if intensity > 0.7:
                    color = COLOR_PRIMARY
                elif intensity > 0.4:
                    color = COLOR_HIGHLIGHT
                else:
                    color = COLOR_BASS
                
                result.append(hex_str, style=color)
                result.append(" ", style=bg_style)
            
            result.append("\n")
        
        return result
    
    def _render_waveform(self, audio_array: np.ndarray, width: int) -> Text:
        """Render a simple ASCII waveform from audio samples."""
        result = Text()
        
        if len(audio_array) < width:
            return result
        
        chunk_size = len(audio_array) // width
        waveform_chars = "▁▂▃▄▅▆▇█"
        
        for i in range(width):
            start = i * chunk_size
            end = start + chunk_size
            chunk = audio_array[start:end]
            
            amplitude = np.abs(chunk).mean() / 32768.0
            char_idx = min(int(amplitude * len(waveform_chars) * 4), len(waveform_chars) - 1)
            char = waveform_chars[char_idx]
            
            if amplitude > 0.5:
                color = COLOR_PRIMARY
            elif amplitude > 0.2:
                color = COLOR_HIGHLIGHT
            else:
                color = COLOR_BASS
            
            result.append(char, style=color)
        
        return result
    
    def _update_byte_stream(self) -> None:
        """Update byte stream with actual audio data."""
        try:
            is_playing = self.audio_player.is_playing()
            audio_buffer = self.audio_player.get_latest_audio_buffer()
            
            current_track = self.audio_player.get_current_track()
            current_path = current_track.file_path if current_track else None
            if current_path != self._last_track_path:
                self.reset_stats()
                self._last_track_path = current_path
            
            if is_playing and audio_buffer is not None and len(audio_buffer) > 0:
                audio_bytes = audio_buffer.tobytes()
                
                width = max(MIN_DISPLAY_WIDTH, self.terminal_width - 10)
                bytes_per_line = width // 3
                scroll_speed = bytes_per_line * SCROLL_SPEED_MULTIPLIER
                
                self.byte_offset = (self.byte_offset + scroll_speed) % len(audio_bytes)
                self.total_bytes_streamed += len(audio_bytes)
                
                self.peak_amplitude = int(np.abs(audio_buffer).max())
                self.rms_level = float(np.sqrt(np.mean(audio_buffer.astype(np.float64) ** 2)))
                
                display = self._render_byte_stream(audio_bytes, audio_buffer)
            else:
                self.byte_offset = 0
                self.total_bytes_streamed = 0
                self.peak_amplitude = 0
                self.rms_level = 0.0
                display = self._render_byte_stream(None)
            
            widget = self.query_one("#byte-stream-display", Static)
            widget.update(display)
            
        except Exception as e:
            logger.error(f"Error updating byte stream: {e}")
