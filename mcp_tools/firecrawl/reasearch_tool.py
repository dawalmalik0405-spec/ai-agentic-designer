from langchain_core.tools import tool
from mcp_tools.firecrawl.firecrawltools import (search_website,scrape_website, crawl_website)


@tool
async def search_design(
  query:str
):
  
  """
  Search for website inspiration.
  """

  return await search_website(query)


@tool
async def scrap_design(
  url:str
):
  
  """
  Scrape website for UI analysis.
  """

  return await scrape_website(url)


@tool
async def crawl_web(
  url:str
):
  
  """
  Crawl website for inspiration
  """

  return await crawl_website(url)



