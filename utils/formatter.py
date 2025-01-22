def format_message(message):
    if not message:
        raise ValueError("空のメッセージです。")
    return f"[フォーマット済み] {message}"