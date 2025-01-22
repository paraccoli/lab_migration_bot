import discord
from discord.ext import commands
from discord import app_commands
from utils.logger import log_event
from utils.formatter import format_message
from utils.embed_utils import create_error_embed, create_notification_embed
from config import DISCORD_BOT_TOKEN, SLACK_BOT_TOKEN, NOTIFICATION_CHANNEL_ID, NOTIFICATION_CHANNEL_ID2, SLACK_CHANNEL_ID_1, SLACK_CHANNEL_ID_4, DISCORD_NEWS_CHANNEL_ID, DISCORD_ROLE_ID, MAX_FILE_SIZE, ALLOWED_FILE_TYPES, DISCORD_ARXIV_CHANNEL_ID, DISCORD_LOG_CHANNEL_ID
import logging
from slack_sdk.web.async_client import AsyncWebClient
from utils.emoji_mapper import EmojiMapper
from datetime import datetime, timedelta, time
import asyncio
import aiohttp
import io
import os
import time as time_module
import chardet
from services.news_service import NewsService
import pytz
import psutil
from typing import Literal
import json
from datetime import datetime, date
import requests
from xml.etree import ElementTree
import random
import json
from typing import Optional

SCHEDULE_FILE = "data/schedules.json" # スケジュールデータを保存するファイル
FAVORITES_FILE = "data/favorites.json" # お気に入り論文を保存するファイル

# スケジュールデータを保存するディレクトリの作成
os.makedirs("data", exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

# Botクラスを拡張
class LabBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = datetime.now()

# Botインスタンスの作成を修正
bot = LabBot(command_prefix="!", intents=intents)

slack_client = AsyncWebClient(token=SLACK_BOT_TOKEN)

# メッセージ転送履歴を追跡するためのキャッシュ
message_cache = {}

# チャンネルチェックデコレータ
def arxiv_channel_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.channel_id != DISCORD_ARXIV_CHANNEL_ID:
            await interaction.response.send_message(
                "このコマンドは arXiv チャンネルでのみ使用できます。",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

# お気に入り論文の読み込み関数を修正
def load_favorites():
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content:
                    return json.loads(content)
        # ファイルが存在しないか空の場合は空の辞書を返す
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"JSONデコードエラー: {e}")
        return {}
    except Exception as e:
        logging.error(f"ファイル読み込みエラー: {e}")
        return {}

# お気に入り論文の保存関数を修正
def save_favorites(favorites):
    try:
        # データディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"ファイル保存エラー: {e}")
        raise

@bot.event
async def on_ready():
    print(f"{bot.user} is now running!")
    try:
        # コマンドの同期
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")

        # ニュース投稿タスクの開始
        bot.loop.create_task(schedule_news())
        
        # ステータス更新タスクの開始
        bot.loop.create_task(update_bot_status())
        
        # サーバー情報をログに記録
        logging.info(f"Connected to {len(bot.guilds)} servers")
        for guild in bot.guilds:
            logging.info(f"Server: {guild.name} (ID: {guild.id})")
            logging.info(f"Members: {guild.member_count}")
            logging.info(f"Channels: {len(guild.channels)}")
            
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# ステータス更新用の関数を追加
async def update_bot_status():
    """定期的にボットのステータスを更新"""
    while True:
        try:
            # 接続時間を計算
            uptime = datetime.now() - bot.start_time
            hours = uptime.total_seconds() // 3600
            minutes = (uptime.total_seconds() % 3600) // 60

            # システム情報を取得
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            cpu_percent = psutil.Process().cpu_percent()
            
            # ネットワーク情報を取得
            net_io = psutil.net_io_counters()
            network_speed = (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024  # MB
            
            # ステータス文字列を作成
            status_details = f"CPU: {cpu_percent:.1f}% | MEM: {memory_usage:.1f}MB"
            status_state = f"NET: {network_speed:.1f}MB/s"
            
            # ステータスを更新
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"稼働時間: {int(hours)}時間{int(minutes)}分",
                details=status_details,
                state=status_state
            )
            await bot.change_presence(
                status=discord.Status.online,
                activity=activity
            )
            await asyncio.sleep(60)  # 1分ごとに更新

        except Exception as e:
            logging.error(f"ステータス更新エラー: {e}")
            await asyncio.sleep(60)

async def schedule_news():
    """毎朝9時にニュースを投稿するスケジューラー"""
    try:
        news_service = NewsService(bot)
        japan_tz = pytz.timezone('Asia/Tokyo')

        while True:
            now = datetime.now(japan_tz)
            target_time = time(hour=9, minute=0)  # datetime.timeを使用

            # 次の実行時刻を計算
            if now.time() >= target_time:
                tomorrow = now.date() + timedelta(days=1)
                next_run = datetime.combine(tomorrow, target_time)
            else:
                next_run = datetime.combine(now.date(), target_time)

            next_run = japan_tz.localize(next_run)
            delay = (next_run - now).total_seconds()

            await asyncio.sleep(delay)
            await news_service.post_news()
    except Exception as e:
        logging.error(f"ニュース配信スケジューラーでエラーが発生: {e}")

# on_message イベントハンドラーを修正

@bot.event
async def on_message(message):
    # Botからのメッセージは完全に無視
    if message.author.bot:
        return

    # コマンド処理を優先
    await bot.process_commands(message)

    # NOTIFICATION_CHANNEL_ID2からのメッセージのみSlackに転送
    if message.channel.id == NOTIFICATION_CHANNEL_ID2:
        try:
            # テキストメッセージの転送
            if message.content:
                await send_to_slack(message, message.author, message.channel)

            # ファイルの転送
            if message.attachments:
                for attachment in message.attachments:
                    await send_file_to_slack(message, attachment)

            logging.info(f"Message and files forwarded from Discord user {message.author.name}")
        except Exception as e:
            logging.error(f"Failed to send message or files to Slack: {e}")
        return

    # 通常のメッセージ処理（スラッシュコマンドではない場合のみ）
    if not message.content.startswith('/'):
        if message.channel.id != NOTIFICATION_CHANNEL_ID:
            log_event(f"Discord メッセージ受信: {message.content}")
            try:
                formatted_message = format_message(message.content)
                await message.channel.send(f"受信メッセージのフォーマット: {formatted_message}")
            except Exception as e:
                embed = create_error_embed("メッセージ処理エラー", str(e))
                await message.channel.send(embed=embed)

@bot.tree.command(name="notify")
async def notify(interaction: discord.Interaction, user: discord.Member, *, content: str):
    channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
    if channel:
        embed = create_notification_embed("通知", content, category="High")
        await channel.send(f"{user.mention}", embed=embed)
        await interaction.response.send_message(f"通知を送信しました: {content}", ephemeral=True)
    else:
        await interaction.response.send_message("通知チャンネルが見つかりません。", ephemeral=True)

# 管理者権限チェック用のデコレータを作成
def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        # 管理者権限またはロールを持っているかチェック
        has_role = any(role.id == DISCORD_ROLE_ID for role in interaction.user.roles)
        if not (interaction.user.guild_permissions.administrator or has_role):
            await interaction.response.send_message(
                "このコマンドは管理者権限または必要なロールが必要です。",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

# logコマンドに管理者権限チェックを追加
# チャンネル制限用デコレータを追加
def log_channel_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.channel_id != DISCORD_LOG_CHANNEL_ID:
            await interaction.response.send_message(
                f"このコマンドは <#{DISCORD_LOG_CHANNEL_ID}> チャンネルでのみ使用できます。",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

# logコマンドを修正
@bot.tree.command(name="log")
@is_admin()
@log_channel_only()
async def log(interaction: discord.Interaction):
    """
    最新のログを表示します（管理者のみ）
    """
    try:
        # ファイルのエンコーディングを自動検出
        with open("logs.txt", 'rb') as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
            encoding = detected['encoding']

        # 検出されたエンコーディングでファイルを読み込み
        with open("logs.txt", "r", encoding=encoding) as f:
            logs = f.readlines()

        # 最新の10行を取得
        recent_logs = ''.join(logs[-10:])

        # 文字列が空でないことを確認
        if not recent_logs.strip():
            await interaction.response.send_message(
                "ログが空です。",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"最新のログ (エンコーディング: {encoding}):\n```\n{recent_logs}\n```",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"ログの読み取りに失敗しました。エラー: {str(e)}\n"
            f"エンコーディング: {encoding if 'encoding' in locals() else '不明'}",
            ephemeral=True
        )
        logging.error(f"ログ読み取りエラー: {e}")

@bot.tree.command(
    name="log_delete",
    description="ログファイルの内容を削除します（管理者のみ）"
)
@is_admin()
@log_channel_only()
async def log_delete(interaction: discord.Interaction):
    """ログファイルの内容を削除します（管理者のみ）"""
    try:
        # ファイルを空にする
        with open("logs.txt", "w", encoding='utf-8') as f:
            f.write("")

        embed = discord.Embed(
            title="✅ ログ削除完了",
            description="ログファイルの内容を削除しました。",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name="実行者",
            value=f"{interaction.user.name} ({interaction.user.id})",
            inline=False
        )
        
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )
        
        # ログにも記録
        logging.info(f"ログファイルが {interaction.user.name} によって削除されました")
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ エラー",
            description=f"ログファイルの削除中にエラーが発生しました：{str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(
            embed=error_embed,
            ephemeral=True
        )
        logging.error(f"ログ削除エラー: {e}")

@bot.tree.command(
    name="news",
    description="最新のテックニュースを取得します"
)
async def news(interaction: discord.Interaction, default: bool = False):
    try:
        if interaction.channel_id != DISCORD_NEWS_CHANNEL_ID:
            await interaction.response.send_message(
                f"このコマンドは <#{DISCORD_NEWS_CHANNEL_ID}> チャンネルでのみ使用できます。",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        news_service = NewsService(bot)
        # ニュース取得中にデフォルトのニュースを表示
        if default:
            default_article = {
                "title": "【重要】Github、のフォローのお願い",
                "description": "個人開発した内容やAIの最新ニュースなどを発信中！是非フォローしてね！",
                "url": "https://github.com/paraccoli",
                "urlToImage": "https://ujise.com/wp-content/uploads/2022/08/GitHub-Logo.png",
                "source": {"name": "研究室Bot News"}
            }
            embed = news_service.create_news_embed(default_article)
            await interaction.followup.send(
                content="🌟 今日のピックアップニュース",
                embed=embed,
                ephemeral=True
            )
            return

        try:
            articles = await asyncio.wait_for(
                news_service.fetch_news(),
                timeout=15.0
            )
            
            if not articles:
                # デフォルトのニュース情報を作成
                default_article = {
                    "title": "【重要】Github、のフォローのお願い",
                    "description": "個人開発した内容やAIの最新ニュースなどを発信中！是非フォローしてね！",
                    "url": "https://github.com/paraccoli",
                    "urlToImage": "https://ujise.com/wp-content/uploads/2022/08/GitHub-Logo.png",
                    "source": {"name": "研究室Bot News"}
                }
                embed = news_service.create_news_embed(default_article)
                await interaction.followup.send(
                    content="🌟 今日のピックアップニュース",
                    embed=embed,
                    ephemeral=True
                )
                return

            for i, article in enumerate(articles[:5]):
                if embed := news_service.create_news_embed(article):
                    prefix = "🌟 今日のテックニュース" if i == 0 else ""
                    await interaction.followup.send(
                        content=prefix,
                        embed=embed,
                        ephemeral=True
                    )
                await asyncio.sleep(0.5)

        except asyncio.TimeoutError:
            await interaction.followup.send(
                "ニュースの取得がタイムアウトしました。",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"ニュース取得エラー: {str(e)}")
            await interaction.followup.send(
                "ニュースの取得中にエラーが発生しました。",
                ephemeral=True
            )

    except Exception as e:
        logging.error(f"コマンド実行エラー: {str(e)}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "エラーが発生しました。",
                ephemeral=True
            )


# arXiv関連のコマンドグループ
@bot.tree.command(
    name="arxiv_search",
    description="arXivから論文を検索します"
)
@arxiv_channel_only()
async def arxiv_search(interaction: discord.Interaction, query: str):
    try:
        url = f'http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results=5'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    root = ElementTree.fromstring(content)
                    entries = root.findall('{http://www.w3.org/2005/Atom}entry')

                    if not entries:
                        await interaction.response.send_message("論文が見つかりませんでした。", ephemeral=True)
                        return

                    embed = discord.Embed(
                        title=f"検索結果 (キーワード: {query})",
                        description="IDをコピーするには、IDの行を選択してコピーしてください。",
                        color=discord.Color.blue()
                    )
                    
                    for entry in entries:
                        title = entry.find('{http://www.w3.org/2005/Atom}title').text
                        link = entry.find('{http://www.w3.org/2005/Atom}id').text
                        paper_id = link.split('/')[-1]
                        
                        # タイトルとキーワードを組み合わせて表示
                        keywords = [kw.strip() for kw in query.split(',')]
                        keyword_text = " | ".join([f"🔑={kw}" for kw in keywords])
                        
                        embed.add_field(
                            name=f"📄 論文情報",
                            value=(
                                f"**タイトル**: {title}\n"
                                f"**キーワード**: {keyword_text}\n"
                                f"**ID**: `{paper_id}`\n"
                                f"**リンク**: [arXiv]({link})"
                            ),
                            inline=False
                        )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message("APIの呼び出しに失敗しました。", ephemeral=True)
    except Exception as e:
        logging.error(f"arXiv検索エラー: {e}")
        await interaction.response.send_message("検索中にエラーが発生しました。", ephemeral=True)

@bot.tree.command(
    name="arxiv_save",
    description="論文をお気に入りに保存します"
)
@arxiv_channel_only()
async def arxiv_save(interaction: discord.Interaction, paper_id: str):
    try:
        favorites = load_favorites()
        user_id = str(interaction.user.id)
        
        if user_id not in favorites:
            favorites[user_id] = []
        
        # 既に保存済みかチェック
        if paper_id in [paper['id'] for paper in favorites[user_id]]:
            await interaction.response.send_message("この論文は既に保存されています。", ephemeral=True)
            return
        
        url = f'http://export.arxiv.org/api/query?id_list={paper_id}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    root = ElementTree.fromstring(content)
                    entry = root.find('{http://www.w3.org/2005/Atom}entry')
                    
                    if entry:
                        title = entry.find('{http://www.w3.org/2005/Atom}title').text
                        # 新しい論文を追加
                        favorites[user_id].append({
                            'id': paper_id,
                            'title': title,
                            'saved_at': datetime.now().isoformat()
                        })
                        # 変更を保存
                        save_favorites(favorites)
                        
                        await interaction.response.send_message(
                            f"論文を保存しました:\nID: {paper_id}\nTitle: {title}",
                            ephemeral=True
                        )
                    else:
                        await interaction.response.send_message("論文が見つかりませんでした。", ephemeral=True)
                else:
                    await interaction.response.send_message("APIの呼び出しに失敗しました。", ephemeral=True)
    except Exception as e:
        logging.error(f"論文保存エラー: {e}")
        await interaction.response.send_message("保存中にエラーが発生しました。", ephemeral=True)


@bot.tree.command(
    name="arxiv_list",
    description="保存した論文の一覧を表示します"
)
@arxiv_channel_only()
async def arxiv_list(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    favorites = load_favorites()
    target_user = user or interaction.user
    user_id = str(target_user.id)
    
    if user_id not in favorites or not favorites[user_id]:
        await interaction.response.send_message(
            f"{target_user.display_name}の保存済み論文はありません。",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title=f"{target_user.display_name}の保存済み論文",
        color=discord.Color.blue()
    )
    
    for paper in favorites[user_id]:
        embed.add_field(
            name=f"ID: {paper['id']}",
            value=f"Title: {paper['title']}\nSaved: {paper['saved_at']}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(
    name="arxiv_delete",
    description="保存した論文を削除します"
)
@arxiv_channel_only()
async def arxiv_delete(interaction: discord.Interaction, paper_id: str):
    favorites = load_favorites()
    user_id = str(interaction.user.id)
    
    if user_id not in favorites or not any(p['id'] == paper_id for p in favorites[user_id]):
        await interaction.response.send_message("指定された論文は保存されていません。", ephemeral=True)
        return
    favorites[user_id] = [p for p in favorites[user_id] if p['id'] != paper_id]
    save_favorites(favorites)
    await interaction.response.send_message("論文を削除しました。", ephemeral=True)


@bot.tree.command(
    name="help",
    description="Botの機能と使い方を表示します"
)
async def help(interaction: discord.Interaction):
    """Botの機能と使い方を表示します。"""
    try:
        embed = discord.Embed(
            title="🤖 研究室Bot ヘルプ",
            description="研究室用の高機能コミュニケーションBotです。\nSlack連携や論文管理、ニュース配信など様々な機能を提供します。",
            color=discord.Color.blue()
        )


        # 基本コマンド
        embed.add_field(
            name="📝 基本コマンド",
            value=(
                "```\n"
                "/help - このヘルプを表示\n"
                "/news [default:True/False] - 最新のテックニュースを表示\n"
                "   - default:True で研究室Bot開発者の情報を表示\n"
                "/notify [@ユーザー] [内容] - 指定したユーザーに通知を送信\n"
                "```"
            ),
            inline=False
        )

        # 論文管理機能
        embed.add_field(
            name="📚 論文管理機能",
            value=(
                "```\n"
                "/arxiv_search [クエリ] - arXivから論文を検索\n"
                "   - 検索結果にキーワードと簡単コピー用IDを表示\n"
                "/arxiv_save [論文ID] - 論文をお気に入りに保存\n"
                "/arxiv_list [ユーザー] - 保存した論文の一覧を表示\n"
                "/arxiv_delete [論文ID] - 保存した論文を削除\n"
                "```\n"
                f"※ これらのコマンドは <#{DISCORD_ARXIV_CHANNEL_ID}> チャンネルでのみ使用可能です。"
            ),
            inline=False
        )

        # 管理者用コマンド
        embed.add_field(
            name="👑 管理者用コマンド",
            value=(
                "```\n"
                "/log - 最新のログを表示\n"
                "/log_delete - ログファイルの内容を削除\n"
                "```\n"
                f"※ これらのコマンドは <#{DISCORD_LOG_CHANNEL_ID}> チャンネルでのみ使用可能です。"
            ),
            inline=False
        )

        # 統計・管理機能
        embed.add_field(
            name="📊 統計・管理",
            value=(
                "```\n"
                "/stats - システムとBotの統計情報を表示\n"
                "/schedule add [日付] [内容] [カテゴリ] - 予定を追加\n"
                "   - カテゴリ: ミーティング/セミナー/締切/その他\n"
                "/schedule show - 予定一覧を表示\n"
                "/schedule delete [日付] - 予定を削除\n"
                "```"
            ),
            inline=False
        )

        # 自動機能
        embed.add_field(
            name="🔄 自動機能",
            value=(
                "• Slack ⇔ Discord メッセージ双方向連携\n"
                "• ファイル転送対応（画像・文書など）\n"
                "• リアクション同期（絵文字反応の共有）\n"
                "• 毎朝9時の自動ニュース配信\n"
                "• ボットステータスの自動更新（CPU/メモリ/ネットワーク）"
            ),
            inline=False
        )

        # チャンネル制限
        embed.add_field(
            name="📢 チャンネル制限",
            value=(
                f"• `/news`: <#{DISCORD_NEWS_CHANNEL_ID}> のみ\n"
                f"• `/arxiv_*`: <#{DISCORD_ARXIV_CHANNEL_ID}> のみ\n"
                f"• `/log`, `/log_delete`: <#{DISCORD_LOG_CHANNEL_ID}> のみ\n"
                f"• Slack連携: <#{NOTIFICATION_CHANNEL_ID2}> のみ"
            ),
            inline=False
        )

        # ファイル制限
        embed.add_field(
            name="📎 ファイル転送制限",
            value=(
                f"• 最大サイズ: {MAX_FILE_SIZE // (1024 * 1024)}MB\n"
                f"• 対応形式: {', '.join(ALLOWED_FILE_TYPES)}"
            ),
            inline=False
        )

        # フッター
        embed.set_footer(
            text=f"Bot稼働時間: {int((datetime.now() - bot.start_time).total_seconds() // 3600)}時間"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logging.error(f"ヘルプ表示エラー: {e}")
        await interaction.response.send_message(
            "ヘルプの表示中にエラーが発生しました。",
            ephemeral=True
        )

@bot.tree.command(
    name="stats",
    description="サーバーの統計情報を表示します"
)
async def stats(interaction: discord.Interaction):
    """サーバーとBotの統計情報を表示します"""
    try:
        embed = discord.Embed(
            title="📊 システム統計情報",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        # システムリソース情報
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_freq = psutil.cpu_freq()
        
        embed.add_field(
            name="💻 システム情報",
            value=(
                f"CPU使用率: {psutil.cpu_percent()}%\n"
                f"CPU周波数: {cpu_freq.current:.1f}MHz\n"
                f"メモリ使用率: {memory.percent}%\n"
                f"ディスク使用率: {disk.percent}%"
            ),
            inline=False
        )

        # ネットワーク情報
        net_io = psutil.net_io_counters()
        net_speed = (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024
        
        embed.add_field(
            name="🌐 ネットワーク",
            value=(
                f"送信: {net_io.bytes_sent / 1024 / 1024:.1f}MB\n"
                f"受信: {net_io.bytes_recv / 1024 / 1024:.1f}MB\n"
                f"現在の速度: {net_speed:.1f}MB/s"
            ),
            inline=True
        )

        # Bot統計
        uptime = datetime.now() - bot.start_time
        embed.add_field(
            name="🤖 Bot統計",
            value=(
                f"稼働時間: {int(uptime.total_seconds() // 3600)}時間\n"
                f"監視メッセージ: {len(message_cache)}件\n"
                f"メモリ使用量: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB"
            ),
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logging.error(f"統計表示エラー: {e}")
        await interaction.response.send_message(
            "統計情報の取得中にエラーが発生しました。",
            ephemeral=True
        )

@bot.tree.command(
    name="schedule",
    description="研究室のスケジュールを管理します"
)
async def schedule(
    interaction: discord.Interaction,
    action: Literal["add", "show", "delete"],
    date: str = None,
    event: str = None,
    category: Literal["ミーティング", "セミナー", "締切", "その他"] = "その他"
):
    try:
        # スケジュールデータの読み込み
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
                schedules = json.load(f)
        else:
            schedules = {}

        if action == "add":
            if not date or not event:
                await interaction.response.send_message(
                    "日付と予定の内容を指定してください。",
                    ephemeral=True
                )
                return

            try:
                # 文字列を日付オブジェクトに変換
                event_date = datetime.strptime(date, "%Y-%m-%d").date()
                today = datetime.now().date()  # 現在の日付を取得
                
                # 過去の日付かどうかをチェック
                if event_date < today:
                    await interaction.response.send_message(
                        "過去の日付は指定できません。",
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    "日付の形式が正しくありません。YYYY-MM-DD形式で指定してください。",
                    ephemeral=True
                )
                return

            if date not in schedules:
                schedules[date] = []
            
            schedules[date].append({
                "event": event,
                "category": category,
                "created_by": str(interaction.user),
                "created_at": datetime.now().isoformat()
            })

            embed = discord.Embed(
                title="📅 予定を追加しました",
                description=f"日付: {date}\n予定: {event}\nカテゴリ: {category}",
                color=discord.Color.green()
            )

        elif action == "show":
            embed = discord.Embed(
                title="📅 スケジュール一覧",
                color=discord.Color.blue()
            )

            if not schedules:
                embed.description = "予定はありません。"
            else:
                for date in sorted(schedules.keys()):
                    events = schedules[date]
                    if events:
                        event_text = "\n".join(
                            f"• [{e['category']}] {e['event']}" for e in events
                        )
                        embed.add_field(
                            name=f"📌 {date}",
                            value=event_text,
                            inline=False
                        )

        elif action == "delete":
            if not date:
                await interaction.response.send_message(
                    "削除する予定の日付を指定してください。",
                    ephemeral=True
                )
                return

            if date in schedules:
                del schedules[date]
                embed = discord.Embed(
                    title="🗑️ 予定を削除しました",
                    description=f"日付: {date}の予定を全て削除しました。",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="❌ エラー",
                    description=f"日付: {date}の予定は見つかりませんでした。",
                    color=discord.Color.red()
                )

        # スケジュールデータの保存
        with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
            json.dump(schedules, f, ensure_ascii=False, indent=2)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logging.error(f"スケジュール管理エラー: {e}")
        await interaction.response.send_message(
            "スケジュールの管理中にエラーが発生しました。",
            ephemeral=True
        )

async def send_to_discord(message_text, user_name, channel_name, from_slack=True):
    """
    Discordの通知チャンネルにメッセージをEmbed形式で送信
    from_slack: Slackからの転送かどうかを示すフラグ
    """
    if not from_slack:  # Slackからの転送でない場合は処理しない
        return

    logging.info(f"Sending message to Discord from {user_name} in {channel_name}")
    channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)

    if channel:
        embed = discord.Embed(
            title=f"Message from {channel_name}",
            description=message_text,
            color=discord.Color.blue()
        )
        embed.set_author(name=user_name)
        embed.set_footer(text=f"Sent from Slack • {channel_name}")

        await channel.send(embed=embed)
        logging.info("Message sent to Discord successfully")
    else:
        logging.error("Discord通知チャンネルが見つかりません")

async def send_to_slack(message, user, channel):
    """
    メッセージの重複送信を防ぐためのキャッシュチェック付きSlack送信
    """
    cache_key = f"{message.id}"
    if cache_key in message_cache:
        return

    message_cache[cache_key] = datetime.now()

    try:
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Message from Discord #{channel.name}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message.content
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Sent by *{user.name}* from Discord"
                    }
                ]
            }
        ]

        response = await slack_client.chat_postMessage(
            channel=SLACK_CHANNEL_ID_4,
            blocks=blocks,
            text=f"Message from Discord: {message.content}"
        )

        # Slackのタイムスタンプをキャッシュに保存
        message_cache[cache_key] = response['ts']

        # 古いキャッシュエントリの削除
        current_time = datetime.now()
        message_cache.update({k: v for k, v in message_cache.items() 
                            if current_time - v < timedelta(minutes=5)})

    except Exception as e:
        logging.error(f"Error sending message to Slack: {e}")

async def handle_file_upload(message, file_url, filename):
    """ファイルをダウンロードして転送する共通関数"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    file_content = await response.read()
                    file_size = len(file_content)

                    if file_size > MAX_FILE_SIZE:
                        return False, "ファイルサイズが大きすぎます"

                    file_ext = os.path.splitext(filename)[1].lower()
                    if file_ext not in ALLOWED_FILE_TYPES:
                        return False, "未対応のファイル形式です"

                    return True, file_content
    except Exception as e:
        logging.error(f"ファイルダウンロードエラー: {e}")
        return False, str(e)

async def send_file_to_slack(message, attachment):
    """Discordのファイルを Slack に転送"""
    try:
        success, result = await handle_file_upload(message, attachment.url, attachment.filename)
        if success:
            await slack_client.files_upload_v2(
                channel=SLACK_CHANNEL_ID_1,
                file=result,
                filename=attachment.filename,
                initial_comment=f"File shared by {message.author.name} from Discord"
            )
            logging.info(f"ファイル転送成功: {attachment.filename}")
        else:
            logging.error(f"ファイル転送失敗: {result}")
    except Exception as e:
        logging.error(f"Slackへのファイル転送エラー: {e}")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if reaction.message.channel.id == NOTIFICATION_CHANNEL_ID2:
        try:
            # メッセージIDをキーとしてSlackのts（タイムスタンプ）を取得
            slack_ts = message_cache.get(str(reaction.message.id))
            if slack_ts:
                emoji = EmojiMapper.discord_to_slack(str(reaction.emoji))
                if emoji:
                    await slack_client.reactions_add(
                        channel=SLACK_CHANNEL_ID_1,
                        timestamp=slack_ts,
                        name=emoji.strip(':')
                    )
                    logging.info(f"Reaction synced to Slack: {emoji}")
        except Exception as e:
            logging.error(f"Failed to sync reaction to Slack: {e}")

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return

    if reaction.message.channel.id == NOTIFICATION_CHANNEL_ID2:
        try:
            slack_ts = message_cache.get(str(reaction.message.id))
            if slack_ts:
                emoji = EmojiMapper.discord_to_slack(str(reaction.emoji))
                if emoji:
                    await slack_client.reactions_remove(
                        channel=SLACK_CHANNEL_ID_1,
                        timestamp=slack_ts,
                        name=emoji.strip(':')
                    )
                    logging.info(f"Reaction removed from Slack: {emoji}")
        except Exception as e:
            logging.error(f"Failed to remove reaction from Slack: {e}")

async def start_discord_bot():
    await bot.start(DISCORD_BOT_TOKEN)