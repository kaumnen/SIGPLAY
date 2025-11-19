"""
DJ Agent Client Service

Client for invoking and communicating with the Strands Agents DJ agent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable

from models import Track

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Raised when agent fails to start or execute."""
    pass


class AgentTimeout(Exception):
    """Raised when agent exceeds timeout."""
    pass


class MixingError(Exception):
    """Raised when audio processing fails."""
    pass


class DJAgentClient:
    """Client for invoking the Strands Agents DJ agent."""
    
    AGENT_TIMEOUT = 300  # 5 minutes in seconds
    
    def __init__(self, agent_script_path: str = "floppy_mix_agent.py"):
        """
        Initialize with path to DJ agent script.
        
        Args:
            agent_script_path: Path to the DJ agent Python script
        """
        self.agent_script_path = Path(agent_script_path)
        
        if not self.agent_script_path.exists():
            raise FileNotFoundError(f"DJ agent script not found: {agent_script_path}")
    
    async def create_mix(
        self,
        tracks: list[Track],
        instructions: str,
        progress_callback: Callable[[str], None] | None = None
    ) -> str:
        """
        Invoke DJ agent to create a mix.
        
        Args:
            tracks: List of Track objects to mix
            instructions: Natural language mixing instructions
            progress_callback: Function to call with status updates
            
        Returns:
            Path to the generated mix file
            
        Raises:
            AgentError: If agent fails to start or execute
            AgentTimeout: If agent exceeds timeout (5 minutes)
            MixingError: If audio processing fails
        """
        if not tracks:
            raise ValueError("At least one track must be provided")
        
        if not instructions or not instructions.strip():
            raise ValueError("Mixing instructions must be provided")
        
        for track in tracks:
            if not Path(track.file_path).exists():
                raise FileNotFoundError(
                    f"Track file not found: {track.title} ({track.file_path}). "
                    "Please check your music library."
                )
        
        logger.info(f"Creating mix with {len(tracks)} tracks")
        
        request_data = self._prepare_agent_input(tracks, instructions)
        
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        ) as request_file:
            json.dump(request_data, request_file)
            request_file_path = request_file.name
        
        agent_process = None
        
        try:
            try:
                env = os.environ.copy()
                
                agent_process = await asyncio.create_subprocess_exec(
                    'uv', 'run', str(self.agent_script_path), request_file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )
            except FileNotFoundError:
                logger.error("uv command not found")
                raise AgentError(
                    "Cannot start DJ agent: 'uv' command not found. "
                    "Please ensure uv is installed and in your PATH."
                )
            except Exception as e:
                logger.error(f"Failed to start agent process: {e}")
                raise AgentError(
                    f"Cannot start DJ agent: {str(e)}. "
                    "Please check your Strands Agents installation."
                )
            
            logger.info(f"Agent process started with PID {agent_process.pid}")
            
            mix_file_path = await self._monitor_agent_progress(
                agent_process,
                progress_callback
            )
            
            return mix_file_path
            
        except asyncio.TimeoutError:
            logger.error("Agent execution timed out")
            if agent_process:
                try:
                    agent_process.kill()
                    await agent_process.wait()
                except Exception as e:
                    logger.warning(f"Error killing agent process: {e}")
            raise AgentTimeout(
                f"DJ agent timed out after {self.AGENT_TIMEOUT} seconds. "
                "Try simpler instructions or fewer tracks."
            )
        except (AgentError, AgentTimeout, MixingError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during agent execution: {e}")
            raise AgentError(f"Failed to execute DJ agent: {str(e)}")
        finally:
            try:
                Path(request_file_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup request file: {e}")
    
    def _prepare_agent_input(
        self,
        tracks: list[Track],
        instructions: str
    ) -> dict:
        """
        Prepare input data for agent.
        
        Args:
            tracks: List of Track objects
            instructions: User's mixing instructions
            
        Returns:
            Dictionary with tracks, instructions, and output directory
        """
        output_dir = Path.home() / '.local' / 'share' / 'sigplay' / 'temp_mixes'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        track_data = [
            {
                'path': str(track.file_path),
                'title': track.title,
                'artist': track.artist or 'Unknown',
                'duration': track.duration
            }
            for track in tracks
        ]
        
        return {
            'tracks': track_data,
            'instructions': instructions,
            'output_dir': str(output_dir)
        }
    
    async def _monitor_agent_progress(
        self,
        agent_process: asyncio.subprocess.Process,
        progress_callback: Callable[[str], None] | None
    ) -> str:
        """
        Monitor agent execution and stream progress updates.
        
        Args:
            agent_process: The running agent subprocess
            progress_callback: Function to call with status updates
            
        Returns:
            Path to the generated mix file
            
        Raises:
            AgentTimeout: If agent exceeds timeout
            AgentError: If agent fails
            MixingError: If audio processing fails
        """
        stderr_lines = []
        stdout_data = []
        
        async def read_stderr():
            """Read and process stderr output for status messages."""
            if agent_process.stderr:
                async for line in agent_process.stderr:
                    line_text = line.decode('utf-8').strip()
                    stderr_lines.append(line_text)
                    
                    if line_text.startswith('STATUS:'):
                        status_msg = line_text[7:].strip()
                        logger.info(f"Agent status: {status_msg}")
                        if progress_callback:
                            progress_callback(status_msg)
                    elif line_text.startswith('ERROR:'):
                        error_msg = line_text[6:].strip()
                        logger.error(f"Agent error: {error_msg}")
                    else:
                        logger.debug(f"Agent stderr: {line_text}")
        
        async def read_stdout():
            """Read stdout output."""
            if agent_process.stdout:
                data = await agent_process.stdout.read()
                if data:
                    stdout_data.append(data)
        
        stderr_task = asyncio.create_task(read_stderr())
        stdout_task = asyncio.create_task(read_stdout())
        
        try:
            await asyncio.wait_for(
                agent_process.wait(),
                timeout=self.AGENT_TIMEOUT
            )
            
            await asyncio.gather(stderr_task, stdout_task)
            
            if agent_process.returncode != 0:
                error_details = '\n'.join(stderr_lines[-5:]) if stderr_lines else 'Unknown error'
                logger.error(f"Agent failed with exit code {agent_process.returncode}")
                
                if any('OPENROUTER_API_KEY' in line for line in stderr_lines):
                    raise AgentError(
                        "❌ OpenRouter API key not configured.\n\n"
                        "Set your OpenRouter API key as an environment variable:\n"
                        "  export OPENROUTER_API_KEY=your-api-key\n\n"
                        "To get an API key:\n"
                        "1. Go to https://openrouter.ai/keys\n"
                        "2. Sign in or create an account\n"
                        "3. Generate a new API key\n"
                        "4. Copy and set it as OPENROUTER_API_KEY"
                    )
                elif any('401' in line or 'unauthorized' in line.lower() for line in stderr_lines):
                    raise AgentError(
                        "❌ OpenRouter API key error.\n\n"
                        "Your API key may be invalid or expired.\n"
                        "Generate a new key at https://openrouter.ai/keys and set:\n"
                        "  export OPENROUTER_API_KEY=your-new-api-key"
                    )
                elif any('insufficient credits' in line.lower() or 'quota' in line.lower() for line in stderr_lines):
                    raise AgentError(
                        "❌ OpenRouter credits exhausted.\n\n"
                        "Add credits to your OpenRouter account:\n"
                        "https://openrouter.ai/credits"
                    )
                elif any('model not found' in line.lower() or 'invalid model' in line.lower() for line in stderr_lines):
                    raise AgentError(
                        "❌ Model not available.\n\n"
                        "The selected model may not be available on OpenRouter.\n"
                        "Check available models at: https://openrouter.ai/models\n\n"
                        "Set a different model:\n"
                        "  export OPENROUTER_MODEL=anthropic/claude-3.5-sonnet"
                    )
                else:
                    raise AgentError(
                        f"DJ agent failed with exit code {agent_process.returncode}. "
                        f"Details: {error_details}"
                    )
            
            stdout = b''.join(stdout_data).decode('utf-8')
            
            try:
                response = json.loads(stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse agent response: {e}")
                raise AgentError(f"Invalid response from DJ agent: {str(e)}")
            
            if response.get('status') == 'error':
                error_msg = response.get('error', 'Unknown error')
                logger.error(f"Agent returned error: {error_msg}")
                raise MixingError(f"Mixing failed: {error_msg}")
            
            mix_file_path = response.get('mix_file_path')
            if not mix_file_path:
                logger.error("Agent response missing mix_file_path")
                raise AgentError("DJ agent did not return a mix file path")
            
            if not Path(mix_file_path).exists():
                logger.error(f"Mix file not found: {mix_file_path}")
                raise MixingError(f"Mix file was not created: {mix_file_path}")
            
            logger.info(f"Mix created successfully: {mix_file_path}")
            return mix_file_path
            
        except asyncio.TimeoutError:
            stderr_task.cancel()
            stdout_task.cancel()
            raise
