import logging

# ロギングの設定
def setup_logging(log_file='nijivoice_mcp.log', level=logging.DEBUG):
    """アプリケーション全体のロギング設定を行う"""
    logging.basicConfig(
        filename=log_file,
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # ルートロガーの取得
    logger = logging.getLogger('nijivoice_mcp')
    
    # コンソールハンドラも追加
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger

# メインロガーの作成
logger = setup_logging()
