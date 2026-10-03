import os, json, requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

# FIX FOR CLOUDFLARE BLOCK - FotMob blocks GitHub IPs
try:
    import cloudscraper
    scraper = cloudscraper.create_scraper()
except:
    scraper = requests

# FotMob needs no key
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
    print("Ballpoint v6.2 FOTMOB mode starting")
    posted=load_state()

    # FOTMOB - No key needed - FIXED HEADERS
    today=datetime.now(timezone.utc).strftime("%Y%m%d")
    headers={
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept":"application/json",
        "Referer":"https://www.fotmob.com/"
    }

    try:
        r=scraper.get(f"https://www.fotmob.com/api/matches?date={today}",headers=headers,timeout=20)
        data=r.json()
    except Exception as e:
        print(f"FOTMOB fetch failed: {e}")
        return

    leagues=data.get("leagues",[])
    print(f"FOTMOB: {len(leagues)} leagues today")

    targets=[]
    for lg in leagues:
        for m in lg.get("matches",[]):
            home=m.get("home",{}).get("name","")
            away=m.get("away",{}).get("name","")
            mid=str(m.get("id"))
            status_obj=m.get("status",{})
            started=status_obj.get("started",False)
            finished=status_obj.get("finished",False)
            live=status_obj.get("liveTime") is not None or (started and not finished)
            reason=status_obj.get("reason",{}).get("short","")

            sh=m.get("home",{}).get("score",0)
            sa=m.get("away",{}).get("score",0)
            if sh is None: sh=0
            if sa is None: sa=0

            live_str=status_obj.get("liveTime",{}).get("short","") if status_obj.get("liveTime") else ""
            elapsed=0
            try:
                if live_str:
                    elapsed=int(''.join(filter(str.isdigit, live_str.split('+')[0])) or 0)
            except: elapsed=0

            if not live and reason not in ["HT"]:
                if reason!="FT":
                    continue

            if is_my_team(home) or is_my_team(away):
                targets.append({
                    "id":mid,
                    "home":home,
                    "away":away,
                    "sh":sh,
                    "sa":sa,
                    "elapsed":elapsed,
                    "reason":reason,
                    "live_str":live_str,
                    "started":started,
                    "finished":finished
                })
                print(f"-> TARGET: {home} vs {away} [{reason or live_str}] {sh}-{sa}")

    print(f"Total for YOUR teams: {len(targets)}")

    for f in targets:
        fid=f["id"]
        home=f["home"]; away=f["away"]
        sh=f["sh"]; sa=f["sa"]
        elapsed=f["elapsed"]
        reason=f["reason"]
        live_str=f["live_str"]

        prev_score=posted.get(f"{fid}_score","x-x")
        curr_score=f"{sh}-{sa}"

        if f["started"] and elapsed<=5 and f"{fid}_kick" not in posted:
            try: post_tweet(format_kickoff(home,away)); posted[f"{fid}_kick"]=True
            except Exception as e: print(e)

        if elapsed>=40 and elapsed<=42 and sh==0 and sa==0 and f"{fid}_40" not in posted:
            try: post_tweet(format_40(home,away)); posted[f"{fid}_40"]=True
            except: pass
        if elapsed>=80 and elapsed<=82 and sh==0 and sa==0 and f"{fid}_80" not in posted:
            try: post_tweet(format_80(home,away)); posted[f"{fid}_80"]=True
            except: pass
        if reason=="HT" and f"{fid}_ht" not in posted:
            try: post_tweet(format_halftime(home,away,sh,sa)); posted[f"{fid}_ht"]=True
            except: pass
        if reason=="FT" and f"{fid}_ft" not in posted:
            try: post_tweet(format_fulltime(home,away,sh,sa)); posted[f"{fid}_ft"]=True
            except: pass

        if curr_score!=prev_score or f["started"]:
            print(f"Score {prev_score} -> {curr_score}, fetching matchDetails for {fid}...")
            try:
                dr=scraper.get(f"https://www.fotmob.com/api/matchDetails?matchId={fid}",headers=headers,timeout=20)
                det=dr.json()
                events=[]
                try:
                    mf=det.get("content",{}).get("matchFacts",{}).get("events",{}).get("events",[])
                    events=mf
                except: events=[]
                if not events:
                    try:
                        events=det.get("header",{}).get("events",{}).get("events",[]) or det.get("content",{}).get("events",{}).get("events",[])
                    except: events=[]

                for ev in events:
                    ev_type=ev.get("type","")
                    if ev_type=="Goal":
                        minute=ev.get("timeStr","").replace("'","") or ev.get("time",0)
                        player=ev.get("playerName") or ev.get("name","Unknown")
                        assist=None
                        if "assist" in str(ev).lower():
                            assist=ev.get("assistStr") or ev.get("assist")
                        key=f"{fid}_{minute}_{player}_goal"
                        if key not in posted:
                            try:
                                post_tweet(format_goal(home,away,sh,sa,player,minute,assist))
                                posted[key]=True
                            except Exception as e: print(e)
                    if "Card" in ev_type or ev.get("card")=="Red" or "Red" in str(ev.get("type","")):
                        if ev.get("card")=="Red" or "red" in str(ev).lower():
                            minute=ev.get("timeStr","").replace("'","") or ev.get("time",0)
                            player=ev.get("playerName","Unknown")
                            key=f"{fid}_red_{minute}_{player}"
                            if key not in posted:
                                try:
                                    post_tweet(format_red(home,away,sh,sa,player,minute))
                                    posted[key]=True
                                except Exception as e: print(e)
            except Exception as e:
                print(f"Details failed for {fid}: {e}")

            posted[f"{fid}_score"]=curr_score

        save_state(posted)
    print("Done - FotMob")

if __name__=="__main__":
    main()
