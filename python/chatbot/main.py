import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from .huddle import create_room
from .open_ai import OpenBot, OpenBotOptions

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    if not room:
        raise Exception("Room not created")

    await room.connect()

    open_bot = OpenBot(
        OpenBotOptions(api_key=open_api_key, model="gpt-4o-realtime-preview")
    )

    try:
        await asyncio.Future()

    except Exception as e:
        logger.error(f"Error in main: {e}")
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    asyncio.run(main())
