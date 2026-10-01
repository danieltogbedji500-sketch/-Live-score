# Ballpoint X Bot v5.8.4 FINAL - NATIONS exact + CLUBS one-team valid
import os, json, requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

API_KEY = os.getenv("API_FOOTBALL_KEY")
X_USER = os.getenv("X_USERNAME")
X_PASS = os.getenv("X_PASSWORD")
STATE_FILE = "state.json"
AUTH_FILE = "auth.json"
TAG = "#BallpointLive"

MY_NATIONS = ["Spain", "Germany", "Portugal", "France", "England", "Italy", "Netherlands", "Belgium"]
MY_CLUBS = ["Real Madrid", "Barcelona", "Atletico Madrid", "Athletic Club", "Villarreal", "Arsenal", "Man City", "Manchester City", "Liverpool", "Chelsea", "Manchester United", "Man Utd", "Newcastle", "Tottenham", "Aston Villa", "Bayern Munich", "Bayern", "Inter Milan", "Inter", "PSG", "Paris SG", "Marseille"]

def is_my_team(home, away):
    h = home.lower().strip()
    a = away.lower().strip()
    if any(x in h or x in a for x in ["u20","u21","u19","u23","women","fem"]):
        return False
    for n in MY_NATIONS:
        if h == n.lower() or a == n.lower():
            return True
    for c in MY_CLUBS:
        if c.lower() in h or c.lower() in a:
            return True
    return False

scorers_today = {}
def format_goal(th, ta, sh, sa, scorer, minute, assist=None):
    count = scorers_today.get(scorer, 0) + 1
    scorers_today[scorer] = count
    score_line = f"{th} {sh}-{sa} {ta}"
    assist_text = f" (Assist: {assist})" if assist else ""
    m = str(minute) + "'"
    if count == 1:
        return f"GOAL!\n\n{score_line}\n{scorer} {m}{assist_text}\n\n{TAG}"
    elif count == 2:
        return f"HE SCORES AGAIN! BRACE!\n\n{score_line}\n{scorer} {m}{assist_text} - On FIRE!\n\n{TAG}"
    else:
        return f"HAT-TRICK HERO!\n\n{score_line}\n{scorer} {m}{assist_text} - UNSTOPPABLE!\n\n{TAG}"

def format_kickoff(th, ta): return f"KICKOFF!\n\n{th} vs {ta} is underway!\nPredictions?\n\n{TAG}"
def format_halftime(th, ta, sh, sa): return f"HALFTIME:\n\n{th} {sh}-{sa} {ta}\nThoughts so far?\n\n{TAG}"
def format_fulltime(th, ta, sh, sa): return f"FT:\n\n{th} {sh}-{sa} {ta}\nWhat a game!\n\n{TAG}"
def format_red_card(th, ta, sh, sa, player, minute): return f"RED CARD!\n\n{th} {sh}-{sa} {ta}\n{player} {minute}' - Sent off!\n\n{TAG}"

def post_tweet(text):
    print(f"TWEETING: {text[:80]}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=AUTH_FILE) if os.path.exists(AUTH_FILE) else browser.new_context()
        page = context.new_page()
        if not os.path.exists(AUTH_FILE):
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
    print("Ballpoint v5.8.4 starting")
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'w') as f: json.dump({}, f)
    with open(STATE_FILE, 'r') as f: posted = json.load(f)

    headers = {"x-apisports-key": API_KEY}

    # 1 REQUEST ONLY - safe for new key
    r = requests.get("https://v3.football.api-sports.io/fixtures?live=all", headers=headers)
    j = r.json()
    print(f"LIVE API: {j.get('results')} fixtures, errors: {j.get('errors')}")
    all_fixtures = j.get('response', [])
    print(f"Combined: {len(all_fixtures)}")

    targets = []
    for fix in all_fixtures:
        home = fix['teams']['home']['name']
        away = fix['teams']['away']['name']
        if is_my_team(home, away):
            status = fix['fixture']['status']['short']
            if status not in ['FT','AET','PEN','CANC','PST','ABD','AWD']:
                targets.append(fix)
                print(f"-> TARGET: {home} vs {away} [{status}] {fix['goals']['home']}-{fix['goals']['away']}")

    print(f"Total for YOUR teams: {len(targets)}")
    for fix in targets:
        home = fix['teams']['home']['name']
        away = fix['teams']['away']['name']
        fid = str(fix['fixture']['id'])
        status = fix['fixture']['status']['short']
        elapsed = fix['fixture']['status']['elapsed'] or 0
        sh = fix['goals']['home']; sa = fix['goals']['away']

        if status in ["1H","HT","2H"] and elapsed <= 5 and f"{fid}_kick" not in posted:
            post_tweet(format_kickoff(home, away))
            posted[f"{fid}_kick"] = True

        ev_resp = requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fid}", headers=headers).json()
        for ev in ev_resp.get('response', []):
            if ev['type'] == 'Goal':
                key = f"{fid}_{ev['time']['elapsed']}_{ev['player']['name']}"
                if key not in posted:
                    assist = ev['assist']['name'] if ev['assist']['name'] else None
                    post_tweet(format_goal(home, away, sh, sa, ev['player']['name'], ev['time']['elapsed'], assist))
                    posted[key] = True
            if ev['type'] == 'Card' and 'Red' in ev['detail']:
                key = f"{fid}_red_{ev['player']['name']}"
                if key not in posted:
                    post_tweet(format_red_card(home, away, sh, sa, ev['player']['name'], ev['time']['elapsed']))
                    posted[key] = True

        if status == "HT" and f"{fid}_ht" not in posted:
            post_tweet(format_halftime(home, away, sh, sa)); posted[f"{fid}_ht"] = True
        if status in ["FT","AET","PEN"] and f"{fid}_ft" not in posted:
            post_tweet(format_fulltime(home, away, sh, sa)); posted[f"{fid}_ft"] = True

    with open(STATE_FILE, 'w') as f: json.dump(posted, f)
    print("Done.")

if __name__ == "__main__":
    main()
