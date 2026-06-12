from mcp_tools.firecrawl.reasearch_tool import (
    scrap_design,
    search_design,
    crawl_web
)
from agents.llm import research_llm
from schema.architect import ArchitectOutput
from schema.research import ResearchOutput

# from langchain.agents import create_agent
from schema.url_selection import WebsiteSelection


import logging

logger = logging.getLogger(__name__)



SYSTEM_PROMPT = """
You are an elite Website Research Agent.

You are researching websites for a premium
AI-powered website generation platform.

Your goal is not content research.

Your goal is design intelligence.

Research:

- layouts
- visual hierarchy
- hero sections
- section ordering
- CTA placement
- typography systems
- color systems
- motion systems
- interactions
- premium visual details

Prefer:

- Apple
- Stripe
- Linear
- Vercel
- OpenAI
- Anthropic
- Airbnb
- Framer

Search multiple times.

use provided tools.

Scrape websites when necessary.

Gather enough information that a
Design System Agent can build a
world-class design system.
"""

class ResearchAgent:

    def __init__(self):

        self.model = research_llm()

        self.parser_model = research_llm()

        self.url_selector = (
            research_llm()
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

        queries  = (
            research_requirements.search_queries
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
                    "results": str(search_result)[:4000]
                }
            )

        design_direction = (
            architect_output.design_direction
        )

        project_summary = (
            architect_output.project_summary
        )


        analysis_prompt = f"""
            You are a senior UX researcher.

            Search Results:

            {all_search}

            Select:

            - best competitor websites
            - best inspiration websites
            - best motion references
            - best typography references

            Return:

            - website name
            - url
            - reason
            """


        selection = await self.url_selector.ainvoke(
            analysis_prompt
        )

        urls = [
            website.url
            for website in selection.websites
        ]


        scraped_data = []

        urls = extract_urls(
            url_selection.content
        )



        for url in urls:

            try:   

                data = await scrap_design.ainvoke(
                    {
                        "url": url
                    }
                )

                scraped_data.append(data)

            except Exception as exc:

                logger.warning(
                    "Failed scraping %s: %s",
                    url,
                    exc
                )











        prompt = f"""
        Project Type:
        {project_summary.project_type}

        Business Goal:
        {project_summary.business_goal}

        Target Audience:
        {project_summary.target_audience}

        Design Style:
        {design_direction.style}

        Mood:
        {design_direction.mood}

        Research Queries:
        {research_requirements.search_queries}

        Research Goals:
        {research_requirements.research_goals}

        Use tools aggressively.

        Search multiple times if necessary.

        Scrape websites when necessary.

        Focus on gathering information useful for:

        - Design System Agent
        - Visual Asset Agent
        - Page Design Agent

        Return detailed findings.
        """

        for attempt in range(3):

            try:
                result = await self.agent.ainvoke(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    }
                )

                break

            except Exception as exc:

                logger.warning(
                    "Research attempt %s failed: %s",
                    attempt + 1,
                    exc
                )

                if attempt == 2:
                    raise


        messages = result.get("messages", [])

        if not messages:
            raise ValueError(
                "Research agent returned no messages."
            )

        research_text = messages[-1].content


        structured_prompt = f"""
            Convert the following website research
            into a valid ResearchOutput.

            Requirements:

            - include all discovered references
            - include hero patterns
            - include layout patterns
            - include typography patterns
            - include color patterns
            - include animation patterns
            - include interaction patterns
            - include premium features

            Research Findings:

            {research_text}
            """
        
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


if __name__ == "__main__":

    import asyncio
    import json

    from schema.architect import ArchitectOutput

    async def main():

        print("Loading Architect Output...")

        with open(
            "architect_output.json",
            "r",
            encoding="utf-8"
        ) as f:

            architecture = (
                ArchitectOutput
                .model_validate_json(
                    f.read()
                )
            )

        print("Architect Output Loaded")

        researcher = ResearchAgent()

        print("Starting Research...")

        research = await researcher.research(
            architecture
        )

        print("Research Completed")

        print(
            research.model_dump_json(
                indent=2
            )
        )

        with open(
            "research_output.json",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                research.model_dump_json(
                    indent=2
                )
            )

        print(
            "Research saved to research_output.json"
        )

    asyncio.run(main())