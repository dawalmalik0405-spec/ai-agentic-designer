# agents/firecrawl_research.py

import asyncio
import json

from mcp_use import MCPClient

CONFIG_FILE = "D:/practice/ui designer/mcp_server/servers.json"


async def run_firecrawl_research(prompt: str) -> dict:

    client = MCPClient(
        config=CONFIG_FILE,
        allowed_servers=["firecrawl"]
    )

    try:
        await client.create_all_sessions()

        session = client.get_session("firecrawl")

        print("=" * 60)
        print("CREATING FIRECRAWL JOB")
        print("=" * 60)
        
        create = await session.call_tool(
            "firecrawl_agent",
            {
                "prompt": prompt,
                "urls": [],
                "schema": {}
            }
        )

        
        print("CREATE RESPONSE:")
        print(create.content[0].text)
        payload = json.loads(create.content[0].text)

        if not payload.get("success"):
            raise RuntimeError(
                f"Failed to create job: {json.dumps(payload, indent=2)}"
            )

        job_id = payload.get("id")
        if not job_id:
            raise RuntimeError(
                f"No job ID in response: {json.dumps(payload, indent=2)}"
            )

        print(f"\n✓ Job created: {job_id}")
        print("=" * 60)
        print("POLLING JOB STATUS")
        print("=" * 60)

        max_polls = 30
        
        for i in range(max_polls):
            # Exponential backoff
            if i < 10:
                poll_interval = 2
            elif i < 20:
                poll_interval = 5
            else:
                poll_interval = 10

            status = await session.call_tool(
                "firecrawl_agent_status",
                {
                    "id": job_id
                }
            )

            print(f"\nPOLL {i}")
            print(status.content[0].text)

            result = json.loads(status.content[0].text)
            status_value = result.get("status", "unknown")

            # Always show status for debugging
            print(f"Poll {i}: status={status_value}")

            if status_value == "completed":
                print("\n✓ Research completed successfully!")
                print("=" * 60)
                return result
            
            if status_value == "failed":
                error_msg = result.get("error", result.get("message", "Unknown error"))
                print(f"\n✗ Job failed: {error_msg}")
                print("Full response:")
                print(json.dumps(result, indent=2))
                print("=" * 60)
                raise RuntimeError(f"Firecrawl failed: {error_msg}")

            if status_value not in ["processing", "pending"]:
                print(f"⚠ Unexpected status: {status_value}")
                print("Full response:")
                print(json.dumps(result, indent=2))

            print(f"  → Waiting {poll_interval}s before next poll...")
            await asyncio.sleep(poll_interval)

        # Job is stuck
        print("\n" + "=" * 60)
        print("TIMEOUT - JOB STILL PROCESSING")
        print("=" * 60)
        
        final_status = await session.call_tool(
            "firecrawl_agent_status",
            {"id": job_id}
        )
        final_result = json.loads(final_status.content[0].text)
        
        print(f"Job ID: {job_id}")
        print(f"Final status: {json.dumps(final_result, indent=2)}")
        print("\nDEBUGGING SUGGESTIONS:")
        print("1. Check Firecrawl account quota/limits")
        print("2. Verify Firecrawl API key is valid")
        print("3. Check if Firecrawl service is operational")
        print("4. Try with a simpler prompt")
        print("5. Check MCP Firecrawl server configuration")
        
        raise TimeoutError(
            f"Job {job_id} still in '{final_result.get('status')}' after {max_polls} polls"
        )

    finally:
        await client.close_all_sessions()