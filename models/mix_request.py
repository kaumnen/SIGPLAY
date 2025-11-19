from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class MixRequest:
    """Request sent to DJ agent for mix creation."""
    
    tracks: list[dict]
    instructions: str
    output_dir: str
    
    def validate(self) -> tuple[bool, str | None]:
        """Validate the mix request.
        
        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is None.
        """
        if not self.tracks:
            return False, "At least one track must be selected"
        
        if not self.instructions or not self.instructions.strip():
            return False, "Mixing instructions cannot be empty"
        
        for i, track in enumerate(self.tracks):
            if not isinstance(track, dict):
                return False, f"Track {i} must be a dictionary"
            
            required_fields = ['path', 'title', 'artist', 'duration']
            for field in required_fields:
                if field not in track:
                    return False, f"Track {i} missing required field: {field}"
            
            track_path = Path(track['path'])
            if not track_path.exists():
                return False, f"Track file not found: {track['path']}"
        
        output_path = Path(self.output_dir)
        if not output_path.exists():
            return False, f"Output directory does not exist: {self.output_dir}"
        
        if not output_path.is_dir():
            return False, f"Output path is not a directory: {self.output_dir}"
        
        return True, None
    
    def is_valid(self) -> bool:
        """Check if the mix request is valid.
        
        Returns:
            True if valid, False otherwise.
        """
        valid, _ = self.validate()
        return valid
