import numpy as np
import random

class Board:
    # Tối ưu: Định nghĩa các hướng là hằng số để dùng chung, tránh khởi tạo lại nhiều lần
    DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]  # Ngang, dọc, 2 chéo

    def __init__(self, size=15, win_condition=5):
        if size < 9:
            raise ValueError("Board size must be at least 9x9.")
        self.size = size
        self.win_condition = win_condition
        self.grid = np.zeros((size, size), dtype=int)  # 0: empty, 1: X, 2: O
        self.current_player = 1
        self.history = []  # Lưu (row, col)
        
        # Zobrist Hashing
        self.zobrist_table = [[[random.getrandbits(64) for _ in range(3)]
                               for _ in range(size)] for _ in range(size)]
        self.zobrist_side = random.getrandbits(64)
        self.current_hash = 0

    def is_valid(self, row, col) -> bool:
        """Kiểm tra nước đi có nằm trong biên và ô đó có trống không."""
        return 0 <= row < self.size and 0 <= col < self.size and self.grid[row, col] == 0

    def get_hash(self):
        return self.current_hash

    def make_move(self, row, col) -> bool:
        """Thực hiện nước đi, trả về False nếu không hợp lệ."""
        if not self.is_valid(row, col):
            return False
        
        self.current_hash ^= self.zobrist_table[row][col][0] # XOR out empty
        self.grid[row, col] = self.current_player
        self.current_hash ^= self.zobrist_table[row][col][self.current_player] # XOR in player
        self.current_hash ^= self.zobrist_side # Flip turn hash

        self.history.append((row, col))
        self.current_player = 3 - self.current_player  # Chuyển 1 -> 2 hoặc 2 -> 1
        return True

    def undo_move(self) -> bool:
        """Hoàn tác nước đi cuối cùng."""
        if not self.history:
            return False
        
        row, col = self.history.pop()
        self.current_hash ^= self.zobrist_table[row][col][self.grid[row, col]] # XOR out player
        self.grid[row, col] = 0
        self.current_hash ^= self.zobrist_table[row][col][0] # XOR in empty
        self.current_hash ^= self.zobrist_side # Flip turn hash

        self.current_player = 3 - self.current_player
        return True

    def check_win(self) -> int:
        """
        Trả về: 1 nếu X thắng, 2 nếu O thắng, -1 nếu hòa, 0 nếu chưa xong.
        """
        if not self.history:
            return 0
        
        last_r, last_c = self.history[-1]
        last_player = self.grid[last_r, last_c]
        
        if self._check_at(last_r, last_c):
            return last_player
        
        if len(self.history) == self.size * self.size:
            return -1  # Hòa
            
        return 0

    def _check_at(self, r, c) -> bool:
        """Kiểm tra xem tại ô (r, c) có tạo thành chuỗi thắng không."""
        player = self.grid[r, c]

        for dr, dc in self.DIRECTIONS:
            count = 1
            for direction in [1, -1]:
                nr, nc = r + dr * direction, c + dc * direction
                while 0 <= nr < self.size and 0 <= nc < self.size and self.grid[nr, nc] == player:
                    count += 1
                    # Early Exit: Thắng ngay lập tức khi đủ số quân liên tiếp
                    if count >= self.win_condition:
                        return True
                    nr += dr * direction
                    nc += dc * direction
        return False

    def get_legal_moves(self) -> list:
        """
        Lấy danh sách các nước đi hợp lệ.
        Tối ưu: Chỉ lấy các ô trống trong bán kính 2 quanh các quân đã đánh bằng numpy mask.
        """
        if not self.history:
            center = self.size // 2
            return [(center, center)]

        candidate_mask = np.zeros((self.size, self.size), dtype=bool)
        for r, c in self.history:
            r_lo, r_hi = max(0, r - 2), min(self.size, r + 3)
            c_lo, c_hi = max(0, c - 2), min(self.size, c + 3)
            candidate_mask[r_lo:r_hi, c_lo:c_hi] = True

        candidate_mask &= (self.grid == 0)
        rows, cols = np.where(candidate_mask)
        candidates = list(zip(rows.tolist(), cols.tolist()))
        opponent = 3 - self.current_player

        def move_priority(pos):
            r, c = pos
            # Thử nước thắng
            self.grid[r, c] = self.current_player
            if self._check_at(r, c):
                self.grid[r, c] = 0
                return 3
            # Thử nước chặn đối thủ
            self.grid[r, c] = opponent
            if self._check_at(r, c):
                self.grid[r, c] = 0
                return 2
            self.grid[r, c] = 0
            return 0

        return sorted(candidates, key=move_priority, reverse=True)

    def copy(self):
        """Tạo một bản sao sâu của bàn cờ."""
        new_board = Board(self.size, self.win_condition)
        new_board.grid = np.copy(self.grid)
        new_board.current_player = self.current_player
        new_board.history = self.history.copy()
        new_board.zobrist_table = self.zobrist_table
        new_board.zobrist_side = self.zobrist_side
        new_board.current_hash = self.current_hash
        return new_board

    def display(self):
        """In bàn cờ ra console để debug."""
        symbols = {0: '.', 1: 'X', 2: 'O'}
        print("  " + " ".join(str(i) for i in range(self.size)))
        for r in range(self.size):
            row_str = " ".join(symbols[self.grid[r, c]] for c in range(self.size))
            print(f"{r} {row_str}")
        print(f"Lượt kế tiếp: {symbols[self.current_player]}")
