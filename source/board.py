import random

# Chia sẻ bảng Zobrist để tránh khởi tạo lại tốn kém khi copy board (đặc biệt quan trọng với 15x15)
_ZOBRIST_CACHE = {}

class Board:
    DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]
    _NEIGHBOR_OFFSETS = [(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3) if dr or dc]

    # Trọng số được tinh chỉnh để phản ánh Open vs Half patterns
    # Open3 = 250k (chia 2 vì 1 thế Open3 tạo ra 2 cửa sổ trượt có điểm)
    # Half3 = 100k
    WIN_SCORE = 1_000_000
    OPEN3_WIN_VAL = 125_000   # _XXX_ tạo ra 2 cửa sổ => 250,000
    HALF3_WIN_VAL = 40_000    # OXXX_ hoặc _XXXO => chỉ nên nhận ~80,000 - 100,000 tổng
    OPEN2_WIN_VAL = 2_500
    HALF2_WIN_VAL = 500

    def __init__(self, size=9, win_condition=4):
        if size < 9:
            raise ValueError("Board size must be at least 9x9.")
        self.size = size
        self.win_condition = win_condition
        self.grid = [0] * (size * size) # Flat array
        self.current_player = 1
        self.history = []
        self.current_score = 0

        # Sử dụng cache cho zobrist_table để tối ưu tốc độ khởi tạo và copy()
        if size not in _ZOBRIST_CACHE:
            _ZOBRIST_CACHE[size] = [
                [[random.getrandbits(64) for _ in range(3)]
                 for _ in range(size)] for _ in range(size)
            ]
        self.zobrist_table = _ZOBRIST_CACHE[size]
        
        self.zobrist_side = random.getrandbits(64)
        self.current_hash = 0
        for r in range(size):
            for c in range(size):
                self.current_hash ^= self.zobrist_table[r][c][0]

        self._cand_refs = [0] * (size * size)
        self._candidates: set = set()

    def _add_neighbors(self, r, c):
        size = self.size
        grid = self.grid
        refs = self._cand_refs
        cands = self._candidates
        for dr, dc in self._NEIGHBOR_OFFSETS:
            nr = r + dr; nc = c + dc
            if 0 <= nr < size and 0 <= nc < size:
                idx = nr * size + nc
                if grid[idx] == 0:
                    refs[idx] += 1
                    cands.add((nr, nc))

    def _remove_neighbors(self, r, c):
        size = self.size
        refs = self._cand_refs
        cands = self._candidates
        for dr, dc in self._NEIGHBOR_OFFSETS:
            nr = r + dr; nc = c + dc
            if 0 <= nr < size and 0 <= nc < size:
                idx = nr * size + nc
                v = refs[idx]
                if v > 0:
                    v -= 1
                    refs[idx] = v
                    if v == 0:
                        cands.discard((nr, nc))

    def is_valid(self, row, col) -> bool:
        return 0 <= row < self.size and 0 <= col < self.size and \
               self.grid[row * self.size + col] == 0

    def get_hash(self):
        return self.current_hash

    def _get_window_score(self, p_cnt, o_cnt, is_blocked_start, is_blocked_end, is_ai):
        """Hàm lượng giá cửa sổ thông minh: Phân biệt Open/Half/Blocked."""
        if p_cnt > 0 and o_cnt > 0: return 0
        
        count = p_cnt
        if count == 0: return 0
        if count >= self.win_condition: return self.WIN_SCORE

        # Nếu bị chặn cả 2 đầu -> Cửa sổ này vô dụng (trừ khi đã thắng)
        if is_blocked_start and is_blocked_end: return 0

        # Phân loại dựa trên số đầu trống
        is_open = not is_blocked_start and not is_blocked_end
        
        if count == 3:
            return self.OPEN3_WIN_VAL if is_open else self.HALF3_WIN_VAL
        if count == 2:
            return self.OPEN2_WIN_VAL if is_open else self.HALF2_WIN_VAL
        return 10 # count == 1

    def _compute_score_delta(self, row, col, player) -> int:
        opp  = 3 - player
        delta = 0
        wc    = self.win_condition
        size  = self.size
        grid  = self.grid

        for dr, dc in self.DIRECTIONS:
            # Tối ưu: Lấy giá trị các ô xung quanh vào 1 list duy nhất để giảm slicing/allocation
            line_vals = []
            for i in range(-wc, wc + 1):
                r, c = row + i*dr, col + i*dc
                if 0 <= r < size and 0 <= c < size:
                    line_vals.append(grid[r*size + c])
                else:
                    line_vals.append(-1) # Biên bàn cờ tính là chặn

            # Quét các cửa sổ chứa ô vừa đánh (index wc trong line_vals)
            for start in range(1, wc + 1):
                end = start + wc
                
                p1_cnt = 0
                p2_cnt = 0
                for k in range(start, end):
                    val = line_vals[k]
                    if val == 1: p1_cnt += 1
                    elif val == 2: p2_cnt += 1
                
                if p1_cnt > 0 and p2_cnt > 0:
                    continue
                
                for p_idx in (1, 2):
                    if (p_idx == 1 and p2_cnt > 0) or (p_idx == 2 and p1_cnt > 0):
                        continue
                    
                    other, is_ai = 3 - p_idx, (p_idx == 2)
                    cnt = p1_cnt if p_idx == 1 else p2_cnt
                    b_s = (line_vals[start-1] == other or line_vals[start-1] == -1)
                    b_e = (line_vals[end] == other or line_vals[end] == -1)

                    if player == p_idx: # Tăng điểm cho quân mình
                        s_before = self._get_window_score(cnt, 0, b_s, b_e, is_ai)
                        s_after  = self._get_window_score(cnt + 1, 0, b_s, b_e, is_ai)
                    else: # Chặn điểm của đối thủ (đối thủ đang có quân trong window này)
                        if cnt == 0: continue
                        s_before = self._get_window_score(cnt, 0, b_s, b_e, is_ai)
                        s_after  = 0
                    
                    wd = s_after - s_before
                    delta += wd if is_ai else -wd

        ctr = size >> 1
        center_val = max(0, 40 - (abs(row-ctr) + abs(col-ctr)) * 3)
        delta += center_val if player == 2 else -center_val
        return delta

    def make_move(self, row, col) -> bool:
        if not self.is_valid(row, col):
            return False

        delta = self._compute_score_delta(row, col, self.current_player)
        idx   = row * self.size + col
        zt    = self.zobrist_table
        self.current_hash ^= zt[row][col][0]
        self.grid[idx]     = self.current_player
        self.current_hash ^= zt[row][col][self.current_player]
        self.current_hash ^= self.zobrist_side
        self.current_score += delta
        # TỐI ƯU: Lưu old_refs để khôi phục trong undo_move mà không cần tính lại neighbor
        self.history.append((row, col, delta, self._cand_refs[idx]))
        self.current_player = 3 - self.current_player
        self._cand_refs[idx] = 0
        self._candidates.discard((row, col))
        self._add_neighbors(row, col)
        return True

    def undo_move(self) -> bool:
        if not self.history:
            return False

        row, col, delta, old_refs = self.history.pop()
        idx  = row * self.size + col
        zt   = self.zobrist_table
        self.current_hash ^= zt[row][col][self.grid[idx]]
        self.grid[idx]     = 0
        self.current_hash ^= zt[row][col][0]
        self.current_hash ^= self.zobrist_side
        self.current_score -= delta
        self.current_player = 3 - self.current_player
        self._remove_neighbors(row, col)
        if old_refs > 0:
            self._cand_refs[idx] = old_refs
            self._candidates.add((row, col))
        return True

    def check_win(self) -> int:
        if not self.history:
            return 0
        # Cập nhật để nhận đủ 4 giá trị (row, col, delta, old_refs) hoặc chỉ lấy 2 giá trị đầu
        last_r, last_c = self.history[-1][:2]
        last_player = self.grid[last_r * self.size + last_c]
        if self._check_at(last_r, last_c):
            return last_player
        if len(self.history) == self.size * self.size:
            return -1
        return 0

    def _check_at(self, r, c) -> bool:
        player = self.grid[r * self.size + c]
        size   = self.size
        grid   = self.grid
        wc     = self.win_condition
        for dr, dc in self.DIRECTIONS:
            cnt = 1
            for d in (1, -1):
                nr = r + dr*d; nc = c + dc*d
                while 0 <= nr < size and 0 <= nc < size and grid[nr*size+nc] == player:
                    cnt += 1
                    if cnt >= wc: return True
                    nr += dr*d; nc += dc*d
        return False

    def fast_check_win(self, r, c, player) -> bool:
        size = self.size
        grid = self.grid
        wc   = self.win_condition
        for dr, dc in self.DIRECTIONS:
            cnt = 1
            for d in (1, -1):
                nr = r + dr*d; nc = c + dc*d
                while 0 <= nr < size and 0 <= nc < size and grid[nr*size+nc] == player:
                    cnt += 1; nr += dr*d; nc += dc*d
            if cnt >= wc: return True
        return False

    MAX_MOVES = 20

    def get_legal_moves(self) -> list:
        if not self.history:
            return [(self.size // 2, self.size // 2)]
        if not self._candidates:
            return []

        cur, opp = self.current_player, 3 - self.current_player
        size = self.size
        ctr = size // 2
        # Tăng số lượng nước xem xét cho bàn lớn (15x15) để không bỏ sót các đường xa
        max_moves = 20 if size <= 9 else 32

        wins, blocks, normal_with_scores = [], [], []
        for pos in self._candidates:
            r, c = pos
            if self.fast_check_win(r, c, cur):
                wins.append(pos)
                continue
            if self.fast_check_win(r, c, opp):
                blocks.append(pos)
                continue
            
            # Ưu tiên các nước gần trung tâm (giúp Alpha-Beta tìm thấy nước tốt nhanh hơn)
            dist_score = (size - abs(r - ctr) - abs(c - ctr))
            normal_with_scores.append((pos, dist_score))

        if wins:
            return wins

        # Sắp xếp các nước đi bình thường theo độ ưu tiên giảm dần
        normal_with_scores.sort(key=lambda x: x[1], reverse=True)
        normal = [x[0] for x in normal_with_scores]
        
        result = blocks + normal
        return result[:max_moves]

    def evaluate_position(self, r, c, player):
        """Đưa evaluate_position về cùng logic 'Phóng tia' để đảm bảo tính nhất quán."""
        score = 0
        size, grid, wc = self.size, self.grid, self.win_condition
        for dr, dc in self.DIRECTIONS:
            line = []
            for i in range(-wc, wc + 1):
                nr, nc = r + i*dr, c + i*dc
                line.append(grid[nr*size + nc] if (0 <= nr < size and 0 <= nc < size) else -1)
            
            for start in range(1, wc + 1):
                window = line[start : start + wc]
                p1, p2 = window.count(1), window.count(2)
                if p1 > 0 and p2 > 0: continue
                
                for p_idx in (1, 2):
                    if (p_idx == 1 and p2 > 0) or (p_idx == 2 and p1 > 0): continue
                    cnt, other, is_ai = (p1 if p_idx == 1 else p2), 3 - p_idx, (p_idx == 2)
                    b_s = (line[start - 1] == other or line[start - 1] == -1)
                    b_e = (line[start + wc] == other or line[start + wc] == -1)
                    s = self._get_window_score(cnt, 0, b_s, b_e, is_ai)
                    score += s if (is_ai == (player == 2)) else -s
                    
        ctr = size >> 1
        score += max(0, 40 - (abs(r - ctr) + abs(c - ctr)) * 3)
        return score

    def copy(self):
        nb = Board(self.size, self.win_condition)
        nb.grid = self.grid[:]
        nb.current_player = self.current_player
        nb.history = self.history.copy()
        nb.current_score = self.current_score
        nb.zobrist_table = self.zobrist_table
        nb.zobrist_side = self.zobrist_side
        nb.current_hash = self.current_hash
        nb._candidates = set(self._candidates)
        nb._cand_refs = self._cand_refs[:]
        return nb

    def display(self):
        symbols = {0:'.', 1:'X', 2:'O'}
        size = self.size
        print("  " + " ".join(str(i) for i in range(size)))
        for r in range(size):
            print(f"{r} " + " ".join(symbols[self.grid[r*size+c]] for c in range(size)))
        print(f"Lượt kế tiếp: {symbols[self.current_player]}")
