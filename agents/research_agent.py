from mcp_tools.firecrawl.reasearch_tool import (
    scrap_design,
    search_design
)
from agents.llm import deepseek_llm
from schema.architect import ArchitectOutput
from schema.research import ResearchOutput
from agents.json_utils import load_model_json, parse_model_json
from agents.resilient_llm import resilient_ainvoke

# from langchain.agents import create_agent
from schema.url_selection import SelectedWebsite, WebsiteSelection


import logging

logger = logging.getLogger(__name__)


FALLBACK_WEBSITES = [
    SelectedWebsite(
        name="Stripe",
        url="https://stripe.com",
        reason="Premium SaaS reference for conversion, layout, and visual polish.",
    ),
    SelectedWebsite(
        name="Linear",
        url="https://linear.app",
        reason="Premium SaaS reference for typography, focus, and dark-mode product design.",
    ),
    SelectedWebsite(
        name="Vercel",
        url="https://vercel.com",
        reason="Developer SaaS reference for modern product storytelling and motion.",
    ),
    SelectedWebsite(
        name="OpenAI",
        url="https://openai.com",
        reason="AI product reference for trust, clarity, and editorial design.",
    ),
    SelectedWebsite(
        name="Framer",
        url="https://framer.com",
        reason="Modern website reference for interaction, motion, and landing-page polish.",
    ),
    SelectedWebsite(
        name="Motionsites",
        url="https://motionsites.ai/",
        reason="Modern website reference for interaction, motion, and landing-page polish. and also the reference for better prompts",
    ),
]


class ResearchAgent:

    def __init__(self):

        self.model = deepseek_llm()

        self.url_selector = deepseek_llm()
            
        
            

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

            "motionsites"
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
            You are selecting websites for design intelligence research.

            Search Results:

            {all_search}

            Select at most 5 websites.

            Return ONLY valid JSON.
            Do not include explanation.
            Do not include markdown.
            Do not wrap the JSON in ```json.
            Do not write any text before or after the JSON.

            The JSON must match this exact schema:

            {{
            "websites": [
                {{
                "name": "Website name",
                "url": "https://example.com",
                "reason": "Short reason for selecting this website"
                }}
            ]
            }}

            Rules:
            - Prefer product websites.
            - Prefer premium SaaS websites.
            - Prefer AI product websites.
            - Prefer Stripe, Linear, Vercel, OpenAI, Anthropic, Framer, Apple, Uiverse.
            - Do not select blogs, accessibility articles, research papers, or forums.
            """

        print("\nFIRST SEARCH RESULT:")
        print(all_search[0])

        selection_response  = await resilient_ainvoke(
            self.model,
            analysis_prompt,
            "research_select_websites"
        )
        print(selection_response.content)
        
        try:
            selection = parse_model_json(
                WebsiteSelection,
                selection_response.content
            )
        except Exception as exc:
            logger.warning(
                "Using fallback website selection: %s",
                exc
            )
            selection = WebsiteSelection(
                websites=FALLBACK_WEBSITES
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

        research_response = await resilient_ainvoke(
            self.model,
            research_prompt,
            "research_synthesize_findings"
        )

        research_text = research_response.content


        structured_prompt = f"""
            Convert the follo
            ng website research
            into a valid ResearchOutput.

            IMPORTANT:

            Return ONLY valid JSON.
            Do not include explanation.
            Do not include markdown.
            Do not wrap JSON in code fences.

            Every pattern field must be an array of strings only.
            Do not return objects inside pattern arrays.
            Do not use keys like category, examples, details, code, url inside pattern arrays.

            Only include references that exist in:

            {urls}

            Every reference must include exactly:
            name, url, reason.

            The url field is required for every reference.
            Never omit url.
            Only use URLs from the selected/scraped URL list.
            If you cannot find a URL for a reference, do not include that reference.

            for example :

            "references": [
                {{
                    "name": "Anthropic",
                    "url": "https://www.anthropic.com",
                    "reason": "Strong AI product reference for trust and technical clarity."
                }}
                ]

            The JSON must match this exact shape:

            {{
            "references": [
                {{
                "name": "Linear",
                "url": "https://linear.app/",
                "reason": "Short reason"
                }}
            ],
            "hero_patterns": [
                "Use a clear hero headline with one primary CTA."
            ],
            "layout_patterns": [
                "Use alternating full-width sections for product proof and features."
            ],
            "typography_patterns": [
                "Use high-contrast headings with concise body copy."
            ],
            "animation_patterns": [
                "Use subtle scroll reveals and hover transitions."
            ],
            "interaction_patterns": [
                "Use tabs or segmented controls for feature exploration."
            ],
            "color_patterns": [
                "Use a dark neutral base with one controlled accent color."
            ],
            "premium_features": [
                "Use customer logos and enterprise trust signals near CTAs."
            ],
            "research_summary": "Short summary of reusable design intelligence.",
            "recommended_libraries": [
                "Framer Motion for animation."
            ],
            "raw_research": null,
            "visual_patterns": [
                "Use abstract AI visuals and product interface previews."
            ],
            "component_patterns": [
                "Use hero, feature grid, testimonial, pricing, and CTA components."
            ]
            }}

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
        
        research_output_response = await resilient_ainvoke(
            self.model,
            structured_prompt,
            "research_output_json"
        )

        research_payload = load_model_json(
            research_output_response.content
        )

        url_by_name = {
            website.name.lower(): website.url
            for website in selection.websites
        }

        cleaned_references = []

        for reference in research_payload.get("references", []):
            if not isinstance(reference, dict):
                continue

            name = str(reference.get("name", "")).strip()
            url = str(reference.get("url", "")).strip()
            reason = str(reference.get("reason", "")).strip()

            if not url and name:
                url = url_by_name.get(name.lower(), "")

            if not reason:
                reason = "Selected as a reusable design reference."

            if name and url:
                cleaned_references.append(
                    {
                        "name": name,
                        "url": url,
                        "reason": reason,
                    }
                )

        if not cleaned_references:
            cleaned_references = [
                {
                    "name": website.name,
                    "url": website.url,
                    "reason": website.reason,
                }
                for website in selection.websites
            ]

        research_payload["references"] = cleaned_references

        for key in [
            "hero_patterns",
            "layout_patterns",
            "typography_patterns",
            "animation_patterns",
            "interaction_patterns",
            "color_patterns",
            "premium_features",
            "recommended_libraries",
            "visual_patterns",
            "component_patterns",
        ]:
            values = research_payload.get(key) or []
            research_payload[key] = [
                item
                if isinstance(item, str)
                else str(item)
                for item in values
            ]

        research_output = ResearchOutput.model_validate(
            research_payload
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

#     architecture ="" \
#     ""

#     async def main():

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
