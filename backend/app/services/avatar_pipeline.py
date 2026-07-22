"""
Stub. Wire in the LivePortrait pipeline from your earlier offline InterviewAI
build here — takes the audio from tts_service and a reference face, produces
the talking-head video. Same idea: keep the signature stable so the router
doesn't care about the implementation.
"""

import asyncio
from typing import AsyncIterator
from app.config import settings
from app.models.schemas import BehaviorCues
import logging

logger = logging.getLogger(__name__)

class LivePortraitError(Exception):
    """Specific exception for LivePortrait rendering failures."""
    pass

import tempfile
import os
import subprocess

async def render_avatar_video(audio_path: str, cues: BehaviorCues, output_path: str) -> str:
    """
    Renders a talking-head video using the LivePortrait pipeline.
    Takes an audio file and a reference face (from config), producing the video.
    If LivePortrait fails, gracefully falls back to FFmpeg static-image rendering.
    """
    face_path = settings.liveportrait_reference_face
    
    cmd = [
        "python", "-m", "liveportrait.inference",
        "--audio", audio_path,
        "--face", face_path,
        "--output", output_path,
        "--expression", cues.expression
    ]
    
    logger.info(f"Starting avatar render with LivePortrait: {' '.join(cmd)}")
    try:
        def run_liveportrait():
            return subprocess.run(cmd, capture_output=True)
            
        process = await asyncio.to_thread(run_liveportrait)
        
        if process.returncode != 0:
            error_msg = process.stderr.decode().strip() or process.stdout.decode().strip()
            logger.error(f"LivePortrait failed with code {process.returncode}: {error_msg}")
            raise LivePortraitError(f"LivePortrait pipeline failed: {error_msg}")
            
        return output_path
            
    except Exception as e:
        logger.warning(f"LivePortrait rendering failed: {e}. Falling back to FFmpeg static image.")
        
        # Determine codecs based on output extension (defaulting to mp4 compatible)
        is_webm = output_path.lower().endswith('.webm')
        vcodec = "libvpx-vp9" if is_webm else "libx264"
        acodec = "libopus" if is_webm else "aac"
        
        ffmpeg_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-framerate", "25",
            "-i", face_path,
            "-i", audio_path,
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v", vcodec,
            "-c:a", acodec,
            "-pix_fmt", "yuv420p",
            "-shortest", output_path
        ]
        
        logger.info(f"Starting fallback FFmpeg render: {' '.join(ffmpeg_cmd)}")
        try:
            def run_ffmpeg():
                return subprocess.run(ffmpeg_cmd, capture_output=True)
                
            ffmpeg_process = await asyncio.to_thread(run_ffmpeg)
            
            if ffmpeg_process.returncode != 0:
                error_msg = ffmpeg_process.stderr.decode().strip() or ffmpeg_process.stdout.decode().strip()
                logger.error(f"FFmpeg fallback failed with code {ffmpeg_process.returncode}: {error_msg}")
                raise LivePortraitError(f"Both LivePortrait and FFmpeg failed. FFmpeg error: {error_msg}")
                
            return output_path
        except Exception as fallback_e:
            if not isinstance(fallback_e, LivePortraitError):
                logger.error(f"Failed to execute FFmpeg fallback subprocess: {fallback_e}")
                raise LivePortraitError(f"FFmpeg subprocess execution failed: {str(fallback_e)}")
            raise

async def render_avatar_video_stream(audio_chunks: AsyncIterator[bytes], cues: BehaviorCues) -> AsyncIterator[bytes]:
    """
    Consumes all audio chunks to form a complete audio file, renders a complete
    turn-based video using render_avatar_video, and then yields the completed video file in chunks.
    Replaces the broken streaming implementation with a robust turn-based approach.
    """
    audio_temp = None
    video_temp = None
    
    try:
        # 1. Create a temp file for incoming TTS audio
        audio_temp_fd, audio_temp = tempfile.mkstemp(suffix=".mp3")
        os.close(audio_temp_fd)
        
        # 2. Accumulate all audio chunks
        with open(audio_temp, "wb") as f:
            async for chunk in audio_chunks:
                f.write(chunk)
                
        # 3. Create temp file for output video
        video_temp_fd, video_temp = tempfile.mkstemp(suffix=".mp4")
        os.close(video_temp_fd)
        
        # 4. Render the full video for this turn (with built-in FFmpeg fallback)
        await render_avatar_video(audio_temp, cues, video_temp)
        
        # 5. Yield the generated video back as chunks
        with open(video_temp, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
                
    except Exception as e:
        logger.error(f"Failed during turn-based avatar rendering: {e}", exc_info=True)
        # Ensure we never silently fail
        raise LivePortraitError(f"Avatar rendering pipeline failed: {e}")
        
    finally:
        # 6. Clean up temporary files safely
        for tmp_file in [audio_temp, video_temp]:
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.unlink(tmp_file)
                except Exception as cleanup_err:
                    logger.error(f"Failed to clean up temp file {tmp_file}: {cleanup_err}", exc_info=True)
