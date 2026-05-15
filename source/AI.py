import math
import time

class SearchTimeout(Exception):
    """Ngoại lệ tùy chỉnh để dừng tìm kiếm khi hết thời gian."""
    pass


# ─────────────────────────────────────────────────────────────
# Trọng số mặc định (baseline đã được căn chỉnh tay)
# Đây là điểm khởi đầu cho GA training.
# ─────────────────────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    # Tấn công (AI)
    "open3":        250_000,   # _XXX_  → Thắng chắc trong luật 4
    "half3":        100_000,   # XXX_   → Buộc phải chặn ngay trong luật 4
    "broken4":      100_000,   # XX_X   → Nguy hiểm tương đương half3
    "open2":          5_000,   # _XX_
    "half2":          1_000,   # XX_
    "broken3":       10_000,   # X_X_
    "open1":             10,   # _X_

    # Hệ số phòng thủ: nhân vào điểm của đối thủ
    # > 1.0: thiên về phòng thủ; < 1.0: thiên về tấn công
    # Không có luật chặn 2 đầu → open3 của địch rất nguy hiểm → nên > 1.0
    "defense_mult":    1.20,

    # Bonus vị trí: cộng thêm cho quân gần tâm
    "center_bonus":      40,
    "fork_bonus":   500_000,   # 2 open3 cùng lúc = gần như thắng chắc
}


class CaroAI:
    def __init__(self, player_id, depth=3, weights=None):
        """
        Args:
            player_id: 1 (X) hoặc 2 (O)
            depth:     độ sâu tìm kiếm tối đa
            weights:   dict trọng số (dùng DEFAULT_WEIGHTS nếu None)
        """
        self.player_id = player_id
        self.opp_id    = 3 - player_id
        self.depth     = depth
        self.weights   = weights if weights is not None else dict(DEFAULT_WEIGHTS)

        # Điểm 3: Precompute Center Weights để tránh tính toán lặp lại
        size = 9 # Mặc định size 9 cho Caro
        ctr = size // 2
        cb = self.weights.get("center_bonus", 40)
        self.center_weights = [[max(0, cb - (abs(r - ctr) + abs(c - ctr)) * 3) 
                                for c in range(size)] for r in range(size)]

        self.nodes_visited     = 0
        self.center            = ctr
        self.start_time        = 0
        self.time_limit        = 0
        self.transposition_table = {}

    # ──────────────────────────────────────────────────────────
    # Giao diện chính
    # ──────────────────────────────────────────────────────────
    def get_move(self, board, mode="alpha_beta", time_limit=10.0):
        """
        Trả về: (best_move, best_score, nodes_visited, time_taken)
        time_limit=None → bỏ qua iterative deepening, chạy thẳng depth.
        """
        self.nodes_visited       = 0
        self.start_time          = time.time()
        self.time_limit          = time_limit
        self.transposition_table = {}

        self.player_id = board.current_player
        self.opp_id    = 3 - self.player_id
        self.center    = board.size // 2

        legal_moves = board.get_legal_moves()
        if not legal_moves:
            return None, 0, 0, 0

        # get_legal_moves() đã sort theo priority (nước thắng=3, nước chặn=2, thường=0).
        # KHÔNG sort lại theo center — làm vậy sẽ xóa mất ordering tốt đó.
        # Center bonus đã được tính trong heuristic() nên không cần ưu tiên ở đây.

        # BƯỚC 0: Kiểm tra nước thắng ngay (depth=1)
        for move in legal_moves:
            if board.fast_check_win(move[0], move[1], self.player_id):
                return move, 1_000_000, 1, time.time() - self.start_time

        # BƯỚC 0.5: Chặn đối thủ thắng ngay (Bắt buộc phải chặn trước khi nghĩ đến Fork)
        for move in legal_moves:
            if board.fast_check_win(move[0], move[1], self.opp_id):
                return move, 950_000, 1, time.time() - self.start_time

        final_best_move  = legal_moves[0]
        final_best_score = -math.inf

        # Nếu time_limit=None → chạy đúng self.depth (dùng cho training)
        # Sửa: Chỉ dùng Depth chẵn để tránh Horizon Effect (2, 4)
        search_range = [self.depth] if self.time_limit is None else range(2, self.depth + 1, 2)

        for current_depth in search_range:
            depth_best_move  = None
            depth_best_score = -math.inf

            try:
                for move in legal_moves:
                    if self.time_limit is not None and \
                       time.time() - self.start_time > self.time_limit:
                        raise SearchTimeout()

                    board.make_move(*move)
                    if mode == "minimax":
                        score = self.minimax(board, current_depth - 1, False)
                    else:  # alpha_beta (mặc định)
                        score = self.alpha_beta(board, current_depth - 1, -math.inf, math.inf, False)
                    board.undo_move()

                    if score > depth_best_score:
                        depth_best_score = score
                        depth_best_move  = move

                # [QUAN TRỌNG] Chỉ cập nhật kết quả cuối cùng khi đã hoàn thành trọn vẹn độ sâu này
                final_best_move  = depth_best_move
                final_best_score = depth_best_score

                # Move ordering: đưa nước tốt nhất của độ sâu vừa hoàn thành lên đầu cho lần lặp kế tiếp
                if final_best_move in legal_moves:
                    legal_moves.remove(final_best_move)
                    legal_moves.insert(0, final_best_move)

                if final_best_score >= 1_000_000:
                    break  # Tìm thấy nước thắng tuyệt đối

            except SearchTimeout:
                break

        duration = time.time() - self.start_time
        return final_best_move, final_best_score, self.nodes_visited, duration

    # ──────────────────────────────────────────────────────────
    # Alpha-Beta (Đã tối ưu: Move Ordering với TT-Move)
    # ──────────────────────────────────────────────────────────
    def alpha_beta(self, board, depth, alpha, beta, is_maximizing):
        self.nodes_visited += 1

        board_hash              = board.get_hash()
        alpha_orig, beta_orig   = alpha, beta
        
        # [MỚI] Biến để hứng nước đi tốt nhất từ TT
        tt_move = None 

        if board_hash in self.transposition_table:
            # [MỚI] Lấy tt_move ra từ index thứ 3 của tuple
            tt_depth, tt_flag, tt_val, tt_move = self.transposition_table[board_hash]
            if tt_depth >= depth:
                if tt_flag == "EXACT":
                    return tt_val
                elif tt_flag == "LOWER":
                    alpha = max(alpha, tt_val)
                elif tt_flag == "UPPER":
                    beta  = min(beta, tt_val)
                if alpha >= beta:
                    return tt_val

        # Kiểm tra timeout (giữ nguyên của bạn)
        if self.nodes_visited % 100 == 0:
            if self.time_limit is not None and \
               time.time() - self.start_time > self.time_limit:
                raise SearchTimeout()

        result = board.check_win()
        if result == self.player_id:  return  1_000_000 + depth
        if result == self.opp_id:     return -1_000_000 - depth
        if result == -1:              return  0
        if depth == 0:                return  self.heuristic(board)

        legal_moves = board.get_legal_moves()

        # ────────────────────────────────────────────────────
        # [MỚI] TT-MOVE ORDERING
        # Nếu TT có lưu nước đi tốt nhất cho trạng thái này,
        # đẩy nó lên đầu danh sách để Alpha-Beta cắt nhánh sớm nhất!
        # ────────────────────────────────────────────────────
        if tt_move is not None and tt_move in legal_moves:
            legal_moves.remove(tt_move)
            legal_moves.insert(0, tt_move)

        # [MỚI] Biến theo dõi nước đi tốt nhất trong nhánh này để lưu vào TT
        best_move_found = None 

        if is_maximizing:
            best_score = -math.inf
            for move in legal_moves:
                board.make_move(*move)
                val = self.alpha_beta(board, depth - 1, alpha, beta, False)
                board.undo_move()
                
                # [MỚI] Cập nhật best_move_found
                if val > best_score:
                    best_score = val
                    best_move_found = move 
                    
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    break
        else:
            best_score = math.inf
            for move in legal_moves:
                board.make_move(*move)
                val = self.alpha_beta(board, depth - 1, alpha, beta, True)
                board.undo_move()
                
                # [MỚI] Cập nhật best_move_found
                if val < best_score:
                    best_score = val
                    best_move_found = move
                    
                beta = min(beta, best_score)
                if beta <= alpha:
                    break

        # LOWER bound: score >= beta_orig → fail-high (cắt alpha)
        # UPPER bound: score <= alpha_orig → fail-low (cắt beta)
        # EXACT: nằm trong cửa sổ
        if best_score <= alpha_orig:
            flag = "UPPER"
        elif best_score >= beta_orig:
            flag = "LOWER"
        else:
            flag = "EXACT"

        self.transposition_table[board_hash] = (depth, flag, best_score, best_move_found)
        return best_score
    # ──────────────────────────────────────────────────────────
    # Minimax thuần túy
    # ──────────────────────────────────────────────────────────
    def minimax(self, board, depth, is_maximizing):
        self.nodes_visited += 1

        if self.nodes_visited % 100 == 0:
            if self.time_limit is not None and \
               time.time() - self.start_time > self.time_limit:
                raise SearchTimeout()

        result = board.check_win()
        if result == self.player_id:  return  1_000_000 + depth
        if result == self.opp_id:     return -1_000_000 - depth
        if result == -1:              return  0
        if depth == 0:                return  self.heuristic(board)

        legal_moves = board.get_legal_moves()

        if is_maximizing:
            best = -math.inf
            for move in legal_moves:
                board.make_move(*move)
                best = max(best, self.minimax(board, depth - 1, False))
                board.undo_move()
            return best
        else:
            best = math.inf
            for move in legal_moves:
                board.make_move(*move)
                best = min(best, self.minimax(board, depth - 1, True))
                board.undo_move()
            return best

    # ──────────────────────────────────────────────────────────
    # Heuristic
    # ──────────────────────────────────────────────────────────
    def heuristic(self, board):
        """
        Lượng giá O(1): Trả về ngay lập tức điểm số đã được tính sẵn bởi bàn cờ.
        """
        w        = self.weights
        score    = 0
        size     = board.size
        grid     = board.grid
        win_cond = board.win_condition   # = 4
        player   = self.player_id
        opp      = self.opp_id

        for r in range(size):
            for c in range(size):
                for dr, dc in board.DIRECTIONS:

                    # ── 1. Consecutive (cửa sổ win_cond ô) ──
                    # Chỉ tính khi các quân của player liền nhau, không có gap.
                    # Nếu có gap → là broken pattern, đã được tính ở section 2.
                    # Cách phát hiện gap: span (last_idx - first_idx + 1) phải == p_count.
                    end_r = r + (win_cond - 1) * dr
                    end_c = c + (win_cond - 1) * dc
                    if 0 <= end_r < size and 0 <= end_c < size:
                        p_count  = 0
                        blocked  = False
                        first_idx = -1
                        last_idx  = -1

                        for i in range(win_cond):
                            v = grid[r + i*dr][c + i*dc]
                            if v == player:
                                p_count += 1
                                if first_idx == -1:
                                    first_idx = i
                                last_idx = i
                            elif v == opp:
                                blocked = True
                                break

                        # Bỏ qua nếu bị chặn, rỗng, hoặc có gap giữa các quân
                        is_consecutive = (
                            not blocked
                            and p_count > 0
                            and (last_idx - first_idx + 1) == p_count
                        )

                        if is_consecutive:
                            open_ends = 0
                            pr, pc = r - dr, c - dc
                            if 0 <= pr < size and 0 <= pc < size and grid[pr][pc] == 0:
                                open_ends += 1
                            nr, nc = end_r + dr, end_c + dc
                            if 0 <= nr < size and 0 <= nc < size and grid[nr][nc] == 0:
                                open_ends += 1

                            if p_count == 3:
                                if open_ends == 2:
                                    score += w["open3"]
                                elif open_ends == 1:
                                    score += w["half3"]
                            elif p_count == 2:
                                if open_ends == 2:
                                    score += w["open2"]
                                elif open_ends == 1:
                                    score += w["half2"]
                            elif p_count == 1:
                                if open_ends == 2:
                                    score += w["open1"]

                    # ── 2. Broken patterns (cửa sổ 5 ô) ──
                    # Chỉ tính khi cửa sổ 5 ô nằm trong bàn
                    end5_r = r + 4 * dr
                    end5_c = c + 4 * dc
                    if not (0 <= end5_r < size and 0 <= end5_c < size):
                        continue

                    w5 = [grid[r + i*dr][c + i*dc] for i in range(5)]
                    if opp in w5:
                        continue   # Bị địch chặn trong cửa sổ → không tính

                    p5 = w5.count(player)
                    z5 = w5.count(0)

                    # broken4: 4 quân + 1 trống trong 5 ô (XX_X hoặc X_XX)
                    if p5 == 4 and z5 == 1:
                        score += w["broken4"]
                    # broken3: 3 quân + 2 trống trong 5 ô
                    elif p5 == 3 and z5 == 2:
                        score += w["broken3"]

        return score
