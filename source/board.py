import random

class Board:
    # Tối ưu: Định nghĩa các hướng là hằng số để dùng chung, tránh khởi tạo lại nhiều lần
    DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]  # Ngang, dọc, 2 chéo

    def __init__(self, size=9, win_condition=4):
        if size < 9:
            raise ValueError("Board size must be at least 9x9.")
        self.size = size
        self.win_condition = win_condition
        self.grid = [[0 for _ in range(size)] for _ in range(size)]
        self.current_player = 1
        self.history = []  # Lưu (row, col)
        self.current_score = 0  # Lưu điểm số hiện tại của bàn cờ (từ góc nhìn của Player 2)

        # Zobrist Hashing
        self.zobrist_table = [[[random.getrandbits(64) for _ in range(3)]
                               for _ in range(size)] for _ in range(size)]
        self.zobrist_side = random.getrandbits(64)
        self.current_hash = 0
        for r in range(size):
            for c in range(size):
                self.current_hash ^= self.zobrist_table[r][c][0]

    def is_valid(self, row, col) -> bool:
        """Kiểm tra nước đi có nằm trong biên và ô đó có trống không."""
        return 0 <= row < self.size and 0 <= col < self.size and self.grid[row][col] == 0

    def get_hash(self):
        return self.current_hash

    def make_move(self, row, col) -> bool:
        if not self.is_valid(row, col):
            return False
        
        self.current_hash ^= self.zobrist_table[row][col][0]
        self.grid[row][col] = self.current_player
        self.current_hash ^= self.zobrist_table[row][col][self.current_player]
        self.current_hash ^= self.zobrist_side

        self.history.append((row, col))
        self.current_player = 3 - self.current_player  # Chuyển 1 -> 2 hoặc 2 -> 1
        return True

    def undo_move(self) -> bool:
        if not self.history:
            return False
        
        row, col = self.history.pop()
        self.current_hash ^= self.zobrist_table[row][col][self.grid[row][col]]
        self.grid[row][col] = 0
        self.current_hash ^= self.zobrist_table[row][col][0]
        self.current_hash ^= self.zobrist_side

        self.current_player = 3 - self.current_player
        return True

    def check_win(self) -> int:
        """
        Trả về: 1 nếu X thắng, 2 nếu O thắng, -1 nếu hòa, 0 nếu chưa xong.
        """
        if not self.history:
            return 0
        
        last_r, last_c = self.history[-1]
        last_player = self.grid[last_r][last_c]
        
        if self._check_at(last_r, last_c):
            return last_player
        
        if len(self.history) == self.size * self.size:
            return -1  # Hòa
            
        return 0

    def _check_at(self, r, c) -> bool:
        """Kiểm tra xem tại ô (r, c) có tạo thành chuỗi thắng không."""
        player = self.grid[r][c]

        for dr, dc in self.DIRECTIONS:
            count = 1
            for direction in [1, -1]:
                nr, nc = r + dr * direction, c + dc * direction
                while 0 <= nr < self.size and 0 <= nc < self.size and self.grid[nr][nc] == player:
                    count += 1
                    # Early Exit: Thắng ngay lập tức khi đủ số quân liên tiếp
                    if count >= self.win_condition:
                        return True
                    nr += dr * direction
                    nc += dc * direction
        return False

    def fast_check_win(self, r, c, player) -> bool:
        """Kiểm tra xem nếu 'player' đánh vào (r, c) thì có thắng luôn không.
        Tuyệt đối không làm thay đổi bàn cờ (Tốc độ ánh sáng)."""
        for dr, dc in self.DIRECTIONS:
            count = 1
            for direction in [1, -1]:
                nr, nc = r + dr * direction, c + dc * direction
                # Đếm các quân liên tiếp cùng màu
                while 0 <= nr < self.size and 0 <= nc < self.size and self.grid[nr][nc] == player:
                    count += 1
                    nr += dr * direction
                    nc += dc * direction
            # Đủ win_condition (thường là 4 hoặc 5) là thắng
            if count >= self.win_condition:
                return True
        return False

    def get_legal_moves(self) -> list:
        # Nếu bàn cờ trống, đánh vào giữa
        if not self.history:
            return [(self.size // 2, self.size // 2)]

        candidates = set()
        
        # [MỚI] Dò tìm ứng viên xung quanh TẤT CẢ các quân cờ đang có trên bàn
        for r, c in self.history:
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    # Nếu là ô trống thì thêm vào tập ứng viên
                    if 0 <= nr < self.size and 0 <= nc < self.size and self.grid[nr][nc] == 0:
                        candidates.add((nr, nc))

        opponent = 3 - self.current_player
        ctr = self.size // 2

        # Hàm heuristic nhẹ để sắp xếp nước đi
        def move_priority(pos):
            r, c = pos
            # 1. Thắng ngay lập tức
            if self.fast_check_win(r, c, self.current_player):
                return 100000 
            # 2. Chặn đối thủ thắng ngay
            if self.fast_check_win(r, c, opponent):
                return 90000  
            # 3. Ưu tiên các ô gần tâm
            return (self.size - abs(r - ctr) - abs(c - ctr))

        # Ép kiểu set về list, sau đó sắp xếp theo priority
        return sorted(list(candidates), key=move_priority, reverse=True)

    def evaluate_position(self, r, c, player):
        """
        Đánh giá điểm số thay đổi tại DUY NHẤT vị trí (r, c) cho 'player'.
        Chỉ duyệt 4 hướng đi qua ô này.
        Điểm số được tính từ góc nhìn của 'player' (tức là điểm của 'player' là dương, điểm của đối thủ là âm).
        """
        score = 0
        opp = 3 - player
        
        for dr, dc in self.DIRECTIONS:
            # Lùi về tối đa (win_condition - 1) ô để kiểm tra mọi cửa sổ 'win_condition' ô chứa (r, c)
            for offset in range(self.win_condition):
                start_r = r - offset * dr
                start_c = c - offset * dc
                
                end_r = start_r + (self.win_condition - 1) * dr
                end_c = start_c + (self.win_condition - 1) * dc
                
                # Nếu cửa sổ nằm gọn trong bàn cờ
                if 0 <= start_r < self.size and 0 <= start_c < self.size and \
                   0 <= end_r < self.size and 0 <= end_c < self.size:
                    
                    p_cnt = 0
                    o_cnt = 0
                    
                    for i in range(self.win_condition):
                        cell = self.grid[start_r + i*dr][start_c + i*dc]
                        if cell == player:
                            p_cnt += 1
                        elif cell == opp:
                            o_cnt += 1
                            
                    # Cửa sổ mở cho phe mình (có khả năng tạo chuỗi)
                    if p_cnt > 0 and o_cnt == 0:
                        if p_cnt == self.win_condition: score += 1000000
                        elif p_cnt == self.win_condition - 1: score += 10000
                        elif p_cnt == self.win_condition - 2: score += 100
                        else: score += 10 # 1 hoặc 2 quân
                    # Cửa sổ mở cho đối thủ (nguy hiểm)
                    elif o_cnt > 0 and p_cnt == 0:
                        if o_cnt == self.win_condition: score -= 1200000 # Trừ nặng hơn một chút để AI thủ kỹ hơn
                        elif o_cnt == self.win_condition - 1: score -= 12000
                        elif o_cnt == self.win_condition - 2: score -= 120
                        else: score -= 12 # 1 hoặc 2 quân
                        
        # Khuyến khích đánh gần trung tâm (Heuristic phụ)
        ctr = self.size // 2
        score += max(0, 40 - (abs(r - ctr) + abs(c - ctr)) * 3)
        return score

    def _count_threats(self, r, c, player) -> float:
        """
        Đếm giá trị đe dọa của nước đi (r, c). 
        Trả về 2.0 nếu tạo cửa sổ có 3 quân, 1.0 nếu tạo cửa sổ có 2 quân.
        """
        threat_score = 0
        for dr, dc in self.DIRECTIONS:
            for offset in range(self.win_condition):
                start_r = r - offset * dr
                start_c = c - offset * dc
                if 0 <= start_r < self.size and 0 <= start_c < self.size:
                    er, ec = start_r + 3*dr, start_c + 3*dc
                    if 0 <= er < self.size and 0 <= ec < self.size:
                        p_cnt, z_cnt = 0, 0
                        for i in range(4):
                            cell = self.grid[start_r + i*dr][start_c + i*dc]
                            if cell == player: p_cnt += 1
                            elif cell == 0: z_cnt += 1
                            else: break
                        if p_cnt == 3 and z_cnt == 1:
                            threat_score = max(threat_score, 2.0)
                        elif p_cnt == 2 and z_cnt == 2:
                            threat_score = max(threat_score, 1.0)
        return threat_score

    def copy(self):
        """Tạo một bản sao sâu của bàn cờ."""
        new_board = Board(self.size, self.win_condition)
        new_board.grid = [r[:] for r in self.grid]
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
            row_str = " ".join(symbols[self.grid[r][c]] for c in range(self.size))
            print(f"{r} {row_str}")
        print(f"Lượt kế tiếp: {symbols[self.current_player]}")
