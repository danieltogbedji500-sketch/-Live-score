# Ballpoint X Bot v5.5 FINAL - 17 CLUBS + 8 NATIONS
import os, json, requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

API_KEY = os.getenv("API_FOOTBALL_KEY")
X_USER = os.getenv("X_USERNAME")
X_PASS = os.getenv("X_PASSWORD")
STATE_FILE = "state.json"
AUTH_FILE = "auth.json"
TAG = "#BallpointLive"

# === FINAL ROSTER - DO NOT FORGET ===
NATIONS_8 = ["Spain", "Germany", "Portugal", "France", "England", "Italy", "Netherlands", "Belgium"]
LALIGA = ["Real Madrid", "Barcelona", "Atletico Madrid", "Athletic Club", "Villarreal"]
PREMIER = ["Arsenal", "Man City", "Manchester City", "Liverpool", "Chelsea", "Manchester United", "Man Utd", "Newcastle", "Newcastle United", "Tottenham", "Aston Villa", "Aston Villa FC"]
EUROPE_EXTRA = ["Bayern", "Bayern Munich", "Inter", "Inter Milan", "PSG", "Paris Saint-Germain", "Paris SG", "Marseille", "Olympique de Marseille"]

ALL_TEAMS = NATIONS_8 + LALIGA + PREMIER + EUROPE_EXTRA

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

def format
