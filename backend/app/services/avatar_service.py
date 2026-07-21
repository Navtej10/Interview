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

class AvatarRenderError(Exception):
    """Specific exception for LivePortrait rendering failures."""
    pass

async def render_avatar_video(audio_path: str, output_path: str, cues: BehaviorCues) -> str:
    """
    Renders a talking-head video using the LivePortrait pipeline.
    Takes an audio file and a reference face (from config), producing the video.
    Uses behavioral cues for expression control.
    """
    face_path = settings.avatar_reference_face
    
    # Example subprocess call to the offline LivePortrait pipeline
    cmd = [
        "python", "-m", "liveportrait.inference",
        "--audio", audio_path,
        "--face", face_path,
        "--output", output_path,
        "--expression", cues.expression
    ]
    
    logger.info(f"Starting avatar render: {' '.join(cmd)}")
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            logger.error(f"LivePortrait failed with code {process.returncode}: {error_msg}")
            raise AvatarRenderError(f"LivePortrait pipeline failed: {error_msg}")
            
        return output_path
        
    except Exception as e:
        if not isinstance(e, AvatarRenderError):
            logger.error(f"Failed to execute LivePortrait subprocess: {e}")
            raise AvatarRenderError(f"Subprocess execution failed: {str(e)}")
        raise

async def render_avatar_video_stream(audio_chunks: AsyncIterator[bytes], cues: BehaviorCues) -> AsyncIterator[bytes]:
    """
    Streams audio chunks into LivePortrait and yields video chunks in real-time.
    Useful for starting lip-sync or playback before the full audio is generated.
    """
    face_path = settings.avatar_reference_face
    
    cmd = [
        "python", "-m", "liveportrait.inference_stream",
        "--face", face_path,
        "--expression", cues.expression
    ]
    
    logger.info("Starting streaming avatar render")
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    except Exception as e:
        raise AvatarRenderError(f"Failed to start streaming subprocess: {str(e)}")
        
    async def write_audio():
        try:
            async for chunk in audio_chunks:
                if process.stdin:
                    process.stdin.write(chunk)
                    await process.stdin.drain()
        except Exception as e:
            logger.error(f"Error writing to LivePortrait stdin: {e}")
        finally:
            if process.stdin:
                process.stdin.close()

    writer_task = asyncio.create_task(write_audio())

    try:
        while True:
            # Read streaming video output (e.g. mpegts or raw frames) from stdout
            video_chunk = await process.stdout.read(8192)
            if not video_chunk:
                break
            yield video_chunk
            
        await process.wait()
        
        if process.returncode != 0:
            stderr = await process.stderr.read()
            raise AvatarRenderError(f"LivePortrait streaming failed: {stderr.decode().strip()}")
            
    except Exception as e:
        if not isinstance(e, AvatarRenderError):
            raise AvatarRenderError(f"Error during video streaming: {str(e)}")
        raise
    finally:
        if not writer_task.done():
            writer_task.cancel()
