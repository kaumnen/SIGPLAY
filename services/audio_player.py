import miniaudio
import time
import threading
import numpy as np
from typing import Optional, List
from pathlib import Path
import logging

from models.track import Track
from models.playback import PlaybackState

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Singleton service for audio playback management."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            try:
                logger.info("Initializing audio player...")
                
                self._current_track: Optional[Track] = None
                self._playlist: List[Track] = []
                self._current_index: int = -1
                self._volume: float = 0.3
                self._state: PlaybackState = PlaybackState.STOPPED
                self._start_time: float = 0
                self._pause_position: float = 0
                self._track_ended_naturally: bool = False
                
                self._device: Optional[miniaudio.PlaybackDevice] = None
                self._stream_generator = None
                self._stop_playback = threading.Event()
                self._pause_event = threading.Event()
                
                self._audio_buffer_lock = threading.Lock()
                self._latest_audio_buffer: Optional[np.ndarray] = None
                
                self._initialized = True
                
                logger.info("Audio player initialized successfully")
                
            except Exception as e:
                error_msg = str(e) if str(e) else "Unknown audio error"
                logger.critical(f"Failed to initialize audio device: {error_msg}")
                raise RuntimeError(
                    f"🔇 No audio device detected\n\n"
                    f"SIGPLAY needs an audio output device to play music.\n"
                    f"Please check that:\n"
                    f"  • Your audio device is connected and powered on\n"
                    f"  • Audio drivers are properly installed\n"
                    f"  • The device is not being used exclusively by another app\n\n"
                    f"Technical details: {error_msg}"
                ) from e
    
    def play(self, track: Track) -> None:
        """Load and play an audio file.
        
        Args:
            track: Track object to play.
            
        Raises:
            FileNotFoundError: If audio file doesn't exist.
            RuntimeError: If file cannot be loaded or played.
        """
        file_path = Path(track.file_path)
        
        if not file_path.exists():
            logger.error(f"Audio file not found: {file_path}")
            self._state = PlaybackState.STOPPED
            self._current_track = None
            raise FileNotFoundError(
                f"Audio file not found: {file_path.name}\n\n"
                f"The file may have been moved or deleted."
            )
        
        try:
            self.stop()
            
            logger.info(f"Loading track: {track.title} by {track.artist}")
            
            self._stream_generator = miniaudio.stream_file(
                str(file_path),
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=2,
                sample_rate=44100
            )
            
            def audio_generator():
                num_frames = yield b''
                
                while not self._stop_playback.is_set():
                    if self._pause_event.is_set():
                        num_frames = yield b'\x00' * (num_frames * 2 * 2)
                        continue
                    
                    try:
                        audio_data = self._stream_generator.send(num_frames)
                        
                        audio_array = np.frombuffer(audio_data, dtype=np.int16)
                        
                        with self._audio_buffer_lock:
                            self._latest_audio_buffer = audio_array.copy()
                        
                        volume_adjusted = (audio_array * self._volume).astype(np.int16)
                        
                        num_frames = yield volume_adjusted.tobytes()
                        
                    except StopIteration:
                        logger.debug("Reached end of audio file")
                        self._state = PlaybackState.STOPPED
                        self._track_ended_naturally = True
                        num_frames = yield b'\x00' * (num_frames * 2 * 2)
                        break
            
            self._device = miniaudio.PlaybackDevice(
                sample_rate=44100,
                nchannels=2,
                output_format=miniaudio.SampleFormat.SIGNED16
            )
            
            gen = audio_generator()
            next(gen)
            self._device.start(gen)
            
            self._current_track = track
            self._state = PlaybackState.PLAYING
            self._start_time = time.time()
            self._pause_position = 0
            self._track_ended_naturally = False
            
            if self._playlist and track in self._playlist:
                self._current_index = self._playlist.index(track)
            
            self._stop_playback.clear()
            self._pause_event.clear()
            
            logger.debug(f"Successfully started playback of {track.title}")
            
        except miniaudio.MiniaudioError as e:
            logger.error(f"miniaudio error loading {file_path}: {e}")
            self._state = PlaybackState.STOPPED
            self._current_track = None
            raise RuntimeError(
                f"Cannot play audio file: {file_path.name}\n\n"
                f"The file may be corrupted or in an unsupported format.\n"
                f"Technical details: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error playing {file_path}: {type(e).__name__}: {e}")
            self._state = PlaybackState.STOPPED
            self._current_track = None
            raise RuntimeError(
                f"Failed to play {file_path.name}: {type(e).__name__}"
            ) from e
    
    def pause(self) -> None:
        """Pause playback."""
        if self._state == PlaybackState.PLAYING:
            self._pause_event.set()
            self._state = PlaybackState.PAUSED
            self._pause_position = time.time() - self._start_time
    
    def resume(self) -> None:
        """Resume playback from paused state."""
        if self._state == PlaybackState.PAUSED:
            self._pause_event.clear()
            self._state = PlaybackState.PLAYING
            self._start_time = time.time() - self._pause_position
    
    def stop(self) -> None:
        """Stop playback and reset position."""
        self._stop_playback.set()
        self._track_ended_naturally = False
        
        if self._device:
            try:
                self._device.stop()
                self._device.close()
            except Exception as e:
                logger.debug(f"Error stopping device: {e}")
            self._device = None
        
        self._stream_generator = None
        self._state = PlaybackState.STOPPED
        self._start_time = 0
        self._pause_position = 0
    
    def next_track(self) -> None:
        """Skip to next track in playlist.
        
        Automatically skips corrupted files and continues to next valid track.
        """
        if not self._playlist:
            logger.debug("No playlist set, cannot skip to next track")
            return
        
        if self._current_index < len(self._playlist) - 1:
            self._current_index += 1
            next_track = self._playlist[self._current_index]
            
            try:
                self.play(next_track)
            except (FileNotFoundError, RuntimeError) as e:
                logger.warning(f"Failed to play next track, skipping: {e}")
                self.next_track()
        else:
            logger.debug("Reached end of playlist")
            self.stop()
    
    def previous_track(self) -> None:
        """Skip to previous track in playlist.
        
        Restarts current track if position > 3 seconds, otherwise goes to previous.
        Automatically skips corrupted files.
        """
        if not self._playlist:
            logger.debug("No playlist set, cannot skip to previous track")
            return
        
        current_position = self.get_position()
        
        if current_position > 3.0:
            current_track = self._playlist[self._current_index]
            try:
                self.play(current_track)
            except (FileNotFoundError, RuntimeError) as e:
                logger.warning(f"Failed to restart track: {e}")
        elif self._current_index > 0:
            self._current_index -= 1
            prev_track = self._playlist[self._current_index]
            try:
                self.play(prev_track)
            except (FileNotFoundError, RuntimeError) as e:
                logger.warning(f"Failed to play previous track, skipping: {e}")
                self.previous_track()
    
    def set_volume(self, level: float) -> None:
        """Set volume level (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, level))
    
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
    
    def get_latest_audio_buffer(self) -> Optional[np.ndarray]:
        """Get the most recent audio buffer.
        
        Returns:
            Numpy array of audio samples or None if no audio playing
        """
        with self._audio_buffer_lock:
            return self._latest_audio_buffer.copy() if self._latest_audio_buffer is not None else None
    
    def track_ended_naturally(self) -> bool:
        """Check if track ended naturally (not manually stopped)."""
        return self._track_ended_naturally
    
    def list_audio_devices(self) -> List[str]:
        """List available audio output devices."""
        try:
            devices = miniaudio.Devices()
            return [device['name'] for device in devices.get_playbacks()]
        except Exception as e:
            logger.error(f"Error listing audio devices: {e}")
            return ["System Default"]
    
    def set_audio_device(self, device_name: str) -> None:
        """Set audio output device.
        
        Currently a stub for future implementation.
        TODO: Implement device switching without interrupting playback.
        """
        pass
