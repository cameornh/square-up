import copy

class DotsAndBoxesGame:
    def __init__(self, width=3, height=3):
        self.width = width
        self.height = height
        self.board_size = (width, height)
        self.horizontal_lines = set()
        self.vertical_lines = set()
        self.box_owners = {}  # (row, col): player_id
        self.scores = {1: 0, 2: 0}
        self.current_player = 1
        self.game_over = False

    def get_state(self):
        """Returns a copy of the game state for players."""
        return {
            "board_size": self.board_size,
            "horizontal_lines": copy.deepcopy(self.horizontal_lines),
            "vertical_lines": copy.deepcopy(self.vertical_lines),
            "box_owners": copy.deepcopy(self.box_owners),
            "your_player_id": self.current_player
        }

    def is_valid_move(self, r, c, orientation):
        """Checks if a move is valid and the line is not already taken."""
        if orientation == 'H':
            return 0 <= r <= self.height and 0 <= c < self.width and (r, c) not in self.horizontal_lines
        elif orientation == 'V':
            return 0 <= r < self.height and 0 <= c <= self.width and (r, c) not in self.vertical_lines
        return False

    def apply_move(self, r, c, orientation):
        """Applies a move, checks for completed boxes, and updates the score."""
        if not self.is_valid_move(r, c, orientation):
            return False, 0  # Invalid move

        if orientation == 'H':
            self.horizontal_lines.add((r, c))
        else: # 'V'
            self.vertical_lines.add((r, c))

        boxes_completed = self._check_for_new_boxes(r, c, orientation)
        
        if boxes_completed > 0:
            self.scores[self.current_player] += boxes_completed
            # Player gets another turn
        else:
            # Switch player
            self.current_player = 3 - self.current_player

        if len(self.horizontal_lines) + len(self.vertical_lines) == self.width * (self.height + 1) + self.height * (self.width + 1):
            self.game_over = True
        
        return True, boxes_completed

    def _check_for_new_boxes(self, r, c, orientation):
        completed_count = 0
        if orientation == 'H':
            # Check box below the line
            if r < self.height and self._is_box_complete(r, c):
                self.box_owners[(r, c)] = self.current_player
                completed_count += 1
            # Check box above the line
            if r > 0 and self._is_box_complete(r - 1, c):
                self.box_owners[(r - 1, c)] = self.current_player
                completed_count += 1
        else: # 'V'
            # Check box to the right of the line
            if c < self.width and self._is_box_complete(r, c):
                self.box_owners[(r, c)] = self.current_player
                completed_count += 1
            # Check box to the left of the line
            if c > 0 and self._is_box_complete(r, c - 1):
                self.box_owners[(r, c - 1)] = self.current_player
                completed_count += 1
        return completed_count

    def _is_box_complete(self, r, c):
        """Check if the box at (r,c) is complete."""
        top = (r, c) in self.horizontal_lines
        bottom = (r + 1, c) in self.horizontal_lines
        left = (r, c) in self.vertical_lines
        right = (r, c + 1) in self.vertical_lines
        return top and bottom and left and right

    def get_winner(self):
        if not self.game_over:
            return None
        if self.scores[1] > self.scores[2]:
            return 1
        elif self.scores[2] > self.scores[1]:
            return 2
        else:
            return 0  # Draw

    def get_available_moves(self):
        moves = []
        for r in range(self.height + 1):
            for c in range(self.width):
                if (r, c) not in self.horizontal_lines:
                    moves.append((r, c, 'H'))
        for r in range(self.height):
            for c in range(self.width + 1):
                if (r, c) not in self.vertical_lines:
                    moves.append((r, c, 'V'))
        return moves