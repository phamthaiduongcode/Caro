import random

class Board:
    DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1)]
    _NEIGHBOR_OFFSETS = [(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3) if dr or dc]

    # Pre-compute score lookup để tránh if-else chain trong inner loop
    _SCORE_TABLE  = [0, 10, 100, 10000, 1000000, 1000000]
    _OSCORE_TABLE = [0, 12, 120, 12000, 1200000, 1200000]

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

    def _compute_score_delta(self, row, col, player) -> int:
        opp  = 3 - player
        delta = 0
        wc    = self.win_condition
        size  = self.size
        grid  = self.grid
        SCORE  = self._SCORE_TABLE
        OSCORE = self._OSCORE_TABLE

        for dr, dc in self.DIRECTIONS:
            for offset in range(wc):
                sr = row - offset * dr;  sc = col - offset * dc
                er = sr + (wc-1) * dr;   ec = sc + (wc-1) * dc
                if not (0 <= sr < size and 0 <= sc < size and
                        0 <= er < size and 0 <= ec < size):
                    continue

                p_cnt = o_cnt = 0
                for i in range(wc):
                    cell = grid[(sr + i*dr)*size + sc + i*dc]
                    if   cell == player: p_cnt += 1
                    elif cell == opp:    o_cnt += 1

                if o_cnt == 0 and p_cnt > 0:
                    wd = SCORE[p_cnt+1] - SCORE[p_cnt]
                elif p_cnt == 0 and o_cnt > 0:
                    wd = -OSCORE[o_cnt]
                else:
                    continue

                delta += wd if player == 2 else -wd

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

        wins = []; blocks = []; normal = []
        for pos in self._candidates:
            r, c = pos
            if self.fast_check_win(r, c, cur):
                wins.append(pos)
            elif self.fast_check_win(r, c, opp):
                blocks.append(pos)
            else:
                normal.append(pos)

        if wins:
            return wins

        remaining = self.MAX_MOVES - len(blocks)
        if remaining > 0 and normal:
            normal.sort(key=lambda p: -(size - abs(p[0]-ctr) - abs(p[1]-ctr)))
            normal = normal[:remaining]

        return blocks + normal

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
