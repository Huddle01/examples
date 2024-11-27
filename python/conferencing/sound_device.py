import asyncio
import base64
import logging
from typing import Callable

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


async def send_input_device_stream(future: asyncio.Future, audio_callback: Callable):
    def callback(
        indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags
    ) -> None:
        try:
            pcm_base64 = base64.b64encode(indata).decode("utf-8")
            asyncio.run(audio_callback(pcm_base64))

        except Exception as e:
            logger.error(f"Error sending audio chunk: {e}")

    try:
        with sd.InputStream(
            samplerate=24000,  # Match the expected sample rate
            channels=1,  # Mono audio
            dtype=np.int16,
            callback=callback,
            blocksize=4096,  # Smaller blocksize for more frequent updates
        ):
            logger.info("Started audio input stream")

            await future

    except Exception as e:
        logger.error(f"Error in audio stream: {e}")
        raise
    except KeyboardInterrupt:
        logger.info("Stopping audio stream due to keyboard interrupt")
        raise
