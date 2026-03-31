import os
import requests
from state import AgentState

def fetch_news(state: AgentState) -> AgentState:
    print("  → Searching latest AI news via Tavily...")
    tavily_key = os.getenv("TAVILY_API_KEY")

    queries = [
    "latest AI news 2026 generative AI developments",
    "new AI model releases 2026 LLM announcements",
    "OpenAI Google DeepMind latest updates 2026",
    "latest generative AI research breakthroughs",
]

    # Only trust these domains
    trusted_domains = [
        "arxiv.org", "huggingface.co", "openai.com", "anthropic.com",
        "deepmind.google", "github.com", "mistral.ai", "meta.ai",
        "together.ai", "venturebeat.com", "techcrunch.com", "theverge.com",
        "blog.google", "pytorch.org", "tensorflow.org"
    ]

    items, urls = [], []

    for query in queries:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": query,
                "search_depth": "advanced",
                "topic": "news",
                "days": 7,
                "max_results": 5,        # more articles instead of more content per article
                "include_answer": True,  # Tavily's own AI summary of results — clean and dense
                "include_domains": trusted_domains,
            }
        )

        # Use Tavily's answer as lead context + individual snippets
        tavily_answer = response.json().get("answer", "")

        for r in response.json().get("results", []):
            url = r.get("url", "")
            if url in urls:
                continue
            urls.append(url)
            items.append(
                f"Title: {r.get('title')}\n"
                f"Summary: {r.get('content', '')}\n"
                f"URL: {url}"
            )

        # Prepend Tavily's synthesized answer as extra context for the LLM
        if tavily_answer:
            items.insert(0, f"[Tavily Summary]\n{tavily_answer}")

    print(f"  → {len(items)} articles fetched\n")
    print(items)
    return {**state, "news_items": items, "source_urls": urls}