import os

def upload_file(file_path, platform):
    """
    ファイルを指定のプラットフォームにアップロードする（Mock）。
    """
    if platform == "slack":
        print(f"Slack に {file_path} をアップロード")
    elif platform == "discord":
        print(f"Discord に {file_path} をアップロード")