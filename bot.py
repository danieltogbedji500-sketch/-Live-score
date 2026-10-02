import os, json, time, requests
from playwright.sync_api import sync_playwright

API_KEY = os.getenv("API_FOOTBALL_KEY")
X_USER = os.getenv("X_USER")
X_PASS = os.getenv("X_PASS")

MY_NATIONS = ["Spain","Germany","Portugal","France","England","Italy","Netherlands","Belgium"]
MY_CLUBS = ["Real Madrid","Barcelona","Atletico Madrid","Sevilla","Real Betis","Villarreal","Arsenal","Manchester City","Liverpool","Chelsea","Bayern Munich","Paris SG","PSG"]
SEEN_FILE = "goals_seen.json"
HEADERS = {"x-apisports-key": API_KEY}

def load_seen():
    try:
        with open(SEEN_FILE,"r") as f: return json.load(f)
    except: return []

def save_seen(s):
    with open(SEEN_FILE,"w") as f: json.dump(s,f)

def is_my_team(name):
    # EXCLUDE youth/reserve teams
    bad = ["U21","U20","U19","U18","U17"," II"," B "," WOMEN","Women"]
    for b in bad:
        if b.lower() in name.lower():
            return False
    n=name.lower()
    for t in MY_NATIONS+MY_CLUBS:
        if t.lower()==n: return True
        # For nations: exact match only (no U21)
        if t in MY_NATIONS and n==t.lower():
            return True
        # For clubs: allow contains
        if t in MY_CLUBS and t.lower() in n:
            return True
        if t=="Paris SG" and "psg" in n: return True
    # Extra exact check for senior nations
    if name in MY_NATIONS:
        return True
    return False

def format_goal(home,away,sh,sa,player,minute,assist=None):
    player=player or "Unknown"
    if str(player)=="None": player="Unknown"
    txt=f"GOAL!\n\n{home} {sh}-{sa} {away}\n{player} {minute}'\n\n#BallpointLive"
    if assist and str(assist)!="None": txt+=f"\nAssist: {assist}"
    return txt

def post_tweet(text):
    print(f"TWEETING: {text[:100]}")
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()
        page.goto("https://x.com/login",timeout=60000)
        page.wait_for_timeout(3000)
        try:
            page.wait_for_selector('input[autocomplete="username"]',timeout=10000)
            page.locator('input[autocomplete="username"]').first.fill(X_USER)
        except:
            page.locator('input[name="text"]').first.fill(X_USER)
        page.get_by_role("button",name="Next").click()
        page.wait_for_timeout(3000)
        page.wait_for_selector('input[type="password"]',timeout=10000)
        page.locator('input[type="password"]').first.fill(X_PASS)
        page.get_by_role("button",name="Log in").click()
        page.wait_for_timeout(5000)
        page.goto("https://x.com/compose/tweet",timeout=60000)
        page.wait_for_timeout(3000)
        page.wait_for_selector('div[role="textbox"]',timeout=15000)
        page.locator('div[role="textbox"]').first.fill(text)
        page.wait_for_timeout(1000)
        page.get_by_role("button",name="Post").first.click()
        page.wait_for_timeout(5000)
        browser.close()
        print("Tweeted OK")

def main():
    print("Ballpoint v5.8.6 starting")
    seen=load_seen()
    r=requests.get("https://v3.football.api-sports.io/fixtures?live=all",headers=HEADERS,timeout=20)
    data=r.json()
    fixtures=data.get("response",[])
    print(f"LIVE API: {len(fixtures)} fixtures, errors: {data.get('errors',[])}")
    print(f"Combined: {len(fixtures)}")
    targets=[]
    for f in fixtures:
        home=f['teams']['home']['name']; away=f['teams']['away']['name']
        if is_my_team(home) or is_my_team(away):
            status=f['fixture']['status']['short']
            targets.append(f)
            print(f"-> TARGET: {home} vs {away} [{status}] {f['goals']['home']}-{f['goals']['away']}")
    print(f"Total for YOUR teams: {len(targets)}")
    for f in targets:
        fid=f['fixture']['id']; home=f['teams']['home']['name']; away=f['teams']['away']['name']
        er=requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fid}",headers=HEADERS,timeout=20)
        events=er.json().get("response",[])
        for ev in events:
            if ev['type']=='Goal':
                pid=ev['player'].get('id','0')
                key=f"{fid}-{ev['time']['elapsed']}-{pid}"
                if key in seen: continue
                sh=f['goals']['home']; sa=f['goals']['away']
                player=ev['player'].get('name'); minute=ev['time']['elapsed']; assist=ev.get('assist',{}).get('name')
                tweet=format_goal(home,away,sh,sa,player,minute,assist)
                try:
                    post_tweet(tweet)
                    seen.append(key); save_seen(seen)
                except Exception as e:
                    print(f"Tweet failed: {e}"); continue

if __name__=="__main__":
    main()
