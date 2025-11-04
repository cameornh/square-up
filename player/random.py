import random

def make_move(game_state):
    """
    This function is called by the tournament runner.
    It returns a move in the format: (row, col, 'H' or 'V')
    """
    # The runner provides a list of all possible moves.
    available_moves = game_state["available_moves"]
    
    # choose a move at random.
    return random.choice(available_moves)
