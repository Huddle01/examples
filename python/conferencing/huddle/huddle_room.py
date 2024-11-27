import json
import logging

from huddle01 import (
    AccessToken,
    AccessTokenData,
    HuddleClient,
    HuddleClientOptions,
    Role,
)
from huddle01.access_token import AccessTokenOptions
from huddle01.local_peer import LocalPeerEvents, Producer
from huddle01.room import Room

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# Create a Huddle room
async def create_room(project_id: str, room_id: str, api_key: str) -> Room:
    """
    Create a Room
    """
    try:
        options = HuddleClientOptions(autoConsume=True, volatileMessaging=False)

        metadata = {
            "displayName": "Artysi",
        }

        accessTokenOptions: AccessTokenOptions = AccessTokenOptions(
            metadata=json.dumps(metadata)
        )

        accessTokenData = AccessTokenData(
            api_key=api_key, room_id=room_id, role=Role.HOST, options=accessTokenOptions
        )

        accessToken = AccessToken(accessTokenData)

        token = await accessToken.to_jwt()

        client = HuddleClient(project_id, options)

        room = await client.create(room_id=room_id, token=token)

        @room.local_peer.on(LocalPeerEvents.ProduceSuccess)
        async def on_produce_success(producer: Producer):
            logger.info(f"Produce Success: {producer.id}")

        return room
    except Exception as e:
        logger.error(f"Error creating room: {e}")

        raise


# async def handle_new_consumer(consumer: Consumer):
#     track = consumer.track

#     logger.info("Handling New Consumer")

#     if track and track.readyState == "live":
#         logger.info(f"New Track {track.readyState}")

#         try:
#             while track.readyState != "ended":
#                 logger.info("Receiving new frame")
#                 frame = await track.recv()

#                 if frame:
#                     logger.info(f"Frame received: {frame}")
#         except Exception as e:
#             logger.error(f"Error receiving frame: {e}")
#         finally:
#             track.stop()
#             logger.info("Track ended and stopped.")


# async def produce_media(local_peer: LocalPeer, audio=True, video=True):
#     player = MediaPlayer("./assets/demo.mov", loop=True)

#     if audio:
#         audio_stream = player.audio or AudioStreamTrack()
#         audio_produce_options = ProduceOptions(track=audio_stream, label="audio")
#         await local_peer.produce(audio_produce_options)

#     if video:
#         video_stream = player.video or VideoStreamTrack()
#         video_produce_options = ProduceOptions(label="video", track=video_stream)
#         await local_peer.produce(video_produce_options)
