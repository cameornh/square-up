import random

def count_sides(r, c, game_state):
    """Helper function to count existing sides of a box at (r, c)."""
    count = 0
    if (r, c) in game_state["horizontal_lines"]: count += 1
    if (r + 1, c) in game_state["horizontal_lines"]: count += 1
    if (r, c) in game_state["vertical_lines"]: count += 1
    if (r, c + 1) in game_state["vertical_lines"]: count += 1
    return count

def make_move(game_state):
    """
    A greedy bot that takes a winning move if available, otherwise plays randomly.
    """
    available_moves = game_state["available_moves"]
    
    # Search for a move that completes a box (i.e., is the 4th side)
    for move in available_moves:
        r, c, orientation = move
        if orientation == 'H':
            # Check box below
            if r < game_state["board_size"][1] and count_sides(r, c, game_state) == 3:
                return move
            # Check box above
            if r > 0 and count_sides(r - 1, c, game_state) == 3:
                return move
        else: # 'V'
            # Check box to the right
            if c < game_state["board_size"][0] and count_sides(r, c, game_state) == 3:
                return move
            # Check box to the left
            if c > 0 and count_sides(r, c - 1, game_state) == 3:
                return move

    # If no winning move is found, just pick a random one.
    # A smarter bot would avoid giving the opponent a box.
    return random.choice(available_moves)
