import os
import sys
import itertools
import subprocess
import re

# Configuration
PLAYER_DIR = "player"
ROUNDS_PER_MATCH = 20
BOARD_SIZE = (2, 2)

def parse_winner_from_output(output, p1_file, p2_file):
    """
    Parses the stdout from game_match.py to find the winner.
    This is dependent on the specific output format of game_match.py.
    """
    p1_wins = 0
    p2_wins = 0

    # Use regex to find lines like "player_file.py: 55 wins"
    for line in output.splitlines():
        # We use the base name for matching, as the output might not have the full path
        if os.path.basename(p1_file) in line and 'wins' in line:
            match = re.search(r'(\d+)\s+wins', line)
            if match:
                p1_wins = int(match.group(1))
        elif os.path.basename(p2_file) in line and 'wins' in line:
            match = re.search(r'(\d+)\s+wins', line)
            if match:
                p2_wins = int(match.group(1))

    if p1_wins > p2_wins:
        return p1_file
    elif p2_wins > p1_wins:
        return p2_file
    else:
        return "Draw"

def run_grand_tournament():
    """Finds all players, runs a round-robin tournament, and prints results."""
    print("Starting Dots and Boxes Tournament")

    try:
        player_files = [f for f in os.listdir(PLAYER_DIR) if f.endswith('.py') and f != '__init__.py']
        if len(player_files) < 2:
            print(f"Error: Found fewer than 2 players in '{PLAYER_DIR}'. Aborting.")
            sys.exit(1)
        print(f"Found {len(player_files)} players: {', '.join(player_files)}\n")
    except FileNotFoundError:
        print(f"Error: The player directory '{PLAYER_DIR}' was not found.")
        sys.exit(1)

    matchups = list(itertools.combinations(player_files, 2))
    tournament_scores = {player: {'wins': 0, 'losses': 0, 'draws': 0} for player in player_files}

    for i, (p1_file_base, p2_file_base) in enumerate(matchups):
        print(f"Match {i+1}/{len(matchups)}: {p1_file_base} vs {p2_file_base}")
        
        p1_path = os.path.join(PLAYER_DIR, p1_file_base)
        p2_path = os.path.join(PLAYER_DIR, p2_file_base)
        
        # Construct the exact command you would type in the terminal
        command = [
            sys.executable,         # The current python interpreter (e.g., 'python' or 'python3')
            "game_match.py",        # The script to run
            p1_path,                # First argument
            p2_path,                # Second argument
            "--rounds", str(ROUNDS_PER_MATCH),
            "--size", f"{BOARD_SIZE[0]}x{BOARD_SIZE[1]}"
        ]

        try:
            # Run the command as a separate process and capture its output
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=600)
            
            # Print the output from the match so you can see the details
            print(result.stdout)
            
            # Parse the winner from the captured output
            match_winner_base = parse_winner_from_output(result.stdout, p1_file_base, p2_file_base)

            if match_winner_base == p1_file_base:
                print(f"  {p1_file_base} wins the match!")
                tournament_scores[p1_file_base]['wins'] += 1
                tournament_scores[p2_file_base]['losses'] += 1
            elif match_winner_base == p2_file_base:
                print(f"  {p2_file_base} wins the match!")
                tournament_scores[p2_file_base]['wins'] += 1
                tournament_scores[p1_file_base]['losses'] += 1
            else: # Draw
                print(f"  The match is a draw!")
                tournament_scores[p1_file_base]['draws'] += 1
                tournament_scores[p2_file_base]['draws'] += 1

        except FileNotFoundError:
            print("  ERROR: 'game_match.py' not found. Make sure it's in the same directory.")
            break # No point continuing if the main script is missing
        except subprocess.CalledProcessError as e:
            print(f"  ERROR: The match crashed. Output:\n{e.stderr}")
        except subprocess.TimeoutExpired:
            print("  ERROR: Match took too long (over 10 minutes) and was terminated.")
        
        print("-" * 50 + "\n")


    # Display the final leaderboard
    print("\nFinal Leaderboard")
    sorted_players = sorted(tournament_scores.items(), key=lambda item: item[1]['wins'], reverse=True)
    print(f"{'Rank':<5} | {'Player':<25} | {'Wins':<5} | {'Losses':<6} | {'Draws':<5}")
    print("-" * 55)
    for rank, (player_file, scores) in enumerate(sorted_players, 1):
        wins, losses, draws = scores['wins'], scores['losses'], scores['draws']
        print(f"{rank:<5} | {player_file:<25} | {wins:<5} | {losses:<6} | {draws:<5}")

if __name__ == "__main__":
    run_grand_tournament()