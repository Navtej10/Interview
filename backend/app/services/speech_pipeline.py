import asyncio
import os
import tempfile
from typing import AsyncIterator

try:
    import edge_tts
    import os
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
    from faster_whisper import WhisperModel
    # base.en costs a bit more latency than tiny.en but is noticeably more
    # accurate on names/technical vocabulary — worth it for interview transcripts.
    model = WhisperModel("base.en", device="cpu", compute_type="int8")
except ImportError:
    edge_tts = None
    WhisperModel = None
    model = None

async def synthesize_speech(text: str, output_path: str) -> str:
    """
    Synthesizes speech using edge-tts and saves it to a file.
    """
    if edge_tts is None:
        raise RuntimeError("edge_tts is not initialized.")
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await communicate.save(output_path)
    return output_path

DEFAULT_TRANSCRIBE_KWARGS = dict(
    beam_size=5,
    language="en",
    vad_filter=True,
    # Note: This 500ms min_silence_duration is whisper's internal VAD, acting as a
    # secondary cleanup pass to filter out silence within the already-chunked audio.
    # It is NOT the turn-boundary signal (the client VAD event triggering END_OF_TURN
    # is the actual boundary signal).
    vad_parameters=dict(min_silence_duration_ms=500),
    condition_on_previous_text=False,
    no_speech_threshold=0.6,
)

def transcribe_speech(audio_path: str, initial_prompt: str | None = None) -> str:
    """
    Transcribes a full audio file using faster-whisper.
    """
    if model is None:
        raise RuntimeError("Whisper model is not initialized.")
    segments, _ = model.transcribe(
        audio_path, initial_prompt=initial_prompt, **DEFAULT_TRANSCRIBE_KWARGS
    )
    return " ".join([segment.text for segment in segments]).strip()

import re

async def synthesize_speech_stream(text: str) -> AsyncIterator[bytes]:
    """
    Synthesizes speech and streams the binary audio chunks.
    Splits the text into shorter sentence-level segments to improve interrupt
    latency by providing more frequent boundaries to break at.
    """
    if edge_tts is None:
        raise RuntimeError("edge_tts is not initialized.")

    # Split on sentence boundaries (punctuation followed by whitespace or end of string)
    segments = re.split(r'(?<=[.!?])\s+', text.strip())
    
    for segment in segments:
        if not segment:
            continue
        communicate = edge_tts.Communicate(segment, voice="en-US-GuyNeural")
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

import logging

logger = logging.getLogger(__name__)

# Minimum bytes for a valid turn to avoid false VAD triggers (breath/pops)
# 16kHz 16-bit mono WAV is ~32 bytes per ms. 250ms = 8000 bytes.
MIN_TURN_AUDIO_BYTES = 8000

async def transcribe_speech_stream(
    audio_chunks: AsyncIterator[bytes],
    initial_prompt: str | None = None,
) -> AsyncIterator[str]:
    """
    Consumes binary audio chunks (each chunk representing a complete recording
    for a single interview turn) and yields the transcribed text immediately.
    """
    async for chunk in audio_chunks:
        if not chunk:
            continue
            
        # Ignore extremely short audio chunks that are likely false VAD triggers
        if len(chunk) < MIN_TURN_AUDIO_BYTES:
            logger.info(f"Ignoring turn audio of {len(chunk)} bytes (under ~250ms minimum).")
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
                return model.transcribe(
                    tmp_path, initial_prompt=initial_prompt, **DEFAULT_TRANSCRIBE_KWARGS
                )
                
            segments, _ = await loop.run_in_executor(None, run_transcription)
            segments = list(segments)  # materialize once, so we can inspect confidence
            text = " ".join([segment.text for segment in segments]).strip()
            
            if text:
                avg_conf = sum(s.avg_logprob for s in segments) / len(segments)
                if avg_conf < -1.0:
                    logger.warning(f"Low-confidence transcription (avg_logprob={avg_conf:.2f}): {text!r}")
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

