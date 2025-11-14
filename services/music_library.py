from pathlib import Path
from typing import Dict, Any, List, Optional

from mutagen import File as MutagenFile

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
    
    def get_tracks(self) -> List[Track]:
        """Return cached track list.
        
        Returns:
            List of Track objects from last scan.
        """
        return self._tracks
    
    def get_track_by_index(self, index: int) -> Optional[Track]:
        """Retrieve specific track by index.
        
        Args:
            index: Index of track in track list.
            
        Returns:
            Track object if index is valid, None otherwise.
        """
        if 0 <= index < len(self._tracks):
            return self._tracks[index]
        return None
    
    def refresh(self) -> None:
        """Rescan library to update track list."""
        self.scan()
    
    @staticmethod
    def _extract_metadata(file_path: Path) -> Dict[str, Any]:
        """Extract metadata from audio file using mutagen.
        
        Args:
            file_path: Path to audio file.
            
        Returns:
            Dictionary containing title, artist, album, and duration.
            Uses fallbacks for missing tags.
            
        Raises:
            Exception: If file is corrupted or cannot be read.
        """
        try:
            audio = MutagenFile(file_path, easy=True)
            
            if audio is None:
                raise ValueError(f"Could not read audio file: {file_path}")
            
            title = file_path.stem
            if audio.tags:
                if 'title' in audio.tags:
                    title = str(audio.tags['title'][0]) if isinstance(audio.tags['title'], list) else str(audio.tags['title'])
                elif 'TIT2' in audio.tags:
                    title = str(audio.tags['TIT2'])
            
            artist = "Unknown Artist"
            if audio.tags:
                if 'artist' in audio.tags:
                    artist = str(audio.tags['artist'][0]) if isinstance(audio.tags['artist'], list) else str(audio.tags['artist'])
                elif 'TPE1' in audio.tags:
                    artist = str(audio.tags['TPE1'])
            
            album = "Unknown Album"
            if audio.tags:
                if 'album' in audio.tags:
                    album = str(audio.tags['album'][0]) if isinstance(audio.tags['album'], list) else str(audio.tags['album'])
                elif 'TALB' in audio.tags:
                    album = str(audio.tags['TALB'])
            
            duration = 0.0
            if audio.info and hasattr(audio.info, 'length'):
                duration = float(audio.info.length)
            
            return {
                'title': title,
                'artist': artist,
                'album': album,
                'duration': duration
            }
            
        except Exception as e:
            print(f"Warning: Could not extract metadata from {file_path}: {e}")
            raise
