---
inclusion: always
---

# Technology Stack

## Core Technologies

- **Python**: 3.13+ (specified in `.python-version`)
- **Framework**: Textual 6.5.0+ - TUI framework for terminal applications
- **Package Manager**: `uv` - see uv-steering.md for dependency management rules
- **Audio**: miniaudio for playback (MP3, WAV, OGG, FLAC support)
- **Audio Processing**: Pedalboard for DJ mixing and effects
- **AI Agent**: Strands Agents with AWS Bedrock (Claude) for natural language DJ mixing
- **FFT**: numpy for frequency spectrum analysis
- **Metadata**: mutagen for reading audio file tags

## Key Dependencies

```toml
textual[syntax]>=6.5.0  # Main TUI framework with syntax highlighting
textual-dev>=1.8.0      # Development tools (console, run --dev)
miniaudio>=1.61         # Audio playback and streaming
numpy>=1.26.0           # Audio buffer processing and RMS calculations
mutagen>=1.47.0         # Audio metadata extraction
pedalboard>=0.9.19      # Audio effects and mixing (Floppy Mix feature)
strands-agents>=1.17.0  # AI agent framework for DJ mixing
hypothesis>=6.148.2     # Property-based testing
```

## Running & Testing

```bash
# Run application
uv run main.py

# Run via entry point
uv run sigplay

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
- Built-in widgets to prefer: `Static`, `ListView`, `ListItem`, `ProgressBar`, `Footer`, `Container`, `ContentSwitcher`, `Label`, `Button`, `Input`, `TextArea`, `LoadingIndicator`

### View Switching Pattern
```python
# Use ContentSwitcher for multiple full-screen views
with ContentSwitcher(id="view-switcher", initial="main-view"):
    yield MainView(id="main-view")
    yield FeatureView(id="feature-view")

# Switch views programmatically
switcher = self.query_one("#view-switcher", ContentSwitcher)
switcher.current = "feature-view"
```

### Modal Screens
```python
# Create modal screen for user input
class PromptScreen(ModalScreen[str | None]):
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Enter value:")
            yield Input(id="input")
            yield Button("OK")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        input_value = self.query_one("#input", Input).value
        self.dismiss(input_value)

# Use modal screen with callback
self.app.push_screen(PromptScreen(), callback=self.handle_input)
```

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
- Use `asyncio.to_thread()` for blocking operations (file scanning, background tasks)
- Use `run_worker()` for background tasks in Textual
- Use `call_from_thread()` to update UI from background threads
- Audio playback uses miniaudio's generator-based callback system (no manual threading needed)

### Subprocess Management for External Agents
```python
# Launch external Python scripts with uv
agent_process = await asyncio.create_subprocess_exec(
    'uv', 'run', 'agent_script.py', 'input.json',
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)

# Stream output asynchronously
async def read_stderr():
    async for line in agent_process.stderr:
        line_text = line.decode('utf-8').strip()
        if line_text.startswith('STATUS:'):
            progress_callback(line_text[7:].strip())

# Wait with timeout
await asyncio.wait_for(agent_process.wait(), timeout=300)
```

### Audio Playback Patterns
```python
# Stream audio file with miniaudio
stream_generator = miniaudio.stream_file(
    str(file_path),
    output_format=miniaudio.SampleFormat.SIGNED16,
    nchannels=2,
    sample_rate=44100
)

# Create playback device
device = miniaudio.PlaybackDevice(
    sample_rate=44100,
    nchannels=2,
    output_format=miniaudio.SampleFormat.SIGNED16
)

# Generator callback must use yield expressions to receive num_frames
def audio_callback_generator():
    num_frames = yield b''  # Prime the generator
    while True:
        audio_data = stream_generator.send(num_frames)
        num_frames = yield audio_data  # Yield data and receive next num_frames

# Initialize and start playback
gen = audio_callback_generator()
next(gen)  # Prime the generator
device.start(gen)
```

## Strands Agents Integration

### Agent Script Pattern
```python
# Create standalone agent script (e.g., floppy_mix_agent.py)
from strands import Agent, tool
from strands.models.bedrock import BedrockModel

@tool
def execute_python_code(code: str) -> str:
    """Execute Python code and return output."""
    result = subprocess.run([sys.executable, "-c", code], ...)
    return result.stdout

# Configure agent with AWS Bedrock
model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region="us-east-1"
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[execute_python_code, write_file, read_file]
)

# Process request and return JSON response
result = agent(prompt)
print(json.dumps({'status': 'success', 'result': result}))
```

### Agent Client Pattern
```python
# Create service to invoke agent (e.g., services/dj_agent_client.py)
class DJAgentClient:
    async def create_mix(
        self,
        tracks: list[Track],
        instructions: str,
        progress_callback: Callable[[str], None] | None = None
    ) -> str:
        # Prepare input JSON
        request_data = {...}
        
        # Launch agent subprocess
        agent_process = await asyncio.create_subprocess_exec(...)
        
        # Stream progress updates
        # Return result path
```

### Error Handling for AWS Bedrock
- Check for `UnrecognizedClientException` → API key not configured
- Check for `security token` or `bearer token` errors → Invalid/expired key
- Check for `credentials` errors → Missing credentials
- Check for `don't have access to the model` → Model access not granted
- Provide user-friendly error messages with actionable steps

## Performance Considerations

- Target 30 FPS for visualizer updates
- Use `set_interval()` for periodic updates, not tight loops
- Debounce expensive operations (FFT calculations, file I/O)
- Monitor playback state via AudioPlayer.get_state() instead of polling
- Profile CPU usage and adapt frame rates dynamically
- Agent operations have 5-minute timeout to prevent hanging
