import os
from groq import Groq
from state import AgentState
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.getenv("groq_api_key"))

SYSTEM_PROMPT = """You are a senior AI/ML engineer with deep expertise in LLMs, agentic systems, and ML infrastructure.
You write LinkedIn posts that other engineers actually want to read — technical, direct, and substantive.

STRUCTURE (follow this exactly):
1. HOOK (line 1): One sharp, specific sentence. A surprising fact, a concrete number, or a bold claim. NOT a question. NOT "Are we...". Make people stop scrolling.
2. CONTEXT (4-5 lines): What happened. Be specific — name the model, framework, paper, or company. Include numbers/benchmarks if available.
3. WHY IT MATTERS (4-5 lines): The real technical implication. What does this change for engineers building systems today? Be concrete, not abstract.
4. YOUR TAKE (2-3 lines): One sharp engineering insight or prediction. This is your voice — make it opinionated and specific.
5. HASHTAGS: 3-5 only. Relevant, not generic.

RULES:
- Explain even the technical details and make it accessible to engineers who aren't deep in the weeds of AI research.
- If a method, technique, or term is non-obvious, add 1 sentence explaining what it does in plain terms before moving on.
- Add two blank lines after every structure element — white space is critical for readability on LinkedIn mobile.
- Between 250-300 words total. Do not write short posts.
- No emojis
- No buzzwords: "game-changer", "revolutionize", "exciting", "the future is here", "delve"
- No fluff openers like "In today's world..." or "As AI continues to..."
- Do NOT include any labels, headers, reasoning, or preamble
- Output ONLY the raw post text
"""

def _extract_post(raw: str) -> str:
    for marker in ["**LinkedIn Post**", "LinkedIn Post:", "---\n**LinkedIn Post"]:
        if marker in raw:
            return raw.split(marker)[-1].strip()
    if "---" in raw:
        return raw.split("---")[-1].strip()
    return raw.strip()

def generate_post(state: AgentState) -> AgentState:
    if not state["news_items"]:
        return {**state, "error": "No news items to generate post from."}

    news_text = "\n\n---\n\n".join(state["news_items"])

    for attempt in range(1, 4):
        try:
            print(f"  → Generating post (attempt {attempt}/3)...")
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"Here are real verified AI news articles:\n\n{news_text}\n\n"
                        "Pick the single most technically interesting one and write a LinkedIn post. "
                        "Write between 250-300 words. "
                        "Output ONLY the raw post — no reasoning, no headers, no labels."
                    )}
                ],
                max_tokens=1500,
                temperature=0.7,
            )
            post = _extract_post(response.choices[0].message.content)
            print("  → Post generated\n")
            print(post)
            return {**state, "post_text": post}
        except Exception as e:
            print(f"  ⚠️  Attempt {attempt} failed: {e}")

    breakpoint()

    return {**state, "error": "Post generation failed after 3 attempts."}