# Design Document

## Overview

This design document outlines the audio playback functionality for SIGPLAY. The implementation uses `pygame.mixer` for audio playback due to its robust feature set, native pause/resume support, and excellent cross-platform compatibility. The design introduces a centralized `AudioPlayer` service class that manages playback state, a `MusicLibrary` class for file discovery and metadata extraction, and updates to existing views to integrate playback controls and real-time progress updates.

The architecture follows a service-oriented pattern where the `AudioPlayer` acts as a singleton service accessible throughout the application, while maintaining Textual's reactive programming model for UI updates.

## Architecture

### Component Overview

```
SIGPLAY Application
├── Services Layer
│   ├── AudioPlayer (playback control, state management)
│   └── MusicLibrary (file scanning, metadata extraction)
├── Models Layer
│   ├── Track (enhanced with file_path, duration_seconds)
│   └── PlaybackState (enum: STOPPED, PLAYING, PAUSED)
├── Views Layer (updated)
│   ├── LibraryView (track selection, play indicator)
│   ├── NowPlayingView (progress updates, controls display)
│   └── VisualizerView (existing)
└── Main App (AudioPlayer integration, keybindings)
```

### Audio Library Selection: pygame.mixer

**Rationale:**
- Cross-platform support (macOS, Linux, Windows)
- Native pause/resume support (critical for music player)
- Built-in volume control
- Supports common formats: MP3, OGG, WAV (FLAC/M4A with additional setup)
- Event system for track completion detection
- Streaming playback (doesn't load entire file into memory)
- Well-documented and stable
- Active community support

**Alternatives Considered:**
- `simpleaudio` + `pydub`: No native pause support, requires workarounds
- `python-vlc`: Requires VLC installation, heavier dependency
- `miniaudio`: Newer library, less mature ecosystem

**Installation:**
```bash
uv add pygame mutagen
```

For metadata extraction, we'll use `mutagen`:
- Reads ID3 tags (MP3), Vorbis comments (OGG), and other formats
- Extracts duration, artist, album, title
- Lightweight and reliable

### Data Flow

```
User Action (key press)
    ↓
Main App (keybinding handler)
    ↓
AudioPlayer Service (state change)
    ↓
pygame.mixer (audio output)
    ↓
Reactive Update (Textual reactive attributes)
    ↓
View Updates (UI refresh)
```

## Components and Interfaces

### AudioPlayer Service

**Location:** `services/audio_player.py`

**Responsibilities:**
- Initialize and manage pygame.mixer
- Load and play audio files
- Control playback (play, pause, stop, skip)
- Manage volume level
- Track playback position and duration
- Emit state changes for UI updates
- Handle audio output device selection

**Class Definition:**

```python
class AudioPlayer:
    """Singleton service for audio playback management."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.music.set_endevent(pygame.USEREVENT)
            self._current_track: Optional[Track] = None
            self._playlist: List[Track] = []
            self._current_index: int = -1
            self._volume: float = 0.7  # 70% default
            self._state: PlaybackState = PlaybackState.STOPPED
            self._start_time: float = 0
            self._pause_position: float = 0
            self._initialized = True
            pygame.mixer.music.set_volume(self._volume)
    
    # Playback Control Methods
    def play(self, track: Track) -> None
    def pause(self) -> None
    def resume(self) -> None
    def stop(self) -> None
    def next_track(self) -> None
    def previous_track(self) -> None
    
    # Volume Control
    def set_volume(self, level: float) -> None  # 0.0 to 1.0
    def increase_volume(self, amount: float = 0.05) -> None
    def decrease_volume(self, amount: float = 0.05) -> None
    
    # State Queries
    def get_state(self) -> PlaybackState
    def get_current_track(self) -> Optional[Track]
    def get_position(self) -> float  # seconds
    def get_volume(self) -> float  # 0.0 to 1.0
    def is_playing(self) -> bool
    
    # Playlist Management
    def set_playlist(self, tracks: List[Track], start_index: int = 0) -> None
    def get_playlist(self) -> List[Track]
    
    # Audio Device Management
    def list_audio_devices(self) -> List[str]
    def set_audio_device(self, device_name: str) -> None
```

**Implementation Details:**

1. **Initialization:**
   - Initialize pygame.mixer with standard audio settings (44.1kHz, 16-bit, stereo)
   - Set up end event notification using `set_endevent(pygame.USEREVENT)`
   - Set default volume to 70%
   - Initialize state to STOPPED

2. **Play Method:**
   - Load audio file using `pygame.mixer.music.load(file_path)`
   - Start playback with `pygame.mixer.music.play()`
   - Record start time for position tracking
   - Update current track and state
   - If track is part of playlist, update current index

3. **Pause/Resume:**
   - Use `pygame.mixer.music.pause()` for pause
   - Use `pygame.mixer.music.unpause()` for resume
   - Record pause position for accurate tracking
   - Toggle state between PLAYING and PAUSED
   - Seamless operation with no audio glitches

4. **Stop Method:**
   - Call `pygame.mixer.music.stop()`
   - Reset position to 0
   - Update state to STOPPED
   - Clear current track reference

5. **Position Tracking:**
   - Use `pygame.mixer.music.get_pos()` to get milliseconds since play started
   - Combine with start time for absolute position
   - Account for pause duration if applicable
   - Return position in seconds for display

6. **Volume Control:**
   - Use `pygame.mixer.music.set_volume(level)` (accepts 0.0 to 1.0)
   - Clamp values to valid range [0.0, 1.0]
   - Store volume level for display
   - Volume persists across tracks

7. **Track Skipping:**
   - Stop current playback
   - Increment/decrement playlist index
   - Call play() with new track
   - Handle boundary conditions (first/last track)

8. **Auto-advance:**
   - pygame sends USEREVENT when track ends
   - Main app event loop listens for this event
   - Automatically calls next_track() on track completion
   - Seamless transition between tracks

### MusicLibrary Service

**Location:** `services/music_library.py`

**Responsibilities:**
- Scan music directory for audio files
- Extract metadata using mutagen
- Build Track objects with complete information
- Provide filtered/sorted track lists

**Class Definition:**

```python
class MusicLibrary:
    """Service for discovering and managing music files."""
    
    SUPPORTED_EXTENSIONS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a'}
    DEFAULT_MUSIC_DIR = Path.home() / "Music"
    
    def __init__(self, music_dir: Optional[Path] = None):
        self.music_dir = music_dir or self.DEFAULT_MUSIC_DIR
        self._tracks: List[Track] = []
    
    def scan(self) -> List[Track]
    def get_tracks(self) -> List[Track]
    def get_track_by_index(self, index: int) -> Optional[Track]
    def refresh(self) -> None
    
    @staticmethod
    def _extract_metadata(file_path: Path) -> Dict[str, Any]
    @staticmethod
    def _format_duration(seconds: float) -> str
```

**Implementation Details:**

1. **Scanning:**
   - Use `Path.rglob()` to recursively find files
   - Filter by supported extensions
   - For each file, extract metadata
   - Create Track objects
   - Sort by artist, then album, then title

2. **Metadata Extraction:**
   - Use mutagen to read audio file tags
   - Extract: title, artist, album, duration
   - Handle missing tags with fallbacks (filename for title, "Unknown" for others)
   - Get duration in seconds using mutagen's `info.length`

3. **Error Handling:**
   - Skip files that can't be read
   - Log errors but don't crash
   - Continue scanning remaining files

### Enhanced Track Model

**Location:** `models/track.py`

**Updates:**

```python
@dataclass
class Track:
    title: str
    artist: str
    album: str
    duration: str  # Format: "MM:SS" for display
    file_path: str  # Full path to audio file
    duration_seconds: float  # Duration in seconds for calculations
    
    @classmethod
    def from_file(cls, file_path: Path, metadata: Dict[str, Any]) -> 'Track':
        """Factory method to create Track from file and metadata."""
        pass
```

### PlaybackState Enum

**Location:** `models/playback.py`

```python
class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
```

### Updated LibraryView

**Location:** `views/library.py`

**New Responsibilities:**
- Display real tracks from MusicLibrary
- Handle Enter key to start playback
- Show play indicator (♪) next to currently playing track
- Update play indicator when track changes

**Key Changes:**

```python
class LibraryView(ListView):
    def __init__(self, music_library: MusicLibrary, audio_player: AudioPlayer):
        super().__init__()
        self.music_library = music_library
        self.audio_player = audio_player
        self.tracks = []
    
    def on_mount(self) -> None:
        # Load real tracks instead of placeholder data
        self.tracks = self.music_library.get_tracks()
        self._populate_list()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # Handle Enter key press on track
        selected_index = event.list_view.index
        track = self.tracks[selected_index]
        self.audio_player.set_playlist(self.tracks, selected_index)
        self.audio_player.play(track)
        # Switch to Now Playing view
        self.app.switch_view("now_playing")
    
    def _populate_list(self) -> None:
        # Create ListItem for each track with play indicator
        pass
    
    def _update_play_indicator(self) -> None:
        # Update which track shows the ♪ symbol
        pass
```

**UI Format:**
```
♪ Track Title - Artist Name (3:45)
  Another Track - Another Artist (4:12)
  Third Track - Third Artist (2:58)
```

### Updated NowPlayingView

**Location:** `views/now_playing.py`

**New Responsibilities:**
- Display current track from AudioPlayer
- Show real-time playback progress
- Update progress bar and time display every second
- Display volume level
- Show playback state (playing/paused/stopped)

**Key Changes:**

```python
class NowPlayingView(Container):
    def __init__(self, audio_player: AudioPlayer):
        super().__init__()
        self.audio_player = audio_player
        self._update_timer = None
    
    def on_mount(self) -> None:
        # Start update timer for progress
        self._update_timer = self.set_interval(1.0, self._update_progress)
    
    def compose(self) -> ComposeResult:
        yield Static("Now Playing", id="np-header")
        yield Static("", id="np-title")
        yield Static("", id="np-artist")
        yield Static("", id="np-album")
        yield ProgressBar(total=100, show_eta=False, id="np-progress")
        yield Static("", id="np-time")
        yield Static("", id="np-volume")
        yield Static("", id="np-state")
    
    def _update_progress(self) -> None:
        # Query AudioPlayer for current position
        # Update progress bar and time display
        # Update all text fields
        pass
    
    def _format_time(self, seconds: float) -> str:
        # Convert seconds to MM:SS format
        pass
```

**UI Layout:**
```
┌─────────────────────────────────────┐
│ Now Playing                         │
│                                     │
│ ♪ Track Title                       │
│ Artist: Artist Name                 │
│ Album: Album Name                   │
│                                     │
│ [████████████░░░░░░░] 2:34 / 4:12  │
│                                     │
│ Volume: 70%                         │
│ State: Playing                      │
└─────────────────────────────────────┘
```

### Audio Device Selection Dialog

**Location:** `widgets/device_selector.py`

**Responsibilities:**
- Display list of available audio devices
- Allow selection with keyboard navigation
- Apply selection and close dialog

**Implementation:**

```python
class DeviceSelector(Container):
    """Modal dialog for selecting audio output device."""
    
    def __init__(self, audio_player: AudioPlayer):
        super().__init__()
        self.audio_player = audio_player
    
    def compose(self) -> ComposeResult:
        yield Static("Select Audio Output Device", id="device-header")
        yield ListView(id="device-list")
    
    def on_mount(self) -> None:
        devices = self.audio_player.list_audio_devices()
        # Populate ListView with devices
        pass
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # Set selected device and close dialog
        pass
```

**Note:** pygame.mixer has limited audio device selection capabilities. For initial implementation, we'll use system defaults. Advanced device selection could be added later using `sounddevice` library or platform-specific APIs.

### Updated Main App

**Location:** `main.py`

**New Responsibilities:**
- Initialize AudioPlayer and MusicLibrary services
- Pass services to views
- Add keybindings for playback controls
- Handle pygame events for track end detection
- Coordinate view updates on playback state changes

**Key Changes:**

```python
class SigplayApp(App):
    CSS_PATH = "styles/app.tcss"
    
    def __init__(self):
        super().__init__()
        self.audio_player = AudioPlayer()
        self.music_library = MusicLibrary()
    
    def on_mount(self) -> None:
        # Scan music library on startup
        self.run_worker(self._scan_library, exclusive=True)
        
        # Set up pygame event checking for track end
        self.set_interval(0.1, self._check_pygame_events)
    
    async def _scan_library(self) -> None:
        # Run library scan in background thread
        tracks = await self.run_in_thread(self.music_library.scan)
        # Update library view when complete
        pass
    
    def _check_pygame_events(self) -> None:
        # Check for track end event from pygame
        for event in pygame.event.get():
            if event.type == pygame.USEREVENT:  # Track ended
                self.audio_player.next_track()
    
    def compose(self) -> ComposeResult:
        yield Header()
        with ContentSwitcher(initial="library"):
            yield LibraryView(self.music_library, self.audio_player)
            yield NowPlayingView(self.audio_player)
            yield VisualizerView()
        yield Footer()
    
    # New keybindings
    def action_play_pause(self) -> None:
        if self.audio_player.is_playing():
            self.audio_player.pause()
        else:
            self.audio_player.resume()
    
    def action_stop(self) -> None:
        self.audio_player.stop()
    
    def action_next_track(self) -> None:
        self.audio_player.next_track()
    
    def action_previous_track(self) -> None:
        self.audio_player.previous_track()
    
    def action_volume_up(self) -> None:
        self.audio_player.increase_volume()
    
    def action_volume_down(self) -> None:
        self.audio_player.decrease_volume()
    
    def action_select_device(self) -> None:
        # Show device selector dialog
        pass
```

**Keybindings:**
- `space`: Play/Pause toggle
- `s`: Stop playback
- `n`: Next track
- `p`: Previous track
- `+` or `=`: Volume up
- `-`: Volume down
- `o`: Open device selector
- `enter`: Play selected track (in Library view)

## Data Models

### Track (Enhanced)

```python
@dataclass
class Track:
    title: str
    artist: str
    album: str
    duration: str  # "MM:SS" format
    file_path: str
    duration_seconds: float
    
    @classmethod
    def from_file(cls, file_path: Path, metadata: Dict[str, Any]) -> 'Track':
        return cls(
            title=metadata.get('title', file_path.stem),
            artist=metadata.get('artist', 'Unknown Artist'),
            album=metadata.get('album', 'Unknown Album'),
            duration=cls._format_duration(metadata.get('duration', 0)),
            file_path=str(file_path),
            duration_seconds=metadata.get('duration', 0)
        )
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
```

### PlaybackState

```python
class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
```

## Error Handling

### File System Errors

- **Missing Music Directory:**
  - If ~/Music doesn't exist, show message in Library view
  - Provide option to specify custom directory (future enhancement)
  - Don't crash application

- **Unreadable Files:**
  - Skip files that can't be read
  - Log error to console
  - Continue scanning other files

- **No Audio Files Found:**
  - Display message in Library view: "No music files found in ~/Music"
  - Suggest adding music files

### Playback Errors

- **File Not Found:**
  - If track file is deleted after scanning, show error message
  - Skip to next track automatically
  - Remove from current playlist

- **Unsupported Format:**
  - If pygame can't play file, show error message
  - Skip to next track
  - Log format for debugging

- **Audio Device Errors:**
  - If device initialization fails, show error message
  - Fall back to system default device
  - Allow retry

### Metadata Extraction Errors

- **Corrupted Tags:**
  - Use filename as title if tags can't be read
  - Use "Unknown" for missing artist/album
  - Set duration to 0:00 if unavailable

- **Missing Files:**
  - Handle case where file is deleted between scan and playback
  - Show error message
  - Continue with next track

## Testing Strategy

### Unit Tests

1. **AudioPlayer Tests:**
   - Test play/pause/stop state transitions
   - Test volume control (increase/decrease/clamp)
   - Test playlist navigation (next/previous/boundaries)
   - Mock pygame.mixer for isolated testing

2. **MusicLibrary Tests:**
   - Test file scanning with mock filesystem
   - Test metadata extraction with sample files
   - Test filtering by extension
   - Test error handling for corrupted files

3. **Track Model Tests:**
   - Test from_file factory method
   - Test duration formatting
   - Test metadata fallbacks

### Integration Tests

1. **Playback Flow:**
   - Test selecting track from library starts playback
   - Test track completion advances to next track
   - Test stop resets position

2. **UI Updates:**
   - Test progress bar updates during playback
   - Test play indicator updates in library view
   - Test volume display updates

### Manual Testing

1. **Audio Quality:**
   - Test with various audio formats (MP3, FLAC, WAV, OGG)
   - Test with different sample rates and bit depths
   - Verify no audio glitches or stuttering

2. **User Experience:**
   - Test all keyboard shortcuts
   - Test rapid key presses (skip multiple tracks quickly)
   - Test switching views during playback
   - Test volume changes during playback

3. **Library Scanning:**
   - Test with large music libraries (1000+ files)
   - Test with nested directory structures
   - Test with missing/corrupted files
   - Test with empty music directory

4. **Edge Cases:**
   - Test with very short tracks (< 5 seconds)
   - Test with very long tracks (> 1 hour)
   - Test with tracks that have no metadata
   - Test with special characters in filenames

## Implementation Notes

### Dependencies

Add to `pyproject.toml`:
```toml
pygame>=2.5.0  # Audio playback
mutagen>=1.47.0  # Metadata extraction
```

Install with:
```bash
uv add pygame mutagen
```

### Performance Considerations

1. **Library Scanning:**
   - Run scan in background thread to avoid blocking UI
   - Show loading indicator during scan
   - Cache results until manual refresh

2. **Progress Updates:**
   - Update UI at 1 Hz (once per second) for progress
   - Use Textual's reactive attributes for efficient updates
   - Avoid unnecessary redraws

3. **Memory Usage:**
   - pygame.mixer streams audio, doesn't load entire file
   - Keep track list in memory (acceptable for typical libraries)
   - Consider pagination for very large libraries (10,000+ tracks)

### Platform-Specific Notes

**macOS:**
- pygame.mixer uses CoreAudio backend
- Default device selection works well
- ~/Music is standard location
- Supports MP3, OGG, WAV out of the box

**Linux:**
- pygame.mixer uses ALSA or PulseAudio
- May need to configure audio backend via SDL environment variables
- ~/Music is standard location (XDG)
- Supports MP3, OGG, WAV out of the box

**Audio Device Selection:**
- pygame.mixer has limited device selection
- For initial version, use system default
- Future enhancement: use `sounddevice` library for advanced device control

### File Structure

```
sigplay/
├── main.py              # Updated with AudioPlayer integration
├── services/
│   ├── __init__.py
│   ├── audio_player.py  # AudioPlayer service
│   └── music_library.py # MusicLibrary service
├── models/
│   ├── __init__.py
│   ├── track.py         # Enhanced Track model
│   └── playback.py      # PlaybackState enum
├── views/
│   ├── __init__.py
│   ├── library.py       # Updated with real tracks
│   ├── now_playing.py   # Updated with progress
│   └── visualizer.py    # Existing
├── widgets/
│   ├── __init__.py
│   ├── header.py        # Existing
│   └── device_selector.py  # New (optional for v1)
└── styles/
    └── app.tcss         # Updated with new widget styles
```

## Future Enhancements

While not part of this initial implementation, these features could be added later:

- Playlist creation and management
- Shuffle and repeat modes
- Equalizer controls
- Seek/scrub functionality (jump to position in track)
- Keyboard shortcuts customization
- Last.fm scrobbling
- Album art display (using terminal graphics protocols)
- Search and filter in library
- Multiple library directories
- Smart playlists based on metadata
- Gapless playback
- Crossfade between tracks
- Audio normalization/ReplayGain
