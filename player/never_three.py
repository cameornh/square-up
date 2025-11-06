from __future__ import annotations
import random
from typing import Dict, List, Set, Tuple

Move = Tuple[int, int, str]
Coord = Tuple[int, int]

def count_sides(r: int, c: int, state: Dict) -> int:
    """
    Return the number of existing sides of the box at (r, c).
    Sides:
      top:    ('H', r,   c)
      bottom: ('H', r+1, c)
      left:   ('V', r,   c)
      right:  ('V', r,   c+1)
    """
    h: Set[Coord] = state["horizontal_lines"]
    v: Set[Coord] = state["vertical_lines"]
    cnt = 0
    if (r, c) in h: cnt += 1
    if (r + 1, c) in h: cnt += 1
    if (r, c) in v: cnt += 1
    if (r, c + 1) in v: cnt += 1
    return cnt

def adjacent_boxes(move: Move, state: Dict) -> List[Coord]:
    """
    Return boxes that share the moved edge.
    For ('H', r, c): (r, c) and (r-1, c) if in bounds.
    For ('V', r, c): (r, c) and (r, c-1) if in bounds.
    """
    r, c, o = move
    W, H = state["board_size"]
    boxes: List[Coord] = []
    if o == "H":
        if 0 <= r < H and 0 <= c < W:        # box below
            boxes.append((r, c))
        if 0 < r <= H and 0 <= c < W:        # box above
            boxes.append((r - 1, c))
    else:  # 'V'
        if 0 <= r < H and 0 <= c < W:        # box right
            boxes.append((r, c))
        if 0 <= r < H and 0 < c <= W:        # box left
            boxes.append((r, c - 1))
    return boxes

def boxes_captured_by(move: Move, state: Dict) -> int:
    """
    How many adjacent boxes would be completed by playing the move.
    A box is captured if it currently has exactly 3 sides.
    """
    return sum(1 for (br, bc) in adjacent_boxes(move, state)
                 if count_sides(br, bc, state) == 3)

def third_siders_after(move: Move, state: Dict) -> int:
    """
    How many adjacent boxes would become exactly 3-sided after playing the move.
    Completing a box (->4) is fine; only new 3-siders are counted.
    """
    r, c, o = move
    h: Set[Coord] = state["horizontal_lines"]
    v: Set[Coord] = state["vertical_lines"]
    # Illegal edge guard
    if (o == "H" and (r, c) in h) or (o == "V" and (r, c) in v):
        return 99

    cnt = 0
    for br, bc in adjacent_boxes(move, state):
        before = count_sides(br, bc, state)
        after = before + 1  # the placed edge touches each adjacent box
        if after == 3:
            cnt += 1
    return cnt

def is_safe(move: Move, state: Dict) -> bool:
    """True if the move does not create any 3-sided boxes."""
    return third_siders_after(move, state) == 0

def make_move(game_state: Dict) -> Move:
    """
    Capture-first never-three policy.

    1) If any move completes boxes, choose the move that completes the most boxes.
       Break ties randomly.
    2) Else choose uniformly among safe moves (no new 3-siders).
    3) Else choose among forced moves that minimize the number of new 3-siders.
    """
    moves: List[Move] = list(game_state["available_moves"])

    # 1) Greedy capture lesson: take points immediately.
    captures = [(boxes_captured_by(m, game_state), m) for m in moves]
    best_cap = max(captures, key=lambda x: x[0])[0]
    if best_cap > 0:
        cand = [m for c, m in captures if c == best_cap]
        return random.choice(cand)

    # 2) No captures available: prefer safety.
    safe_moves = [m for m in moves if is_safe(m, game_state)]
    if safe_moves:
        return random.choice(safe_moves)

    # 3) Forced: minimize damage (fewest new 3-siders).
    scored = [(third_siders_after(m, game_state), m) for m in moves]
    min_thirds = min(s for s, _ in scored)
    cand = [m for s, m in scored if s == min_thirds]
    return random.choice(cand)
