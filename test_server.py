import os
import asyncio
import tempfile
import base64
import json
import pytest
import server
from nijivoice.models import VoiceActor, Balance, VoiceGenerationRequest

# 既存のサーバ起動テスト
def test_server_start():
    """
    サーバーがエラーなく起動するかどうかをテストします。
    """
    try:
        if hasattr(server, 'main'):
            server.main()
    except Exception as e:
        pytest.fail(f"サーバー起動時に例外が発生しました: {e}")

# 各関数に対するテスト（出力を表示）

@pytest.mark.asyncio
async def test_get_voice_actors_success(monkeypatch):
    dummy_voice_actor = VoiceActor(id="actor1", name="Test Actor")
    async def fake_get_voice_actors():
        return [dummy_voice_actor]
    monkeypatch.setattr(server.client, "get_voice_actors", fake_get_voice_actors)
    result = await server.get_voice_actors()
    print("get_voice_actors output:", result)
    assert isinstance(result, list)
    assert result[0].id == "actor1"

@pytest.mark.asyncio
async def test_generate_voice_success(monkeypatch):
    # ダミーのレスポンスオブジェクトを作成
    class DummyResponse:
        def __init__(self):
            self.generated_voice = {
                "audioFileUrl": "http://example.com/audio.mp3",
                "duration": 123,
                "remainingCredits": 456
            }
        def model_dump(self):
            return self.generated_voice
    async def fake_generate_encoded_voice(voice_actor_id, request):
        return DummyResponse()
    monkeypatch.setattr(server.client, "generate_encoded_voice", fake_generate_encoded_voice)
    # ctx は不要なため None で代用
    result = await server.generate_voice(None, script="テストスクリプト")
    print("generate_voice output:", result)
    assert result["status"] == "success"
    assert result["audio_url"] == "http://example.com/audio.mp3"

@pytest.mark.asyncio
async def test_generate_encoded_voice_success(monkeypatch):
    # DummyResponse は generate_encoded_voice 用のダミーレスポンス
    class DummyResponse:
        def __init__(self):
            self._encoded_voice = "dGVzdGRhdGE="  # base64 for "testdata"
            self.generation_time = 100
        def get_encoded_voice(self):
            return self._encoded_voice
        def get_audio_url(self):
            return "http://example.com/encoded_audio.mp3"
        def get_duration(self):
            return 200
        def get_remaining_credits(self):
            return 789
    async def fake_generate_encoded_voice(voice_actor_id, request):
        return DummyResponse()
    monkeypatch.setattr(server.client, "generate_encoded_voice", fake_generate_encoded_voice)
    result = await server.generate_encoded_voice(None, script="テスト")
    print("generate_encoded_voice output:", result)
    assert result["status"] == "success"
    assert "audio_url" in result
    assert result["audio_url"] == "http://example.com/encoded_audio.mp3"

@pytest.mark.asyncio
async def test_get_credit_balance_success(monkeypatch):
    dummy_balance = Balance(balance=100)
    monkeypatch.setattr(Balance, "get_credit", lambda self: self.balance)
    async def fake_get_balance():
        return dummy_balance
    monkeypatch.setattr(server.client, "get_balance", fake_get_balance)
    credit = await server.get_credit_balance()
    print("get_credit_balance output:", credit)
    assert credit == 100

@pytest.mark.asyncio
async def test_voice_actors_resource(monkeypatch):
    dummy_voice_actor = VoiceActor(id="actor1", name="Test Actor")
    async def fake_get_voice_actors():
        return [dummy_voice_actor]
    monkeypatch.setattr(server.client, "get_voice_actors", fake_get_voice_actors)
    result = await server.voice_actors_resource()
    print("voice_actors_resource output:", result)
    assert isinstance(result, list)
    assert result[0].id == "actor1"

@pytest.mark.asyncio
async def test_voice_actor_resource_found(monkeypatch):
    dummy_voice_actor = VoiceActor(id="actor1", name="Test Actor")
    async def fake_get_voice_actors():
        return [dummy_voice_actor]
    monkeypatch.setattr(server.client, "get_voice_actors", fake_get_voice_actors)
    result = await server.voice_actor_resource("actor1")
    print("voice_actor_resource (found) output:", result)
    assert result is not None
    assert result.id == "actor1"

@pytest.mark.asyncio
async def test_voice_actor_resource_not_found(monkeypatch):
    async def fake_get_voice_actors():
        return []
    monkeypatch.setattr(server.client, "get_voice_actors", fake_get_voice_actors)
    result = await server.voice_actor_resource("nonexistent")
    print("voice_actor_resource (not found) output:", result)
    assert result is None

@pytest.mark.asyncio
async def test_credit_balance_resource(monkeypatch):
    dummy_balance = Balance(balance=50)
    async def fake_get_balance():
        return dummy_balance
    monkeypatch.setattr(server.client, "get_balance", fake_get_balance)
    result = await server.credit_balance_resource()
    print("credit_balance_resource output:", result)
    assert result.balance == 50

def test_voice_generation_prompt():
    prompt = server.voice_generation_prompt()
    print("voice_generation_prompt output:", prompt)
    assert isinstance(prompt, str)
    assert "にじボイス音声生成" in prompt
