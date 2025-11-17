---
inclusion: always
---

# Project Structure & Architecture

## Directory Organization

```
sigplay/
├── main.py              # Entry point: SigplayApp class, global keybindings, logging setup
├── views/               # Screen implementations (library, now_playing, meters)
├── widgets/             # Reusable UI components (header)
├── services/            # Business logic (audio_player, music_library, spectrum_analyzer)
├── models/              # Data models (Track, Playback, Frequency dataclasses)
├── styles/              # Textual CSS files (app.tcss)
├── pyproject.toml       # Dependencies managed by uv
└── uv.lock              # Locked dependency versions
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
├── Vertical (#main-container)
│   ├── Horizontal (#top-container)
│   │   ├── LibraryView (views/library.py)
│   │   └── NowPlayingView (views/now_playing.py)
│   └── MetersView (views/meters.py)
└── Footer (Textual built-in)
```

### When Creating New Components

- **New view**: Add to `views/` directory, inherit from Textual widget, export in `views/__init__.py`
- **New widget**: Add to `widgets/` directory if reusable across multiple views
- **New service**: Add to `services/` directory for business logic, audio processing, or external integrations
- **New model**: Add to `models/` directory as dataclass with type hints
- **New styles**: Add to `styles/app.tcss`, use CSS classes not inline styles

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
