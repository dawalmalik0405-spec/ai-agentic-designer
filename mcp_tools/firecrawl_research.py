# agents/firecrawl_research.py

import asyncio
import json

from mcp_tools.firecrawl_research import run_mcp_agent




async def run_firecrawl_research(prompt: str) -> dict:

    
    dissallowed_tools = ['firecrawl_scrape', 'firecrawl_map', 'firecrawl_search', 'firecrawl_search_feedback', 'firecrawl_crawl', 'firecrawl_check_crawl_status', 'firecrawl_extract', 'firecrawl_agent', 'firecrawl_agent_status', 'firecrawl_interact', 'firecrawl_interact_stop', 'firecrawl_parse', 'firecrawl_monitor_create', 'firecrawl_monitor_list', 'firecrawl_monitor_get', 'firecrawl_monitor_update', 'firecrawl_monitor_delete', 'firecrawl_monitor_run', 'firecrawl_monitor_checks', 'firecrawl_monitor_check']


    agent = run_mcp_agent(
        allowed_server = "firecrawl",
        disallowed_tools = dissallowed_tools

    )


    





























































































































































    # try:
    #     await client.create_all_sessions()

    #     session = client.get_session("firecrawl")

    #     print("=" * 60)
    #     print("CREATING FIRECRAWL JOB")
    #     print("=" * 60)
        
    #     create = await session.call_tool(
    #         "firecrawl_agent",
    #         {
    #             "prompt": prompt,
    #             "urls": [],
    #             "schema": {}
    #         }
    #     )









   

