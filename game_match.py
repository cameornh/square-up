import sys
import importlib.util
import argparse
from game_logic import DotsAndBoxesGame

def load_player_module(file_path):
    """Dynamically loads a player's Python file as a module."""
    module_name = file_path.replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def play_one_round(player1_module, player2_module, board_size, starting_player):
    """Plays a single game of Dots and Boxes and returns the winner."""
    game = DotsAndBoxesGame(width=board_size[0], height=board_size[1])
    players = {1: player1_module, 2: player2_module}
    game.current_player = starting_player

    while not game.game_over:
        current_player_module = players[game.current_player]
        
        # Get the complete game state to pass to the player
        game_state = game.get_state()
        game_state["available_moves"] = game.get_available_moves()

        try:
            move = current_player_module.make_move(game_state)
            is_valid, _ = game.apply_move(*move)
            if not is_valid:
                print(f"Player {game.current_player} made an invalid move {move}. Forfeiting round.")
                return 3 - game.current_player # the other player wins
        except Exception as e:
            print(f"Player {game.current_player}'s code produced an error: {e}. Forfeiting round.")
            return 3 - game.current_player

    return game.get_winner()

def main():
    parser = argparse.ArgumentParser(description="Run a Dots and Boxes tournament between two AI players.") # argparser will show this if you use --help flag
    
    parser.add_argument("player1_file", help="The python file for player 1.")
    parser.add_argument("player2_file", help="The python file for player 2.")
    
    # Optional arguments with flags
    parser.add_argument("-r", "--rounds", type=int, default=20, 
                        help="Number of rounds to play. Must be an even number. Defaults to 20.")
    parser.add_argument("-s", "--size", type=str, default="2x2", 
                        help="Board size formatted as WIDTHxHEIGHT (e.g., '4x4'). Defaults to '2x2'.")

    args = parser.parse_args()

    # Use the parsed arguments
    player1_file = args.player1_file
    player2_file = args.player2_file
    total_rounds = args.rounds

    if total_rounds % 2 != 0:
        print("Error: The number of rounds must be even so that each player starts the same number of times.")
        sys.exit(1)

    # Parse board size from string 'WxH' to tuple (W, H)
    try:
        width, height = map(int, args.size.split('x'))
        board_size = (width, height)
    except ValueError:
        print("Error: Invalid board size format. Please use WIDTHxHEIGHT (e.g., '4x4').")
        sys.exit(1)
    
    if len(sys.argv) < 3 or len(sys.argv) > 7:
        print("Usage: python ../game_match.py <player1_file.py> <player2_file.py>")
        sys.exit(1)

    try:
        player1 = load_player_module(player1_file)
        player2 = load_player_module(player2_file)
    except Exception as e:
        print(f"Error loading player files: {e}")
        sys.exit(1)

    total_rounds = 20 # change round count here (should be even so that each player starts the same amount of times)
    board_size = (2, 2) # change board size here
    scores = {player1_file: 0, player2_file: 0, "Draws": 0}

    print(f"{player1_file} vs {player2_file}")
    
    for i in range(total_rounds):
        # alternate who starts each round, first argument player will always go first
        starting_player = 1 if i % 2 == 0 else 2
        
        winner = play_one_round(player1, player2, board_size, starting_player)
        
        round_winner_name = "no one (Draw)"
        if winner == 1:
            scores[player1_file] += 1
            round_winner_name = player1_file
        elif winner == 2:
            scores[player2_file] += 1
            round_winner_name = player2_file
        else:
            scores["Draws"] += 1
            
        print(f"Round {i+1}: Winner is {round_winner_name}")

    print("\nFinal Score:")
    print(f"{player1_file}: {scores[player1_file]} wins")
    print(f"{player2_file}: {scores[player2_file]} wins")
    print(f"Draws: {scores['Draws']}")

if __name__ == "__main__":
    main()
