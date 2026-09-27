# Ballpoint X Bot v5.6 FINAL - LIVE + TODAY check
import os, json, requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

API_KEY = os.getenv("API_FOOTBALL_KEY")
X_USER = os.getenv("X_USERNAME")
X_PASS = os.getenv("X_PASSWORD")
STATE_FILE = "state.json"
AUTH_FILE = "auth.json"
TAG = "#BallpointLive"

NATIONS_8 = ["Spain", "Germany", "Portugal", "France", "England", "Italy", "Netherlands", "Belgium"]
LALIGA = ["Real Madrid", "Barcelona", "Atletico Madrid", "Athletic Club", "Villarreal"]
PREMIER = ["Arsenal", "Man City", "Manchester City", "Liverpool", "Chelsea", "Manchester United", "Man Utd", "Newcastle", "Newcastle United", "Tottenham", "Aston Villa"]
EUROPE_EXTRA = ["Bayern", "Bayern Munich", "Inter", "Inter Milan", "PSG", "Paris Saint-Germain", "Paris SG", "Marseille", "Olympique de Marseille"]

ALL_TEAMS = NATIONS_8 + LALIGA + PREMIER + EUROPE_EXTRA
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

def format_kickoff(th, ta):
    return f"KICKOFF!\n\n{th} vs {ta} is underway!\nPredictions?\n\n{TAG}"

def format_halftime(th, ta, sh, sa):
    return f"HALFTIME:\n\n{th} {sh}-{sa} {ta}\nThoughts so far?\n\n{TAG}"

def format_fulltime(th, ta, sh, sa):
    return f"FT:\n\n{th} {sh}-{sa} {ta}\nWhat a game! Thoughts?\n\n{TAG}"

def format_red_card(th, ta, sh, sa, player, minute):
    m = str(minute) + "'"
    return f"RED CARD!\n\n{th} {sh}-{sa} {ta}\n{player} {m} - Sent off!\n\n{TAG}"

def post_tweet(text):
    print(f"TWEETING: {text[:60]}...")
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
            if os.path.exists(AUTH_FILE):
                os.remove(AUTH_FILE)
            browser.close()
            return post_tweet(text)
        page.fill('div[data-testid="tweetTextarea_0"]', text)
        page.wait_for_timeout(1000)
        page.click('div[data-testid="tweetButtonInline"]')
        page.wait_for_timeout(4000)
        browser.close()
        print("Posted!")

def main():
    print("Ballpoint Bot v5.6 FINAL starting")
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'w') as f:
            json.dump({}, f)
    with open(STATE_FILE, 'r') as f:
        posted = json.load(f)

    headers = {"x-apisports-key": API_KEY}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Date UTC: {today}")

    all_fixtures = []
    seen_ids = set()

    # 1. Check TODAY
    try:
        r1 = requests.get(f"https://v3.football.api-sports.io/fixtures?date={today}", headers=headers)
        j1 = r1.json()
        print(f"TODAY API: {j1.get('results')} fixtures, errors: {j1.get('errors')}")
        for fix in j1.get('response', []):
            fid = fix['fixture']['id']
            if fid not in seen_ids:
                all_fixtures.append(fix)
                seen_ids.add(fid)
    except Exception as e:
        print(f"Error today: {e}")

    # 2. Check LIVE (crucial to avoid 0)
    try:
        r2 = requests.get(f"https://v3.football.api-sports.io/fixtures?live=all", headers=headers)
        j2 = r2.json()
        print(f"LIVE API: {j2.get('results')} fixtures")
        for fix in j2.get('response', []):
            fid = fix['fixture']['id']
            if fid not in seen_ids:
                all_fixtures.append(fix)
                seen_ids.add(fid)
    except Exception as e:
        print(f"Error live: {e}")

    print(f"Combined unique fixtures: {len(all_fixtures)}")

    targets = []
    for fix in all_fixtures:
        home = fix['teams']['home']['name']
        away = fix['teams']['away']['name']
        for team in ALL_TEAMS:
            if team.lower() in home.lower() or team.lower() in away.lower():
                status = fix['fixture']['status']['short']
                if status not in ['FT','AET','PEN','CANC','PST','ABD','AWD']:
                    targets.append(fix)
                    print(f"-> TARGET: {home} vs {away} [{status}] {fix['goals']['home']}-{fix['goals']['away']}")
                break
