import httpx
from dotenv import load_dotenv
import os
import sys
import json  # JSONを見やすく表示するために追加

load_dotenv()

api_key = os.getenv("NIJIVOICE_API_KEY")
if api_key is None:
    print("エラー: NIJIVOICE_API_KEY が環境変数に設定されていません")
    sys.exit(1)

base_url = "https://api.nijivoice.com/api/platform/"
version = "v1"

def get_actors():
    url = f"{base_url}{version}/voice-actors"
    headers = {"Content-Type": "application/json", "x-api-key": api_key}
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        try:
            error_detail = response.json()
            print(f"エラー詳細: {error_detail}")
        except:
            print(f"レスポンス内容: {response.text}")
        return None
    
def generate_voice(actor_id, text):
    url = f"{base_url}{version}/voice-actors/{actor_id}/generate-voice"
    payload = {
        "script": text,
        "speed": "1.0",  # 文字列に変更
        "emotionalLevel": "0.5",  # 文字列に変更
        "soundDuration": "0.5",  # 文字列に変更
        "format": "mp3"
    }
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    response = httpx.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        try:
            error_detail = response.json()
            print(f"エラー詳細: {error_detail}")
        except:
            print(f"レスポンス内容: {response.text}")
        return None

# まず利用可能な声優一覧を取得
print("声優一覧を取得中...")
actors = get_actors()

if actors:
    print(f"利用可能な声優数: {len(actors)}")
    # 返されたデータ構造を確認
    print("\nレスポンスの型:", type(actors))
    
    # レスポンス構造を確認
    print("\nレスポンス構造:")
    print(json.dumps(actors, indent=2, ensure_ascii=False)[:500] + "..." if len(json.dumps(actors)) > 500 else json.dumps(actors, indent=2, ensure_ascii=False))
    
    # データ構造を分析して声優IDを取得
    actor_ids = []
    
    # 辞書型データを解析してIDを見つける
    if isinstance(actors, dict):
        # データ構造に応じた処理（例: actorsの中にvoiceActorsキーがある場合）
        if "voiceActors" in actors and isinstance(actors["voiceActors"], list):
            actor_list = actors["voiceActors"]
            for actor in actor_list:
                if isinstance(actor, dict) and "id" in actor:
                    actor_ids.append(actor["id"])
        # データ構造に応じた処理（例: actorsの中に直接データがある場合）
        elif "data" in actors and isinstance(actors["data"], list):
            actor_list = actors["data"]
            for actor in actor_list:
                if isinstance(actor, dict) and "id" in actor:
                    actor_ids.append(actor["id"])
        # 辞書型のactorsに直接idキーがある場合
        elif "id" in actors:
            actor_ids.append(actors["id"])
    
    # データが配列の場合
    elif isinstance(actors, list):
        for actor in actors:
            if isinstance(actor, dict) and "id" in actor:
                actor_ids.append(actor["id"])
    
    print(f"\n見つかった声優ID: {actor_ids}")
    
    if actor_ids:
        first_actor_id = actor_ids[0]
        print(f"\n使用する声優ID: {first_actor_id}")
        print("\n音声生成を実行中...")
        result = generate_voice(first_actor_id, "私はAIアシスタントです")
        print("\n生成結果:")
        print(json.dumps(result, indent=2, ensure_ascii=False) if result else "生成失敗")
    else:
        print("利用可能な声優IDが見つかりませんでした")
else:
    print("声優一覧の取得に失敗しました")