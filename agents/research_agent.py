from mcp_tools.firecrawl.reasearch_tool import (
    scrap_design,
    search_design
)
from agents.llm import deepseek_llm
from schema.architect import ArchitectOutput
from schema.research import ResearchOutput

# from langchain.agents import create_agent
from schema.url_selection import WebsiteSelection


import logging

logger = logging.getLogger(__name__)


class ResearchAgent:

    def __init__(self):

        self.model = deepseek_llm()

        self.parser_model = (
            deepseek_llm()
            .with_structured_output(
                ResearchOutput
            )
        )

        self.url_selector = (
            deepseek_llm()
            .with_structured_output(
                WebsiteSelection
            )
        )
            

        # self.tools = [
        #     search_design,
        #     scrap_design,
        #     crawl_web
        # ]

        # self.agent = create_agent(
        #     model=self.model,
        #     tools=self.tools,
        #     system_prompt=SYSTEM_PROMPT
        # )


    def generate_queries(
        self,
        architect_output: ArchitectOutput
    ) -> list[str]:

        project_type = (
            architect_output
            .project_summary
            .project_type
        )

        style = (
            architect_output
            .design_direction
            .style
        )

        inspiration = (
            architect_output
            .design_direction
            .inspiration_keywords
        )

        queries = [

            f"{project_type} website inspiration",

            f"{project_type} landing page design",

            f"{project_type} hero section",

            f"{style} website examples",

            "Linear website design",

            "Stripe website design",

            "Vercel website inspiration",

            "OpenAI website design",

            "Anthropic website design",

            "Framer website inspiration",
        ]

        queries.extend(inspiration)
        queries.extend([
            "Magic UI components",
            "Uiverse UI components",
            "Mobbin SaaS landing page",
            "Awwwards AI website",
            "Landbook SaaS website",
            "One Page Love startup website",
            "v0 landing page inspiration"
        ])

        return queries

    async def research(
        self,
        architect_output: ArchitectOutput
    ) -> ResearchOutput:
        



        logger.info(
            "Starting research phase"
        )


        research_requirements = (
            architect_output.research_requirements
        )

        queries = []

        queries.extend(
            research_requirements.search_queries
        )

        queries.extend(
            research_requirements.inspiration_sources
        )

        queries.extend(
            self.generate_queries(
                architect_output
            )
        )

        queries = list(
            dict.fromkeys(queries)
        )

        all_search = []

        for query in queries:

            print(f"\nSearching: {query}")

            search_result = await search_design.ainvoke(
                {
                    "query": query
                }
            )

            all_search.append(
                {
                    "query": query,
                    "results": str(search_result)[:300]
                }
            )

        design_direction = (
            architect_output.design_direction
        )

        project_summary = (
            architect_output.project_summary
        )


        analysis_prompt = f"""
            You are selecting websites
            for design intelligence research.

            Search Results:

            {all_search}

            Rules:

            - Select at most 5 websites.
            - Prefer product websites.
            - Prefer premium SaaS websites.
            - Prefer AI product websites.
            - Prefer:
                - Stripe
                - Linear
                - Vercel
                - OpenAI
                - Anthropic
                - Framer
                - Apple
                - Uiverse


            Do not select:

            - blogs
            - accessibility articles
            - research papers
            - forums

            Return only the best websites.
            """

        print("\nFIRST SEARCH RESULT:")
        print(all_search[0])
        
        selection = await self.url_selector.ainvoke(
            analysis_prompt
        )

        print("\nSelection:")
        print(selection)
        print(type(selection))

        selection.websites = (
            selection.websites[:5]
        )

        print("\nSelected Websites:\n")

        for website in selection.websites:
            print(
                website.name,
                website.url
            )

        if not selection.websites:
            raise ValueError(
                "No websites selected."
            )

        urls = [
            website.url
            for website in selection.websites[:5]
        ]


        logger.info(
            "Selected %s websites",
            len(selection.websites)
        )

        scraped_data = []

        for url in urls:

            try:

                data = await scrap_design.ainvoke(
                    {
                        "url": url
                    }
                )

                scraped_data.append(
                    {
                        "url": url,
                        "content": str(data)[:1500]
                    }
                )

                print("\nScraped Sites:")

                for site in scraped_data:
                    print(site["url"])

        

            except Exception as exc:

                logger.warning(
                    "Failed scraping %s: %s",
                    url,
                    exc
                )

        logger.info(
            "Scraped %s websites",
            len(scraped_data)
        )



        research_prompt = f"""
            Project Summary:

            {project_summary.model_dump_json(indent=2)}

            Design Direction:

            {design_direction.model_dump_json(indent=2)}

            Research Goals:

            {research_requirements.research_goals}

            Search Results:

            {all_search}

            Scraped Websites:

            {scraped_data}

            You are an elite website design researcher.

            Analyze all collected websites.

            Extract:

            - hero section patterns
            - page structure patterns
            - navigation patterns
            - typography systems
            - color systems
            - animation systems
            - interaction systems
            - premium UI patterns
            - premium UX patterns
            - modern AI startup design trends

            Focus only on reusable design intelligence.
            Do not summarize website content.

            Return detailed design intelligence.
            """
        
        print("\nScraped Count:")
        print(len(scraped_data))

        research_response = await self.model.ainvoke(
            research_prompt
        )

        research_text = research_response.content


        structured_prompt = f"""
            Convert the following website research
            into a valid ResearchOutput.

            IMPORTANT:

            Only include references that exist in:

            {urls}

            Do not invent websites.
            Do not add references that were not scraped.

            Research Findings:

            {research_text}
            """
        
        print("\nResearch Text Length:")
        print(len(research_text))

        with open(
            "raw_research.txt",
            "w",
            encoding="utf-8"
        ) as f:
            f.write(research_text)
        
        research_output = await self.parser_model.ainvoke(
            structured_prompt
        )

        if research_output is None:
            raise ValueError(
                "Failed to parse research output."
            )


        logger.info(
            "Research completed with %s references",
            len(research_output.references)
        )

        research_output.raw_research = research_text

        if not research_output.references:
            raise ValueError(
                "Research agent produced no references."
            )

        if not research_output.layout_patterns:
            raise ValueError(
                "Research agent produced no layout patterns."
            )

        if not research_output.animation_patterns:
            raise ValueError(
                "Research agent produced no animation patterns."
            )


        return research_output


# if __name__ == "__main__":

#     import asyncio
#     import json

#     from schema.architect import ArchitectOutput

#     async def main():

#         print("Loading Architect Output...")

#         with open(
#             "architect_output.json",
#             "r",
#             encoding="utf-8"
#         ) as f:

#             architecture = (
#                 ArchitectOutput
#                 .model_validate_json(
#                     f.read()
#                 )
#             )

#         print("Architect Output Loaded")

#         researcher = ResearchAgent()

#         print("Starting Research...")

#         research = await researcher.research(
#             architecture
#         )

#         print("Research Completed")

#         print(
#             research.model_dump_json(
#                 indent=2
#             )
#         )

#         with open(
#             "research_output.json",
#             "w",
#             encoding="utf-8"
#         ) as f:

#             f.write(
#                 research.model_dump_json(
#                     indent=2
#                 )
#             )

#         print(
#             "Research saved to research_output.json"
#         )

#     asyncio.run(main())