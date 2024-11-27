import asyncio
import json
import logging
import os

from dotenv import load_dotenv

from example.conferencing.audio_from_room import (
    push_room_audio_frame,
    push_to_callback,
)
from huddle01.handlers.local_peer_handler import ProduceOptions

from .huddle import Consumer, LocalPeerEvents, create_room
from .open_ai import OpenBot, OpenBotOptions
from .transcribe import Transcribe, TranscriptionResult

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_peer_audio(consumer: Consumer):
    try:
        track = consumer.track

        if track is None:
            raise ValueError("Track is None")

        if track.kind != "audio":
            raise ValueError("This handler is only for audio tracks.")

        while track.readyState != "ended":
            try:
                frame = await track.recv()
                frame.pts = None

                if frame is None:
                    continue

                push_room_audio_frame(frame)
            except Exception as e:
                logger.error(f"Error processing frame: {e}")

    except Exception as e:
        logger.error(f"Error processing frame: {e}")


async def main():
    open_api_key = os.getenv("OPENAI_API_KEY")
    project_id = os.getenv("PROJECT_ID")
    room_id = os.getenv("ROOM_ID")
    api_key = os.getenv("API_KEY")

    if not open_api_key or not api_key or not project_id or not room_id:
        raise Exception("Required ENVs not found")

    room = await create_room(
        api_key=api_key,
        project_id=project_id,
        room_id=room_id,
    )

    @room.local_peer.on(LocalPeerEvents.NewConsumer)
    async def on_produce_success(consumer: Consumer):
        logger.info(f"Consume Success: {Consumer.id}")

        if consumer.kind == "audio":
            asyncio.create_task(
                handle_peer_audio(consumer=consumer),
                name=f"handle_audio_chunk-{consumer.id}",
            )

    if not room:
        raise Exception("Failed to create room")

    await room.connect()

    openBot = OpenBot(
        OpenBotOptions(
            api_key=open_api_key,
            model="gpt-4o-realtime-preview",
        )
    )

    transcribe_bot = Transcribe()

    async def audio_callback(encoded_data: bytes):
        transcribe_bot.send_audio_byte(encoded_data)
        await openBot.send_audio_chunks(encoded_data)

    asyncio.create_task(
        push_to_callback(audio_callback=audio_callback),
        name="handle_callback",
    )

    await openBot.connect()

    logger.info("Connected to OpenAI")

    await room.local_peer.produce(
        options=ProduceOptions(track=openBot.audio_track, label="audio")
    )

    loop = asyncio.get_running_loop()

    @transcribe_bot.on("transcription")
    def on_transcription(transcription: TranscriptionResult):
        logger.info(f"Transcription: {transcription.text}")
        json_payload = json.dumps({"message": transcription.text, "name": "Ai Bot"})
        if transcription.is_final:
            asyncio.run_coroutine_threadsafe(
                room.local_peer.send_volatile_data(
                    label="volatile-message",
                    payload=json_payload,
                ),
                loop,
            )

    try:
        await asyncio.Future()
    except Exception as e:
        logger.error(f"Error: {e}")

    except KeyboardInterrupt:
        logger.info("Stopping audio stream.")
        # audio_play_back_future.set_result(True)


if __name__ == "__main__":
    asyncio.run(main())
