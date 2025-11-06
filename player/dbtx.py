import copy

def is_legal_move(game_state, r, c, orientation):
    """Checks if a move is valid and the line is not already taken."""
    width, height = game_state["board_size"]
    horizontal_lines = game_state["horizontal_lines"]
    vertical_lines = game_state["vertical_lines"]
    
    if orientation == 'H':
        return 0 <= r <= height and 0 <= c < width and (r, c) not in horizontal_lines
    elif orientation == 'V':
        return 0 <= r < height and 0 <= c <= width and (r, c) not in vertical_lines
    return False

def make_move(game_state):
    """
    Strategic Dots and Boxes AI implementing the PSPACE-complete paper's strategy:
    - Avoid creating long chains (3+ boxes) in early/mid game
    - Gain control of loony endgame
    - Use double-dealing moves when in control
    - Maximize disjoint cycles when not in control
    """
    board_size = game_state["board_size"]
    width, height = board_size
    available_moves = game_state["available_moves"]
    my_player_id = game_state["your_player_id"]
    
    if not available_moves:
        return None
    
    # Analyze current game phase
    total_edges = width * (height + 1) + height * (width + 1)
    edges_played = len(game_state["horizontal_lines"]) + len(game_state["vertical_lines"])
    total_boxes = width * height
    boxes_claimed = len(game_state["box_owners"])
    
    # Check if we're in loony endgame (all remaining boxes are in chains/cycles)
    is_loony_endgame = check_loony_endgame(game_state)
    
    if is_loony_endgame:
        # Endgame strategy: make double-dealing moves or open chains strategically
        return select_endgame_move(game_state, available_moves, my_player_id)
    else:
        # Pre-endgame: avoid creating long chains, complete safe boxes
        return select_safe_move(game_state, available_moves, my_player_id)


def check_loony_endgame(game_state):
    """Check if all unclaimed boxes are part of long chains (3+) or cycles."""
    width, height = game_state["board_size"]
    
    # Count unclaimed boxes not in chains/cycles
    for r in range(height):
        for c in range(width):
            if (r, c) not in game_state["box_owners"]:
                degree = count_box_degree(game_state, r, c)
                # If there's a box with degree 1 (capturable) or degree 3/4, not loony endgame
                if degree == 1 or degree >= 3:
                    return False
    
    # All remaining boxes are degree 2 (part of chains)
    # Check if any chains are short (1-2 boxes)
    chains = find_all_chains(game_state)
    for chain in chains:
        if len(chain) <= 2:
            return False
    
    return len(chains) > 0


def select_safe_move(game_state, available_moves, my_player_id):
    """
    Pre-endgame strategy:
    1. Complete boxes if safe (doesn't give opponent long chain)
    2. Otherwise, make moves that don't create long chains
    3. Fill in "safe" edges that don't complete boxes or create vulnerabilities
    """
    move_evaluations = []
    
    for move in available_moves:
        score = 0
        boxes_completed = count_boxes_completed(game_state, move)
        
        # Simulate the move
        sim_state = simulate_move(game_state, move, my_player_id)
        
        if boxes_completed > 0:
            # Completing boxes is great!
            score += boxes_completed * 10000
            
            # But check what we leave for opponent
            opponent_capturable = count_capturable_boxes(sim_state)
            opponent_long_chains = count_long_chains(sim_state)
            
            # If we complete boxes but create a long chain for opponent, penalize
            if opponent_long_chains > 0:
                score -= opponent_long_chains * 5000
            
            # Check if we get to continue safely
            our_capturable = count_capturable_boxes(sim_state)
            if our_capturable > 0:
                score += our_capturable * 1000
                
        else:
            # Not completing boxes - evaluate safety
            
            # Check what this creates for opponent
            opponent_capturable = count_capturable_boxes(sim_state)
            long_chains_created = count_long_chains(sim_state)
            
            # Strongly avoid creating long chains (paper's key insight)
            if long_chains_created > 0:
                score -= long_chains_created * 8000
            
            # Avoid creating capturable boxes for opponent
            if opponent_capturable > 0:
                score -= opponent_capturable * 2000
            
            # Prefer moves that don't change board structure much
            score += 100
            
            # Slightly prefer moves that advance toward endgame symmetrically
            sim_chains = find_all_chains(sim_state)
            if len(sim_chains) > 0:
                # Creating short chains is ok, long chains are bad
                avg_chain_length = sum(len(c) for c in sim_chains) / len(sim_chains)
                if avg_chain_length <= 2:
                    score += 50
        
        move_evaluations.append((score, move))
    
    # Sort by score (highest first)
    move_evaluations.sort(reverse=True, key=lambda x: x[0])
    
    return move_evaluations[0][1]


def select_endgame_move(game_state, available_moves, my_player_id):
    """
    Loony endgame strategy from the paper:
    - If in control: make double-dealing moves (leave 2 boxes in chains, 4 in cycles)
    - If not in control: open chains/cycles to maximize disjoint cycles
    """
    move_evaluations = []
    
    for move in available_moves:
        score = 0
        boxes_completed = count_boxes_completed(game_state, move)
        sim_state = simulate_move(game_state, move, my_player_id)
        
        if boxes_completed > 0:
            # We're claiming boxes - check for double-dealing opportunity
            score += boxes_completed * 1000
            
            # Check if this is in a chain or cycle we're claiming
            chain_info = analyze_chain_for_move(game_state, move)
            
            if chain_info:
                chain_length, is_cycle_flag = chain_info
                
                # Can we make a double-dealing move?
                if is_cycle_flag and chain_length >= 8:
                    # In a long cycle, we can take all but 4 boxes
                    score += 5000  # Double-dealing in cycle is optimal
                elif not is_cycle_flag and chain_length >= 4:
                    # In a long chain, we can take all but 2 boxes
                    score += 4000  # Double-dealing in chain
        else:
            # Opening a chain/cycle
            chain_info = analyze_chain_for_move(game_state, move)
            
            if chain_info:
                chain_length, is_cycle_flag = chain_info
                
                # Opening short chains is better than long ones
                if chain_length <= 3:
                    score += 1000
                else:
                    # Opening long chains gives opponent advantage
                    score -= chain_length * 100
                
                # Cycles are worth more (4 boxes from double-dealing vs 2)
                if is_cycle_flag:
                    score += 500
        
        move_evaluations.append((score, move))
    
    move_evaluations.sort(reverse=True, key=lambda x: x[0])
    return move_evaluations[0][1]


def analyze_chain_for_move(game_state, move):
    """Analyze if a move is part of a chain and return chain info."""
    r, c, orientation = move
    width, height = game_state["board_size"]
    
    # Find affected boxes
    affected_boxes = []
    
    if orientation == 'H':
        if r < height:
            affected_boxes.append((r, c))
        if r > 0:
            affected_boxes.append((r - 1, c))
    else:  # 'V'
        if c < width:
            affected_boxes.append((r, c))
        if c > 0:
            affected_boxes.append((r, c - 1))
    
    # Check if any affected box is part of a chain
    chains = find_all_chains(game_state)
    
    for chain in chains:
        for box in affected_boxes:
            if box in chain:
                is_cycle_flag = is_cycle(game_state, chain)
                return (len(chain), is_cycle_flag)
    
    return None


def count_capturable_boxes(game_state):
    """Count boxes with only 1 missing edge (immediately capturable)."""
    width, height = game_state["board_size"]
    count = 0
    
    for r in range(height):
        for c in range(width):
            if (r, c) not in game_state["box_owners"]:
                if count_box_degree(game_state, r, c) == 1:
                    count += 1
    
    return count


def count_long_chains(game_state):
    """Count chains of length 3+ (exploitable by opponent)."""
    chains = find_all_chains(game_state)
    return sum(1 for chain in chains if len(chain) >= 3)


def find_all_chains(game_state):
    """Find all chains and cycles of degree-2 boxes."""
    width, height = game_state["board_size"]
    visited = set()
    chains = []
    
    for r in range(height):
        for c in range(width):
            if (r, c) not in visited and (r, c) not in game_state["box_owners"]:
                degree = count_box_degree(game_state, r, c)
                if degree == 2:
                    chain = trace_chain(game_state, r, c, visited)
                    if len(chain) > 0:
                        chains.append(chain)
    
    return chains


def trace_chain(game_state, start_r, start_c, visited):
    """Trace a chain of degree-2 boxes."""
    chain = []
    current = (start_r, start_c)
    
    while current and current not in visited:
        r, c = current
        if count_box_degree(game_state, r, c) != 2:
            break
        
        visited.add(current)
        chain.append(current)
        
        current = find_next_in_chain(game_state, r, c, visited)
    
    return chain


def find_next_in_chain(game_state, r, c, visited):
    """Find the next box in a chain of degree-2 boxes."""
    width, height = game_state["board_size"]
    neighbors = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
    
    for nr, nc in neighbors:
        if (0 <= nr < height and 0 <= nc < width and
            (nr, nc) not in visited and
            (nr, nc) not in game_state["box_owners"] and
            count_box_degree(game_state, nr, nc) == 2):
            return (nr, nc)
    
    return None


def is_cycle(game_state, chain):
    """Check if a chain forms a cycle."""
    if len(chain) < 4:
        return False
    
    first = chain[0]
    last = chain[-1]
    
    # Check if first and last boxes are adjacent
    return abs(first[0] - last[0]) + abs(first[1] - last[1]) == 1


def count_box_degree(game_state, r, c):
    """Count missing edges for a box (0 = complete, 4 = empty)."""
    width, height = game_state["board_size"]
    
    if r < 0 or r >= height or c < 0 or c >= width:
        return 4
    
    if (r, c) in game_state["box_owners"]:
        return 0
    
    h_lines = game_state["horizontal_lines"]
    v_lines = game_state["vertical_lines"]
    
    missing = 0
    if (r, c) not in h_lines:
        missing += 1
    if (r + 1, c) not in h_lines:
        missing += 1
    if (r, c) not in v_lines:
        missing += 1
    if (r, c + 1) not in v_lines:
        missing += 1
    
    return missing


def count_boxes_completed(game_state, move):
    """Count how many boxes a move would complete."""
    r, c, orientation = move
    width, height = game_state["board_size"]
    h_lines = game_state["horizontal_lines"]
    v_lines = game_state["vertical_lines"]
    
    completed = 0
    
    if orientation == 'H':
        # Check box below
        if r < height and (r, c) not in game_state["box_owners"]:
            if ((r + 1, c) in h_lines and 
                (r, c) in v_lines and 
                (r, c + 1) in v_lines):
                completed += 1
        # Check box above
        if r > 0 and (r - 1, c) not in game_state["box_owners"]:
            if ((r - 1, c) in h_lines and 
                (r - 1, c) in v_lines and 
                (r - 1, c + 1) in v_lines):
                completed += 1
    else:  # 'V'
        # Check box to the right
        if c < width and (r, c) not in game_state["box_owners"]:
            if ((r, c) in h_lines and 
                (r + 1, c) in h_lines and 
                (r, c + 1) in v_lines):
                completed += 1
        # Check box to the left
        if c > 0 and (r, c - 1) not in game_state["box_owners"]:
            if ((r, c - 1) in h_lines and 
                (r + 1, c - 1) in h_lines and 
                (r, c - 1) in v_lines):
                completed += 1
    
    return completed


def simulate_move(game_state, move, my_player_id):
    """Create a new game state with the move applied."""
    new_state = {
        "board_size": game_state["board_size"],
        "horizontal_lines": copy.deepcopy(game_state["horizontal_lines"]),
        "vertical_lines": copy.deepcopy(game_state["vertical_lines"]),
        "box_owners": copy.deepcopy(game_state["box_owners"]),
        "your_player_id": my_player_id
    }
    
    r, c, orientation = move
    if orientation == 'H':
        new_state["horizontal_lines"].add((r, c))
    else:
        new_state["vertical_lines"].add((r, c))
    
    return new_state