import logging
import asyncio
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.errors import SlackApiError
from utils.emoji_mapper import EmojiMapper
import discord
import io
import aiohttp
from config import (
    SLACK_BOT_TOKEN,
    SLACK_APP_TOKEN,
    SLACK_CHANNEL_ID_1,
    SLACK_CHANNEL_ID_2,
    SLACK_CHANNEL_ID_3,
    NOTIFICATION_CHANNEL_ID,
    NOTIFICATION_CHANNEL_ID2,
    MAX_FILE_SIZE,
    ALLOWED_FILE_TYPES
)
from bot.discord_bot import send_to_discord, bot
from datetime import datetime

# グローバル変数
slack_client = AsyncWebClient(token=SLACK_BOT_TOKEN)
socket_mode_client = SocketModeClient(app_token=SLACK_APP_TOKEN, web_client=slack_client)

# メッセージキャッシュ
message_cache = {}

# チャンネルID
CHANNEL_IDS = [SLACK_CHANNEL_ID_1, SLACK_CHANNEL_ID_2, SLACK_CHANNEL_ID_3]

# 監視するユーザーリスト
monitored_users = set()

def process_message(message, user, channel, platform):
    # フォーマットを "[チャンネル名] ユーザー名: 投稿内容" に変更
    return f"[{channel}] {user}: {message}"

# リアクション処理の修正
async def handle_reaction_event(event, action="add"):
    try:
        channel = event["item"]["channel"]
        ts = event["item"]["ts"]
        emoji = f":{event['reaction']}:"        
        if channel == SLACK_CHANNEL_ID_1:
            discord_emoji = EmojiMapper.slack_to_discord(emoji)
            if discord_emoji:
                discord_channel = bot.get_channel(NOTIFICATION_CHANNEL_ID2)
                if discord_channel:
                    async for message in discord_channel.history(limit=100):
                        if str(message.id) in message_cache:
                            if message_cache[str(message.id)]["slack_ts"] == ts:
                                if action == "add":
                                    await message.add_reaction(discord_emoji)
                                else:
                                    await message.remove_reaction(discord_emoji, bot.user)
                                logging.info(f"Reaction {'added to' if action == 'add' else 'removed from'} Discord: {emoji}")
                                break
    except Exception as e:
        logging.error(f"Error handling reaction {action}: {e}")

async def handle_slack_events(event):
    try:
        if event.get("type") == "message":
            # ファイル添付の確認
            files = event.get("files", [])
            if files:
                channel = event["channel"]
                user = event["user"]
                # ユーザー情報とチャンネル情報を取得
                user_info = await slack_client.users_info(user=user)
                channel_info = await slack_client.conversations_info(channel=channel)
                user_name = user_info["user"]["real_name"]
                channel_name = channel_info["channel"]["name"]
                for file in files:
                    try:
                        # ファイルサイズと種類のチェック
                        file_size = file.get("size", 0)
                        file_type = file.get("filetype", "").lower()
                        if file_size > MAX_FILE_SIZE:
                            logging.warning(f"ファイルサイズが大きすぎます: {file_size} bytes")
                            continue
                        if file_type not in ALLOWED_FILE_TYPES:
                            logging.warning(f"未対応のファイル形式です: {file_type}")
                            continue
                        # ファイルURLと認証情報を取得
                        file_url = file["url_private"]
                        headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
                        # ファイルをダウンロード
                        async with aiohttp.ClientSession(headers=headers) as session:
                            async with session.get(file_url) as response:
                                if response.status == 200:
                                    file_content = await response.read()
                                    # Discordのチャンネルを取得
                                    discord_channel = bot.get_channel(NOTIFICATION_CHANNEL_ID2)
                                    if discord_channel:
                                        # ファイル名を取得
                                        filename = file["name"]
                                        # Discordに送信
                                        file_obj = discord.File(io.BytesIO(file_content), filename=filename)
                                        embed = discord.Embed(
                                            title="📎 Slackからのファイル共有",
                                            description=f"チャンネル: #{channel_name}\n"
                                                      f"ファイル名: {filename}\n"
                                                      f"サイズ: {file_size / 1024 / 1024:.1f}MB",
                                            color=discord.Color.blue()
                                        )
                                        embed.set_author(name=user_name)
                                        await discord_channel.send(embed=embed, file=file_obj)
                                        logging.info(f"ファイル転送成功: {filename}")
                    except Exception as e:
                        logging.error(f"ファイル転送エラー: {e}")

            # 既存のメッセージ処理を続行
            if "text" in event and "user" in event:
                channel = event["channel"]
                user = event["user"]
                text = event["text"]
                # Botのユーザー情報を取得
                auth_response = await slack_client.auth_test()
                bot_user_id = auth_response["user_id"]
                
                # 以下の条件のいずれかに該当する場合はスキップ
                if any([
                    user == bot_user_id,  # Botからのメッセージ
                    "bot_id" in event,    # Bot投稿
                    event.get("subtype") == "bot_message",  # Botメッセージ
                    not text.strip(),     # 空のメッセージ
                ]):
                    logging.info("Botまたは空のメッセージなのでスキップします")
                    return
                
                # 通常のメッセージ処理
                if channel in CHANNEL_IDS:
                    channel_info = await slack_client.conversations_info(channel=channel)
                    user_info = await slack_client.users_info(user=user)
                    channel_name = channel_info["channel"]["name"]
                    user_name = user_info["user"]["real_name"]
                    
                    await send_to_discord(text, user_name, channel_name)
                
        # リアクションイベントの処理
        elif event.get("type") == "reaction_added":
            await handle_reaction_event(event, "add")
        elif event.get("type") == "reaction_removed":
            await handle_reaction_event(event, "remove")

    except Exception as e:
        logging.error(f"Error handling Slack event: {e}")
        logging.debug(f"Event data: {event}")

async def handle_slash_command(client: SocketModeClient, request: SocketModeRequest):
    if request.type == "slash_commands" and request.payload["command"] == "/add_user":
        user_id = request.payload["user_id"]
        monitored_users.add(user_id)
        response = SocketModeResponse(envelope_id=request.envelope_id)
        await client.send_socket_mode_response(response)
        # メッセージ送信をコメントアウトまたは削除
        # await slack_client.chat_postMessage(channel=request.payload["channel_id"], text=f"User <@{user_id}> is now being monitored.")
        logging.info(f"Added user {user_id} to monitored users.")

async def event_handler(client: SocketModeClient, req: SocketModeRequest):
    logging.info(f"Received SocketModeRequest: {req}")
    if req.type == "events_api":
        event = req.payload.get("event", {})
        await handle_slack_events(event)
    await client.send_socket_mode_response(
        SocketModeResponse(envelope_id=req.envelope_id)
    )

def start_slack_bot():
    """
    SlackのSocket Modeを起動してリアルタイムにイベントを受信
    """
    # スレッド内でイベントループを新規作成して設定
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    socket_mode_client.socket_mode_request_listeners.append(
        lambda client, req: asyncio.run_coroutine_threadsafe(event_handler(client, req), loop)
    )
    socket_mode_client.connect()
    loop.run_forever()

if __name__ == "__main__":
    asyncio.run(start_slack_bot())
    logging.info("Slack bot is running...")