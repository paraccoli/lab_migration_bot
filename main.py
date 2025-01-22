import sys
import os
import asyncio
import signal
import logging
import tracemalloc
from threading import Event, Thread

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from bot.discord_bot import start_discord_bot, send_to_discord
from config import (
    SLACK_BOT_TOKEN,
    SLACK_APP_TOKEN,
    SLACK_CHANNEL_ID_1,
    SLACK_CHANNEL_ID_2,
    SLACK_CHANNEL_ID_3,
    LOG_LEVEL
)

# トレースバック追跡を有効化
tracemalloc.start()

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

shutdown_event = Event()

CHANNEL_IDS = [SLACK_CHANNEL_ID_1, SLACK_CHANNEL_ID_2, SLACK_CHANNEL_ID_3]

class SlackBot:
    def __init__(self):
        self.slack_client = AsyncWebClient(token=SLACK_BOT_TOKEN)
        self.socket_mode_client = SocketModeClient(
            app_token=SLACK_APP_TOKEN,
            web_client=self.slack_client
        )
        self.monitored_users = set()
        self.running = True

    async def handle_slack_events(self, event):
        try:
            if event.get("type") == "message":
                channel = event.get("channel")
                user = event.get("user")
                
                if not user:
                    return

                if channel in CHANNEL_IDS and user not in self.monitored_users:
                    self.monitored_users.add(user)
                    logger.info(f"Added user {user} to monitored users.")

                if channel in CHANNEL_IDS and user in self.monitored_users:
                    channel_info = await self.slack_client.conversations_info(channel=channel)
                    user_info = await self.slack_client.users_info(user=user)
                    channel_name = channel_info["channel"]["name"]
                    user_name = user_info["user"]["real_name"]
                    message_text = event["text"]
                    logger.info(f"Processing message from {user_name} in {channel_name}")

                    # handle_slack_events メソッド内の send_to_discord の呼び出し部分
                    await send_to_discord(
                        message_text=message_text,
                        user_name=user_name,
                        channel_name=channel_name
                    )
        except Exception as e:
            logger.error(f"Error handling Slack event: {e}")
            logger.debug(f"Event data: {event}")

    async def event_handler(self, client, req):
        try:
            if req.type == "events_api":
                event = req.payload.get("event", {})
                await self.handle_slack_events(event)
            await client.send_socket_mode_response(
                SocketModeResponse(envelope_id=req.envelope_id)
            )
        except Exception as e:
            logger.error(f"Error in event handler: {e}")
            logger.debug(f"Request data: {req}")

    async def start(self):
        try:
            self.socket_mode_client.socket_mode_request_listeners.append(
                lambda c, r: asyncio.create_task(self.event_handler(c, r))
            )
            await self.socket_mode_client.connect()
            logger.info("Slack bot started successfully")
            
            while self.running:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in Slack bot: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        logger.info("Cleaning up Slack bot...")
        if self.socket_mode_client:
            await self.socket_mode_client.close()
        logger.info("Cleanup completed")

    def stop(self):
        self.running = False

def signal_handler(signum, frame):
    logger.info("シャットダウンシグナルを受信")
    shutdown_event.set()

async def main():
    try:
        bot = SlackBot()
        discord_task = asyncio.create_task(start_discord_bot())
        slack_task = asyncio.create_task(bot.start())
        
        await asyncio.gather(discord_task, slack_task)
    except Exception as e:
        logger.error(f"メインループでエラーが発生: {e}")
        raise

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("キーボード割り込みを受信")
        while True:
            response = input("強制終了しますか？ (Y/n): ").strip().lower()
            if response == 'y':
                logger.info("強制終了します...")
                sys.exit(0)
            elif response == 'n':
                logger.info("強制終了をキャンセルしました。")
                break
    except Exception as e:
        logger.error(f"致命的なエラー: {e}")
    finally:
        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            logger.debug("メモリトレースバック:")
            for stat in snapshot.statistics('lineno')[:3]:
                logger.debug(str(stat))