from typing import TypedDict, Optional

from typing import TypedDict, Optional

class AgentState(TypedDict):
    # Core pipeline data
    news_items: list[str]        # fetcher → generator
    source_urls: list[str]       # fetcher → fact_checker
    post_text: str               # generator → fact_checker → reviewer → poster

    # Routing flags
    fact_verified: bool          # fact_checker → router
    review_verdict: str          # reviewer → router
    review_score: int            # reviewer → router

    # Final status
    posted: bool
    error: Optional[str]
    dry_run: bool