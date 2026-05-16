import math
import time
from source.utils import log_ai_move

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
    def __init__(self, player_id, depth, weights=None):
        """
        Args:
            player_id: 1 (X) hoặc 2 (O)
            depth:     độ sâu tìm kiếm tối đa
            weights:   dict trọng số (dùng DEFAULT_WEIGHTS nếu None)
        """
        self.player_id = player_id
        self.opp_id    = 3 - player_id
        self.depth     = depth
        self.weights = weights if weights is not None else dict(DEFAULT_WEIGHTS)

        # ─── TỐI ƯU 3: center_weights được khởi tạo lazy theo board size ───
        # Không hard-code size=9 nữa. Tính lại khi size thay đổi.
        self._center_weights_size = None
        self.center_weights = None

        self.nodes_visited     = 0
        self.center            = 0
        self.start_time        = 0
        self.time_limit        = 0
        self.transposition_table = {}

    def _ensure_center_weights(self, size):
        if self._center_weights_size == size:
            return
        ctr = size // 2
        cb  = self.weights.get("center_bonus", 40)
        self.center_weights = [
            [max(0, cb - (abs(r - ctr) + abs(c - ctr)) * 3) for c in range(size)]
            for r in range(size)
        ]
        self._center_weights_size = size

    # ──────────────────────────────────────────────────────────
    # Giao diện chính
    # ──────────────────────────────────────────────────────────
    def get_move(self, board, mode="alpha_beta", time_limit= 20.0, log_path=None):
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
        self._ensure_center_weights(board.size)

        legal_moves = board.get_legal_moves()
        if not legal_moves:
            return None, 0, 0, 0

        # TỐI ƯU ROOT: Đánh giá sơ bộ các nước đi tại Root để Alpha-Beta cắt nhánh tốt nhất có thể ngay từ đầu
        if len(legal_moves) > 1:
            move_evals = []
            for m in legal_moves:
                board.make_move(*m)
                val = self.heuristic(board)
                board.undo_move()
                move_evals.append((m, val))
            # Sắp xếp giảm dần để Alpha-Beta ưu tiên nhánh tốt nhất của máy lên trước
            move_evals.sort(key=lambda x: x[1], reverse=True)
            legal_moves = [x[0] for x in move_evals]

        # BƯỚC 0: Kiểm tra nước thắng ngay (depth=1)
        for move in legal_moves:
            if board.fast_check_win(move[0], move[1], self.player_id):
                return move, 1_000_000, 1, time.time() - self.start_time # ply=0 win

        # BƯỚC 0.5: Chặn đối thủ thắng ngay (Bắt buộc phải chặn trước khi nghĩ đến Fork)
        for move in legal_moves:
            if board.fast_check_win(move[0], move[1], self.opp_id):
                return move, 950_000, 1, time.time() - self.start_time

        final_best_move  = legal_moves[0]
        final_best_score = -math.inf

        achieved_depth = 0
        root_beta = math.inf

        # Nếu time_limit=None → chạy đúng self.depth (dùng cho training)
        # Sửa: Chỉ dùng Depth chẵn để tránh Horizon Effect (2, 4)
        search_range = [self.depth] if self.time_limit is None else range(1, self.depth + 1)

        for current_depth in search_range:
            depth_best_move  = None
            depth_best_score = -math.inf
            alpha = -math.inf

            try:
                for move in legal_moves:
                    if self.time_limit is not None and \
                       time.time() - self.start_time > self.time_limit:
                        raise SearchTimeout()

                    board.make_move(*move)
                    # Đoạn code cũ trong get_move
                    if mode == "minimax":
                        score = self.minimax(board, current_depth - 1, False, ply=1)
                    else:
                        score = self.alpha_beta(board, current_depth - 1, alpha, root_beta, False, ply=1, use_pvs=(mode == "alpha_beta"))
                    board.undo_move()

                    if score > depth_best_score:
                        depth_best_score = score
                        depth_best_move  = move
                    
                    # Cập nhật alpha để các nước đi sau ở Root được cắt tỉa
                    alpha = max(alpha, depth_best_score)

                # [QUAN TRỌNG] Chỉ cập nhật kết quả cuối cùng khi đã hoàn thành trọn vẹn độ sâu này
                final_best_move  = depth_best_move
                final_best_score = depth_best_score
                achieved_depth = current_depth

                # Move ordering: đưa nước tốt nhất của độ sâu vừa hoàn thành lên đầu cho lần lặp kế tiếp
                if final_best_move in legal_moves:
                    legal_moves.remove(final_best_move)
                    legal_moves.insert(0, final_best_move)

                if final_best_score >= 1_000_000:
                    break  # Tìm thấy nước thắng tuyệt đối

            except SearchTimeout:
                break

        duration = time.time() - self.start_time

        # Ghi log vào file moves.csv (chung cho cả Human và AI)
        if log_path:
            try:
                log_ai_move(log_path, [
                    'X' if self.player_id == 1 else 'O', str(final_best_move),
                    final_best_score, self.nodes_visited, round(duration, 4), achieved_depth
                ])
            except: pass

        return final_best_move, final_best_score, self.nodes_visited, duration

    def _check_timeout(self):
        """Gộp logic timeout vào một chỗ, tránh lặp code."""
        if self.nodes_visited % 200 == 0:   # Tăng từ 100 → 200 để giảm overhead time.time()
            if self.time_limit is not None and time.time() - self.start_time > self.time_limit:
                raise SearchTimeout()

    # Alpha-Beta
    # Alpha-Beta (Đã tối ưu: Move Ordering với TT-Move)
    def alpha_beta(self, board, depth, alpha, beta, is_maximizing, ply=0, use_pvs=True):
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

        self._check_timeout()

        result = board.check_win()
        if result == self.player_id:  return  1_000_000 - ply
        if result == self.opp_id:     return -1_000_000 + ply
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
            for i, move in enumerate(legal_moves):
                board.make_move(*move)
                
                if use_pvs and i > 0:
                    # Null Window Search: Giả định nước này tệ hơn alpha
                    val = self.alpha_beta(board, depth - 1, alpha, alpha + 1, False, ply + 1, True)
                    if alpha < val < beta:
                        # Fail-high: Tìm kiếm lại với cửa sổ đầy đủ
                        val = self.alpha_beta(board, depth - 1, val, beta, False, ply + 1, True)
                else:
                    # Tìm kiếm Alpha-Beta truyền thống (hoặc nước đầu tiên của PVS)
                    val = self.alpha_beta(board, depth - 1, alpha, beta, False, ply + 1, use_pvs)
                
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
            for i, move in enumerate(legal_moves):
                board.make_move(*move)
                
                if use_pvs and i > 0:
                    # Null Window Search cho phía Minimizing
                    val = self.alpha_beta(board, depth - 1, beta - 1, beta, True, ply + 1, True)
                    if alpha < val < beta:
                        val = self.alpha_beta(board, depth - 1, alpha, val, True, ply + 1, True)
                else:
                    val = self.alpha_beta(board, depth - 1, alpha, beta, True, ply + 1, use_pvs)

                board.undo_move()
                
                # [MỚI] Cập nhật best_move_found
                if val < best_score:
                    best_score = val
                    best_move_found = move
                    
                beta = min(beta, best_score)
                if beta <= alpha:
                    break

        flag = ("UPPER" if best_score <= alpha_orig
                else "LOWER" if best_score >= beta_orig
                else "EXACT")
                
        # [MỚI] Lưu best_move_found vào TT thay vì để None
        self.transposition_table[board_hash] = (depth, flag, best_score, best_move_found)
        return best_score
    # ──────────────────────────────────────────────────────────
    # Minimax thuần túy
    # ──────────────────────────────────────────────────────────
    def minimax(self, board, depth, is_maximizing, ply=0):
        self.nodes_visited += 1

        self._check_timeout()

        result = board.check_win()
        if result == self.player_id:  return  1_000_000 - ply
        if result == self.opp_id:     return -1_000_000 + ply
        if result == -1:              return  0
        if depth == 0:                return  self.heuristic(board)

        legal_moves = board.get_legal_moves()

        if is_maximizing:
            best = -math.inf
            for move in legal_moves:
                board.make_move(*move)
                best = max(best, self.minimax(board, depth - 1, False, ply + 1))
                board.undo_move()
            return best
        else:
            best = math.inf
            for move in legal_moves:
                board.make_move(*move)
                best = min(best, self.minimax(board, depth - 1, True, ply + 1))
                board.undo_move()
            return best

    # ──────────────────────────────────────────────────────────
    # Heuristic
    # ──────────────────────────────────────────────────────────
    def heuristic(self, board):
        """
        Lượng giá O(1): Trả về ngay lập tức điểm số đã được tính sẵn bởi bàn cờ.
        """
        # current_score được tính từ góc nhìn của Player 2 (O).
        # Nếu AI là Player 1 (X), ta cần đảo ngược dấu.
        if self.player_id == 1:
            return -board.current_score
        return board.current_score
