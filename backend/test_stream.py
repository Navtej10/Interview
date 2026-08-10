import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())
from app.services.speech_pipeline import synthesize_speech_stream

async def main():
    chunks = []
    async for c in synthesize_speech_stream('hello'):
        chunks.append(c)
    print('Got', len(chunks), 'chunks')

asyncio.run(main())
