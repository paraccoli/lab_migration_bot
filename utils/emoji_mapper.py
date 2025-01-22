from typing import Dict, Optional

class EmojiMapper:
    # SlackとDiscordの基本的な絵文字マッピング
    EMOJI_MAP: Dict[str, str] = {
        # 基本的な絵文字
        ":smile:": "😊",
        ":laughing:": "😄",
        ":thumbsup:": "👍",
        ":thumbsdown:": "👎",
        ":heart:": "❤️",
        ":warning:": "⚠️",
        ":anger:": "💢",
        ":star:": "⭐",
        ":question:": "❓",
        ":exclamation:": "❗",
        ":ok:": "🆗",
        ":pray:": "🙏",
        ":clap:": "👏",
        ":fire:": "🔥",
        ":eyes:": "👀",
        # 研究室向けカスタム絵文字
        ":paper:": "📄",
        ":book:": "📚",
        ":computer:": "💻",
        ":bulb:": "💡",
        ":calendar:": "📅",
        ":clock:": "⏰",
    }

    @classmethod
    def slack_to_discord(cls, slack_emoji: str) -> Optional[str]:
        """Slack形式の絵文字をDiscord形式に変換"""
        return cls.EMOJI_MAP.get(slack_emoji)

    @classmethod
    def discord_to_slack(cls, discord_emoji: str) -> Optional[str]:
        """Discord形式の絵文字をSlack形式に変換"""
        for slack, discord in cls.EMOJI_MAP.items():
            if discord == discord_emoji:
                return slack
        return None