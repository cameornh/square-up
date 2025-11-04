# Dots and Boxes AI Tournament

The goal is to create a Python script that plays the game of Dots and Boxes. You will submit a single Python file, and it will be pitted against other submissions in a tournament

## How to Participate

1.  Create a Python file. You can name it `your_name.py` or give it a cool name if you want
2.  In this file, you must define a single function with the exact signature: `def make_move(game_state):`
3.  Write your logic inside this function to decide which line to draw
4.  Your function must return a single move as a tuple: `(row, col, orientation)`

## The `make_move` function

Your function will receive one argument, `game_state`, which is a Python dictionary containing all the information you need about the current board state

### `game_state` Dictionary Structure:
```python
{
  "board_size": (width, height),      # e.g., (4, 4) for a 4x4 grid of boxes
  "horizontal_lines": {(r, c), ...}, # A set of tuples for lines already drawn
  "vertical_lines": {(r, c), ...},   # A set of tuples for lines already drawn
  "box_owners": {(r, c): player_id},  # A dict mapping box coords to the player who won it
  "your_player_id": 1 or 2,          # Your assigned player number for this game
  "available_moves": [(r,c,o), ...]  # A list of all valid moves you can make
}

To play two players against each other, move into the 'player' directory and run this command: 
`python ../game_match.py <player1_file.py> <player2_file.py> -r ROUNDS -s SIZE`

The '--rounds' flag ('-r') is optional and defaults to 20. Whatever you change it to should be an even number
The '--size' flag ('-s') is also optional and defaults to 2x2
e.g. if you want to run a match against greedy.py and random.py for 20 rounds on a 2x2 board:
`python ../game_match.py greedy.py random.py`

If you want to run a match against greedy.py and greedy.py for 40 rounds on a 13x13 board:
`python ../game_match.py greedy.py greedy.py -r 40 -s 13x13`

If you're confused about the arguments of game_match.py, you can run it with a '--help' flag ('-h'). Assuming you're in the 'player' directory:
`python ../game_match.py -h`

If you get an error that looks like this:
`python: can't open file '...game_match.py': [Errno 2] No such file or directory`
make sure you're in the 'player' directory first:
`cd player`

I was thinking about writing a file to automatically run a tournament of all the players. If this is something that interests you, feel free to submit a pull request