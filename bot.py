# Ballpoint X Bot v5.1 - FIXED SYNTAX
import os, json, time, requests
from playwright.sync_api import sync_playwright

LEAGUES = {
    "LALIGA": ["Real Madrid", "Barcelona", "Atletico Madrid", "Athletic Club", "Villarreal"],
    "PREMIER_LEAGUE": ["Arsenal", "Man City", "Liverpool", "Chelsea", "Man Utd", "Newcastle", "Tottenham"],
    "NATIONS_LEAGUE": ["Spain", "Germany", "Portugal", "France", "England", "Italy", "Netherlands", "Belgium", "Greece"]
}
API_KEY = os.getenv("API_FOOTBALL_KEY")
X_USER = os.getenv("X_USERNAME")
X_PASS = os.getenv("X_PASSWORD")
STATE_FILE = "state.json"
AUTH_FILE = "auth.json"
TAG = "#BallpointLive"
scorers_today = {}

def format_goal(th, ta, sh, sa, scorer, minute, assist=None):
    count = scorers_today.get(scorer, 0) + 1
    scorers_today[scorer] = count
    score_line = f"{th} {sh}-{sa} {ta}"
    assist_text = f" (Assist: {assist})" if assist else ""
    if count == 1:
        return f"GOAL!\n\n{score_line}\n{scorer} {minute}'{assist_text}\n\n{TAG}"
    elif count == 2:
        return f"HE SCORES AGAIN! BRACE!\n\n{score_line}\n{scorer} {minute}'{assist_text} - On FIRE!\n\n{TAG}"
    else:
        return f"HAT-TRICK HERO!\n\n{score_line}\n{scorer} {minute}'{assist_text} - UNSTOPPABLE!\n\n{TAG}"

def format_kickoff(th, ta):
    return f"KICKOFF!\n\n{th} vs {ta} is underway!\nPredictions?\n\n{TAG}"

def format_halftime(th, ta, sh, sa):
    return f"HALFTIME:\n\n{th} {sh}-{sa} {ta}\nThoughts so far?\n\n{TAG}"

def format_fulltime(th, ta, sh, sa):
    return f"FT:\n\n{th} {sh}-{sa} {ta}\nWhat a game! Thoughts?\n\n{TAG}"

def format_red_card(th, ta, sh, sa, player, minute):
    return f"RED CARD!\n\n{th} {sh}-{sa} {ta}\n{player} {minute}' - Sent off!\n\n{TAG}"

def format_40(th, ta):
    return f"40' - Still goalless!\n\n{th} 0-0 {ta}\nThis is TENSE... who breaks the deadlock?\n\n{TAG}"

def format_80(th, ta):
    return f"80' - STILL 0-0!\n\n{th} vs {ta} is going CRAZY!\nLate winner coming?\n\n{TAG}"

def post_tweet(text):
    print(f"TWEETING: {text[:60]}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=AUTH_FILE) if os.path.exists(AUTH_FILE) else browser.new_context()
        page = context.new_page()
        if not os.path.exists(AUTH_FILE):
            print("Logging in fresh...")
            page.goto("https://x.com/login")
            page.wait_for_timeout(3000)
            page.fill('input[name="text"]', X_USER)
            page.locator('span:has-text("Next")').click()
            page.wait_for_timeout(2000)
            page.fill('input[name="password"]', X_PASS)
            page.locator('span:has-text("Log in")').click()
            page.wait_for_timeout(5000)
            context.storage_state(path=AUTH_FILE)
        page.goto("https://x.com/compose/tweet")
        page.wait_for_timeout(3000)
        if "login" in page.url:
            print("Cookie expired, deleting auth...")
            if os.path.exists(AUTH_FILE): os.remove(AUTH_FILE)
            browser.close()
            return post_tweet(text)
        page.fill('div[data-testid="tweetTextarea_0"]', text)
        page.wait_for_timeout(1000)
        page.click('div[data-testid="tweetButtonInline"]')
        page.wait_for_timeout(4000)
        browser.close()
        print("Posted!")

def main():
    print("Ballpoint Bot v5.1 starting...")
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'w') as f: json.dump({}, f)
    with open(STATE_FILE, 'r') as f: posted = json.load(f)
    headers = {"x-apisports-key": API_KEY}
    resp = requests.get("https://v3.football.api-sports.io/fixtures?live=all", headers=headers)
    data = resp.json()
    print(f"Live: {len(data.get('response',[]))}")
    for fix in data.get('response', []):
        home = fix['teams']['home']['name']
        away = fix['teams']['away']['name']
        fid = str(fix['fixture']['id'])
        status = fix['fixture']['status']['short']
        elapsed = fix['fixture']['status']['elapsed'] or 0
        sh = fix['goals']['home']
        sa = fix['goals']['away']
        print(f"{home} vs {away} {sh}-{sa} {elapsed}' {status}")
        key_kick = f"{fid}_kick"
        if status == "1H" and elapsed <= 5 and key_kick not in posted:
            post_tweet(format_kickoff(home, away))
            posted[key_kick] = True
        key_40 = f"{fid}_40"
        if elapsed == 40 and sh == 0 and sa == 0 and key_40 not in posted:
            post_tweet(format_40(home, away))
            posted[key_40] = True
        key_80 = f"{fid}_80"
        if elapsed == 80 and sh == 0 and sa == 0 and key_80 not in posted:
            post_tweet(format_80(home, away))
            posted[key_80] = True
        events = requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fid}", headers=headers).json()
        for ev in events.get('response', []):
            if ev['type'] == 'Goal':
                key = f"{fid}_{ev['time']['elapsed']}_{ev['player']['name']}"
                if key not in posted:
                    assist = ev['assist']['name'] if ev['assist']['name'] else None
                    post_tweet(format_goal(home, away, sh, sa, ev['player']['name'], ev['time']['elapsed'], assist))
                    posted[key] = True
        if status == "HT" and f"{fid}_ht" not in posted:
            post_tweet(format_halftime(home, away, sh, sa))
            posted[f"{fid}_ht"] = True
        if status in ["FT", "AET", "PEN"] and f"{fid}_ft" not in posted:
            post_tweet(format_fulltime(home, away, sh, sa))
            posted[f"{fid}_ft"] = True
    with open(STATE_FILE, 'w') as f: json.dump(posted, f)
    print("Done.")

if __name__ == "__main__":
    main()
