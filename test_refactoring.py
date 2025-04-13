#!/usr/bin/env python3
"""
リファクタリング後のコードをテストするスクリプト
"""
import asyncio
import logging
from fastmcp import FastMCP
from mcp import initialize_mcp

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_refactoring')

async def test_mcp_initialization():
    """MCPの初期化をテスト"""
    logger.info("MCPの初期化テスト開始")
    
    # MCPの初期化
    mcp = initialize_mcp()
    
    # MCPのインスタンスが正しく生成されたか確認
    if isinstance(mcp, FastMCP):
        logger.info("✅ MCPが正しく初期化されました")
    else:
        logger.error("❌ MCPの初期化に失敗しました")
        return False
    
    return True

async def test_mounted_tools():
    """マウントされたツールをテスト"""
    logger.info("マウントされたツールのテスト開始")
    
    # MCPの初期化
    mcp = initialize_mcp()
    
    # 各マウントされたツールの名前を確認
    tool_names = [tool.name for tool in mcp._tool_manager.tools.values()]
    
    expected_tools = [
        'actor/get_voice_actors',
        'voice/generate_voice',
        'voice/generate_encoded_voice',
        'credit/get_credit_balance',
    ]
    
    missing_tools = [tool for tool in expected_tools if tool not in tool_names]
    
    if not missing_tools:
        logger.info(f"✅ すべての期待されるツールが登録されています: {tool_names}")
    else:
        logger.error(f"❌ 次のツールが見つかりません: {missing_tools}")
        return False
    
    return True

async def test_mounted_resources():
    """マウントされたリソースをテスト"""
    logger.info("マウントされたリソースのテスト開始")
    
    # MCPの初期化
    mcp = initialize_mcp()
    
    # 各マウントされたリソースの名前を確認
    resource_handlers = list(mcp._resource_manager.resources.keys())
    
    expected_resources = [
        'voice+voice-actors://list',
        'voice+voice-actors://{voice_actor_id}',
        'actor+voice-actors://list',
        'actor+voice-actors://{voice_actor_id}',
        'credit+credit://balance',
    ]
    
    # すべての期待されるリソースが存在するか確認
    missing_resources = [res for res in expected_resources if not any(res in handler for handler in resource_handlers)]
    
    if not missing_resources:
        logger.info(f"✅ すべての期待されるリソースが登録されています")
    else:
        logger.error(f"❌ 次のリソースが見つかりません: {missing_resources}")
        return False
    
    return True

async def test_prompts():
    """プロンプトをテスト"""
    logger.info("プロンプトのテスト開始")
    
    # MCPの初期化
    mcp = initialize_mcp()
    
    # プロンプトが登録されているか確認
    if 'voice_generation_prompt' in mcp._prompt_manager.prompts:
        prompt_content = await mcp._prompt_manager.prompts['voice_generation_prompt']()
        
        # プロンプト内容が正しく更新されているか確認
        expected_mentions = [
            'actor/get_voice_actors',
            'voice/generate_voice',
            'voice/generate_encoded_voice',
            'credit/get_credit_balance',
        ]
        
        all_found = all(mention in prompt_content for mention in expected_mentions)
        
        if all_found:
            logger.info("✅ プロンプトが正しく更新されています")
        else:
            missing = [m for m in expected_mentions if m not in prompt_content]
            logger.error(f"❌ プロンプト内に次の言及が見つかりません: {missing}")
            return False
    else:
        logger.error("❌ voice_generation_promptが登録されていません")
        return False
    
    return True

async def run_tests():
    """すべてのテストを実行"""
    tests = [
        test_mcp_initialization,
        test_mounted_tools,
        test_mounted_resources,
        test_prompts,
    ]
    
    results = []
    
    for test in tests:
        result = await test()
        results.append(result)
    
    if all(results):
        logger.info("🎉 すべてのテストに合格しました！")
    else:
        logger.error("❌ いくつかのテストに失敗しました。上記のエラーを確認してください。")

if __name__ == "__main__":
    asyncio.run(run_tests())
