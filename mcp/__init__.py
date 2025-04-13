from fastmcp import FastMCP

# サブモジュールのインポート
from .voice import voice_mcp
from .actors import actors_mcp
from .credits import credits_mcp
from .prompts import register_prompts

# メインMCPインスタンス
main_mcp = FastMCP("にじボイスMCP")

def initialize_mcp():
    """MCPサーバーの初期化と各コンポーネントの登録"""
    # サブモジュールのマウント - URLとツール名に接頭辞を付ける
    main_mcp.mount("voice", voice_mcp)  # ツール: voice/, リソース: voice+
    main_mcp.mount("actor", actors_mcp)  # ツール: actor/, リソース: actor+
    main_mcp.mount("credit", credits_mcp)  # ツール: credit/, リソース: credit+
    
    # プロンプトの登録
    register_prompts(main_mcp)
    
    return main_mcp
