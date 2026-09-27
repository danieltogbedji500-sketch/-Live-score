# Ballpoint X Bot v5.7 MINIMAL
import os, json, requests, sys
from datetime import datetime, timezone
print("Ballpoint Bot v5.7 starting", flush=True)

API_KEY = os.getenv("API_FOOTBALL_KEY")
X_USER = os.getenv("X_USERNAME")
X_PASS = os.getenv("X_PASSWORD")

STATE_FILE = "state.json"
TEAMS = ["Spain","Germany","Portugal","France","England","Italy","Netherlands","Belgium","Real Madrid","Barcelona","Atletico","Villarreal","Arsenal","Man City","Manchester City","Liverpool","Chelsea","Man Utd","Manchester United","Newcastle","Tottenham","Aston Villa","Bayern","Inter","PSG","Marseille"]

if not API_KEY:
    print("ERROR: API_FOOTBALL_KEY missing!", flush=True)
    sys.exit(1)

if not os.path.exists(STATE_FILE):
    with open(STATE_FILE, 'w') as f: json.dump({}, f)
with open(STATE_FILE, 'r') as f: posted = json.load(f)

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
print(f"Date UTC: {today}", flush=True)

headers = {"x-apisports-key": API_KEY}
all_fixtures = []
seen = set()

for mode in [f"date={today}", "live=all"]:
    try:
        url = f"https://v3.football.api-sports.io/fixtures?{mode}"
        r = requests.get(url, headers=headers, timeout=15)
        j = r.json()
        print(f"API {mode}: {j.get('results')} results errors={j.get('errors')}", flush=True)
        for fx in j.get('response', []):
            fid = fx['fixture']['id']
            if fid not in seen:
                all_fixtures.append(fx)
                seen.add(fid)
    except Exception as e:
        print(f"Error {mode}: {e}", flush=True)

print(f"Combined: {len(all_fixtures)}", flush=True)

targets = []
for fx in all_fixtures:
    h = fx['teams']['home']['name']
    a = fx['teams']['away']['name']
    stat = fx['fixture']['status']['short']
    if any(t.lower() in h.lower() or t.lower() in a.lower() for t in TEAMS):
        if stat not in ['FT','AET','PEN','CANC','PST','ABD']:
            targets.append(fx)
            print(f"TARGET: {h} vs {a} [{stat}] {fx['goals']['home']}-{fx['goals']['away']}", flush=True)

print(f"Total for YOUR teams: {len(targets)}", flush=True)
print("Done - bot logic OK, no tweet in this test version", flush=True)
