import os, json, time, requests
from playwright.sync_api import sync_playwright

# === CONFIG ===
API_KEY = os.getenv("API_FOOTBALL_KEY")
X_USER = os.getenv("X_USER")
X_PASS = os.getenv("X_PASS")

MY_NATIONS = ["Spain", "Germany", "Portugal", "France", "England", "Italy", "Netherlands", "Belgium"]
MY_CLUBS = ["Real Madrid", "Barcelona", "Atletico Madrid", "Sevilla", "Real Betis", "Villarreal", "Arsenal", "Manchester City", "Liverpool", "Chelsea", "Bayern Munich", "Paris SG", "PSG"]

SEEN_FILE = "goals_seen.json"

HEADERS = {"x-apisports-key": API_KEY}

def load_seen():
    try:
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f)

def is_my_team(name):
    name = name.lower()
    for t in MY_NATIONS + MY_CLUBS:
        if t.lower() in name or name in t.lower():
            return True
        # handle PSG special
        if t == "Paris SG" and "psg" in name:
            return True
    return False

def format_goal(home, away, sh, sa, player, minute, assist=None):
    player = player or "Unknown"
    if not player or player == "None":
        player = "Unknown"
    txt = f"GOAL!\n\n{home} {sh}-{sa} {away}\n{player} {minute}'\n\n#BallpointLive"
    if assist:
        txt += f"\nAssist: {assist}"
    return txt

def post_tweet(text):
    print(f"TWEETING: {text[:80]}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://x.com/login", timeout=60000)
        page.wait_for_timeout(3000)
        
        # NEW SELECTORS - X changed UI
        try:
            # try new UI
            page.wait_for_selector('input[autocomplete="username"]', timeout=10000)
            page.fill('input[autocomplete="username"]', X_USER)
        except:
            # fallback old UI
            page.fill('input[name="text"]', X_USER)
        
        page.get_by_role("button", name="Next").click()
        page.wait_for_timeout(3000)
        
        page.wait_for_selector('input[name="password"], input[type="password"]', timeout=10000)
        page.fill('input[name="password"], input[type="password"]', X_PASS)
        page.get_by_role("button", name="Log in").click()
        page.wait_for_timeout(5000)

        # Tweet
        page.goto("https://x.com/compose/tweet", timeout=60000)
        page.wait_for_timeout(3000)
        page.wait_for_selector('div[role="textbox"]', timeout=15000)
        page.fill('div[role="textbox"]', text)
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="Post").first.click()
        page.wait_for_timeout(5000)
        browser.close()
        print("Tweeted OK")

def main():
    print("Ballpoint v5.8.5 starting")
    seen = load_seen()
    
    # LIVE
    r = requests.get("https://v3.football.api-sports.io/fixtures?live=all", headers=HEADERS, timeout=20)
    data = r.json()
    fixtures = data.get("response", [])
    print(f"LIVE API: {len(fixtures)} fixtures, errors: {data.get('errors', [])}")
    print(f"Combined: {len(fixtures)}")
    
    targets = []
    for f in fixtures:
        home = f['teams']['home']['name']
        away = f['teams']['away']['name']
        if is_my_team(home) or is_my_team(away):
            status = f['fixture']['status']['short']
            targets.append(f)
            print(f"-> TARGET: {home} vs {away} [{status}] {f['goals']['home']}-{f['goals']['away']}")

    print(f"Total for YOUR teams: {len(targets)}")
    
    for f in targets:
        fid = f['fixture']['id']
        home = f['teams']['home']['name']
        away = f['teams']['away']['name']
        
        # get events
        er = requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fid}", headers=HEADERS, timeout=20)
        events = er.json().get("response", [])
        
        for ev in events:
            if ev['type'] == 'Goal':
                key = f"{fid}-{ev['time']['elapsed']}-{ev['player']['id']}"
                if key in seen:
                    continue
                sh = f['goals']['home']
                sa = f['goals']['away']
                player = ev['player'].get('name')
                minute = ev['time']['elapsed']
                assist = ev.get('assist', {}).get('name')
                
                tweet = format_goal(home, away, sh, sa, player, minute, assist)
                try:
                    post_tweet(tweet)
                    seen.append(key)
                    save_seen(seen)
                except Exception as e:
                    print(f"Tweet failed: {e}")
                    # don't mark as seen if failed, so retry next run
                    continue

if __name__ == "__main__":
    main()
