import os, json, requests, time
from datetime import datetime, timezone

# For free posting
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except:
    PLAYWRIGHT_AVAILABLE = False

API_KEY = os.getenv("API_FOOTBALL_KEY")
API_HOST = "v3.football.api-sports.io"

TEAMS = {
    541: "Real Madrid", 529: "Barcelona", 530: "Atletico Madrid",
    33: "Man United", 50: "Man City", 42: "Arsenal", 49: "Chelsea",
    40: "Liverpool", 47: "Tottenham", 34: "Newcastle", 66: "Aston Villa",
    85: "PSG", 81: "Marseille", 157: "Bayern Munich", 165: "Dortmund",
    505: "Inter Milan", 9568: "Inter Miami", 2939: "Al Nassr", 2938: "Al Hilal"
}
TEAM_IDS = list(TEAMS.keys())
STATE_FILE = "state.json"

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"posted_ids": [], "last_post_time": None, "daily_count": 0, "daily_date": ""}
    with open(STATE_FILE, "r") as f: return json.load(f)

def save_state(s):
    with open(STATE_FILE, "w") as f: json.dump(s, f)

def can_post(state):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state["daily_date"] != today:
        print(f"New day {today}, clearing old data")
        state["posted_ids"] = []
        state["daily_count"] = 0
        state["daily_date"] = today
        save_state(state)
    if state["daily_count"] >= 25: return False
    if state["last_post_time"]:
        last = datetime.fromisoformat(state["last_post_time"])
        if (datetime.now(timezone.utc) - last).total_seconds() / 60 < 5: return False
    return True

# --- FREE X POSTING FUNCTION (Playwright) ---
def post_to_x(message):
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not installed, simulating post:")
        print(message)
        return True

    # Get creds from GitHub secrets
    username = os.getenv("X_USERNAME")
    password = os.getenv("X_PASSWORD")
    
    if not username or not password:
        print("No X_USERNAME/X_PASSWORD set, just printing")
        print(message)
        return True

    print(f"Trying to post to X as {username}...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            
            # Try to load saved session if exists
            if os.path.exists("auth.json"):
                try:
                    context = browser.new_context(storage_state="auth.json")
                except: pass

            page = context.new_page()
            page.goto("https://x.com/login", timeout=60000)
            time.sleep(3)

            # If already logged in, go to compose
            if "home" in page.url or "compose" in page.url or os.path.exists("auth.json"):
                page.goto("https://x.com/compose/tweet")
            else:
                # Login flow
                page.fill('input[name="text"]', username)
                page.get_by_text("Next").click()
                time.sleep(2)
                # Sometimes it asks for email/phone
                try:
                    page.fill('input[type="password"]', password, timeout=5000)
                    page.get_by_text("Log in").click()
                except:
                    # Enter password on next page
                    page.fill('input[name="password"]', password)
                    page.get_by_text("Log in").click()
                time.sleep(5)
                # Save session for next time
                context.storage_state(path="auth.json")
                page.goto("https://x.com/compose/tweet")
            
            time.sleep(4)
            # Type tweet
            page.fill('div[role="textbox"]', message)
            time.sleep(1)
            page.get_by_test_id("tweetButtonInline").click()
            time.sleep(5)
            print("Posted!")
            browser.close()
            return True
    except Exception as e:
        print(f"Post failed: {e}")
        # Fail safe: print message so you can see it in logs
        print(message)
        return False

def main():
    state = load_state()
    if not can_post(state): return
    headers = {"x-apisports-key": API_KEY}
    try:
        resp = requests.get(f"https://{API_HOST}/fixtures?live=all", headers=headers, timeout=20).json()
    except Exception as e:
        print(f"API error: {e}"); return

    for fixture in resp.get("response", []):
        if fixture["teams"]["home"]["id"] not in TEAM_IDS and fixture["teams"]["away"]["id"] not in TEAM_IDS: continue
        fid = fixture["fixture"]["id"]
        sh = fixture["goals"]["home"] or 0
        sa = fixture["goals"]["away"] or 0
        hn = fixture["teams"]["home"]["name"]
        an = fixture["teams"]["away"]["name"]
        status = fixture["fixture"]["status"]["short"]
        cur = fixture["fixture"]["status"]["elapsed"] or 0

        try:
            ev_url = f"https://{API_HOST}/fixtures/events?fixture={fid}"
            events = requests.get(ev_url, headers=headers, timeout=20).json().get("response", [])
        except: events = []

        for ev in events:
            et = ev["time"]["elapsed"]
            if et is None: continue
            eid = f"{fid}-{et}-{ev['player']['id']}-{ev['type']}-{ev['detail']}"
            if eid in state["posted_ids"]: continue
            if cur - et > 10:
                print(f"Skip old {et}' now {cur}'")
                state["posted_ids"].append(eid); continue
            
            msg = None
            if ev["type"] == "Goal":
                scorer = ev["player"]["name"]
                assist = ev.get("assist", {}).get("name")
                if assist and assist != scorer:
                    msg = f"🚨 GOAL! {et}'\n{hn} {sh}-{sa} {an}\n⚽️ {scorer}\n🎯 Assist: {assist}"
                else:
                    msg = f"🚨 GOAL! {et}'\n{hn} {sh}-{sa} {an}\n⚽️ {scorer}"
            elif ev["type"] == "Card" and "Red" in ev["detail"]:
                msg = f"🟥 RED CARD! {et}'\n{hn} {sh}-{sa} {an}\nPlayer: {ev['player']['name']} ({ev['team']['name']})"

            if msg and post_to_x(msg):
                state["posted_ids"].append(eid)
                state["last_post_time"] = datetime.now(timezone.utc).isoformat()
                state["daily_count"] += 1
                save_state(state)
                return

        if status == "FT":
            ft_id = f"{fid}-FT"
            if ft_id not in state["posted_ids"]:
                msg = f"⏱️ FULL TIME!\n{hn} {sh}-{sa} {an}"
                if post_to_x(msg):
                    state["posted_ids"].append(ft_id)
                    state["last_post_time"] = datetime.now(timezone.utc).isoformat()
                    state["daily_count"] += 1
                    save_state(state)
                    return
    save_state(state)

if __name__ == "__main__": main()
