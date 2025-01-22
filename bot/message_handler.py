from utils.formatter import format_message
from utils.logger import log_event

def process_message(message, user, channel, platform):
    try:
        formatted_message = f"[{channel}] {user}: {message}"
        if platform == "slack":
            formatted_message += " from Slack!"
        elif platform == "discord":
            formatted_message += " from Discord!"
        log_event(f"メッセージ処理成功: {formatted_message} (プラットフォーム: {platform})")
        return formatted_message
    except Exception as e:
        log_event(f"メッセージ処理エラー: {e}", level="ERROR")
        raise e