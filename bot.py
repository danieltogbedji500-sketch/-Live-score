# Ballpoint X - Final Bot v5
LEAGUES = {
    "LALIGA": ["Real Madrid", "Barcelona", "Atletico Madrid", "Athletic Club", "Villarreal"],
    "PREMIER_LEAGUE": ["Arsenal", "Man City", "Liverpool", "Chelsea", "Man Utd", "Newcastle", "Tottenham"],
    "UCL": "ALL",
    "NATIONS_LEAGUE": ["Spain", "Germany", "Portugal", "France", "England", "Italy", "Netherlands", "Belgium"]
}

scorers_today = {}

def format_goal(team_home, team_away, sh, sa, scorer, minute, assist=None, tag="#BallpointLive"):
    count = scorers_today.get(scorer, 0) + 1
    scorers_today[scorer] = count
    score_line = f"{team_home} {sh}-{sa} {team_away}"
    assist_text = f" (Assist: {assist})" if assist else ""

    if count == 1:
        return f"""🚨 GOAL!

{score_line}
⚽ {scorer} {minute}'{assist_text}

{tag}"""
    elif count == 2:
        return f"""HE SCORES AGAIN! 🚨 BRACE!

{score_line}
⚽ {scorer} {minute}'{assist_text} - He's on FIRE! 🔥

{tag}"""
    else:
        return f"""HAT-TRICK HERO! 🎩🔥

{score_line}
⚽ {scorer} {minute}'{assist_text} - UNSTOPPABLE!

{tag}"""

def format_red_card(th, ta, sh, sa, player, minute, tag):
    return f"""🟥 RED CARD!

{th} {sh}-{sa} {ta}
{player} {minute}' - Sent off!

{tag}"""

def format_penalty(th, ta, sh, sa, player, minute, tag):
    return f"""⚠️ PENALTY!

{th} {sh}-{sa} {ta}
{player} to take it {minute}'...

{tag}"""

def format_reminder_40(th, ta, tag):
    return f"""⏳ 40' - Still goalless!

{th} 0-0 {ta}
This is TENSE... who breaks the deadlock? 👀

{tag}"""

def format_reminder_80(th, ta, tag):
    return f"""⏳ 80' - STILL 0-0! 😬

{th} vs {ta} is going CRAZY!
Late winner coming? 👇

{tag}"""

def format_fulltime(th, ta, sh, sa, tag):
    return f"""⏱️ FT:

{th} {sh}-{sa} {ta}
What a game! Thoughts? 👇

{tag}"""
