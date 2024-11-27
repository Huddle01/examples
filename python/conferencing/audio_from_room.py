import asyncio
import logging
from typing import Callable

from av import AudioFrame, AudioResampler
from av.audio.fifo import AudioFifo

logger = logging.getLogger(__name__)

audio_fifo = AudioFifo()

resampler = AudioResampler(
    format="s16",
    layout="mono",
    rate=16000,
)


def push_room_audio_frame(frame: AudioFrame):
    """Asynchronously write frames to the AudioFifo buffer."""
    resampled_frames = resampler.resample(frame)

    for resampled_frame in resampled_frames:
        audio_fifo.write(resampled_frame)


# The audio_callback function is called with the base64-encoded audio data
# The block size for each audio chunk has to be 4096
async def push_to_callback(audio_callback: Callable):
    """Asynchronously read frames from AudioFifo and send base64-encoded PCM data."""

    while True:
        try:
            frame = audio_fifo.read()

            if frame is None:
                await asyncio.sleep(0.01)
                continue

            pcm_data = frame.to_ndarray()

            pcm_bytes = pcm_data.tobytes()

            await audio_callback(pcm_bytes)
        except Exception as e:
            logger.error(f"Error sending audio chunk: {e}", exc_info=True)
            break  # Exit the loop on error
