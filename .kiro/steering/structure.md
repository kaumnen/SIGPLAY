# Project Structure

## Directory Organization

```
sigplay/
├── .git/                # Version control
├── .kiro/               # Kiro IDE configuration
│   ├── specs/           # Feature specifications
│   └── steering/        # AI assistant guidance rules
├── .venv/               # Python virtual environment (managed by uv)
├── main.py              # Application entry point
├── views/               # View widgets for different screens
│   ├── library.py       # Music library list view
│   ├── now_playing.py   # Current track display
│   └── visualizer.py    # Audio visualization
├── widgets/             # Reusable UI components
│   ├── header.py        # ASCII art header
│   └── footer.py        # Command help footer
├── styles/              # Textual CSS theme files
│   └── app.tcss         # Main application styles
├── models/              # Data models and types
│   └── track.py         # Track dataclass, ViewState enum
├── pyproject.toml       # Project metadata and dependencies
├── uv.lock              # Locked dependency versions
└── README.md            # Project documentation
```

## Architecture Patterns

### Component Hierarchy

```
SigplayApp (Main App)
├── Header (Static widget with ASCII art)
├── ContentSwitcher (View container)
│   ├── LibraryView (ListView with track list)
│   ├── NowPlayingView (Container with track info)
│   └── VisualizerView (Static with animated content)
└── Footer (Command help display)
```

### Key Responsibilities

- **main.py**: Application lifecycle, global keybindings (Tab, q), view switching logic
- **views/**: Individual screen implementations with view-specific logic
- **widgets/**: Reusable components shared across views
- **styles/**: All visual styling in Textual CSS format
- **models/**: Data structures (Track, ViewState, AppState)

## File Naming Conventions

- Snake_case for Python files: `now_playing.py`, `track.py`
- Lowercase for directories: `views/`, `widgets/`, `styles/`
- `.tcss` extension for Textual CSS files

## Import Organization

Each package should have an `__init__.py` for clean imports:

```python
# views/__init__.py
from .library import LibraryView
from .now_playing import NowPlayingView
from .visualizer import VisualizerView
```
