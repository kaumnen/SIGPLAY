# Implementation Plan

- [x] 1. Add faster-whisper dependency and create data model
  - Add `faster-whisper>=1.1.0` to pyproject.toml dependencies
  - Create `models/lyrics.py` with `LyricSegment` dataclass
  - Export `LyricSegment` in `models/__init__.py`
  - _Requirements: 8.3_

- [ ]* 1.1 Write property test for LyricSegment serialization
  - **Property 11: Cache format round-trip**
  - **Validates: Requirements 3.5**

- [x] 2. Implement LyricsService with Whisper integration
  - Create `services/lyrics_service.py` with `LyricsService` class
  - Implement cache directory setup in `__init__` method
  - Implement `_get_model()` method for lazy loading Whisper large-v3 model with int8 quantization
  - Implement cache key generation using MD5 hash of track path
  - Export `LyricsService` in `services/__init__.py`
  - _Requirements: 2.5, 3.3, 3.4, 4.1, 4.4, 8.1_

- [ ]* 2.1 Write property test for cache key generation
  - **Property 10: Cache key is MD5 hash of track path**
  - **Validates: Requirements 3.3**

- [x] 3. Implement lyrics transcription and caching
  - Implement `get_lyrics()` method in `LyricsService` with cache check
  - Implement transcription using Whisper model with word timestamps and beam_size=5
  - Implement progress callback support for status updates
  - Implement cache saving as JSON with segment data
  - Implement cache loading and deserialization to `LyricSegment` objects
  - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.5, 4.2, 4.3_

- [ ]* 3.1 Write property test for cache bypass
  - **Property 9: Cached lyrics bypass transcription**
  - **Validates: Requirements 3.2**

- [ ]* 3.2 Write property test for transcription output format
  - **Property 5: Completed transcription produces timestamped lyrics**
  - **Validates: Requirements 2.3**

- [x] 4. Implement error handling in LyricsService
  - Add try-catch blocks for file not found errors
  - Add try-catch blocks for model download failures
  - Add try-catch blocks for transcription errors
  - Add try-catch blocks for cache read/write errors
  - Log all errors to `~/.local/share/sigplay/sigplay.log`
  - _Requirements: 2.4_

- [ ]* 4.1 Write property test for error handling
  - **Property 6: Transcription errors show error UI**
  - **Validates: Requirements 2.4**

- [x] 5. Create LyricsView layout and composition
  - Create `views/lyrics.py` with `LyricsView` class
  - Implement `__init__` to accept `MusicLibrary`, `AudioPlayer`, and `LyricsService` dependencies
  - Implement `compose()` method with horizontal split layout
  - Add left panel with track library title and ListView
  - Add right panel with lyrics title, LoadingIndicator, status label, and scrollable lyrics container
  - Add reactive properties: `current_track`, `lyrics`, `active_segment_index`, `is_loading`, `status_message`
  - Export `LyricsView` in `views/__init__.py`
  - _Requirements: 1.2, 6.1, 8.2_

- [x] 6. Implement track library display and navigation
  - Implement `on_mount()` to call `_refresh_track_list()` and set up update timer
  - Implement `on_show()` to refresh track list and reload lyrics for current track
  - Implement `_refresh_track_list()` to populate ListView with tracks from MusicLibrary
  - Store track reference on each ListItem for later retrieval
  - Implement `on_list_view_selected()` to handle track selection
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ]* 6.1 Write property test for track selection behavior
  - **Property 15: Track selection loads lyrics**
  - **Property 16: Track selection starts playback**
  - **Validates: Requirements 6.3, 6.4**

- [x] 7. Implement lyrics loading and display
  - Implement `_load_lyrics_for_track()` method to request lyrics from LyricsService
  - Show loading indicator and status updates during transcription
  - Handle progress callbacks to update status label
  - Implement error handling with notifications
  - Implement `_render_lyrics()` to create Static widgets for each segment
  - Handle empty state with "Select a track to view lyrics" message
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 9.1, 9.2, 9.3, 9.4, 10.1, 10.5_

- [ ]* 7.1 Write property test for loading indicator visibility
  - **Property 4: Loading indicator displays during transcription**
  - **Validates: Requirements 2.2, 9.1**

- [ ]* 7.2 Write property test for status message content
  - **Property 20: Transcription status includes track name**
  - **Validates: Requirements 9.3**

- [x] 8. Implement playback synchronization
  - Implement `_update_active_segment()` method called every 0.5 seconds
  - Query AudioPlayer for current playback position
  - Find segment whose start/end times contain current position
  - Update `active_segment_index` when segment changes
  - Implement `_highlight_active_segment()` to apply/remove CSS classes
  - Implement auto-scroll to center active segment in VerticalScroll
  - _Requirements: 1.3, 1.4, 5.1, 5.2, 5.3, 5.4_

- [ ]* 8.1 Write property test for active segment calculation
  - **Property 1: Active segment matches playback position**
  - **Validates: Requirements 1.3, 5.1**

- [ ]* 8.2 Write property test for auto-scroll behavior
  - **Property 2: Auto-scroll keeps active segment visible**
  - **Validates: Requirements 1.4, 5.3**

- [ ] 9. Implement cleanup and state management
  - Implement `cleanup()` method to stop update timer
  - Implement track switching to cancel pending transcription
  - Handle playback stop to reset active segment
  - Handle playback pause to maintain current highlight
  - _Requirements: 5.5, 6.5_

- [ ]* 9.1 Write property test for track switching cancellation
  - **Property 17: Track switching cancels pending transcription**
  - **Validates: Requirements 6.5**

- [ ]* 9.2 Write property test for paused playback state
  - **Property 14: Paused playback preserves highlight**
  - **Validates: Requirements 5.4**

- [ ] 10. Add lyrics view styling to app.tcss
  - Add styles for `#lyrics-container` with horizontal layout
  - Add styles for `#lyrics-library-panel` with fixed width and border
  - Add styles for `#lyrics-display-panel` with flexible width
  - Add styles for `#lyrics-track-list` with orange theme
  - Add styles for `.lyric-segment` with dimmed orange color
  - Add styles for `.lyric-segment.active` with bright orange and bold
  - Add styles for `.lyrics-empty` with centered text
  - Add styles for `#lyrics-loading` and `#lyrics-status`
  - _Requirements: 8.4, 10.2, 10.3, 10.4_

- [ ] 11. Integrate lyrics view with main app
  - Import `LyricsView` and `LyricsService` in `main.py`
  - Instantiate `LyricsService` in `SigplayApp.__init__`
  - Add `LyricsView` to ContentSwitcher with id `lyrics-view`
  - Add keybinding `l` to switch to lyrics view
  - Update keybinding `d` to return to main view from lyrics view
  - Pass `MusicLibrary`, `AudioPlayer`, and `LyricsService` to `LyricsView`
  - _Requirements: 1.1, 1.5, 8.5_

- [ ] 12. Add help documentation for lyrics view
  - Update help screen to include lyrics view keybindings
  - Document `l` key to open lyrics view
  - Document `j`/`k` navigation in lyrics track library
  - Document `Enter` to select track and load lyrics
  - Document `d` or `Escape` to return to main view
  - _Requirements: 1.1, 1.5, 6.2_

- [ ] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
