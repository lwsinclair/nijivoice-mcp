# グローバル設定値
import os
import logging
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

# APIキーの取得
API_KEY = os.environ.get("NIJIVOICE_API_KEY")
if not API_KEY:
    raise ValueError("NIJIVOICE_API_KEY 環境変数を設定してください。")

# APIのベースURL
API_BASE_URL = "https://api.nijivoice.com/api/platform/v1"

# デフォルトのタイムアウト設定（秒）
DEFAULT_TIMEOUT = 30.0

# デフォルトのVoice Actor ID
DEFAULT_VOICE_ACTOR_ID = "90031163-c497-44f3-a8a6-e45e4d0cb8f6"

# リトライ設定
MAX_RETRIES = 3
BASE_RETRY_DELAY = 2.0

# ファイルサーバーのURL（一時ファイル用）
FILE_SERVER_URL = os.environ.get("NIJIVOICE_FILE_SERVER_URL", "http://localhost:8000/files")
