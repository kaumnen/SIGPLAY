---
inclusion: always
---

# Project Structure & Architecture

## Directory Organization

```
sigplay/
├── main.py                  # Entry point: SigplayApp class, global keybindings, logging setup
├── floppy_mix_agent.py      # Standalone Strands Agent for DJ mixing (invoked via subprocess)
├── views/                   # Screen implementations (library, now_playing, meters, floppy_mix)
├── widgets/                 # Reusable UI components (header, track_selection_panel, etc.)
├── services/                # Business logic (audio_player, music_library, dj_agent_client)
├── models/                  # Data models (Track, Playback, Frequency, MixRequest dataclasses)
├── styles/                  # Textual CSS files (app.tcss)
├── pyproject.toml           # Dependencies managed by uv
└── uv.lock                  # Locked dependency versions
```

## Architecture Rules

### Separation of Concerns

- **main.py**: App lifecycle, global keybindings, view orchestration only
- **views/**: UI presentation and user interaction handling
- **services/**: Audio playback, file I/O, signal processing, external library integration
- **models/**: Data structures with no business logic
- **widgets/**: Reusable UI components with minimal logic
- **styles/**: All visual styling (NO inline styles in Python)

### Component Hierarchy

```
SigplayApp (main.py)
├── Header (widgets/header.py)
├── ContentSwitcher (#view-switcher)
│   ├── MainViewContainer (#main-view)
│   │   ├── Horizontal (#top-container)
│   │   │   ├── LibraryView (views/library.py)
│   │   │   └── NowPlayingView (views/now_playing.py)
│   │   └── MetersView (views/meters.py)
│   └── FloppyMixView (#floppy-mix-view)
│       ├── Header section with title and Start Mix button
│       ├── Status row with LoadingIndicator and status display
│       ├── Controls row with Save/Discard buttons
│       ├── TrackSelectionPanel (widgets/track_selection_panel.py)
│       └── InstructionsPanel (widgets/instructions_panel.py)
└── Footer (Textual built-in)
```

### When Creating New Components

- **New view**: Add to `views/` directory, inherit from Textual widget, export in `views/__init__.py`
- **New widget**: Add to `widgets/` directory if reusable across multiple views
- **New service**: Add to `services/` directory for business logic, audio processing, or external integrations
- **New model**: Add to `models/` directory as dataclass with type hints
- **New styles**: Add to `styles/app.tcss`, use CSS classes not inline styles
- **New agent**: Create standalone script at project root (e.g., `floppy_mix_agent.py`) with Strands Agent configuration

### Floppy Mix Architecture

The Floppy Mix feature is implemented as a full-screen view (`FloppyMixView`) that integrates specialized widgets:

**FloppyMixView** (`views/floppy_mix.py`)
- Full-screen container managing the entire Floppy Mix workflow
- Reactive `mixing_state` property: `"idle"`, `"mixing"`, `"previewing"`
- Orchestrates track selection, mixing, preview playback, and save/discard
- Implements cleanup pattern for resource management
- Handles modal screens for filename input

**Embedded Widgets:**

1. **TrackSelectionPanel** (`widgets/track_selection_panel.py`)
   - Displays track list with vim-style navigation (j/k)
   - Space key toggles selection with visual indicators (✓)
   - Provides `get_selected_tracks()`, `clear_selection()`, `refresh_tracks()` methods

2. **InstructionsPanel** (`widgets/instructions_panel.py`)
   - TextArea for natural language mixing instructions
   - Provides `get_instructions()`, `clear()`, `is_empty()` methods

**UI Components Managed by FloppyMixView:**
- LoadingIndicator for progress display
- Status display (Static widget)
- Start Mix button
- Save/Discard buttons (shown only during preview)
- All state transitions and button visibility

### Agent Architecture Pattern

Agents are implemented as standalone Python scripts that:
- Accept JSON input via command-line argument (file path)
- Use Strands Agents framework with OpenRouter (OpenAI-compatible API)
- Define tools using `@tool` decorator for audio processing, file I/O, etc.
- Return JSON response to stdout with `status` and result fields
- Log to `~/.local/share/sigplay/<agent_name>.log`
- Are invoked via `uv run` subprocess from service layer
- Communicate progress via stderr with `STATUS:` prefix messages
- Use `client_args` dict for OpenAI model configuration (not direct kwargs)
- Use `hooks` parameter with `HookProvider` subclasses for progress streaming
- Use context classes (e.g., `MixContext`) to avoid global state pollution

**Floppy Mix Agent Tools:**
- `load_audio_track` - Load audio file into memory cache
- `detect_bpm` - Analyze track tempo using beat tracking (librosa)
- `time_stretch_to_bpm` - Time-stretch track to target BPM (±15% max, 60-200 BPM range)
- `apply_effects` - Standard effects (reverb, compression, EQ, phaser, distortion, noise gate, pitch shift)
- `apply_ladder_filter` - Moog-style resonant filter (LPF/HPF/BPF modes)
- `apply_parallel_effects` - Dry/wet parallel processing
- `apply_creative_effects` - Lo-fi effects (bitcrush, clipping)
- `automate_filter_sweep` - Automated filter cutoff modulation
- `add_track_to_mix` - Add processed track with crossfade
- `render_final_mix` - Render and save final mix file

### Import Conventions

Each package has `__init__.py` for clean imports:

```python
# views/__init__.py
from .library import LibraryView
from .now_playing import NowPlayingView
from .visualizer import VisualizerView

# services/__init__.py
from .audio_player import AudioPlayer
from .music_library import MusicLibrary
from .spectrum_analyzer import SpectrumAnalyzer
```

Import from package level in other files:

```python
from views import LibraryView, NowPlayingView
from services import AudioPlayer, MusicLibrary
from models import Track, Playback
```

### File Naming

- Python files: `snake_case.py`
- Directories: lowercase
- Textual CSS: `.tcss` extension
- Classes: `PascalCase`
- Functions/methods: `snake_case`

### State Management

- Use Textual's reactive variables for UI state
- Pass services as dependencies to views (dependency injection pattern)
- Avoid global state except for the main App instance
- Use dataclasses for structured data passed between components

### Custom Message Pattern

Widgets can define custom messages for parent communication:

```python
class MyWidget(Widget):
    class ActionRequested(Message):
        """Posted when user requests an action."""
        def __init__(self, data: str) -> None:
            super().__init__()
            self.data = data
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_message(self.ActionRequested("data"))

# Parent handles message
def on_my_widget_action_requested(self, event: MyWidget.ActionRequested) -> None:
    # Handle the action
    pass
```

### Session State Pattern

For sensitive data that should not persist:

```python
class SigplayApp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_openrouter_key: str | None = None
    
    def _handle_api_key_input(self, api_key: str | None) -> None:
        """Store API key in session state and environment."""
        if api_key:
            self._session_openrouter_key = api_key
            os.environ['OPENROUTER_API_KEY'] = api_key
```

### Cleanup Pattern

Views should implement cleanup methods for resource management:

```python
class MyView(Container):
    def cleanup(self) -> None:
        """Called when view is hidden or app exits."""
        # Stop playback
        # Delete temporary files
        # Reset state
```

### Filename Validation Pattern

For user-provided filenames, validate and sanitize:

```python
import re

def _validate_filename(self, filename: str) -> str | None:
    """Validate and sanitize filename."""
    if not filename or not filename.strip():
        return None
    
    filename = filename.strip()
    
    # Remove extension if provided
    if filename.endswith('.wav'):
        filename = filename[:-4]
    
    # Validate: alphanumeric, spaces, hyphens, underscores only
    if not re.match(r'^[a-zA-Z0-9_\-\s]+$', filename):
        return None
    
    # Sanitize: replace spaces with underscores
    filename = re.sub(r'\s+', '_', filename)
    
    return filename
```

### Widget Initialization Pattern

Widgets should defer widget queries until after mount:

```python
class MyWidget(Container):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store data, but don't query child widgets yet
        self._child_widget: ChildWidget | None = None
    
    def on_mount(self) -> None:
        """Query child widgets after mount."""
        try:
            self._child_widget = self.query_one("#child", ChildWidget)
        except Exception as e:
            logger.error(f"Error mounting: {e}")
```

### View Lifecycle Pattern

Views should implement `on_show()` for initialization when becoming visible and `cleanup()` for resource management:

```python
class MyView(Container):
    def on_show(self) -> None:
        """Called when view becomes visible."""
        # Refresh data
        # Set initial focus
        # Update UI state
        self.call_after_refresh(self._set_initial_focus)
    
    def _set_initial_focus(self) -> None:
        """Set focus after view is fully rendered."""
        widget = self.query_one("#my-widget")
        widget.focus()
    
    def cleanup(self) -> None:
        """Called when view is hidden or app exits."""
        # Stop playback
        # Delete temporary files
        # Reset state
```

### Help Screen Pattern

For context-aware help screens that adapt to current view:

```python
class HelpScreen(ModalScreen[None]):
    """Modal screen displaying help information."""
    
    def __init__(self, view_type: str = "main") -> None:
        """Initialize help screen.
        
        Args:
            view_type: Either "main" or "floppy_mix" to show appropriate help.
        """
        super().__init__()
        self.view_type = view_type
    
    def compose(self) -> ComposeResult:
        with Container(id="help-container"):
            with VerticalScroll(id="help-scroll"):
                if self.view_type == "main":
                    yield self._compose_main_help()
                else:
                    yield self._compose_floppy_mix_help()
            yield Button("Close (Esc)", id="help-close-button", variant="primary")
    
    def _compose_main_help(self) -> Static:
        """Compose help content for main view."""
        help_text = """[bold #ff8c00]🎵 SIGPLAY - Terminal Music Player[/bold #ff8c00]
        
[bold]NAVIGATION[/bold]
  j/k         Move down/up in track list
  ..."""
        return Static(help_text, id="help-content")
    
    async def on_key(self, event) -> None:
        """Handle key events including j/k for scrolling."""
        if event.key == "escape":
            self.dismiss()
        elif event.key == "j":
            scroll = self.query_one("#help-scroll", VerticalScroll)
            scroll.scroll_down()
        elif event.key == "k":
            scroll = self.query_one("#help-scroll", VerticalScroll)
            scroll.scroll_up()

# Show help based on current view
switcher = self.query_one("#view-switcher", ContentSwitcher)
view_type = "floppy_mix" if switcher.current == "floppy-mix-view" else "main"
self.push_screen(HelpScreen(view_type=view_type))
```

### Modal Screen with Filename Input Pattern

For prompting user input with validation:

```python
class FilenamePromptScreen(ModalScreen[str | None]):
    """Modal screen to prompt user for filename."""
    
    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
    ]
    
    def compose(self) -> ComposeResult:
        with Container(id="filename-prompt-container"):
            yield Label("💾 Save Mix", id="filename-prompt-title")
            yield Label("Enter a name for your mix:", id="filename-prompt-label")
            yield Input(
                value="",
                placeholder="my_awesome_mix",
                id="filename-input"
            )
            with Horizontal(id="filename-prompt-buttons"):
                yield Button("Save", id="save-confirm-button", variant="success")
                yield Button("Cancel", id="cancel-button", variant="default")
    
    def on_mount(self) -> None:
        """Focus input on mount."""
        self.call_after_refresh(self._focus_input)
    
    def _focus_input(self) -> None:
        input_widget = self.query_one("#filename-input", Input)
        input_widget.focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-confirm-button":
            input_widget = self.query_one("#filename-input", Input)
            filename = input_widget.value.strip()
            self.dismiss(filename if filename else None)
        elif event.button.id == "cancel-button":
            self.dismiss(None)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        filename = event.value.strip()
        self.dismiss(filename if filename else None)

# Use with callback
self.app.push_screen(
    FilenamePromptScreen(),
    callback=self._handle_filename_input
)
```
