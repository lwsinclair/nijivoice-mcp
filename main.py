import os
import sys
import logging
from logger import setup_logging
from server import run_server

# ロガーの設定
logger = setup_logging()

def main():
    """アプリケーションのメインエントリーポイント"""
    logger.info("NijiVoice MCPアプリケーションを起動しています...")
    
    try:
        # サーバーの実行
        run_server()
        return 0
    except KeyboardInterrupt:
        logger.info("ユーザーによる中断を検出しました。アプリケーションを終了します。")
        return 0
    except Exception as e:
        logger.error(f"アプリケーション実行中にエラーが発生しました: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
