import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())
import tempfile
from app.services.speech_pipeline import synthesize_speech_stream
from app.services.avatar_service import avatar_service
from app.models.schemas import BehaviorCues

async def main():
    text = "Hello world, this is a test"
    audio_stream = synthesize_speech_stream(text)
    cues = BehaviorCues(expression="neutral", blink_rate=1.5, gaze_pattern="normal")
    
    audio_temp_fd, audio_temp = tempfile.mkstemp(suffix=".mp3")
    os.close(audio_temp_fd)
    
    print("Synthesizing speech...")
    with open(audio_temp, "wb") as f:
        async for chunk in audio_stream:
            f.write(chunk)
            
    print("Rendering avatar...")
    video_temp_fd, video_temp = tempfile.mkstemp(suffix=".mp4")
    os.close(video_temp_fd)
    
    await avatar_service.render_avatar(audio_temp, cues, video_temp)
    print("Done! Video at:", video_temp)

asyncio.run(main())
