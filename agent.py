import argparse
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from state import AgentState
from nodes.news_fetcher import fetch_news
from nodes.post_generator import generate_post
from nodes.fact_checker import fact_check
from nodes.quality_reviewer import review_post
from nodes.linkedin_poster import post_to_linkedin

load_dotenv()

# ── Conditional edge functions ─────────────────────────────────────────────────

def route_after_generation(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    return "fact_check"

def route_after_fact_check(state: AgentState) -> str:
    if not state.get("fact_verified"):
        print("❌ Fact check failed — aborting.")
        return "end"
    return "review_post"

# def route_after_review(state: AgentState) -> str:
#     if state.get("review_verdict") != "APPROVE":
#         print("❌ Quality review failed — aborting.")
#         return "end"
#     return "post_to_linkedin"

# ── Build graph ────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("fetch_news", fetch_news)
    graph.add_node("generate_post", generate_post)
    graph.add_node("fact_check", fact_check)
    graph.add_node("review_post", review_post)
    graph.add_node("post_to_linkedin", post_to_linkedin)

    graph.set_entry_point("fetch_news")
    graph.add_edge("fetch_news", "generate_post")

    graph.add_conditional_edges("generate_post", route_after_generation, {
        "fact_check": "fact_check",
        "end": END
    })
    graph.add_conditional_edges("fact_check", route_after_fact_check, {
        "review_post": "review_post",
        "end": END
    })
    # graph.add_conditional_edges("review_post", route_after_review, {
    #     "post_to_linkedin": "post_to_linkedin",
    #     "end": END
    # })
    graph.add_edge("review_post", "post_to_linkedin")

    graph.add_edge("post_to_linkedin", END)

    return graph.compile()

# ── Entry point ────────────────────────────────────────────────────────────────

def run(dry_run: bool = False):
    print("🤖 NewsForge Agent starting...\n")

    initial_state: AgentState = {
        "news_items": [],
        "source_urls": [],
        "post_text": "",
        "fact_verified": False,
        "review_score": 0,
        "review_verdict": "",
        "posted": False,
        "error": None,
        "dry_run": dry_run,
    }

    app = build_graph()
    final_state = app.invoke(initial_state)

    print("\n--- FINAL STATE ---")
    print(f"Post     :\n{final_state['post_text']}")
    print(f"Verified : {final_state['fact_verified']}")
    print(f"Score    : {final_state['review_score']}/10")
    print(f"Posted   : {final_state['posted']}")
    if final_state.get("error"):
        print(f"Error    : {final_state['error']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
