import os
import asyncio
import logging
import subprocess
import time
from typing import Optional

from app.config import settings
from app.models.schemas import BehaviorCues

logger = logging.getLogger(__name__)

class AvatarError(Exception):
    """Specific exception for Avatar rendering failures."""
    pass

class AvatarService:
    """
    Service responsible for keeping the Hallo2 avatar model in memory
    and rendering talking-head videos efficiently.
    """
    _instance: Optional['AvatarService'] = None

    def __init__(self):
        """
        Initializes the Hallo2 model in GPU memory and loads the reference face.
        This operation happens once on startup.
        """
        self.reference_face_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "assets", 
            "default_face.jpg"
        )
        
        logger.info(f"Loading AvatarService with reference face: {self.reference_face_path}")
        
        if not os.path.exists(self.reference_face_path):
            logger.warning(f"Reference face not found at {self.reference_face_path}")
            
        start_time = time.time()
        
        # ---------------------------------------------------------
        # TODO: Initialize Hallo2 model here.
        # Example:
        # import torch
        # from hallo2.inference import Hallo2Model
        # self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        # self.model = Hallo2Model.from_pretrained('path/to/weights').to(self.device)
        # self.model.eval()
        # ---------------------------------------------------------
        
        self.model = "Hallo2_Model_Loaded_Mock" # Placeholder for actual loaded weights
        
        logger.info(f"AvatarService initialized in {time.time() - start_time:.2f} seconds.")

    @classmethod
    def get_instance(cls) -> 'AvatarService':
        """Singleton access for the AvatarService."""
        if cls._instance is None:
            cls._instance = AvatarService()
        return cls._instance

    async def render_avatar(self, audio_path: str, cues: BehaviorCues, output_path: str) -> str:
        """
        Renders a talking-head video using the in-memory Hallo2 model.
        Takes an audio file and produces the video at output_path.
        If Hallo2 fails, gracefully falls back to FFmpeg static-image rendering.
        """
        start_time = time.time()
        logger.info(f"Starting avatar render for audio: {audio_path} with cues: {cues.expression}")
        
        try:
            # ---------------------------------------------------------
            # TODO: Run actual Hallo2 inference using self.model
            # Example:
            # def run_hallo2_inference():
            #     with torch.no_grad():
            #         # Preprocess audio and image
            #         audio_tensor = load_audio(audio_path).to(self.device)
            #         face_tensor = load_image(self.reference_face_path).to(self.device)
            #         
            #         # Convert abstract cues to specific parameters if supported
            #         expression_factor = map_expression(cues.expression)
            #         
            #         # Inference
            #         video_frames = self.model.generate(audio_tensor, face_tensor, expression_factor)
            #         
            #         # Save output
            #         save_video(video_frames, output_path)
            #
            # await asyncio.to_thread(run_hallo2_inference)
            # ---------------------------------------------------------
            
            # Simulated rendering delay for mock implementation
            await asyncio.sleep(1.0) 
            
            # For the mock, we just generate a dummy file to simulate success
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                # Fallback to creating a static video to represent the mock output
                await self._fallback_render(audio_path, output_path)
                
            logger.info(f"Avatar render completed in {time.time() - start_time:.2f} seconds. Output: {output_path}")
            return output_path
            
        except Exception as e:
            logger.warning(f"Hallo2 rendering failed: {e}. Falling back to FFmpeg static image.")
            return await self._fallback_render(audio_path, output_path)

    async def _fallback_render(self, audio_path: str, output_path: str) -> str:
        """
        Fallback renderer using FFmpeg to create a static video from the reference image.
        """
        is_webm = output_path.lower().endswith('.webm')
        vcodec = "libvpx-vp9" if is_webm else "libx264"
        acodec = "libopus" if is_webm else "aac"
        
        ffmpeg_cmd = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-framerate", "25",
            "-i", self.reference_face_path,
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
                raise AvatarError(f"Both Hallo2 and FFmpeg failed. FFmpeg error: {error_msg}")
                
            return output_path
        except Exception as fallback_e:
            if not isinstance(fallback_e, AvatarError):
                logger.error(f"Failed to execute FFmpeg fallback subprocess: {fallback_e}")
                raise AvatarError(f"FFmpeg subprocess execution failed: {str(fallback_e)}")
            raise

# Global accessor for convenience, can be used by orchestrator
avatar_service = AvatarService.get_instance()
