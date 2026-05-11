import numpy as np

class Board:
    def __init__(self, size=15):
        self.size = size
        self.grid = np.zeros((size, size), dtype=int)

    def is_valid_move(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size and self.grid[x][y] == 0

    def make_move(self, x, y, player):
        if self.is_valid_move(x, y):
            self.grid[x][y] = player
            return True
        return False