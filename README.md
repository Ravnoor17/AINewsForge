# AINewsForge

> An agentic LinkedIn content pipeline that fetches verified AI/ML news, generates technically sharp posts, fact-checks every claim, and publishes to LinkedIn — all through a stateful LangGraph multi-node graph.

---

## Table of Contents

- [About](#about)
- [Pipeline Architecture](#pipeline-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [Post Structure](#post-structure)
- [Quality Gates](#quality-gates)
- [Roadmap](#roadmap)

---

## About

AINewsForge is a fully agentic system built with **LangGraph** that runs as a directed graph of specialized nodes. Each node operates on a shared `AgentState` — fetching news, writing posts, verifying claims, reviewing quality, and publishing to LinkedIn.

The system has two hard abort points:

- If **fact verification scores below 70/100**, the pipeline stops and does not post
- If **post generation fails after 3 retries**, the pipeline stops

Quality review runs as a **logging-only step** — it gives you visibility into post quality without blocking the pipeline.

---

## Pipeline Architecture

```
[fetch_news] → [generate_post] → [fact_check] → [review_post] → [post_to_linkedin]
                     ↓                ↓
                   (END)            (END)
              on error        score < 70/100
```

### Nodes

| Node | Responsibility |
|---|---|
| `fetch_news` | Queries Tavily across 3 targeted queries, filters to trusted AI domains, returns articles with full summaries |
| `generate_post` | Groq `llama-3.3-70b-versatile` writes a structured LinkedIn post from verified articles |
| `fact_check` | Extracts 3 standalone claims → searches each on Tavily → LLM semantic verification → rewrites contradicted claims → checks source URL health |
| `review_post` | Second LLM pass scores the post on hook sharpness, technical substance, engineering insight, structure, and hashtag quality. Logs only — never blocks. |
| `post_to_linkedin` | Posts to LinkedIn REST API with human `y/n` confirmation (skipped on `--dry-run`) |

---

## Tech Stack

| Component | Tool |
|---|---|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM — writing, fact-check, review | Groq `llama-3.3-70b-versatile` |
| News search + claim verification | [Tavily API](https://tavily.com) — free tier, 1,000 calls/month |
| LinkedIn publishing | LinkedIn REST API `v202601` |
| Config management | `python-dotenv` |

---

## Project Structure

```
AINewsForge/
├── agent.py                  ← LangGraph graph + entry point
├── state.py                  ← Shared AgentState TypedDict
├── get_token.py              ← One-time LinkedIn OAuth flow
├── requirements.txt
├── .env
├── README.md
└── nodes/
    ├── __init__.py
    ├── news_fetcher.py       ← fetch_news node
    ├── post_generator.py     ← generate_post node
    ├── fact_checker.py       ← fact_check node
    ├── quality_reviewer.py   ← review_post node
    └── linkedin_poster.py    ← post_to_linkedin node
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/yourname/ainewsforge.git
cd ainewsforge
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Get API keys

| Key | Source | Cost |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | Free |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | Free — 1,000 calls/month |
| `access_token` + `person_urn` | Run `get_token.py` (see below) | Free |

### 3. LinkedIn OAuth — one time setup

1. Go to [LinkedIn Developer Portal](https://developer.linkedin.com) and create an app
2. Under **Products**, add:
   - `Share on LinkedIn`
   - `Sign In with LinkedIn using OpenID Connect`
3. Under **Auth → OAuth 2.0 settings**, add redirect URL:
   ```
   http://localhost:8000/callback
   ```
4. Run the token generator:
   ```bash
   python get_token.py
   ```
5. Copy the printed `ACCESS_TOKEN` and `PERSON_URN` into your `.env`

> **Note:** LinkedIn access tokens expire every **60 days**. Re-run `get_token.py` to refresh.

---

## Configuration

Create a `.env` file in the project root:

```env
# LinkedIn App credentials
client_id=your_linkedin_client_id
client_secret=your_linkedin_client_secret

# LinkedIn user credentials (from get_token.py)
access_token=your_linkedin_access_token
person_urn=urn:li:person:xxxxxxxx

# LLM
groq_api_key=your_groq_api_key

# News search + fact verification
TAVILY_API_KEY=your_tavily_api_key
```

---

## Usage

```bash
# Dry run — generate, fact-check, and review without posting
python agent.py --dry-run

# Full run — complete pipeline with LinkedIn posting
python agent.py
```

### Example output

```
🤖 AINewsForge Agent starting...

  → Searching latest AI news via Tavily...
  → 9 articles fetched

  → Generating post (attempt 1/3)...
  → Post generated

--- GENERATED POST ---
Mistral released a 7B model that matches GPT-4 on coding benchmarks at 10x lower inference cost.
...
----------------------

  → Extracting claims...
  → Found 3 claims

  → Checking: Mistral 7B matches GPT-4 on HumanEval benchmark
     → 3 relevant results found
     → Verdict: SUPPORT

  → Fact score   : 100.0/100
  → URL health   : 100.0%

  → Running quality review...
  → Score      : 8/10
  → Verdict    : APPROVE
  → Suggestions: Add inference latency numbers for stronger hook

Post this to LinkedIn? (y/n): y
✅ Posted successfully!
```

---

## Post Structure

Every generated post enforces this structure:

| Section | Description |
|---|---|
| **Hook** | One sharp sentence — a surprising stat, concrete number, or bold claim. Never a question. |
| **Context** | 4–5 lines naming the model, framework, paper, or company with benchmarks |
| **Why It Matters** | 4–5 lines on concrete engineering implications for builders today |
| **Your Take** | 2–3 lines of opinionated insight or prediction |
| **Hashtags** | 3–5 relevant, non-generic tags at the end |

**Rules enforced in prompt:**
- Between 350–500 words
- No emojis
- No buzzwords: *game-changer, revolutionize, exciting, the future is here, delve*
- No fluff openers
- Non-obvious terms explained inline in plain language

---

## Quality Gates

| Gate | Condition | Action |
|---|---|---|
| Post generation | Fails after 3 retries | Abort pipeline |
| Fact check | Score < 70/100 | Abort pipeline |
| Contradicted claims | Any claim marked CONTRADICT | Auto-rewrite using evidence |
| Unclear claims | Any claim marked UNCLEAR | Softened with "reportedly" / "early reports suggest" |
| Quality review | Score < 8/10 or buzzwords detected | Log only — does not block posting |

---

## Roadmap

- [ ] Token auto-refresh before 60-day LinkedIn expiry
- [ ] Langfuse tracing for full pipeline observability
- [ ] Daily scheduler via APScheduler or cron
- [ ] Slack / email notification on post success or failure
- [ ] Post history log to avoid duplicate topics across runs
- [ ] Multi-platform support — Twitter/X and Bluesky

---