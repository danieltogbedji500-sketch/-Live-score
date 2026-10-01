import os, json, requests, time
from datetime import datetime

API_KEY = os.getenv("API_FOOTBALL_KEY")
STATE_FILE = "state.json"

# Your popular teams filter - edit this list
POPULAR_TEAMS = ["Real Madrid","Barcelona","Manchester City","Arsenal","Liverpool","Man United","Chelsea","PSG","Bayern Munich","Inter"]

headers = {"x-apisports-key": API_KEY}

def get_live():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    r = requests.get(url, headers=headers, timeout=20)
    print(r.text[:500]) # for debug
    data = r.json()
    return data.get("response", [])

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except: return {}

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f)

# --- main ---
live_games = get_live()
print(f"Live games found: {len(live_games)}")
state = load_state()

for game in live_games:
    fid = str(game["fixture"]["id"])
    home = game["teams"]["home"]["name"]
    away = game["teams"]["away"]["name"]
    if not any(t in [home,away] for t in POPULAR_TEAMS): continue

    goals_home = game["goals"]["home"]
    goals_away = game["goals"]["away"]
    minute = game["fixture"]["status"]["elapsed"]
    score_key = f"{goals_home}-{goals_away}"

    last_score = state.get(fid)
    if last_score!= score_key:
        text = f"⚽️ {minute}' GOAL! {home} {goals_home}-{goals_away} {away}"
        print(f"NEW: {text}")
        # --- post to X here (Playwright part stays same as your old bot) ---
        # If you use API, call it here
        state[fid] = score_key

save_state(state)
