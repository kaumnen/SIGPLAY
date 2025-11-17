# Implementation Plan

- [x] 1. Add required dependencies for audio analysis
  - Add numpy>=1.26.0 to pyproject.toml for FFT computation
  - Add sounddevice>=0.4.6 to pyproject.toml for audio capture
  - Run uv sync to install new dependencies
  - _Requirements: 5.1_

- [x] 2. Create FrequencyBands data model
  - Create models/frequency.py file
  - Implement FrequencyBands dataclass with bass, mid, high, timestamp fields
  - Implement get_all_bands() method to concatenate frequency arrays
  - Implement normalize() method with configurable max_value
  - _Requirements: 1.2, 5.5_

- [ ]* 2.1 Write property test for amplitude normalization
  - **Property 2: Amplitude normalization bounds**
  - **Validates: Requirements 5.5**

- [x] 3. Create VisualizerConfig data model
  - Add VisualizerConfig dataclass to models/frequency.py
  - Define configuration fields: update_rate, bar_count, max_bar_height, frequency ranges, smoothing_factor
  - Provide sensible defaults (20 FPS, 60 bars, 20 height, standard frequency ranges)
  - _Requirements: 1.4, 6.1, 6.2_

- [x] 4. Implement SpectrumAnalyzer core class
  - Create services/spectrum_analyzer.py file
  - Implement SpectrumAnalyzer class with __init__, start, stop, get_frequency_bands, is_active methods
  - Set up audio capture using sounddevice with loopback configuration
  - Implement audio buffer storage with thread-safe access
  - _Requirements: 3.1, 3.2, 4.3, 4.4_

- [x] 4.1 Implement FFT analysis in SpectrumAnalyzer
  - Import numpy.fft for FFT computation
  - Apply Hann window to audio buffer before FFT
  - Compute FFT using numpy.fft.rfft()
  - Calculate frequency resolution based on sample rate and buffer size
  - _Requirements: 3.2, 5.1, 5.3_

- [x] 4.2 Implement frequency bin mapping
  - Map FFT bins to bass range (20-250 Hz)
  - Map FFT bins to mid range (250-4000 Hz)
  - Map FFT bins to high range (4000-20000 Hz)
  - Extract amplitude values for each frequency range
  - Create and return FrequencyBands object with mapped data
  - _Requirements: 1.2, 3.3, 3.4, 3.5_

- [ ]* 4.3 Write property test for frequency band coverage
  - **Property 1: Frequency band coverage**
  - **Validates: Requirements 1.2**

- [x] 4.3 Implement amplitude normalization and smoothing
  - Normalize frequency amplitudes to consistent scale (0-1)
  - Implement exponential moving average for temporal smoothing (alpha=0.3)
  - Handle edge cases: NaN, Inf, zero amplitudes
  - _Requirements: 5.5, 5.3_

- [x] 4.4 Add error handling for audio capture
  - Handle loopback device not available error with fallback message
  - Handle permission denied errors with platform-specific guidance
  - Handle sample rate mismatches with logging
  - Implement graceful degradation when capture fails
  - _Requirements: 4.1, 4.2, 7.5_

- [ ]* 4.5 Write unit tests for SpectrumAnalyzer
  - Test FFT bin mapping with known sample rates
  - Test amplitude normalization with various input ranges
  - Test error handling for missing audio devices
  - Test thread-safe buffer access

- [ ] 5. Update VisualizerView for frequency visualization
  - Update views/visualizer.py to accept audio_player parameter in __init__
  - Initialize SpectrumAnalyzer instance in __init__
  - Update on_mount to start spectrum analyzer and set 20 FPS update interval
  - Add on_unmount method to stop spectrum analyzer when view is hidden
  - _Requirements: 1.1, 6.1, 6.3_

- [ ] 5.1 Implement frequency bar rendering
  - Implement _render_bars method that takes FrequencyBands and returns string
  - Resample frequency data to match bar_count using numpy.interp
  - Convert normalized amplitudes to bar heights (0 to max_bar_height)
  - Render bars from top to bottom with filled characters (█) based on height
  - Add horizontal baseline at bottom using box-drawing characters (─)
  - _Requirements: 1.1, 1.4, 2.1, 2.2, 2.3, 2.4_

- [ ]* 5.2 Write property test for baseline visibility
  - **Property 4: Baseline visibility**
  - **Validates: Requirements 2.1, 2.4**

- [ ]* 5.3 Write property test for bar height proportionality
  - **Property 5: Bar height proportionality**
  - **Validates: Requirements 1.3, 2.3**

- [ ] 5.4 Implement baseline-only rendering for non-playing state
  - Implement _render_baseline_only method
  - Display baseline with minimal bar heights when audio is not playing
  - Ensure visual consistency with active visualization
  - _Requirements: 7.1, 2.2_

- [ ]* 5.5 Write property test for zero amplitude baseline
  - **Property 7: Zero amplitude baseline**
  - **Validates: Requirements 7.1, 7.3**

- [ ] 5.6 Update visualization update loop
  - Modify _update_visualization to check if audio is playing
  - Fetch frequency bands from spectrum analyzer when playing
  - Call _render_bars with frequency data
  - Call _render_baseline_only when not playing or paused
  - Update visualizer-content widget with rendered output
  - _Requirements: 1.3, 3.1, 7.1, 7.2_

- [ ] 6. Implement frequency-based color gradients
  - Calculate bass, mid, high bar counts based on frequency bin distribution
  - Implement _apply_frequency_colors method using Rich Text
  - Apply darker orange (#cc5500) to bass frequency bars
  - Apply medium orange (#ff8c00) to mid frequency bars
  - Apply lighter amber (#ffb347) to high frequency bars
  - Integrate color application into bar rendering
  - _Requirements: 1.5, 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]* 6.1 Write unit tests for color gradient application
  - Test color assignment for bass range bars
  - Test color assignment for mid range bars
  - Test color assignment for high range bars
  - Test color boundaries between frequency ranges

- [ ] 7. Implement terminal resize handling
  - Add watch for terminal size changes in VisualizerView
  - Recalculate bar_count based on new terminal width
  - Ensure minimum of 20 bars and maximum based on width
  - Re-render visualization with new bar count
  - _Requirements: 7.4_

- [ ]* 7.1 Write property test for terminal resize adaptation
  - **Property 8: Terminal resize adaptation**
  - **Validates: Requirements 7.4**

- [ ] 8. Integrate VisualizerView with AudioPlayer
  - Update main.py to pass audio_player instance to VisualizerView
  - Ensure VisualizerView has access to playback state
  - Test that visualizer starts/stops with audio playback
  - Verify no impact on audio playback performance
  - _Requirements: 4.5, 6.3_

- [ ]* 8.1 Write property test for playback independence
  - **Property 6: Playback independence**
  - **Validates: Requirements 6.3**

- [ ] 9. Add performance monitoring and optimization
  - Implement CPU usage tracking for visualization processing
  - Add frame rate measurement to verify 15-30 FPS range
  - Implement adaptive frame rate reduction if CPU exceeds 20%
  - Add logging for performance metrics
  - _Requirements: 6.1, 6.2, 6.5_

- [ ]* 9.1 Write property test for update rate bounds
  - **Property 3: Visualization update rate bounds**
  - **Validates: Requirements 6.1, 6.2**

- [ ]* 9.2 Write performance tests
  - Measure CPU usage during visualization with various audio files
  - Measure memory usage with different buffer sizes
  - Verify no audio dropouts during sustained visualization
  - Test performance across different terminal emulators

- [ ] 10. Handle edge cases and error conditions
  - Implement silence detection to prevent flickering (minimum amplitude threshold)
  - Add 2-second timeout to return to baseline when paused
  - Handle FFT computation errors (NaN, Inf) with zero replacement
  - Add user-friendly error messages for common audio capture issues
  - _Requirements: 7.1, 7.2, 7.3, 7.5_

- [ ]* 10.1 Write unit tests for edge case handling
  - Test behavior with silent audio buffers
  - Test behavior when playback is paused
  - Test handling of NaN and Inf values in FFT output
  - Test error message display when audio capture fails

- [ ] 11. Update CSS styling for visualizer
  - Update styles/app.tcss with visualizer-specific styles
  - Ensure baseline uses distinct styling from bars
  - Apply orange color scheme consistent with SIGPLAY aesthetic
  - Test styling across different terminal color capabilities
  - _Requirements: 1.5, 2.5, 8.5_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Add documentation and logging
  - Add docstrings to SpectrumAnalyzer class and methods
  - Add docstrings to FrequencyBands and VisualizerConfig
  - Add logging statements for audio capture start/stop
  - Add logging for FFT computation errors
  - Document sounddevice setup requirements in README
  - _Requirements: 4.1, 4.2, 7.5_

- [ ]* 14. Integration testing with real audio files
  - Test visualizer with MP3 files
  - Test visualizer with FLAC files
  - Test visualizer with WAV files
  - Test visualizer with various sample rates (44.1kHz, 48kHz)
  - Verify frequency response matches audio content (bass-heavy, treble-heavy tracks)
  - _Requirements: 3.4, 3.5, 4.4, 5.4_

- [ ] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
