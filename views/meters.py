import logging
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static
from textual.reactive import var
from rich.text import Text

from services.audio_player import AudioPlayer

logger = logging.getLogger(__name__)

BYTE_STREAM_UPDATE_FPS = 60
BYTE_STREAM_NUM_LINES = 8
MIN_DISPLAY_WIDTH = 40
SCROLL_SPEED_MULTIPLIER = 2


class MetersView(Container):
    
    terminal_width = var(0)
    
    def __init__(self, audio_player: AudioPlayer, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.audio_player = audio_player
        self.animation_timer = None
        self.byte_offset = 0
    
    def compose(self) -> ComposeResult:
        yield Static(self._render_byte_stream(None), id="byte-stream-display")
    
    def on_mount(self) -> None:
        self.terminal_width = self.size.width
        self.animation_timer = self.set_interval(1.0 / BYTE_STREAM_UPDATE_FPS, self._update_byte_stream)
    
    def on_resize(self) -> None:
        self.terminal_width = self.size.width
    
    def _render_byte_stream(self, audio_bytes: bytes | None) -> Text:
        """Render actual audio bytes as hex stream."""
        result = Text()
        
        if not audio_bytes or len(audio_bytes) == 0:
            result.append("\n  [ NO AUDIO DATA ]\n", style="#333333")
            result.append("  Waiting for playback...\n", style="#555555")
            return result
        
        width = max(MIN_DISPLAY_WIDTH, self.terminal_width - 6)
        bytes_per_line = width // 3
        
        result.append("\n  LIVE AUDIO STREAM\n", style="#ff8c00 bold")
        result.append("  " + "─" * width + "\n", style="#cc5500")
        
        start_idx = self.byte_offset % len(audio_bytes)
        display_bytes = audio_bytes[start_idx:start_idx + bytes_per_line * BYTE_STREAM_NUM_LINES]
        
        if len(display_bytes) < bytes_per_line * BYTE_STREAM_NUM_LINES:
            display_bytes += audio_bytes[:bytes_per_line * BYTE_STREAM_NUM_LINES - len(display_bytes)]
        
        for line_idx in range(BYTE_STREAM_NUM_LINES):
            result.append("  ", style="#1a1a1a")
            line_start = line_idx * bytes_per_line
            line_end = line_start + bytes_per_line
            line_bytes = display_bytes[line_start:line_end]
            
            for i, byte in enumerate(line_bytes):
                hex_str = f"{byte:02X}"
                
                intensity = byte / 255.0
                if intensity > 0.7:
                    color = "#ff8c00"
                elif intensity > 0.4:
                    color = "#ffb347"
                else:
                    color = "#cc5500"
                
                result.append(hex_str, style=color)
                result.append(" ", style="#1a1a1a")
            
            result.append("\n")
        
        result.append("  " + "─" * width + "\n", style="#cc5500")
        result.append("  ", style="#1a1a1a")
        result.append(f"Offset: {self.byte_offset:08X}  |  ", style="#888888")
        result.append(f"Bytes/sec: {len(audio_bytes) * 60:,}", style="#ffb347")
        result.append("\n", style="#1a1a1a")
        
        return result
    
    def _update_byte_stream(self) -> None:
        """Update byte stream with actual audio data."""
        try:
            is_playing = self.audio_player.is_playing()
            audio_buffer = self.audio_player.get_latest_audio_buffer()
            
            if is_playing and audio_buffer is not None and len(audio_buffer) > 0:
                audio_bytes = audio_buffer.tobytes()
                
                width = max(MIN_DISPLAY_WIDTH, self.terminal_width - 10)
                bytes_per_line = width // 3
                scroll_speed = bytes_per_line * SCROLL_SPEED_MULTIPLIER
                
                self.byte_offset = (self.byte_offset + scroll_speed) % len(audio_bytes)
                
                display = self._render_byte_stream(audio_bytes)
            else:
                self.byte_offset = 0
                display = self._render_byte_stream(None)
            
            widget = self.query_one("#byte-stream-display", Static)
            widget.update(display)
            
        except Exception as e:
            logger.error(f"Error updating byte stream: {e}")
