from typing import Callable
from models import Track


class AgentError(Exception):
    """Agent failed to start or execute."""
    pass


class AgentTimeout(Exception):
    """Agent exceeded timeout."""
    pass


class MixingError(Exception):
    """Audio processing failed."""
    pass


class DJAgentClient:
    """Client for invoking the Strands Agents DJ agent."""
    
    def __init__(self, agent_script_path: str):
        """Initialize with path to DJ agent script."""
        self.agent_script_path = agent_script_path
        
    async def create_mix(
        self,
        tracks: list[Track],
        instructions: str,
        progress_callback: Callable[[str], None]
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
        pass
        
    def _prepare_agent_input(
        self,
        tracks: list[Track],
        instructions: str
    ) -> dict:
        """Prepare input data for agent."""
        pass
        
    async def _monitor_agent_progress(
        self,
        agent_process,
        progress_callback: Callable[[str], None]
    ) -> str:
        """Monitor agent execution and stream progress updates."""
        pass
