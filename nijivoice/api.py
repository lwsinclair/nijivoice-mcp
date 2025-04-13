import os
import httpx
import logging
from typing import List, Optional, Union, BinaryIO
import base64
from .models import VoiceActor, VoiceGenerationRequest, EncodedVoiceResponse, Balance
from .exceptions import NijiVoiceAPIError

# ロガーの設定
logger = logging.getLogger('nijivoice_mcp.api')

class NijiVoiceClient:
    """にじボイスAPIクライアント"""
    
    BASE_URL = "https://api.nijivoice.com/api/platform/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: APIキー。指定しない場合は環境変数 NIJIVOICE_API_KEY から読み込みます。
        """
        self.api_key = api_key or os.environ.get("NIJIVOICE_API_KEY")
        if not self.api_key:
            raise ValueError("APIキーが指定されていません。引数で指定するか、NIJIVOICE_API_KEY 環境変数を設定してください。")
        
        self.headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json",
        }
    
    async def get_voice_actors(self) -> List[VoiceActor]:
        """
        利用可能なVoice Actorの一覧を取得します。
        
        Returns:
            Voice Actorのリスト
        """
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.BASE_URL}/voice-actors", headers=self.headers)
            
            if response.status_code != 200:
                raise NijiVoiceAPIError(f"Voice Actor一覧の取得に失敗しました: {response.text}", status_code=response.status_code)
            
            data = response.json()
            # APIがvoiceActorsキーの中に配列を返す場合の対応
            actors_data = data.get("voiceActors", data)
            if not isinstance(actors_data, list):
                # データがリストでない場合の対処
                raise NijiVoiceAPIError(f"予期しないデータ形式です: {data}", status_code=response.status_code)
                
            return [VoiceActor.model_validate(actor) for actor in actors_data]
    
    async def generate_voice(
        self, 
        voice_actor_id: str, 
        request: VoiceGenerationRequest,
    ) -> bytes:
        """
        指定されたVoice Actorの声で音声を生成します。
        
        Args:
            voice_actor_id: Voice Actor ID
            request: 音声生成リクエスト
            
        Returns:
            生成された音声データ（バイナリ）
        """
        url = f"{self.BASE_URL}/voice-actors/{voice_actor_id}/generate-voice"
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url, 
                headers=self.headers,
                json=request.model_dump(by_alias=True),
            )
            
            if response.status_code != 200:
                raise NijiVoiceAPIError(f"音声生成に失敗しました: {response.text}", status_code=response.status_code)
            
            data = response.json()
            logger.debug("generate_voice API response: %s", data)
            generated_voice = data.get("generatedVoice", {})
            file_url = (generated_voice.get("audioFileUrl") or 
                        generated_voice.get("audioFileDownloadUrl") or 
                        generated_voice.get("url") or 
                        data.get("audioUrl"))
            
            if not file_url:
                raise NijiVoiceAPIError("音声生成中にエラーが発生しました: APIレスポンスからURLを取得できませんでした。レスポンス: " + str(data))
            
            file_response = await client.get(file_url)
            if file_response.status_code != 200:
                raise NijiVoiceAPIError(f"音声ファイルのダウンロードに失敗しました: {file_response.text}", status_code=file_response.status_code)
            
            return file_response.content
    
    async def generate_encoded_voice(
        self, 
        voice_actor_id: str, 
        request: VoiceGenerationRequest,
    ) -> EncodedVoiceResponse:
        """
        指定されたVoice Actorの声でBase64エンコードされた音声を生成します。
        
        Args:
            voice_actor_id: Voice Actor ID
            request: 音声生成リクエスト
            
        Returns:
            Base64エンコードされた音声データ
        """
        url = f"{self.BASE_URL}/voice-actors/{voice_actor_id}/generate-encoded-voice"
        
        # タイムアウト時間を長く設定（30秒など）またはタイムアウトを指定しない
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url, 
                headers=self.headers,
                json=request.model_dump(by_alias=True),
            )
            
            if response.status_code != 200:
                raise NijiVoiceAPIError(f"エンコード音声生成に失敗しました: {response.text}", status_code=response.status_code)
            
            data = response.json()
            
            # デバッグ用にレスポンス構造をログに出力
            logger.debug(f"API Response structure: {data.keys()}")
            logger.debug(f"API Response full content: {data}")
            
            # ユーザーが提供した具体例の構造かどうかを確認
            if "generatedVoice" in data and isinstance(data["generatedVoice"], dict):
                if "audioFileUrl" in data["generatedVoice"] or "audioFileDownloadUrl" in data["generatedVoice"]:
                    logger.info("APIレスポンスから直接audioFileUrl/audioFileDownloadUrlを持つgeneratedVoiceを検出しました")
            
            # モデル検証
            resp = EncodedVoiceResponse.model_validate(data)
            
            # レスポンス形式に応じて適切なエンコード音声を取得
            encoded_voice = resp.get_encoded_voice()
            if encoded_voice:
                resp.encoded_voice = encoded_voice
                return resp
            else:
                # レスポンス構造をログに出力して診断を容易にする
                logger.error(f"Unexpected response structure: {data}")
                
                # それでも何もなければ、そのままのデータを返す（フォールバック）
                logger.warning("レスポンス検証に失敗しましたが、生のレスポンスでEncodedVoiceResponseを構築します")
                return EncodedVoiceResponse(generated_voice=data)
    
    async def get_balance(self) -> Balance:
        """
        クレジット残高を取得します。
        
        Returns:
            クレジット残高
        """
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.BASE_URL}/balances", headers=self.headers)
            
            if response.status_code != 200:
                raise NijiVoiceAPIError(f"クレジット残高の取得に失敗しました: {response.text}", status_code=response.status_code)
            
            data = response.json()
            # APIレスポンスの構造をログに出力
            logger.debug(f"Balance API response: {data}")
            
            # モデル検証
            balance = Balance.model_validate(data)
            return balance
