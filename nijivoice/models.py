from typing import Optional, List, Literal
import logging
from pydantic import BaseModel, field_serializer, Field, ConfigDict

# ロガーの設定
logger = logging.getLogger('nijivoice_mcp.models')

class RecommendedParameters(BaseModel):
    """にじボイスの推奨パラメータモデル"""
    emotional_level: Optional[float] = Field(1.0, alias="emotionalLevel")
    sound_duration: Optional[float] = Field(1.0, alias="soundDuration")

    # 未知のフィールドをスキップする設定
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"  # 未知のフィールドを無視する
    )

class VoiceActor(BaseModel):
    """にじボイスのVoice Actorモデル"""
    id: str
    name: str
    description: Optional[str] = ""
    sample_audio_url: Optional[str] = Field("", alias="sampleAudioUrl")
    image_url: Optional[str] = Field("", alias="imageUrl")
    recommended_parameters: Optional[RecommendedParameters] = Field(None, alias="recommendedParameters")
    
    # 未知のフィールドをスキップする設定
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"  # 未知のフィールドを無視する
    )

class VoiceGenerationRequest(BaseModel):
    """音声生成リクエストモデル"""
    script: str
    speed: float
    emotional_level: Optional[float] = Field(None, alias="emotionalLevel")
    sound_duration: Optional[float] = Field(None, alias="soundDuration")
    format: Optional[Literal["mp3", "wav"]] = "mp3"

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer('speed')
    def serialize_speed(self, speed: float) -> str:
        return str(speed)
        
    @field_serializer('emotional_level')
    def serialize_emotional_level(self, emotional_level: Optional[float]) -> Optional[str]:
        return str(emotional_level) if emotional_level is not None else None
        
    @field_serializer('sound_duration')
    def serialize_sound_duration(self, sound_duration: Optional[float]) -> Optional[str]:
        return str(sound_duration) if sound_duration is not None else None

    @field_serializer('format')
    def serialize_format(self, fmt: str):
        return fmt.lower()

class EncodedVoiceResponse(BaseModel):
    """エンコードされた音声のレスポンスモデル"""
    encoded_voice: Optional[str] = Field(None, alias="encodedVoice")
    generated_voice: Optional[dict] = Field(None, alias="generatedVoice")
    remaining_credits: Optional[int] = Field(None, alias="remainingCredits")
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"  # 未知のフィールドを無視する
    )
    
    def get_encoded_voice(self) -> Optional[str]:
        """異なるレスポンス形式に対応して音声データを取得する"""
        # 1. 直接encodedVoiceがある場合
        if self.encoded_voice is not None:
            logger.debug(f"Found encoded_voice directly: length={len(self.encoded_voice)}")
            return self.encoded_voice
        
        # 2. 生成された音声データを探す
        if self.generated_voice and isinstance(self.generated_voice, dict):
            logger.debug(f"Searching in generated_voice: keys={list(self.generated_voice.keys())}")
            
            # a. トップレベルのキーを確認
            for key in ["base64", "base64Audio", "audio", "encodedAudio"]:
                if key in self.generated_voice:
                    logger.debug(f"Found Base64 data in key: {key}")
                    return self.generated_voice[key]
            
            # b. ネストされた構造を確認（例: generatedVoice.base64Audio）
            for nested_key in ["base64", "base64Audio", "audio", "encodedAudio"]:
                # ネストされた辞書を探索
                for key, value in self.generated_voice.items():
                    if isinstance(value, dict) and nested_key in value:
                        logger.debug(f"Found Base64 data in nested structure: {key}.{nested_key}")
                        return value[nested_key]
            
            # c. 特殊なケース: base64Audioなどの文字列がそのまま値になっている場合
            # generatedVoiceそのものが文字列の場合
            if isinstance(self.generated_voice, str) and self.generated_voice.startswith("//"):
                logger.debug("generatedVoice itself is a Base64 string")
                return self.generated_voice
            
            # d. キーを含まない形式でも、値が//で始まるBase64文字列の場合
            for key, value in self.generated_voice.items():
                if isinstance(value, str) and value.startswith("//"):
                    logger.debug(f"Found Base64 data starting with // in key: {key}")
                    return value
        
        # 3. 含まれるすべてのキーをデバッグ出力
        if self.generated_voice and isinstance(self.generated_voice, dict):
            logger.debug(f"Available keys in generated_voice: {self.generated_voice.keys()}")
            for key, value in self.generated_voice.items():
                if isinstance(value, dict):
                    logger.debug(f"Nested keys in {key}: {value.keys()}")
                elif isinstance(value, str) and len(value) > 100:
                    logger.debug(f"Long string value in {key}: {value[:50]}...")
        
        return None
    
    def get_audio_url(self) -> Optional[str]:
        """音声ファイルのURLを取得する"""
        if self.generated_voice and isinstance(self.generated_voice, dict):
            # デバッグ: キーの一覧を出力
            logger.debug(f"generatedVoice keys in get_audio_url: {list(self.generated_voice.keys())}")
            
            # 直接URLがある場合
            if "audioFileUrl" in self.generated_voice:
                logger.debug("Found audioFileUrl in generatedVoice")
                return self.generated_voice["audioFileUrl"]
            
            # ダウンロード用URLがある場合
            if "audioFileDownloadUrl" in self.generated_voice:
                logger.debug("Found audioFileDownloadUrl in generatedVoice")
                return self.generated_voice["audioFileDownloadUrl"]
            
            # 他のキーを探す
            for key in ["url", "fileUrl", "audioUrl"]:
                if key in self.generated_voice:
                    logger.debug(f"Found {key} in generatedVoice")
                    return self.generated_voice[key]
                
            # ネストされた構造を確認
            for key, value in self.generated_voice.items():
                if isinstance(value, dict):
                    logger.debug(f"Checking nested structure in key: {key}, keys: {list(value.keys())}")
                    # これらのキーを確認
                    for url_key in ["url", "fileUrl", "audioUrl", "audioFileUrl", "audioFileDownloadUrl"]:
                        if url_key in value:
                            logger.debug(f"Found {url_key} in nested structure {key}")
                            return value[url_key]
        
        return None
    
    def get_duration(self) -> Optional[int]:
        """音声の再生時間を取得する（ミリ秒）"""
        if self.generated_voice and isinstance(self.generated_voice, dict):
            if "duration" in self.generated_voice:
                return self.generated_voice["duration"]
        
        return None
    
    def get_remaining_credits(self) -> Optional[int]:
        """残りのクレジット数を取得する"""
        # 直接remaining_creditsが設定されている場合
        if self.remaining_credits is not None:
            return self.remaining_credits
            
        # generated_voice内にある場合
        if self.generated_voice and isinstance(self.generated_voice, dict):
            if "remainingCredits" in self.generated_voice:
                return self.generated_voice["remainingCredits"]
        
        return None
    
    def get_audio_url_first(self) -> Optional[tuple]:
        """URLを最優先で探し、見つかった場合はURLとフィールド名を返す"""
        url_fields = [
            "audioFileUrl",
            "audioFileDownloadUrl", 
            "url", 
            "fileUrl", 
            "audioUrl"
        ]
        
        # 1. generated_voiceを確認
        if self.generated_voice and isinstance(self.generated_voice, dict):
            for field in url_fields:
                if field in self.generated_voice and self.generated_voice[field]:
                    return self.generated_voice[field], field
            
            # ネストされた構造を確認
            for key, value in self.generated_voice.items():
                if isinstance(value, dict):
                    for field in url_fields:
                        if field in value and value[field]:
                            return value[field], f"{key}.{field}"
        
        return None, None

class Balance(BaseModel):
    """クレジット残高モデル"""
    balance: Optional[int] = None
    balances: Optional[dict] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore"  # 未知のフィールドを無視する
    )
    
    def get_credit(self) -> int:
        """異なるレスポンス形式に対応してクレジット残高を取得する"""
        # 直接balanceフィールドがある場合
        if self.balance is not None:
            return self.balance
        
        # balancesオブジェクト内の様々な構造に対応
        if self.balances and isinstance(self.balances, dict):
            # remainingBalanceがある場合
            if 'remainingBalance' in self.balances:
                return self.balances['remainingBalance']
            # balanceがある場合
            elif 'balance' in self.balances:
                return self.balances['balance']
            
            # creditsリストがあり、その中にbalanceがある場合
            if 'credits' in self.balances and isinstance(self.balances['credits'], list) and len(self.balances['credits']) > 0:
                for credit in self.balances['credits']:
                    if isinstance(credit, dict) and 'balance' in credit:
                        return credit['balance']
        
        # どのフィールドにも残高情報がない場合
        logger.warning("クレジット残高情報が見つかりませんでした")
        return 0
    
