---
inclusion: always
---

# Product Overview

SIGPLAY is a terminal-based music player (TUI) built with Python's Textual framework. It features a retro-modern aesthetic with a warm orange color scheme reminiscent of vintage computing systems.

## Design Philosophy

- **Retro-modern aesthetic**: Balance nostalgia with modern usability
- **Keyboard-first**: All interactions via keyboard shortcuts, no mouse required
- **Graceful degradation**: Display user-friendly error messages, never crash
- **Performance-conscious**: Monitor CPU usage and adapt frame rates dynamically

## Color Palette

Use these exact colors consistently across all UI elements:

- **Bass/Dark Orange**: `#cc5500` - Used for bass frequencies, darker accents
- **Primary Orange**: `#ff8c00` - Used for mid frequencies, primary UI elements
- **Light Amber**: `#ffb347` - Used for high frequencies, highlights
- **Background**: Dark backgrounds to enhance orange contrast

## Layout Structure

The app uses a view-switching architecture with two main views:

### Main View (default)
```
┌─────────────────────────────────────────────────┐
│ Header (ASCII art logo + volume)                │
├──────────────────┬──────────────────────────────┤
│ Library          │ Now Playing                  │
│ (left side)      │ (right side)                 │
│                  │                              │
├──────────────────┴──────────────────────────────┤
│ Meters (full width)                             │
├─────────────────────────────────────────────────┤
│ Footer (keybindings)                            │
└─────────────────────────────────────────────────┘
```

### Floppy Mix View (press `f`)
```
┌─────────────────────────────────────────────────┐
│ Header (ASCII art logo + volume)                │
├─────────────────────────────────────────────────┤
│ 💾 Floppy Mix              [🎵 Start Mix]       │
├──────────────────┬──────────────────────────────┤
│ Track Selection  │ Mixing Instructions          │
│ (Space to select)│ (Natural language)           │
│                  │                              │
├──────────────────┴──────────────────────────────┤
│ Progress / Preview Controls                     │
├─────────────────────────────────────────────────┤
│ Footer (keybindings)                            │
└─────────────────────────────────────────────────┘
```

## Navigation & Keybindings

### Global Keybindings (work everywhere)
- `q` - Quit application
- `space` - Play/Pause (in Floppy Mix: toggle selection when idle, play/pause preview when previewing)
- `s` - Stop playback
- `n` - Next track
- `p` - Previous track
- `+`/`=` - Volume up
- `-` - Volume down
- `m` - Toggle mute
- `f` - Open Floppy Mix view
- `d` - Return to default/main view (from Floppy Mix)
- `h` or `?` - Show help screen

### Library View Keybindings (vim-style)
- `j` - Move down in track list
- `k` - Move up in track list
- `Enter` - Play selected track

## User Experience Principles

### Error Handling
- Always display user-friendly error messages via notifications
- Never expose raw exceptions to users
- Log all errors to `~/.local/share/sigplay/sigplay.log`
- Use severity levels: `information`, `warning`, `error`
- Include actionable guidance in error messages

### Visual Feedback
- Show `♪` indicator next to currently playing track
- Show `▶` arrows around selected track in library
- Update progress bar in real-time (1 second intervals)
- Display playback state: Playing, Paused, Stopped

### Performance
- Target 30 FPS for visualizer
- Reduce frame rate if CPU usage exceeds 20%
- Scan music library in background thread
- Check for track end every 0.5 seconds

## Music Library

- Default location: `~/Music`
- Supported formats: MP3, WAV, OGG, FLAC (via miniaudio)
- Scans recursively through subdirectories
- Displays: Title, Artist, Album, Duration
- Auto-advances to next track when current track ends

## Meters Behavior

- **Active state**: Shows live audio byte stream as scrolling hexadecimal display when music is playing
- **Idle state**: Shows "NO AUDIO DATA" message when stopped
- **Visualization**: Real-time hex dump of audio buffer data
- **Color mapping**: Bytes colored by intensity (darker orange for low values, brighter for high values)
- **Adaptive**: Adjusts bytes per line based on terminal width (minimum 40 chars)
- **Responsive**: Recalculates layout on terminal resize
- **Scrolling**: Auto-scrolls through audio data at 2x speed for visual effect

## Floppy Mix Feature

AI-powered DJ mixing using natural language instructions.

### Workflow
1. Press `f` to open Floppy Mix view (prompts for API key if not configured)
2. Select tracks using `Space` key (vim-style `j`/`k` navigation)
3. Tab to instructions panel and enter natural language mixing instructions
4. Click "Start Mix" button or press Enter
5. AI agent analyzes instructions and generates mix using Pedalboard
6. Mix automatically plays as preview (Space to pause/resume)
7. Click "Save Mix" to save to Music Library with custom filename
8. Click "Discard Mix" to delete and start over
9. Press `d` to return to main view

### Natural Language Instructions
Users can request mixing operations in plain English:
- "Mix these tracks with smooth 4-second crossfades"
- "Boost the bass and add some reverb"
- "Create a high-energy mix with compression"
- "Blend tracks smoothly with subtle effects"
- "Add warmth with bass boost and gentle compression"

The AI agent interprets instructions and applies appropriate:
- BPM detection and tempo synchronization (±15% max stretch)
- Crossfades (2-6 seconds typical)
- EQ adjustments (bass/treble boost/cut)
- Effects (reverb, compression, chorus, delay)
- Filters (highpass to remove rumble, lowpass for warmth)
- Gain adjustments for volume matching

### Technical Implementation
- **AI Agent**: Strands Agents with OpenRouter (user-selectable models)
- **Audio Processing**: Pedalboard library for effects and mixing
- **Agent Tools**: Python code execution, file I/O
- **Progress Streaming**: Real-time status updates via stderr
- **Timeout**: 5-minute maximum for mix generation
- **Output**: WAV file in `~/.local/share/sigplay/temp_mixes/`

### Configuration
Users can configure OpenRouter in two ways:
1. **Environment variable** (persistent): Set `OPENROUTER_API_KEY` and optionally `SIGPLAY_MIX_MODEL_ID` in shell profile
2. **Runtime prompt** (session-only): Enter API key and model ID when prompted on first use

Environment variables:
- `OPENROUTER_API_KEY` (required): API key from https://openrouter.ai/keys
- `SIGPLAY_MIX_MODEL_ID` (optional): Model to use (default: `anthropic/claude-haiku-4.5`)

### Configuration Prompt
If no API key is configured, the app displays a modal prompt with two inputs:
- **API Key**: User can paste API key for current session only
- **Model ID**: User can specify which OpenRouter model to use (defaults to `anthropic/claude-haiku-4.5`)
- Includes instructions for generating keys at https://openrouter.ai/keys
- Can cancel to exit Floppy Mix feature
- Session credentials are not persisted to disk
- Supports Tab/Enter navigation between fields

### Error Handling
- Validates track selection (at least 1 track required)
- Validates instructions (must replace placeholder text)
- Checks for OpenRouter API key configuration
- Provides actionable error messages for API/credential issues
- Handles agent timeouts gracefully
- Cleans up temporary files on discard or error

### File Management
- **Temporary mixes**: Stored in `~/.local/share/sigplay/temp_mixes/`
- **Saved mixes**: Copied to `~/Music` with user-provided filename
- **Filename validation**: Alphanumeric, spaces, hyphens, underscores only (regex: `^[a-zA-Z0-9_\-\s]+$`)
- **Filename sanitization**: Spaces converted to underscores, `.wav` extension auto-added
- **Auto-cleanup**: Temporary files deleted on discard or view exit
