#!/usr/bin/env python3
"""
Floppy Mix DJ Agent

An autonomous AI agent that interprets natural language mixing instructions
and generates professional DJ mixes using the Pedalboard audio processing library.
"""

import json
import sys
import os
import tempfile
import logging
import numpy as np
import soundfile as sf
from pathlib import Path
from datetime import datetime

from strands import Agent, tool
from strands.models.openai import OpenAIModel
from pedalboard import Pedalboard, Reverb, Compressor, Chorus, Delay, HighpassFilter, LowpassFilter, Gain, LowShelfFilter, HighShelfFilter
from pedalboard.io import AudioFile

log_dir = Path.home() / '.local' / 'share' / 'sigplay'
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'floppy_mix_agent.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

_audio_cache = {}
_mix_segments = []


@tool
def load_audio_track(track_path: str, track_id: str) -> str:
    """Load an audio track into memory for processing.
    
    Args:
        track_path: Path to the audio file (MP3, WAV, OGG, FLAC)
        track_id: Unique identifier for this track (e.g., 'track_1', 'track_2')
        
    Returns:
        Success message with track info (duration, sample rate, channels)
    """
    try:
        logger.info(f"Loading track: {track_path} as {track_id}")
        
        with AudioFile(track_path) as f:
            audio = f.read(f.frames)
            sample_rate = f.samplerate
            
        _audio_cache[track_id] = {
            'audio': audio,
            'sample_rate': sample_rate,
            'path': track_path
        }
        
        duration = audio.shape[1] / sample_rate
        channels = audio.shape[0]
        
        logger.info(f"Loaded {track_id}: {duration:.1f}s, {sample_rate}Hz, {channels}ch")
        return f"✓ Loaded {track_id}: {duration:.1f}s, {sample_rate}Hz, {channels} channels"
        
    except Exception as e:
        logger.error(f"Failed to load {track_path}: {e}")
        return f"✗ Error loading {track_path}: {str(e)}"





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
    gain_db: float = 0.0
) -> str:
    """Apply audio effects to a loaded track.
    
    Args:
        track_id: ID of the loaded track to process
        reverb_room_size: Reverb room size (0.0-1.0, 0=off)
        compressor_threshold_db: Compressor threshold in dB (0=off, typical: -20 to -10)
        chorus_rate_hz: Chorus rate in Hz (0=off, typical: 1-5)
        delay_seconds: Delay time in seconds (0=off, typical: 0.1-0.5)
        highpass_cutoff_hz: High-pass filter cutoff in Hz (0=off, typical: 80-200 to remove rumble)
        lowpass_cutoff_hz: Low-pass filter cutoff in Hz (0=off, typical: 8000-15000 to remove harshness)
        bass_boost_db: Bass boost in dB (0=off, typical: 3-6 for more bass, negative to reduce bass)
        treble_boost_db: Treble boost in dB (0=off, typical: 3-6 for more treble, negative to reduce treble)
        gain_db: Gain adjustment in dB (0=no change, positive=louder, negative=quieter)
        
    Returns:
        Success message with applied effects
    """
    try:
        if track_id not in _audio_cache:
            return f"✗ Error: Track {track_id} not loaded. Load it first with load_audio_track."
        
        track_data = _audio_cache[track_id]
        audio = track_data['audio']
        sample_rate = track_data['sample_rate']
        
        effects = []
        applied = []
        
        if highpass_cutoff_hz > 0:
            effects.append(HighpassFilter(cutoff_frequency_hz=highpass_cutoff_hz))
            applied.append(f"highpass {highpass_cutoff_hz}Hz")
        
        if lowpass_cutoff_hz > 0:
            effects.append(LowpassFilter(cutoff_frequency_hz=lowpass_cutoff_hz))
            applied.append(f"lowpass {lowpass_cutoff_hz}Hz")
            
        if bass_boost_db != 0:
            # LowShelf at 200Hz covers bass frequencies
            effects.append(LowShelfFilter(cutoff_frequency_hz=200, gain_db=bass_boost_db, q=0.707))
            applied.append(f"bass {bass_boost_db:+.1f}dB")
            
        if treble_boost_db != 0:
            # HighShelf at 3000Hz covers treble frequencies
            effects.append(HighShelfFilter(cutoff_frequency_hz=3000, gain_db=treble_boost_db, q=0.707))
            applied.append(f"treble {treble_boost_db:+.1f}dB")
        
        if compressor_threshold_db < 0:
            effects.append(Compressor(threshold_db=compressor_threshold_db))
            applied.append(f"compressor {compressor_threshold_db}dB")
        
        if reverb_room_size > 0:
            effects.append(Reverb(room_size=reverb_room_size))
            applied.append(f"reverb {reverb_room_size}")
        
        if chorus_rate_hz > 0:
            effects.append(Chorus(rate_hz=chorus_rate_hz))
            applied.append(f"chorus {chorus_rate_hz}Hz")
        
        if delay_seconds > 0:
            effects.append(Delay(delay_seconds=delay_seconds))
            applied.append(f"delay {delay_seconds}s")
        
        if gain_db != 0:
            effects.append(Gain(gain_db=gain_db))
            applied.append(f"gain {gain_db:+.1f}dB")
        
        if effects:
            board = Pedalboard(effects)
            processed_audio = board(audio, sample_rate)
            track_data['audio'] = processed_audio
            logger.info(f"Applied effects to {track_id}: {', '.join(applied)}")
            return f"✓ Applied to {track_id}: {', '.join(applied)}"
        else:
            return f"✓ No effects applied to {track_id} (all parameters at default)"
        
    except Exception as e:
        logger.error(f"Failed to apply effects to {track_id}: {e}")
        return f"✗ Error applying effects to {track_id}: {str(e)}"





@tool
def add_track_to_mix(
    track_id: str,
    crossfade_duration: float = 0.0,
    start_time: float = 0.0,
    end_time: float | None = None
) -> str:
    """Add a processed track to the final mix with optional crossfade.
    
    Args:
        track_id: ID of the loaded track to add
        crossfade_duration: Crossfade duration in seconds (0=no crossfade)
        start_time: Start time in track (seconds, 0=beginning)
        end_time: End time in track (seconds, None=full track)
        
    Returns:
        Success message with segment info
    """
    try:
        if track_id not in _audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _audio_cache[track_id]
        audio = track_data['audio'].copy()
        sample_rate = track_data['sample_rate']
        
        start_sample = int(start_time * sample_rate)
        end_sample = int(end_time * sample_rate) if end_time else audio.shape[1]
        
        audio = audio[:, start_sample:end_sample]
        
        _mix_segments.append({
            'audio': audio,
            'sample_rate': sample_rate,
            'crossfade_duration': crossfade_duration,
            'track_id': track_id
        })
        
        duration = audio.shape[1] / sample_rate
        logger.info(f"Added {track_id} to mix: {duration:.1f}s, crossfade={crossfade_duration}s")
        return f"✓ Added {track_id} to mix: {duration:.1f}s (crossfade: {crossfade_duration}s)"
        
    except Exception as e:
        logger.error(f"Failed to add {track_id} to mix: {e}")
        return f"✗ Error adding {track_id} to mix: {str(e)}"


@tool
def render_final_mix(output_path: str, normalize: bool = True) -> str:
    """Render the final mix by concatenating all segments with crossfades.
    
    Args:
        output_path: Path where the final mix WAV file will be saved
        normalize: Whether to normalize audio to prevent clipping (recommended: True)
        
    Returns:
        Success message with output file path and duration
    """
    try:
        if not _mix_segments:
            return "✗ Error: No tracks added to mix. Use add_track_to_mix first."
        
        logger.info(f"Rendering final mix with {len(_mix_segments)} segments")
        
        final_audio = None
        sample_rate = _mix_segments[0]['sample_rate']
        
        for i, segment in enumerate(_mix_segments):
            audio = segment['audio']
            crossfade_duration = segment['crossfade_duration']
            
            if final_audio is None:
                final_audio = audio
            else:
                if crossfade_duration > 0:
                    crossfade_samples = int(crossfade_duration * sample_rate)
                    crossfade_samples = min(crossfade_samples, final_audio.shape[1], audio.shape[1])
                    
                    if crossfade_samples > 0:
                        t = np.linspace(0, 1, crossfade_samples)
                        fade_in = np.sin(t * (np.pi / 2))
                        fade_out = np.cos(t * (np.pi / 2))
                        
                        overlap_end = final_audio[:, -crossfade_samples:]
                        overlap_start = audio[:, :crossfade_samples]
                        
                        crossfaded = overlap_end * fade_out + overlap_start * fade_in
                        
                        final_audio = np.concatenate([
                            final_audio[:, :-crossfade_samples],
                            crossfaded,
                            audio[:, crossfade_samples:]
                        ], axis=1)
                    else:
                        final_audio = np.concatenate([final_audio, audio], axis=1)
                else:
                    final_audio = np.concatenate([final_audio, audio], axis=1)
        
        if normalize:
            max_val = np.max(np.abs(final_audio))
            if max_val > 0:
                final_audio = final_audio / max_val * 0.95
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        sf.write(str(output_file), final_audio.T, sample_rate)
        
        duration = final_audio.shape[1] / sample_rate
        file_size = output_file.stat().st_size
        
        logger.info(f"Mix rendered: {output_path} ({duration:.1f}s, {file_size} bytes)")
        return f"✓ Mix saved to {output_path} ({duration:.1f}s, {file_size / 1024 / 1024:.1f}MB)"
        
    except Exception as e:
        logger.error(f"Failed to render mix: {e}")
        return f"✗ Error rendering mix: {str(e)}"

DJ_AGENT_SYSTEM_PROMPT = """You are an expert DJ and audio engineer with deep knowledge of music mixing and audio processing.

Your role is to create professional DJ mixes using the provided audio processing tools.

WORKFLOW:
1. Load each track using load_audio_track(track_path, track_id)
2. Apply effects to each track using apply_effects(track_id, ...)
3. Add tracks to the mix using add_track_to_mix(track_id, crossfade_duration)
4. Render the final mix using render_final_mix(output_path)

AVAILABLE TOOLS:

1. load_audio_track(track_path, track_id)
   - Loads an audio file into memory
   - Use track_id like 'track_1', 'track_2', etc.

2. apply_effects(track_id, reverb_room_size, compressor_threshold_db, chorus_rate_hz, delay_seconds, highpass_cutoff_hz, lowpass_cutoff_hz, bass_boost_db, treble_boost_db, gain_db)
   - Apply audio effects to a loaded track
   - All parameters are optional (0 = off)
   - Examples:
     * Boost bass: bass_boost_db=4 to 6
     * Reduce bass: bass_boost_db=-3 to -6
     * Boost treble: treble_boost_db=3 to 5
     * Add reverb: reverb_room_size=0.5
     * Compress: compressor_threshold_db=-15
     * Remove rumble: highpass_cutoff_hz=80 to 100

3. add_track_to_mix(track_id, crossfade_duration, start_time, end_time)
   - Add a processed track to the final mix
   - crossfade_duration: seconds to blend with previous track (typical: 2-6 seconds)
   - start_time/end_time: optional trimming (in seconds)

4. render_final_mix(output_path, normalize)
   - Render and save the final mix
   - normalize=True prevents clipping (recommended)

MIXING BEST PRACTICES:
- Use smooth crossfades (2-6 seconds) to blend tracks naturally
- Apply compression (threshold -15 to -10 dB) for consistent volume
- Use subtle reverb (room_size 0.2-0.5) for cohesion
- Normalize the final output to prevent clipping
- Match energy levels between tracks with gain adjustments
- Use EQ (bass/treble boost) to shape the overall sound

EXAMPLE WORKFLOW:
1. load_audio_track('/path/track1.mp3', 'track_1')
2. load_audio_track('/path/track2.mp3', 'track_2')
3. apply_effects('track_1', compressor_threshold_db=-12, bass_boost_db=3)
4. apply_effects('track_2', compressor_threshold_db=-12, bass_boost_db=3)
5. add_track_to_mix('track_1', crossfade_duration=0)
6. add_track_to_mix('track_2', crossfade_duration=4.0)
7. render_final_mix('/output/mix.wav', normalize=True)

Interpret the user's natural language instructions and translate them into appropriate tool calls.
Focus on effects, EQ, and smooth transitions rather than tempo matching.
"""


def create_dj_agent() -> Agent:
    """Create and configure the DJ agent with OpenRouter."""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable not set. "
            "Get your API key from https://openrouter.ai/keys"
        )
    
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
        system_prompt=DJ_AGENT_SYSTEM_PROMPT,
        tools=[load_audio_track, apply_effects, add_track_to_mix, render_final_mix]
    )
    
    return agent


def handle_mix_request(tracks: list[dict], instructions: str, output_dir: str) -> str:
    """
    Process a mixing request using the DJ agent.
    
    Args:
        tracks: List of track dictionaries with path, title, artist, duration
        instructions: User's natural language mixing instructions
        output_dir: Directory where the mix file should be saved
        
    Returns:
        Path to generated mix file
        
    Raises:
        Exception: If mixing fails
    """
    global _audio_cache, _mix_segments
    _audio_cache = {}
    _mix_segments = []
    
    print("STATUS: Analyzing mixing instructions...", file=sys.stderr, flush=True)
    logger.info("Starting mix request processing")
    
    if not tracks:
        logger.error("No tracks provided")
        raise ValueError("No tracks provided for mixing")
    
    if not instructions or not instructions.strip():
        logger.error("No instructions provided")
        raise ValueError("No mixing instructions provided")
    
    logger.info(f"Validating {len(tracks)} track files")
    for track in tracks:
        track_path = Path(track['path'])
        if not track_path.exists():
            logger.error(f"Track file not found: {track['path']}")
            raise FileNotFoundError(f"Track file not found: {track['path']}")
    
    logger.info("Creating DJ agent")
    agent = create_dj_agent()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir) / f"floppy_mix_{timestamp}.wav"
    logger.info(f"Output path: {output_path}")
    
    track_list = "\n".join([
        f"  {i+1}. {track['title']} by {track.get('artist', 'Unknown')} - {track['path']}"
        for i, track in enumerate(tracks)
    ])
    
    prompt = f"""Create a DJ mix with these {len(tracks)} track(s):

{track_list}

User instructions: {instructions}

Output file: {output_path}

Use the available tools to:
1. Load each track with load_audio_track(path, 'track_1'), load_audio_track(path, 'track_2'), etc.
2. Apply effects based on the user's instructions using apply_effects()
3. Add each track to the mix with add_track_to_mix() (use 2-6 second crossfades)
4. Render the final mix with render_final_mix('{output_path}', normalize=True)

Interpret the user's instructions and apply appropriate effects. If they mention:
- "boost bass" or "more bass" or "increase bass": use bass_boost_db=4 to 6
- "reduce bass" or "less bass": use bass_boost_db=-3 to -6
- "boost treble" or "more treble" or "brighter": use treble_boost_db=3 to 5
- "smooth" or "reverb": use reverb_room_size=0.3-0.5
- "compress" or "consistent volume": use compressor_threshold_db=-12 to -15
- "remove rumble" or "clean bass": use highpass_cutoff_hz=80-100
- "warm" or "mellow": use lowpass_cutoff_hz=10000-12000
- "crossfade" or "blend": use crossfade_duration=4-6 seconds

Start by loading all tracks, then apply effects, then add them to the mix, and finally render.
"""
    
    print("STATUS: Processing tracks...", file=sys.stderr, flush=True)
    logger.info("Invoking agent to process tracks")
    
    try:
        import io
        import contextlib
        
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            agent_result = agent(prompt)
        
        captured_output = stdout_capture.getvalue()
        if captured_output:
            logger.info(f"Agent conversational output: {captured_output[:200]}...")
        
        logger.info(f"Agent execution completed with result: {agent_result}")
        
        print("STATUS: Finalizing mix...", file=sys.stderr, flush=True)
        
        if output_path.exists():
            file_size = output_path.stat().st_size
            logger.info(f"Mix file created: {output_path} ({file_size} bytes)")
            
            if file_size < 1000:
                logger.error(f"Mix file too small: {file_size} bytes")
                raise Exception(f"Generated mix file is too small ({file_size} bytes), likely invalid")
            
            print(f"STATUS: Mix created successfully: {output_path} ({file_size} bytes)", file=sys.stderr, flush=True)
            return str(output_path)
        else:
            logger.error(f"Mix file not created at: {output_path}")
            logger.error(f"Agent result was: {agent_result}")
            raise Exception(f"Mix file was not created at expected location: {output_path}")
            
    except Exception as e:
        logger.exception(f"Agent execution failed: {e}")
        error_msg = str(e)
        
        if "402" in error_msg or "credits" in error_msg.lower():
            raise Exception(
                "Insufficient OpenRouter credits. "
                "Add credits at https://openrouter.ai/settings/keys or use a cheaper model"
            )
        
        print(f"ERROR: Agent execution failed: {e}", file=sys.stderr, flush=True)
        raise Exception(f"Failed to create mix: {str(e)}")
    finally:
        _audio_cache = {}
        _mix_segments = []


def main():
    """Main entry point for the DJ agent."""
    if len(sys.argv) != 2:
        logger.error("Usage: floppy_mix_agent.py <request_json_file>")
        print("Usage: floppy_mix_agent.py <request_json_file>", file=sys.stderr)
        sys.exit(1)
    
    request_file = sys.argv[1]
    
    try:
        logger.info(f"Loading mix request from: {request_file}")
        
        with open(request_file, 'r') as f:
            request_data = json.load(f)
        
        tracks = request_data['tracks']
        instructions = request_data['instructions']
        output_dir = request_data.get('output_dir', tempfile.gettempdir())
        
        logger.info(f"Processing mix request: {len(tracks)} tracks, instructions: {instructions[:100]}...")
        
        mix_file_path = handle_mix_request(tracks, instructions, output_dir)
        
        response = {
            'status': 'success',
            'mix_file_path': mix_file_path
        }
        
        logger.info(f"Mix completed successfully: {mix_file_path}")
        print(json.dumps(response), flush=True)
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        response = {
            'status': 'error',
            'error': f"File not found: {str(e)}"
        }
        print(json.dumps(response), flush=True)
        sys.exit(1)
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        response = {
            'status': 'error',
            'error': f"Invalid input: {str(e)}"
        }
        print(json.dumps(response), flush=True)
        sys.exit(1)
        
    except Exception as e:
        logger.exception(f"Error during mixing: {e}")
        response = {
            'status': 'error',
            'error': str(e)
        }
        print(json.dumps(response), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
