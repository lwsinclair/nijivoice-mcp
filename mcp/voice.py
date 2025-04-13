import json
import logging
import httpx
import asyncio
from typing import Dict, Optional
from fastmcp import FastMCP, Context

from nijivoice.api import NijiVoiceClient
from nijivoice.models import VoiceGenerationRequest
from utils.retry import retry_async
from utils.audio import calculate_timeout, extract_audio_url_from_response
from utils.error_handling import handle_exceptions
import config

# ロガーの設定
logger = logging.getLogger('nijivoice_mcp.mcp.voice')

# APIクライアントの初期化
client = NijiVoiceClient(api_key=config.API_KEY)

# 音声生成用のMCPインスタンス
voice_mcp = FastMCP("NijiVoice Voice Generation")

@voice_mcp.tool(name="generate_voice")
@handle_exceptions
async def generate_voice(
    ctx: Context,
    script: str,
    voice_actor_id: str = config.DEFAULT_VOICE_ACTOR_ID,
    speed: float = 1.0,
    emotional_level: Optional[float] = None,
    sound_duration: Optional[float] = None,
    format: str = "mp3",
) -> Dict:
    """
    指定されたVoice Actorの声で音声を生成します。
    
    Args:
        script: 読み上げるテキスト（必須）
        voice_actor_id: Voice Actor ID
        speed: 読み上げのスピード（0.4〜3.0、デフォルト: 1.0）
        emotional_level: 感情レベル（0〜1.5、未指定の場合は0.1）
        sound_duration: 音素発音の長さ（0〜1.7、未指定の場合は0.1）
        format: 音声フォーマット（"mp3"または"wav"）
    
    Returns:
        音声生成結果の情報（ファイルのURLやメタデータを含む辞書）
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
        await ctx.info(f"APIリクエストを開始します: voice_actor_id={voice_actor_id}, スクリプト長={len(script)}文字")
        await ctx.report_progress(0, 100)  # 進捗状況を報告
        
        # リトライ付きAPIリクエスト
        try:
            await ctx.info(f"APIへリクエストを送信中... タイムアウト={timeout}秒")
            audio_url = await retry_async(
                client.get_voice_url,
                voice_actor_id,
                request,
                max_retries=config.MAX_RETRIES,
                base_delay=config.BASE_RETRY_DELAY
            )
            await ctx.info("APIリクエスト成功: URL取得完了")
            await ctx.report_progress(100, 100)  # 完了
            
            # URLが取得できた場合は必ずそれを使用
            if audio_url:
                await ctx.info(f"Audio URL: {audio_url}")
                result.update({
                    "audio_url": audio_url,
                    "url_source": "direct_api_call",
                    "message": "APIから直接取得した音声URLです"
                })
                return result
            
            # URLが取得できなかった場合
            error_message = "get_voice_urlからURLを取得できませんでした"
            await ctx.error(error_message)
            logger.error(error_message)
            raise ValueError(f"音声生成中にエラーが発生しました: APIから音声URLを取得できませんでした")
            
        except (httpx.TimeoutException, asyncio.TimeoutError) as e:
            # タイムアウトエラー
            error_message = f"APIリクエストがタイムアウトしました: {str(e)}"
            await ctx.error(error_message)
            logger.error(error_message)
            raise ValueError(f"APIリクエストがタイムアウトしました。サーバーの負荷が高いか、スクリプトが長すぎる可能性があります。")
        except Exception as e:
            # その他のエラー
            error_message = f"APIリクエスト中にエラーが発生しました: {str(e)}"
            await ctx.error(error_message)
            logger.error(error_message, exc_info=True)
            raise ValueError(f"音声生成に失敗しました: {str(e)}")
    except Exception as e:
        # エラーメッセージを詳細に返す
        error_message = f"音声生成中にエラーが発生しました: {str(e)}"
        await ctx.error(error_message)
        logger.error(error_message, exc_info=True)
        raise ValueError(error_message)

@voice_mcp.tool(name="generate_encoded_voice")
@handle_exceptions
async def generate_encoded_voice(
    ctx: Context,
    script: str,
    voice_actor_id: str = config.DEFAULT_VOICE_ACTOR_ID,
    speed: float = 1.0,
    emotional_level: Optional[float] = None,
    sound_duration: Optional[float] = None,
    format: str = "mp3",
) -> Dict:
    """
    指定されたVoice Actorの声でBase64エンコードされた音声を生成します。
    
    Args:
        script: 読み上げるテキスト（必須）
        voice_actor_id: Voice Actor ID
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
        await ctx.info(f"APIリクエストを開始します: voice_actor_id={voice_actor_id}, スクリプト長={len(script)}文字")
        await ctx.report_progress(0, 100)  # 進捗状況を報告
        
        # リトライ機能付きAPIリクエスト
        try:
            await ctx.info(f"APIへリクエストを送信中... タイムアウト={timeout}秒")
            response = await retry_async(
                client.generate_encoded_voice,
                voice_actor_id,
                request,
                max_retries=config.MAX_RETRIES,
                base_delay=config.BASE_RETRY_DELAY
            )
            await ctx.info("APIリクエスト成功: レスポンス取得完了")
            await ctx.report_progress(80, 100)  # 80%完了
            
            # レスポンスの生データをダンプしてデバッグ
            if hasattr(response, 'model_dump'):
                try:
                    raw_model = response.model_dump()
                    logger.debug(f"Model dump: {json.dumps(raw_model, default=str)[:1000]}")
                except Exception as e:
                    logger.debug(f"Model dump failed: {str(e)}")

            # URLを検索
            audio_url, url_field = None, None
            # EncodedVoiceResponseの新メソッドを使用
            if hasattr(response, 'get_audio_url_first'):
                audio_url, url_field = response.get_audio_url_first()
                if audio_url:
                    logger.info(f"Direct URL found in response: {url_field}={audio_url}")
                    await ctx.info(f"レスポンスから直接URLを検出: {url_field}")

            # URLが見つからない場合はヘルパー関数で検索
            if not audio_url:
                audio_url, url_field = await extract_audio_url_from_response(response)
                if audio_url:
                    logger.info(f"URL found via helper: {url_field}={audio_url}")
                    await ctx.info(f"ヘルパー関数でURLを検出: {url_field}")

            # URLが見つかった場合は必ずそれを使用
            if audio_url:
                await ctx.info(f"検出したURL: {audio_url}")
                await ctx.report_progress(100, 100)  # 完了
                
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
                return result
            else:
                # エラーが発生した場合
                error_message = "エンコード音声を取得できませんでした。APIのレスポンス構造が変わった可能性があります。"
                await ctx.error(error_message)
                raise ValueError(f"{error_message} ログファイル(nijivoice_mcp.log)を確認してください。")
        except (httpx.TimeoutException, asyncio.TimeoutError) as e:
            # タイムアウトエラー
            error_message = f"APIリクエストがタイムアウトしました: {str(e)}"
            await ctx.error(error_message)
            logger.error(error_message)
            raise ValueError(f"{error_message} サーバーの負荷が高いか、スクリプトが長すぎる可能性があります。")
        except Exception as e:
            # エラーメッセージを詳細に返す
            error_message = f"音声生成中にエラーが発生しました: {str(e)}"
            await ctx.error(error_message)
            logger.error(error_message, exc_info=True)
            raise ValueError(error_message)
    except Exception as e:
        # エラーメッセージを詳細に返す
        error_message = f"音声生成中にエラーが発生しました: {str(e)}"
        await ctx.error(error_message)
        logger.error(error_message, exc_info=True)
        raise ValueError(error_message)