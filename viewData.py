import pandas as pd

print("=== VALORANT MATCHES DATA ===")
matches_df = pd.read_csv('valorant_matches.csv')
print("Columns:", matches_df.columns.tolist())
print("\nData shape:", matches_df.shape)
print("\nFirst few rows:")
print(matches_df.head())

print("\n=== VALORANT PLAYER STATS DATA ===")
player_stats_df = pd.read_csv('valorant_player_stats.csv')
print("Columns:", player_stats_df.columns.tolist())
print("\nData shape:", player_stats_df.shape)
print("\nFirst few rows:")
print(player_stats_df.head())

print("\n=== TOURNAMENTS REPRESENTED ===")
print(matches_df['tournament'].value_counts())