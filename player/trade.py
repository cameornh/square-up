import random

def count_sides(r, c, game_state):
    """Helper: count how many sides of the box at (r, c) are filled."""
    count = 0
    if (r, c) in game_state["horizontal_lines"]:
        count += 1
    if (r + 1, c) in game_state["horizontal_lines"]:
        count += 1
    if (r, c) in game_state["vertical_lines"]:
        count += 1
    if (r, c + 1) in game_state["vertical_lines"]:
        count += 1
    return count

def move_creates_box(move, game_state):
    """Check if a move completes any box."""
    r, c, orientation = move
    if orientation == 'H':
        # Check below
        if r < game_state["board_size"][1] and count_sides(r, c, game_state) == 3:
            return True
        # Check above
        if r > 0 and count_sides(r - 1, c, game_state) == 3:
            return True
    else:  # 'V'
        # Check right
        if c < game_state["board_size"][0] and count_sides(r, c, game_state) == 3:
            return True
        # Check left
        if c > 0 and count_sides(r, c - 1, game_state) == 3:
            return True
    return False

def move_creates_risk(move, game_state):
    """Check if a move would create a box with 3 sides (giving opponent an easy point)."""
    r, c, orientation = move
    risky = False
    if orientation == 'H':
        # below
        if r < game_state["board_size"][1] and count_sides(r, c, game_state) == 2:
            risky = True
        # above
        if r > 0 and count_sides(r - 1, c, game_state) == 2:
            risky = True
    else:  # 'V'
        # right
        if c < game_state["board_size"][0] and count_sides(r, c, game_state) == 2:
            risky = True
        # left
        if c > 0 and count_sides(r, c - 1, game_state) == 2:
            risky = True
    return risky

def make_move(game_state):
    """
    Trade Bot — a balanced, defensive player that avoids risky moves,
    takes boxes when safe, and plays long-term positional strategy.
    """
    available_moves = game_state["available_moves"]

    # If any move completes a box, take it.
    box_moves = [m for m in available_moves if move_creates_box(m, game_state)]
    if box_moves:
        return random.choice(box_moves)

    # Avoid moves that set up 3-sides boxes.
    safe_moves = [m for m in available_moves if not move_creates_risk(m, game_state)]
    if safe_moves:
        return random.choice(safe_moves)

    # If all moves are risky, choose the least bad one (random fallback).
    return random.choice(available_moves)
