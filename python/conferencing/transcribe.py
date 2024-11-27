import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech as cloud_speech_types
from google.oauth2 import service_account
from pydantic import BaseModel

from huddle01.emitter import EnhancedEventEmitter

logger = logging.getLogger("transcribe")


class TranscriptionResult(BaseModel):
    """Structured container for transcription results."""

    text: str
    is_final: bool
    confidence: float
    alternatives: list


class AudioProcessor:
    MAX_CHUNK_SIZE = 25600
    PREFERRED_CHUNK_SIZE = 24576

    def __init__(self):
        self.buffer = bytearray()

    def add_audio(self, audio_data: bytes) -> list[bytes]:
        """
        Adds audio data to buffer and returns complete chunks.

        Args:
            audio_data: Raw audio bytes to process

        Returns:
            List of properly sized chunks ready for transmission
        """
        self.buffer.extend(audio_data)

        chunks = []

        while len(self.buffer) >= self.PREFERRED_CHUNK_SIZE:
            chunk = bytes(self.buffer[: self.PREFERRED_CHUNK_SIZE])
            chunks.append(chunk)
            self.buffer = self.buffer[self.PREFERRED_CHUNK_SIZE :]

        return chunks

    def get_remaining(self) -> Optional[bytes]:
        """Returns any remaining audio data in the buffer."""
        if self.buffer:
            return bytes(self.buffer)
        return None


class Transcribe(EnhancedEventEmitter):
    def __init__(self):
        super(Transcribe, self).__init__()
        self.PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")

        if not self.PROJECT_ID:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set.")

        self.client = SpeechClient(
            credentials=service_account.Credentials.from_service_account_file(
                "key.json"
            )
        )

        self.audio_processor = AudioProcessor()

        self.executor = ThreadPoolExecutor(max_workers=5)

    def _create_streaming_config(self) -> cloud_speech_types.StreamingRecognizeRequest:
        """Creates the streaming configuration for the Speech API."""
        explicit_decoding = cloud_speech_types.ExplicitDecodingConfig(
            encoding=cloud_speech_types.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            audio_channel_count=1,
        )

        recognition_config = cloud_speech_types.RecognitionConfig(
            explicit_decoding_config=explicit_decoding,
            model="long",
            language_codes=["en-US"],
        )

        streaming_config = cloud_speech_types.StreamingRecognitionConfig(
            config=recognition_config,
        )

        return cloud_speech_types.StreamingRecognizeRequest(
            recognizer=f"projects/{self.PROJECT_ID}/locations/global/recognizers/_",
            streaming_config=streaming_config,
        )

    def _transcribe_response(self, streaming_request, audio_chunk: list[bytes]):
        """Handles the transcription response."""

        audio_requests = (
            cloud_speech_types.StreamingRecognizeRequest(audio=audio)
            for audio in audio_chunk
        )

        def request_generator():
            yield streaming_request
            yield from audio_requests

        responses_iterator = self.client.streaming_recognize(
            requests=request_generator()
        )

        responses = []
        for response in responses_iterator:
            responses.append(response)

            for result in response.results:
                if result.alternatives:
                    t = TranscriptionResult(
                        text=result.alternatives[0].transcript,
                        is_final=result.is_final,
                        confidence=result.alternatives[0].confidence,
                        alternatives=[
                            {"transcript": alt.transcript, "confidence": alt.confidence}
                            for alt in result.alternatives[1:]
                        ],
                    )

                    self.emit("transcription", t)

    def send_audio_byte(self, audio: bytes):
        try:
            streaming_request = self._create_streaming_config()

            audio_chunk = self.audio_processor.add_audio(audio)

            if len(audio_chunk) == 0:
                return

            self.executor.submit(
                self._transcribe_response, streaming_request, audio_chunk
            )

        except Exception as e:
            print(f"Error sending audio chunk: {str(e)}")
            raise
