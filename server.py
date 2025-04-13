import os
import logging
from mcp import initialize_mcp
from logger import setup_logging

# ロギングの設定
logger = setup_logging()

def run_server():
    """MCPサーバーを初期化して実行する"""
    logger.info("NijiVoice MCPサーバーを起動しています...")
    
    try:
        # MCPサーバーの初期化
        mcp = initialize_mcp()
        
        # サーバーの実行
        logger.info("MCPサーバーを実行します")
        mcp.run()
    except Exception as e:
        logger.error(f"サーバー起動中にエラーが発生しました: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    run_server()
