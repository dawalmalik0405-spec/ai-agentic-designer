import logging

from mcp_tools.initialize_mcps import create_mcp_client
from mcp_tools.resilience import ProviderResilience


logger = logging.getLogger(__name__)


class FirecrawlService:

    def __init__(
        self,
        resilience: ProviderResilience | None = None
    ):

        self.client = create_mcp_client(
            allowed_servers=["firecrawl"]
        )

        self.session = None
        self.resilience = (
            resilience
            or ProviderResilience.from_env(
                "firecrawl",
                logger=logger
            )
        )

    async def connect(self):

        await self.client.create_all_sessions()

        self.session = self.client.get_session(
            "firecrawl"
        )

        return self.session

    async def close(self):

        await self.client.close_all_sessions()








async def search_website(
        query: str,
        limit:int = 10
):
    

    service = FirecrawlService()


    try:
        
        session = await service.connect()

        result = await service.resilience.execute(
            "search",
            lambda: session.call_tool(
                "firecrawl_search",
                {
                    "query": query,
                    "limit":limit
                }
            )
        )

        return result

    finally:
        

        await service.close()



async def scrape_website(
        url:str
):
    

    service = FirecrawlService()


    try:
        
        session = await service.connect()

        result = await service.resilience.execute(
            "scrape",
            lambda: session.call_tool(
                "firecrawl_scrape",
                {
                    "url":url,
                    "formats":["markdown"]
                }
            )
        )

        return result

    finally:
        

        await service.close()





async def crawl_website(
        url:str,
        limit:int = 20
):
    

    service = FirecrawlService()


    try:
        
        session = await service.connect()

        result = await service.resilience.execute(
            "crawl",
            lambda: session.call_tool(
                "firecrawl_crawl",
                {
                    "url":url,
                    "limit":limit
                }
            )
        )

        return result

    finally:
        

        await service.close()
