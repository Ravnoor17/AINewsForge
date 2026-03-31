# get_token.py
import urllib.parse
import threading
import webbrowser
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = os.getenv("client_id")
CLIENT_SECRET = os.getenv("client_secret")
REDIRECT_URI = "http://localhost:8000/callback"
SCOPE = "openid profile w_member_social"

print("client_id:", CLIENT_ID)
print("client_secret:", CLIENT_SECRET)

auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Got it! You can close this tab.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code found.")
    
    def log_message(self, format, *args):
        pass  # suppress server logs

def get_auth_url():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": "random_state_123"
    }
    return "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode(params)

def exchange_code_for_token(code):
    response = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return response.json()

def get_person_urn(access_token):
    response = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    data = response.json()
    return data.get("sub")  # this is your person URN ID

if __name__ == "__main__":
    # Step 1 — start local server
    server = HTTPServer(("localhost", 8000), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    # Step 2 — open browser for LinkedIn login
    url = get_auth_url()
    print(f"Opening browser for LinkedIn login...")
    webbrowser.open(url)

    # Step 3 — wait for callback
    thread.join()

    if not auth_code:
        print("Failed to get auth code.")
        exit(1)

    # Step 4 — exchange code for token
    print("Exchanging code for access token...")
    token_data = exchange_code_for_token(auth_code)
    access_token = token_data.get("access_token")

    if not access_token:
        print("Error:", token_data)
        exit(1)

    # Step 5 — get your person URN
    person_id = get_person_urn(access_token)
    person_urn = f"urn:li:person:{person_id}"

    print("\n--- SAVE THESE ---")
    print(f"ACCESS_TOKEN={access_token}")
    print(f"PERSON_URN={person_urn}")
    print(f"Expires in: {token_data.get('expires_in', 'N/A')} seconds (~60 days)")