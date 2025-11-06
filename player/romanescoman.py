import random
import copy
import math
from collections import defaultdict

class MCTSNode:
    def __init__(self, state, parent=None, move=None):
        self.state = state
        self.parent = parent
        self.move = move
        self.children = []
        self.visits = 0
        self.value = 0.0

    def is_fully_expanded(self):
        return len(self.children) == len(self.state["available_moves"])

    def best_child(self, c_param=1.4):
        """Select child with best UCT score."""
        choices = []
        for child in self.children:
            if child.visits == 0:
                uct = float('inf')
            else:
                uct = (child.value / child.visits) + c_param * math.sqrt(
                    math.log(self.visits + 1) / (child.visits)
                )
            choices.append((uct, child))
        return max(choices, key=lambda x: x[0])[1]


def apply_move_to_state(state, move, player_id):
    """
    Returns a deep-copied next state after applying `move` by `player_id`.
    """
    next_state = copy.deepcopy(state)
    r, c, orientation = move
    scored_box = False

    if orientation == "H":
        next_state["horizontal_lines"].add((r, c))
    else:
        next_state["vertical_lines"].add((r, c))

    next_state["available_moves"].remove(move)

    # Check boxes formed by this move
    potential_boxes = []
    if orientation == "H":
        potential_boxes = [(r - 1, c), (r, c)]
    else:  # 'V'
        potential_boxes = [(r, c - 1), (r, c)]

    for br, bc in potential_boxes:
        if 0 <= br < next_state["board_size"][1] and 0 <= bc < next_state["board_size"][0]:
            top = (br, bc) in next_state["horizontal_lines"]
            bottom = (br + 1, bc) in next_state["horizontal_lines"]
            left = (br, bc) in next_state["vertical_lines"]
            right = (br, bc + 1) in next_state["vertical_lines"]
            if top and bottom and left and right and (br, bc) not in next_state["box_owners"]:
                next_state["box_owners"][(br, bc)] = player_id
                scored_box = True

    # If no box was completed, switch turns
    if not scored_box:
        next_state["your_player_id"] = 3 - player_id

    return next_state


def rollout(state, starting_player):
    """
    Simulate a random game until the end.
    """
    current_state = copy.deepcopy(state)
    current_player = starting_player

    while current_state["available_moves"]:
        move = random.choice(current_state["available_moves"])
        current_state = apply_move_to_state(current_state, move, current_player)

        # If the player didn’t score a box, switch
        if current_state["your_player_id"] != current_player:
            current_player = 3 - current_player

    # Count boxes
    player1_boxes = sum(1 for v in current_state["box_owners"].values() if v == 1)
    player2_boxes = sum(1 for v in current_state["box_owners"].values() if v == 2)

    if player1_boxes > player2_boxes:
        return 1
    elif player2_boxes > player1_boxes:
        return 2
    else:
        return 0


def backpropagate(node, result, player_id):
    """
    Backpropagate rollout results up the tree.
    """
    while node is not None:
        node.visits += 1
        if result == player_id:
            node.value += 1
        elif result == 0:
            node.value += 0.5  # draw
        node = node.parent


def expand(node, player_id):
    """
    Expand one unexplored move from this node.
    """
    tried_moves = {child.move for child in node.children}
    untried_moves = [m for m in node.state["available_moves"] if m not in tried_moves]
    if not untried_moves:
        return node

    move = random.choice(untried_moves)
    new_state = apply_move_to_state(node.state, move, player_id)
    child_node = MCTSNode(new_state, parent=node, move=move)
    node.children.append(child_node)
    return child_node


def make_move(game_state):
    """
    Monte Carlo Tree Search AI for Dots and Boxes.
    Selects the move with the best simulated win rate.
    """
    root = MCTSNode(copy.deepcopy(game_state))
    player_id = game_state["your_player_id"]
    iterations = 1000  # You can tune this

    for _ in range(iterations):
        node = root
        state = copy.deepcopy(game_state)

        # Selection
        while node.children and node.is_fully_expanded():
            node = node.best_child()

        # Expansion
        if node.state["available_moves"]:
            node = expand(node, player_id)

        # Simulation
        result = rollout(node.state, node.state["your_player_id"])

        # Backpropagation
        backpropagate(node, result, player_id)

    # Choose best child (highest average reward)
    best_move = max(
        root.children,
        key=lambda c: c.value / (c.visits + 1e-6)
    ).move

    return best_move
