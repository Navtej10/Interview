import asyncio
import os
import tempfile
from typing import AsyncIterator

try:
    import edge_tts
    import os
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
    from faster_whisper import WhisperModel
    # Uses tiny.en for acceptable latency on short utterances
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
except ImportError:
    edge_tts = None
    WhisperModel = None
    model = None

async def synthesize_speech(text: str, output_path: str) -> str:
    """
    Synthesizes speech using edge-tts and saves it to a file.
    """
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await communicate.save(output_path)
    return output_path

def transcribe_speech(audio_path: str) -> str:
    """
    Transcribes a full audio file using faster-whisper.
    """
    segments, _ = model.transcribe(audio_path, beam_size=1)
    return " ".join([segment.text for segment in segments]).strip()

async def synthesize_speech_stream(text: str) -> AsyncIterator[bytes]:
    """
    Synthesizes speech and streams the binary audio chunks.
    """
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]

import logging

logger = logging.getLogger(__name__)

async def transcribe_speech_stream(audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[str]:
    """
    Consumes binary audio chunks (each chunk representing a complete recording
    for a single interview turn) and yields the transcribed text immediately.
    """
    async for chunk in audio_chunks:
        if not chunk:
            continue
            
        # Safely create a temporary file for the received audio chunk
        try:
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(chunk)
                tmp_path = tmp.name
        except Exception as e:
            logger.error(f"Failed to write audio chunk to temporary file: {e}", exc_info=True)
            continue
            
        try:
            # Use asyncio to prevent the synchronous transcription from blocking the event loop
            loop = asyncio.get_running_loop()
            
            def run_transcription():
                if model is None:
                    raise RuntimeError("Whisper model is not initialized.")
                return model.transcribe(tmp_path, beam_size=1)
                
            segments, _ = await loop.run_in_executor(None, run_transcription)
            text = " ".join([segment.text for segment in segments]).strip()
            
            if text:
                yield text
            else:
                logger.warning("Transcription completed but returned empty text.")
        except Exception as e:
            # Ensure transcription failures never crash the interview
            logger.error(f"Transcription failed for the current turn: {e}", exc_info=True)
        finally:
            # Safely clean up the temporary file, ensuring no leftover files
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception as e:
                logger.error(f"Failed to delete temporary file {tmp_path}: {e}", exc_info=True)
