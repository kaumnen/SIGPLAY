# Design Document

## Overview

The Frequency Visualizer feature transforms SIGPLAY's placeholder visualizer into a real-time frequency spectrum analyzer. The system captures audio samples during playback, performs Fast Fourier Transform (FFT) analysis to extract frequency content, and renders vertical bars that react to bass, mid, and high-frequency amplitudes. The design prioritizes performance to ensure smooth visualization without impacting audio playback quality.

The architecture introduces a new Spectrum Analyzer component that bridges the audio playback system and the visualization display. Since pygame.mixer does not provide direct access to the audio stream being played, the design evaluates alternative approaches including parallel audio capture with sounddevice or switching to a more analysis-friendly playback library.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SIGPLAY Application                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   VisualizerView                       │ │
│  │  - Renders frequency bars                             │ │
│  │  - Updates display at 20 FPS                          │ │
│  │  - Handles terminal resize                            │ │
│  └──────────────────┬─────────────────────────────────────┘ │
│                     │ get_frequency_data()                  │
│  ┌──────────────────▼─────────────────────────────────────┐ │
│  │              SpectrumAnalyzer                          │ │
│  │  - Captures audio samples                             │ │
│  │  - Performs FFT analysis                              │ │
│  │  - Maps to bass/mid/high bins                         │ │
│  │  - Normalizes amplitudes                              │ │
│  └──────────────────┬─────────────────────────────────────┘ │
│                     │ audio samples                         │
│  ┌──────────────────▼─────────────────────────────────────┐ │
│  │           Audio Capture Layer                          │ │
│  │  Option A: sounddevice loopback capture               │ │
│  │  Option B: miniaudio with analysis callback           │ │
│  │  Option C: pyaudio stream tap                         │ │
│  └──────────────────┬─────────────────────────────────────┘ │
│                     │                                       │
│  ┌──────────────────▼─────────────────────────────────────┐ │
│  │              AudioPlayer (pygame.mixer)                │ │
│  │  - Continues handling playback                         │ │
│  │  - No changes to existing functionality               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Audio Capture Strategy

After evaluating pygame.mixer's capabilities, it does not provide access to the audio stream for analysis. Three viable approaches:

**Option A: sounddevice Loopback (Recommended)**
- Use sounddevice to capture system audio output
- Requires system loopback device (available on most platforms)
- Pros: Non-invasive, works with existing pygame.mixer
- Cons: Platform-specific setup, may require user configuration

**Option B: Switch to miniaudio**
- Replace pygame.mixer with miniaudio for playback
- miniaudio provides callback access to audio buffers
- Pros: Direct buffer access, cross-platform, modern library
- Cons: Requires refactoring AudioPlayer class

**Option C: pyaudio Stream Tap**
- Use pyaudio to create a parallel audio stream
- Tap into the audio output for analysis
- Pros: Widely supported, mature library
- Cons: More complex setup, potential latency issues

**Design Decision: Start with Option A (sounddevice loopback), with Option B (miniaudio) as fallback if loopback proves unreliable.**

## Components and Interfaces

### SpectrumAnalyzer Class

**Responsibilities:**
- Capture audio samples from the audio stream
- Perform FFT analysis on audio buffers
- Map frequency bins to bass/mid/high ranges
- Normalize amplitude values for visualization
- Provide thread-safe access to frequency data

**Interface:**

```python
class SpectrumAnalyzer:
    def __init__(self, sample_rate: int = 44100, buffer_size: int = 2048):
        """Initialize spectrum analyzer.
        
        Args:
            sample_rate: Audio sample rate in Hz
            buffer_size: Number of samples per FFT window
        """
        
    def start(self) -> None:
        """Start capturing and analyzing audio."""
        
    def stop(self) -> None:
        """Stop audio capture and analysis."""
        
    def get_frequency_bands(self) -> FrequencyBands:
        """Get current frequency band amplitudes.
        
        Returns:
            FrequencyBands object with bass, mid, high arrays
        """
        
    def is_active(self) -> bool:
        """Check if analyzer is currently running."""
```

### FrequencyBands Data Class

**Responsibilities:**
- Store frequency amplitude data for bass, mid, and high ranges
- Provide convenient access to frequency band arrays

**Interface:**

```python
@dataclass
class FrequencyBands:
    bass: np.ndarray      # Shape: (n_bass_bins,), range 20-250 Hz
    mid: np.ndarray       # Shape: (n_mid_bins,), range 250-4000 Hz
    high: np.ndarray      # Shape: (n_high_bins,), range 4000-20000 Hz
    timestamp: float      # Time of capture
    
    def get_all_bands(self) -> np.ndarray:
        """Concatenate all bands into single array."""
        return np.concatenate([self.bass, self.mid, self.high])
    
    def normalize(self, max_value: float = 1.0) -> 'FrequencyBands':
        """Normalize all bands to max_value."""
```

### Updated VisualizerView Widget

**Responsibilities:**
- Initialize and manage SpectrumAnalyzer lifecycle
- Fetch frequency data at regular intervals
- Render frequency bars with baseline
- Handle terminal resize events
- Apply color gradients for frequency ranges

**Key Methods:**

```python
class VisualizerView(Container):
    def __init__(self, audio_player: AudioPlayer):
        """Initialize visualizer with audio player reference."""
        self.audio_player = audio_player
        self.spectrum_analyzer = SpectrumAnalyzer()
        self.bar_count = 60  # Adjusted based on terminal width
        
    def on_mount(self) -> None:
        """Start spectrum analyzer and visualization timer."""
        self.spectrum_analyzer.start()
        self.set_interval(1/20, self._update_visualization)  # 20 FPS
        
    def on_unmount(self) -> None:
        """Stop spectrum analyzer when view is hidden."""
        self.spectrum_analyzer.stop()
        
    def _update_visualization(self) -> None:
        """Fetch frequency data and update display."""
        if self.audio_player.is_playing():
            bands = self.spectrum_analyzer.get_frequency_bands()
            visualization = self._render_bars(bands)
        else:
            visualization = self._render_baseline_only()
        self.query_one("#visualizer-content").update(visualization)
        
    def _render_bars(self, bands: FrequencyBands) -> str:
        """Render frequency bars with baseline.
        
        Args:
            bands: Frequency band amplitudes
            
        Returns:
            String representation of visualization
        """
        
    def _render_baseline_only(self) -> str:
        """Render baseline with minimal bars when not playing."""
```

## Data Models

### FrequencyBands

```python
from dataclasses import dataclass
import numpy as np

@dataclass
class FrequencyBands:
    """Frequency amplitude data for visualization."""
    bass: np.ndarray
    mid: np.ndarray
    high: np.ndarray
    timestamp: float
    
    def get_all_bands(self) -> np.ndarray:
        return np.concatenate([self.bass, self.mid, self.high])
    
    def normalize(self, max_value: float = 1.0) -> 'FrequencyBands':
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
```

### VisualizerConfig

```python
@dataclass
class VisualizerConfig:
    """Configuration for visualizer behavior."""
    update_rate: int = 20  # FPS
    bar_count: int = 60
    max_bar_height: int = 20
    bass_range: tuple[int, int] = (20, 250)
    mid_range: tuple[int, int] = (250, 4000)
    high_range: tuple[int, int] = (4000, 20000)
    smoothing_factor: float = 0.3  # For temporal smoothing
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Frequency band coverage

*For any* FFT output with sample rate and buffer size, the mapped frequency bins should completely cover the bass (20-250 Hz), mid (250-4000 Hz), and high (4000-20000 Hz) ranges without gaps or overlaps.

**Validates: Requirements 1.2**

### Property 2: Amplitude normalization bounds

*For any* FrequencyBands object after normalization with max_value M, all amplitude values in bass, mid, and high arrays should be in the range [0, M].

**Validates: Requirements 5.5**

### Property 3: Visualization update rate bounds

*For any* sequence of visualization updates over a time period T, the update rate should be between 15 and 30 frames per second.

**Validates: Requirements 6.1, 6.2**

### Property 4: Baseline visibility

*For any* rendered visualization frame, the baseline should be present and positioned at the bottom of the display area.

**Validates: Requirements 2.1, 2.4**

### Property 5: Bar height proportionality

*For any* two frequency bins with amplitudes A1 and A2 where A1 > A2, the rendered bar height for A1 should be greater than or equal to the bar height for A2.

**Validates: Requirements 1.3, 2.3**

### Property 6: Playback independence

*For any* audio playback session, enabling or disabling the frequency visualizer should not affect the audio playback state, position, or quality.

**Validates: Requirements 6.3**

### Property 7: Zero amplitude baseline

*For any* audio buffer containing only silence (all samples near zero), the frequency visualizer should display bars at or near the baseline position.

**Validates: Requirements 7.1, 7.3**

### Property 8: Terminal resize adaptation

*For any* terminal width W, the visualizer should render a number of bars that fits within W without horizontal overflow.

**Validates: Requirements 7.4**

## Error Handling

### Audio Capture Failures

- **Loopback device not available**: Display error message suggesting manual audio routing setup, fall back to placeholder visualization
- **Permission denied**: Inform user about audio capture permissions, provide platform-specific guidance
- **Sample rate mismatch**: Automatically resample audio to match expected rate using scipy.signal.resample

### FFT Computation Errors

- **Insufficient buffer data**: Skip frame and wait for next buffer
- **NaN or Inf values**: Replace with zeros and log warning
- **Memory allocation failure**: Reduce buffer size and retry

### Performance Degradation

- **CPU usage exceeds 20%**: Reduce update rate from 20 FPS to 15 FPS
- **Frame drops detected**: Increase buffer size to reduce computation frequency
- **UI thread blocking**: Ensure spectrum analyzer runs in separate thread with proper synchronization

### Edge Cases

- **No audio playing**: Display static baseline with minimal bars
- **Paused playback**: Freeze visualization at last state or return to baseline after 2 seconds
- **Very quiet audio**: Apply minimum threshold to prevent flickering from noise floor
- **Terminal too narrow**: Reduce bar count to minimum of 20 bars

## Testing Strategy

### Unit Tests

- Test FFT bin mapping to frequency ranges (bass/mid/high)
- Test amplitude normalization with various input ranges
- Test FrequencyBands data class methods
- Test baseline rendering with zero amplitudes
- Test bar height calculation from amplitude values
- Test terminal width to bar count conversion

### Property-Based Tests

- **Property 1**: Generate random sample rates and buffer sizes, verify frequency coverage
- **Property 2**: Generate random amplitude arrays, normalize, verify bounds
- **Property 3**: Measure actual update rates over time windows
- **Property 4**: Parse rendered frames, verify baseline presence
- **Property 5**: Generate random amplitude pairs, verify height ordering
- **Property 6**: Start/stop visualizer during playback, verify playback state unchanged
- **Property 7**: Generate silent buffers, verify bars at baseline
- **Property 8**: Generate random terminal widths, verify no overflow

### Integration Tests

- Test SpectrumAnalyzer with real audio files
- Test VisualizerView updates during actual playback
- Test visualizer performance with various audio formats (MP3, FLAC, WAV)
- Test visualizer behavior across different terminal emulators
- Test graceful degradation when audio capture fails

### Performance Tests

- Measure CPU usage during visualization with various update rates
- Measure memory usage with different buffer sizes
- Verify no audio dropouts or glitches during visualization
- Test sustained operation over 30+ minute playback sessions

## Implementation Notes

### FFT Configuration

- **Buffer size**: 2048 samples provides good frequency resolution (21.5 Hz bins at 44.1kHz)
- **Window function**: Apply Hann window to reduce spectral leakage
- **Overlap**: Use 50% overlap between FFT windows for smoother updates

### Frequency Bin Mapping

```python
# Example bin calculation for 44100 Hz sample rate, 2048 buffer
freq_resolution = 44100 / 2048  # ~21.5 Hz per bin
bass_bins = range(int(20 / freq_resolution), int(250 / freq_resolution))
mid_bins = range(int(250 / freq_resolution), int(4000 / freq_resolution))
high_bins = range(int(4000 / freq_resolution), int(20000 / freq_resolution))
```

### Temporal Smoothing

Apply exponential moving average to reduce jitter:

```python
smoothed_amplitude = (1 - alpha) * previous_amplitude + alpha * current_amplitude
# alpha = 0.3 provides good balance between responsiveness and smoothness
```

### Bar Rendering

```python
def _render_bars(self, bands: FrequencyBands, max_height: int = 20) -> str:
    """Render frequency bars with baseline."""
    all_amplitudes = bands.get_all_bands()
    
    # Resample to match bar count
    bar_amplitudes = np.interp(
        np.linspace(0, len(all_amplitudes), self.bar_count),
        np.arange(len(all_amplitudes)),
        all_amplitudes
    )
    
    # Convert to bar heights
    bar_heights = (bar_amplitudes * max_height).astype(int)
    
    # Render from top to bottom
    lines = []
    for row in range(max_height, 0, -1):
        line = ""
        for height in bar_heights:
            if height >= row:
                line += "█"
            else:
                line += " "
        lines.append(line)
    
    # Add baseline
    baseline = "─" * self.bar_count
    lines.append(baseline)
    
    return "\n".join(lines)
```

### Color Gradient Application

Use Textual's Rich integration for color gradients:

```python
from rich.text import Text

def _apply_frequency_colors(self, bar_line: str, row: int) -> Text:
    """Apply color gradient based on frequency range."""
    text = Text()
    bass_count = len(self.bass_bins)
    mid_count = len(self.mid_bins)
    
    for i, char in enumerate(bar_line):
        if i < bass_count:
            color = "#cc5500"  # Darker orange for bass
        elif i < bass_count + mid_count:
            color = "#ff8c00"  # Medium orange for mid
        else:
            color = "#ffb347"  # Lighter amber for high
        text.append(char, style=f"color({color})")
    
    return text
```

## Dependencies

### New Dependencies

```toml
[project]
dependencies = [
    "textual[syntax]>=6.5.0",
    "textual-dev>=1.8.0",
    "pygame>=2.6.1",
    "mutagen>=1.47.0",
    "numpy>=1.26.0",           # FFT computation
    "sounddevice>=0.4.6",      # Audio capture (Option A)
    # "miniaudio>=1.59",       # Alternative playback (Option B)
    # "scipy>=1.11.0",         # Resampling if needed
]
```

### Library Evaluation

**numpy**: Required for FFT via `numpy.fft.rfft()`. Mature, fast, well-documented.

**sounddevice**: Recommended for audio capture. Cross-platform, Python-friendly wrapper around PortAudio. Supports loopback capture on most systems.

**miniaudio**: Alternative if sounddevice loopback proves problematic. Modern, lightweight, provides direct buffer access. Would require refactoring AudioPlayer.

**pedalboard**: Spotify's audio processing library. Powerful but may be overkill for basic FFT analysis. Consider for future enhancements (EQ, filters).

**scipy**: Only needed if audio resampling is required. Can be added later if sample rate issues arise.

## Future Enhancements

- Configurable frequency ranges and bar counts
- Multiple visualization modes (bars, waveform, spectrogram)
- Peak hold indicators for maximum amplitudes
- Stereo channel separation (left/right visualization)
- Beat detection and rhythm visualization
- Export visualization as animated GIF or video
- Integration with pedalboard for audio effects visualization
