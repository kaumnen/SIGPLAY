# Requirements Document

## Introduction

This document specifies requirements for a lyrics generation and display feature in SIGPLAY. The feature uses faster-whisper (an optimized Whisper implementation) to transcribe audio tracks locally, generating timestamped lyrics that display in sync with playback. The system prioritizes accuracy by using the largest available Whisper model, provides offline functionality, and caches results to avoid re-processing.

## Glossary

- **Lyrics Service**: The service component responsible for loading the Whisper model, transcribing audio, and managing the lyrics cache
- **Lyrics View**: The full-screen UI view that displays the track library and synchronized lyrics
- **Whisper Model**: The pre-trained speech recognition model from OpenAI, accessed via faster-whisper library
- **Lyrics Cache**: Persistent storage of transcribed lyrics indexed by track file hash
- **Lyric Segment**: A timestamped text fragment with start time, end time, and transcribed text
- **Active Segment**: The lyric segment currently being played based on playback position
- **Track Hash**: MD5 hash of the track file path used as cache key

## Requirements

### Requirement 1

**User Story:** As a user, I want to view lyrics for my music tracks, so that I can read along while listening

#### Acceptance Criteria

1. WHEN a user presses the `l` key THEN the Lyrics Service SHALL switch to the lyrics view
2. WHEN the lyrics view is displayed THEN the Lyrics Service SHALL show a track library on the left side and a lyrics panel on the right side
3. WHEN a track is playing THEN the Lyrics Service SHALL highlight the current lyric segment based on playback position
4. WHEN playback progresses THEN the Lyrics Service SHALL auto-scroll the lyrics panel to keep the active segment visible
5. WHEN a user presses `d` or `escape` THEN the Lyrics Service SHALL return to the main view

### Requirement 2

**User Story:** As a user, I want lyrics to be generated automatically from audio, so that I don't need to manually find or input lyrics

#### Acceptance Criteria

1. WHEN a user selects a track without cached lyrics THEN the Lyrics Service SHALL transcribe the audio using the Whisper model
2. WHEN transcription begins THEN the Lyrics Service SHALL display a loading indicator with status text
3. WHEN transcription completes THEN the Lyrics Service SHALL display the generated lyrics with timestamps
4. WHEN transcription fails THEN the Lyrics Service SHALL display an error message and allow the user to retry or select another track
5. WHEN the Whisper model is not loaded THEN the Lyrics Service SHALL load the large-v3 model before transcription

### Requirement 3

**User Story:** As a user, I want lyrics to be cached after generation, so that I don't wait for re-transcription on subsequent plays

#### Acceptance Criteria

1. WHEN lyrics are generated for a track THEN the Lyrics Service SHALL save the lyrics to the cache directory
2. WHEN a user selects a track with cached lyrics THEN the Lyrics Service SHALL load lyrics from cache instead of re-transcribing
3. WHEN checking for cached lyrics THEN the Lyrics Service SHALL use the MD5 hash of the track file path as the cache key
4. WHEN the cache directory does not exist THEN the Lyrics Service SHALL create it at `~/.local/share/sigplay/lyrics_cache/`
5. WHEN saving to cache THEN the Lyrics Service SHALL store lyrics as JSON with start time, end time, and text for each segment

### Requirement 4

**User Story:** As a user, I want accurate lyrics transcription, so that I can trust the displayed text matches the audio

#### Acceptance Criteria

1. WHEN transcribing audio THEN the Lyrics Service SHALL use the large-v3 Whisper model
2. WHEN transcribing audio THEN the Lyrics Service SHALL enable word-level timestamps for precise synchronization
3. WHEN transcribing audio THEN the Lyrics Service SHALL detect language automatically if not specified
4. WHEN transcribing audio THEN the Lyrics Service SHALL use int8 quantization for efficient CPU inference
5. WHEN the model downloads for the first time THEN the Lyrics Service SHALL show download progress to the user

### Requirement 5

**User Story:** As a user, I want lyrics to synchronize with playback, so that I can follow along in real-time

#### Acceptance Criteria

1. WHEN playback position changes THEN the Lyrics Service SHALL update the active segment based on current time
2. WHEN a segment becomes active THEN the Lyrics Service SHALL highlight it with distinct styling
3. WHEN the active segment changes THEN the Lyrics Service SHALL scroll the lyrics panel to center the active segment
4. WHEN playback is paused THEN the Lyrics Service SHALL maintain the current active segment highlight
5. WHEN playback is stopped THEN the Lyrics Service SHALL reset the active segment to the beginning

### Requirement 6

**User Story:** As a user, I want to navigate the track library while viewing lyrics, so that I can switch between tracks easily

#### Acceptance Criteria

1. WHEN the lyrics view is active THEN the Lyrics Service SHALL display the full track library on the left side
2. WHEN a user presses `j` or `k` THEN the Lyrics Service SHALL move selection down or up in the track library
3. WHEN a user presses `Enter` on a selected track THEN the Lyrics Service SHALL load and display lyrics for that track
4. WHEN a user presses `Enter` on a selected track THEN the Lyrics Service SHALL begin playback of that track
5. WHEN switching tracks THEN the Lyrics Service SHALL cancel any in-progress transcription for the previous track

### Requirement 7

**User Story:** As a user, I want the lyrics feature to work offline, so that I can use it without internet connectivity

#### Acceptance Criteria

1. WHEN transcribing audio THEN the Lyrics Service SHALL use the locally installed faster-whisper library
2. WHEN the Whisper model is needed THEN the Lyrics Service SHALL load it from local cache if previously downloaded
3. WHEN the Whisper model is not cached THEN the Lyrics Service SHALL download it once and cache it locally
4. WHEN transcribing audio THEN the Lyrics Service SHALL not require any network requests after model download
5. WHEN the system is offline THEN the Lyrics Service SHALL function normally with cached models and lyrics

### Requirement 8

**User Story:** As a developer, I want the lyrics feature to integrate cleanly with existing architecture, so that it maintains code quality and consistency

#### Acceptance Criteria

1. WHEN implementing the lyrics feature THEN the Lyrics Service SHALL follow the existing service pattern in `services/`
2. WHEN implementing the lyrics view THEN the Lyrics Service SHALL follow the existing view pattern in `views/`
3. WHEN implementing lyric data structures THEN the Lyrics Service SHALL use dataclasses in `models/`
4. WHEN styling the lyrics view THEN the Lyrics Service SHALL define all styles in `styles/app.tcss`
5. WHEN the lyrics view is mounted THEN the Lyrics Service SHALL integrate with the existing ContentSwitcher pattern

### Requirement 9

**User Story:** As a user, I want clear visual feedback during lyrics generation, so that I understand what the system is doing

#### Acceptance Criteria

1. WHEN lyrics generation starts THEN the Lyrics Service SHALL display a loading indicator
2. WHEN the model is downloading THEN the Lyrics Service SHALL show "Downloading Whisper model..." status
3. WHEN transcription is in progress THEN the Lyrics Service SHALL show "Generating lyrics..." status with the track name
4. WHEN transcription completes THEN the Lyrics Service SHALL hide the loading indicator and display lyrics
5. WHEN an error occurs THEN the Lyrics Service SHALL display the error message with actionable guidance

### Requirement 10

**User Story:** As a user, I want lyrics to display with proper formatting, so that they are easy to read

#### Acceptance Criteria

1. WHEN displaying lyrics THEN the Lyrics Service SHALL show each segment on a separate line
2. WHEN displaying lyrics THEN the Lyrics Service SHALL use the orange color palette for consistency with the app theme
3. WHEN a segment is active THEN the Lyrics Service SHALL display it in bright orange with bold styling
4. WHEN a segment is not active THEN the Lyrics Service SHALL display it in dimmed orange
5. WHEN the lyrics panel is empty THEN the Lyrics Service SHALL display a message prompting the user to select a track
