import os
import requests
import re
from groq import Groq
from state import AgentState
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("groq_api_key"))


# -----------------------------
# 1. Claims with Context
# -----------------------------
def _enrich_claims_with_context(post_text):
    context_prompt = f"""
Post:
{post_text}

Extract exactly 5 key factual claims from this post.
- Only extract verifiable facts (model names, numbers, benchmarks, releases)
- Ignore opinions, predictions, and subjective statements
- Each claim must be standalone and include the subject/company/model name
- Keep each claim short and precise.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": context_prompt}],
        temperature=0.0,
        max_tokens=400,
    )

    enriched = response.choices[0].message.content.strip().split("\n")
    return [c.strip("- ").strip() for c in enriched if c.strip()]




# -----------------------------
# 2. Tavily Search
# -----------------------------
def _search_tavily(query: str, api_key: str):
    try:
        res = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "days": 14,
                "max_results": 3,
            },
            timeout=10,
        )
        return res.json().get("results", [])
    except Exception:
        return []


# -----------------------------
# 3. Filter Relevant Results
# -----------------------------

def _get_keywords(claim):
    stopwords = {
        "the", "is", "and", "of", "to", "a", "in", "for", "with",
        "on", "by", "an", "be", "this", "that", "it", "as", "at"
    }

    words = claim.lower().split()

    keywords = [
        w for w in words
        if w not in stopwords and len(w) > 3
    ]

    return keywords[:6]

def _filter_results(results, claim):
    keywords = _get_keywords(claim)

    filtered = []
    for r in results:
        text = (r.get("title", "") + " " + r.get("content", "")).lower()
        if any(k in text for k in keywords):
            filtered.append(r)

    print(f"     → {len(filtered)} relevant results found out of {len(results)} total")
    return filtered


# -----------------------------
# 4. LLM Semantic Verification
# -----------------------------
def _verify_with_llm(claim: str, results):
    context = "\n\n".join(
        [f"{r.get('title')}\n{r.get('content')}" for r in results[:3]]
    )

    prompt = f"""
Claim: {claim}

Evidence:
{context}

Does the evidence SUPPORT, CONTRADICT, or is it UNCLEAR?

Answer ONLY one word: SUPPORT/ CONTRADICT / UNCLEAR
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=10,
    )

    return response.choices[0].message.content.strip().upper()


# -----------------------------
# 5. Rewrite Post with Evidence
# -----------------------------
def _rewrite_post_with_evidence(original_post, claim_results):
    context = "\n\n".join([
        f"Claim: {c['claim']}\nVerdict: {c['verdict']}\nEvidence: {c['evidence']}"
        for c in claim_results
    ])

    prompt = f"""
You are an AI editor.

Original Post:
{original_post}

Fact-check results:
{context}

Instructions:
- Keep supported claims
- Fix contradicted claims using evidence
- Soften unclear claims (use "reportedly", "early reports suggest")
- Keep tone engaging like LinkedIn
- Do NOT hallucinate

Return only the corrected post.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=400,
    )

    return response.choices[0].message.content.strip()


# -----------------------------
# 6. URL Health Check (Non-blocking)
# -----------------------------
def _check_urls(urls):
    results = []

    for url in urls:
        try:
            r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                results.append(f"[URL OK] {url}")
            else:
                results.append(f"[URL {r.status_code}] {url}")
        except Exception as e:
            results.append(f"[URL ERROR] {url} — {e}")

    return results


# -----------------------------
# 7. MAIN FACT CHECK FUNCTION
# -----------------------------
def fact_check(state: AgentState) -> AgentState:
    tavily_key = os.getenv("TAVILY_API_KEY")

    post_text = state["post_text"]
    source_urls = state.get("source_urls", [])

    print("  → Extracting claims...")
    claim_response = _enrich_claims_with_context(post_text)
    all_claims = "\n".join(claim_response)
    claims = re.findall(r"\d+\.\s+(.*)", all_claims)

    claim_results = []
    total_score = 100 

    print(f"  → Found {len(claims)} claims")

    for claim in claims:
        print(f"\n  → Checking: {claim}")

        all_results = []
        all_results.extend(_search_tavily(claim, tavily_key))

        # Deduplicate
        seen = set()
        unique_results = []
        for r in all_results:
            url = r.get("url")
            if url and url not in seen:
                seen.add(url)
                unique_results.append(r)

        filtered = _filter_results(unique_results, claim)

        verdict = _verify_with_llm(claim, filtered) if filtered else "UNCLEAR"
        print(f"     - {claim} → {verdict}")

        evidence_text = "\n".join([
            f"{r.get('title')} — {r.get('url')}"
            for r in filtered])

        claim_results.append({
            "claim": claim,
            "verdict": verdict,
            "evidence": evidence_text
        })

        # Scoring
        if verdict == "SUPPORT":
            continue  # no penalty
        else:
            total_score -= (1 / len(claims)) * 100  # small penalty

    # -----------------------------
    # URL checks (non-blocking)
    # -----------------------------
    print("\n  → Checking URLs...")
    url_results = _check_urls(source_urls)
    correct_urls = sum(1 for r in url_results if r.startswith("[URL OK]"))
    correct_url_percentage = (correct_urls / len(source_urls)) * 100 if source_urls else 100
    
    # -----------------------------
    # Final summary
    # -----------------------------
    print(f"     → {total_score:.1f}% factual accuracy based on claims")
    print(f"     → {correct_url_percentage:.1f}% of URLs are healthy")
    print(f"     → {100 - correct_url_percentage:.1f}% of URLs are broken or slow\n")

    # -----------------------------
    # Decide if rewrite needed
    # -----------------------------
    needs_correction = any(
        c["verdict"] in ["CONTRADICT", "UNCLEAR"]
        for c in claim_results
    )

    if needs_correction:
        print("\n  → Rewriting post based on evidence...")
        final_post = _rewrite_post_with_evidence(post_text, claim_results)
    else:
        final_post = post_text

    print("fact_score :=", total_score)
    print("\nfact_verified :=", total_score == 100)
    print("\nfact_evidence :=", claim_results)
    print("\npost_text :=", final_post)
    print("\ncorrect_url_percentage :=", correct_url_percentage)
 
    return {
        **state,
        "post_text": final_post,
        "fact_verified": total_score >= 80,
    }