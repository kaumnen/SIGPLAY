import numpy as np
import time
import logging
from typing import Optional
from models.frequency import FrequencyBands, VisualizerConfig

logger = logging.getLogger(__name__)


class SpectrumAnalyzer:
    """Real-time audio spectrum analyzer using FFT.
    
    Receives audio samples from AudioPlayer, performs FFT analysis,
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
    
    def start(self) -> None:
        """Start analyzing audio."""
        if self._is_active:
            return
        
        self._is_active = True
        logger.info(f"Spectrum analyzer started (sample_rate={self.sample_rate}, buffer_size={self.buffer_size})")
    
    def stop(self) -> None:
        """Stop audio analysis."""
        if not self._is_active:
            return
        
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
    
    def get_frequency_bands(self, audio_buffer: Optional[np.ndarray] = None) -> FrequencyBands:
        """Get current frequency band amplitudes.
        
        Args:
            audio_buffer: Audio samples to analyze (int16 format from miniaudio)
        
        Returns:
            FrequencyBands object with bass, mid, high arrays
        """
        if audio_buffer is None or len(audio_buffer) == 0:
            return FrequencyBands(
                bass=np.zeros(self._bass_bins[1] - self._bass_bins[0]),
                mid=np.zeros(self._mid_bins[1] - self._mid_bins[0]),
                high=np.zeros(self._high_bins[1] - self._high_bins[0]),
                timestamp=time.time()
            )
        
        if len(audio_buffer) > 1:
            audio_data = audio_buffer[::audio_buffer.shape[0] // self.buffer_size] if len(audio_buffer) > self.buffer_size else audio_buffer
        else:
            audio_data = audio_buffer
        
        if len(audio_data) < self.buffer_size:
            audio_data = np.pad(audio_data, (0, self.buffer_size - len(audio_data)))
        elif len(audio_data) > self.buffer_size:
            audio_data = audio_data[:self.buffer_size]
        
        audio_data = audio_data.astype(np.float32) / 32768.0
        
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
