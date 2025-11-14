from pathlib import Path
from typing import List, Optional

from models.track import Track


class MusicLibrary:
    """Service for discovering and managing music files."""
    
    SUPPORTED_EXTENSIONS = {'.mp3', '.flac', '.wav', '.ogg', '.m4a'}
    DEFAULT_MUSIC_DIR = Path.home() / "Music"
    
    def __init__(self, music_dir: Optional[Path] = None):
        """Initialize MusicLibrary with optional custom music directory.
        
        Args:
            music_dir: Path to music directory. Defaults to ~/Music if not provided.
        """
        self.music_dir = music_dir or self.DEFAULT_MUSIC_DIR
        self._tracks: List[Track] = []
    
    def scan(self) -> List[Track]:
        """Scan music directory for audio files and build track list.
        
        Returns:
            List of Track objects sorted by artist, album, then title.
        """
        self._tracks = []
        
        if not self.music_dir.exists():
            return self._tracks
        
        audio_files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            audio_files.extend(self.music_dir.rglob(f"*{ext}"))
        
        for file_path in audio_files:
            try:
                metadata = self._extract_metadata(file_path)
                track = Track.from_file(file_path, metadata)
                self._tracks.append(track)
            except Exception:
                continue
        
        self._tracks.sort(key=lambda t: (t.artist.lower(), t.album.lower(), t.title.lower()))
        
        return self._tracks
