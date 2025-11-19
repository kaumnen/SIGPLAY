#!/usr/bin/env python3
"""
Floppy Mix DJ Agent

An autonomous AI agent that interprets natural language mixing instructions
and generates professional DJ mixes using the Pedalboard audio processing library.
"""

import json
import sys
import tempfile
import logging
import subprocess
from pathlib import Path
from datetime import datetime

from strands import Agent, tool
from strands.models.bedrock import BedrockModel

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
        result = subprocess.run(
            [sys.executable, "-c", code],
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

When you receive a mixing request, you should:
1. Analyze the user's instructions and understand their intent
2. Plan the mixing approach (tempo matching, EQ adjustments, transitions, effects)
3. Write Python code using Pedalboard to execute the mix
4. Handle errors gracefully and provide clear feedback

Available capabilities:
- Load audio files (MP3, WAV, OGG, FLAC)
- Adjust tempo/BPM without changing pitch
- Apply EQ (bass, mid, treble adjustments)
- Create crossfade transitions for gapless playback
- Apply effects: reverb, chorus, delay, phaser, compression
- Render final mix to WAV file

Best practices:
- Always normalize audio levels to prevent clipping
- Use appropriate crossfade durations (2-4 seconds typical)
- Match tempos when user requests specific BPM
- Boost bass frequencies by 2-4 dB when user requests "more bass"
- Create smooth transitions between tracks
- Save output to the specified directory with timestamp in filename

Return the full path to the generated mix file when complete.
"""


def create_dj_agent() -> Agent:
    """Create and configure the DJ agent with AWS Bedrock."""
    model = BedrockModel(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        region="us-east-1"
    )
    
    agent = Agent(
        model=model,
        system_prompt=DJ_AGENT_SYSTEM_PROMPT,
        tools=[execute_python_code, write_file, read_file],
        max_iterations=10
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

Your task:
1. Analyze the user's instructions to understand their mixing intent
2. Generate a structured mixing plan that addresses:
   - Tempo adjustments (if BPM is specified)
   - EQ adjustments (bass, mid, treble)
   - Transitions between tracks (crossfades for gapless playback)
   - Any other effects mentioned
3. Write Python code using Pedalboard to execute the mix
4. Save the final mix to: {output_path}

Technical requirements:
- Import necessary libraries: pedalboard, soundfile (or librosa), numpy
- Load each audio file and verify it loads correctly
- Apply tempo changes using time stretching (preserve pitch)
- Apply EQ adjustments as needed
- Create smooth crossfade transitions between tracks (2-4 seconds)
- Normalize the final output to prevent clipping
- Save as WAV file at the specified path
- Handle errors gracefully with clear messages

Begin by writing the Python code to create the mix. Execute it and verify the output file is created.
"""
    
    print("STATUS: Generating mixing plan...", file=sys.stderr, flush=True)
    logger.info("Invoking agent to generate mixing plan")
    
    try:
        result = agent(prompt)
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
        print(json.dumps(response))
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        response = {
            'status': 'error',
            'error': f"File not found: {str(e)}"
        }
        print(json.dumps(response))
        sys.exit(1)
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        response = {
            'status': 'error',
            'error': f"Invalid input: {str(e)}"
        }
        print(json.dumps(response))
        sys.exit(1)
        
    except Exception as e:
        logger.exception(f"Error during mixing: {e}")
        response = {
            'status': 'error',
            'error': str(e)
        }
        print(json.dumps(response))
        sys.exit(1)


if __name__ == "__main__":
    main()
