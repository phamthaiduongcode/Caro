import math
import numpy as np
import time

class SearchTimeout(Exception):
    """Ngoại lệ tùy chỉnh để dừng tìm kiếm khi hết thời gian."""
    pass

class CaroAI:
    def __init__(self, player_id, depth=3, defense_multiplier=2):
        self.player_id = player_id           # 1 (X) hoặc 2 (O)
        self.opp_id = 3 - player_id          # Đối thủ
        self.depth = depth
        self.defense_multiplier = defense_multiplier
        self.nodes_visited = 0
        self.center = 0
        self.start_time = 0
        self.time_limit = 0
        self.transposition_table = {}

    def get_move(self, board, mode="alpha_beta", time_limit=8.0):
        """
        Hàm giao tiếp chính với GUI hoặc Benchmark, hỗ trợ Iterative Deepening.
        Trả về: (best_move, best_score, nodes_visited, time_taken)
        """
        self.nodes_visited = 0
        self.start_time = time.time()
        self.time_limit = time_limit
        self.transposition_table = {} # Clear TT at the start of each search
        
        # Cập nhật ID người chơi theo trạng thái hiện tại của bàn cờ
        self.player_id = board.current_player
        self.opp_id = 3 - self.player_id
        # Bug 2 Fix: Sử dụng chia lấy nguyên để tránh sai số float và tối ưu hiệu suất
        self.center = board.size // 2
        
        legal_moves = board.get_legal_moves()
        if not legal_moves:
            return None, 0, 0, 0

        # Move Ordering: Ưu tiên duyệt các nước đi gần trung tâm bàn cờ trước
        legal_moves.sort(key=lambda m: abs(m[0] - self.center) + abs(m[1] - self.center))

        # Bug 1 Fix: Gán nước đi dự phòng là nước tốt nhất (gần tâm nhất) 
        # để tránh trả về None nếu timeout xảy ra ngay ở độ sâu 1.
        final_best_move = legal_moves[0]
        final_best_score = -math.inf

        # Bug 2: Nếu không có time_limit (benchmark), chạy thẳng ở độ sâu self.depth
        search_range = [self.depth] if self.time_limit is None else range(1, self.depth + 1)

        for current_depth in search_range:
            depth_best_move = None
            depth_best_score = -math.inf
            
            try:
                for move in legal_moves:
                    # Bug 1: Kiểm tra time_limit trước khi so sánh
                    if self.time_limit is not None and time.time() - self.start_time > self.time_limit:
                        raise SearchTimeout()

                    board.make_move(*move)
                    if mode == "minimax":
                        score = self.minimax(board, current_depth - 1, False)
                    else: # alpha_beta
                        score = self.alpha_beta(board, current_depth - 1, -math.inf, math.inf, False)
                    board.undo_move()
                    
                    if score > depth_best_score:
                        depth_best_score = score
                        depth_best_move = move
                
                # Chỉ cập nhật kết quả cuối cùng khi đã hoàn thành trọn vẹn một độ sâu
                final_best_move = depth_best_move
                final_best_score = depth_best_score
                
                # Cập nhật Move Ordering: Đưa nước đi tốt nhất vừa tìm được lên đầu 
                # để tối ưu hóa việc cắt tỉa Alpha-Beta ở độ sâu (depth) tiếp theo.
                if final_best_move in legal_moves:
                    legal_moves.remove(final_best_move)
                    legal_moves.insert(0, final_best_move)

                # Nếu tìm thấy nước đi thắng tuyệt đối, ngừng tìm kiếm sâu hơn
                if final_best_score >= 1000000:
                    break
            except SearchTimeout:
                # Hết thời gian: Dừng tìm kiếm và trả về kết quả từ độ sâu hoàn thành gần nhất
                break
                
        duration = time.time() - self.start_time
        return final_best_move, final_best_score, self.nodes_visited, duration

    def alpha_beta(self, board, depth, alpha, beta, is_maximizing):
        """Thuật toán Minimax với cắt tỉa Alpha-Beta (Level 2)."""
        self.nodes_visited += 1

        # Tra cứu transposition table
        board_hash = board.get_hash()
        alpha_orig, beta_orig = alpha, beta
        if board_hash in self.transposition_table:
            tt_depth, tt_flag, tt_val, _ = self.transposition_table[board_hash]
            if tt_depth >= depth:
                if tt_flag == "EXACT": return tt_val
                elif tt_flag == "LOWER": alpha = max(alpha, tt_val)
                elif tt_flag == "UPPER": beta = min(beta, tt_val)
                if alpha >= beta: return tt_val
        
        # Kiểm tra giới hạn thời gian (kiểm tra mỗi 100 node để giảm overhead)
        if self.nodes_visited % 100 == 0:
            if self.time_limit is not None and time.time() - self.start_time > self.time_limit:
                raise SearchTimeout()

        result = board.check_win()
        if result == self.player_id: return 1000000 + depth
        if result == self.opp_id: return -1000000 - depth
        if result == -1: return 0  # Hòa
        if depth == 0: return self.heuristic(board)

        legal_moves = board.get_legal_moves()

        if is_maximizing:
            best_score = -math.inf
            for move in legal_moves:
                board.make_move(*move)
                val = self.alpha_beta(board, depth - 1, alpha, beta, False)
                board.undo_move()
                best_score = max(best_score, val)
                alpha = max(alpha, val)
                if beta <= alpha:
                    break
        else:
            best_score = math.inf
            for move in legal_moves:
                board.make_move(*move)
                val = self.alpha_beta(board, depth - 1, alpha, beta, True)
                board.undo_move()
                best_score = min(best_score, val)
                beta = min(beta, val)
                if beta <= alpha:
                    break

        # Lưu vào transposition table
        flag = "UPPER" if best_score <= alpha_orig else ("LOWER" if best_score >= beta_orig else "EXACT")
        self.transposition_table[board_hash] = (depth, flag, best_score, None)
        return best_score

    def minimax(self, board, depth, is_maximizing):
        """Thuật toán Minimax thuần túy (Level 1)."""
        self.nodes_visited += 1
        
        if self.nodes_visited % 100 == 0:
            if self.time_limit is not None and time.time() - self.start_time > self.time_limit:
                raise SearchTimeout()

        result = board.check_win()
        if result == self.player_id: return 1000000 + depth
        if result == self.opp_id: return -1000000 - depth
        if result == -1: return 0
        if depth == 0: return self.heuristic(board)

        legal_moves = board.get_legal_moves()

        if is_maximizing:
            max_eval = -math.inf
            for move in legal_moves:
                board.make_move(*move)
                val = self.minimax(board, depth - 1, False)
                board.undo_move()
                max_eval = max(max_eval, val)
            return max_eval
        else:
            min_eval = math.inf
            for move in legal_moves:
                board.make_move(*move)
                val = self.minimax(board, depth - 1, True)
                board.undo_move()
                min_eval = min(min_eval, val)
            return min_eval

    def heuristic(self, board):
        """Hàm đánh giá cục diện bàn cờ."""
        ai_score = self.calculate_player_score(board, self.player_id)
        opp_score = self.calculate_player_score(board, self.opp_id)
        
        # Tính điểm AI − defense_multiplier × điểm đối thủ
        return ai_score - (self.defense_multiplier * opp_score)

    def calculate_player_score(self, board, player):
        """
        Đánh giá theo pattern cụ thể thay vì dùng weights tuyến tính.
        
        Thang điểm phản ánh mức độ nguy hiểm thực tế:
          _OOO_  (open-three)      → 100,000  (gần thắng chắc)
          OOO_   (half-open-three) →  10,000  (mối đe dọa mạnh)
          _OO_   (open-two)        →   1,000
          OO_    (half-open-two)   →     100
          _O_    (single, 2 đầu)   →      10
        """
        score = 0
        size     = board.size
        grid     = board.grid
        win_cond = board.win_condition
        opp      = 3 - player

        for r in range(size):
            for c in range(size):
                for dr, dc in board.DIRECTIONS:
                    end_r = r + (win_cond - 1) * dr
                    end_c = c + (win_cond - 1) * dc
                    if not (0 <= end_r < size and 0 <= end_c < size):
                        continue

                    p_count    = 0
                    is_blocked = False
                    for i in range(win_cond):
                        val = grid[r + i * dr, c + i * dc]
                        if val == player:
                            p_count += 1
                        elif val == opp:
                            is_blocked = True
                            break

                    if is_blocked or p_count == 0:
                        continue

                    # Đếm đầu mở
                    open_ends = 0
                    prev_r, prev_c = r - dr, c - dc
                    if 0 <= prev_r < size and 0 <= prev_c < size \
                            and grid[prev_r, prev_c] == 0:
                        open_ends += 1
                    next_r, next_c = end_r + dr, end_c + dc
                    if 0 <= next_r < size and 0 <= next_c < size \
                            and grid[next_r, next_c] == 0:
                        open_ends += 1

                    
                    # ── Gán điểm theo pattern ──
                    if p_count == 3:
                        if open_ends == 2:
                            score += 	19680     # Thế _OOO_
                        elif open_ends == 1:
                            score += 23437    # Thế OOO_
                    elif p_count == 2:
                        if open_ends == 2:
                            score += 750       # Thế _OO_
                        elif open_ends == 1:
                            score += 19        # Thế OO_
                    elif p_count == 1:
                        if open_ends == 2:
                            score += 1         # Thế _O_
                        else:
                            score += 1

        return score