import os
import requests
from state import AgentState
from dotenv import load_dotenv
load_dotenv()

def post_to_linkedin(state: AgentState) -> AgentState:
    if state.get("dry_run"):
        print("🧪 Dry run — not posting to LinkedIn.")
        return {**state, "posted": False}

    confirm = input("Post this to LinkedIn? (y/n): ")
    if confirm.lower() != "y":
        print("Aborted.")
        return {**state, "posted": False}

    token = os.getenv("access_token")
    urn = os.getenv("person_urn")

    response = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202601",
        },
        json={
            "author": urn,
            "lifecycleState": "PUBLISHED",
            "visibility": "PUBLIC",
            "commentary": state["post_text"],
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            }
        }
    )

    if response.status_code == 201:
        print("✅ Posted successfully!")
        return {**state, "posted": True}
    else:
        print(f"❌ Failed: {response.status_code} — {response.text}")
        return {**state, "posted": False, "error": response.text}