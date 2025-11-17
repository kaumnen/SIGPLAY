# Requirements Document

## Introduction

This specification defines a real-time frequency-based audio visualizer for SIGPLAY that analyzes and displays bass, mid-range, and high-frequency content from currently playing audio. The visualizer will feature a baseline at the bottom with vertical bars that react dynamically to the music's frequency spectrum, providing users with visual feedback that corresponds to the audio characteristics of their music.

## Glossary

- **SIGPLAY**: The terminal-based music player application
- **Frequency Visualizer**: A visual display component that shows audio frequency content in real-time
- **Bass Frequencies**: Audio frequencies in the range of 20-250 Hz
- **Mid Frequencies**: Audio frequencies in the range of 250-4000 Hz  
- **High Frequencies**: Audio frequencies in the range of 4000-20000 Hz
- **FFT (Fast Fourier Transform)**: An algorithm that converts time-domain audio signals into frequency-domain data
- **Frequency Bins**: Discrete frequency ranges resulting from FFT analysis
- **Baseline**: A horizontal reference line at the bottom of the visualizer from which bars extend upward
- **Audio Buffer**: A temporary storage area for audio samples used for analysis
- **Playback Engine**: The audio playback system currently using pygame.mixer
- **Spectrum Analyzer**: A component that performs frequency analysis on audio data
- **Visualization Frame**: A single rendered instance of the frequency visualization display
- **Update Rate**: The frequency at which the visualization refreshes, measured in frames per second

## Requirements

### Requirement 1

**User Story:** As a user, I want to see a frequency-based audio visualizer that reacts to the music I'm playing, so that I can visually experience the bass, mid, and high-frequency content of my tracks.

#### Acceptance Criteria

1. WHEN audio is playing, THE Frequency Visualizer SHALL display vertical bars representing frequency content across the audio spectrum
2. THE Frequency Visualizer SHALL separate the frequency spectrum into three distinct ranges: bass (20-250 Hz), mid (250-4000 Hz), and high (4000-20000 Hz)
3. WHEN frequency content changes in the audio, THE Frequency Visualizer SHALL update bar heights to reflect the amplitude of each frequency range within 100 milliseconds
4. THE Frequency Visualizer SHALL display a minimum of 40 vertical bars across the terminal width
5. THE Frequency Visualizer SHALL maintain the retro-modern orange color scheme consistent with SIGPLAY's visual identity

### Requirement 2

**User Story:** As a user, I want the visualizer to have a clear baseline at the bottom, so that I can easily see how the bars react and jump in response to the music.

#### Acceptance Criteria

1. THE Frequency Visualizer SHALL display a horizontal baseline at the bottom of the visualization area
2. WHEN no audio is playing or frequency content is minimal, THE vertical bars SHALL rest at the baseline position
3. WHEN frequency content increases, THE vertical bars SHALL extend upward from the baseline proportionally to the amplitude
4. THE baseline SHALL remain visible and stationary regardless of bar height changes
5. THE Frequency Visualizer SHALL use distinct visual characters or styling to differentiate the baseline from the vertical bars

### Requirement 3

**User Story:** As a user, I want the visualizer to accurately analyze the audio being played, so that the visual representation matches what I'm hearing.

#### Acceptance Criteria

1. THE Spectrum Analyzer SHALL capture audio samples from the Playback Engine at a minimum rate of 20 times per second
2. THE Spectrum Analyzer SHALL apply FFT to convert time-domain audio samples into frequency-domain data
3. THE Spectrum Analyzer SHALL map FFT output to frequency bins corresponding to bass, mid, and high ranges
4. WHEN audio contains strong bass content, THE Frequency Visualizer SHALL display taller bars in the bass frequency range
5. WHEN audio contains strong high-frequency content, THE Frequency Visualizer SHALL display taller bars in the high frequency range

### Requirement 4

**User Story:** As a developer, I want to evaluate whether pygame.mixer provides sufficient audio analysis capabilities, so that I can determine if an alternative audio library is needed.

#### Acceptance Criteria

1. THE system SHALL assess pygame.mixer's capability to provide real-time audio sample access for frequency analysis
2. IF pygame.mixer cannot provide audio sample access, THEN THE system SHALL evaluate alternative audio libraries including sounddevice, pyaudio, and miniaudio
3. THE selected audio library SHALL support real-time audio buffer access without interrupting playback
4. THE selected audio library SHALL provide audio samples at a rate sufficient for smooth visualization updates (minimum 20 Hz)
5. THE system SHALL maintain compatibility with existing audio playback functionality when integrating the audio analysis library

### Requirement 5

**User Story:** As a developer, I want to use appropriate audio processing libraries for frequency analysis, so that the visualizer performs efficiently and accurately.

#### Acceptance Criteria

1. THE Spectrum Analyzer SHALL use numpy for FFT computation to ensure efficient frequency analysis
2. IF additional audio processing is required, THE system SHALL evaluate the pedalboard library from Spotify for audio effects and filtering
3. THE Spectrum Analyzer SHALL process audio buffers and compute frequency data within 50 milliseconds per frame
4. THE system SHALL handle audio sample rate variations (44.1kHz, 48kHz) without requiring manual configuration
5. THE Spectrum Analyzer SHALL normalize frequency amplitudes to a consistent scale for visualization rendering

### Requirement 6

**User Story:** As a user, I want the visualizer to perform smoothly without impacting audio playback, so that I can enjoy both the music and the visualization without interruptions.

#### Acceptance Criteria

1. THE Frequency Visualizer SHALL update at a minimum rate of 15 frames per second
2. THE Frequency Visualizer SHALL update at a maximum rate of 30 frames per second to avoid excessive CPU usage
3. WHEN the Frequency Visualizer is active, THE Playback Engine SHALL maintain uninterrupted audio playback
4. THE Spectrum Analyzer SHALL run in a separate execution context to prevent blocking the UI thread
5. THE system SHALL limit CPU usage for visualization processing to less than 20% of a single core on typical hardware

### Requirement 7

**User Story:** As a user, I want the visualizer to handle edge cases gracefully, so that the application remains stable regardless of audio content or playback state.

#### Acceptance Criteria

1. WHEN no audio is playing, THE Frequency Visualizer SHALL display the baseline with bars at minimum height
2. WHEN audio playback is paused, THE Frequency Visualizer SHALL freeze at the last analyzed state or return to baseline
3. WHEN audio contains silence or very low amplitude, THE Frequency Visualizer SHALL display minimal bar heights without flickering
4. WHEN the terminal window is resized, THE Frequency Visualizer SHALL adjust the number of bars to fit the new width
5. IF audio analysis fails or encounters errors, THE Frequency Visualizer SHALL display an error message and continue attempting to reconnect to the audio stream

### Requirement 8

**User Story:** As a user, I want the visualizer bars to be visually distinct for different frequency ranges, so that I can easily identify bass, mid, and high-frequency content.

#### Acceptance Criteria

1. THE Frequency Visualizer SHALL group bars visually by frequency range using spacing or color variations
2. WHERE color differentiation is used, THE bass frequency bars SHALL use darker orange tones
3. WHERE color differentiation is used, THE mid frequency bars SHALL use medium orange tones  
4. WHERE color differentiation is used, THE high frequency bars SHALL use lighter orange or amber tones
5. THE Frequency Visualizer SHALL maintain readability and visual clarity across different terminal color capabilities
