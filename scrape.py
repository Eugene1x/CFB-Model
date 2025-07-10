import requests
import pandas as pd
from tqdm import tqdm
import json

API_KEY = 'axgT5m9AuQFoSzePzDDbDMW8DgL/twgK/qfs1vJfbbVyupttCv7OsIZMTZSet0TP'  # ← replace with your API key
HEADERS = {'Authorization': f'Bearer {API_KEY}'}

def get_games(year):
    url = f"https://api.collegefootballdata.com/games?year={year}&seasonType=regular&division=fbs"
    r = requests.get(url, headers=HEADERS)
    print(f"GET {url} → {r.status_code}")
    return r.json()

all_games = []

for year in [2019, 2020, 2021, 2022, 2023]:
    print(f"📅 Loading games from {year}...")
    games = get_games(year)
    print(f"🔎 Found {len(games)} games.")

    for game in tqdm(games):
        home_team = game.get('homeTeam')
        away_team = game.get('awayTeam')
        home_points = game.get('homePoints')
        away_points = game.get('awayPoints')
        spread = game.get('spread')

        # Safety checks
        if not game.get('completed'):
            continue
        if home_team is None or away_team is None:
            print("⏩ Skipping (missing team info)")
            continue
        if home_points is None or away_points is None:
            print(f"⏩ Skipping (missing score): {home_team} vs {away_team}")
            continue

        # If no spread available, set it to 0 (assume pick-em)
        if spread is None:
            spread = 0.0

        row = {
            "season": game.get("season"),
            "week": game.get("week"),
            "home_team": home_team,
            "away_team": away_team,
            "home_points": home_points,
            "away_points": away_points,
            "spread": spread,
            "neutral_site": game.get("neutralSite"),
            "venue": game.get("venue")
        }

        # Favorite and underdog based on spread
        if spread < 0:
            favorite = home_team
            underdog = away_team
        else:
            favorite = away_team
            underdog = home_team

        row["favorite"] = favorite
        row["underdog"] = underdog

        # Determine winner
        if home_points > away_points:
            winner = home_team
        elif away_points > home_points:
            winner = away_team
        else:
            winner = "tie"

        row["winner"] = winner
        row["underdog_win"] = 1 if winner == underdog else 0

        all_games.append(row)

# Save results
df = pd.DataFrame(all_games)
df.to_csv("base_games_with_underdogs.csv", index=False)
print("✅ Done! Saved base_games_with_underdogs.csv with", len(df), "rows.")
