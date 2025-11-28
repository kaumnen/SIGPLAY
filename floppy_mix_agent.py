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
from pathlib import Path
from datetime import datetime

from strands import Agent, tool
from strands.models.openai import OpenAIModel
from strands.hooks import HookProvider, HookRegistry, BeforeToolCallEvent, AfterToolCallEvent
from pedalboard import (
    Pedalboard, Reverb, Compressor, Chorus, Delay, Limiter,
    HighpassFilter, LowpassFilter, Gain, LowShelfFilter, HighShelfFilter,
    LadderFilter, Phaser, Distortion, Clipping, Bitcrush, NoiseGate,
    PitchShift, Mix
)
from pedalboard.io import AudioFile
import librosa

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


class MixContext:
    """Context for a single mix operation to avoid global state."""
    
    def __init__(self):
        self.audio_cache: dict = {}
        self.mix_segments: list = []
        self.bpm_cache: dict = {}
    
    def clear(self):
        self.audio_cache.clear()
        self.mix_segments.clear()
        self.bpm_cache.clear()


_mix_context = MixContext()


class ProgressHook(HookProvider):
    """Hook to stream progress updates during agent execution."""
    
    TOOL_DESCRIPTIONS = {
        'load_audio_track': '📂 Loading track',
        'detect_bpm': '🎵 Detecting BPM',
        'time_stretch_to_bpm': '⏱️ Time-stretching',
        'apply_effects': '🎛️ Applying effects',
        'apply_ladder_filter': '🎚️ Applying ladder filter',
        'apply_parallel_effects': '🔀 Applying parallel effects',
        'apply_creative_effects': '🎨 Applying creative effects',
        'automate_filter_sweep': '📈 Automating filter sweep',
        'add_track_to_mix': '➕ Adding track to mix',
        'render_final_mix': '💾 Rendering final mix',
    }
    
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.on_tool_start)
        registry.add_callback(AfterToolCallEvent, self.on_tool_end)
    
    def on_tool_start(self, event: BeforeToolCallEvent) -> None:
        tool_name = event.tool_use.get('name', 'unknown')
        description = self.TOOL_DESCRIPTIONS.get(tool_name, f'🔧 {tool_name}')
        
        tool_input = event.tool_use.get('input', {})
        if tool_name == 'load_audio_track':
            track_path = tool_input.get('track_path', '')
            track_name = Path(track_path).stem if track_path else 'track'
            print(f"STATUS: {description}: {track_name}...", file=sys.stderr, flush=True)
        elif tool_name == 'apply_effects':
            track_id = tool_input.get('track_id', '')
            print(f"STATUS: {description} to {track_id}...", file=sys.stderr, flush=True)
        elif tool_name == 'render_final_mix':
            print(f"STATUS: {description}...", file=sys.stderr, flush=True)
        else:
            print(f"STATUS: {description}...", file=sys.stderr, flush=True)
        
        logger.debug(f"Tool started: {tool_name}")
    
    def on_tool_end(self, event: AfterToolCallEvent) -> None:
        tool_name = event.tool_use.get('name', 'unknown')
        logger.debug(f"Tool completed: {tool_name}")


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
            
        _mix_context.audio_cache[track_id] = {
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
def detect_bpm(track_id: str) -> str:
    """Detect the BPM (tempo) of a loaded track using beat tracking.
    
    Args:
        track_id: ID of the loaded track to analyze
        
    Returns:
        Detected BPM value and confidence info
    """
    try:
        if track_id not in _mix_context.audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _mix_context.audio_cache[track_id]
        audio = track_data['audio']
        sample_rate = track_data['sample_rate']
        
        if audio.shape[0] > 1:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio[0]
        
        tempo, beat_frames = librosa.beat.beat_track(y=audio_mono, sr=sample_rate)
        
        if hasattr(tempo, '__len__'):
            bpm = float(tempo[0])
        else:
            bpm = float(tempo)
        
        _mix_context.bpm_cache[track_id] = bpm
        
        beat_times = librosa.frames_to_time(beat_frames, sr=sample_rate)
        num_beats = len(beat_times)
        
        logger.info(f"Detected BPM for {track_id}: {bpm:.1f} ({num_beats} beats)")
        return f"✓ {track_id} BPM: {bpm:.1f} ({num_beats} beats detected)"
        
    except Exception as e:
        logger.error(f"Failed to detect BPM for {track_id}: {e}")
        return f"✗ Error detecting BPM for {track_id}: {str(e)}"


MIN_BPM = 60.0
MAX_BPM = 200.0
MAX_STRETCH_RATIO = 1.15
MIN_STRETCH_RATIO = 0.85


@tool
def time_stretch_to_bpm(track_id: str, target_bpm: float, source_bpm: float | None = None) -> str:
    """Time-stretch a track to match a target BPM without changing pitch.
    
    Guardrails:
    - Target BPM must be between 60-200
    - Maximum stretch is ±15% (beyond this sounds bad)
    - Skips if already within 5% of target
    
    Args:
        track_id: ID of the loaded track to stretch
        target_bpm: Target BPM to stretch to (60-200 range)
        source_bpm: Source BPM (if None, uses cached BPM from detect_bpm or auto-detects)
        
    Returns:
        Success message with stretch ratio applied
    """
    try:
        if track_id not in _mix_context.audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        if not MIN_BPM <= target_bpm <= MAX_BPM:
            return f"✗ Error: Target BPM {target_bpm} out of range ({MIN_BPM}-{MAX_BPM})"
        
        track_data = _mix_context.audio_cache[track_id]
        audio = track_data['audio']
        sample_rate = track_data['sample_rate']
        
        if source_bpm is None:
            if track_id in _mix_context.bpm_cache:
                source_bpm = _mix_context.bpm_cache[track_id]
            else:
                if audio.shape[0] > 1:
                    audio_mono = np.mean(audio, axis=0)
                else:
                    audio_mono = audio[0]
                tempo, _ = librosa.beat.beat_track(y=audio_mono, sr=sample_rate)
                source_bpm = float(tempo[0]) if hasattr(tempo, '__len__') else float(tempo)
                _mix_context.bpm_cache[track_id] = source_bpm
        
        stretch_ratio = source_bpm / target_bpm
        
        if 0.95 <= stretch_ratio <= 1.05:
            logger.info(f"Skipping stretch for {track_id}: ratio {stretch_ratio:.3f} too close to 1.0")
            return f"✓ {track_id} already close to target ({source_bpm:.1f} → {target_bpm:.1f}, ratio {stretch_ratio:.3f})"
        
        if stretch_ratio > MAX_STRETCH_RATIO or stretch_ratio < MIN_STRETCH_RATIO:
            pct_change = abs(1 - stretch_ratio) * 100
            logger.warning(f"Stretch ratio {stretch_ratio:.3f} exceeds ±15% limit for {track_id}")
            return f"✗ Cannot stretch {track_id}: {source_bpm:.1f} → {target_bpm:.1f} BPM requires {pct_change:.0f}% change (max 15%). Tracks are too different in tempo."
        
        stretched_channels = []
        for ch in range(audio.shape[0]):
            stretched_ch = librosa.effects.time_stretch(audio[ch], rate=1.0/stretch_ratio)
            stretched_channels.append(stretched_ch)
        track_data['audio'] = np.array(stretched_channels)
        
        _mix_context.bpm_cache[track_id] = target_bpm
        
        pct_change = abs(1 - stretch_ratio) * 100
        logger.info(f"Stretched {track_id}: {source_bpm:.1f} → {target_bpm:.1f} BPM ({pct_change:.1f}% change)")
        return f"✓ Stretched {track_id}: {source_bpm:.1f} → {target_bpm:.1f} BPM ({pct_change:.1f}% change)"
        
    except Exception as e:
        logger.error(f"Failed to time-stretch {track_id}: {e}")
        return f"✗ Error time-stretching {track_id}: {str(e)}"





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
        if track_id not in _mix_context.audio_cache:
            return f"✗ Error: Track {track_id} not loaded. Load it first with load_audio_track."
        
        track_data = _mix_context.audio_cache[track_id]
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
            effects.append(Compressor(
                threshold_db=compressor_threshold_db,
                ratio=4.0,
                attack_ms=10.0,
                release_ms=100.0
            ))
            applied.append(f"compressor {compressor_threshold_db}dB")
        
        if pitch_shift_semitones != 0:
            effects.append(PitchShift(semitones=pitch_shift_semitones))
            applied.append(f"pitch {pitch_shift_semitones:+.1f}st")
        
        if chorus_rate_hz > 0:
            effects.append(Chorus(
                rate_hz=chorus_rate_hz,
                depth=0.25,
                centre_delay_ms=7.0,
                mix=0.5
            ))
            applied.append(f"chorus {chorus_rate_hz}Hz")
        
        if phaser_rate_hz > 0:
            effects.append(Phaser(
                rate_hz=phaser_rate_hz,
                depth=0.5,
                feedback=0.3,
                mix=0.5
            ))
            applied.append(f"phaser {phaser_rate_hz}Hz")
        
        if delay_seconds > 0:
            effects.append(Delay(
                delay_seconds=delay_seconds,
                feedback=0.3,
                mix=0.3
            ))
            applied.append(f"delay {delay_seconds}s")
        
        if reverb_room_size > 0:
            effects.append(Reverb(
                room_size=reverb_room_size,
                damping=0.5,
                wet_level=0.3,
                dry_level=0.7,
                width=1.0
            ))
            applied.append(f"reverb {reverb_room_size}")
        
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
        if track_id not in _mix_context.audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _mix_context.audio_cache[track_id]
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
        if track_id not in _mix_context.audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _mix_context.audio_cache[track_id]
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
        if track_id not in _mix_context.audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _mix_context.audio_cache[track_id]
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
        if track_id not in _mix_context.audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _mix_context.audio_cache[track_id]
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
        if track_id not in _mix_context.audio_cache:
            return f"✗ Error: Track {track_id} not loaded"
        
        track_data = _mix_context.audio_cache[track_id]
        audio = track_data['audio'].copy()
        sample_rate = track_data['sample_rate']
        
        start_sample = int(start_time * sample_rate)
        end_sample = int(end_time * sample_rate) if end_time else audio.shape[1]
        
        audio = audio[:, start_sample:end_sample]
        
        _mix_context.mix_segments.append({
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
        if not _mix_context.mix_segments:
            return "✗ Error: No tracks added to mix. Use add_track_to_mix first."
        
        logger.info(f"Rendering final mix with {len(_mix_context.mix_segments)} segments")
        
        final_audio = None
        sample_rate = _mix_context.mix_segments[0]['sample_rate']
        
        for i, segment in enumerate(_mix_context.mix_segments):
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
            limiter = Limiter(threshold_db=-1.0, release_ms=100.0)
            final_audio = limiter(final_audio, sample_rate)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with AudioFile(str(output_file), 'w', sample_rate, final_audio.shape[0]) as f:
            f.write(final_audio)
        
        duration = final_audio.shape[1] / sample_rate
        file_size = output_file.stat().st_size
        
        logger.info(f"Mix rendered: {output_path} ({duration:.1f}s, {file_size} bytes)")
        return f"✓ Mix saved to {output_path} ({duration:.1f}s, {file_size / 1024 / 1024:.1f}MB)"
        
    except Exception as e:
        logger.error(f"Failed to render mix: {e}")
        return f"✗ Error rendering mix: {str(e)}"

DJ_AGENT_SYSTEM_PROMPT = """You are an expert DJ and audio engineer. Your #1 rule: LESS IS MORE.

CRITICAL: Most mixes sound best with MINIMAL or NO effects. Only apply effects when explicitly requested.
If the user says "clean" or "no effects", apply ZERO effects - just crossfade the tracks.

WORKFLOW:
1. Load each track using load_audio_track(track_path, track_id)
2. If user wants BPM matching: detect_bpm() then time_stretch_to_bpm() to sync tempos
3. Apply effects ONLY if specifically requested (skip this step for clean mixes)
4. Add tracks to the mix using add_track_to_mix(track_id, crossfade_duration)
5. Render the final mix using render_final_mix(output_path)

GOLDEN RULES:
- When in doubt, DON'T apply an effect
- Never stack more than 1-2 effects on a single track
- Use very conservative values (half of what you think)
- The original audio already sounds good - don't ruin it

AVAILABLE TOOLS:

1. load_audio_track(track_path, track_id) - Load audio file

2. detect_bpm(track_id) - Analyze track and return detected BPM
   - Call after loading to find the track's tempo
   - Returns BPM value (e.g., 120.5 BPM)

3. time_stretch_to_bpm(track_id, target_bpm, source_bpm=None) - Time-stretch without pitch change
   - Stretches track to match target BPM (must be 60-200 BPM)
   - LIMIT: Max ±15% tempo change (beyond this sounds bad)
   - Skips if already within 5% of target
   - If tracks differ by >15%, DON'T try to sync - just crossfade them

4. apply_effects(track_id, ...) - Standard effects (USE SPARINGLY)
   - compressor_threshold_db: Use -15 to -18 (gentle), never below -10
   - bass_boost_db: Use +2 to +3 max (not +6!)
   - treble_boost_db: Use +1 to +2 max
   - reverb_room_size: Use 0.15 to 0.25 max (not 0.5!)
   - highpass_cutoff_hz: 30-60Hz to remove rumble only
   - lowpass_cutoff_hz: 12000-15000Hz for subtle warmth
   - gain_db: Small adjustments only (-3 to +3)

3. apply_ladder_filter(track_id, mode, cutoff_hz, resonance) - Resonant filter
   - Only use if user specifically asks for filter effects
   - Keep resonance low (0.2-0.4)

4. apply_parallel_effects(track_id, ...) - Parallel wet/dry processing
   - Best way to add reverb - keeps dry signal intact
   - wet_gain_db should be -9 to -12 (very subtle)

5. apply_creative_effects(track_id, ...) - Lo-fi effects
   - ONLY use if user explicitly asks for lo-fi/retro sound
   - bitcrush: 12-bit is subtle, 8-bit is noticeable

6. automate_filter_sweep(track_id, ...) - Filter automation
   - Only for dramatic builds when requested

7. add_track_to_mix(track_id, crossfade_duration, start_time, end_time)
   - crossfade_duration: 2-4 seconds is usually ideal
   - First track always has crossfade_duration=0

8. render_final_mix(output_path, normalize=True) - Always normalize

EFFECT GUIDELINES (only when requested):
- "compression" or "consistent volume": compressor_threshold_db=-15 (gentle!)
- "bass boost": bass_boost_db=+2 (subtle!)
- "warm" or "mellow": lowpass_cutoff_hz=12000 (just soften highs)
- "reverb" or "spacey": use apply_parallel_effects with wet_gain_db=-9
- "clean bass": highpass_cutoff_hz=40 (remove sub-rumble only)
- "lo-fi": lowpass_cutoff_hz=10000 (NO bitcrush unless they say "8-bit" or "crushed")

EXAMPLE - CLEAN MIX (most common):
1. load_audio_track('/path/track1.mp3', 'track_1')
2. load_audio_track('/path/track2.mp3', 'track_2')
3. add_track_to_mix('track_1', crossfade_duration=0)
4. add_track_to_mix('track_2', crossfade_duration=3.0)
5. render_final_mix('/output/mix.wav', normalize=True)

EXAMPLE - WITH LIGHT COMPRESSION:
1. load_audio_track('/path/track1.mp3', 'track_1')
2. apply_effects('track_1', compressor_threshold_db=-15)
3. add_track_to_mix('track_1', crossfade_duration=0)
4. render_final_mix('/output/mix.wav', normalize=True)

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
            detect_bpm,
            time_stretch_to_bpm,
            apply_effects,
            apply_ladder_filter,
            apply_parallel_effects,
            apply_creative_effects,
            automate_filter_sweep,
            add_track_to_mix,
            render_final_mix
        ],
        hooks=[ProgressHook()]
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
    _mix_context.clear()
    
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
- "sync tempo", "match bpm", "beatmatch": detect_bpm() all tracks, then time_stretch_to_bpm() to match
- "speed up" or "faster": time_stretch_to_bpm() with higher target BPM
- "slow down" or "slower": time_stretch_to_bpm() with lower target BPM

BPM MATCHING WORKFLOW (when requested):
1. Load all tracks
2. detect_bpm() on each track
3. Check if BPMs are within 15% of each other - if not, SKIP tempo sync and warn user
4. Choose target BPM (usually the first track's BPM, or user-specified)
5. time_stretch_to_bpm() on tracks that need adjustment (only if within ±15%)
6. Apply effects if requested
7. Add to mix and render

IMPORTANT: If tracks have very different tempos (e.g., 80 BPM vs 140 BPM), do NOT try to sync them.
Just mix them with crossfades and let the user know tempo sync wasn't possible.

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
        _mix_context.clear()


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
