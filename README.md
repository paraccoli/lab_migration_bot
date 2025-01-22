# 🤖 Lab Migration Bot

Discord と Slack を連携する高機能コミュニケーションBotです。

## ✨ 主な機能

### 💬 コミュニケーション連携
- **Slack ⇔ Discord メッセージの双方向連携**
  - テキストメッセージの自動同期
  - 絵文字リアクションの同期
  - メンション対応
  - スレッド対応
- **ファイル転送対応**
  - 画像ファイル (PNG, JPG, GIF)
  - 文書ファイル (PDF, DOC, DOCX)
  - 圧縮ファイル (ZIP)
  - 最大転送サイズ: 10MB
- **リアクション同期**
  - Discord絵文字 → Slack絵文字の自動変換
  - カスタム絵文字対応
  - リアクション削除の同期

### 📚 論文管理
- **arXiv論文の検索**
  - キーワード検索
  - カテゴリ検索
  - 著者検索
  - 日付範囲指定
- **お気に入り論文の保存**
  - ユーザーごとの保存機能
  - タグ付け機能
  - 簡単コピー用ID
- **論文リストの管理**
  - 保存日時表示
  - 論文情報の一覧表示
  - 削除機能

### 📰 ニュース配信
- **最新テックニュースの取得**
  - AIニュース
  - テクノロジーニュース
  - 研究関連ニュース
- **自動ニュース配信**
  - 毎朝9時に自動配信
  - カスタマイズ可能なトピック
  - エラー時の代替表示
- **カスタムニュース**
  - デフォルトニュース表示
  - キーワードフィルター
  - ソース選択

### 📅 スケジュール管理
- **予定管理**
  - 追加：`/schedule add YYYY-MM-DD イベント内容 カテゴリ`
  - 表示：`/schedule show`
  - 削除：`/schedule delete YYYY-MM-DD`
- **カテゴリ**
  - ミーティング
  - セミナー
  - 締切
  - その他
- **表示機能**
  - 日付順表示
  - カテゴリ別表示
  - 期限切れ自動削除

## 🛠️ インストール

### システム要件
- Windows 10/11 または Linux
- Python 3.9以上
- pip (Python パッケージマネージャー)
- Git

### インストール手順

```bash
# 1. リポジトリのクローン
git clone https://github.com/paraccoli/lab_migration_bot.git
cd lab_migration_bot

# 2. 仮想環境の作成と有効化
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. 依存パッケージのインストール
pip install -r requirements.txt

# 4. 設定ファイルの準備
cp config.example.py config.py
```

### 設定手順
1. Discord Botトークンの取得
   - Discord Developer Portalでアプリケーション作成
   - Botトークンの発行
   - 必要な権限の設定

2. Slack APIトークンの取得
   - Slack API設定でアプリケーション作成
   - BotトークンとAppトークンの発行
   - チャンネルIDの取得

3. NewsAPIキーの取得
   - NewsAPI.orgでアカウント作成
   - APIキーの発行

4. 環境設定
```python
# config.py の設定
DISCORD_BOT_TOKEN = "your-discord-token"
SLACK_BOT_TOKEN = "your-slack-token"
SLACK_APP_TOKEN = "your-slack-app-token"
NEWS_API_KEY = "your-newsapi-key"
```

## 📝 使い方

### 基本コマンド
```
/help
└── Botの全機能と使い方を表示

/news [default:True/False]
├── default:False → 最新ニュースを表示
└── default:True → Bot開発者情報を表示

/arxiv_search [query]
├── 論文をキーワード検索
└── 結果は最大5件表示

/schedule add [date] [event] [category]
├── date: YYYY-MM-DD形式
├── event: イベント内容
└── category: ミーティング/セミナー/締切/その他
```

### 🚦 チャンネル制限

| コマンド | チャンネル | 説明 |
|---------|------------|------|
| `/news` | #news-feed | ニュース関連の操作 |
| `/arxiv_*` | #arxiv-papers | 論文関連の操作 |
| `/log` | #bot-logs | ログ確認・管理 |
| Slack連携 | #slack-sync | Slackとの連携 |

### ⚠️ エラー対処
- **ニュース取得エラー**
  - APIキーの確認
  - インターネット接続の確認
  - デフォルトニュースの表示確認

- **Slack連携エラー**
  - トークンの有効性確認
  - チャンネルIDの確認
  - 権限設定の確認

- **論文検索エラー**
  - クエリの形式確認
  - API制限の確認
  - タイムアウト設定の確認

## 🔧 開発環境

### 必要なライブラリ
```
discord.py>=2.0.0
slack-sdk>=3.0.0
aiohttp>=3.8.0
python-dotenv>=0.19.0
newsapi-python>=0.2.6
```

### 開発ツール
- Visual Studio Code
- Python Extension
- Git

## 👤 開発者情報

**paraccoli**
- GitHub: [@paraccoli](https://github.com/paraccoli)
- Twitter: [@paraccoli](https://twitter.com/paraccoli)
- プロジェクト管理: [研究室Bot Project](https://github.com/paraccoli/lab_migration_bot)

## 📄 ライセンス

MIT License - 詳細は LICENSE ファイルを参照してください。

## 🤝 コントリビューション

1. Fork the Project
2. Create your Feature Branch
3. Commit your Changes
4. Push to the Branch
5. Open a Pull Request

## 📞 サポート

問題が発生した場合は、GitHub Issuesで報告してください。