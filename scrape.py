import requests
import pandas as pd
import json

API_KEY = 'axgT5m9AuQFoSzePzDDbDMW8DgL/twgK/qfs1vJfbbVyupttCv7OsIZMTZSet0TP'  # <-- replace with your actual API key
HEADERS = {'Authorization': f'Bearer {API_KEY}'}

YEAR = 2023
WEEK = 1

def get_games(year, week):
    url = f"https://api.collegefootballdata.com/games?year={year}&week={week}&seasonType=regular&division=fbs"
    r = requests.get(url, headers=HEADERS)
    print(f"GET {url} → {r.status_code}")
    return r.json()

def get_game_stats(year, week):
    url = f"https://api.collegefootballdata.com/stats/game/teams?year={year}&week={week}&seasonType=regular"
    r = requests.get(url, headers=HEADERS)
    print(f"GET {url} → {r.status_code}")
    try:
        return r.json()
    except json.decoder.JSONDecodeError:
        print("⚠️ No stats returned (API returned empty response).")
        return []

print(f"📅 Pulling Week {WEEK}, {YEAR}")
games = get_games(YEAR, WEEK)

all_rows = []

for game in games:
    home_team = game.get("homeTeam")
    away_team = game.get("awayTeam")
    home_score = game.get("homePoints")
    away_score = game.get("awayPoints")

    if not home_team or not away_team:
        print("⏩ Skipping (missing teams)")
        continue
    if home_score is None or away_score is None:
        print(f"⏩ Skipping (missing scores): {home_team} vs {away_team}")
        continue

    print(f"🟢 Game: {home_team} vs {away_team} | Score: {home_score}-{away_score}")

    row = {
        "season": game.get("season"),
        "week": game.get("week"),
        "home_team": home_team,
        "away_team": away_team,
        "home_points": home_score,
        "away_points": away_score,
        "spread": game.get("spread"),
        "over_under": game.get("over_under"),
        "neutral_site": game.get("neutralSite"),
        "home_conference": game.get("homeConference"),
        "away_conference": game.get("awayConference"),
        "venue": game.get("venue"),
    }

    # Add team stats
    stats = get_game_stats(YEAR, WEEK)
    for team_data in stats:
        team = team_data.get("team")
        side = "home" if team == home_team else "away" if team == away_team else None
        if side:
            for stat in team_data.get("stats", []):
                stat_name = stat["stat"].replace(" ", "_").lower()
                row[f"{side}_{stat_name}"] = stat["value"]

    all_rows.append(row)

# Save to CSV
df = pd.DataFrame(all_rows)
df.to_csv("fixed_week1_2023_data.csv", index=False)
print("✅ Saved fixed_week1_2023_data.csv with", len(df), "games")
