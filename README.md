# Dots and Boxes AI Tournament

The goal is to create a Python script that plays the game of Dots and Boxes. You will submit a single Python file, and it will be pitted against other submissions in a tournament

## How to Participate

1.  Create a Python file. You can name it `your_name.py` or give it a cool name if you want
2.  In this file, you must define a single function with the exact signature: `def make_move(game_state):`
3.  Write your logic inside this function to decide which line to draw
4.  Your function must return a single move as a tuple: `(row, col, orientation)`
5.  Email me your file at crhalaby652@gmail.com (you can do this at any point in the future and I'll add it to the repo)

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
```

## Help
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

## Tournament Rules
The players will compete against each other player for 20 rounds on a 2x2 board. The total number of match wins will be added to the leaderboard.

## Leaderboard (subject to change)
```
Rank  | Player                | Author               | Wins  | Losses | Draws
---------------------------------------------------------------------------------
1     | charmer.py            | Chaz                 | 7     | 0      | 1    
2     | bots_and_doxes.py     | Dom                  | 7     | 1      | 0    
3     | onionman.py           | Alex                 | 6     | 1      | 1    
4     | never_three.py        | Chaz                 | 5     | 3      | 0    
5     | dbtx.py               | Nikhil               | 3     | 5      | 0    
6     | tomatoman.py          | Alex                 | 3     | 4      | 1    
7     | greedy.py             | Cameron              | 2     | 5      | 1    
8     | romanescoman.py       | Alex                 | 1     | 7      | 0    
9     | random.py             | Cameron              | 0     | 8      | 0 
```

### Note
I was thinking about writing a file to visualize the tournament results (something more visually appealing than an ASCII table). If this is something that interests you, feel free to submit a pull request
