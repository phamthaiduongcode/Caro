import random

class Board:
    DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]
    _NEIGHBOR_OFFSETS = [(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3) if dr or dc]

    # Trọng số được tinh chỉnh để phản ánh Open vs Half patterns
    # Open3 = 250k (chia 2 vì 1 thế Open3 tạo ra 2 cửa sổ trượt có điểm)
    # Half3 = 100k
    WIN_SCORE = 1_000_000
    OPEN3_WIN_VAL = 125_000   # _XXX_ tạo ra 2 cửa sổ => 250,000
    HALF3_WIN_VAL = 100_000
    OPEN2_WIN_VAL = 2_500
    HALF2_WIN_VAL = 1_000

    def __init__(self, size=9, win_condition=4):
        if size < 9:
            raise ValueError("Board size must be at least 9x9.")
        self.size = size
        self.win_condition = win_condition
        self.grid = [0] * (size * size) # Flat array
        self.current_player = 1
        self.history = []
        self.current_score = 0

        self.zobrist_table = [[[random.getrandbits(64) for _ in range(3)]
                               for _ in range(size)] for _ in range(size)]
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
        SCORE  = self._SCORE_TABLE
        OSCORE = self._OSCORE_TABLE

        for dr, dc in self.DIRECTIONS:
            # "Phóng tia": Lấy dữ liệu 1 đường thẳng duy nhất chứa ô vừa đánh
            # wc=4 -> lấy 4 ô mỗi phía để bao quát mọi cửa sổ 4 ô chứa điểm này
            line = []
            for i in range(-wc, wc + 1):
                r, c = row + i*dr, col + i*dc
                if 0 <= r < size and 0 <= c < size:
                    line.append(grid[r*size + c])
                else:
                    line.append(-1) # Biên bàn cờ tính là chặn

            # Quét các cửa sổ kích thước wc đi qua điểm trung tâm (index wc trong line)
            for start in range(1, wc + 1):
                end = start + wc
                window = line[start:end]
                
                p1_cnt = window.count(1)
                p2_cnt = window.count(2)

                # Nếu cửa sổ hỗn tạp (có cả X và O) -> 0 điểm, không cần tính delta
                if p1_cnt > 0 and p2_cnt > 0: continue
                
                for p_idx in (1, 2):
                    if (p_idx == 1 and p2_cnt > 0) or (p_idx == 2 and p1_cnt > 0): continue
                    
                    other = 3 - p_idx
                    is_ai = (p_idx == 2)
                    cnt = p1_cnt if p_idx == 1 else p2_cnt
                    
                    # Check chặn bằng dữ liệu từ 'line' đã fetch
                    b_s = (line[start-1] == other or line[start-1] == -1)
                    b_e = (line[end] == other or line[end] == -1)

                    if player == p_idx: # Tăng điểm cho quân mình
                        s_before = self._get_window_score(cnt, 0, b_s, b_e, is_ai)
                        s_after  = self._get_window_score(cnt + 1, 0, b_s, b_e, is_ai)
                    else: # Chặn điểm của đối thủ (đối thủ đang có quân trong window này)
                        if cnt == 0: continue
                        s_before = self._get_window_score(cnt, 0, b_s, b_e, is_ai)
                        s_after  = 0
                    
                    wd = s_after - s_before
                    delta += wd if is_ai else -wd

        # ─── FORK LOGIC ───
        # 1. Fork bonus cho người vừa đánh
        threat_dirs = 0
        opp = 3 - player
        opp_threat_dirs = 0

        for dr, dc in self.DIRECTIONS:
            cnt_p = 1
            cnt_o = 1
            for d in (1, -1):
                # Check threat cho người vừa đánh
                nr, nc = row + dr*d, col + dc*d
                while 0 <= nr < size and 0 <= nc < size and grid[nr*size+nc] == player:
                    cnt_p += 1
                    nr += dr*d; nc += dc*d
                
                # Check threat mà đối thủ đáng lẽ có tại đây
                nr, nc = row + dr*d, col + dc*d
                while 0 <= nr < size and 0 <= nc < size and grid[nr*size+nc] == opp:
                    cnt_o += 1
                    nr += dr*d; nc += dc*d
            
            if cnt_p >= wc - 1: threat_dirs += 1
            if cnt_o >= wc - 1: opp_threat_dirs += 1

        if threat_dirs >= 2:
            fork_bonus = 80_000  # Gần bằng HALF3 — rất nguy hiểm
            delta += fork_bonus if player == 2 else -fork_bonus
        
        if opp_threat_dirs >= 2:
            # Đánh vào đây CHẶN fork của đối thủ -> cực kỳ quan trọng
            fork_block_bonus = 70_000
            delta += fork_block_bonus if player == 2 else -fork_block_bonus

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
        self.history.append((row, col, delta))
        self.current_player = 3 - self.current_player
        self._cand_refs[idx] = 0
        self._candidates.discard((row, col))
        self._add_neighbors(row, col)
        return True

    def undo_move(self) -> bool:
        if not self.history:
            return False

        row, col, delta = self.history.pop()
        idx  = row * self.size + col
        zt   = self.zobrist_table
        self.current_hash ^= zt[row][col][self.grid[idx]]
        self.grid[idx]     = 0
        self.current_hash ^= zt[row][col][0]
        self.current_hash ^= self.zobrist_side
        self.current_score -= delta
        self.current_player = 3 - self.current_player
        self._remove_neighbors(row, col)
        size = self.size
        grid = self.grid
        ref  = sum(1 for dr, dc in self._NEIGHBOR_OFFSETS
                   if 0 <= row+dr < size and 0 <= col+dc < size
                   and grid[(row+dr)*size + col+dc] != 0)
        if ref > 0:
            self._cand_refs[idx] = ref
            self._candidates.add((row, col))
        return True

    def check_win(self) -> int:
        if not self.history:
            return 0
        last_r, last_c, _ = self.history[-1]
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

    def _is_fork_threat(self, r, c, player) -> bool:
        """Kiểm tra nếu đánh vào (r,c) tạo ra >= 2 đe dọa Open/Half-3 cùng lúc."""
        threat_count = 0
        wc, size, grid = self.win_condition, self.size, self.grid
        for dr, dc in self.DIRECTIONS:
            cnt = 1
            open_ends = 0
            for d in (1, -1):
                nr, nc = r + dr*d, c + dc*d
                while 0 <= nr < size and 0 <= nc < size and grid[nr*size+nc] == player:
                    cnt += 1; nr += dr*d; nc += dc*d
                if 0 <= nr < size and 0 <= nc < size and grid[nr*size+nc] == 0:
                    open_ends += 1
            if cnt >= wc - 1 and open_ends >= 1:  # Half-3 hoặc Open-3
                threat_count += 1
            if threat_count >= 2:
                return True
        return False

    MAX_MOVES = 20

    def get_legal_moves(self) -> list:
        if not self.history:
            return [(self.size // 2, self.size // 2)]
        if not self._candidates:
            return []

        cur  = self.current_player
        opp  = 3 - cur
        ctr  = self.size >> 1
        size = self.size

        # Tăng max_moves cho bàn 15x15. Bàn càng to, giới hạn càng nên rộng ra đôi chút.
        max_moves = min(20 + (self.size - 9) * 2, 40) # Cho tối đa 30-40 nước

        wins = []; blocks = []; threats = []; normal = []
        for pos in self._candidates:
            r, c = pos
            if self.fast_check_win(r, c, cur):
                wins.append(pos)
            elif self.fast_check_win(r, c, opp):
                blocks.append(pos)
            elif self._is_fork_threat(r, c, cur) or self._is_fork_threat(r, c, opp):
                threats.append(pos)
            else:
                normal.append(pos)

        if wins:
            return wins

        remaining = max_moves - len(blocks) - len(threats)
        if remaining > 0 and normal:
            # Sửa lại hàm sort:
            # Ưu tiên 1: Điểm nóng (self._cand_refs lớn nhất - đông quân cờ xung quanh nhất)
            # Ưu tiên 2: Gần trung tâm bàn cờ (để giải quyết các điểm có cùng độ nóng)
            normal.sort(key=lambda p: (
                self._cand_refs[p[0] * size + p[1]], 
                -(abs(p[0] - ctr) + abs(p[1] - ctr)) 
            ), reverse=True)
            
            normal = normal[:remaining]
        elif remaining <= 0:
            normal = []

        return blocks + threats + normal

    def evaluate_position(self, r, c, player):
        score = 0; opp = 3 - player
        grid = self.grid; size = self.size; wc = self.win_condition
        for dr, dc in self.DIRECTIONS:
            for offset in range(wc):
                sr, sc = r - offset*dr, c - offset*dc
                er, ec = sr+(wc-1)*dr, sc+(wc-1)*dc
                if not (0<=sr<size and 0<=sc<size and 0<=er<size and 0<=ec<size): continue
                p_cnt = o_cnt = 0
                for i in range(wc):
                    cell = grid[(sr+i*dr)*size + sc+i*dc]
                    if cell == player: p_cnt += 1
                    elif cell == opp:  o_cnt += 1
                if p_cnt > 0 and o_cnt == 0:
                    score += (1000000 if p_cnt==wc else 10000 if p_cnt==wc-1 else 100 if p_cnt==wc-2 else 10)
                elif o_cnt > 0 and p_cnt == 0:
                    score -= (1200000 if o_cnt==wc else 12000 if o_cnt==wc-1 else 120 if o_cnt==wc-2 else 12)
        ctr = size >> 1
        score += max(0, 40 - (abs(r-ctr)+abs(c-ctr))*3)
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