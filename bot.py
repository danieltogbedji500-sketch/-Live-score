# Ballpoint X Bot v5.1 - FULL RUNNABLE FIXED
import os, json, time, requests
from playwright.sync_api import sync_playwright

# --- CONFIG ---
LEAGUES = {
    "LALIGA": ["Real Madrid", "Barcelona", "Atletico Madrid", "Athletic Club", "Villarreal"],
    "PREMIER_LEAGUE": ["Arsenal", "Man City", "Liverpool", "Chelsea", "Man Utd", "Newcastle", "Tottenham"],
    "NATIONS_LEAGUE": ["Spain", "Germany", "Portugal", "France", "England", "Italy", "Netherlands", "Belgium"]
}
API_KEY = os.getenv("API_FOOTBALL_KEY")
X_USER = os.getenv("X_USERNAME")
X_PASS = os.getenv("X_PASSWORD")

STATE_FILE = "state.json"
AUTH_FILE = "auth.json"
TAG = "#BallpointLive"

scorers_today = {}

# --- FORMATS (Your v5) ---
def format_goal(th, ta, sh, sa, scorer, minute, assist=None):
    count = scorers_today.get(scorer, 0) + 1
    scorers_today[scorer] = count
    score_line = f"{th} {sh}-{sa} {ta}"
    assist_text = f" (Assist: {assist})" if assist else ""
    if count == 1:
        return f"""🚨 GOAL!

{score_line}
⚽ {scorer} {minute}'{assist_text}

{TAG}"""
    elif count == 2:
        return f"""HE SCORES AGAIN! 🚨 BRACE!

{score_line}
⚽ {scorer} {minute}'{assist_text} - He's on FIRE! 🔥

{TAG}"""
    else:
        return f"""HAT-TRICK HERO! 🎩🔥

{score_line}
⚽ {scorer} {minute}'{assist_text} - UNSTOPPABLE!

{TAG}"""

def format_kickoff(th, ta):
    return f"""⏱️ KICKOFF!

{th} vs {ta} is underway!
Predictions? 👇

{TAG}"""

def format_halftime(th, ta, sh, sa):
    return f"""⏸️
