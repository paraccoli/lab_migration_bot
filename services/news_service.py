import asyncio
import aiohttp
from datetime import datetime, timedelta
import discord
from config import NEWS_API_KEY, NEWS_KEYWORDS, DISCORD_NEWS_CHANNEL_ID
import logging

class NewsService:
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://newsapi.org/v2"
        self.headers = {"X-Api-Key": NEWS_API_KEY}
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def fetch_news(self, fallback=False):
        """ニュース記事を取得"""
        try:
            # 日付設定
            today = datetime.now().strftime("%Y-%m-%d")
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            # APIエンドポイントとパラメータ設定
            if fallback:
                endpoint = f"{self.base_url}/everything"
                params = {
                    "q": NEWS_KEYWORDS,
                    "from": week_ago,
                    "to": today,
                    "sortBy": "popularity",
                    "pageSize": 1
                }
            else:
                endpoint = f"{self.base_url}/top-headlines"
                params = {
                    "category": "technology",
                    "country": "jp",
                    "pageSize": 5
                }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(endpoint, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = data.get("articles", [])
                        
                        if not articles and not fallback:
                            return await self.fetch_news(fallback=True)
                        
                        if not articles:
                            # デフォルトニュースの配列を返す
                            return [{
                                "title": "AIと機械学習の最新動向",
                                "description": "最新のAI技術動向とその応用について解説します。",
                                "url": "https://github.com/paraccoli",
                                "urlToImage": "https://i.pinimg.com/736x/71/d7/f0/71d7f0358952998072b0d92de58c8257.jpg",
                                "source": {"name": "研究室Bot News"},
                                "publishedAt": datetime.now().isoformat()
                            }]
                        
                        return articles

                    elif response.status == 429:
                        logging.error("NewsAPI rate limit exceeded")
                        return self.get_default_articles()
                    else:
                        logging.error(f"NewsAPI Error: Status {response.status}")
                        return [] if fallback else await self.fetch_news(fallback=True)

        except Exception as e:
            logging.error(f"ニュース取得エラー: {str(e)}")
            return self.get_default_articles()

    def get_default_articles(self):
        """デフォルトニュース記事を返す"""
        return [{
            "title": "AI研究の最前線：新しい発見と課題",
            "description": "AI研究における最新の進展と、今後の課題について詳しく解説します。",
            "url": "https://github.com/paraccoli",
            "urlToImage": "https://i.pinimg.com/736x/71/d7/f0/71d7f0358952998072b0d92de58c8257.jpg",
            "source": {"name": "研究室Bot News"},
            "publishedAt": datetime.now().isoformat()
        }]

    def create_news_embed(self, article):
        """ニュース記事のEmbed作成"""
        try:
            published_at = datetime.fromisoformat(article.get("publishedAt", datetime.now().isoformat()).replace('Z', '+00:00'))
            
            embed = discord.Embed(
                title=article.get("title", "タイトルなし")[:256],
                url=article.get("url", ""),
                description=article.get("description", "説明なし")[:2048],
                color=discord.Color.blue(),
                timestamp=published_at
            )
            
            if article.get("urlToImage"):
                embed.set_image(url=article["urlToImage"])
            
            embed.add_field(
                name="出典",
                value=article.get("source", {}).get("name", "不明"),
                inline=True
            )
            
            embed.set_footer(text="Tech News Bot")
            return embed
            
        except Exception as e:
            logging.error(f"Embed作成エラー: {str(e)}")
            return None

    async def post_news(self):
        """定期ニュース投稿用"""
        channel = self.bot.get_channel(DISCORD_NEWS_CHANNEL_ID)
        if not channel:
            return False

        try:
            articles = await self.fetch_news()
            if not articles:
                return False

            for article in articles:
                if embed := self.create_news_embed(article):
                    await channel.send(embed=embed)
                    await asyncio.sleep(1)
            return True

        except Exception as e:
            logging.error(f"ニュース投稿エラー: {str(e)}")
            return False