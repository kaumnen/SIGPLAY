---
inclusion: always
---

# Technology Stack

## Core Technologies

- **Python**: 3.13+ (specified in pyproject.toml)
- **Framework**: Textual 6.5.0+ - TUI framework for terminal applications
- **Package Manager**: `uv` - see uv-steering.md for dependency management rules
- **Audio**: miniaudio for playback (MP3, WAV, OGG, FLAC support)
- **Audio Processing**: Pedalboard for DJ mixing and effects
- **AI Agent**: Strands Agents with OpenRouter (user-selectable models) for natural language DJ mixing
- **FFT**: numpy for frequency spectrum analysis
- **Metadata**: mutagen for reading audio file tags

## Key Dependencies

```toml
textual[syntax]>=6.5.0          # Main TUI framework with syntax highlighting
textual-dev>=1.8.0              # Development tools (console, run --dev)
miniaudio>=1.61                 # Audio playback and streaming
numpy>=1.26.0                   # Audio buffer processing and RMS calculations
mutagen>=1.47.0                 # Audio metadata extraction
pedalboard>=0.9.19              # Audio effects and mixing (Floppy Mix feature)
strands-agents[openai]>=1.17.0  # AI agent framework with OpenAI support
librosa>=0.11.0                 # Audio analysis (BPM detection, time-stretching)
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
    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
    ]
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Enter value:")
            yield Input(id="input")
            yield Button("OK")
    
    def on_mount(self) -> None:
        """Focus input on mount."""
        self.call_after_refresh(self._focus_input)
    
    def _focus_input(self) -> None:
        """Focus the input after screen is fully rendered."""
        input_widget = self.query_one("#input", Input)
        input_widget.focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        input_value = self.query_one("#input", Input).value
        self.dismiss(input_value)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        self.dismiss(event.value.strip() if event.value.strip() else None)
    
    def on_key(self, event: events.Key) -> None:
        """Prevent key events from propagating to parent app."""
        if event.key not in ("escape",):
            event.stop()

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

# Deferred focus after screen render
self.call_after_refresh(self._focus_input)

# Prevent key event propagation
event.prevent_default()
event.stop()
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

### Agent Context Pattern
```python
class MixContext:
    """Context for a single mix operation to avoid global state."""
    
    def __init__(self):
        self.audio_cache: dict = {}
        self.mix_segments: list = []
    
    def clear(self):
        self.audio_cache.clear()
        self.mix_segments.clear()

_mix_context = MixContext()
```

### Progress Hook Pattern
```python
from strands.hooks import HookProvider, HookRegistry, BeforeToolCallEvent, AfterToolCallEvent

class ProgressHook(HookProvider):
    """Hook to stream progress updates during agent execution."""
    
    TOOL_DESCRIPTIONS = {
        'load_audio_track': '📂 Loading track',
        'apply_effects': '🎛️ Applying effects',
        'render_final_mix': '💾 Rendering final mix',
    }
    
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.on_tool_start)
        registry.add_callback(AfterToolCallEvent, self.on_tool_end)
    
    def on_tool_start(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use.get('name', 'unknown')
        description = self.TOOL_DESCRIPTIONS.get(tool_name, f'🔧 {tool_name}')
        print(f"STATUS: {description}...", file=sys.stderr, flush=True)
    
    def on_tool_end(self, event: AfterToolCallEvent) -> None:
        tool_name = event.tool_use.get('name', 'unknown')
        logger.debug(f"Tool completed: {tool_name}")

# Register hooks with agent
agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[...],
    hooks=[ProgressHook()]
)
```

### Agent Script Pattern
```python
from strands import Agent, tool
from strands.models.openai import OpenAIModel

@tool
def load_audio_track(track_path: str, track_id: str) -> str:
    """Load an audio track into memory for processing."""
    return f"✓ Loaded {track_id}: duration, sample_rate, channels"

@tool
def detect_bpm(track_id: str) -> str:
    """Detect the BPM (tempo) of a loaded track using beat tracking."""
    return f"✓ {track_id} BPM: 120.0 (X beats detected)"

@tool
def time_stretch_to_bpm(track_id: str, target_bpm: float, source_bpm: float | None = None) -> str:
    """Time-stretch a track to match a target BPM without changing pitch.
    
    Guardrails:
    - Target BPM must be between 60-200
    - Maximum stretch is ±15% (beyond this sounds bad)
    - Skips if already within 5% of target
    """
    return f"✓ Stretched {track_id}: source → target BPM"

@tool
def apply_effects(
    track_id: str,
    reverb_room_size: float = 0.0,
    compressor_threshold_db: float = 0.0,
    chorus_rate_hz: float = 0.0,
    delay_seconds: float = 0.0,
    highpass_cutoff_hz: float = 0.0,
    lowpass_cutoff_hz: float = 0.0,
    bass_boost_db: float = 0.0,
    treble_boost_db: float = 0.0,
    gain_db: float = 0.0,
    phaser_rate_hz: float = 0.0,
    distortion_drive_db: float = 0.0,
    noise_gate_threshold_db: float = 0.0,
    pitch_shift_semitones: float = 0.0
) -> str:
    """Apply audio effects to a loaded track.
    
    All parameters are optional (0 = off). Examples:
    - Boost bass: bass_boost_db=4 to 6
    - Movement: phaser_rate_hz=0.5 to 1.5
    - Warmth: distortion_drive_db=10 to 15
    - Clean noise: noise_gate_threshold_db=-40 to -50
    - Harmonic mixing: pitch_shift_semitones=+/-7 (fifth) or +/-12 (octave)
    """
    return f"✓ Applied effects to {track_id}"

@tool
def apply_ladder_filter(
    track_id: str,
    mode: str = "LPF24",
    cutoff_hz: float = 1000.0,
    resonance: float = 0.0
) -> str:
    """Apply Moog-style ladder filter with resonance.
    
    Modes: "LPF12", "LPF24", "HPF12", "HPF24", "BPF12", "BPF24"
    """
    return f"✓ Applied ladder filter to {track_id}"

@tool
def apply_parallel_effects(
    track_id: str,
    dry_gain_db: float = 0.0,
    wet_reverb_room_size: float = 0.0,
    wet_delay_seconds: float = 0.0,
    wet_gain_db: float = -6.0
) -> str:
    """Apply parallel effects processing (dry/wet mix)."""
    return f"✓ Applied parallel effects to {track_id}"

@tool
def apply_creative_effects(
    track_id: str,
    bitcrush_bit_depth: int = 0,
    clipping_threshold_db: float = 0.0
) -> str:
    """Apply creative lo-fi and distortion effects."""
    return f"✓ Applied creative effects to {track_id}"

@tool
def automate_filter_sweep(
    track_id: str,
    start_cutoff_hz: float = 200.0,
    end_cutoff_hz: float = 5000.0,
    filter_mode: str = "LPF24",
    resonance: float = 0.5
) -> str:
    """Automate a filter sweep across the entire track."""
    return f"✓ Applied filter sweep to {track_id}"

@tool
def add_track_to_mix(
    track_id: str,
    crossfade_duration: float = 0.0,
    start_time: float = 0.0,
    end_time: float | None = None
) -> str:
    """Add a processed track to the final mix with optional crossfade."""
    return f"✓ Added {track_id} to mix"

@tool
def render_final_mix(output_path: str, normalize: bool = True) -> str:
    """Render and save the final mix."""
    return f"✓ Mix saved to {output_path}"

# Configure agent with OpenRouter (OpenAI-compatible)
api_key = os.environ.get('OPENROUTER_API_KEY')
model_id = os.environ.get('SIGPLAY_MIX_MODEL_ID', os.environ.get('OPENROUTER_MODEL', 'anthropic/claude-haiku-4.5'))

model = OpenAIModel(
    client_args={
        "api_key": api_key,
        "base_url": "https://openrouter.ai/api/v1"
    },
    model_id=model_id,
    max_tokens=8192
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[
        load_audio_track, detect_bpm, time_stretch_to_bpm,
        apply_effects, apply_ladder_filter, apply_parallel_effects,
        apply_creative_effects, automate_filter_sweep,
        add_track_to_mix, render_final_mix
    ],
    hooks=[ProgressHook()]
)

result = agent(prompt)
print(json.dumps({'status': 'success', 'result': result}))
```

### Agent Client Pattern
```python
# Create service to invoke agent (e.g., services/dj_agent_client.py)
class DJAgentClient:
    AGENT_TIMEOUT = 300  # 5 minutes
    
    async def create_mix(
        self,
        tracks: list[Track],
        instructions: str,
        progress_callback: Callable[[str], None] | None = None
    ) -> str:
        # Validate inputs
        if not tracks:
            raise ValueError("At least one track must be provided")
        
        # Prepare input JSON with track metadata
        request_data = {
            'tracks': [{'path': t.file_path, 'title': t.title, ...} for t in tracks],
            'instructions': instructions,
            'output_dir': str(temp_dir)
        }
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(request_data, f)
            request_file = f.name
        
        # Launch agent subprocess
        agent_process = await asyncio.create_subprocess_exec(
            'uv', 'run', 'floppy_mix_agent.py', request_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Stream progress updates from stderr
        async def read_stderr():
            async for line in agent_process.stderr:
                if line.startswith(b'STATUS:'):
                    progress_callback(line[7:].decode().strip())
        
        # Wait with timeout
        await asyncio.wait_for(agent_process.wait(), timeout=self.AGENT_TIMEOUT)
        
        # Parse JSON response from stdout
        response = json.loads(stdout)
        return response['mix_file_path']
```

### Agent System Prompt Best Practices

When writing system prompts for agents:
- **Describe the workflow**: Explain the sequence of tool calls needed
- **List available tools**: Document each tool with parameters and purpose
- **Provide examples**: Show typical tool call sequences for common scenarios
- **Map user intent to tools**: Guide how to interpret natural language into tool parameters
- **Include best practices**: Share domain expertise (e.g., "use 2-4 second crossfades")
- **Keep it concise**: Focus on tool usage, not implementation details

### Error Handling for OpenRouter
- Check for `OPENROUTER_API_KEY` → API key not configured (prompt user with modal)
- Check for `401` or `unauthorized` → Invalid/expired key
- Check for `402` or `insufficient credits` or `quota` → Credits exhausted
- Check for `model not found` → Model not available
- Provide user-friendly error messages with actionable steps
- Include links to OpenRouter dashboard for key management and credits

### Environment Variables
- `OPENROUTER_API_KEY` (required): API key from https://openrouter.ai/keys
  - Can be set via environment variable or provided at runtime via modal prompt
  - Session-level API keys stored in app state for current session only
- `SIGPLAY_MIX_MODEL_ID` (optional): Model to use for Floppy Mix (default: `anthropic/claude-haiku-4.5`)
  - Can be set via environment variable or provided at runtime via modal prompt
  - Session-level model IDs stored in app state for current session only
  - Available models: https://openrouter.ai/models
- `OPENROUTER_MODEL` (optional): Legacy alias for `SIGPLAY_MIX_MODEL_ID`

## Performance Considerations

- Target 30 FPS for visualizer updates
- Use `set_interval()` for periodic updates, not tight loops
- Debounce expensive operations (FFT calculations, file I/O)
- Monitor playback state via AudioPlayer.get_state() instead of polling
- Profile CPU usage and adapt frame rates dynamically
- Agent operations have 5-minute timeout to prevent hanging
