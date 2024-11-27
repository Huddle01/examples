import asyncio
import base64
import fractions
import logging
import threading

import numpy as np
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack
from av import AudioFrame
from av.audio.fifo import AudioFifo

logger = logging.getLogger(__name__)


class BotAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self):
        super().__init__()

        # Audio configuration
        self.sample_rate = 24000
        self.channels = 1
        self.sample_width = 2  # 2 bytes per sample (16 bits)

        self._start = None
        self._timestamp = 0

        self.AUDIO_PTIME = 0.020  # 20ms audio packetization
        self.frame_samples = int(self.AUDIO_PTIME * self.sample_rate)

        # Audio FIFO buffer
        self.audio_fifo = AudioFifo()
        self.fifo_lock = threading.Lock()

    def enqueue_audio(self, base64_audio: str):
        """Process and add audio data directly to the AudioFifo"""
        if self.readyState != "live":
            return

        try:
            audio_bytes = base64.b64decode(base64_audio)
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_array = audio_array.reshape(self.channels, -1)

            frame = AudioFrame.from_ndarray(
                audio_array,
                format="s16",
                layout="mono" if self.channels == 1 else "stereo",
            )
            frame.sample_rate = self.sample_rate
            frame.time_base = fractions.Fraction(1, self.sample_rate)

            with self.fifo_lock:
                self.audio_fifo.write(frame)

        except Exception as e:
            logger.error(f"Error in enqueue_audio: {e}", exc_info=True)

    def flush_audio(self):
        """Flush the audio FIFO buffer"""
        with self.fifo_lock:
            self.audio_fifo = AudioFifo()

    async def recv(self) -> AudioFrame:
        """Receive the next audio frame"""
        if self.readyState != "live":
            raise MediaStreamError

        if self._start is None:
            self._start = asyncio.get_event_loop().time()
            self._timestamp = 0

        samples = self.frame_samples
        self._timestamp += samples

        target_time = self._start + (self._timestamp / self.sample_rate)
        current_time = asyncio.get_event_loop().time()
        wait = target_time - current_time

        if wait > 0:
            await asyncio.sleep(wait)

        try:
            # Read frames from the FIFO buffer
            with self.fifo_lock:
                frame = self.audio_fifo.read(samples)

            if frame is None:
                # If no data is available, generate silence
                frame = AudioFrame(
                    format="s16",
                    layout="mono" if self.channels == 1 else "stereo",
                    samples=samples,
                )
                for p in frame.planes:
                    p.update(np.zeros(samples, dtype=np.int16).tobytes())

                frame.sample_rate = self.sample_rate
                frame.time_base = fractions.Fraction(1, self.sample_rate)
            else:
                # Update frame properties
                frame.sample_rate = self.sample_rate
                frame.time_base = fractions.Fraction(1, self.sample_rate)

            # Set frame PTS
            frame.pts = self._timestamp

            return frame

        except Exception as e:
            logger.error(f"Error in recv: {e}", exc_info=True)
            raise MediaStreamError("Error processing audio frame")

    def stop(self) -> None:
        """Stop the track"""
        if self.readyState == "live":
            super().stop()
