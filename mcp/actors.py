import logging
from typing import List, Optional
from fastmcp import FastMCP, Context

from nijivoice.api import NijiVoiceClient
from nijivoice.models import VoiceActor
from utils.error_handling import handle_exceptions
import config

# ロガーの設定
logger = logging.getLogger('nijivoice_mcp.mcp.actors')

# APIクライアントの初期化
client = NijiVoiceClient(api_key=config.API_KEY)

# ボイスアクター用のMCPインスタンス
actors_mcp = FastMCP("NijiVoice Voice Actors")

@actors_mcp.tool(name="get_voice_actors")
@handle_exceptions
async def get_voice_actors(ctx: Context) -> List[VoiceActor]:
    """
    利用可能なVoice Actorの一覧を取得します。
    
    Returns:
        Voice Actorのリスト
    """
    try:
        await ctx.info("Voice Actor一覧を取得しています...")
        actors = await client.get_voice_actors()
        await ctx.info(f"{len(actors)}件のVoice Actorを取得しました")
        return actors
    except Exception as e:
        error_message = f"Voice Actor一覧の取得中にエラーが発生しました: {str(e)}"
        await ctx.error(error_message)
        logger.error(error_message)
        raise ValueError(error_message)

@actors_mcp.resource("voice-actors://list", name="voice_actors_resource")
@handle_exceptions
async def voice_actors_resource(ctx: Context) -> List[VoiceActor]:
    """利用可能なVoice Actorの一覧"""
    try:
        await ctx.info("Voice Actor一覧リソースを取得しています...")
        actors = await client.get_voice_actors()
        await ctx.info(f"{len(actors)}件のVoice Actorリソースを取得しました")
        return actors
    except Exception as e:
        error_message = f"Voice Actor一覧リソースの取得中にエラーが発生しました: {str(e)}"
        await ctx.error(error_message)
        logger.error(error_message)
        return []  # エラー時は空リストを返す

@actors_mcp.resource("voice-actors://{voice_actor_id}", name="voice_actor_resource")
@handle_exceptions
async def voice_actor_resource(voice_actor_id: str, ctx: Context) -> Optional[VoiceActor]:
    """指定されたIDのVoice Actor"""
    try:
        await ctx.info(f"Voice Actor(ID: {voice_actor_id})リソースを取得しています...")
        actors = await client.get_voice_actors()
        for actor in actors:
            if actor.id == voice_actor_id:
                await ctx.info(f"Voice Actor '{actor.name}'を取得しました")
                return actor
        await ctx.warning(f"ID '{voice_actor_id}'のVoice Actorは見つかりませんでした")
        return None
    except Exception as e:
        error_message = f"Voice Actor(ID: {voice_actor_id})リソースの取得中にエラーが発生しました: {str(e)}"
        await ctx.error(error_message)
        logger.error(error_message)
        return None