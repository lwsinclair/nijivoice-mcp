import asyncio
import json
import os
import httpx
from dotenv import load_dotenv

# API設定
load_dotenv()
API_KEY = os.environ.get("NIJIVOICE_API_KEY")
BASE_URL = "https://api.nijivoice.com/api/platform/v1"

async def test_api():
    # ヘッダー設定
    headers = {
        "x-api-key": API_KEY,
        "Accept": "application/json",
    }

    # Voice Actor一覧を取得
    print(f"APIキー: {API_KEY}")
    print(f"ヘッダー: {headers}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/voice-actors", headers=headers)
            
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("レスポンス構造:")
                # 最初のレベルのキーを表示
                print(f"最初のレベルのキー: {list(data.keys())}")
                
                # データの構造を深堀り
                if "voiceActors" in data:
                    voice_actors = data["voiceActors"]
                    print(f"Voice Actorsの数: {len(voice_actors)}")
                    if len(voice_actors) > 0:
                        print("最初のVoice Actorのキー:")
                        print(list(voice_actors[0].keys()))
                        print("\n最初のVoice Actor:")
                        print(json.dumps(voice_actors[0], indent=2, ensure_ascii=False))
                else:
                    print("データの全体構造:")
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])  # 長すぎる場合は制限
            else:
                print(f"エラーレスポンス: {response.text}")
        except Exception as e:
            print(f"例外が発生しました: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_api())
