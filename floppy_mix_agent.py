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
from pedalboard import (
    Pedalboard, Reverb, Compressor, Chorus, Delay, 
    HighpassFilter, LowpassFilter, Gain, LowShelfFilter, HighShelfFilter,
    LadderFilter, Phaser, Distortion, Clipping, Bitcrush, NoiseGate,
    PitchShift, Mix
)
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
        track_name = Path(track_path).stem
        print(f"STATUS: 📂 Loading {track_name}...", file=sys.stderr, flush=True)
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
        print(f"STATUS: ✓ Loaded {track_name} ({duration:.1f}s)", file=sys.stderr, flush=True)
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
    gain_db: float = 0.0,
    phaser_rate_hz: float = 0.0,
    distortion_drive_db: float = 0.0,
    noise_gate_threshold_db: float = 0.0,
    pitch_shift_semitones: float = 0.0
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
        phaser_rate_hz: Phaser rate in Hz (0=off, typical: 0.5-2 for movement)
        distortion_drive_db: Distortion drive in dB (0=off, typical: 10-20 for warmth)
        noise_gate_threshold_db: Noise gate threshold in dB (0=off, typical: -40 to -50 to remove noise)
        pitch_shift_semitones: Pitch shift in semitones (0=off, +/-12 for octave, +/-7 for fifth)
        
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
        
        if noise_gate_threshold_db < 0:
            effects.append(NoiseGate(threshold_db=noise_gate_threshold_db, ratio=10))
            applied.append(f"noise_gate {noise_gate_threshold_db}dB")
        
        if highpass_cutoff_hz > 0:
            effects.append(HighpassFilter(cutoff_frequency_hz=highpass_cutoff_hz))
            applied.append(f"highpass {highpass_cutoff_hz}Hz")
        
        if lowpass_cutoff_hz > 0:
            effects.append(LowpassFilter(cutoff_frequency_hz=lowpass_cutoff_hz))
            applied.append(f"lowpass {lowpass_cutoff_hz}Hz")
            
        if bass_boost_db != 0:
            effects.append(LowShelfFilter(cutoff_frequency_hz=200, gain_db=bass_boost_db, q=0.707))
            applied.append(f"bass {bass_boost_db:+.1f}dB")
            
        if treble_boost_db != 0:
            effects.append(HighShelfFilter(cutoff_frequency_hz=3000, gain_db=treble_boost_db, q=0.707))
            applied.append(f"treble {treble_boost_db:+.1f}dB")
        
        if distortion_drive_db > 0:
            effects.append(Distortion(drive_db=distortion_drive_db))
            applied.append(f"distortion {distortion_drive_db}dB")
        
        if compressor_threshold_db < 0:
            effects.append(Compressor(threshold_db=compressor_threshold_db))
            applied.append(f"compressor {compressor_threshold_db}dB")
        
        if pitch_shift_semitones != 0:
            effects.append(PitchShift(semitones=pitch_shift_semitones))
            applied.append(f"pitch {pitch_shift_semitones:+.1f}st")
        
        if chorus_rate_hz > 0:
            effects.append(Chorus(rate_hz=chorus_rate_hz))
            applied.append(f"chorus {chorus_rate_hz}Hz")
        
        if phaser_rate_hz > 0:
            effects.append(Phaser(rate_hz=phaser_rate_hz))
            applied.append(f"phaser {phaser_rate_hz}Hz")
        
        if delay_seconds > 0:
            effects.append(Delay(delay_seconds=delay_seconds))
            applied.append(f"delay {delay_seconds}s")
        
        if reverb_room_size > 0:
            effects.append(Reverb(room_size=reverb_room_size))
            applied.append(f"reverb {reverb_room_size}")
        
        if gain_db != 0:
            effects.append(Gain(gain_db=gain_db))
            applied.append(f"gain {gain_db:+.1f}dB")
        
        if effects:
            print(f"STATUS: 🎛️ Applying effects to {track_id}: {', '.join(applied)}", file=sys.stderr, flush=True)
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
def apply_ladder_filter(
    track_id: str,
    mode: str = "LPF24",
    cutoff_hz: float = 1000.0,
    resonance: float = 0.0
) -> str:
    """Apply a Moog-style ladder filter with resonance for classic synth sounds.
    
    Args:
        track_id: ID of the loaded track to process
        mode: Filter mode - "LPF12", "LPF24", "HPF12", "HPF24", "BPF12", "BPF24"
        cutoff_hz: Cutoff frequency in Hz (20-20000, typical: 200-5000)
        resonance: Resonance amount (0.0-1.0, typical: 0.3-0.8 for character)
        
    Returns:
        Success message with filter info
    """
    try:
        if track_id not in _audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _audio_cache[track_id]
        audio = track_data['audio']
        sample_rate = track_data['sample_rate']
        
        mode_map = {
            "LPF12": LadderFilter.Mode.LPF12,
            "LPF24": LadderFilter.Mode.LPF24,
            "HPF12": LadderFilter.Mode.HPF12,
            "HPF24": LadderFilter.Mode.HPF24,
            "BPF12": LadderFilter.Mode.BPF12,
            "BPF24": LadderFilter.Mode.BPF24
        }
        
        filter_mode = mode_map.get(mode, LadderFilter.Mode.LPF24)
        ladder = LadderFilter(mode=filter_mode, cutoff_hz=cutoff_hz, resonance=resonance)
        
        processed_audio = ladder(audio, sample_rate)
        track_data['audio'] = processed_audio
        
        logger.info(f"Applied ladder filter to {track_id}: {mode} @ {cutoff_hz}Hz, res={resonance}")
        return f"✓ Applied ladder filter to {track_id}: {mode} @ {cutoff_hz}Hz, resonance={resonance}"
        
    except Exception as e:
        logger.error(f"Failed to apply ladder filter to {track_id}: {e}")
        return f"✗ Error applying ladder filter to {track_id}: {str(e)}"


@tool
def apply_parallel_effects(
    track_id: str,
    dry_gain_db: float = 0.0,
    wet_reverb_room_size: float = 0.0,
    wet_delay_seconds: float = 0.0,
    wet_gain_db: float = -6.0
) -> str:
    """Apply parallel effects processing (dry/wet mix) for more control.
    
    Args:
        track_id: ID of the loaded track to process
        dry_gain_db: Gain for dry (unprocessed) signal in dB
        wet_reverb_room_size: Reverb room size for wet signal (0.0-1.0)
        wet_delay_seconds: Delay time for wet signal in seconds
        wet_gain_db: Gain for wet (processed) signal in dB (typically -3 to -6)
        
    Returns:
        Success message with parallel processing info
    """
    try:
        if track_id not in _audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _audio_cache[track_id]
        audio = track_data['audio']
        sample_rate = track_data['sample_rate']
        
        dry_chain = Pedalboard([Gain(gain_db=dry_gain_db)])
        
        wet_effects = []
        if wet_reverb_room_size > 0:
            wet_effects.append(Reverb(room_size=wet_reverb_room_size, wet_level=1.0))
        if wet_delay_seconds > 0:
            wet_effects.append(Delay(delay_seconds=wet_delay_seconds, mix=1.0))
        wet_effects.append(Gain(gain_db=wet_gain_db))
        
        wet_chain = Pedalboard(wet_effects)
        
        board = Pedalboard([
            Mix([dry_chain, wet_chain])
        ])
        
        processed_audio = board(audio, sample_rate)
        track_data['audio'] = processed_audio
        
        logger.info(f"Applied parallel effects to {track_id}: dry={dry_gain_db}dB, wet={wet_gain_db}dB")
        return f"✓ Applied parallel effects to {track_id}: dry={dry_gain_db}dB, wet reverb={wet_reverb_room_size}, delay={wet_delay_seconds}s"
        
    except Exception as e:
        logger.error(f"Failed to apply parallel effects to {track_id}: {e}")
        return f"✗ Error applying parallel effects to {track_id}: {str(e)}"


@tool
def apply_creative_effects(
    track_id: str,
    bitcrush_bit_depth: int = 0,
    clipping_threshold_db: float = 0.0
) -> str:
    """Apply creative lo-fi and distortion effects.
    
    Args:
        track_id: ID of the loaded track to process
        bitcrush_bit_depth: Bit depth for lo-fi effect (0=off, 4-12 for lo-fi sound)
        clipping_threshold_db: Hard clipping threshold in dB (0=off, -6 to -3 for aggressive sound)
        
    Returns:
        Success message with creative effects info
    """
    try:
        if track_id not in _audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _audio_cache[track_id]
        audio = track_data['audio']
        sample_rate = track_data['sample_rate']
        
        effects = []
        applied = []
        
        if bitcrush_bit_depth > 0:
            effects.append(Bitcrush(bit_depth=bitcrush_bit_depth))
            applied.append(f"bitcrush {bitcrush_bit_depth}bit")
        
        if clipping_threshold_db < 0:
            effects.append(Clipping(threshold_db=clipping_threshold_db))
            applied.append(f"clipping {clipping_threshold_db}dB")
        
        if effects:
            board = Pedalboard(effects)
            processed_audio = board(audio, sample_rate)
            track_data['audio'] = processed_audio
            logger.info(f"Applied creative effects to {track_id}: {', '.join(applied)}")
            return f"✓ Applied creative effects to {track_id}: {', '.join(applied)}"
        else:
            return f"✓ No creative effects applied to {track_id}"
        
    except Exception as e:
        logger.error(f"Failed to apply creative effects to {track_id}: {e}")
        return f"✗ Error applying creative effects to {track_id}: {str(e)}"


@tool
def automate_filter_sweep(
    track_id: str,
    start_cutoff_hz: float = 200.0,
    end_cutoff_hz: float = 5000.0,
    filter_mode: str = "LPF24",
    resonance: float = 0.5
) -> str:
    """Automate a filter sweep across the entire track for dynamic movement.
    
    Args:
        track_id: ID of the loaded track to process
        start_cutoff_hz: Starting cutoff frequency in Hz
        end_cutoff_hz: Ending cutoff frequency in Hz
        filter_mode: Filter mode - "LPF24", "HPF24", "BPF24"
        resonance: Resonance amount (0.0-1.0)
        
    Returns:
        Success message with automation info
    """
    try:
        if track_id not in _audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _audio_cache[track_id]
        audio = track_data['audio']
        sample_rate = track_data['sample_rate']
        
        mode_map = {
            "LPF24": LadderFilter.Mode.LPF24,
            "HPF24": LadderFilter.Mode.HPF24,
            "BPF24": LadderFilter.Mode.BPF24
        }
        
        filter_obj = LadderFilter(
            mode=mode_map.get(filter_mode, LadderFilter.Mode.LPF24),
            cutoff_hz=start_cutoff_hz,
            resonance=resonance
        )
        
        chunk_size = 4096
        output = np.zeros_like(audio)
        num_chunks = int(np.ceil(audio.shape[1] / chunk_size))
        
        for i in range(num_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, audio.shape[1])
            chunk = audio[:, start:end]
            
            progress = i / num_chunks
            filter_obj.cutoff_hz = start_cutoff_hz + (end_cutoff_hz - start_cutoff_hz) * progress
            
            processed = filter_obj(chunk, sample_rate, reset=False)
            output[:, start:end] = processed
        
        track_data['audio'] = output
        
        logger.info(f"Applied filter sweep to {track_id}: {start_cutoff_hz}Hz -> {end_cutoff_hz}Hz")
        return f"✓ Applied filter sweep to {track_id}: {start_cutoff_hz}Hz -> {end_cutoff_hz}Hz ({filter_mode})"
        
    except Exception as e:
        logger.error(f"Failed to apply filter sweep to {track_id}: {e}")
        return f"✗ Error applying filter sweep to {track_id}: {str(e)}"


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
        print(f"STATUS: ➕ Added {track_id} to mix ({duration:.1f}s, {crossfade_duration}s crossfade)", file=sys.stderr, flush=True)
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
        print(f"STATUS: 🎚️ Rendering final mix ({len(_mix_segments)} segments)...", file=sys.stderr, flush=True)
        
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
            print("STATUS: 🔊 Normalizing audio levels...", file=sys.stderr, flush=True)
            max_val = np.max(np.abs(final_audio))
            if max_val > 0:
                final_audio = final_audio / max_val * 0.95
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        print("STATUS: 💾 Writing audio file...", file=sys.stderr, flush=True)
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
2. Apply effects to each track using the various effect tools
3. Add tracks to the mix using add_track_to_mix(track_id, crossfade_duration)
4. Render the final mix using render_final_mix(output_path)

AVAILABLE TOOLS:

1. load_audio_track(track_path, track_id)
   - Loads an audio file into memory
   - Use track_id like 'track_1', 'track_2', etc.

2. apply_effects(track_id, ...)
   - Apply standard audio effects to a loaded track
   - Parameters: reverb_room_size, compressor_threshold_db, chorus_rate_hz, delay_seconds,
     highpass_cutoff_hz, lowpass_cutoff_hz, bass_boost_db, treble_boost_db, gain_db,
     phaser_rate_hz, distortion_drive_db, noise_gate_threshold_db, pitch_shift_semitones
   - All parameters are optional (0 = off)
   - Examples:
     * Boost bass: bass_boost_db=4 to 6
     * Add warmth: distortion_drive_db=10 to 15
     * Movement: phaser_rate_hz=0.5 to 1.5
     * Clean noise: noise_gate_threshold_db=-40 to -50
     * Harmonic mixing: pitch_shift_semitones=+/-7 (fifth) or +/-12 (octave)

3. apply_ladder_filter(track_id, mode, cutoff_hz, resonance)
   - Apply Moog-style resonant filter for classic synth sounds
   - Modes: "LPF24" (low-pass), "HPF24" (high-pass), "BPF24" (band-pass)
   - Resonance: 0.3-0.8 for character, higher for dramatic effect
   - Great for creating tension and release

4. apply_parallel_effects(track_id, dry_gain_db, wet_reverb_room_size, wet_delay_seconds, wet_gain_db)
   - Process dry and wet signals separately for more control
   - Maintains clarity while adding depth
   - Typical: dry_gain_db=0, wet_gain_db=-6

5. apply_creative_effects(track_id, bitcrush_bit_depth, clipping_threshold_db)
   - Lo-fi and aggressive effects
   - Bitcrush: 4-12 bits for retro/lo-fi sound
   - Clipping: -6 to -3 dB for aggressive distortion

6. automate_filter_sweep(track_id, start_cutoff_hz, end_cutoff_hz, filter_mode, resonance)
   - Automate filter cutoff across entire track
   - Creates dynamic movement and builds tension
   - Example: 200Hz -> 5000Hz for build-up

7. add_track_to_mix(track_id, crossfade_duration, start_time, end_time)
   - Add a processed track to the final mix
   - crossfade_duration: seconds to blend with previous track (typical: 2-6 seconds)
   - start_time/end_time: optional trimming (in seconds)

8. render_final_mix(output_path, normalize)
   - Render and save the final mix
   - normalize=True prevents clipping (recommended)

MIXING BEST PRACTICES:
- Use smooth crossfades (2-6 seconds) to blend tracks naturally
- Apply compression (threshold -15 to -10 dB) for consistent volume
- Use subtle reverb (room_size 0.2-0.5) for cohesion
- Normalize the final output to prevent clipping
- Match energy levels between tracks with gain adjustments
- Use EQ (bass/treble boost) to shape the overall sound
- Add phaser/chorus for movement and depth
- Use parallel processing to maintain clarity while adding effects
- Apply filter sweeps for dramatic builds and transitions
- Use pitch shifting for harmonic mixing (key matching)
- Clean up recordings with noise gate before processing

CREATIVE TECHNIQUES:
- Filter sweeps: Build tension with automate_filter_sweep (200Hz -> 5000Hz)
- Parallel reverb: Use apply_parallel_effects for depth without muddiness
- Lo-fi vibes: Use bitcrush (8-bit) + distortion for retro sound
- Harmonic mixing: Pitch shift tracks by +/-7 semitones (fifth) for key matching
- Movement: Combine phaser + chorus for swirling effects
- Warmth: Subtle distortion (10-15dB) + bass boost for analog feel

EXAMPLE WORKFLOW:
1. load_audio_track('/path/track1.mp3', 'track_1')
2. load_audio_track('/path/track2.mp3', 'track_2')
3. apply_effects('track_1', compressor_threshold_db=-12, bass_boost_db=3, phaser_rate_hz=0.8)
4. apply_parallel_effects('track_2', wet_reverb_room_size=0.4, wet_gain_db=-6)
5. automate_filter_sweep('track_2', start_cutoff_hz=200, end_cutoff_hz=5000)
6. add_track_to_mix('track_1', crossfade_duration=0)
7. add_track_to_mix('track_2', crossfade_duration=4.0)
8. render_final_mix('/output/mix.wav', normalize=True)

Interpret the user's natural language instructions and translate them into appropriate tool calls.
Be creative and use the full range of available effects to create professional, engaging mixes.
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
        tools=[
            load_audio_track,
            apply_effects,
            apply_ladder_filter,
            apply_parallel_effects,
            apply_creative_effects,
            automate_filter_sweep,
            add_track_to_mix,
            render_final_mix
        ]
    )
    
    return agent


def handle_mix_request(tracks: list[dict], instructions: str, output_dir: str) -> dict:
    """
    Process a mixing request using the DJ agent.
    
    Args:
        tracks: List of track dictionaries with path, title, artist, duration
        instructions: User's natural language mixing instructions
        output_dir: Directory where the mix file should be saved
        
    Returns:
        Dictionary with mix_file_path and statistics
        
    Raises:
        Exception: If mixing fails
    """
    global _audio_cache, _mix_segments
    _audio_cache = {}
    _mix_segments = []
    
    import time
    start_time = time.time()
    
    print("STATUS: 🎯 Analyzing mixing instructions...", file=sys.stderr, flush=True)
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
    
    print("STATUS: 🤖 Initializing AI DJ agent...", file=sys.stderr, flush=True)
    logger.info("Creating DJ agent")
    agent = create_dj_agent()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir) / f"floppy_mix_{timestamp}.wav"
    logger.info(f"Output path: {output_path}")
    
    print(f"STATUS: 📋 Planning mix strategy for {len(tracks)} track(s)...", file=sys.stderr, flush=True)
    
    track_list = "\n".join([
        f"  {i+1}. {track['title']} by {track.get('artist', 'Unknown')} - {track['path']}"
        for i, track in enumerate(tracks)
    ])
    
    prompt = f"""Create a DJ mix with these {len(tracks)} track(s) IN THE EXACT ORDER LISTED:

{track_list}

User instructions: {instructions}

Output file: {output_path}

IMPORTANT: You MUST add tracks to the mix in the EXACT order they are listed above (1, 2, 3, etc.).
The user selected these tracks in this specific order, so respect that order in the final mix.

Use the available tools to:
1. Load each track with load_audio_track(path, 'track_1'), load_audio_track(path, 'track_2'), etc.
2. Apply effects based on the user's instructions using the various effect tools
3. Add tracks to the mix IN ORDER with add_track_to_mix():
   - First track (track_1): crossfade_duration=0
   - Subsequent tracks: crossfade_duration=2-6 seconds
4. Render the final mix with render_final_mix('{output_path}', normalize=True)

Interpret the user's instructions and apply appropriate effects. If they mention:
- "boost bass" or "more bass": use bass_boost_db=4 to 6
- "reduce bass" or "less bass": use bass_boost_db=-3 to -6
- "boost treble" or "brighter": use treble_boost_db=3 to 5
- "smooth" or "reverb": use reverb_room_size=0.3-0.5 or apply_parallel_effects()
- "compress" or "consistent volume": use compressor_threshold_db=-12 to -15
- "remove rumble" or "clean bass": use highpass_cutoff_hz=80-100
- "warm" or "mellow": use lowpass_cutoff_hz=10000-12000 or distortion_drive_db=10-15
- "movement" or "swirl": use phaser_rate_hz=0.5-1.5 or chorus_rate_hz=1-3
- "lo-fi" or "retro": use apply_creative_effects() with bitcrush_bit_depth=8
- "build" or "tension": use automate_filter_sweep() with increasing cutoff
- "harmonic" or "key match": use pitch_shift_semitones=+/-7 or +/-12
- "clean" or "remove noise": use noise_gate_threshold_db=-40 to -50
- "aggressive" or "distorted": use distortion_drive_db=15-20 or clipping_threshold_db=-6
- "resonant" or "synth": use apply_ladder_filter() with resonance=0.5-0.8
- "crossfade" or "blend": use crossfade_duration=4-6 seconds

Be creative and use the full range of tools to create an engaging mix that matches the user's vision.
Start by loading all tracks, then apply effects, then add them to the mix, and finally render.
"""
    
    print("STATUS: 🎵 Agent is processing tracks and applying effects...", file=sys.stderr, flush=True)
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
        logger.info(f"Agent result type: {type(agent_result)}")
        if hasattr(agent_result, 'metrics'):
            logger.info(f"Agent metrics: {agent_result.metrics}")
        if hasattr(agent_result, 'message'):
            logger.info(f"Agent message type: {type(agent_result.message)}")
        
        print("STATUS: 🎚️ Finalizing mix and rendering audio...", file=sys.stderr, flush=True)
        
        if output_path.exists():
            file_size = output_path.stat().st_size
            logger.info(f"Mix file created: {output_path} ({file_size} bytes)")
            
            if file_size < 1000:
                logger.error(f"Mix file too small: {file_size} bytes")
                raise Exception(f"Generated mix file is too small ({file_size} bytes), likely invalid")
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            tool_calls = 0
            total_tokens = 0
            
            try:
                if hasattr(agent_result, 'metrics') and agent_result.metrics:
                    metrics = agent_result.metrics
                    
                    if hasattr(metrics, 'tool_metrics') and metrics.tool_metrics:
                        for tool_name, tool_metric in metrics.tool_metrics.items():
                            if hasattr(tool_metric, 'call_count'):
                                tool_calls += tool_metric.call_count
                    
                    if hasattr(metrics, 'accumulated_usage') and metrics.accumulated_usage:
                        usage = metrics.accumulated_usage
                        if isinstance(usage, dict):
                            total_tokens = usage.get('totalTokens', 0)
                            if not total_tokens:
                                total_tokens = usage.get('inputTokens', 0) + usage.get('outputTokens', 0)
                        elif hasattr(usage, 'totalTokens'):
                            total_tokens = usage.totalTokens
                        elif hasattr(usage, 'inputTokens') and hasattr(usage, 'outputTokens'):
                            total_tokens = usage.inputTokens + usage.outputTokens
                
                logger.info(f"Extracted stats: tool_calls={tool_calls}, tokens={total_tokens}")
            except Exception as e:
                logger.exception(f"Could not extract usage stats: {e}")
            
            stats = {
                'time_seconds': round(elapsed_time, 2),
                'file_size_mb': round(file_size / 1024 / 1024, 2),
                'num_tracks': len(tracks),
                'tool_calls': tool_calls,
                'tokens_used': total_tokens
            }
            
            print(f"STATUS: ✅ Mix complete! {elapsed_time:.1f}s, {tool_calls} tool calls", file=sys.stderr, flush=True)
            
            return {
                'mix_file_path': str(output_path),
                'statistics': stats
            }
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
        
        result = handle_mix_request(tracks, instructions, output_dir)
        
        response = {
            'status': 'success',
            'mix_file_path': result['mix_file_path'],
            'statistics': result['statistics']
        }
        
        logger.info(f"Mix completed successfully: {result['mix_file_path']}")
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
