import random
import copy

def count_sides(r, c, game_state):
    """Helper function to count existing sides of a box at (r, c)."""
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


def apply_move_inplace(state, move, player_id):
    """Apply a move to the state in-place and return number of boxes completed."""
    r, c, o = move
    if o == 'H':
        state["horizontal_lines"].add((r, c))
    else:
        state["vertical_lines"].add((r, c))

    if move in state["available_moves"]:
        state["available_moves"].remove(move)

    completed = 0
    width, height = state["board_size"]
    affected = []
    if o == 'H':
        affected = [(r - 1, c), (r, c)]
    else:
        affected = [(r, c - 1), (r, c)]

    for br, bc in affected:
        if 0 <= br < height and 0 <= bc < width:
            if count_sides(br, bc, state) == 4 and (br, bc) not in state["box_owners"]:
                state["box_owners"][(br, bc)] = player_id
                completed += 1

    # Determine next player
    state["next_player"] = player_id if completed > 0 else 3 - player_id
    return completed


def simulate_greedy_exhaust(state, greedy_player_id):
    """Simulate a greedy opponent repeatedly taking any available 3-sided boxes."""
    while True:
        moved = False
        for mv in list(state["available_moves"]):
            # Check if this move completes a box
            s_test = copy.deepcopy(state)
            completed = apply_move_inplace(s_test, mv, greedy_player_id)
            if completed > 0:
                apply_move_inplace(state, mv, greedy_player_id)
                moved = True
                break
        if not moved:
            break
    return state


def score_state_for_player(state, player_id):
    """Compute the score difference (my_boxes - opp_boxes)."""
    my = sum(1 for v in state["box_owners"].values() if v == player_id)
    opp = sum(1 for v in state["box_owners"].values() if v == 3 - player_id)
    return my - opp


def find_best_exploit_move(game_state):
    """
    Try every legal move, simulate greedy responses, and pick the move
    that maximizes (my_boxes - opp_boxes) after the greedy sequence.
    """
    me = game_state["your_player_id"]
    best_move = None
    best_score = -float("inf")

    for mv in list(game_state["available_moves"]):
        s_copy = copy.deepcopy(game_state)
        apply_move_inplace(s_copy, mv, me)
        next_player = s_copy.get("next_player", me)

        if next_player != me:
            s_after = simulate_greedy_exhaust(s_copy, next_player)
        else:
            s_after = copy.deepcopy(s_copy)
            s_after = simulate_greedy_exhaust(s_after, 3 - me)

        sc = score_state_for_player(s_after, me)
        if sc > best_score:
            best_score = sc
            best_move = mv

    return best_move


def make_move(game_state):
    """
    Exploitative player that simulates greedy responses
    and picks the move maximizing the resulting score advantage.
    """
    move = find_best_exploit_move(game_state)
    if move is not None:
        return move
    # fallback in case of unexpected issue
    return random.choice(game_state["available_moves"])
