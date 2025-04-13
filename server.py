import os
import tempfile
import asyncio
import logging
import httpx
import json
from typing import List, Optional, Dict, Any
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
        
        # エンコード音声APIを呼び出し（10秒のタイムアウトを設定）
        try:
            logger.info(f"APIへのリクエスト開始: voice_actor_id={voice_actor_id}, スクリプト長={len(script)}")
            try:
                response = await asyncio.wait_for(
                    client.generate_encoded_voice(voice_actor_id, request), 
                    timeout=10.0
                )
                logger.info("APIリクエスト成功: レスポンス取得")
            except asyncio.TimeoutError:
                logger.error("APIリクエストがタイムアウトしました（10秒）")
                raise ValueError("APIリクエストが10秒でタイムアウトしました。サーバーの負荷が高いか、ネットワークの問題が発生しています。")
            
            # レスポンス全体をログに出力（デバッグ目的）
            logger.debug(f"API Response structure: {response.model_dump()}")
            
            # より詳細なレスポンス解析を追加
            if hasattr(response, 'generated_voice'):
                if isinstance(response.generated_voice, dict):
                    logger.info(f"generated_voice keys: {list(response.generated_voice.keys())}")
                    
                    # audioFileUrl を優先的に使用
                    if "audioFileUrl" in response.generated_voice:
                        url = response.generated_voice["audioFileUrl"]
                        logger.info(f"APIレスポンスからaudioFileUrl取得: {url}")
                        result.update({
                            "audio_url": url,
                            "url_source": "api_audioFileUrl",
                            "duration": response.generated_voice.get("duration"),
                            "remaining_credits": response.generated_voice.get("remainingCredits"),
                            "message": "APIレスポンスから取得した音声URLです"
                        })
                        return result
                    
                    # audioFileDownloadUrl があれば使用
                    if "audioFileDownloadUrl" in response.generated_voice:
                        url = response.generated_voice["audioFileDownloadUrl"]
                        logger.info(f"APIレスポンスからaudioFileDownloadUrl取得: {url}")
                        result.update({
                            "audio_url": url,
                            "url_source": "api_audioFileDownloadUrl",
                            "duration": response.generated_voice.get("duration"),
                            "remaining_credits": response.generated_voice.get("remainingCredits"),
                            "message": "APIレスポンスから取得した音声ダウンロードURLです"
                        })
                        return result
                    
                    # base64Audio があれば使用（base64文字列からdata URLを生成）
                    if "base64Audio" in response.generated_voice:
                        base64_audio = response.generated_voice["base64Audio"]
                        url = f"data:audio/{format};base64," + base64_audio
                        logger.info(f"APIレスポンスからbase64Audio取得: {url}")
                        result.update({
                            "audio_url": url,
                            "url_source": "api_base64Audio",
                            "duration": response.generated_voice.get("duration"),
                            "remaining_credits": response.generated_voice.get("remainingCredits"),
                            "message": "APIレスポンスから取得した音声URL（base64）です"
                        })
                        return result

                        # 他の可能性のあるURLキーを探す（API仕様変更に対応）
                    for key in ["url", "downloadUrl", "fileUrl", "audioUrl"]:
                        if key in response.generated_voice:
                            url = response.generated_voice[key]
                            logger.info(f"APIレスポンスから代替URL({key})取得: {url}")
                            result.update({
                                "audio_url": url,
                                "url_source": f"api_{key}",
                                "duration": response.generated_voice.get("duration"),
                                "remaining_credits": response.generated_voice.get("remainingCredits"),
                                "message": f"APIレスポンスから取得した代替音声URL({key})です"
                            })
                            return result
                    
                    # audioDataフィールドがあればそこから探索（新API構造対応）
                    if "audioData" in response.generated_voice:
                        audio_data = response.generated_voice["audioData"]
                        logger.info(f"audioDataフィールドを検出しました: {type(audio_data)}")
                        
                        # audioDataが辞書の場合
                        if isinstance(audio_data, dict):
                            logger.info(f"audioData keys: {list(audio_data.keys())}")
                            # 一般的なURLキーを探す
                            for url_key in ["url", "downloadUrl", "fileUrl", "audioUrl", "audioFileUrl", "audioFileDownloadUrl"]:
                                if url_key in audio_data:
                                    url = audio_data[url_key]
                                    logger.info(f"audioDataフィールド内からURL({url_key})取得: {url}")
                                    result.update({
                                        "audio_url": url,
                                        "url_source": f"audioData_{url_key}",
                                        "duration": audio_data.get("duration") or response.generated_voice.get("duration"),
                                        "remaining_credits": response.generated_voice.get("remainingCredits"),
                                        "message": f"audioDataフィールド内から取得した音声URL({url_key})です"
                                    })
                                    return result
                        # audioDataが文字列の場合、それ自体がURLかもしれない
                        elif isinstance(audio_data, str) and (audio_data.startswith("http://") or audio_data.startswith("https://")):
                            logger.info(f"audioDataフィールドに直接URLが含まれていました: {audio_data}")
                            result.update({
                                "audio_url": audio_data,
                                "url_source": "audioData_direct",
                                "duration": response.generated_voice.get("duration"),
                                "remaining_credits": response.generated_voice.get("remainingCredits"),
                                "message": "audioDataフィールドから直接取得した音声URLです"
                            })
                            return result
                    
                    # dataフィールドがあればそこから探索（さらに新しい可能性のある構造）
                    if "data" in response.generated_voice:
                        data_field = response.generated_voice["data"]
                        logger.info(f"dataフィールドを検出しました: {type(data_field)}")
                        
                        # dataが辞書の場合
                        if isinstance(data_field, dict):
                            logger.info(f"data keys: {list(data_field.keys())}")
                            # 一般的なURLキーを探す
                            for url_key in ["url", "downloadUrl", "fileUrl", "audioUrl", "audioFileUrl", "audioFileDownloadUrl"]:
                                if url_key in data_field:
                                    url = data_field[url_key]
                                    logger.info(f"dataフィールド内からURL({url_key})取得: {url}")
                                    result.update({
                                        "audio_url": url,
                                        "url_source": f"data_{url_key}",
                                        "duration": data_field.get("duration") or response.generated_voice.get("duration"),
                                        "remaining_credits": response.generated_voice.get("remainingCredits"),
                                        "message": f"dataフィールド内から取得した音声URL({url_key})です"
                                    })
                                    return result
                        # dataが文字列の場合、それ自体がURLかもしれない
                        elif isinstance(data_field, str) and (data_field.startswith("http://") or data_field.startswith("https://")):
                            logger.info(f"dataフィールドに直接URLが含まれていました: {data_field}")
                            result.update({
                                "audio_url": data_field,
                                "url_source": "data_direct",
                                "duration": response.generated_voice.get("duration"),
                                "remaining_credits": response.generated_voice.get("remainingCredits"),
                                "message": "dataフィールドから直接取得した音声URLです"
                            })
                            return result
                    
                    # ネストされた構造を確認
                    for nested_key, value in response.generated_voice.items():
                        if isinstance(value, dict):
                            logger.info(f"Checking nested structure: {nested_key}, keys: {list(value.keys())}")
                            for url_key in ["url", "downloadUrl", "fileUrl", "audioUrl", "audioFileUrl", "audioFileDownloadUrl"]:
                                if url_key in value:
                                    url = value[url_key]
                                    logger.info(f"APIレスポンスからネストされたURL({nested_key}.{url_key})取得: {url}")
                                    result.update({
                                        "audio_url": url,
                                        "url_source": f"api_nested_{nested_key}_{url_key}",
                                        "duration": response.generated_voice.get("duration"),
                                        "remaining_credits": response.generated_voice.get("remainingCredits"),
                                        "message": f"APIレスポンスから取得したネスト構造内の音声URL({nested_key}.{url_key})です"
                                    })
                                    return result
                    
                    # URLが見つからない場合はレスポンスをダンプしてエラーを発生させる
                    logger.error("APIレスポンスにURLらしきものが見つかりませんでした。レスポンス全体をダンプします:")
                    logger.error(json.dumps(response.generated_voice, default=str))
                    raise ValueError("APIレスポンスからURLを取得できませんでした。API仕様が変更されたかエラーが発生した可能性があります。")
                else:
                    # generated_voiceが辞書でない場合
                    logger.error(f"generated_voice is not a dict: {type(response.generated_voice)}")
                    logger.error(f"generated_voice content: {response.generated_voice}")
                    raise ValueError(f"不正なAPIレスポンス形式です: generated_voice が辞書ではありません（{type(response.generated_voice)}）")
            # キャメルケースのgeneratedVoiceにも対応
            elif hasattr(response, 'generatedVoice'):
                if isinstance(response.generatedVoice, dict):
                    logger.info(f"generatedVoice keys: {list(response.generatedVoice.keys())}")
                    
                    # audioFileUrl を優先的に使用
                    if "audioFileUrl" in response.generatedVoice:
                        url = response.generatedVoice["audioFileUrl"]
                        logger.info(f"APIレスポンスからaudioFileUrl取得（キャメルケース）: {url}")
                        result.update({
                            "audio_url": url,
                            "url_source": "api_audioFileUrl_camel",
                            "duration": response.generatedVoice.get("duration"),
                            "remaining_credits": response.generatedVoice.get("remainingCredits"),
                            "message": "APIレスポンスから取得した音声URL（キャメルケース）です"
                        })
                        return result
                    
                    # audioFileDownloadUrl があれば使用
                    if "audioFileDownloadUrl" in response.generatedVoice:
                        url = response.generatedVoice["audioFileDownloadUrl"]
                        logger.info(f"APIレスポンスからaudioFileDownloadUrl取得（キャメルケース）: {url}")
                        result.update({
                            "audio_url": url,
                            "url_source": "api_audioFileDownloadUrl_camel",
                            "duration": response.generatedVoice.get("duration"),
                            "remaining_credits": response.generatedVoice.get("remainingCredits"),
                            "message": "APIレスポンスから取得した音声ダウンロードURL（キャメルケース）です"
                        })
                        return result
                else:
                    # generatedVoiceが辞書でない場合
                    logger.error(f"generatedVoice is not a dict: {type(response.generatedVoice)}")
                    logger.error(f"generatedVoice content: {response.generatedVoice}")
                    raise ValueError(f"不正なAPIレスポンス形式です: generatedVoice が辞書ではありません（{type(response.generatedVoice)}）")
            else:
                # generated_voice属性がない場合
                logger.error("Response does not have generated_voice attribute")
                logger.error(f"Response available attributes: {dir(response)}")
                raise ValueError("APIレスポンスにgenerated_voice属性がありません。API仕様が変更された可能性があります。")
            
            # model_dump()メソッドを使ってraw dictを取得してみる（Pydanticモデル対応）
            if hasattr(response, 'model_dump'):
                try:
                    raw_data = response.model_dump()
                    logger.info(f"モデルダンプからデータ取得: {list(raw_data.keys())}")
                    
                    # generatedVoiceキーを確認
                    if "generatedVoice" in raw_data and isinstance(raw_data["generatedVoice"], dict):
                        gv = raw_data["generatedVoice"]
                        logger.info(f"Raw generatedVoice keys: {list(gv.keys())}")
                        
                        if "audioFileUrl" in gv:
                            url = gv["audioFileUrl"]
                            logger.info(f"Rawデータからaudioファイルのurl: {url}")
                            result.update({
                                "audio_url": url,
                                "url_source": "raw_generatedVoice_audioFileUrl",
                                "duration": gv.get("duration"),
                                "remaining_credits": gv.get("remainingCredits"),
                                "message": "Raw APIレスポンスから取得した音声URLです"
                            })
                            return result
                        elif "audioFileDownloadUrl" in gv:
                            url = gv["audioFileDownloadUrl"]
                            logger.info(f"Rawデータからaudioファイルのダウンロードurl: {url}")
                            result.update({
                                "audio_url": url,
                                "url_source": "raw_generatedVoice_audioFileDownloadUrl",
                                "duration": gv.get("duration"),
                                "remaining_credits": gv.get("remainingCredits"),
                                "message": "Raw APIレスポンスから取得した音声ダウンロードURLです"
                            })
                            return result
                except Exception as e:
                    logger.warning(f"model_dumpからのデータ取得に失敗: {str(e)}")
        except asyncio.TimeoutError:
            # タイムアウトエラーは上でキャッチしているが、念のためここでも
            logger.error("APIリクエストがタイムアウトしました（10秒）")
            raise ValueError("APIリクエストが10秒でタイムアウトしました。サーバーの負荷が高いか、ネットワークの問題が発生しています。")
        except Exception as e:
            # エラー詳細をログに記録
            logger.error(f"エンコード音声APIからURLを取得できませんでした: {str(e)}", exc_info=True)
            logger.error(f"詳細なエラー情報: {type(e).__name__}: {str(e)}")
            
            # このエラーをそのまま上位に伝播させる（ローカルファイル生成によるフォールバック処理は行わない）
            raise ValueError(f"音声生成に失敗しました: {str(e)}")
    except Exception as e:
        # エラーメッセージを詳細に返す
        error_message = f"音声生成中にエラーが発生しました: {str(e)}"
        logger.error(error_message)
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
        
        # 10秒のタイムアウトを設定してAPIを呼び出し
        try:
            logger.info(f"APIへのリクエスト開始: voice_actor_id={voice_actor_id}, スクリプト長={len(script)}")
            response = await asyncio.wait_for(
                client.generate_encoded_voice(voice_actor_id, request),
                timeout=10.0
            )
            logger.info("APIリクエスト成功: レスポンス取得")
        except asyncio.TimeoutError:
            logger.error("APIリクエストがタイムアウトしました（10秒）")
            raise ValueError("APIリクエストが10秒でタイムアウトしました。サーバーの負荷が高いか、ネットワークの問題が発生しています。")
        
        # 異なるレスポンス形式に対応
        encoded_voice = response.get_encoded_voice()
        if encoded_voice is not None:
            # Base64データのメタ情報を返す
            data_size = len(encoded_voice)
            data_preview = encoded_voice[:30] + "..." if len(encoded_voice) > 30 else encoded_voice
            
            # APIから返されるURLを取得
            audio_url = response.get_audio_url()
            audio_duration = response.get_duration()
            remaining_credits = response.get_remaining_credits()
            
            # URLが取得できた場合はファイルに保存せずURLを返す
            if audio_url:
                logger.info(f"APIから返されたオーディオURL: {audio_url}")
                return {
                    "status": "success",
                    "voice_actor_id": voice_actor_id,
                    "format": format,
                    "data_size_bytes": data_size,
                    "data_preview": data_preview,
                    "audio_url": audio_url,
                    "duration_ms": audio_duration,
                    "script_length": len(script),
                    "remaining_credits": remaining_credits,
                    "message": f"音声生成に成功しました。サイズ: {data_size} バイト, 形式: {format}, URL: {audio_url}"
                }
            
            # URLが取得できない場合は一時ファイルに保存（従来の方法）
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
            
            return {
                "status": "success",
                "voice_actor_id": voice_actor_id,
                "format": format,
                "data_size_bytes": data_size,
                "data_preview": data_preview,
                "file_path": temp_path,
                "file_url": full_url,  # URLを追加
                "script_length": len(script),
                "generation_time": response.generation_time if hasattr(response, 'generation_time') else None,
                "message": f"音声生成に成功しました。サイズ: {data_size} バイト, 形式: {format}, URL: {full_url}"
            }
        else:
            # デバッグ情報をログに出力
            logger.debug(f"Response object: {response}")
            if response.generated_voice:
                logger.debug(f"generated_voice content: {response.generated_voice}")
            
            # エラーが発生した場合
            raise ValueError("エンコード音声を取得できませんでした。APIのレスポンス構造が変わった可能性があります。ログファイル(nijivoice_mcp.log)を確認してください。")
    except asyncio.TimeoutError:
        # タイムアウトエラーは上でキャッチしているが、念のためここでも
        error_message = "APIリクエストが10秒でタイムアウトしました。サーバーの負荷が高いか、ネットワークの問題が発生しています。"
        logger.error(error_message)
        raise ValueError(error_message)
    except Exception as e:
        # エラーメッセージを詳細に返す
        error_message = f"音声生成中にエラーが発生しました: {str(e)}"
        logger.error(error_message)
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
