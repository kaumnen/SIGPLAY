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

The app uses a fixed 3-component layout:

```
┌─────────────────────────────────────────────────┐
│ Header (ASCII art logo)                         │
├──────────────────┬──────────────────────────────┤
│ Library          │ Now Playing                  │
│ (left side)      │ (right side)                 │
│                  │                              │
├──────────────────┴──────────────────────────────┤
│ Visualizer (full width)                         │
├─────────────────────────────────────────────────┤
│ Footer (keybindings)                            │
└─────────────────────────────────────────────────┘
```

## Navigation & Keybindings

### Global Keybindings (work everywhere)
- `q` - Quit application
- `space` - Play/Pause
- `s` - Stop playback
- `n` - Next track
- `p` - Previous track
- `+`/`=` - Volume up
- `-` - Volume down
- `o` - Select audio device (future feature)

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

## Visualizer Behavior

- **Active state**: Shows frequency bars when music is playing
- **Idle state**: Shows baseline only when stopped
- **Frequency ranges**: Bass (left), Mid (center), High (right)
- **Color mapping**: Bars colored by frequency range using palette
- **Adaptive**: Adjusts bar count based on terminal width (20-120 bars)
- **Responsive**: Recalculates layout on terminal resize
