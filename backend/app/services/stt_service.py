"""
Speech-to-Text service.
Currently a functional stub that yields dummy text, since no specific STT 
provider (e.g. Deepgram, Whisper) has been selected yet.
"""

import asyncio
from typing import AsyncIterator

async def transcribe_stream(audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[str]:
    """
    Consumes binary audio chunks and yields partial/final transcription strings.
    This is a stub implementation. In a real system (like Deepgram), this would 
    open a WebSocket to the STT provider, forward the chunks, and yield the text
    responses.
    """
    total_bytes = 0
    async for chunk in audio_chunks:
        total_bytes += len(chunk)
        # Simulate some processing delay and yield partials if we wanted to.
        # For the stub, we will just yield a final dummy transcript if we receive enough data.
        # Alternatively, we could just yield the string "Candidate audio received."
        # This allows the interruption logic to trigger when this yields.
        
        # Real-time STT systems return partials and finals.
        # Here we just yield a simulated word every few chunks to trigger interruption.
        if total_bytes > 5000:  # Arbitrary threshold to simulate "speech detected"
            yield "Simulated candidate speech text."
            total_bytes = 0
