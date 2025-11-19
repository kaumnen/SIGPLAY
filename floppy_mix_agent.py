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
import subprocess
from pathlib import Path
from datetime import datetime

from strands import Agent, tool
from strands.models.openai import OpenAIModel

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


@tool
def execute_python_code(code: str) -> str:
    """Execute Python code and return the output.
    
    Args:
        code: Python code to execute
        
    Returns:
        The output from executing the code
    """
    try:
        temp_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        try:
            temp_script.write(code)
            temp_script.close()
            
            result = subprocess.run(
                ["uv", "run", "python", temp_script.name],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            
            if result.returncode != 0:
                return f"Error (exit code {result.returncode}):\n{output}"
            
            return output if output else "Code executed successfully (no output)"
        finally:
            Path(temp_script.name).unlink(missing_ok=True)
        
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out after 5 minutes"
    except Exception as e:
        return f"Error executing code: {str(e)}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file.
    
    Args:
        path: Path to the file
        content: Content to write
        
    Returns:
        Success message
    """
    try:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def read_file(path: str) -> str:
    """Read content from a file.
    
    Args:
        path: Path to the file
        
    Returns:
        File content
    """
    try:
        return Path(path).read_text()
    except Exception as e:
        return f"Error reading file: {str(e)}"

DJ_AGENT_SYSTEM_PROMPT = """You are an expert DJ and audio engineer with deep knowledge of music mixing and audio processing.

Your role is to create professional DJ mixes using Python and the Pedalboard library.

CRITICAL: You must write a SINGLE Python script that:
1. Loads ALL audio files into memory first
2. Processes them in memory (no intermediate files)
3. Concatenates them with crossfades
4. Saves ONLY the final output file

DO NOT create intermediate files like "temp_mix_step_01.mp3" - work entirely in memory using numpy arrays.

Example structure:
```python
import soundfile as sf
import numpy as np
from pedalboard import Pedalboard, Reverb, Compressor
from pedalboard.io import AudioFile

# Load all tracks
tracks_audio = []
for track_path in ['/path/to/track1.mp3', '/path/to/track2.mp3']:
    with AudioFile(track_path) as f:
        audio = f.read(f.frames)
        sr = f.samplerate
        tracks_audio.append((audio, sr))

# Process and mix in memory
final_audio = []
for i, (audio, sr) in enumerate(tracks_audio):
    # Apply effects
    board = Pedalboard([Compressor(threshold_db=-10)])
    processed = board(audio, sr)
    
    # Add crossfade if not first track
    if i > 0 and len(final_audio) > 0:
        crossfade_samples = int(3.0 * sr)  # 3 second crossfade
        # Implement crossfade logic
    
    final_audio.append(processed)

# Concatenate and save
final_mix = np.concatenate(final_audio, axis=1)
sf.write('/output/path.wav', final_mix.T, sr)
```

Available capabilities:
- Load audio files (MP3, WAV, OGG, FLAC) using pedalboard.io.AudioFile
- Apply effects: reverb, chorus, delay, compression, EQ
- Create crossfade transitions for smooth playback
- Normalize audio levels to prevent clipping

Best practices:
- Load all audio into memory first
- Process in memory using numpy arrays
- Use 2-4 second crossfades between tracks
- Normalize final output
- Save only the final mix file

Return the full path to the generated mix file when complete.
"""


def create_dj_agent() -> Agent:
    """Create and configure the DJ agent with OpenRouter."""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable not set. "
            "Get your API key from https://openrouter.ai/keys"
        )
    
    model_id = os.environ.get('OPENROUTER_MODEL', 'anthropic/claude-sonnet-4.5')
    
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
        tools=[execute_python_code, write_file, read_file]
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
        f"  - {track['title']} by {track.get('artist', 'Unknown')} ({track['path']})"
        for track in tracks
    ])
    
    prompt = f"""
Create a DJ mix with the following {len(tracks)} track(s):
{track_list}

User instructions: {instructions}

CRITICAL REQUIREMENTS:
1. Write a SINGLE Python script that works entirely in memory
2. DO NOT create any intermediate files (no temp_mix_step_01.mp3, etc.)
3. Load all tracks into memory first using pedalboard.io.AudioFile
4. Process and mix in memory using numpy arrays
5. Save ONLY the final output to: {output_path}

Your task:
1. Load all audio files into memory as numpy arrays
2. Apply effects/processing to each track in memory
3. Concatenate tracks with crossfade transitions (2-4 seconds)
4. Normalize the final mix to prevent clipping
5. Save the final mix to the specified path

Technical requirements:
- Use pedalboard.io.AudioFile to load audio files
- Use numpy for array operations and concatenation
- Use soundfile (sf.write) to save the final output
- Apply crossfades by blending overlapping audio samples
- Normalize using: audio = audio / np.max(np.abs(audio)) * 0.95
- Handle errors gracefully with clear messages

Example crossfade logic:
```python
crossfade_samples = int(3.0 * sample_rate)
fade_out = np.linspace(1, 0, crossfade_samples)
fade_in = np.linspace(0, 1, crossfade_samples)
# Apply fades to overlapping regions
```

Begin by writing and executing the Python code to create the mix.
"""
    
    print("STATUS: Generating mixing plan...", file=sys.stderr, flush=True)
    logger.info("Invoking agent to generate mixing plan")
    
    try:
        import io
        import contextlib
        
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            agent(prompt)
        
        captured_output = stdout_capture.getvalue()
        if captured_output:
            logger.info(f"Agent stdout: {captured_output[:500]}")
        
        logger.info("Agent execution completed")
        
        print("STATUS: Rendering final mix...", file=sys.stderr, flush=True)
        
        if output_path.exists():
            file_size = output_path.stat().st_size
            logger.info(f"Mix file created: {output_path} ({file_size} bytes)")
            
            if file_size < 1000:
                logger.error(f"Mix file too small: {file_size} bytes")
                raise Exception(f"Generated mix file is too small ({file_size} bytes), likely invalid")
            
            print(f"Mix created successfully: {output_path} ({file_size} bytes)", file=sys.stderr, flush=True)
            return str(output_path)
        else:
            logger.error(f"Mix file not created at: {output_path}")
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
