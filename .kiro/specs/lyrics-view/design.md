# Design Document: Lyrics View with Faster-Whisper

## Overview

The lyrics feature adds a new full-screen view to SIGPLAY that displays synchronized, timestamped lyrics generated from audio transcription. The system uses faster-whisper (an optimized implementation of OpenAI's Whisper model) to transcribe audio locally on the user's machine, eliminating the need for API keys, internet connectivity, or external services.

The feature follows a lazy-loading pattern where the Whisper model is only loaded when first needed, and transcribed lyrics are cached to disk to avoid re-processing. The UI displays a split view with the track library on the left and synchronized lyrics on the right, with automatic scrolling and highlighting of the current lyric segment during playback.

## Architecture

### Component Structure

```
views/
  lyrics.py              # LyricsView - full-screen view with library + lyrics panel

services/
  lyrics_service.py      # LyricsService - Whisper model management and transcription

models/
  lyrics.py              # LyricSegment dataclass

styles/
  app.tcss               # Lyrics view styling (orange theme)
```

### Data Flow

```
User presses 'l' key
    ↓
App switches to LyricsView
    ↓
User selects track from library
    ↓
LyricsView requests lyrics from LyricsService
    ↓
LyricsService checks cache
    ↓
If cached: Load from disk
If not cached:
    ↓
    Load Whisper model (if not loaded)
    ↓
    Transcribe audio in background thread
    ↓
    Save to cache
    ↓
Return lyrics to LyricsView
    ↓
LyricsView displays lyrics
    ↓
During playback: Update active segment based on position
```

### Integration Points

- **AudioPlayer**: Query playback position to determine active lyric segment
- **MusicLibrary**: Access track list for library display
- **ContentSwitcher**: Register lyrics view as switchable view with ID `lyrics-view`
- **Main App**: Add keybinding `l` to switch to lyrics view

## Components and Interfaces

### LyricSegment Model

```python
from dataclasses import dataclass

@dataclass
class LyricSegment:
    """Represents a single timestamped lyric segment."""
    start: float  # Start time in seconds
    end: float    # End time in seconds
    text: str     # Transcribed text
```

### LyricsService

```python
class LyricsService:
    """Service for managing Whisper model and lyrics transcription."""
    
    def __init__(self) -> None:
        """Initialize service with cache directory setup."""
        self._model: WhisperModel | None = None
        self._cache_dir: Path = Path.home() / ".local/share/sigplay/lyrics_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_model(self) -> WhisperModel:
        """Lazy-load Whisper model on first use."""
        if self._model is None:
            self._model = WhisperModel(
                "large-v3",
                device="cpu",
                compute_type="int8"
            )
        return self._model
    
    async def get_lyrics(
        self,
        track_path: str,
        progress_callback: Callable[[str], None] | None = None
    ) -> list[LyricSegment]:
        """Get lyrics for track, from cache or by transcribing."""
        # Check cache first
        cache_key = hashlib.md5(track_path.encode()).hexdigest()
        cache_file = self._cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            return [LyricSegment(**seg) for seg in data]
        
        # Transcribe in background thread
        def _transcribe() -> list[LyricSegment]:
            if progress_callback:
                progress_callback("Loading Whisper model...")
            
            model = self._get_model()
            
            if progress_callback:
                progress_callback(f"Generating lyrics...")
            
            segments, info = model.transcribe(
                track_path,
                word_timestamps=True,
                beam_size=5
            )
            
            lyrics = []
            for segment in segments:
                lyrics.append(LyricSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip()
                ))
            
            # Cache results
            cache_data = [
                {"start": seg.start, "end": seg.end, "text": seg.text}
                for seg in lyrics
            ]
            cache_file.write_text(json.dumps(cache_data, indent=2))
            
            return lyrics
        
        return await asyncio.to_thread(_transcribe)
    
    def clear_cache(self) -> None:
        """Clear all cached lyrics."""
        for cache_file in self._cache_dir.glob("*.json"):
            cache_file.unlink()
```

### LyricsView

```python
class LyricsView(Container):
    """Full-screen view displaying track library and synchronized lyrics."""
    
    current_track: reactive[Track | None] = reactive(None)
    lyrics: reactive[list[LyricSegment]] = reactive([])
    active_segment_index: reactive[int] = reactive(-1)
    is_loading: reactive[bool] = reactive(False)
    status_message: reactive[str] = reactive("")
    
    def __init__(
        self,
        music_library: MusicLibrary,
        audio_player: AudioPlayer,
        lyrics_service: LyricsService
    ) -> None:
        super().__init__()
        self._music_library = music_library
        self._audio_player = audio_player
        self._lyrics_service = lyrics_service
        self._update_timer: Timer | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the lyrics view layout."""
        with Horizontal(id="lyrics-container"):
            # Left side: Track library
            with Container(id="lyrics-library-panel"):
                yield Static("🎵 Track Library", id="lyrics-library-title")
                yield ListView(id="lyrics-track-list")
            
            # Right side: Lyrics display
            with Container(id="lyrics-display-panel"):
                yield Static("📝 Lyrics", id="lyrics-panel-title")
                yield LoadingIndicator(id="lyrics-loading")
                yield Static("", id="lyrics-status")
                with VerticalScroll(id="lyrics-scroll"):
                    yield Container(id="lyrics-content")
    
    def on_mount(self) -> None:
        """Initialize view on mount."""
        self._refresh_track_list()
        self._update_timer = self.set_interval(0.5, self._update_active_segment)
        self.query_one("#lyrics-loading", LoadingIndicator).display = False
    
    def on_show(self) -> None:
        """Called when view becomes visible."""
        self._refresh_track_list()
        if self.current_track:
            self._load_lyrics_for_track(self.current_track)
    
    def _refresh_track_list(self) -> None:
        """Populate track list from music library."""
        track_list = self.query_one("#lyrics-track-list", ListView)
        track_list.clear()
        
        for track in self._music_library.tracks:
            item = ListItem(Label(f"{track.title} - {track.artist or 'Unknown'}"))
            item.track = track  # Store track reference
            track_list.append(item)
    
    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle track selection."""
        if hasattr(event.item, 'track'):
            track = event.item.track
            self.current_track = track
            
            # Start playback
            self._audio_player.load_track(track.file_path)
            self._audio_player.play()
            
            # Load lyrics
            await self._load_lyrics_for_track(track)
    
    async def _load_lyrics_for_track(self, track: Track) -> None:
        """Load or generate lyrics for the selected track."""
        self.is_loading = True
        self.lyrics = []
        self.active_segment_index = -1
        
        loading_indicator = self.query_one("#lyrics-loading", LoadingIndicator)
        status_label = self.query_one("#lyrics-status", Static)
        
        loading_indicator.display = True
        status_label.update("")
        
        try:
            def progress_callback(message: str) -> None:
                self.call_from_thread(status_label.update, message)
            
            lyrics = await self._lyrics_service.get_lyrics(
                track.file_path,
                progress_callback=progress_callback
            )
            
            self.lyrics = lyrics
            self._render_lyrics()
            
        except Exception as e:
            logger.error(f"Error loading lyrics: {e}")
            status_label.update(f"Error: {str(e)}")
            self.notify(
                f"Failed to generate lyrics: {str(e)}",
                severity="error"
            )
        finally:
            self.is_loading = False
            loading_indicator.display = False
            status_label.update("")
    
    def _render_lyrics(self) -> None:
        """Render lyrics segments to the display."""
        content = self.query_one("#lyrics-content", Container)
        content.remove_children()
        
        if not self.lyrics:
            content.mount(Static("Select a track to view lyrics", classes="lyrics-empty"))
            return
        
        for i, segment in enumerate(self.lyrics):
            label = Static(
                segment.text,
                classes="lyric-segment",
                id=f"lyric-{i}"
            )
            content.mount(label)
    
    def _update_active_segment(self) -> None:
        """Update active segment based on playback position."""
        if not self.lyrics or not self._audio_player.is_playing():
            return
        
        position = self._audio_player.get_position()
        
        # Find active segment
        new_index = -1
        for i, segment in enumerate(self.lyrics):
            if segment.start <= position < segment.end:
                new_index = i
                break
        
        if new_index != self.active_segment_index:
            self.active_segment_index = new_index
            self._highlight_active_segment()
    
    def _highlight_active_segment(self) -> None:
        """Highlight the active segment and scroll to it."""
        content = self.query_one("#lyrics-content", Container)
        
        # Remove previous highlights
        for widget in content.query(".lyric-segment"):
            widget.remove_class("active")
        
        # Highlight active segment
        if self.active_segment_index >= 0:
            try:
                active = content.query_one(f"#lyric-{self.active_segment_index}")
                active.add_class("active")
                
                # Scroll to center active segment
                scroll = self.query_one("#lyrics-scroll", VerticalScroll)
                scroll.scroll_to_widget(active, animate=True, center=True)
            except Exception as e:
                logger.error(f"Error highlighting segment: {e}")
    
    def cleanup(self) -> None:
        """Cleanup when view is hidden."""
        if self._update_timer:
            self._update_timer.stop()
```

## Data Models

### LyricSegment

The `LyricSegment` dataclass represents a single timestamped lyric fragment:

- `start: float` - Start time in seconds
- `end: float` - End time in seconds  
- `text: str` - Transcribed text content

Segments are ordered chronologically and stored as JSON in the cache.

### Cache File Format

```json
[
  {
    "start": 0.0,
    "end": 3.5,
    "text": "Welcome to the show"
  },
  {
    "start": 3.5,
    "end": 7.2,
    "text": "Let's get started with the music"
  }
]
```

Cache files are named using MD5 hash of the track file path: `<hash>.json`

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Active segment matches playback position

*For any* track with lyrics and any playback position, the highlighted segment should be the one whose start and end times contain the current playback position.

**Validates: Requirements 1.3, 5.1**

### Property 2: Auto-scroll keeps active segment visible

*For any* track with lyrics, when the active segment changes during playback, the lyrics panel should scroll to keep the active segment within the visible area.

**Validates: Requirements 1.4, 5.3**

### Property 3: Uncached tracks trigger transcription

*For any* track without cached lyrics, selecting that track should initiate a transcription process using the Whisper model.

**Validates: Requirements 2.1**

### Property 4: Loading indicator displays during transcription

*For any* transcription operation, a loading indicator should be visible from the start of transcription until completion or error.

**Validates: Requirements 2.2, 9.1**

### Property 5: Completed transcription produces timestamped lyrics

*For any* successful transcription, the output should be a list of segments where each segment has a start time, end time, and text content.

**Validates: Requirements 2.3**

### Property 6: Transcription errors show error UI

*For any* transcription that fails, an error message should be displayed to the user with actionable guidance.

**Validates: Requirements 2.4, 9.5**

### Property 7: Lazy model loading

*For any* first transcription request when the model is not loaded, the Whisper large-v3 model should be loaded before transcription begins.

**Validates: Requirements 2.5**

### Property 8: Transcription results are cached

*For any* track that is successfully transcribed, the lyrics should be saved to the cache directory as a JSON file.

**Validates: Requirements 3.1**

### Property 9: Cached lyrics bypass transcription

*For any* track with cached lyrics, selecting that track should load lyrics from cache without initiating transcription.

**Validates: Requirements 3.2**

### Property 10: Cache key is MD5 hash of track path

*For any* track file path, the cache key used for storing and retrieving lyrics should be the MD5 hash of that path.

**Validates: Requirements 3.3**

### Property 11: Cache format round-trip

*For any* list of lyric segments, saving to cache and then loading from cache should produce an equivalent list of segments with the same start times, end times, and text content.

**Validates: Requirements 3.5**

### Property 12: Language auto-detection

*For any* audio transcription without a specified language parameter, the Whisper model should automatically detect the language.

**Validates: Requirements 4.3**

### Property 13: Active segment styling

*For any* segment that is currently active based on playback position, that segment should have distinct highlighting applied (bright orange, bold).

**Validates: Requirements 5.2, 10.3**

### Property 14: Paused playback preserves highlight

*For any* track with lyrics, pausing playback should maintain the current active segment highlight without changing it.

**Validates: Requirements 5.4**

### Property 15: Track selection loads lyrics

*For any* track in the library, pressing Enter on that track should initiate loading and displaying lyrics for that track.

**Validates: Requirements 6.3**

### Property 16: Track selection starts playback

*For any* track in the library, pressing Enter on that track should start audio playback of that track.

**Validates: Requirements 6.4**

### Property 17: Track switching cancels pending transcription

*For any* in-progress transcription, switching to a different track should cancel the pending transcription operation.

**Validates: Requirements 6.5**

### Property 18: Cached model loads locally

*For any* transcription request when the Whisper model has been previously downloaded, the model should be loaded from local cache without network requests.

**Validates: Requirements 7.2**

### Property 19: Offline operation with cached data

*For any* track with cached lyrics and a cached Whisper model, the lyrics feature should function without requiring network connectivity.

**Validates: Requirements 7.4, 7.5**

### Property 20: Transcription status includes track name

*For any* track being transcribed, the status message should include the track name to inform the user which track is being processed.

**Validates: Requirements 9.3**

### Property 21: Completion hides loading indicator

*For any* transcription that completes successfully, the loading indicator should be hidden and the lyrics should be displayed.

**Validates: Requirements 9.4**

### Property 22: Each segment on separate line

*For any* list of lyric segments being displayed, each segment should be rendered on its own line in the lyrics panel.

**Validates: Requirements 10.1**

### Property 23: Inactive segments have dimmed styling

*For any* segment that is not currently active, that segment should be displayed with dimmed orange styling.

**Validates: Requirements 10.4**

## Error Handling

### Transcription Errors

- **File not found**: Display "Audio file not found" with suggestion to refresh library
- **Unsupported format**: Display "Audio format not supported by Whisper" with list of supported formats
- **Model download failure**: Display "Failed to download Whisper model" with network troubleshooting tips
- **Transcription timeout**: Display "Transcription timed out" with suggestion to try a shorter track
- **Out of memory**: Display "Insufficient memory for transcription" with suggestion to close other applications

### Cache Errors

- **Cache directory creation failure**: Log error and continue without caching
- **Cache write failure**: Log error but display lyrics normally
- **Cache read failure**: Log error and fall back to transcription
- **Corrupted cache file**: Delete corrupted file and re-transcribe

### Playback Synchronization Errors

- **Invalid segment timestamps**: Skip invalid segments and continue with valid ones
- **Playback position unavailable**: Disable highlighting until position is available
- **Segment index out of bounds**: Reset to first segment

All errors are logged to `~/.local/share/sigplay/sigplay.log` with full stack traces for debugging.

## Testing Strategy

### Unit Testing

Unit tests will verify specific behaviors and edge cases:

- **LyricsService**:
  - Cache key generation from track paths
  - Cache directory creation
  - JSON serialization/deserialization of segments
  - Model lazy loading behavior
  - Error handling for missing files

- **LyricsView**:
  - Track list rendering
  - Empty state display
  - Segment rendering
  - Active segment index calculation

- **LyricSegment**:
  - Dataclass instantiation
  - JSON conversion

### Property-Based Testing

Property-based tests will verify universal properties across many inputs using the Hypothesis library:

- **Property tests** will be configured to run a minimum of 100 iterations
- Each property-based test will be tagged with a comment referencing the design document property
- Tag format: `# Feature: lyrics-view, Property {number}: {property_text}`

Property tests will cover:

- Cache round-trip consistency (Property 11)
- Active segment calculation for various playback positions (Property 1)
- Cache key uniqueness and determinism (Property 10)
- Segment ordering and timestamp validity (Property 5)
- Error handling for invalid inputs (Property 6)

### Integration Testing

Integration tests will verify end-to-end workflows:

- Full transcription workflow from audio file to cached lyrics
- View switching and track selection
- Playback synchronization with lyrics display
- Error recovery and retry mechanisms

### Testing Framework

- **Unit tests**: pytest
- **Property-based tests**: Hypothesis
- **Test location**: `tests/` directory with structure mirroring source code
- **Coverage target**: 80% code coverage for core logic

## Performance Considerations

### Model Loading

- **First load**: 2-5 seconds to load large-v3 model into memory (~1.5 GB)
- **Memory usage**: ~1.5 GB for model, ~500 MB for inference
- **Optimization**: Model stays loaded for session duration (lazy loading pattern)

### Transcription Performance

- **Processing time**: ~30-60 seconds for a 3-minute song on CPU
- **CPU usage**: 80-100% during transcription (background thread)
- **Optimization**: Run in background thread to keep UI responsive

### Cache Performance

- **Cache lookup**: <1ms (file existence check + MD5 hash)
- **Cache read**: <10ms for typical lyrics file (5-10 KB)
- **Cache write**: <20ms for typical lyrics file
- **Storage**: ~5-10 KB per track (JSON format)

### UI Responsiveness

- **Active segment update**: Every 0.5 seconds (timer interval)
- **Scroll animation**: 200ms smooth scroll to active segment
- **Rendering**: Lazy rendering of lyrics (only visible segments)

### Optimization Strategies

1. **Background processing**: All transcription in separate thread
2. **Persistent cache**: Avoid re-transcription on subsequent plays
3. **Lazy model loading**: Only load model when first needed
4. **Efficient segment lookup**: Binary search for active segment (O(log n))
5. **Debounced scrolling**: Prevent excessive scroll updates

## Dependencies

### New Dependencies

```toml
[project.dependencies]
faster-whisper = ">=1.1.0"  # Optimized Whisper implementation
```

### Dependency Justification

- **faster-whisper**: Provides 4x faster transcription than original Whisper with lower memory usage through CTranslate2 optimization and int8 quantization

### Installation

```bash
uv add faster-whisper
```

The faster-whisper library will automatically download the Whisper model on first use and cache it locally in `~/.cache/huggingface/hub/`.

## Future Enhancements

### Potential Improvements

1. **Model size configuration**: Allow users to choose model size via environment variable
2. **Manual lyrics editing**: Allow users to correct transcription errors
3. **Lyrics export**: Export lyrics to .lrc or .srt format
4. **Multi-language support**: Better handling of non-English tracks
5. **Real-time transcription**: Show lyrics as they're being generated
6. **Karaoke mode**: Highlight words instead of segments
7. **Lyrics search**: Search across all cached lyrics
8. **GPU acceleration**: Use CUDA if available for faster transcription

### Known Limitations

1. **Instrumental tracks**: Will produce empty or nonsensical lyrics
2. **Background noise**: May affect transcription accuracy
3. **Multiple speakers**: No speaker diarization (all lyrics merged)
4. **Singing vs speech**: Whisper is trained on speech, may struggle with singing
5. **Memory requirements**: Large model requires ~1.5 GB RAM
