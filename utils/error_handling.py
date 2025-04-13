import logging
import functools
import inspect
from typing import Any, Callable, TypeVar, cast
from fastmcp import Context

logger = logging.getLogger('nijivoice_mcp.error_handling')

T = TypeVar('T')

def handle_exceptions(func: Callable[..., T]) -> Callable[..., T]:
    """
    例外処理を行うデコレータ。
    Contextオブジェクトがある場合はそれを使用してエラーログを出力します。
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # 関数の引数情報を取得
        sig = inspect.signature(func)
        bound_args = sig.bind_partial(*args, **kwargs)
        
        # Contextオブジェクトがあれば取得
        ctx = None
        for param_name, param in sig.parameters.items():
            if param.annotation == Context and param_name in bound_args.arguments:
                ctx = bound_args.arguments[param_name]
                break
        
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # エラーメッセージを構築
            error_message = f"{func.__name__}実行中にエラーが発生しました: {str(e)}"
            
            # ロギング
            logger.error(error_message, exc_info=True)
            
            # コンテキストがあればエラーを記録
            if ctx and hasattr(ctx, 'error'):
                await ctx.error(error_message)
            
            # ユーザーにわかりやすいエラーを返す
            if "タイムアウト" in str(e):
                raise ValueError("APIリクエストがタイムアウトしました。サーバーの負荷が高いか、テキストが長すぎる可能性があります。")
            else:
                raise ValueError(error_message)
    
    return cast(Callable[..., T], wrapper)
