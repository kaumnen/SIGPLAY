from dataclasses import dataclass
import numpy as np


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
