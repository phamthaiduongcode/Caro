"""
board.py - Logic game cờ Caro
Bàn cờ 10x10, thắng 4 quân liên tiếp
"""

EMPTY  = '.'
PLAYER = 'X'
AI     = 'O'
SIZE   = 10
WIN    = 4


class Board:
    def __init__(self):
        self.grid = [[EMPTY] * SIZE for _ in range(SIZE)]
        self.move_history = []  # Stack lưu (row, col, player)
        self.count = 0          # Đếm số quân trên bàn

    # ── last_move ────────────────────────────────────────────
    @property
    def last_move(self):
        return self.move_history[-1] if self.move_history else None

    # ── Hiển thị ─────────────────────────────────────────────
    def display(self):
        print("   " + " ".join(f"{c:2}" for c in range(SIZE)))
        for r in range(SIZE):
            print(f"{r:2} " + "  ".join(self.grid[r]))
        print()

    # ── Kiểm tra nước đi hợp lệ ──────────────────────────────
    def is_valid_move(self, row, col):
        return (0 <= row < SIZE and
                0 <= col < SIZE and
                self.grid[row][col] == EMPTY)

    # ── Đặt / xóa quân ───────────────────────────────────────
    def make_move(self, row, col, player):
        if self.is_valid_move(row, col):
            self.grid[row][col] = player
            self.move_history.append((row, col, player))
            self.count += 1
            return True
        return False

    def undo_move(self):
        """Xóa quân cuối — dùng cho Minimax."""
        if self.move_history:
            r, c, _ = self.move_history.pop()
            self.grid[r][c] = EMPTY
            self.count -= 1

    # ── Kiểm tra thắng tại ô vừa đánh ───────────────────────
    def check_win_at(self, row, col, player):
        """
        Chỉ đếm quân liên tiếp qua ô (row, col) theo 4 hướng.
        Nhanh hơn scan toàn bộ bàn cờ.
        """
        directions = [
            (0, 1),   # ngang
            (1, 0),   # dọc
            (1, 1),   # chéo chính
            (1, -1),  # chéo phụ
        ]
        for dr, dc in directions:
            count = 1
            # Đếm về phía thuận
            nr, nc = row + dr, col + dc
            while 0 <= nr < SIZE and 0 <= nc < SIZE and self.grid[nr][nc] == player:
                count += 1
                nr += dr
                nc += dc
            # Đếm về phía ngược
            nr, nc = row - dr, col - dc
            while 0 <= nr < SIZE and 0 <= nc < SIZE and self.grid[nr][nc] == player:
                count += 1
                nr -= dr
                nc -= dc
            if count >= WIN:
                return True
        return False

    def check_win(self, player):
        """
        Scan toàn bộ bàn cờ — dùng khi load trạng thái test
        mà không có move_history.
        """
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for r in range(SIZE):
            for c in range(SIZE):
                if self.grid[r][c] != player:
                    continue
                for dr, dc in directions:
                    count = 1
                    nr, nc = r + dr, c + dc
                    while 0 <= nr < SIZE and 0 <= nc < SIZE and self.grid[nr][nc] == player:
                        count += 1
                        if count >= WIN:
                            return True
                        nr += dr
                        nc += dc
        return False

    # ── Trạng thái kết thúc ───────────────────────────────────
    def is_terminal(self):
        """
        Trả về:
          'X'    → người thắng
          'O'    → máy thắng
          'draw' → hòa
          None   → chưa kết thúc
        """
        if self.last_move:
            r, c, player = self.last_move
            if self.check_win_at(r, c, player):
                return player
        else:
            # Load state từ file test → không có move_history
            if self.check_win(PLAYER): return PLAYER
            if self.check_win(AI):     return AI

        if self.count == SIZE * SIZE:  # O(1) nhờ biến count
            return 'draw'
        return None

    # ── Sinh nước đi ──────────────────────────────────────────
    def get_valid_moves(self):
        """Tất cả ô trống — dùng khi cần xét toàn bộ."""
        return [(r, c)
                for r in range(SIZE)
                for c in range(SIZE)
                if self.grid[r][c] == EMPTY]

    def get_candidate_moves(self):
        """
        Chỉ xét ô trống gần quân đã đánh (radius=2).
        Duyệt qua move_history thay vì scan toàn bàn.
        """
        if self.count == 0:
            return [(SIZE // 2, SIZE // 2)]

        radius = 2
        candidates = set()
        for r, c, _ in self.move_history:
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    nr, nc = r + dr, c + dc
                    if (0 <= nr < SIZE and
                            0 <= nc < SIZE and
                            self.grid[nr][nc] == EMPTY):
                        candidates.add((nr, nc))
        return list(candidates)

    # ── Sao chép bàn cờ ──────────────────────────────────────
    def copy(self):
        """Sao chép bàn cờ — dùng cho benchmark/test."""
        new_board = Board()
        new_board.grid = [row[:] for row in self.grid]
        new_board.move_history = self.move_history[:]
        new_board.count = self.count
        return new_board