import base64
import os
from queue import Queue

import google.cloud.speech_v2 as speech
from dotenv import load_dotenv
from google.cloud.speech_v2.services.speech.client import Iterator

load_dotenv()


PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")


class TranscriptionBot:
    def __init__(self):
        self.client = speech.SpeechClient.from_service_account_json("key.json")
        self.project_id = PROJECT_ID
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set.")

        self.audio_requests = Queue()

        # Configure the recognition settings
        self.config = speech.RecognitionConfig(
            explicit_decoding_config=speech.ExplicitDecodingConfig(
                encoding=speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=24000,
                audio_channel_count=1,
            ),
            language_codes=["en-US"],  # Set the language of the transcription
            model="long",
        )

        # Initialize recognizer request
        self.config_request = speech.StreamingRecognizeRequest(
            recognizer=f"projects/{self.project_id}/locations/global/recognizers/_",
            streaming_config=speech.StreamingRecognitionConfig(config=self.config),
        )

    async def send_encoded_audio(self, base64_audio_data: str):
        """
        Decodes base64 audio data and sends it as a chunk to the Google Cloud
        Speech-to-Text API for streaming transcription.
        """
        # Decode the base64 audio data
        audio_bytes = base64.b64decode(base64_audio_data)

        # Create an audio request chunk
        audio_request = speech.StreamingRecognizeRequest(audio=audio_bytes)

        # Add the request to the queue
        self.audio_requests.put(audio_request)

    def yield_audio_request(self):
        audio_request = self.audio_requests.get()

        yield audio_request

    async def listen_for_transcription(self):
        """
        Continuously listens to the transcription responses from Google Cloud
        Speech-to-Text API and prints the results.
        """
        while True:
            # Generator to yield requests for the streaming API
            def request_generator() -> Iterator[speech.StreamingRecognizeRequest]:
                # Send the initial config request
                yield self.config_request
                yield from self.yield_audio_request()

            # Start streaming recognition
            responses_iterator = self.client.streaming_recognize(
                requests=request_generator()
            )

            for response in responses_iterator:
                for result in response.results:
                    print(f"Transcript: {result.alternatives[0].transcript}")
