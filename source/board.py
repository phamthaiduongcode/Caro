"""
board.py - Logic game cờ Caro
Bàn cờ 9x9, thắng 4 quân liên tiếp
"""

EMPTY  = '.'
PLAYER = 'X'
AI     = 'O'
SIZE   = 9
WIN    = 4


class Board:
    def __init__(self):
        # Bàn cờ 9x9, toàn ô trống
        self.grid = [[EMPTY] * SIZE for _ in range(SIZE)]

    #  Hiển thị 
    def display(self):
        print("   " + " ".join(str(c) for c in range(SIZE)))
        for r in range(SIZE):
            print(f"{r:2} " + " ".join(self.grid[r]))
        print()

    #  Kiểm tra nước đi hợp lệ 
    def is_valid_move(self, row, col):
        return (0 <= row < SIZE and
                0 <= col < SIZE and
                self.grid[row][col] == EMPTY)

    #  Đặt / xóa quân 
    def make_move(self, row, col, player):
        if self.is_valid_move(row, col):
            self.grid[row][col] = player
            return True
        return False

    def undo_move(self, row, col):
        """Xóa quân tại ô — dùng cho Minimax."""
        self.grid[row][col] = EMPTY

    #Kiểm tra thắng
    def check_win(self, player):
        """
        Kiểm tra player có 4 quân liên tiếp không.
        4 hướng: ngang, dọc, chéo chính, chéo phụ.
        """
        directions = [
            (0, 1),   # ngang
            (1, 0),   # dọc
            (1, 1),   # chéo chính
            (1, -1),  # chéo phụ
        ]
        for r in range(SIZE):
            for c in range(SIZE):
                if self.grid[r][c] != player:
                    continue
                for dr, dc in directions:
                    count = 1
                    nr, nc = r + dr, c + dc
                    while (0 <= nr < SIZE and
                           0 <= nc < SIZE and
                           self.grid[nr][nc] == player):
                        count += 1
                        if count == WIN:
                            return True
                        nr += dr
                        nc += dc
        return False

    #Kiểm tra hòa
    def is_full(self):
        return all(self.grid[r][c] != EMPTY
                   for r in range(SIZE)
                   for c in range(SIZE))

    #Trạng thái kết thúc 
    def is_terminal(self):
        """
        Trả về:
          'X'    → người thắng
          'O'    → máy thắng
          'draw' → hòa
          None   → chưa kết thúc
        """
        if self.check_win(PLAYER): return PLAYER
        if self.check_win(AI):     return AI
        if self.is_full():         return 'draw'
        return None

    # Sinh nước đi 
    def get_valid_moves(self):
        """Tất cả ô trống trên bàn cờ."""
        return [(r, c)
                for r in range(SIZE)
                for c in range(SIZE)
                if self.grid[r][c] == EMPTY]

    def get_candidate_moves(self, radius=2):
        """
        Chỉ xét ô trống gần quân đã đánh (trong vòng radius ô).
        Giúp Minimax không phải xét toàn bộ bàn cờ.
        """
        candidates = set()
        has_piece = False

        for r in range(SIZE):
            for c in range(SIZE):
                if self.grid[r][c] == EMPTY:
                    continue
                has_piece = True
                for dr in range(-radius, radius + 1):
                    for dc in range(-radius, radius + 1):
                        nr, nc = r + dr, c + dc
                        if (0 <= nr < SIZE and
                                0 <= nc < SIZE and
                                self.grid[nr][nc] == EMPTY):
                            candidates.add((nr, nc))

        # Bàn cờ trống 
        if not has_piece:
            return [(SIZE // 2, SIZE // 2)]

        return list(candidates)