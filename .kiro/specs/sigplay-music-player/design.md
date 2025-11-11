# Design Document

## Overview

SIGPLAY is a Textual-based TUI music player with a retro-modern aesthetic. The application uses a warm orange color scheme inspired by vintage computing terminals while maintaining modern usability standards. The architecture follows Textual's reactive programming model with a main app class managing multiple view screens that users can cycle through using Tab navigation.

The initial implementation focuses on establishing the UI framework with placeholder content for the three main views (Library, Now Playing, and Visualizer), vim-style navigation, and the distinctive visual identity with ASCII art branding.

## Architecture

### Application Structure

```
SIGPLAY (Textual App)
├── Custom CSS Theme (retro-modern orange palette)
├── Header (Static - ASCII art)
├── Content Area (Dynamic - switches between views)
│   ├── LibraryView
│   ├── NowPlayingView
│   └── VisualizerView
└── Footer (Static - command help)
```

### Component Hierarchy

- **SigplayApp**: Main Textual App class
  - Manages application lifecycle
  - Handles global keybindings (Tab, q)
  - Maintains current view state
  - Applies custom CSS theme

- **Header Widget**: Static header component
  - Displays SIGPLAY ASCII art
  - Uses orange color scheme
  - Remains visible across all views

- **ContentContainer**: Uses Textual's built-in `ContentSwitcher` or `TabbedContent` widget
  - Hosts one active view at a time
  - Manages view transitions
  - Maintains view state

- **View Widgets**: Individual screen components
  - LibraryView: List-based interface with vim navigation
  - NowPlayingView: Track information display
  - VisualizerView: Audio visualization display

- **Footer Widget**: Static footer component
  - Shows current view indicator
  - Displays keyboard shortcuts
  - Updates based on active view

## Components and Interfaces

### SigplayApp (Main Application)

**Responsibilities:**
- Initialize Textual application
- Load and apply custom CSS theme
- Compose UI layout (Header, Content, Footer)
- Handle global keyboard events
- Manage view cycling logic

**Key Methods:**
```python
compose() -> ComposeResult
    # Yields Header, ContentContainer, Footer widgets

on_mount() -> None
    # Initialize default view (Library)

action_quit() -> None
    # Handle 'q' key press, exit application

action_cycle_view() -> None
    # Handle Tab key press, cycle to next view

switch_view(view_name: str) -> None
    # Change active view in content container
```

**Keybindings:**
- `q`: Quit application
- `Tab`: Cycle through views

### Header Widget

**Responsibilities:**
- Display SIGPLAY ASCII art logo
- Apply orange color styling

**Implementation:**
- Uses Textual's built-in `Static` widget
- ASCII art stored as multi-line string constant
- Styled via CSS with orange foreground color

**ASCII Art Design:**
```
 ███████╗██╗ ██████╗ ██████╗ ██╗      █████╗ ██╗   ██╗
 ██╔════╝██║██╔════╝ ██╔══██╗██║     ██╔══██╗╚██╗ ██╔╝
 ███████╗██║██║  ███╗██████╔╝██║     ███████║ ╚████╔╝ 
 ╚════██║██║██║   ██║██╔═══╝ ██║     ██╔══██║  ╚██╔╝  
 ███████║██║╚██████╔╝██║     ███████╗██║  ██║   ██║   
 ╚══════╝╚═╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   
```

### Footer Widget

**Responsibilities:**
- Display current view name
- Show available keyboard shortcuts
- Update dynamically based on context

**Implementation:**
- Uses Textual's built-in `Footer` widget with custom bindings display
- Displays: `[View: Library] | Tab: Switch View | q: Quit | j/k: Navigate`
- Styled with orange accents for key indicators via CSS

### LibraryView Widget

**Responsibilities:**
- Display list of music tracks (placeholder data)
- Handle vim-style navigation (j/k keys)
- Highlight selected track
- Show track metadata

**Implementation:**
- Uses Textual's built-in `ListView` and `ListItem` widgets
- Placeholder data: 5-10 sample tracks with artist/album info
- Vim navigation via key event handlers mapped to ListView actions
- Visual selection indicator with orange highlight using CSS

**Key Methods:**
```python
on_mount() -> None
    # Load placeholder track data

on_key(event: Key) -> None
    # Handle j/k navigation keys

action_move_up() -> None
    # Move selection up (k key)

action_move_down() -> None
    # Move selection down (j key)
```

**Placeholder Data Structure:**
```python
tracks = [
    {"title": "Track Name", "artist": "Artist Name", "album": "Album Name", "duration": "3:45"},
    # ... more sample tracks
]
```

### NowPlayingView Widget

**Responsibilities:**
- Display currently playing track information
- Show playback progress (placeholder)
- Display track metadata

**Implementation:**
- Uses Textual's built-in `Container` widget with nested `Static` widgets for text
- Uses Textual's built-in `ProgressBar` widget for playback progress (placeholder)
- Placeholder content showing sample track
- Large text display for track title using `Static` with custom styling

**Layout:**
```
┌─────────────────────────────────┐
│  Now Playing                    │
│                                 │
│  ♪ Sample Track Title           │
│  Artist: Sample Artist          │
│  Album: Sample Album            │
│                                 │
│  [████████░░░░░░░░] 2:34 / 4:12 │
└─────────────────────────────────┘
```

### VisualizerView Widget

**Responsibilities:**
- Display audio visualization (placeholder pattern)
- Update animation periodically
- Use retro-modern color scheme

**Implementation:**
- Uses Textual's built-in `Static` widget with periodic content updates
- Placeholder: animated ASCII bar pattern or waveform
- Uses Textual's `set_interval()` for animation timing
- Orange color gradient for visual elements via CSS

**Placeholder Pattern:**
- Simple bar graph that animates up/down using ASCII characters
- Or scrolling waveform pattern
- Updates every 100-200ms for smooth animation

## Data Models

### Track Model (Placeholder)

```python
@dataclass
class Track:
    title: str
    artist: str
    album: str
    duration: str  # Format: "MM:SS"
    file_path: str = ""  # Empty for placeholder
```

### ViewState Enum

```python
class ViewState(Enum):
    LIBRARY = "library"
    NOW_PLAYING = "now_playing"
    VISUALIZER = "visualizer"
```

### AppState

```python
@dataclass
class AppState:
    current_view: ViewState
    selected_track_index: int = 0
    # Future: playback state, volume, etc.
```

## Styling and Theme

### Color Palette

**Primary Colors:**
- Orange: `#ff8c00` (dark orange) - primary accent
- Amber: `#ffb347` (light orange) - highlights
- Burnt Orange: `#cc5500` - darker accents
- Cream: `#fff8dc` - text on dark backgrounds
- Dark Gray: `#1a1a1a` - background
- Medium Gray: `#2d2d2d` - secondary background

**Usage:**
- Background: Dark Gray
- Text: Cream
- Accents/Borders: Orange
- Highlights/Selection: Amber
- Headers: Burnt Orange

### CSS Structure

```css
/* Global theme */
Screen {
    background: #1a1a1a;
}

/* Header styling */
#header {
    background: #2d2d2d;
    color: #ff8c00;
    text-align: center;
    height: auto;
    border: solid #cc5500;
}

/* Footer styling */
#footer {
    background: #2d2d2d;
    color: #fff8dc;
    height: 3;
    border: solid #cc5500;
}

/* View containers */
.view-container {
    background: #1a1a1a;
    border: solid #ff8c00;
}

/* Selection highlight */
.selected {
    background: #ff8c00;
    color: #1a1a1a;
}

/* List items */
.track-item {
    color: #fff8dc;
}

.track-item:hover {
    background: #2d2d2d;
}
```

## Error Handling

### Keyboard Event Handling

- Invalid key presses are silently ignored
- No error messages for unbound keys
- Graceful degradation if view switching fails

### View Switching

- If view fails to load, remain on current view
- Log error to console (development mode)
- No user-facing error messages in initial version

### Application Lifecycle

- Clean shutdown on 'q' key press
- Textual handles most cleanup automatically
- No persistent state to save in initial version

## Testing Strategy

### Manual Testing Focus

Given the visual nature of the TUI and placeholder content, initial testing will be primarily manual:

1. **Visual Verification:**
   - Launch app and verify ASCII art displays correctly
   - Check color scheme matches retro-modern orange palette
   - Verify all three views are accessible

2. **Navigation Testing:**
   - Test Tab key cycles through all views in order
   - Test vim keys (j/k) work in Library view
   - Verify 'q' key exits cleanly

3. **Layout Testing:**
   - Test in different terminal sizes
   - Verify responsive behavior
   - Check text wrapping and overflow handling

4. **Cross-Terminal Testing:**
   - Test in common terminals (iTerm2, Terminal.app, GNOME Terminal, etc.)
   - Verify color rendering
   - Check ASCII art rendering

### Future Testing Considerations

- Unit tests for view switching logic
- Unit tests for keyboard event handlers
- Integration tests for app lifecycle
- Snapshot tests for UI layouts (using Textual's testing tools)

## Implementation Notes

### Textual Framework Usage

- Use Textual 0.60+ features
- Maximize use of built-in widgets (Static, ListView, ListItem, ProgressBar, Footer, Container, ContentSwitcher)
- Leverage reactive attributes for state management
- Use CSS for all styling (no inline styles)
- Follow Textual's widget composition patterns
- Avoid custom widget implementations where built-in widgets suffice

### Development Workflow

1. Create base app structure with Header/Footer
2. Implement view switching mechanism
3. Build individual view widgets with placeholder content
4. Apply CSS theme
5. Add keyboard navigation
6. Polish and refine visuals

### Dependencies

Current dependencies from pyproject.toml:
- `textual[syntax]>=6.5.0` - Main framework
- `textual-dev>=1.8.0` - Development tools

No additional dependencies needed for initial implementation.

### File Structure

```
sigplay/
├── main.py              # Entry point, SigplayApp class
├── views/
│   ├── __init__.py
│   ├── library.py       # LibraryView widget
│   ├── now_playing.py   # NowPlayingView widget
│   └── visualizer.py    # VisualizerView widget
├── widgets/
│   ├── __init__.py
│   ├── header.py        # Header widget
│   └── footer.py        # Footer widget
├── styles/
│   └── app.tcss         # Textual CSS file
└── models/
    ├── __init__.py
    └── track.py         # Track dataclass
```

## Future Enhancements

While not part of the initial implementation, these design considerations support future expansion:

- Audio playback integration (pygame, python-vlc, or mpv)
- File system scanning for music library
- Playlist management
- Real-time audio visualization using FFT
- Configuration file support
- Keyboard shortcut customization
- Multiple color themes
- Search and filter functionality
