import pygame
import time
from typing import Optional, List
from models.track import Track
from models.playback import PlaybackState


class AudioPlayer:
    """Singleton service for audio playback management."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.music.set_endevent(pygame.USEREVENT)
            
            self._current_track: Optional[Track] = None
            self._playlist: List[Track] = []
            self._current_index: int = -1
            self._volume: float = 0.7
            self._state: PlaybackState = PlaybackState.STOPPED
            self._start_time: float = 0
            self._pause_position: float = 0
            
            pygame.mixer.music.set_volume(self._volume)
            self._initialized = True
    
    def play(self, track: Track) -> None:
        """Load and play an audio file."""
        try:
            pygame.mixer.music.load(track.file_path)
            pygame.mixer.music.play()
            
            self._current_track = track
            self._state = PlaybackState.PLAYING
            self._start_time = time.time()
            self._pause_position = 0
            
            if self._playlist and track in self._playlist:
                self._current_index = self._playlist.index(track)
        except Exception:
            self._state = PlaybackState.STOPPED
            self._current_track = None
            raise
    
    def pause(self) -> None:
        """Pause playback."""
        if self._state == PlaybackState.PLAYING:
            pygame.mixer.music.pause()
            self._state = PlaybackState.PAUSED
            self._pause_position = time.time() - self._start_time
    
    def resume(self) -> None:
        """Resume playback from paused state."""
        if self._state == PlaybackState.PAUSED:
            pygame.mixer.music.unpause()
            self._state = PlaybackState.PLAYING
            self._start_time = time.time() - self._pause_position
    
    def stop(self) -> None:
        """Stop playback and reset position."""
        pygame.mixer.music.stop()
        self._state = PlaybackState.STOPPED
        self._start_time = 0
        self._pause_position = 0
    
    def next_track(self) -> None:
        """Skip to next track in playlist."""
        if not self._playlist:
            return
        
        if self._current_index < len(self._playlist) - 1:
            self._current_index += 1
            next_track = self._playlist[self._current_index]
            self.play(next_track)
        else:
            self.stop()
    
    def previous_track(self) -> None:
        """Skip to previous track in playlist."""
        if not self._playlist:
            return
        
        current_position = self.get_position()
        
        if current_position > 3.0:
            current_track = self._playlist[self._current_index]
            self.play(current_track)
        elif self._current_index > 0:
            self._current_index -= 1
            prev_track = self._playlist[self._current_index]
            self.play(prev_track)
    
    def set_volume(self, level: float) -> None:
        """Set volume level (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, level))
        pygame.mixer.music.set_volume(self._volume)
    
    def increase_volume(self, amount: float = 0.05) -> None:
        """Increase volume by specified amount."""
        self.set_volume(self._volume + amount)
    
    def decrease_volume(self, amount: float = 0.05) -> None:
        """Decrease volume by specified amount."""
        self.set_volume(self._volume - amount)
    
    def get_state(self) -> PlaybackState:
        """Return current playback state."""
        return self._state
    
    def get_current_track(self) -> Optional[Track]:
        """Return currently playing track or None."""
        return self._current_track
    
    def get_position(self) -> float:
        """Return current playback position in seconds."""
        if self._state == PlaybackState.STOPPED:
            return 0.0
        elif self._state == PlaybackState.PAUSED:
            return self._pause_position
        elif self._state == PlaybackState.PLAYING:
            return time.time() - self._start_time
        return 0.0
    
    def get_volume(self) -> float:
        """Return current volume level (0.0 to 1.0)."""
        return self._volume
    
    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._state == PlaybackState.PLAYING
    
    def set_playlist(self, tracks: List[Track], start_index: int = 0) -> None:
        """Set current playlist and starting track index."""
        self._playlist = tracks
        self._current_index = max(0, min(start_index, len(tracks) - 1)) if tracks else -1
    
    def get_playlist(self) -> List[Track]:
        """Return current playlist."""
        return self._playlist
    
    def list_audio_devices(self) -> List[str]:
        """List available audio output devices.
        
        Currently returns system default only.
        TODO: Integrate sounddevice library for full device enumeration.
        """
        return ["System Default"]
    
    def set_audio_device(self, device_name: str) -> None:
        """Set audio output device.
        
        Currently a stub for future implementation.
        TODO: Integrate sounddevice library for device selection.
        TODO: Implement device switching without interrupting playback.
        """
        pass
