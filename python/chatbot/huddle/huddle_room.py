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
