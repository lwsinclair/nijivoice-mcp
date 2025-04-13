import logging
from fastmcp import FastMCP

# ロガーの設定
logger = logging.getLogger('nijivoice_mcp.mcp.prompts')

def register_prompts(mcp: FastMCP):
    """MCPプロンプトの登録"""
    
    @mcp.prompt(name="voice_generation_prompt")
    def voice_generation_prompt() -> str:
        """音声生成のためのプロンプト"""
        return """
        # にじボイス音声生成

        にじボイスAPIを使用して音声を生成します。

        ## 使用可能なVoice Actor
        利用可能なVoice Actorの一覧を取得するには `actor/get_voice_actors` ツールを使用してください。

        ## 音声生成
        音声を生成するには以下のパラメータを指定します：

        - `script`: 読み上げるテキスト（最大3,000文字）（必須）
        - `voice_actor_id`: Voice Actor ID（デフォルト: 90031163-c497-44f3-a8a6-e45e4d0cb8f6）
        - `speed`: 読み上げのスピード（0.4〜3.0、デフォルト: 1.0）
        - `emotional_level`: 感情レベル（0〜1.5、未指定の場合は0.1）
        - `sound_duration`: 音素発音の長さ（0〜1.7、未指定の場合は0.1）
        - `format`: 音声フォーマット（"mp3"または"wav"、デフォルトは"mp3"）

        ## 特殊タグ
        scriptには以下の特殊タグを含めることができます：

        - `<sp 1.0>xxx</sp>`: タグ内のテキストのスピードを変更します。
        - `<wait 0.3>`: 指定した秒数の間を挿入します。

        ## 利用可能な関数
        - `actor/get_voice_actors()`: 利用可能なVoice Actorの一覧を取得
        - `voice/generate_voice(script, voice_actor_id="90031163-c497-44f3-a8a6-e45e4d0cb8f6", speed=1.0, emotional_level=None, sound_duration=None, format="mp3")`: 音声ファイル生成。構造化されたレスポンス（音声ファイルのURL、フォーマット、ファイルタイプなどの情報を含む）を返します。
        - `voice/generate_encoded_voice(script, voice_actor_id="90031163-c497-44f3-a8a6-e45e4d0cb8f6", speed=1.0, emotional_level=None, sound_duration=None, format="mp3")`: 音声データの生成。音声サイズなどのメタ情報と音声ファイルのURLを返します。
        - `credit/get_credit_balance()`: クレジット残高取得

        ## 例
        ```
        こんにちは、<wait 0.5>これは<sp 0.8>テスト</sp>です。
        ```

        ## エラー処理
        - APIエラーが発生した場合は詳細なエラーメッセージが返されます
        - レスポンス形式が変更された場合も自動的に対応します
        - エラー発生時はログにエラー詳細が出力されます
        """
