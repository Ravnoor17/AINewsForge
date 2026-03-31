import os
import json
from groq import Groq
from state import AgentState
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.getenv("groq_api_key"))

REVIEW_PROMPT = """You are a strict LinkedIn content reviewer for an AI/ML engineer's personal brand.

Review the post and return ONLY this JSON:
{
  "score": <integer 1-10>,
  "verdict": "APPROVE" or "REJECT",
  "issues": ["issue1"],
  "suggestions": ["suggestion1"]
}

REJECT if score < 8, or contains buzzwords, generic hook, no technical details, or sounds like a press release."""

import re

def review_post(state: AgentState) -> AgentState:
    print("  → Running quality review...")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": REVIEW_PROMPT},
            {"role": "user", "content": f"Review this LinkedIn post:\n\n{state['post_text']}"}
        ],
        max_tokens=300,
        temperature=0.3,
    )
    
    raw = response.choices[0].message.content.strip()
    
    # Debug — see what the model actually returned
    print(f"  → Raw response: {raw[:200]}")
    
    try:
        # Try direct parse first
        review = json.loads(raw)
    except Exception:
        try:
            # Extract JSON block if wrapped in markdown or extra text
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            review = json.loads(match.group()) if match else {}
        except Exception:
            review = {}

    if not review:
        review = {"score": 0, "verdict": "REJECT", "issues": ["Parsing failed"], "suggestions": []}

    print(f"  → Score      : {review.get('score')}/10")
    print(f"  → Verdict    : {review.get('verdict')}")
    if review.get("issues"):
        print(f"  → Issues     : {', '.join(review.get('issues', []))}")
    if review.get("suggestions"):
        print(f"  → Suggestions: {', '.join(review.get('suggestions', []))}")
    print()

    return {
        **state,
        "review_score": review.get("score", 0),
        "review_verdict": review.get("verdict", "REJECT"),
    }