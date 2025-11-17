from dataclasses import dataclass
import numpy as np


@dataclass
class VisualizerConfig:
    """Configuration for visualizer behavior.
    
    Defines parameters that control how the frequency visualizer operates,
    including update rates, display dimensions, and frequency range mappings.
    
    Attributes:
        update_rate: Visualization refresh rate in frames per second
        bar_count: Number of vertical bars to display
        max_bar_height: Maximum height of bars in terminal rows
        bass_range: Frequency range for bass (Hz), as (min, max) tuple
        mid_range: Frequency range for mid frequencies (Hz), as (min, max) tuple
        high_range: Frequency range for high frequencies (Hz), as (min, max) tuple
        smoothing_factor: Temporal smoothing coefficient (0-1), higher = smoother
    """
    update_rate: int = 20
    bar_count: int = 60
    max_bar_height: int = 20
    bass_range: tuple[int, int] = (20, 250)
    mid_range: tuple[int, int] = (250, 4000)
    high_range: tuple[int, int] = (4000, 20000)
    smoothing_factor: float = 0.3


@dataclass
class FrequencyBands:
    """Frequency amplitude data for visualization.
    
    Stores frequency amplitude data separated into bass, mid, and high ranges
    for real-time audio visualization.
    
    Attributes:
        bass: Amplitude array for bass frequencies (20-250 Hz)
        mid: Amplitude array for mid frequencies (250-4000 Hz)
        high: Amplitude array for high frequencies (4000-20000 Hz)
        timestamp: Time of capture in seconds
    """
    bass: np.ndarray
    mid: np.ndarray
    high: np.ndarray
    timestamp: float
    
    def get_all_bands(self) -> np.ndarray:
        """Concatenate all frequency bands into a single array.
        
        Returns:
            Combined array containing bass, mid, and high frequency data
        """
        return np.concatenate([self.bass, self.mid, self.high])
    
    def normalize(self, max_value: float = 1.0) -> 'FrequencyBands':
        """Normalize all bands to a maximum value.
        
        Scales all amplitude values proportionally so that the maximum
        amplitude across all bands equals max_value.
        
        Args:
            max_value: Target maximum amplitude value (default: 1.0)
            
        Returns:
            New FrequencyBands instance with normalized amplitudes
        """
        max_amp = max(self.bass.max(), self.mid.max(), self.high.max())
        if max_amp > 0:
            scale = max_value / max_amp
            return FrequencyBands(
                bass=self.bass * scale,
                mid=self.mid * scale,
                high=self.high * scale,
                timestamp=self.timestamp
            )
        return self
