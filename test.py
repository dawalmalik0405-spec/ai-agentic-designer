import asyncio
import json
from mcp_tools.initialize_mcps import create_mcp_client

async def main():
    client = create_mcp_client(allowed_servers=["pollinations"])
    
    try:
        await client.create_all_sessions()
        session = client.sessions["pollinations"]
        
        print("Fetching image models...")
        result = await session.call_tool("listImageModels", {})
        data = result.model_dump()
        
        # Try structuredContent first, then fall back to text
        structured = data.get("structuredContent")
        if structured:
            models = structured.get("imageModels", [])
            print(f"Found {len(models)} models via structuredContent:")
            for model in models:
                print(f"  - {model.get('name')} (id: {model.get('id', model.get('name'))})")
        else:
            content = data.get("content", [{}])
            text = content[0].get("text", "") if content else ""
            print(f"Raw content: {text[:500]}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close_all_sessions()

if __name__ == "__main__":
    asyncio.run(main())
