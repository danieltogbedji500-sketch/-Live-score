import os, json, requests, base64
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

try:
    import cloudscraper
    scraper = cloudscraper.create_scraper()
except:
    scraper = requests

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
    bad=["U21","U20","U19","U18","U17"," II","- II"," WOMEN","Women","(W)"," W "," WOMEN","Women "]
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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=AUTH_FILE if os.path.exists(AUTH_FILE) else None,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://x.com/compose/tweet", timeout=60000)
        page.wait_for_timeout(4000)
        if "login" in page.url or "flow" in page.url:
            print("Auth expired, doing fresh login...")
            if os.path.exists(AUTH_FILE):
                os.remove(AUTH_FILE)
                browser.close()
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                page = context.new_page()
            page.goto("https://x.com/i/flow/login", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=20000)
            page.wait_for_timeout(3000)
            try:
                user_input = page.locator('input[data-testid="ocfEnterTextTextInput"]').first
                if not user_input.is_visible(timeout=3000):
                    user_input = page.locator('input[name="text"]').first
                if not user_input.is_visible(timeout=3000):
                    user_input = page.locator('input[autocomplete="username"]').first
                if not user_input.is_visible(timeout=3000):
                    user_input = page.locator('input').first
                user_input.fill(X_USER, timeout=10000)
                page.wait_for_timeout(1000)
                next_btn = page.locator('button[data-testid="ocfEnterTextNextButton"]').first
                if not next_btn.is_visible(timeout=2000):
                    next_btn = page.get_by_role("button", name="Next").first
                next_btn.click()
                page.wait_for_timeout(4000)
            except Exception as e:
                print(f"Username step failed: {e}")
                raise
            try:
                challenge_input = page.locator('input[data-testid="ocfEnterTextTextInput"]').first
                if challenge_input.is_visible(timeout=3000):
                    if "phone" in page.content().lower() or "email" in page.content().lower():
                        challenge_input.fill(X_USER)
                        page.get_by_role("button", name="Next").first.click()
                        page.wait_for_timeout(3000)
            except:
                pass
            try:
                page.wait_for_selector('input[type="password"]', timeout=15000)
                page.locator('input[type="password"]').first.fill(X_PASS, timeout=10000)
                page.wait_for_timeout(1000)
                login_btn = page.locator('button[data-testid="ocfEnterTextNextButton"]').first
                if not login_btn.is_visible(timeout=2000):
                    login_btn = page.get_by_role("button", name="Log in").first
                login_btn.click()
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(5000)
                context.storage_state(path=AUTH_FILE)
                print("Saved new auth.json")
            except Exception as e:
                print(f"Password step failed: {e}")
                raise
            page.goto("https://x.com/compose/tweet", timeout=60000)
            page.wait_for_timeout(3000)
        try:
            page.wait_for_selector('div[role="textbox"]', timeout=15000)
            box = page.locator('div[role="textbox"]').first
            box.click()
            page.wait_for_timeout(500)
            box.fill(text)
        except:
            page.wait_for_selector('div[data-testid="tweetTextarea_0"]', timeout=15000)
            page.locator('div[data-testid="tweetTextarea_0"]').first.fill(text)
        page.wait_for_timeout(1500)
        try:
            page.locator('button[data-testid="tweetButtonInline"]').first.click(timeout=5000)
        except:
            try:
                page.locator('button[data-testid="tweetButton"]').first.click(timeout=5000)
            except:
                page.get_by_role("button", name="Post").first.click()
        page.wait_for_timeout(7000)
        context.storage_state(path=AUTH_FILE)
        browser.close()
        print("Posted OK")

def main():
    print("Ballpoint v7.0 ONE PER RUN + 15MIN EXPIRY")
    posted=load_state()
    now=datetime.now(timezone.utc)
    today=now.strftime("%Y%m%d")
    print(f"Date {today}")
    leagues=None
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page=context.new_page()
        captured=[]
        def on_response(resp):
            url=resp.url
            if "fotmob" in url and ("matches" in url):
                try:
                    if resp.status==200:
                        body=resp.text()
                        if '"leagues"' in body and len(body)>1000:
                            print(f"INTERCEPTED {url} len {len(body)}")
                            captured.append(json.loads(body))
                except: pass
        page.on("response", on_response)
        for url_try in [f"https://www.fotmob.com/matches?date={today}", "https://www.fotmob.com/matches"]:
            print(f"GOTO {url_try}")
            try:
                page.goto(url_try, timeout=60000)
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(5000)
                if captured: break
            except Exception as e:
                print(f"goto fail {e}")
        browser.close()
        if captured:
            for data in captured:
                if isinstance(data, dict) and "leagues" in data:
                    leagues=data["leagues"]
                    break
                for v in data.values() if isinstance(data, dict) else []:
                    if isinstance(v, dict) and "leagues" in v:
                        leagues=v["leagues"]
                        break
    if not leagues:
        print("FOTMOB fetch failed: could not parse leagues")
        return
    print(f"FOTMOB: {len(leagues)} leagues today")

    # --- NEW LOGIC: COLLECT CANDIDATES, POST ONLY 1 NEWEST, EXPIRE 15MIN ---
    candidates = [] # (first_seen_datetime, text, key)

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
            if not live and reason not in ["HT","FT"]:
                continue
            if not is_my_team(home) and not is_my_team(away):
                continue

            # FT / HT / KICKOFF etc - track first seen
            def add_candidate(txt, key):
                fk = f"{key}_first_seen"
                if key in posted:
                    return
                if fk not in posted:
                    posted[fk] = now.isoformat()
                    candidates.append((now, txt, key))
                else:
                    try:
                        first = datetime.fromisoformat(posted[fk])
                        if (now - first).total_seconds() / 60 <= 15:
                            candidates.append((first, txt, key))
                        else:
                            print(f"Expired >15min skip: {key}")
                            posted[key] = True # mark as expired to never retry
                    except:
                        candidates.append((now, txt, key))

            is_live = started and not finished and reason!="FT"
            if is_live and elapsed<=5:
                add_candidate(format_kickoff(home,away), f"{mid}_kick")
            if elapsed>=40 and elapsed<=42 and sh==0 and sa==0:
                add_candidate(format_40(home,away), f"{mid}_40")
            if elapsed>=80 and elapsed<=82 and sh==0 and sa==0:
                add_candidate(format_80(home,away), f"{mid}_80")
            if reason=="HT":
                add_candidate(format_halftime(home,away,sh,sa), f"{mid}_ht")
            if reason=="FT":
                add_candidate(format_fulltime(home,away,sh,sa), f"{mid}_ft")

            # Goals / Red cards from details - only for live or just finished
            if live or reason=="FT":
                try:
                    det=None
                    with sync_playwright() as pw3:
                        browser3=pw3.chromium.launch(headless=True)
                        context3=browser3.new_context()
                        page3=context3.new_page()
                        captured_det=[]
                        def on_det(resp):
                            if "matchDetails" in resp.url and resp.status==200:
                                try:
                                    txt=resp.text()
                                    if len(txt)>1000 and '"content"' in txt:
                                        captured_det.append(json.loads(txt))
                                except: pass
                        page3.on("response", on_det)
                        page3.goto(f"https://www.fotmob.com/match/{mid}", timeout=60000)
                        page3.wait_for_load_state("networkidle", timeout=15000)
                        page3.wait_for_timeout(3000)
                        browser3.close()
                        if captured_det: det=captured_det[0]
                    if not det: continue
                    def find_events(o):
                        if isinstance(o, dict):
                            if "events" in o and isinstance(o["events"], dict) and "events" in o["events"]:
                                return o["events"]["events"]
                            if "matchFacts" in o:
                                r=find_events(o["matchFacts"])
                                if r: return r
                            for v in o.values():
                                r=find_events(v)
                                if r: return r
                        elif isinstance(o, list):
                            for it in o:
                                r=find_events(it)
                                if r: return r
                        return None
                    events = find_events(det) or []
                    for ev in events:
                        ev_type=ev.get("type","")
                        if ev_type=="Goal":
                            minute=str(ev.get("timeStr","") or ev.get("time",0)).replace("'","")
                            player=ev.get("playerName") or ev.get("name") or ev.get("player",{}).get("name","Unknown")
                            if isinstance(player, dict): player=player.get("name","Unknown")
                            assist=ev.get("assistStr") or ev.get("assist") or ev.get("assistPlayer",{}).get("name")
                            key=f"{mid}_{minute}_{player}_goal"
                            if key not in posted:
                                add_candidate(format_goal(home,away,sh,sa,player,minute,assist), key)
                        if ev.get("card")=="Red" or "red" in str(ev).lower():
                            minute=str(ev.get("timeStr","") or ev.get("time",0)).replace("'","")
                            player=ev.get("playerName") or ev.get("player",{}).get("name","Unknown")
                            if isinstance(player, dict): player=player.get("name","Unknown")
                            key=f"{mid}_red_{minute}_{player}"
                            if key not in posted:
                                add_candidate(format_red(home,away,sh,sa,player,minute), key)
                except Exception as e:
                    print(f"Details failed for {mid}: {e}")

    if not candidates:
        print("No new events within 15min window")
        save_state(posted)
        return

    # Newest first
    candidates.sort(key=lambda x: x[0], reverse=True)
    newest_time, newest_text, newest_key = candidates[0]
    print(f"Posting 1 of {len(candidates)} newest: {newest_key} from {newest_time}")

    try:
        post_tweet(newest_text)
        posted[newest_key]=True
        save_state(posted)
        print(f"Done - posted {newest_key}")
    except Exception as e:
        print(f"Post failed: {e}")
        save_state(posted)

if __name__=="__main__":
    main()
