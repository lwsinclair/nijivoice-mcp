import os
import tempfile
import base64
import logging
from typing import Optional, Tuple

# config.pyからのインポート
import sys
sys.path.append('/home/ryoooo/dev/nijivoice-mcp')
from config import FILE_SERVER_URL

logger = logging.getLogger('nijivoice_mcp.utils.audio')

def calculate_timeout(script_length, base_timeout=30.0, char_factor=0.01):
    """スクリプトの長さに応じたタイムアウト時間を計算"""
    # 基本のタイムアウト + スクリプトの長さに応じた追加時間
    # 例: 1000文字のスクリプトなら、base_timeout + 10秒
    return min(base_timeout + (script_length * char_factor), 120.0)  # 最大2分

async def extract_audio_url_from_response(response) -> Tuple[Optional[str], Optional[str]]:
    """レスポンスから音声URLを優先的に抽出する関数"""
    # デバッグ用にレスポンス構造をログ出力
    logger.debug(f"レスポンス構造分析: {type(response).__name__}")
    
    # 優先順位の高いURLフィールド
    url_fields = [
        "audioFileUrl",        # 最優先
        "audioFileDownloadUrl",
        "url",
        "downloadUrl",
        "fileUrl",
        "audioUrl"
    ]
    
    # 1. generated_voice属性から直接検索
    if hasattr(response, 'generated_voice') and isinstance(response.generated_voice, dict):
        gv = response.generated_voice
        logger.debug(f"generated_voice キー: {list(gv.keys())}")
        
        # URLフィールドを優先順位順に検索
        for field in url_fields:
            if field in gv and gv[field]:
                url = gv[field]
                logger.info(f"URLを検出: {field}={url}")
                return url, field
    
    # 2. キャメルケース対応（generatedVoice）
    if hasattr(response, 'generatedVoice') and isinstance(response.generatedVoice, dict):
        gv = response.generatedVoice
        logger.debug(f"generatedVoice キー: {list(gv.keys())}")
        
        for field in url_fields:
            if field in gv and gv[field]:
                url = gv[field]
                logger.info(f"キャメルケースURLを検出: {field}={url}")
                return url, f"camel_{field}"
    
    # 3. model_dumpを使用（Pydantic v2対応）
    if hasattr(response, 'model_dump'):
        try:
            raw_data = response.model_dump()
            logger.debug(f"model_dump キー: {list(raw_data.keys())}")
            
            for gv_key in ['generatedVoice', 'generated_voice']:
                if gv_key in raw_data and isinstance(raw_data[gv_key], dict):
                    gv = raw_data[gv_key]
                    logger.debug(f"{gv_key} in raw_data keys: {list(gv.keys())}")
                    
                    for field in url_fields:
                        if field in gv and gv[field]:
                            url = gv[field]
                            logger.info(f"model_dumpからURLを検出: {gv_key}.{field}={url}")
                            return url, f"dump_{field}"
        except Exception as e:
            logger.warning(f"model_dumpからのデータ取得に失敗: {str(e)}")
    
    # 4. ネストされた構造を探索
    for attr_name in ['generated_voice', 'generatedVoice']:
        if hasattr(response, attr_name):
            attr_value = getattr(response, attr_name)
            if isinstance(attr_value, dict):
                # 主要なネスト構造を探索
                for nested_key in ['audioData', 'data']:
                    if nested_key in attr_value and isinstance(attr_value[nested_key], dict):
                        nested = attr_value[nested_key]
                        logger.debug(f"{nested_key} keys: {list(nested.keys())}")
                        
                        for field in url_fields:
                            if field in nested and nested[field]:
                                url = nested[field]
                                logger.info(f"ネスト構造からURLを検出: {nested_key}.{field}={url}")
                                return url, f"{nested_key}.{field}"
                
                # その他のネスト構造を探索
                for key, value in attr_value.items():
                    if isinstance(value, dict):
                        for field in url_fields:
                            if field in value and value[field]:
                                url = value[field]
                                logger.info(f"その他のネスト構造からURLを検出: {key}.{field}={url}")
                                return url, f"{key}.{field}"
    
    # URLが見つからなかった場合
    logger.warning("レスポンスから音声URLを検出できませんでした")
    return None, None

def save_base64_to_file(encoded_data: str, file_format: str = "mp3") -> Tuple[Optional[str], Optional[str]]:
    """Base64エンコードされたデータを一時ファイルに保存し、ファイルパスとURLを返す"""
    # 一時ファイルの作成
    fd, temp_path = tempfile.mkstemp(suffix=f".{file_format}")
    
    try:
        # Base64データの前処理
        # //で始まる場合は特殊なフォーマットなので修正
        processed_data = encoded_data
        if encoded_data.startswith("//"):
            logger.debug("特殊な形式のBase64データを検出しました。修正を試みます。")
            # よく使われる置換パターンを試す
            processed_data = encoded_data.replace('-', '+').replace('_', '/')
            # パディングの修正
            padding = 4 - (len(processed_data) % 4) if len(processed_data) % 4 else 0
            processed_data += "=" * padding
        
        # デコード処理を実行
        try:
            logger.debug(f"Base64デコードを実行します。データ長: {len(processed_data)}")
            decoded_data = base64.b64decode(processed_data)
            logger.debug(f"デコード成功: {len(decoded_data)} バイト")
            with os.fdopen(fd, 'wb') as f:
                f.write(decoded_data)
        except base64.binascii.Error as e:
            # 標準的なデコードに失敗した場合は、異なる方法を試す
            logger.warning(f"標準的なBase64デコードに失敗しました: {str(e)}")
            if "Incorrect padding" in str(e):
                try:
                    padded_data = processed_data + "=="  # 最大パディングを追加
                    decoded_data = base64.b64decode(padded_data)
                    logger.debug(f"パディング追加後のデコード成功: {len(decoded_data)} バイト")
                    with os.fdopen(fd, 'wb') as f:
                        f.write(decoded_data)
                except Exception as e2:
                    raise Exception(f"パディング追加後もBase64デコードに失敗しました: {str(e2)}")
            else:
                raise
                
        # 絶対URLに変換
        file_name = os.path.basename(temp_path)
        full_url = f"{FILE_SERVER_URL}/{file_name}"
        
        logger.info(f"Base64データをファイルに保存しました: {temp_path}, URL: {full_url}")
        return temp_path, full_url
        
    except Exception as e:
        logger.error(f"音声データのデコードまたは保存に失敗しました: {str(e)}")
        os.close(fd)
        os.unlink(temp_path)
        return None, None
