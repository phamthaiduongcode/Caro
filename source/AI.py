import math
import time
import random
from source.utils import log_ai_move

class SearchTimeout(Exception):
    """Ngoại lệ tùy chỉnh để dừng tìm kiếm khi hết thời gian."""
    pass

class CaroAI:
    def __init__(self, player_id, depth):
        """
        Args:
            player_id: 1 (X) hoặc 2 (O)
            depth:     độ sâu tìm kiếm tối đa
        """
        self.player_id = player_id
        self.opp_id    = 3 - player_id
        self.depth     = depth

        self.nodes_visited     = 0
        self.start_time        = 0
        self.time_limit        = 0
        self.transposition_table = {}  # Khởi tạo một lần duy nhất tại __init__

    def _get_opening_move(self, board):
        """
        Xử lý khai cuộc cứng cho 2 nước đầu tiên.
        Trả về (row, col) nếu đang ở giai đoạn khai cuộc, ngược lại trả về None.
        """
        moves_made = len(board.history)
        ctr = board.size // 2

        # Trường hợp 1: AI được đi nước đầu tiên (AI là X)
        if moves_made == 0:
            return (ctr, ctr)

        # Trường hợp 2: AI đi nước thứ 2 (AI là O, đáp trả nước đầu của X)
        if moves_made == 1:
            x_row, x_col, _ = board.history[0]
            # 8 vị trí bao quanh quân X vừa đánh
            standard_replies = [
                (x_row - 1, x_col), (x_row + 1, x_col), (x_row, x_col - 1), (x_row, x_col + 1),       # Direct
                (x_row - 1, x_col - 1), (x_row - 1, x_col + 1), (x_row + 1, x_col - 1), (x_row + 1, x_col + 1) # Indirect
            ]
            # Lọc ra các ô hợp lệ (không bị lọt ra ngoài bàn cờ)
            valid_replies = [(r, c) for r, c in standard_replies 
                             if 0 <= r < board.size and 0 <= c < board.size]
            if valid_replies:
                return random.choice(valid_replies)
        return None

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
        
        # Kiểm tra kích thước TT để tránh tràn RAM (giới hạn 1 triệu entry)
        if len(self.transposition_table) > 1_000_000:
            self.transposition_table.clear()

        self.player_id = board.current_player
        self.opp_id    = 3 - self.player_id

        # 1. KIỂM TRA OPENING BOOK TRƯỚC TIÊN
        opening_move = self._get_opening_move(board)
        if opening_move is not None:
            duration = time.time() - self.start_time
            if log_path:
                try:
                    log_ai_move(log_path, [
                        'X' if self.player_id == 1 else 'O', str(opening_move),
                        0, 0, round(duration, 4), 0
                    ])
                except: pass
            return opening_move, 0, 0, duration

        legal_moves = board.get_legal_moves()
        if not legal_moves:
            return None, 0, 0, 0

        # get_legal_moves() đã sort theo priority (nước thắng=3, nước chặn=2, thường=0).
        # KHÔNG sort lại theo center — làm vậy sẽ xóa mất ordering tốt đó.
        # Center bonus đã được tính trong heuristic() nên không cần ưu tiên ở đây.

        # BƯỚC 0: Kiểm tra nước thắng ngay (depth=1)
        for move in legal_moves:
            if board.fast_check_win(move[0], move[1], self.player_id):
                duration = time.time() - self.start_time
                if log_path:
                    try:
                        log_ai_move(log_path, [
                            'X' if self.player_id == 1 else 'O', str(move),
                            1000000, 1, round(duration, 4), 1
                        ])
                    except: pass
                return move, 1_000_000, 1, duration # ply=0 win

        # BƯỚC 0.5: Chặn đối thủ thắng ngay (Bắt buộc phải chặn trước khi nghĩ đến Fork)
        for move in legal_moves:
            if board.fast_check_win(move[0], move[1], self.opp_id):
                duration = time.time() - self.start_time
                if log_path:
                    try:
                        log_ai_move(log_path, [
                            'X' if self.player_id == 1 else 'O', str(move),
                            950000, 1, round(duration, 4), 1
                        ])
                    except: pass
                return move, 950_000, 1, duration

        final_best_move  = legal_moves[0]
        final_best_score = -math.inf

        achieved_depth = 0
        root_beta = math.inf

        # Nếu time_limit=None → chạy đúng self.depth (dùng cho training)
        # Sửa: Chỉ dùng Depth chẵn để tránh Horizon Effect (2, 4)
        search_range = [self.depth] if self.time_limit is None else range(2, self.depth + 2, 2)

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

    # ──────────────────────────────────────────────────────────
    # Alpha-Beta
    # ──────────────────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────
    # Alpha-Beta (Đã tối ưu: Move Ordering với TT-Move)
    # ──────────────────────────────────────────────────────────
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
                
        # [SỬA LỖI] Chỉ ghi đè nếu kết quả mới có độ sâu tính toán lớn hơn hoặc bằng kết quả cũ
        if (board_hash not in self.transposition_table or 
            depth >= self.transposition_table[board_hash][0]):
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