"""
Media Analyzer Tool — inspects audio, video, and image files for acoustic, structural, and visual metadata with workspace path validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kryntis.chunking.audio_chunker import AudioChunker
from kryntis.chunking.image_chunker import ImageChunker
from kryntis.chunking.video_chunker import VideoChunker
from kryntis.tools.file_system import _resolve_safe_workspace_path
from kryntis.tools.tool_registry import ToolDefinition, ToolParameter


def analyze_media_file(path: str) -> dict[str, Any]:
    """
    Analyze an audio, video, or image file and return its properties.

    Args:
        path: Path to the media file on disk.

    Returns:
        dict with metadata, dimensions/duration, format, and chunks.
    """
    try:
        p = _resolve_safe_workspace_path(path)
    except PermissionError as pe:
        return {"error": str(pe)}
    except Exception as e:
        return {"error": f"Invalid media path: {e}"}

    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Path is not a file: {path}"}

    file_size = p.stat().st_size
    ext = p.suffix.lower()

    if ext in AudioChunker.SUPPORTED_EXTENSIONS:
        chunker = AudioChunker()
        chunks = list(chunker.chunk_file(p, source_id=p.name))
        return {
            "media_type": "audio",
            "file_name": p.name,
            "size_kb": file_size / 1024,
            "chunks_count": len(chunks),
            "summary": chunks[0].text if chunks else "",
        }
    elif ext in VideoChunker.SUPPORTED_EXTENSIONS:
        chunker = VideoChunker()
        chunks = list(chunker.chunk_file(p, source_id=p.name))
        return {
            "media_type": "video",
            "file_name": p.name,
            "size_kb": file_size / 1024,
            "chunks_count": len(chunks),
            "summary": chunks[0].text if chunks else "",
        }
    elif ext in ImageChunker.SUPPORTED_EXTENSIONS:
        chunker = ImageChunker()
        chunks = list(chunker.chunk_file(p, source_id=p.name))
        return {
            "media_type": "image",
            "file_name": p.name,
            "size_kb": file_size / 1024,
            "chunks_count": len(chunks),
            "summary": chunks[0].text if chunks else "",
        }
    else:
        return {
            "error": f"Unsupported media extension '{ext}'. Supported: audio {AudioChunker.SUPPORTED_EXTENSIONS}, video {VideoChunker.SUPPORTED_EXTENSIONS}, image {ImageChunker.SUPPORTED_EXTENSIONS}"
        }


TOOL_MEDIA_ANALYZER = ToolDefinition(
    name="analyze_media",
    description="Analyzes audio, video, or image files (<10 MB) and extracts duration, acoustic profile, resolution, and structural metadata.",
    parameters=[
        ToolParameter(
            name="path",
            type="string",
            description="Path to the audio, video, or image file to analyze.",
            required=True,
        )
    ],
    handler=analyze_media_file,
    category="multimodal",
)
