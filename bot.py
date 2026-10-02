import os, json, requests
from playwright.sync_api import sync_playwright

API_KEY=os.getenv("API_FOOTBALL_KEY")
X_USER=os.getenv("X_USER")
X_PASS=os.getenv("X_PASS")
STATE_FILE="state.json"
AUTH_FILE="auth.json"
TAG="#BallpointLive"

MY_NATIONS=["Spain","Germany","Portugal","France","England","Italy","Netherlands","Belgium"]
MY_CLUBS=["Real Madrid","Barcelona","Atletico Madrid","Sevilla","Real Betis","Villarreal","Arsenal","Manchester City","Man City","Liverpool","Chelsea","Bayern Munich","Paris SG","PSG"]
ALL_TEAMS=MY_NATIONS+MY_CLUBS
scorers_today={}

def load_state():
    try:
        with open(STATE_FILE,"r") as f: return json.load(f)
    except: return {}

def save_state(s):
    with open(STATE_FILE,"w") as f: json.dump(s,f)

def is_my_team(name):
    bad=["U21","U20","U19","U18","U17"," II","- II"," WOMEN","Women"," U23"]
    for b in bad:
        if b.lower() in name.lower(): return False
    if name in MY_NATIONS: return True
    n=name.lower()
    for t in ALL_TEAMS:
        if t.lower() in n or n in t.lower(): return True
    return False

def format_goal(th,ta,sh,sa,scorer,minute,assist=None):
    count=scorers_today.get(scorer,0)+1
    scorers_today[scorer]=count
    assist_text=f" (Assist: {assist})" if assist and str(assist)!="None" else ""
    score_line=f"{th} {sh}-{sa} {ta}"
    if count==1: return f"GOAL!\n\n{score_line}\n{scorer} {minute}'{assist_text}\n\n{TAG}"
    elif count==2: return f"HE SCORES AGAIN! BRACE!\n\n{score_line}\n{scorer} {minute}'{assist_text} - On FIRE!\n\n{TAG}"
    else: return f"HAT-TRICK HERO!\n\n{score_line}\n{scorer} {minute}'{assist_text} - UNSTOPPABLE!\n\n{TAG}"

def format_kickoff(th,ta): return f"KICKOFF!\n\n{th} vs {ta} is underway!\nPredictions?\n\n{TAG}"
def format_halftime(th,ta,sh,sa): return f"HALFTIME:\n\n{th} {sh}-{sa} {ta}\nThoughts so far?\n\n{TAG}"
def format_fulltime(th,ta,sh,sa): return f"FT:\n\n{th} {sh}-{sa} {ta}\nWhat a game!\n\n{TAG}"
def format_40(th,ta): return f"40' - Still goalless!\n\n{th} 0-0 {ta}\nTENSE...\n\n{TAG}"
def format_80(th,ta): return f"80' - STILL 0-0!\n\n{th} vs {ta} is CRAZY!\n\n{TAG}"
def format_red(th,ta,sh,sa,player,minute): return f"RED CARD!\n\n{th} {sh}-{sa} {ta}\n{player} {minute}' - Sent off!\n\n{TAG}"

def post_tweet(text):
    print(f"TWEETING: {text[:80]}...")
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(storage_state=AUTH_FILE) if os.path.exists(AUTH_FILE) else browser.new_context()
        page=context.new_page()
        if not os.path.exists(AUTH_FILE):
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
            context.storage_state(path=AUTH_FILE)
        page.goto("https://x.com/compose/tweet",timeout=60000)
        page.wait_for_timeout(3000)
        if "login" in page.url:
            if os.path.exists(AUTH_FILE): os.remove(AUTH_FILE)
            browser.close()
            return post_tweet(text)
        page.wait_for_selector('div[role="textbox"]',timeout=15000)
        page.locator('div[role="textbox"]').first.fill(text)
        page.wait_for_timeout(1000)
        page.get_by_role("button",name="Post").first.click()
        page.wait_for_timeout(5000)
        browser.close()

def main():
    print("Ballpoint v5.8.7 FINAL starting")
    posted=load_state()
    headers={"x-apisports-key":API_KEY}
    r=requests.get("https://v3.football.api-sports.io/fixtures?live=all",headers=headers,timeout=20)
    data=r.json()
    if data.get("errors") and data["errors"].get("requests"):
        print(f"LIMIT HIT: {data['errors']}")
        return
    fixtures=data.get("response",[])
    print(f"LIVE API: {len(fixtures)} fixtures")
    targets=[]
    for f in fixtures:
        home=f['teams']['home']['name']; away=f['teams']['away']['name']
        if is_my_team(home) or is_my_team(away):
            targets.append(f)
            print(f"-> TARGET: {home} vs {away} [{f['fixture']['status']['short']}] {f['goals']['home']}-{f['goals']['away']}")
    print(f"Total for YOUR teams: {len(targets)}")
    for f in targets:
        fid=str(f['fixture']['id'])
        home=f['teams']['home']['name']; away=f['teams']['away']['name']
        sh=f['goals']['home']; sa=f['goals']['away']
        status=f['fixture']['status']['short']; elapsed=f['fixture']['status']['elapsed'] or 0
        prev_score=posted.get(f"{fid}_score","x-x")
        curr_score=f"{sh}-{sa}"
        if status in ["1H","HT","2H"] and elapsed<=5 and f"{fid}_kick" not in posted:
            try: post_tweet(format_kickoff(home,away)); posted[f"{fid}_kick"]=True
            except Exception as e: print(e)
        if elapsed>=40 and elapsed<=42 and sh==0 and sa==0 and f"{fid}_40" not in posted:
            try: post_tweet(format_40(home,away)); posted[f"{fid}_40"]=True
            except: pass
        if elapsed>=80 and elapsed<=82 and sh==0 and sa==0 and f"{fid}_80" not in posted:
            try: post_tweet(format_80(home,away)); posted[f"{fid}_80"]=True
            except: pass
        if status=="HT" and f"{fid}_ht" not in posted:
            try: post_tweet(format_halftime(home,away,sh,sa)); posted[f"{fid}_ht"]=True
            except: pass
        if status in ["FT","AET","PEN"] and f"{fid}_ft" not in posted:
            try: post_tweet(format_fulltime(home,away,sh,sa)); posted[f"{fid}_ft"]=True
            except: pass
        if curr_score!=prev_score:
            print(f"Score changed {prev_score} -> {curr_score}, fetching events...")
            er=requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fid}",headers=headers,timeout=20)
            events=er.json().get("response",[])
            for ev in events:
                if ev['type']=='Goal':
                    key=f"{fid}_{ev['time']['elapsed']}_{ev['player'].get('id')}"
                    if key not in posted:
                        assist=ev.get('assist',{}).get('name')
                        try:
                            post_tweet(format_goal(home,away,sh,sa,ev['player'].get('name','Unknown'),ev['time']['elapsed'],assist))
                            posted[key]=True
                        except Exception as e: print(e)
                if ev['type']=='Card' and 'Red' in ev.get('detail',''):
                    key=f"{fid}_red_{ev['time']['elapsed']}_{ev['player'].get('id')}"
                    if key not in posted:
                        try:
                            post_tweet(format_red(home,away,sh,sa,ev['player'].get('name'),ev['time']['elapsed']))
                            posted[key]=True
                        except Exception as e: print(e)
            posted[f"{fid}_score"]=curr_score
        save_state(posted)
    print("Done")

if __name__=="__main__":
    main()
