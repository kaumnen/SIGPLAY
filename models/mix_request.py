from dataclasses import dataclass


@dataclass
class MixRequest:
    """Request sent to DJ agent for mix creation."""
    
    tracks: list[dict]
    instructions: str
    output_dir: str
