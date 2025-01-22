# APIトークンや設定
SLACK_BOT_TOKEN = "YOUR_TOKEN"  # Bot User OAuth Access Token
SLACK_APP_TOKEN = "YOUR_TOKEN"  # Slack App Level Token
SLACK_VERIFICATION_TOKEN = "YOUR_TOKEN" # Verification Token
DISCORD_BOT_TOKEN = "YOUR_TOKEN" # Discord Bot Token
DATABASE_URL = "sqlite:///migration.db" # データベースのURL
NGROK_AUTH_TOKEN = "YOUR_TOKEN" # ngrokの認証トークン

# 通知専用チャンネルID
NOTIFICATION_CHANNEL_ID = 1234567890
NOTIFICATION_CHANNEL_ID2 = 1234567890
SLACK_CHANNEL_ID_1 = "C088HUYSTLN"
SLACK_CHANNEL_ID_2 = "C088QHN1YN6"
SLACK_CHANNEL_ID_3 = "C089390MPRP"
SLACK_CHANNEL_ID_4 = "C089T1HKMA4"


# Discord News Channel
DISCORD_NEWS_CHANNEL_ID = 1234567890
DISCORD_ROLE_ID = 1234567890
DISCORD_ARXIV_CHANNEL_ID = 1234567890
DISCORD_LOG_CHANNEL_ID = 1234567890

# ファイル転送の設定を追加

# 最大ファイルサイズ (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# 許可するファイル形式
ALLOWED_FILE_TYPES = [
    '.txt', '.pdf', '.doc', '.docx',
    '.xls', '.xlsx', '.png', '.jpg',
    '.jpeg', '.gif', '.zip'
]

# NewsAPI設定
NEWS_API_KEY = "YOUR_API_KEY"
NEWS_KEYWORDS = [
    "機械学習", "AI", "Google", "OpenAI", "自動運転", "Waymo",
    "Machine Learning", "Artificial Intelligence", "Deep Learning"
]

# デバッグ設定
DEBUG_MODE = True

# ログ設定
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'DEBUG'

# Slack Bot Scopes
REQUIRED_BOT_SCOPES = [
    "channels:history",
    "channels:read",
    "chat:write",
    "files:read",
    "im:history",
    "users:read"
]

# App Level Token Scopes
REQUIRED_APP_SCOPES = [
    "connections:write",
    "authorizations:read"
]