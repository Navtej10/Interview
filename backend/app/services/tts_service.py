"""
Stub. Wire in the edge-tts pipeline from your earlier offline InterviewAI
build here. Keep the signature the same (text in, audio file path out) so
avatar_service.py and the routers don't need to change when you fill this in.
"""

import edge_tts
from typing import AsyncIterator

async def synthesize_speech(text: str, output_path: str) -> str:
    """
    Synthesizes speech and saves it to a file.
    """
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await communicate.save(output_path)
    return output_path

async def synthesize_speech_stream(text: str) -> AsyncIterator[bytes]:
    """
    Synthesizes speech and streams the binary audio chunks.
    Useful for starting lip-sync or playback before the full audio is generated.
    """
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]
