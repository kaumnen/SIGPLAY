from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Callable

from faster_whisper.utils import get_assets_path

from models.lyrics import LyricSegment

logger = logging.getLogger(__name__)


class LyricsService:
    """Service for managing Whisper model and lyrics transcription."""
    
    AVAILABLE_MODELS = [
        ("tiny", "Tiny (~75 MB) - Fastest, lowest accuracy"),
        ("base", "Base (~150 MB) - Good balance of speed and accuracy"),
        ("small", "Small (~500 MB) - Better accuracy, slower"),
        ("medium", "Medium (~1.5 GB) - High accuracy, much slower"),
        ("large-v3", "Large V3 (~3 GB) - Best accuracy, very slow"),
    ]
    
    def __init__(self) -> None:
        """Initialize service with cache directory setup."""
        self._current_model_name: str | None = None
        self._cache_dir: Path = Path.home() / ".local/share/sigplay/lyrics_cache"
        self._device: str | None = None
        self._compute_type: str | None = None
        
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Lyrics cache directory: {self._cache_dir}")
        except Exception as e:
            logger.error(f"Failed to create cache directory: {e}")
        
        self._detect_device()
    
    def _detect_device(self) -> None:
        """Detect best available device for Whisper processing.
        
        Checks for CUDA availability and falls back to CPU if needed.
        Sets device and compute_type for optimal performance.
        """
        try:
            import torch
            if torch.cuda.is_available():
                self._device = "cuda"
                self._compute_type = "float16"
                logger.info(f"CUDA detected: Using GPU acceleration (compute_type: {self._compute_type})")
                return
        except ImportError:
            logger.debug("PyTorch not available, checking for CUDA via faster-whisper")
        except Exception as e:
            logger.warning(f"Error checking CUDA via PyTorch: {e}")
        
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                self._device = "cuda"
                self._compute_type = "float16"
                logger.info(f"CUDA detected via ctranslate2: Using GPU acceleration (compute_type: {self._compute_type})")
                return
        except ImportError:
            logger.debug("ctranslate2 not available for CUDA detection")
        except Exception as e:
            logger.warning(f"Error checking CUDA via ctranslate2: {e}")
        
        self._device = "cpu"
        self._compute_type = "int8"
        logger.info(f"No CUDA detected: Using CPU (compute_type: {self._compute_type})")
    
    def get_device_info(self) -> str:
        """Get human-readable device information.
        
        Returns:
            String describing the device and compute type being used.
        """
        if self._device == "cuda":
            return f"GPU (CUDA) - {self._compute_type}"
        return f"CPU - {self._compute_type}"
    
    def get_downloaded_models(self) -> list[str]:
        """Get list of already downloaded Whisper models.
        
        Returns:
            List of model names that are already downloaded.
        """
        downloaded = []
        try:
            assets_path = Path(get_assets_path())
            
            for model_name, _ in self.AVAILABLE_MODELS:
                model_path = assets_path / model_name
                if model_path.exists() and any(model_path.iterdir()):
                    downloaded.append(model_name)
                    logger.debug(f"Found downloaded model: {model_name}")
        except Exception as e:
            logger.error(f"Error checking downloaded models: {e}", exc_info=True)
        
        return downloaded
    
    def set_model(self, model_name: str) -> None:
        """Set the model to use for transcription.
        
        Args:
            model_name: Name of the Whisper model to use.
        """
        self._current_model_name = model_name
        logger.info(f"Model set to: {model_name}")
    
    async def download_model(
        self, model_name: str, progress_callback: Callable[[str], None] | None = None
    ) -> bool:
        """Download a Whisper model if not already downloaded.
        
        Uses subprocess to avoid tqdm multiprocessing issues in Textual.
        
        Args:
            model_name: Name of the model to download.
            progress_callback: Optional callback for progress updates.
            
        Returns:
            True if download succeeded, False otherwise.
        """
        try:
            if progress_callback:
                progress_callback(f"Downloading {model_name} model...")
            
            logger.info(f"Downloading Whisper {model_name} model via subprocess...")
            
            download_script = (
                "import os\n"
                "os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'\n"
                "os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'\n"
                "\n"
                "from faster_whisper import WhisperModel\n"
                "\n"
                "try:\n"
                f"    model = WhisperModel('{model_name}', device='{self._device}', compute_type='{self._compute_type}')\n"
                "    del model\n"
                "    print('SUCCESS')\n"
                "except Exception as e:\n"
                "    import traceback\n"
                "    print('ERROR: ' + str(e))\n"
                "    traceback.print_exc()\n"
            )
            
            import os
            env = os.environ.copy()
            env['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
            env['HF_HUB_DISABLE_TELEMETRY'] = '1'
            
            process = await asyncio.create_subprocess_exec(
                "uv",
                "run",
                "python",
                "-c",
                download_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=600
            )
            
            output = stdout.decode().strip()
            
            if "SUCCESS" in output:
                if progress_callback:
                    progress_callback(f"✓ {model_name} model ready")
                logger.info(f"Model {model_name} downloaded successfully")
                return True
            else:
                error_msg = output if output else stderr.decode().strip()
                logger.error(f"Failed to download model: {error_msg}")
                if progress_callback:
                    progress_callback("✗ Download failed")
                return False
                
        except asyncio.TimeoutError:
            logger.error("Model download timed out after 10 minutes")
            if progress_callback:
                progress_callback("✗ Download timed out")
            return False
        except Exception as e:
            logger.error(f"Failed to download model: {e}", exc_info=True)
            if progress_callback:
                progress_callback(f"✗ Download failed: {str(e)[:50]}")
            return False
    

    def _get_cache_key(self, track_path: str) -> str:
        """Generate cache key using MD5 hash of track path.
        
        Args:
            track_path: Path to the audio track file.
            
        Returns:
            MD5 hash of the track path as hexadecimal string.
        """
        return hashlib.md5(track_path.encode()).hexdigest()
    
    async def get_lyrics(
        self,
        track_path: str,
        progress_callback: Callable[[str], None] | None = None
    ) -> list[LyricSegment]:
        """Get lyrics for track, from cache or by transcribing.
        
        Args:
            track_path: Path to the audio track file.
            progress_callback: Optional callback for progress updates.
            
        Returns:
            List of LyricSegment objects with timestamped lyrics.
            
        Raises:
            FileNotFoundError: If the audio file doesn't exist.
            RuntimeError: If transcription fails.
        """
        track_file = Path(track_path)
        if not track_file.exists():
            logger.error(f"Audio file not found: {track_path}")
            raise FileNotFoundError(f"Audio file not found: {track_path}")
        
        cache_key = self._get_cache_key(track_path)
        cache_file = self._cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            logger.info(f"Loading lyrics from cache: {cache_key}")
            try:
                data = json.loads(cache_file.read_text())
                return [LyricSegment(**seg) for seg in data]
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted cache file, will re-transcribe: {e}")
                try:
                    cache_file.unlink(missing_ok=True)
                except Exception as unlink_error:
                    logger.error(f"Failed to delete corrupted cache file: {unlink_error}", exc_info=True)
            except Exception as e:
                logger.error(f"Failed to read cache file, will re-transcribe: {e}", exc_info=True)
                try:
                    cache_file.unlink(missing_ok=True)
                except Exception as unlink_error:
                    logger.error(f"Failed to delete invalid cache file: {unlink_error}", exc_info=True)
        
        try:
            if progress_callback:
                progress_callback("Loading Whisper model...")
            
            model_name = self._current_model_name or "base"
            logger.info(f"Transcribing via subprocess: {track_path}")
            
            transcribe_script = f"""
import os
import json
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'

from faster_whisper import WhisperModel

try:
    model = WhisperModel('{model_name}', device='{self._device}', compute_type='{self._compute_type}')
    segments, info = model.transcribe('{track_path}', word_timestamps=True, beam_size=5)
    
    lyrics = []
    for segment in segments:
        lyrics.append({{
            'start': segment.start,
            'end': segment.end,
            'text': segment.text.strip()
        }})
    
    result = {{
        'status': 'success',
        'language': info.language,
        'language_probability': info.language_probability,
        'lyrics': lyrics
    }}
    print(json.dumps(result))
except Exception as e:
    import traceback
    result = {{
        'status': 'error',
        'error': str(e),
        'traceback': traceback.format_exc()
    }}
    print(json.dumps(result))
"""
            
            import os
            env = os.environ.copy()
            env['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
            env['HF_HUB_DISABLE_TELEMETRY'] = '1'
            
            if progress_callback:
                progress_callback(f"Generating lyrics for {track_file.name}...")
            
            process = await asyncio.create_subprocess_exec(
                "uv",
                "run",
                "python",
                "-c",
                transcribe_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=300
            )
            
            output = stdout.decode().strip()
            
            try:
                result = json.loads(output)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse transcription output: {e}")
                logger.error(f"stdout: {output}")
                logger.error(f"stderr: {stderr.decode()}")
                raise RuntimeError("Failed to parse transcription output")
            
            if result['status'] == 'error':
                logger.error(f"Transcription failed: {result['error']}")
                logger.error(f"Traceback: {result.get('traceback', 'N/A')}")
                raise RuntimeError(f"Transcription failed: {result['error']}")
            
            logger.info(f"Detected language: {result['language']} (probability: {result['language_probability']:.2f})")
            logger.info(f"Transcription complete: {len(result['lyrics'])} segments")
            
            lyrics = [LyricSegment(**seg) for seg in result['lyrics']]
            
            try:
                cache_file.write_text(json.dumps(result['lyrics'], indent=2))
                logger.info(f"Cached lyrics: {cache_key}")
            except Exception as e:
                logger.error(f"Failed to cache lyrics: {e}", exc_info=True)
            
            return lyrics
            
        except asyncio.TimeoutError:
            logger.error("Transcription timed out after 5 minutes")
            raise RuntimeError("Transcription timed out. The audio file may be too long.")
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to transcribe audio: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached lyrics."""
        try:
            for cache_file in self._cache_dir.glob("*.json"):
                cache_file.unlink()
            logger.info("Lyrics cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
