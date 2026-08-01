import asyncio
import os
from dotenv import load_dotenv

from schema.asset import AssetRequirement, AssetType, AssetPriority, SourceStrategy
from mcp_tools.asset_generation.executor import AssetExecutor

async def test_internet_strategy():
    load_dotenv()
    print("Testing SourceStrategy.INTERNET via AssetExecutor...")
    print(f"Unsplash Key Check: {'Found' if os.getenv('UNSPLASH_ACCESS_KEY') else 'MISSING!'}")
    
    executor = AssetExecutor()
    
    # Create a mock asset requirement that demands internet search
    req = AssetRequirement(
        asset_id="test_living_room",
        page_name="home",
        section_name="hero",
        purpose="A background image showing a modern living room",
        asset_type=AssetType.IMAGE,
        priority=AssetPriority.MEDIUM,
        source_strategy=SourceStrategy.INTERNET,
        generation_required=True,
        prompt="luxury modern living room with large windows",
        style_keywords=["interior", "architecture", "sunny"],
        width=1200,
        height=800,
        format="png",
        output_filename="test_living_room.png"
    )
    
    try:
        results = await executor.execute_asset(req)
        for result in results:
            print(f"Status: {result.status.value}")
            if result.error:
                print(f"Error: {result.error}")
            else:
                print(f"File Path: {result.file_path}")
                print(f"Provider: {result.provider}")
                print(f"Source URL: {result.provider_asset_url}")
                print(f"Dimensions: {result.width}x{result.height}")
    except Exception as e:
        print(f"Execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_internet_strategy())
