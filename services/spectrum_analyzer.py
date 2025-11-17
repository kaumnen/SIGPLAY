import numpy as np
import sounddevice as sd
import threading
import time
import logging
from typing import Optional
from models.frequency import FrequencyBands, VisualizerConfig

logger = logging.getLogger(__name__)


class SpectrumAnalyzer:
    """Real-time audio spectrum analyzer using FFT.
    
    Captures audio samples from the system audio output, performs FFT analysis,
    and maps frequency bins to bass, mid, and high ranges for visualization.
    
    Attributes:
        sample_rate: Audio sample rate in Hz
        buffer_size: Number of samples per FFT window
        config: Visualizer configuration with frequency ranges
    """
    
    def __init__(self, sample_rate: int = 44100, buffer_size: int = 2048, 
                 config: Optional[VisualizerConfig] = None):
        """Initialize spectrum analyzer.
        
        Args:
            sample_rate: Audio sample rate in Hz (default: 44100)
            buffer_size: Number of samples per FFT window (default: 2048)
            config: Visualizer configuration (default: creates new VisualizerConfig)
        """
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.config = config or VisualizerConfig()
        
        self._audio_buffer = np.zeros(buffer_size, dtype=np.float32)
        self._buffer_lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        self._is_active = False
        
        self._previous_bands: Optional[FrequencyBands] = None
        
        self._freq_resolution = sample_rate / buffer_size
        self._bass_bins = self._get_frequency_bins(*self.config.bass_range)
        self._mid_bins = self._get_frequency_bins(*self.config.mid_range)
        self._high_bins = self._get_frequency_bins(*self.config.high_range)
        
        self._hann_window = np.hanning(buffer_size)
    
    def _get_frequency_bins(self, freq_min: int, freq_max: int) -> tuple[int, int]:
        """Calculate FFT bin indices for a frequency range.
        
        Args:
            freq_min: Minimum frequency in Hz
            freq_max: Maximum frequency in Hz
            
        Returns:
            Tuple of (start_bin, end_bin) indices
        """
        start_bin = int(freq_min / self._freq_resolution)
        end_bin = int(freq_max / self._freq_resolution)
        return (start_bin, end_bin)
    
    def _audio_callback(self, indata: np.ndarray, frames: int, 
                       time_info: dict, status: sd.CallbackFlags) -> None:
        """Callback function for audio stream.
        
        Args:
            indata: Input audio data
            frames: Number of frames
            time_info: Timing information
            status: Stream status flags
        """
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        with self._buffer_lock:
            if indata.shape[1] > 1:
                self._audio_buffer = indata[:, 0].flatten()
            else:
                self._audio_buffer = indata.flatten()
    
    def start(self) -> None:
        """Start capturing and analyzing audio.
        
        Raises:
            RuntimeError: If audio capture cannot be started
        """
        if self._is_active:
            return
        
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.buffer_size,
                channels=1,
                callback=self._audio_callback,
                dtype=np.float32
            )
            self._stream.start()
            self._is_active = True
            logger.info(f"Spectrum analyzer started (sample_rate={self.sample_rate}, buffer_size={self.buffer_size})")
            
        except sd.PortAudioError as e:
            error_msg = str(e).lower()
            
            if "device" in error_msg or "not found" in error_msg:
                logger.error("Audio loopback device not available. Please configure system audio routing.")
                raise RuntimeError(
                    "Audio capture device not available. "
                    "Please ensure your system supports audio loopback or configure virtual audio routing."
                ) from e
            
            elif "permission" in error_msg or "access" in error_msg:
                import platform
                system = platform.system()
                
                if system == "Darwin":
                    guidance = "On macOS, grant microphone permissions in System Preferences > Security & Privacy > Privacy > Microphone"
                elif system == "Linux":
                    guidance = "On Linux, ensure your user is in the 'audio' group and PulseAudio/PipeWire is configured correctly"
                elif system == "Windows":
                    guidance = "On Windows, grant microphone permissions in Settings > Privacy > Microphone"
                else:
                    guidance = "Please check your system's audio permissions"
                
                logger.error(f"Audio permission denied. {guidance}")
                raise RuntimeError(f"Audio capture permission denied. {guidance}") from e
            
            else:
                logger.error(f"Failed to start audio capture: {e}")
                raise RuntimeError(f"Failed to start audio capture: {e}") from e
        
        except Exception as e:
            logger.error(f"Unexpected error starting spectrum analyzer: {e}")
            raise RuntimeError(f"Failed to initialize spectrum analyzer: {e}") from e
    
    def stop(self) -> None:
        """Stop audio capture and analysis."""
        if not self._is_active:
            return
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        self._is_active = False
        logger.info("Spectrum analyzer stopped")
    
    def _compute_fft(self, audio_data: np.ndarray) -> np.ndarray:
        """Compute FFT on audio buffer with Hann window.
        
        Args:
            audio_data: Audio samples to analyze
            
        Returns:
            FFT magnitude spectrum
        """
        windowed_data = audio_data * self._hann_window
        
        fft_result = np.fft.rfft(windowed_data)
        
        magnitude = np.abs(fft_result)
        
        return magnitude
    
    def _extract_frequency_bands(self, fft_magnitude: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Extract bass, mid, and high frequency bands from FFT output.
        
        Args:
            fft_magnitude: FFT magnitude spectrum
            
        Returns:
            Tuple of (bass_amplitudes, mid_amplitudes, high_amplitudes)
        """
        bass_start, bass_end = self._bass_bins
        mid_start, mid_end = self._mid_bins
        high_start, high_end = self._high_bins
        
        bass = fft_magnitude[bass_start:bass_end]
        mid = fft_magnitude[mid_start:mid_end]
        high = fft_magnitude[high_start:high_end]
        
        return bass, mid, high
    
    def _normalize_amplitudes(self, bass: np.ndarray, mid: np.ndarray, 
                             high: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Normalize frequency amplitudes to 0-1 range.
        
        Args:
            bass: Bass frequency amplitudes
            mid: Mid frequency amplitudes
            high: High frequency amplitudes
            
        Returns:
            Tuple of normalized (bass, mid, high) arrays
        """
        bass = np.nan_to_num(bass, nan=0.0, posinf=0.0, neginf=0.0)
        mid = np.nan_to_num(mid, nan=0.0, posinf=0.0, neginf=0.0)
        high = np.nan_to_num(high, nan=0.0, posinf=0.0, neginf=0.0)
        
        max_amplitude = max(
            bass.max() if len(bass) > 0 else 0,
            mid.max() if len(mid) > 0 else 0,
            high.max() if len(high) > 0 else 0
        )
        
        if max_amplitude > 0:
            bass = bass / max_amplitude
            mid = mid / max_amplitude
            high = high / max_amplitude
        
        return bass, mid, high
    
    def _apply_smoothing(self, current_bands: FrequencyBands) -> FrequencyBands:
        """Apply exponential moving average for temporal smoothing.
        
        Args:
            current_bands: Current frequency band data
            
        Returns:
            Smoothed frequency bands
        """
        if self._previous_bands is None:
            self._previous_bands = current_bands
            return current_bands
        
        alpha = self.config.smoothing_factor
        
        smoothed_bass = (1 - alpha) * self._previous_bands.bass + alpha * current_bands.bass
        smoothed_mid = (1 - alpha) * self._previous_bands.mid + alpha * current_bands.mid
        smoothed_high = (1 - alpha) * self._previous_bands.high + alpha * current_bands.high
        
        smoothed_bands = FrequencyBands(
            bass=smoothed_bass,
            mid=smoothed_mid,
            high=smoothed_high,
            timestamp=current_bands.timestamp
        )
        
        self._previous_bands = smoothed_bands
        return smoothed_bands
    
    def get_frequency_bands(self) -> FrequencyBands:
        """Get current frequency band amplitudes.
        
        Returns:
            FrequencyBands object with bass, mid, high arrays
        """
        with self._buffer_lock:
            audio_data = self._audio_buffer.copy()
        
        fft_magnitude = self._compute_fft(audio_data)
        
        bass, mid, high = self._extract_frequency_bands(fft_magnitude)
        
        bass, mid, high = self._normalize_amplitudes(bass, mid, high)
        
        current_bands = FrequencyBands(
            bass=bass,
            mid=mid,
            high=high,
            timestamp=time.time()
        )
        
        smoothed_bands = self._apply_smoothing(current_bands)
        
        return smoothed_bands
    
    def is_active(self) -> bool:
        """Check if analyzer is currently running.
        
        Returns:
            True if analyzer is active, False otherwise
        """
        return self._is_active
