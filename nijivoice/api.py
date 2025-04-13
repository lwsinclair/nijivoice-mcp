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
    
    def __init__(self, api_key: Optional[str] = None, timeout: Optional[float] = 30.0):
        """
        初期化
        
        Args:
            api_key: APIキー。指定しない場合は環境変数 NIJIVOICE_API_KEY から読み込みます。
            timeout: HTTPリクエストのタイムアウト時間（秒）
        """
        self.api_key = api_key or os.environ.get("NIJIVOICE_API_KEY")
        if not self.api_key:
            raise ValueError("APIキーが指定されていません。引数で指定するか、NIJIVOICE_API_KEY 環境変数を設定してください。")
        
        self.timeout = timeout
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
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
    
    async def get_voice_url(
        self, 
        voice_actor_id: str, 
        request: VoiceGenerationRequest,
    ) -> str:
        """
        指定されたVoice Actorの声で生成される音声ファイルのURLを取得します。
        
        Args:
            voice_actor_id: Voice Actor ID
            request: 音声生成リクエスト
            
        Returns:
            音声ファイルのURL
        """
        url = f"{self.BASE_URL}/voice-actors/{voice_actor_id}/generate-voice"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url, 
                headers=self.headers,
                json=request.model_dump(by_alias=True),
            )
            
            if response.status_code != 200:
                raise NijiVoiceAPIError(f"音声生成に失敗しました: {response.text}", status_code=response.status_code)
            
            data = response.json()
            logger.debug(f"get_voice_url API response: {data}")
            
            # URLを抽出する共通関数を使用
            file_url = self._extract_url_from_response(data)
            
            if not file_url:
                raise NijiVoiceAPIError("音声生成中にエラーが発生しました: APIレスポンスからURLを取得できませんでした。レスポンス: " + str(data))
            
            return file_url
            
    def _extract_url_from_response(self, data: dict) -> str:
        """レスポンスから音声URLを抽出する共通関数"""
        if not data:
            return None
            
        # generatedVoiceオブジェクト内を検索
        generated_voice = data.get("generatedVoice", {})
        
        # 優先順位順にURLを検索
        for field in ["audioFileUrl", "audioFileDownloadUrl", "url", "downloadUrl", "fileUrl", "audioUrl"]:
            # 直接generatedVoice内を検索
            if field in generated_voice and generated_voice[field]:
                return generated_voice[field]
            
            # トップレベルも検索
            if field in data and data[field]:
                return data[field]
                
        # audioUrlがトップレベルにある場合
        if "audioUrl" in data:
            return data["audioUrl"]
            
        # ネストされた構造を検索
        for key, value in generated_voice.items():
            if isinstance(value, dict):
                for field in ["url", "fileUrl", "audioUrl", "audioFileUrl", "audioFileDownloadUrl"]:
                    if field in value and value[field]:
                        return value[field]
        
        return None
    
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
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url, 
                headers=self.headers,
                json=request.model_dump(by_alias=True),
            )
            
            if response.status_code != 200:
                raise NijiVoiceAPIError(f"音声生成に失敗しました: {response.text}", status_code=response.status_code)
            
            data = response.json()
            logger.debug("generate_voice API response: %s", data)
            
            # 共通のURL抽出関数を使用
            file_url = self._extract_url_from_response(data)
            
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
        
        # タイムアウト設定を適用
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.BASE_URL}/balances", headers=self.headers)
            
            if response.status_code != 200:
                raise NijiVoiceAPIError(f"クレジット残高の取得に失敗しました: {response.text}", status_code=response.status_code)
            
            data = response.json()
            # APIレスポンスの構造をログに出力
            logger.debug(f"Balance API response: {data}")
            
            # モデル検証
            balance = Balance.model_validate(data)
            return balance
