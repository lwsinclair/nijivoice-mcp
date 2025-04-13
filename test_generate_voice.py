import pytest
import asyncio
from server import generate_voice

# ダミーのコンテキストオブジェクト
class DummyContext:
    pass

@pytest.mark.asyncio
async def test_generate_voice():
    ctx = DummyContext()
    # テスト用のスクリプト
    script = "こんにちは、これはテストです。"
    
    # 正しい NIJIVOICE_API_KEY が設定されている必要があります
    result = await generate_voice(ctx, script)
    
    # 結果が辞書型で、ステータスが "success" の場合、成功とみなす
    assert isinstance(result, dict)
    assert result.get("status") == "success"
    
    # API から音声URLが返される場合、"audio_url" または "file_url" キーが含まれていることを確認
    assert "audio_url" in result or "file_url" in result
