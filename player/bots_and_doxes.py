import copy
import time
from functools import lru_cache

# Bots and Doxes - Dots & Boxes AI
# Implements a depth-limited minimax search with alpha-beta pruning,
# a simple transposition table, opening heuristics, and rigorous move validation.
# The only required function (exported) is: def make_move(game_state)

# Configuration: tune depth by board area. Keep modest defaults for speed.
BASE_DEPTH = 4
# Give the bot more time for deeper search; user said time is not a problem
TIME_LIMIT = 5.0  # seconds per make_move (best-effort)
MAX_DEPTH_CAP = 20

# history heuristic for move ordering (simple)
history_table = {}
# killer moves per depth for move ordering: map depth -> [mv1, mv2]
killer_moves = {}

# Helper accessors -----------------------------------------------------------

def board_width_height(game_state):
    return game_state["board_size"]


def get_available_moves(game_state):
    return list(game_state["available_moves"])


# Simulation helpers: operate on a lightweight simulated state dict ---------
# The simulated state has the same keys as game_state but uses mutable sets
# and tracks current_player and scores to evaluate outcomes.

def make_sim_state(game_state):
    state = {
        "board_size": tuple(game_state["board_size"]),
        "horizontal_lines": set(game_state["horizontal_lines"]),
        "vertical_lines": set(game_state["vertical_lines"]),
        "box_owners": dict(game_state["box_owners"]),
        "current_player": game_state["your_player_id"],
        "scores": {1: 0, 2: 0},
    }
    # Derive scores from box_owners
    for owner in state["box_owners"].values():
        state["scores"][owner] = state["scores"].get(owner, 0) + 1
    return state


def is_valid_move_in_state(state, move):
    r, c, orientation = move
    width, height = state["board_size"]
    if orientation == 'H':
        if not (0 <= r <= height and 0 <= c < width):
            return False
        return (r, c) not in state["horizontal_lines"]
    elif orientation == 'V':
        if not (0 <= r < height and 0 <= c <= width):
            return False
        return (r, c) not in state["vertical_lines"]
    return False


def state_get_available_moves(state):
    moves = []
    width, height = state["board_size"]
    for r in range(height + 1):
        for c in range(width):
            if (r, c) not in state["horizontal_lines"]:
                moves.append((r, c, 'H'))
    for r in range(height):
        for c in range(width + 1):
            if (r, c) not in state["vertical_lines"]:
                moves.append((r, c, 'V'))
    return moves


def _is_box_complete_in_state(state, r, c):
    top = (r, c) in state["horizontal_lines"]
    bottom = (r + 1, c) in state["horizontal_lines"]
    left = (r, c) in state["vertical_lines"]
    right = (r, c + 1) in state["vertical_lines"]
    return top and bottom and left and right


def apply_move_to_state(state, move):
    """
    Applies move to a copied state and returns (new_state, boxes_completed, next_player)
    """
    if not is_valid_move_in_state(state, move):
        raise ValueError("Applying invalid move to simulated state: {}".format(move))

    new_state = {
        "board_size": state["board_size"],
        "horizontal_lines": set(state["horizontal_lines"]),
        "vertical_lines": set(state["vertical_lines"]),
        "box_owners": dict(state["box_owners"]),
        "current_player": state["current_player"],
        "scores": dict(state["scores"]),
    }

    r, c, orientation = move
    width, height = new_state["board_size"]

    if orientation == 'H':
        new_state["horizontal_lines"].add((r, c))
    else:
        new_state["vertical_lines"].add((r, c))

    boxes_completed = 0

    # check potentially affected boxes
    if orientation == 'H':
        # box below
        if r < height and _is_box_complete_in_state(new_state, r, c):
            new_state["box_owners"][(r, c)] = new_state["current_player"]
            boxes_completed += 1
        # box above
        if r > 0 and _is_box_complete_in_state(new_state, r - 1, c):
            new_state["box_owners"][(r - 1, c)] = new_state["current_player"]
            boxes_completed += 1
    else:  # 'V'
        # box right
        if c < width and _is_box_complete_in_state(new_state, r, c):
            new_state["box_owners"][(r, c)] = new_state["current_player"]
            boxes_completed += 1
        # box left
        if c > 0 and _is_box_complete_in_state(new_state, r, c - 1):
            new_state["box_owners"][(r, c - 1)] = new_state["current_player"]
            boxes_completed += 1

    if boxes_completed > 0:
        new_state["scores"][new_state["current_player"]] = new_state["scores"].get(new_state["current_player"], 0) + boxes_completed
        next_player = new_state["current_player"]
    else:
        next_player = 3 - new_state["current_player"]
        new_state["current_player"] = next_player

    return new_state, boxes_completed, next_player


def resolve_all_forced_captures(state):
    """Simulate all forced captures (3-sided boxes) greedily until none remain.
    Returns a new state after all immediate captures are resolved."""
    st = {
        "board_size": state["board_size"],
        "horizontal_lines": set(state["horizontal_lines"]),
        "vertical_lines": set(state["vertical_lines"]),
        "box_owners": dict(state["box_owners"]),
        "current_player": state["current_player"],
        "scores": dict(state["scores"]),
    }
    while True:
        comps = find_completable_boxes_in_state(st)
        if not comps:
            break
        # pick a capture move that completes at least one box (prefer multi-box)
        best_mv = None
        best_boxes = -1
        moves = state_get_available_moves(st)
        for mv in moves:
            r, c, orientation = mv
            boxes = 0
            if orientation == 'H':
                if r < st['board_size'][1] and count_box_sides_in_state(st, r, c) == 3:
                    boxes += 1
                if r > 0 and count_box_sides_in_state(st, r - 1, c) == 3:
                    boxes += 1
            else:
                if c < st['board_size'][0] and count_box_sides_in_state(st, r, c) == 3:
                    boxes += 1
                if c > 0 and count_box_sides_in_state(st, r, c - 1) == 3:
                    boxes += 1
            if boxes > best_boxes:
                best_boxes = boxes
                best_mv = mv
        if best_mv is None or best_boxes == 0:
            break
        st, _, _ = apply_move_to_state(st, best_mv)
    return st


# Heuristics and evaluation --------------------------------------------------

def count_box_sides_in_state(state, r, c):
    count = 0
    if (r, c) in state["horizontal_lines"]: count += 1
    if (r + 1, c) in state["horizontal_lines"]: count += 1
    if (r, c) in state["vertical_lines"]: count += 1
    if (r, c + 1) in state["vertical_lines"]: count += 1
    return count


def find_completable_boxes_in_state(state):
    width, height = state["board_size"]
    comps = []
    for r in range(height):
        for c in range(width):
            if (r, c) not in state["box_owners"] and count_box_sides_in_state(state, r, c) == 3:
                comps.append((r, c))
    return comps


def evaluate_state(state, my_id):
    """
    Evaluation function (higher is better for my_id). Combines immediate score diff,
    potential captures (3-side boxes), and penalties for giving opponent moves.
    """
    opp = 3 - my_id
    score = state["scores"].get(my_id, 0) - state["scores"].get(opp, 0)

    # value of imminent captures
    comps = find_completable_boxes_in_state(state)
    # if it's my turn, these are positive; otherwise they are negative for me
    turn_multiplier = 1 if state["current_player"] == my_id else -1
    score += 0.9 * len(comps) * turn_multiplier

    # penalty for number of 2-sided boxes (they indicate chains forming that can be dangerous)
    width, height = state["board_size"]
    two_sided = 0
    for r in range(height):
        for c in range(width):
            if (r, c) not in state["box_owners"] and count_box_sides_in_state(state, r, c) == 2:
                two_sided += 1
    # make this penalty stronger so we aggressively avoid creating chains greedy can exploit
    score -= 0.45 * two_sided

    # small tie-breaker favoring center-ish moves by number of remaining moves
    remaining = len(state_get_available_moves(state))
    score += 0.01 * ( (width * height * 4) - remaining )

    # parity-aware chain estimation (more accurate than raw chain_sum)
    score += parity_chain_value(state, my_id)

    # mobility: fewer opponent moves is slightly better
    opp = 3 - my_id
    # count opponent moves by simulating a no-capture single-step opponent move count
    # (cheap approximation): if opponent is next, use current available; otherwise estimate after one move
    avail = len(state_get_available_moves(state))
    score -= 0.02 * avail

    return score


def find_chains_in_state(state):
    """Find connected components of boxes with exactly 2 sides (simple chain detection).
    Returns a list of chain lengths."""
    width, height = state["board_size"]
    visited = set()
    chains = []
    for r in range(height):
        for c in range(width):
            if (r, c) in visited:
                continue
            if (r, c) in state["box_owners"]:
                continue
            if count_box_sides_in_state(state, r, c) != 2:
                continue
            # BFS
            stack = [(r, c)]
            visited.add((r, c))
            length = 0
            while stack:
                br, bc = stack.pop()
                length += 1
                # neighbors: up/down/left/right
                for nr, nc in ((br-1, bc), (br+1, bc), (br, bc-1), (br, bc+1)):
                    if 0 <= nr < height and 0 <= nc < width and (nr, nc) not in visited and (nr, nc) not in state["box_owners"] and count_box_sides_in_state(state, nr, nc) == 2:
                        visited.add((nr, nc))
                        stack.append((nr, nc))
            chains.append(length)
    return chains


def parity_chain_value(state, my_id):
    """Estimate the parity value of chains and loops in the position.
    This is an approximation: for each chain of length L we award +/- ceil(L/2)
    to the player who stands to benefit given whose turn it is. Loops are
    treated like chains but slightly discounted since they can be converted.
    """
    chains = find_chains_in_state(state)
    if not chains:
        return 0

    total = 0
    for L in chains:
        val = (L + 1) // 2  # parity value approximation
        # if opponent to move, this favors us (they may be forced to open)
        if state["current_player"] == my_id:
            total -= val
        else:
            total += val

    # discount factor for approximation
    return 0.9 * total


# Transposition table key ---------------------------------------------------

def make_tt_key(state):
    return (
        state["current_player"],
        tuple(sorted(state["horizontal_lines"])),
        tuple(sorted(state["vertical_lines"]))
    )


# Minimax with alpha-beta and transposition table ---------------------------

def find_best_move_with_minimax(root_state, my_id, time_limit=TIME_LIMIT):
    start_time = time.time()
    width, height = root_state["board_size"]
    area = width * height
    # choose max depth heuristically by board area; iterative deepening will use this as cap
    max_depth = BASE_DEPTH
    if area <= 4:
        max_depth = 14
    elif area <= 9:
        max_depth = 12
    elif area <= 25:
        max_depth = 10
    max_depth = min(max_depth, MAX_DEPTH_CAP)

    tt = {}
    best_move = None
    best_val = float('-inf')

    moves = state_get_available_moves(root_state)
    if not moves:
        return None

    # Order moves: prefer those that complete boxes (quick heuristic)
    def move_priority(move):
        r, c, orientation = move
        # emulate without copying heavy state: quick check
        temp_state = root_state
        # check if move completes box
        completed = 0
        if orientation == 'H':
            if r < height and count_box_sides_in_state(temp_state, r, c) == 3: completed += 1
            if r > 0 and count_box_sides_in_state(temp_state, r - 1, c) == 3: completed += 1
        else:
            if c < width and count_box_sides_in_state(temp_state, r, c) == 3: completed += 1
            if c > 0 and count_box_sides_in_state(temp_state, r, c - 1) == 3: completed += 1
        # reduction in opponent options metric
        # simulate applying the move quickly
        try:
            ns, boxes, _ = apply_move_to_state(root_state, move)
            opp_next_moves = len(state_get_available_moves(ns))
        except Exception:
            opp_next_moves = 999

        hist_score = history_table.get((move), 0)

        # penalize moves that create 3-sided boxes for opponent after our move (very bad)
        try:
            ns2, b2, _ = apply_move_to_state(root_state, move)
            # count 3-side boxes that opponent would get immediately (i.e., boxes with 3 sides after our move)
            opp_threes = 0
            for rr in range(ns2['board_size'][1]):
                for cc in range(ns2['board_size'][0]):
                    if (rr, cc) not in ns2['box_owners'] and count_box_sides_in_state(ns2, rr, cc) == 3:
                        opp_threes += 1
        except Exception:
            opp_threes = 0

        # Higher completed -> higher priority, fewer opp moves -> higher priority, but huge penalty for opp threes
        return (-completed, opp_next_moves, opp_threes, -hist_score)

    moves.sort(key=move_priority)

    # inner recursive minimax
    def minimax(state, depth_left, alpha, beta, maximizing, my_id):
        # time cutoff
        if time.time() - start_time > time_limit:
            # raise to bubble up the timeout
            raise TimeoutError()

        key = make_tt_key(state)
        if key in tt and tt[key]["depth"] >= depth_left:
            # reuse stored value
            return tt[key]["value"]

        # quiescence: if there are immediate captures, resolve them before evaluating/branching
        avail = state_get_available_moves(state)
        if not avail:
            val = evaluate_state(state, my_id)
            tt[key] = {"value": val, "depth": depth_left}
            return val

        if depth_left == 0:
            # resolve forced captures before evaluation
            resolved = resolve_all_forced_captures(state)
            val = evaluate_state(resolved, my_id)
            tt[key] = {"value": val, "depth": depth_left}
            return val

        if maximizing:
            value = float('-inf')
            # order moves: try TT/PV move first, then killer moves for this depth, then captures, then history
            pv_move = tt.get(key, {}).get("best_move") if key in tt else None
            kmoves = killer_moves.get(depth_left, [])
            def move_order_key(mv):
                r,c,o = mv
                score = 0
                if pv_move is not None and mv == pv_move:
                    score -= 10000
                if mv in kmoves:
                    score -= 5000
                # prefer captures
                b = 0
                if o == 'H':
                    if r < state['board_size'][1] and count_box_sides_in_state(state,r,c) == 3: b += 1
                    if r > 0 and count_box_sides_in_state(state,r-1,c) == 3: b += 1
                else:
                    if c < state['board_size'][0] and count_box_sides_in_state(state,r,c) == 3: b += 1
                    if c > 0 and count_box_sides_in_state(state,r,c-1) == 3: b += 1
                score -= b*100
                # history heuristic (prefer moves with higher history_table)
                score -= history_table.get(mv,0)
                return score

            ordered_avail = sorted(avail, key=move_order_key)
            best_local_move = None
            for mv in ordered_avail:
                new_state, boxes, _ = apply_move_to_state(state, mv)
                next_maximizing = (new_state["current_player"] == my_id)
                # if capture occurred, keep depth (extra turn doesn't consume search depth)
                next_depth = depth_left if boxes > 0 else depth_left - 1
                v = minimax(new_state, next_depth, alpha, beta, next_maximizing, my_id)
                if v > value:
                    value = v
                    best_local_move = mv
                alpha = max(alpha, value)
                if alpha >= beta:
                    # beta cutoff -> record killer move
                    km = killer_moves.setdefault(depth_left, [])
                    if mv not in km:
                        km.insert(0, mv)
                        if len(km) > 2:
                            km.pop()
                    break
            tt[key] = {"value": value, "depth": depth_left, "best_move": best_local_move or tt.get(key,{}).get("best_move", None)}
            return value
        else:
            value = float('inf')
            pv_move = tt.get(key, {}).get("best_move") if key in tt else None
            kmoves = killer_moves.get(depth_left, [])
            def move_order_key2(mv):
                r,c,o = mv
                score = 0
                if pv_move is not None and mv == pv_move:
                    score -= 10000
                if mv in kmoves:
                    score -= 5000
                # prefer captures
                b = 0
                if o == 'H':
                    if r < state['board_size'][1] and count_box_sides_in_state(state,r,c) == 3: b += 1
                    if r > 0 and count_box_sides_in_state(state,r-1,c) == 3: b += 1
                else:
                    if c < state['board_size'][0] and count_box_sides_in_state(state,r,c) == 3: b += 1
                    if c > 0 and count_box_sides_in_state(state,r,c-1) == 3: b += 1
                score -= b*100
                score -= history_table.get(mv,0)
                return score

            ordered_avail = sorted(avail, key=move_order_key2)
            best_local_move = None
            for mv in ordered_avail:
                new_state, boxes, _ = apply_move_to_state(state, mv)
                next_maximizing = (new_state["current_player"] == my_id)
                next_depth = depth_left if boxes > 0 else depth_left - 1
                v = minimax(new_state, next_depth, alpha, beta, next_maximizing, my_id)
                if v < value:
                    value = v
                    best_local_move = mv
                beta = min(beta, value)
                if alpha >= beta:
                    # record killer
                    km = killer_moves.setdefault(depth_left, [])
                    if mv not in km:
                        km.insert(0, mv)
                        if len(km) > 2:
                            km.pop()
                    break
            tt[key] = {"value": value, "depth": depth_left, "best_move": best_local_move or tt.get(key,{}).get("best_move", None)}
            return value

    # Evaluate root moves with alpha-beta
    # Iterative deepening loop
    try:
        for d in range(1, max_depth + 1):
            # stop if time nearly up
            if time.time() - start_time > time_limit:
                break
            cur_best = None
            cur_best_val = float('-inf')
            # use same ordering
            for mv in moves:
                if time.time() - start_time > time_limit:
                    break
                if not is_valid_move_in_state(root_state, mv):
                    continue
                new_state, boxes, _ = apply_move_to_state(root_state, mv)
                maximizing = (new_state["current_player"] == my_id)
                next_depth = d - 1 if boxes == 0 else d
                val = minimax(new_state, next_depth, float('-inf'), float('inf'), maximizing, my_id)
                if val > cur_best_val or cur_best is None:
                    cur_best_val = val
                    cur_best = mv
            # accept cur_best if found
            if cur_best is not None:
                best_move = cur_best
                best_val = cur_best_val
                # update history heuristic to prefer this move next time
                history_table[cur_best] = history_table.get(cur_best, 0) + 1
    except TimeoutError:
        # timed out; return best found so far
        pass

    # If we didn't find anything with minimax or timed out, fallback heuristics
    if best_move is None:
        # Try to find any completions
        for mv in moves:
            r, c, orientation = mv
            if orientation == 'H':
                if r < height and count_box_sides_in_state(root_state, r, c) == 3:
                    return mv
                if r > 0 and count_box_sides_in_state(root_state, r - 1, c) == 3:
                    return mv
            else:
                if c < width and count_box_sides_in_state(root_state, r, c) == 3:
                    return mv
                if c > 0 and count_box_sides_in_state(root_state, r, c - 1) == 3:
                    return mv

        # otherwise choose the move that looks safest
        for mv in moves:
            if is_safe_move_in_root(root_state, mv):
                return mv

        return moves[0]

    return best_move


# Safety check used in fallback: avoid creating 3-side boxes for opponent
def is_safe_move_in_root(state, move):
    r, c, orientation = move
    width, height = state["board_size"]
    if orientation == 'H':
        if r < height and count_box_sides_in_state(state, r, c) == 2:
            return False
        if r > 0 and count_box_sides_in_state(state, r - 1, c) == 2:
            return False
    else:
        if c < width and count_box_sides_in_state(state, r, c) == 2:
            return False
        if c > 0 and count_box_sides_in_state(state, r, c - 1) == 2:
            return False
    return True


# Public API required by the tournament runner -------------------------------

def make_move(game_state):
    """
    Entry point for the tournament. Must return a single move (r, c, 'H'|'V').
    Guarantees to return a legal move from game_state["available_moves"].
    """
    # Validate inputs and ensure we won't return an illegal move
    available = list(game_state.get("available_moves", []))
    if not available:
        # no moves left (shouldn't happen unless game end); return a dummy safe move
        # but to avoid invalid move, raise or return arbitrary first move if present
        raise RuntimeError("No available moves in game_state")

    # Build a lightweight simulated state for search
    root_state = make_sim_state(game_state)
    # override the simulated current_player to match runner's provided id
    root_state["current_player"] = game_state["your_player_id"]

    # Try timeout-aware minimax search
    try:
        mv = find_best_move_with_minimax(root_state, game_state["your_player_id"], time_limit=TIME_LIMIT)
    except Exception:
        # In case something unexpected happens, fallback to a safe choice
        mv = None

    # Ensure returned move is in available moves and legal
    if mv is None or mv not in available:
        # Try to pick a completions move first
        for candidate in available:
            r, c, orientation = candidate
            if orientation == 'H':
                if r < root_state['board_size'][1] and count_box_sides_in_state(root_state, r, c) == 3:
                    return candidate
                if r > 0 and count_box_sides_in_state(root_state, r - 1, c) == 3:
                    return candidate
            else:
                if c < root_state['board_size'][0] and count_box_sides_in_state(root_state, r, c) == 3:
                    return candidate
                if c > 0 and count_box_sides_in_state(root_state, r, c - 1) == 3:
                    return candidate

        # pick any safe available move
        for candidate in available:
            if is_safe_move_in_root(root_state, candidate):
                return candidate

        # last resort: return the first available move
        return available[0]

    return mv
