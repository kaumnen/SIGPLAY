---
inclusion: always
---

# Technology Stack

## Core Technologies

- **Python**: 3.13+ (specified in `.python-version`)
- **Framework**: Textual 6.5.0+ - TUI framework for terminal applications
- **Package Manager**: `uv` - see uv-steering.md for dependency management rules
- **Audio**: pygame.mixer for playback (MP3, WAV, OGG, FLAC support)
- **FFT**: numpy for frequency spectrum analysis

## Key Dependencies

```toml
textual[syntax]>=6.5.0  # Main TUI framework with syntax highlighting
textual-dev>=1.8.0      # Development tools (console, run --dev)
pygame>=2.6.0           # Audio playback via pygame.mixer
numpy>=2.0.0            # FFT calculations for visualizer
```

## Running & Testing

```bash
# Run application
uv run main.py

# Development mode with live reload and console
uv run textual run --dev main.py

# Debug console (run in separate terminal)
uv run textual console

# Add new dependency
uv add <package>

# Sync after pulling changes
uv sync
```

## Textual Framework Patterns

### Widget Composition
- Inherit from `Widget`, `Static`, `Container`, or `ListView` based on needs
- Use `compose()` method to yield child widgets
- Never instantiate widgets in `__init__`, always in `compose()`

### Reactive Programming
```python
from textual.reactive import reactive

class MyWidget(Widget):
    current_track: reactive[str | None] = reactive(None)
    
    def watch_current_track(self, new_value: str | None) -> None:
        # Called automatically when current_track changes
        self.refresh()
```

### Message Handling
```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    # Handle button press
    pass

def on_list_view_selected(self, event: ListView.Selected) -> None:
    # Handle list selection
    pass
```

### Styling Rules
- **NEVER** use inline styles in Python code
- All styling in `styles/app.tcss` using Textual CSS syntax
- Use widget IDs (`#my-widget`) and classes (`.my-class`) for selectors
- Reference color palette variables defined in app.tcss
- Built-in widgets to prefer: `Static`, `ListView`, `ListItem`, `ProgressBar`, `Footer`, `Container`, `ContentSwitcher`, `Label`

### Common Patterns
```python
# Updating UI from background thread
self.call_from_thread(self.update_display, data)

# Posting messages between widgets
self.post_message(self.TrackChanged(track))

# Setting timers
self.set_interval(1.0, self.update_progress)

# Querying widgets
progress_bar = self.query_one("#progress", ProgressBar)
```

## Code Style

### Type Hints
- Use type hints for all function parameters and return values
- Use `from __future__ import annotations` for forward references
- Prefer `str | None` over `Optional[str]` (Python 3.10+ union syntax)

### Dataclasses
```python
from dataclasses import dataclass

@dataclass
class Track:
    path: str
    title: str
    artist: str | None = None
```

### Error Handling
- Catch specific exceptions, not bare `except:`
- Log errors to file: `~/.local/share/sigplay/sigplay.log`
- Show user-friendly notifications via `self.notify(message, severity="error")`
- Never let exceptions crash the app

### Async/Threading
- Use `asyncio` for Textual's async methods (`on_mount`, etc.)
- Use `threading.Thread` for blocking operations (audio playback, file scanning)
- Use `call_from_thread()` to update UI from background threads

## Performance Considerations

- Target 30 FPS for visualizer updates
- Use `set_interval()` for periodic updates, not tight loops
- Debounce expensive operations (FFT calculations, file I/O)
- Check `pygame.mixer.music.get_busy()` instead of polling continuously
- Profile CPU usage and adapt frame rates dynamically
