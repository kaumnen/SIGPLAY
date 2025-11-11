# Technology Stack

## Core Technologies

- **Python**: 3.13+ (specified in `.python-version`)
- **Framework**: Textual 6.5.0+ - TUI framework for building terminal applications
- **Package Manager**: `uv` (see uv-steering.md for dependency management rules)

## Dependencies

```toml
textual[syntax]>=6.5.0  # Main TUI framework
textual-dev>=1.8.0      # Development tools
```

## Project Structure

```
sigplay/
├── main.py              # Entry point, SigplayApp class
├── views/               # View widgets (library, now_playing, visualizer)
├── widgets/             # Reusable widgets (header, footer)
├── styles/              # Textual CSS files (app.tcss)
└── models/              # Data models (Track dataclass)
```

## Common Commands

```bash
# Run the application
uv run main.py

# Add dependencies
uv add <package>

# Sync dependencies from lock file
uv sync

# Development mode (with Textual dev tools)
uv run textual run --dev main.py

# Textual console for debugging
uv run textual console
```

## Styling

- All styling uses Textual CSS (`.tcss` files)
- No inline styles
- Color palette defined in `styles/app.tcss`
- Maximize use of Textual's built-in widgets (Static, ListView, ListItem, ProgressBar, Footer, Container, ContentSwitcher)

## Development Guidelines

- Use Textual's reactive programming model
- Leverage built-in widgets before creating custom ones
- Follow Textual's widget composition patterns
- Use CSS for all visual styling
