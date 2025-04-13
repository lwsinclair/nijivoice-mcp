import os
import tempfile
import asyncio
import logging
import httpx
import json
from typing import List, Optional, Dict, Any, Tuple
from fastmcp import FastMCP, Context
from nijivoice.api import NijiVoiceClient
from nijivoice.models import VoiceGenerationRequest, VoiceActor, Balance
from dotenv import load_dotenv

# ロギングの設定
logging.basicConfig(
    filename='nijivoice_mcp.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('nijivoice_mcp')


# APIキーの取得
load_dotenv()
api_key = os.environ.get("NIJIVOICE_API_KEY")
if not api_key:
    raise ValueError("NIJIVOICE_API_KEY 環境変数を設定してください。")

# APIクライアントの初期化
client = NijiVoiceClient(api_key=api_key)

# MCPサーバーの作成
mcp = FastMCP("NijiVoice MCP")

# タイムアウト時間をスクリプトの長さに応じて動的に設定
def calculate_timeout(script_length, base_timeout=30.0, char_factor=0.01):
    """スクリプトの長さに応じたタイムアウト時間を計算"""
    # 基本のタイムアウト + スクリプトの長さに応じた追加時間
    # 例: 1000文字のスクリプトなら、base_timeout + 10秒
    return min(base_timeout + (script_length * char_factor), 120.0)  # 最大2分

async def retry_async(func, *args, max_retries=3, base_delay=2.0, **kwargs):
    """非同期関数のリトライ処理を行うヘルパー関数"""
    retries = 0
    last_exception = None
    
    while retries < max_retries:
        try:
            return await func(*args, **kwargs)
        except (httpx.TimeoutException, asyncio.TimeoutError) as e:
            last_exception = e
            retries += 1
            logger.warning(f"リトライ {retries}/{max_retries}: {str(e)}")
            
            if retries < max_retries:
                # 指数バックオフ（リトライごとに待機時間を増加）
                wait_time = base_delay * (2 ** (retries - 1))
                logger.info(f"{wait_time}秒後にリトライします...")
                await asyncio.sleep(wait_time)
    
    # 最大リトライ回数に達した場合
    logger.error(f"最大リトライ回数（{max_retries}回）に達しました: {str(last_exception)}")
    raise last_exception

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

@mcp.tool(name="get_voice_actors")
async def get_voice_actors() -> List[VoiceActor]:
    """
    利用可能なVoice Actorの一覧を取得します。
    
    Returns:
        Voice Actorのリスト
    """
    try:
        return await client.get_voice_actors()
    except Exception as e:
        # エラーメッセージを詳細に返す
        error_message = f"Voice Actor一覧の取得中にエラーが発生しました: {str(e)}"
        logger.error(error_message)
        raise ValueError(error_message)

@mcp.tool(name="generate_voice")
async def generate_voice(
    ctx: Context,
    script: str,
    voice_actor_id: str = "90031163-c497-44f3-a8a6-e45e4d0cb8f6",  # デフォルトのVoice Actor ID
    speed: float = 1.0,  # デフォルト値を追加
    emotional_level: Optional[float] = None,
    sound_duration: Optional[float] = None,
    format: str = "mp3",
) -> dict:
    """
    指定されたVoice Actorの声で音声を生成します。
    
    Args:
        script: 読み上げるテキスト（必須）
        voice_actor_id: Voice Actor ID（デフォルト: 90031163-c497-44f3-a8a6-e45e4d0cb8f6）
        speed: 読み上げのスピード（0.4〜3.0、デフォルト: 1.0）
        emotional_level: 感情レベル（0〜1.5、未指定の場合は0.1）
        sound_duration: 音素発音の長さ（0〜1.7、未指定の場合は0.1）
        format: 音声フォーマット（"mp3"または"wav"）
    
    Returns:
        音声生成結果の情報（ファイルのURLやメタデータを含む辞書）
        
    Raises:
        ValueError: APIからURLを取得できない場合
    """
    try:
        # パラメータのデフォルト値を設定
        if emotional_level is None:
            emotional_level = 0.1
        if sound_duration is None:
            sound_duration = 0.1
            
        request = VoiceGenerationRequest(
            script=script,
            speed=speed,
            emotional_level=emotional_level,
            sound_duration=sound_duration,
            format=format,
        )
        
        # 基本的なレスポンス構造を準備
        result = {
            "status": "success",
            "script": script,
            "format": format,
            "voice_actor_id": voice_actor_id,
            "file_type": f"audio/{format}"
        }
        
        # スクリプトの長さに応じたタイムアウト時間の計算
        timeout = calculate_timeout(len(script))
        logger.info(f"APIリクエスト開始: voice_actor_id={voice_actor_id}, スクリプト長={len(script)}, タイムアウト={timeout}秒")
        
        # リトライ付きAPIリクエスト - get_voice_urlを使用
        try:
            # get_voice_urlメソッドを呼び出す
            logger.info(f"APIへのリクエスト開始: voice_actor_id={voice_actor_id}, スクリプト長={len(script)}")
            audio_url = await retry_async(
                client.get_voice_url,
                voice_actor_id,
                request,
                max_retries=3,
                base_delay=2.0
            )
            logger.info("APIリクエスト成功: URL取得")
            
            # URLが取得できた場合は必ずそれを使用
            if audio_url:
                logger.info(f"Using audio URL from direct API call: {audio_url}")
                result.update({
                    "audio_url": audio_url,
                    "url_source": "direct_api_call",
                    "message": "APIから直接取得した音声URLです"
                })
                return result  # ここで早期リターン
            
            # URLが取得できなかった場合（通常はここに到達しない）
            logger.error("get_voice_urlからURLを取得できませんでした")
            raise ValueError("音声生成中にエラーが発生しました: APIから音声URLを取得できませんでした")
            
            raise ValueError("APIレスポンスから音声データを取得できませんでした。API仕様が変更された可能性があります。")
            
        except (httpx.TimeoutException, asyncio.TimeoutError) as e:
            # タイムアウトエラー
            logger.error(f"APIリクエストがタイムアウトしました: {str(e)}")
            raise ValueError(f"APIリクエストがタイムアウトしました。サーバーの負荷が高いか、スクリプトが長すぎる可能性があります。")
        except Exception as e:
            # その他のエラー
            logger.error(f"APIリクエスト中にエラーが発生しました: {str(e)}", exc_info=True)
            raise ValueError(f"音声生成に失敗しました: {str(e)}")
    except Exception as e:
        # エラーメッセージを詳細に返す
        error_message = f"音声生成中にエラーが発生しました: {str(e)}"
        logger.error(error_message, exc_info=True)
        raise ValueError(error_message)

@mcp.tool(name="generate_encoded_voice")
async def generate_encoded_voice(
    ctx: Context,
    script: str,
    voice_actor_id: str = "90031163-c497-44f3-a8a6-e45e4d0cb8f6",  # デフォルトのVoice Actor ID
    speed: float = 1.0,  # デフォルト値を追加
    emotional_level: Optional[float] = None,
    sound_duration: Optional[float] = None,
    format: str = "mp3",
) -> dict:
    """
    指定されたVoice Actorの声でBase64エンコードされた音声を生成します。
    
    Args:
        script: 読み上げるテキスト（必須）
        voice_actor_id: Voice Actor ID（デフォルト: 90031163-c497-44f3-a8a6-e45e4d0cb8f6）
        speed: 読み上げのスピード（0.4〜3.0、デフォルト: 1.0）
        emotional_level: 感情レベル（0〜1.5、未指定の場合は0.1）
        sound_duration: 音素発音の長さ（0〜1.7、未指定の場合は0.1）
        format: 音声フォーマット（"mp3"または"wav"）
    
    Returns:
        音声生成結果の情報（音声データのサイズやプレビューなど）
    """
    try:
        # パラメータのデフォルト値を設定
        if emotional_level is None:
            emotional_level = 0.1
        if sound_duration is None:
            sound_duration = 0.1
            
        request = VoiceGenerationRequest(
            script=script,
            speed=speed,
            emotional_level=emotional_level,
            sound_duration=sound_duration,
            format=format,
        )
        
        # スクリプトの長さに応じたタイムアウト時間の計算
        timeout = calculate_timeout(len(script))
        logger.info(f"APIリクエスト開始: voice_actor_id={voice_actor_id}, スクリプト長={len(script)}, タイムアウト={timeout}秒")
        
        # リトライ機能付きAPIリクエスト
        try:
            response = await retry_async(
                client.generate_encoded_voice,
                voice_actor_id,
                request,
                max_retries=3,
                base_delay=2.0
            )
            logger.info("APIリクエスト成功: レスポンス取得")
            
            # レスポンスの生データをダンプしてデバッグ
            logger.debug(f"==== API RESPONSE DEBUG ====")
            if hasattr(response, 'model_dump'):
                try:
                    raw_model = response.model_dump()
                    logger.debug(f"Model dump: {json.dumps(raw_model, default=str)[:1000]}")
                except Exception as e:
                    logger.debug(f"Model dump failed: {str(e)}")

            if hasattr(response, 'generated_voice'):
                logger.debug(f"Generated voice: {type(response.generated_voice)}")
                if isinstance(response.generated_voice, dict):
                    logger.debug(f"Generated voice keys: {list(response.generated_voice.keys())}")
            logger.debug(f"==== END API RESPONSE DEBUG ====")

            # EncodedVoiceResponseの新メソッドを使用してURLを取得
            audio_url, url_field = None, None
            if hasattr(response, 'get_audio_url_first'):
                audio_url, url_field = response.get_audio_url_first()
                if audio_url:
                    logger.info(f"Direct URL found in response: {url_field}={audio_url}")

            # URLが見つからない場合はヘルパー関数で検索
            if not audio_url:
                audio_url, url_field = await extract_audio_url_from_response(response)
                if audio_url:
                    logger.info(f"URL found via helper: {url_field}={audio_url}")

            # URLが見つかった場合は必ずそれを使用
            if audio_url:
                logger.info(f"Using audio URL: {url_field}={audio_url}")
                # 基本的なレスポンス構造を準備
                result = {
                    "status": "success",
                    "script": script,
                    "format": format,
                    "voice_actor_id": voice_actor_id,
                    "file_type": f"audio/{format}"
                }
                result.update({
                    "audio_url": audio_url,
                    "url_source": url_field,
                    "duration": (
                        response.generated_voice.get("duration") 
                        if hasattr(response, 'generated_voice') 
                        else getattr(response, 'generatedVoice', {}).get("duration")
                    ),
                    "remaining_credits": (
                        response.generated_voice.get("remainingCredits") 
                        if hasattr(response, 'generated_voice') 
                        else getattr(response, 'generatedVoice', {}).get("remainingCredits")
                    ),
                    "message": f"APIレスポンスから取得した音声URL（{url_field}）です"
                })
                return result  # ここで早期リターン
                
                # URLが無い場合はbase64データを使用
                # 一時ファイルに保存する処理は残しておく
                fd, temp_path = tempfile.mkstemp(suffix=f".{format}")
                try:
                    import base64
                    
                    # Base64データの前処理
                    # //で始まる場合は特殊なフォーマットなので修正
                    processed_data = encoded_voice
                    if encoded_voice.startswith("//"):
                        logger.debug("特殊な形式のBase64データを検出しました。修正を試みます。")
                        # よく使われる置換パターンを試す
                        processed_data = encoded_voice.replace('-', '+').replace('_', '/')
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
                except Exception as e:
                    logger.error(f"音声データのデコードまたは保存に失敗しました: {str(e)}")
                    os.close(fd)
                    os.unlink(temp_path)
                    temp_path = None
                
                # 絶対URLに変換
                base_url = os.environ.get("NIJIVOICE_FILE_SERVER_URL", "http://localhost:8000/files")
                file_name = os.path.basename(temp_path) if temp_path else None
                full_url = f"{base_url}/{file_name}" if file_name else None
                
                if full_url:
                    logger.info(f"生成された音声ファイル: {file_name}, URL: {full_url}")
                
                result.update({
                    "file_path": temp_path,
                    "file_url": full_url,  # URLを追加
                    "message": f"音声生成に成功しました。サイズ: {data_size} バイト, 形式: {format}, URL: {full_url}"
                })
                return result
            else:
                # デバッグ情報をログに出力
                logger.debug(f"Response object: {response}")
                if hasattr(response, 'generated_voice') and response.generated_voice:
                    logger.debug(f"generated_voice content: {response.generated_voice}")
                
                # エラーが発生した場合
                raise ValueError("エンコード音声を取得できませんでした。APIのレスポンス構造が変わった可能性があります。ログファイル(nijivoice_mcp.log)を確認してください。")
        except (httpx.TimeoutException, asyncio.TimeoutError) as e:
            # タイムアウトエラー
            error_message = f"APIリクエストがタイムアウトしました: {str(e)}。サーバーの負荷が高いか、スクリプトが長すぎる可能性があります。"
            logger.error(error_message)
            raise ValueError(error_message)
        except Exception as e:
            # エラーメッセージを詳細に返す
            error_message = f"音声生成中にエラーが発生しました: {str(e)}"
            logger.error(error_message, exc_info=True)
            raise ValueError(error_message)
    except Exception as e:
        # エラーメッセージを詳細に返す
        error_message = f"音声生成中にエラーが発生しました: {str(e)}"
        logger.error(error_message, exc_info=True)
        raise ValueError(error_message)

@mcp.tool(name="get_credit_balance")
async def get_credit_balance() -> int:
    """
    クレジット残高を取得します。
    
    Returns:
        クレジット残高
    """
    try:
        balance = await client.get_balance()
        # バリエーションに対応したクレジット取得
        return balance.get_credit()
    except Exception as e:
        # エラーメッセージを詳細に返す
        error_message = f"クレジット残高の取得中にエラーが発生しました: {str(e)}"
        logger.error(error_message)
        raise ValueError(error_message)

@mcp.resource("voice-actors://list", name="voice_actors_resource")
async def voice_actors_resource() -> List[VoiceActor]:
    """利用可能なVoice Actorの一覧"""
    try:
        return await client.get_voice_actors()
    except Exception as e:
        logger.error(f"Voice Actor一覧リソースの取得中にエラーが発生しました: {str(e)}")
        return []  # エラー時は空リストを返す

@mcp.resource("voice-actors://{voice_actor_id}", name="voice_actor_resource")
async def voice_actor_resource(voice_actor_id: str) -> Optional[VoiceActor]:
    """指定されたIDのVoice Actor"""
    try:
        actors = await client.get_voice_actors()
        for actor in actors:
            if actor.id == voice_actor_id:
                return actor
        return None
    except Exception as e:
        logger.error(f"Voice Actor(ID: {voice_actor_id})リソースの取得中にエラーが発生しました: {str(e)}")
        return None

@mcp.resource("credit://balance", name="credit_balance_resource")
async def credit_balance_resource() -> Balance:
    """クレジット残高"""
    try:
        return await client.get_balance()
    except Exception as e:
        logger.error(f"クレジット残高リソースの取得中にエラーが発生しました: {str(e)}")
        # エラー時はダミーの残高を返す（0クレジット）
        return Balance(balance=0)

@mcp.prompt(name="voice_generation_prompt")
def voice_generation_prompt() -> str:
    """音声生成のためのプロンプト"""
    return """
    # にじボイス音声生成

    にじボイスAPIを使用して音声を生成します。

    ## 使用可能なVoice Actor
    利用可能なVoice Actorの一覧を取得するには `get_voice_actors` ツールを使用してください。

    ## 音声生成
    音声を生成するには以下のパラメータを指定します：

    - `script`: 読み上げるテキスト（最大3,000文字）（必須）
    - `voice_actor_id`: Voice Actor ID（デフォルト: 90031163-c497-44f3-a8a6-e45e4d0cb8f6）
    - `speed`: 読み上げのスピード（0.4〜3.0、デフォルト: 1.0）
    - `emotional_level`: 感情レベル（0〜1.5、未指定の場合は0.1）
    - `sound_duration`: 音素発音の長さ（0〜1.7、未指定の場合は0.1）
    - `format`: 音声フォーマット（"mp3"または"wav"、デフォルトは"mp3"）

    ## 特殊タグ
    scriptには以下の特殊タグを含めることができます：

    - `<sp 1.0>xxx</sp>`: タグ内のテキストのスピードを変更します。
    - `<wait 0.3>`: 指定した秒数の間を挿入します。

    ## 利用可能な関数
    - `get_voice_actors()`: 利用可能なVoice Actorの一覧を取得
    - `generate_voice(script, voice_actor_id="90031163-c497-44f3-a8a6-e45e4d0cb8f6", speed=1.0, emotional_level=None, sound_duration=None, format="mp3")`: 音声ファイル生成。構造化されたレスポンス（音声ファイルのURL、フォーマット、ファイルタイプなどの情報を含む）を返します。
    - `generate_encoded_voice(script, voice_actor_id="90031163-c497-44f3-a8a6-e45e4d0cb8f6", speed=1.0, emotional_level=None, sound_duration=None, format="mp3")`: 音声データの生成。音声サイズなどのメタ情報と音声ファイルのURLを返します。
    - `get_credit_balance()`: クレジット残高取得

    ## 例
    ```
    こんにちは、<wait 0.5>これは<sp 0.8>テスト</sp>です。
    ```

    ## エラー処理
    - APIエラーが発生した場合は詳細なエラーメッセージが返されます
    - レスポンス形式が変更された場合も自動的に対応します
    - エラー発生時はログにエラー詳細が出力されます
    """

if __name__ == "__main__":
    mcp.run()
