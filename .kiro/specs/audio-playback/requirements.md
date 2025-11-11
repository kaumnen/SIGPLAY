# Requirements Document

## Introduction

This specification defines the audio playback functionality for SIGPLAY, a terminal-based music player. The feature enables users to play, pause, stop, and control audio files from their music library. It includes real-time playback progress tracking, volume control, audio output device selection, and automatic music library scanning from the default system music directory.

## Glossary

- **SIGPLAY**: The terminal-based music player application
- **Playback Engine**: The audio processing component responsible for playing audio files
- **Music Library**: The collection of audio files scanned from the user's music directory
- **Track**: An individual audio file with associated metadata (title, artist, album, duration)
- **Playback State**: The current status of audio playback (playing, paused, stopped)
- **Progress Indicator**: Visual representation of current playback position within a track
- **Volume Level**: Audio output amplitude expressed as a percentage (0-100%)
- **Audio Output Device**: The hardware or virtual device used for audio playback
- **Music Directory**: The default system location for music files (~/Music on macOS and Linux)
- **Audio Format**: Supported file types including MP3, FLAC, WAV, OGG, M4A

## Requirements

### Requirement 1

**User Story:** As a user, I want SIGPLAY to automatically discover music files from my system's music directory, so that I can access my music library without manual configuration.

#### Acceptance Criteria

1. WHEN SIGPLAY launches, THE Playback Engine SHALL scan the Music Directory for audio files
2. THE Playback Engine SHALL use "~/Music" as the default Music Directory on macOS and Linux systems
3. THE Playback Engine SHALL recursively scan subdirectories within the Music Directory
4. THE Playback Engine SHALL identify files with extensions: .mp3, .flac, .wav, .ogg, .m4a
5. THE Playback Engine SHALL extract metadata (title, artist, album, duration) from each discovered audio file

### Requirement 2

**User Story:** As a user, I want to start playing a selected track from the library, so that I can listen to my music.

#### Acceptance Criteria

1. WHEN the user presses the Enter key on a selected track in the Library View, THE Playback Engine SHALL begin playing the selected Track
2. WHEN playback begins, THE SIGPLAY SHALL update the Playback State to "playing"
3. WHEN playback begins, THE SIGPLAY SHALL switch to the Now Playing View
4. THE Playback Engine SHALL load the audio file from the file system
5. THE Playback Engine SHALL output audio to the currently selected Audio Output Device

### Requirement 3

**User Story:** As a user, I want to pause and resume playback, so that I can temporarily stop listening without losing my position in the track.

#### Acceptance Criteria

1. WHEN the user presses the space bar WHILE the Playback State is "playing", THE Playback Engine SHALL pause playback
2. WHEN playback is paused, THE SIGPLAY SHALL update the Playback State to "paused"
3. WHEN the user presses the space bar WHILE the Playback State is "paused", THE Playback Engine SHALL resume playback from the current position
4. WHEN playback resumes, THE SIGPLAY SHALL update the Playback State to "playing"
5. THE Playback Engine SHALL maintain the current playback position when paused

### Requirement 4

**User Story:** As a user, I want to stop playback completely, so that I can end the current listening session and reset the track position.

#### Acceptance Criteria

1. WHEN the user presses the 's' key WHILE audio is playing or paused, THE Playback Engine SHALL stop playback
2. WHEN playback stops, THE SIGPLAY SHALL update the Playback State to "stopped"
3. WHEN playback stops, THE Playback Engine SHALL reset the playback position to the beginning of the Track
4. THE Playback Engine SHALL release audio resources when stopped

### Requirement 5

**User Story:** As a user, I want to see real-time playback progress, so that I know how much of the track has played and how much remains.

#### Acceptance Criteria

1. WHILE the Playback State is "playing", THE SIGPLAY SHALL update the Progress Indicator at least once per second
2. THE Progress Indicator SHALL display the current playback position in MM:SS format
3. THE Progress Indicator SHALL display the total track duration in MM:SS format
4. THE Progress Indicator SHALL display a visual progress bar showing the percentage of track completed
5. THE Progress Indicator SHALL be visible in the Now Playing View

### Requirement 6

**User Story:** As a user, I want to adjust the volume level, so that I can control the audio output loudness.

#### Acceptance Criteria

1. WHEN the user presses the '+' or '=' key, THE Playback Engine SHALL increase the Volume Level by 5 percentage points
2. WHEN the user presses the '-' key, THE Playback Engine SHALL decrease the Volume Level by 5 percentage points
3. THE Playback Engine SHALL constrain the Volume Level between 0% and 100%
4. THE SIGPLAY SHALL display the current Volume Level as a percentage
5. THE Volume Level SHALL persist across track changes

### Requirement 7

**User Story:** As a user, I want to select which audio output device to use, so that I can direct playback to my preferred speakers or headphones.

#### Acceptance Criteria

1. WHEN the user presses the 'o' key, THE SIGPLAY SHALL display a list of available Audio Output Devices
2. THE SIGPLAY SHALL highlight the currently selected Audio Output Device
3. WHEN the user selects a different Audio Output Device, THE Playback Engine SHALL switch audio output to the selected device
4. THE Playback Engine SHALL continue playback without interruption when switching devices
5. THE selected Audio Output Device SHALL persist for the duration of the session

### Requirement 8

**User Story:** As a user, I want playback to automatically advance to the next track when the current track ends, so that I can enjoy continuous music playback.

#### Acceptance Criteria

1. WHEN a Track completes playback, THE Playback Engine SHALL automatically begin playing the next Track in the library
2. WHEN the last Track in the library completes, THE Playback Engine SHALL stop playback
3. THE SIGPLAY SHALL update the Now Playing View to display the new Track information
4. THE Playback Engine SHALL reset the Progress Indicator for the new Track

### Requirement 9

**User Story:** As a user, I want to skip to the next or previous track, so that I can navigate through my music library during playback.

#### Acceptance Criteria

1. WHEN the user presses the 'n' key, THE Playback Engine SHALL skip to the next Track in the library
2. WHEN the user presses the 'p' key, THE Playback Engine SHALL skip to the previous Track in the library
3. WHEN skipping tracks, THE Playback Engine SHALL begin playing the new Track immediately
4. WHEN skipping to the previous track WHILE playback position is less than 3 seconds, THE Playback Engine SHALL play the previous Track
5. WHEN skipping to the previous track WHILE playback position is 3 seconds or greater, THE Playback Engine SHALL restart the current Track from the beginning

### Requirement 10

**User Story:** As a user, I want to see which track is currently playing in the library view, so that I can identify the active track at a glance.

#### Acceptance Criteria

1. WHILE a Track is playing, THE SIGPLAY SHALL display a visual indicator next to the currently playing Track in the Library View
2. THE visual indicator SHALL use a distinctive symbol (such as "♪" or "▶")
3. THE visual indicator SHALL use the orange color scheme for consistency
4. THE visual indicator SHALL update when playback switches to a different Track
