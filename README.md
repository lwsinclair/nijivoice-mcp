[![MseeP.ai Security Assessment Badge](https://mseep.net/mseep-audited.png)](https://mseep.ai/app/ryoooo-nijivoice-mcp)

# NijiVoice-MCP

**⚠️ 注意: このプロジェクトは開発中であり、動作未検証です。本番環境での使用は推奨されません。 ⚠️**

NijiVoice-MCPは、[にじボイス](https://www.nijivoice.com/)APIのModel Context Protocol (MCP)実装です。LLM（大規模言語モデル）からにじボイスAPIへのアクセスを可能にし、テキストから音声生成を簡単に行えるようにします。

## 機能概要

- にじボイスAPIを使用した音声合成
- 利用可能な声優（Voice Actor）の取得
- クレジット残高の確認
- MCPインターフェースを通じたLLMとの統合

## 必要条件

- Python 3.12以上
- にじボイスAPIキー
- インターネット接続

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/YOUR_USERNAME/nijivoice-mcp.git
cd nijivoice-mcp

# 依存パッケージのインストール
pip install -e .
```

## 環境設定

1. `.env`ファイルを作成し、以下の内容を追加します：

```
NIJIVOICE_API_KEY=あなたのAPIキー
DEFAULT_VOICE_ACTOR_ID=デフォルトで使用する声優ID（オプション）
LOG_LEVEL=INFO
```

2. APIキーはにじボイス公式サイトから取得できます。

## 使用方法

### MCPサーバーの起動

```bash
python main.py
```

これにより、MCPサーバーが起動し、LLMからのリクエストを受け付ける状態になります。

### 音声合成の例

MCPサーバーを利用するLLMクライアントから以下のようにツールを呼び出します：

```python
# 利用可能な声優の取得
actors = await tools.call("actor/get_voice_actors")

# 音声の生成
voice_result = await tools.call("voice/generate_voice", {
    "script": "こんにちは、にじボイスのテストです。",
    "voice_actor_id": "90031163-c497-44f3-a8a6-e45e4d0cb8f6",  # 声優ID
    "speed": 1.0,
    "emotional_level": 0.5,
    "sound_duration": 0.1,
    "format": "mp3"
})

# クレジット残高の確認
balance = await tools.call("credit/get_credit_balance")
```

## 利用可能なMCPツール

### 声優関連

- `actor/get_voice_actors()`: 利用可能な声優の一覧を取得

### 音声生成

- `voice/generate_voice(script, voice_actor_id, speed, emotional_level, sound_duration, format)`: 音声ファイルURL生成
- `voice/generate_encoded_voice(script, voice_actor_id, speed, emotional_level, sound_duration, format)`: Base64エンコードされた音声データ生成

### クレジット管理

- `credit/get_credit_balance()`: クレジット残高取得

## 特殊タグのサポート

スクリプト内で以下の特殊タグを使用できます：

- `<sp 1.0>xxx</sp>`: タグ内のテキストのスピードを変更
- `<wait 0.3>`: 指定した秒数の間を挿入

## 開発者向け情報

### プロジェクト構造

```
nijivoice-mcp/
├── config.py                # 設定ファイル
├── debug_api.py             # APIデバッグ用スクリプト
├── lib/                     # ライブラリ
├── logger.py                # ロギング設定
├── main.py                  # メインエントリーポイント
├── mcp/                     # MCP実装
│   ├── __init__.py          # MCPサーバー初期化
│   ├── actors.py            # 声優関連ツール
│   ├── credits.py           # クレジット関連ツール
│   ├── prompts.py           # プロンプト定義
│   └── voice.py             # 音声生成ツール
├── nijivoice/               # にじボイスAPIクライアント
│   ├── __init__.py
│   ├── api.py               # APIクライアント実装
│   ├── exceptions.py        # 例外定義
│   └── models.py            # データモデル
├── pyproject.toml           # プロジェクト定義
├── server.py                # サーバー実装
└── utils/                   # ユーティリティ
    ├── __init__.py
    ├── audio.py             # 音声処理ユーティリティ
    ├── error_handling.py    # エラーハンドリング
    └── retry.py             # リトライロジック
```

### テスト

```bash
# テストの実行
pytest
```

## 制限事項と既知の問題

⚠️ **重要な制限事項**:

1. このプロジェクトは**開発中**であり、機能や仕様が変更される可能性があります
2. にじボイスAPIの仕様変更により、動作しなくなる可能性があります
3. エラーハンドリングが十分でない箇所があります
4. 長文の音声生成時にタイムアウトが発生する場合があります
5. 一部のAPIレスポンス構造に対応できない可能性があります

## トラブルシューティング

問題が発生した場合：

1. ログファイル`nijivoice_mcp.log`を確認してください
2. APIキーが正しく設定されていることを確認してください
3. インターネット接続を確認してください
4. にじボイスAPIの状態を確認してください

## ライセンス

このプロジェクトは [MIT ライセンス](LICENSE) の下で提供されています。

## 謝辞

このプロジェクトは[FastMCP](https://github.com/fastmcp/fastmcp)と[Model Context Protocol](https://modelcontextprotocol.io/)を使用しています。にじボイスの音声合成技術を利用しています。

---

*「Voiced by NIJI Voice」*
