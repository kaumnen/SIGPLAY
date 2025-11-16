# Implementation Plan

- [x] 1. Install dependencies and create service structure
  - Add pygame and mutagen dependencies using uv
  - Create services directory with __init__.py
  - Create models/playback.py for PlaybackState enum
  - _Requirements: 1.1, 2.1_

- [x] 2. Implement PlaybackState enum
  - Create PlaybackState enum with STOPPED, PLAYING, PAUSED states
  - Add to models/__init__.py for easy imports
  - _Requirements: 2.2, 3.2, 4.2_

- [x] 3. Enhance Track model with file path and duration
  - Add file_path field to Track dataclass
  - Add duration_seconds field for calculations
  - Implement from_file classmethod to create Track from file and metadata
  - Implement _format_duration static method to convert seconds to MM:SS
  - Update models/__init__.py exports
  - _Requirements: 1.5, 5.2, 5.3_

- [x] 4. Implement MusicLibrary service
- [x] 4.1 Create MusicLibrary class structure
  - Create services/music_library.py
  - Define SUPPORTED_EXTENSIONS constant (.mp3, .flac, .wav, .ogg, .m4a)
  - Define DEFAULT_MUSIC_DIR as Path.home() / "Music"
  - Initialize with music_dir parameter (defaults to DEFAULT_MUSIC_DIR)
  - Create _tracks list to store discovered tracks
  - _Requirements: 1.1, 1.2, 1.4_

- [x] 4.2 Implement file scanning functionality
  - Implement scan() method using Path.rglob() for recursive search
  - Filter files by SUPPORTED_EXTENSIONS
  - Handle missing music directory gracefully
  - Sort tracks by artist, then album, then title
  - Return list of Track objects
  - _Requirements: 1.1, 1.3, 1.4_

- [x] 4.3 Implement metadata extraction
  - Implement _extract_metadata() static method using mutagen
  - Extract title, artist, album, duration from audio files
  - Handle missing tags with fallbacks (filename for title, "Unknown" for others)
  - Get duration in seconds using mutagen's info.length
  - Handle corrupted files gracefully (skip and log)
  - _Requirements: 1.5_

- [x] 4.4 Implement helper methods
  - Implement get_tracks() to return cached track list
  - Implement get_track_by_index() to retrieve specific track
  - Implement refresh() to rescan library
  - Add services/__init__.py with exports
  - _Requirements: 1.1_

- [x] 5. Implement AudioPlayer service
- [x] 5.1 Create AudioPlayer singleton structure
  - Create services/audio_player.py
  - Implement singleton pattern with __new__ method
  - Initialize pygame.mixer in __init__ (44.1kHz, 16-bit, stereo)
  - Set up end event notification with set_endevent(pygame.USEREVENT)
  - Initialize state variables (current_track, playlist, volume, state)
  - Set default volume to 70%
  - _Requirements: 2.1, 6.5_

- [x] 5.2 Implement playback control methods
  - Implement play(track) method to load and play audio file
  - Implement pause() method using pygame.mixer.music.pause()
  - Implement resume() method using pygame.mixer.music.unpause()
  - Implement stop() method to stop playback and reset position
  - Update state appropriately in each method
  - _Requirements: 2.1, 2.2, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4_

- [x] 5.3 Implement volume control methods
  - Implement set_volume(level) to set volume (0.0 to 1.0)
  - Implement increase_volume(amount) to increase by 5% (0.05)
  - Implement decrease_volume(amount) to decrease by 5% (0.05)
  - Clamp volume values between 0.0 and 1.0
  - Use pygame.mixer.music.set_volume()
  - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [x] 5.4 Implement position tracking
  - Implement get_position() method using pygame.mixer.music.get_pos()
  - Track start time when playback begins
  - Calculate elapsed time accounting for pauses
  - Return position in seconds
  - _Requirements: 5.1, 5.2_

- [x] 5.5 Implement playlist management
  - Implement set_playlist(tracks, start_index) to set current playlist
  - Implement get_playlist() to return current playlist
  - Implement next_track() to skip to next track in playlist
  - Implement previous_track() to skip to previous track
  - Handle boundary conditions (first/last track)
  - Implement logic for previous track: restart if > 3 seconds, else go to previous
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 5.6 Implement state query methods
  - Implement get_state() to return current PlaybackState
  - Implement get_current_track() to return current Track or None
  - Implement get_volume() to return current volume level
  - Implement is_playing() to check if currently playing
  - _Requirements: 2.2, 3.2, 4.2, 6.4_

- [x] 5.7 Implement audio device management stub
  - Implement list_audio_devices() returning system default for now
  - Implement set_audio_device(device_name) as stub for future
  - Add TODO comments for future sounddevice integration
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 6. Update LibraryView to use real tracks and handle playback
- [x] 6.1 Update LibraryView initialization
  - Add music_library and audio_player parameters to __init__
  - Store references as instance variables
  - Remove placeholder track data
  - _Requirements: 1.1, 2.1_

- [x] 6.2 Implement track loading from MusicLibrary
  - Update on_mount() to load tracks from music_library.get_tracks()
  - Handle empty library case with message
  - Populate ListView with real track data
  - _Requirements: 1.1, 5.1_

- [x] 6.3 Implement track selection and playback
  - Implement on_list_view_selected() handler for Enter key
  - Get selected track from tracks list
  - Call audio_player.set_playlist() with all tracks and selected index
  - Call audio_player.play() with selected track
  - Switch to Now Playing view using app.switch_view()
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 6.4 Implement play indicator display
  - Update _populate_list() to show ♪ symbol next to currently playing track
  - Query audio_player.get_current_track() to determine which track is playing
  - Format list items as "♪ Title - Artist (Duration)" for playing track
  - Format list items as "  Title - Artist (Duration)" for other tracks
  - _Requirements: 10.1, 10.2, 10.3_

- [x] 6.5 Implement play indicator updates
  - Implement _update_play_indicator() method to refresh list display
  - Call this method when track changes (use Textual reactive or manual refresh)
  - Update only the affected list items for efficiency
  - _Requirements: 10.4_

- [x] 7. Update NowPlayingView with real-time progress
- [x] 7.1 Update NowPlayingView initialization
  - Add audio_player parameter to __init__
  - Store reference as instance variable
  - Initialize update timer variable
  - _Requirements: 5.1, 6.1_

- [x] 7.2 Implement view composition with progress widgets
  - Update compose() to yield Static widgets for track info
  - Add ProgressBar widget with id "np-progress"
  - Add Static widgets for time display (current / total)
  - Add Static widget for volume display
  - Add Static widget for playback state display
  - Apply CSS IDs for styling
  - _Requirements: 5.3, 5.4, 5.5, 6.4_

- [x] 7.3 Implement real-time progress updates
  - Implement on_mount() to start update timer (1 second interval)
  - Implement _update_progress() method called by timer
  - Query audio_player.get_current_track() for track info
  - Query audio_player.get_position() for current position
  - Query audio_player.get_volume() for volume level
  - Query audio_player.get_state() for playback state
  - Update all display widgets with current values
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.4_

- [x] 7.4 Implement time formatting
  - Implement _format_time(seconds) helper method
  - Convert seconds to MM:SS format
  - Handle edge cases (0 seconds, very long tracks)
  - _Requirements: 5.2, 5.3_

- [x] 7.5 Update progress bar calculation
  - Calculate percentage: (current_position / total_duration) * 100
  - Update ProgressBar.update() with percentage
  - Handle division by zero for tracks with unknown duration
  - _Requirements: 5.4_

- [x] 8. Update main app with playback integration
- [x] 8.1 Initialize services in SigplayApp
  - Import AudioPlayer and MusicLibrary
  - Create AudioPlayer instance in __init__
  - Create MusicLibrary instance in __init__
  - _Requirements: 1.1, 2.1_

- [x] 8.2 Implement library scanning on startup
  - Implement on_mount() to start library scan
  - Use run_worker() to scan library in background thread
  - Implement _scan_library() async method
  - Update LibraryView when scan completes
  - Show loading indicator during scan (optional)
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 8.3 Implement pygame event checking for track end
  - Set up interval timer in on_mount() to check pygame events (0.1 second)
  - Implement _check_pygame_events() method
  - Check for pygame.USEREVENT (track end event)
  - Call audio_player.next_track() when track ends
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 8.4 Update view composition with service injection
  - Update compose() to pass music_library and audio_player to LibraryView
  - Update compose() to pass audio_player to NowPlayingView
  - Ensure VisualizerView remains unchanged
  - _Requirements: 2.1, 5.1_

- [x] 8.5 Implement playback control keybindings
  - Add keybinding for space bar to action_play_pause
  - Add keybinding for 's' key to action_stop
  - Add keybinding for 'n' key to action_next_track
  - Add keybinding for 'p' key to action_previous_track
  - Add keybinding for '+' and '=' keys to action_volume_up
  - Add keybinding for '-' key to action_volume_down
  - Add keybinding for 'o' key to action_select_device (stub)
  - _Requirements: 2.1, 3.1, 4.1, 6.1, 6.2, 9.1, 9.2_

- [x] 8.6 Implement playback control action methods
  - Implement action_play_pause() to toggle play/pause
  - Implement action_stop() to stop playback
  - Implement action_next_track() to skip to next track
  - Implement action_previous_track() to skip to previous track
  - Implement action_volume_up() to increase volume
  - Implement action_volume_down() to decrease volume
  - Implement action_select_device() as stub (show message for future feature)
  - _Requirements: 2.1, 2.2, 3.1, 3.3, 4.1, 6.1, 6.2, 9.1, 9.2_

- [x] 9. Update Footer to show playback controls
  - Update Footer widget or binding display to show new keybindings
  - Display: "Space: Play/Pause | s: Stop | n: Next | p: Prev | +/-: Volume | o: Device"
  - Ensure footer updates dynamically based on current view
  - _Requirements: 2.1, 3.1, 4.1, 6.1, 9.1_

- [x] 10. Update CSS styles for new widgets
  - Add styles for play indicator (♪ symbol) in library view
  - Add styles for progress bar in now playing view
  - Add styles for volume and state displays
  - Ensure orange color scheme is applied consistently
  - Add hover effects for better UX
  - _Requirements: 5.3, 5.4, 6.4, 10.1, 10.2, 10.3_

- [x] 11. Handle error cases and edge conditions
  - Add error handling for missing music directory in MusicLibrary
  - Add error handling for corrupted audio files in AudioPlayer
  - Add error handling for file not found during playback
  - Display user-friendly error messages in views
  - Add logging for debugging (use Python logging module)
  - _Requirements: 1.1, 2.5, 4.4_

- [x] 12. Test and verify complete playback flow
  - Test library scanning with real music files
  - Test selecting and playing a track
  - Test pause/resume functionality
  - Test stop functionality
  - Test volume controls (increase/decrease)
  - Test track skipping (next/previous)
  - Test auto-advance when track ends
  - Test play indicator updates in library view
  - Test progress bar updates in now playing view
  - Verify all keybindings work correctly
  - Test with various audio formats (MP3, OGG, WAV)
  - Test with empty music directory
  - Test with large music library (100+ tracks)
  - _Requirements: All_
