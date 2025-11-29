# SIGPLAY

A terminal music player with a retro-modern vibe. Built with Python and Textual.

![Python 3.13+](https://img.shields.io/badge/python-3.13+-orange)
![License MIT](https://img.shields.io/badge/license-MIT-orange)

## What it does

- Plays music from your `~/Music` folder (MP3, WAV, OGG, FLAC)
- Keyboard-driven interface with vim-style navigation
- Real-time audio visualization
- **Floppy Mix**: AI-powered DJ mixing using natural language instructions

## What it looks like

<p align="center">
  <img alt="main-view" src="https://github.com/user-attachments/assets/ba4901ea-8a97-4f57-a808-5232c6063018" width="800" />
</p>


## Run

First, install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then run:

```bash
uvx sigplay
```

That's all! No other things needed.

## Controls

| Key | Action |
|-----|--------|
| `j/k` | Navigate track list |
| `Enter` | Play selected track |
| `Space` | Play/Pause |
| `s` | Stop |
| `n/p` | Next/Previous track |
| `+/-` | Volume up/down |
| `m` | Mute |
| `r` | Shuffle |
| `f` | Floppy Mix (AI DJ) |
| `d` | Back to main view |
| `h` or `?` | Help |
| `q` | Quit |

## Floppy Mix

Press `f` to open the AI DJ mixer. Select tracks, write instructions in plain English, and let the AI create a mix.

Example instructions:
- "Mix these with smooth 4-second crossfades"
- "Boost the bass and add reverb"
- "Create a high-energy mix with compression"

Requires an [OpenRouter](https://openrouter.ai/keys) API key. You can set it as an environment variable or enter it when prompted:

```bash
export OPENROUTER_API_KEY="your-key-here"
export SIGPLAY_MIX_MODEL_ID="anthropic/claude-haiku-4.5"  # optional
```

## Requirements

- `uv` installed
- Audio files in `~/Music`

## License

MIT
