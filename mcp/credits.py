import logging
from fastmcp import FastMCP, Context

from nijivoice.api import NijiVoiceClient
from nijivoice.models import Balance
from utils.error_handling import handle_exceptions
import config

# ロガーの設定
logger = logging.getLogger('nijivoice_mcp.mcp.credits')

# APIクライアントの初期化
client = NijiVoiceClient(api_key=config.API_KEY)

# クレジット用のMCPインスタンス
credits_mcp = FastMCP("NijiVoice Credits")

@credits_mcp.tool(name="get_credit_balance")
@handle_exceptions
async def get_credit_balance(ctx: Context) -> int:
    """
    クレジット残高を取得します。
    
    Returns:
        クレジット残高
    """
    try:
        await ctx.info("クレジット残高を取得しています...")
        balance = await client.get_balance()
        credits = balance.get_credit()
        await ctx.info(f"クレジット残高: {credits}")
        return credits
    except Exception as e:
        error_message = f"クレジット残高の取得中にエラーが発生しました: {str(e)}"
        await ctx.error(error_message)
        logger.error(error_message)
        raise ValueError(error_message)

@credits_mcp.resource("credit://balance", name="credit_balance_resource")
@handle_exceptions
async def credit_balance_resource(ctx: Context) -> Balance:
    """クレジット残高"""
    try:
        await ctx.info("クレジット残高リソースを取得しています...")
        balance = await client.get_balance()
        await ctx.info(f"クレジット残高: {balance.get_credit()}")
        return balance
    except Exception as e:
        error_message = f"クレジット残高リソースの取得中にエラーが発生しました: {str(e)}"
        await ctx.error(error_message)
        logger.error(error_message)
        # エラー時はダミーの残高を返す（0クレジット）
        return Balance(balance=0)