# super_bot.py
import random
import copy
import math
from functools import lru_cache

# ---------------------------
# Internal helpers (self-contained)
# ---------------------------

def count_sides(r, c, state):
    """Count sides of box at (r, c)."""
    cnt = 0
    if (r, c) in state["horizontal_lines"]:
        cnt += 1
    if (r + 1, c) in state["horizontal_lines"]:
        cnt += 1
    if (r, c) in state["vertical_lines"]:
        cnt += 1
    if (r, c + 1) in state["vertical_lines"]:
        cnt += 1
    return cnt

def canonical_key(state):
    """Create a compact, hashable key for memoization from the game state.
    Uses frozensets of lines and frozenset of owned boxes items, plus next_player."""
    h = frozenset(state["horizontal_lines"])
    v = frozenset(state["vertical_lines"])
    b = frozenset(state["box_owners"].items())
    next_p = state.get("next_player", state["your_player_id"])
    return (h, v, b, next_p)

def apply_move(state, move, player_id):
    """Return a new copied state after applying move by player_id and whether it completed any box(s)."""
    s = copy.deepcopy(state)
    r, c, o = move
    completed = 0

    if o == 'H':
        s["horizontal_lines"].add((r, c))
    else:
        s["vertical_lines"].add((r, c))

    if move in s["available_moves"]:
        s["available_moves"].remove(move)

    width, height = s["board_size"]
    affected = []
    if o == 'H':
        affected = [(r - 1, c), (r, c)]
    else:
        affected = [(r, c - 1), (r, c)]

    for br, bc in affected:
        if 0 <= br < height and 0 <= bc < width:
            if count_sides(br, bc, s) == 4 and (br, bc) not in s["box_owners"]:
                s["box_owners"][(br, bc)] = player_id
                completed += 1

    # next_player handling: if completed at least one box, same player continues
    s["next_player"] = player_id if completed > 0 else 3 - player_id
    return s, completed

# ---------------------------
# Exact solver (negamax-like) for small endgames
# ---------------------------
def solve_exact(state):
    """Return the score difference (current_player_boxes - opponent_boxes) assuming perfect play
    for the remainder of the game from the perspective of the player who is about to move.
    This uses recursion with memoization and the typical Dots & Boxes negamax transformation:
      - If a move completes k boxes, reward k + solve(new_state)
      - Otherwise the value is -solve(new_state)
    """

    @lru_cache(maxsize=None)
    def _solve(hfro, vfro, boxfro, next_player, width, height):
        # Reconstruct minimal state
        horizontal = set(hfro)
        vertical = set(vfro)
        box_owners = dict(boxfro)
        # compute available moves
        avail = []
        # horizontal moves: r from 0..height, c from 0..width-1
        for r in range(0, height + 1):
            for c in range(0, width):
                mv = (r, c, 'H')
                if mv not in horizontal:
                    avail.append(mv)
        for r in range(0, height):
            for c in range(0, width + 1):
                mv = (r, c, 'V')
                if mv not in vertical:
                    avail.append(mv)

        if not avail:
            # game over: compute final difference for next_player perspective
            p_boxes = sum(1 for v in box_owners.values() if v == next_player)
            o_boxes = sum(1 for v in box_owners.values() if v == 3 - next_player)
            return p_boxes - o_boxes

        best = -10**9
        # try all moves
        for mv in avail:
            r, c, o = mv
            completed = 0
            # apply move locally
            if o == 'H':
                horizontal2 = set(horizontal)
                horizontal2.add(mv)
                vertical2 = set(vertical)
            else:
                vertical2 = set(vertical)
                vertical2.add(mv)
                horizontal2 = set(horizontal)

            box2 = dict(box_owners)
            affected = []
            if o == 'H':
                affected = [(r - 1, c), (r, c)]
            else:
                affected = [(r, c - 1), (r, c)]

            for br, bc in affected:
                if 0 <= br < height and 0 <= bc < width:
                    top = (br, bc) in horizontal2
                    bottom = (br + 1, bc) in horizontal2
                    left = (br, bc) in vertical2
                    right = (br, bc + 1) in vertical2
                    if top and bottom and left and right and (br, bc) not in box2:
                        box2[(br, bc)] = next_player
                        completed += 1

            if completed > 0:
                val = completed + _solve(frozenset(horizontal2), frozenset(vertical2), frozenset(box2.items()), next_player, width, height)
            else:
                # opponent to move; value is negative of their score difference
                val_op = _solve(frozenset(horizontal2), frozenset(vertical2), frozenset(box2.items()), 3 - next_player, width, height)
                val = -val_op

            if val > best:
                best = val
                # alpha-beta could be added but for very small spaces it's fine

        return best

    hfro = frozenset(state["horizontal_lines"])
    vfro = frozenset(state["vertical_lines"])
    boxfro = frozenset(state["box_owners"].items())
    next_player = state.get("next_player", state["your_player_id"])
    w, h = state["board_size"]
    return _solve(hfro, vfro, boxfro, next_player, w, h)

# ---------------------------
# MCTS implementation (with heuristic rollout)
# ---------------------------

class MNode:
    __slots__ = ("state_key","state","move","parent","children","visits","wins","untried")
    def __init__(self, state, move=None):
        self.state = state
        self.state_key = canonical_key(state)
        self.move = move
        self.parent = None
        self.children = []
        self.visits = 0
        self.wins = 0.0
        self.untried = list(state["available_moves"])

    def uct_score(self, child, c=1.4):
        if child.visits == 0:
            return float('inf')
        return (child.wins / child.visits) + c * math.sqrt(math.log(self.visits + 1) / child.visits)

def rollout_policy(state):
    """Heuristic rollout policy:
    - If a move completes a box, pick it.
    - Else avoid moves that create a 3-sided box if possible.
    - Otherwise random.
    """
    # immediate wins
    for mv in state["available_moves"]:
        s2, completed = apply_move(state, mv, state.get("next_player", state["your_player_id"]))
        if completed > 0:
            return mv

    # avoid risky moves
    safe = []
    for mv in state["available_moves"]:
        r, c, o = mv
        risky = False
        width, height = state["board_size"]
        # check boxes that would be affected: if any becomes 3-sided after this move, it's risky
        if o == 'H':
            affected = [(r - 1, c), (r, c)]
        else:
            affected = [(r, c - 1), (r, c)]
        # simulate single-line add (without completing)
        for br, bc in affected:
            if 0 <= br < height and 0 <= bc < width:
                # count current sides (before move)
                sides_before = count_sides(br, bc, state)
                # if the move increases sides to 3, it's risky
                if sides_before == 2:
                    risky = True
                    break
        if not risky:
            safe.append(mv)

    if safe:
        return random.choice(safe)

    # fallback
    return random.choice(state["available_moves"])

def simulate_playout(state, me_id):
    """Simulate a full game from state using rollout_policy. Return 1 if me wins, 0 lose/draw."""
    s = copy.deepcopy(state)
    current = s.get("next_player", s["your_player_id"])
    while s["available_moves"]:
        mv = rollout_policy(s)
        s, completed = apply_move(s, mv, current)
        if completed == 0:
            current = s["next_player"]
        # else current remains (scored a box)

    # final scoring
    scores = {1:0, 2:0}
    for owner in s["box_owners"].values():
        scores[owner] += 1
    me = me_id
    opp = 3 - me
    if scores[me] > scores[opp]:
        return 1
    else:
        return 0

def mcts_choose_move(root_state, me_id, iterations):
    root = MNode(root_state)

    # quick safety: if only one move, return it
    if len(root_state["available_moves"]) == 1:
        return root_state["available_moves"][0]

    for _ in range(iterations):
        node = root
        state = copy.deepcopy(root_state)

        # SELECTION
        while node.untried == [] and node.children:
            # pick child with best UCT
            node = max(node.children, key=lambda c: node.uct_score(c))
            state, _ = apply_move(state, node.move, state.get("next_player", state["your_player_id"]))

        # EXPANSION
        if node.untried:
            mv = random.choice(node.untried)
            state, completed = apply_move(state, mv, state.get("next_player", state["your_player_id"]))
            child = MNode(state, move=mv)
            child.parent = node
            node.children.append(child)
            node.untried.remove(mv)
            node = child

        # SIMULATION
        reward = simulate_playout(state, me_id)

        # BACKPROPAGATION
        while node is not None:
            node.visits += 1
            node.wins += reward
            node = node.parent

    # pick child with best visit count / win rate
    best = max(root.children, key=lambda c: (c.wins / (c.visits + 1e-9), c.visits))
    return best.move

# ---------------------------
# Public API: make_move(game_state)
# ---------------------------

def make_move(game_state):
    """
    Ultimate-playing bot entry point. Expects game_state in the form:
    {
      "board_size": (width, height),
      "horizontal_lines": set(),
      "vertical_lines": set(),
      "box_owners": dict(),
      "your_player_id": 1 or 2,
      "available_moves": [(r,c,o), ...]
      # optional: "next_player": id
    }
    Returns a move (r, c, 'H' or 'V').
    """
    # Normalize next_player
    if "next_player" not in game_state:
        game_state["next_player"] = game_state["your_player_id"]

    me = game_state["your_player_id"]
    next_p = game_state["next_player"]

    # 1) Immediate winning move: if we can complete a box now, do it.
    for mv in game_state["available_moves"]:
        s2, completed = apply_move(game_state, mv, next_p)
        if completed > 0:
            # If it's our turn, and we complete a box, play it.
            # If it's opponent's turn, avoid - but typically game harness calls on our turn.
            return mv

    # 2) If very small remaining space, run exact solver.
    N_avail = len(game_state["available_moves"])
    if N_avail <= 10:
        # Use exact solver: evaluate every candidate move
        best_move = None
        best_val = -10**9
        for mv in game_state["available_moves"]:
            s2, completed = apply_move(game_state, mv, next_p)
            if completed > 0:
                val = completed + solve_exact(s2)  # same player's perspective continues
            else:
                # opponent to move, value is negative of opponent's optimal result
                # solve_exact returns value for player to move in s2 (which will be opponent)
                val = -solve_exact(s2)
            if val > best_val:
                best_val = val
                best_move = mv
        return best_move

    # 3) Otherwise use MCTS with heuristic rollouts. Tune iterations by board area:
    width, height = game_state["board_size"]
    area = width * height
    # Heuristic: more simulations for larger boards, but cap to reasonable number
    base = 800
    iterations = int(min(8000, max(300, base * (area / 4.0))))  # ~300..8000
    # Prefer picking moves that minimize giving the opponent a 3-sided box
    # quick filter: avoid moves that create a 3-sided box if there are safe moves
    safe_moves = []
    for mv in game_state["available_moves"]:
        r, c, o = mv
        risky = False
        if o == 'H':
            affected = [(r - 1, c), (r, c)]
        else:
            affected = [(r, c - 1), (r, c)]
        for br, bc in affected:
            if 0 <= br < height and 0 <= bc < width:
                if count_sides(br, bc, game_state) == 2:
                    risky = True
                    break
        if not risky:
            safe_moves.append(mv)
    if safe_moves:
        # sample root states replacing available_moves with safe subset for expansion
        # create a temporary copy and run MCTS biased to safe moves by replacing root.available_moves
        temp = copy.deepcopy(game_state)
        temp["available_moves"] = safe_moves
        mv = mcts_choose_move(temp, me, iterations)
        # If chosen mv was a placeholder (from safe list), return it, else fallback
        if mv in game_state["available_moves"]:
            return mv

    # fallback: run normal MCTS on full state
    return mcts_choose_move(game_state, me, iterations)
