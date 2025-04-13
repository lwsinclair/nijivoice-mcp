import asyncio
import logging
import httpx

logger = logging.getLogger('nijivoice_mcp.utils.retry')

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
