import requests
import pandas as pd
from tqdm import tqdm
import numpy as np
import time
from math import radians, cos, sin, asin, sqrt

API_KEY = 'axgT5m9AuQFoSzePzDDbDMW8DgL/twgK/qfs1vJfbbVyupttCv7OsIZMTZSet0TP'
HEADERS = {'Authorization': f'Bearer {API_KEY}'}

# === STEP 1: Pull base games with spreads and outcomes ===
def get_games(year):
    url = f"https://api.collegefootballdata.com/games?year={year}&seasonType=regular&division=fbs"
    r = requests.get(url, headers=HEADERS)
    return r.json()

all_games = []
for year in [2019, 2020, 2021, 2022, 2023]:
    games = get_games(year)
    for game in games:
        if not isinstance(game, dict):
            continue

        if not game.get('completed') or game.get('homePoints') is None or game.get('awayPoints') is None:
            continue

        spread = game.get('spread') or 0.0
        home_team = game.get('homeTeam')
        away_team = game.get('awayTeam')
        home_points = game.get('homePoints')
        away_points = game.get('awayPoints')

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

        favorite = home_team if spread < 0 else away_team
        underdog = away_team if spread < 0 else home_team
        winner = home_team if home_points > away_points else away_team if away_points > home_points else "tie"

        row.update({
            "favorite": favorite,
            "underdog": underdog,
            "winner": winner,
            "underdog_win": int(winner == underdog)
        })

        all_games.append(row)

base_df = pd.DataFrame(all_games)

# === STEP 2: Pull team stats week-by-week and compute rolling averages ===
def get_team_stats(year, week):
    url = f"https://api.collegefootballdata.com/stats/game/teams?year={year}&week={week}&seasonType=regular"
    for _ in range(3):
        r = requests.get(url, headers=HEADERS)
        try:
            if r.status_code == 200 and r.headers.get('Content-Type') == 'application/json' and r.text.strip():
                data = r.json()
                if isinstance(data, list):
                    return data
                else:
                    print(f"⚠️ Invalid JSON structure for year={year}, week={week} — Retrying...")
            else:
                print(f"⚠️ Empty or invalid response for year={year}, week={week} — Retrying...")
        except requests.exceptions.JSONDecodeError:
            print(f"⚠️ Failed to decode JSON for year={year}, week={week} — Retrying...")
        time.sleep(1)
    print(f"❌ Skipping year={year}, week={week} due to persistent error.")
    return []

stats_list = []
for year in [2019, 2020, 2021, 2022, 2023]:
    for week in range(1, 16):
        stats = get_team_stats(year, week)
        for team_stat in stats:
            team = team_stat['team']
            row = {
                'season': team_stat['season'],
                'week': team_stat['week'],
                'team': team
            }
            for stat in team_stat['stats']:
                row[stat['stat'].replace(' ', '_').lower()] = stat['value']
            stats_list.append(row)

stats_df = pd.DataFrame(stats_list)
num_cols = ['points', 'total_yards', 'yards_per_play', 'turnovers', 'third_down_conversions', 'third_down_attempts']
for col in num_cols:
    if col in stats_df.columns:
        stats_df[col] = pd.to_numeric(stats_df[col], errors='coerce')
    else:
        stats_df[col] = np.nan

stats_df['third_down_pct'] = stats_df.apply(lambda r: r['third_down_conversions'] / r['third_down_attempts'] if r['third_down_attempts'] else 0, axis=1)

rolling_stats = (
    stats_df.sort_values(['team', 'season', 'week'])
    .groupby('team')
    .rolling(3, on='week')[['points', 'total_yards', 'yards_per_play', 'turnovers', 'third_down_pct']]
    .mean()
    .reset_index()
    .rename(columns={
        'points': 'avg_points_3g',
        'total_yards': 'avg_yards_3g',
        'yards_per_play': 'avg_ypp_3g',
        'turnovers': 'avg_turnovers_3g',
        'third_down_pct': 'avg_3rd_pct_3g'
    })
)

# === STEP 3: Pull PPA metrics ===
def get_ppa(year):
    url = f"https://api.collegefootballdata.com/metrics/ppa/games?year={year}&seasonType=regular"
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.status_code == 200 else []

ppa_data = []
for year in [2019, 2020, 2021, 2022, 2023]:
    ppa_season = get_ppa(year)
    for game in ppa_season:
        for side in ['home', 'away']:
            team_data = game.get(side, {})
            ppa = team_data.get('ppa', {}).get('overall', {})
            ppa_data.append({
                'season': game.get('season'),
                'week': game.get('week'),
                'team': team_data.get('team'),
                'ppa': ppa.get('value'),
                'success_rate': ppa.get('successRate'),
                'explosiveness': ppa.get('explosiveness')
            })
ppa_df = pd.DataFrame(ppa_data)

# === STEP 4: Merge features into base_df ===
def attach_team_features(row, side):
    season = row['season']
    week = row['week']
    team = row[f'{side}_team']

    rs = rolling_stats[(rolling_stats['season'] == season) & (rolling_stats['week'] == week) & (rolling_stats['team'] == team)]
    ppa = ppa_df[(ppa_df['season'] == season) & (ppa_df['week'] == week) & (ppa_df['team'] == team)]

    if not rs.empty:
        for col in ['avg_points_3g', 'avg_yards_3g', 'avg_ypp_3g', 'avg_turnovers_3g', 'avg_3rd_pct_3g']:
            row[f'{side}_{col}'] = rs.iloc[0][col]
    if not ppa.empty:
        for col in ['ppa', 'success_rate', 'explosiveness']:
            row[f'{side}_{col}'] = ppa.iloc[0][col]
    return row

df = base_df.apply(lambda row: attach_team_features(row, 'home'), axis=1)
df = df.apply(lambda row: attach_team_features(row, 'away'), axis=1)

# === STEP 5: Add matchup deltas ===
delta_fields = ['avg_ypp_3g', 'avg_points_3g', 'avg_turnovers_3g', 'avg_3rd_pct_3g', 'ppa', 'success_rate', 'explosiveness']
for f in delta_fields:
    df[f'delta_{f}'] = df[f'home_{f}'] - df[f'away_{f}']

# === STEP 6: Simulated rest + travel distance (basic version) ===
df['home_days_rest'] = 7
df['away_days_rest'] = 7
df['home_is_short_week'] = df['home_days_rest'] < 6
df['away_is_short_week'] = df['away_days_rest'] < 6

df['home_travel_miles'] = 0  # Optional: Add lat/lon logic here
df['away_travel_miles'] = 0

# === Save final dataset ===
df.to_csv("final_all_features_dataset.csv", index=False)
print("✅ Saved final_all_features_dataset.csv with", len(df), "games")
