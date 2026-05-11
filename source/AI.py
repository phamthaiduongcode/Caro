import math
import numpy as np
import time

class CaroAI:
    def __init__(self, player_id, depth=3, defense_multiplier=1.45):
        self.player_id = player_id           # 1 (X) hoặc 2 (O)
        self.opp_id = 3 - player_id          # Đối thủ
        self.depth = depth
        self.defense_multiplier = defense_multiplier
        self.nodes_visited = 0
        self.center = 0

    def get_move(self, board, mode="alpha_beta"):
        """
        Hàm giao tiếp chính với GUI hoặc Benchmark.
        Trả về: (best_move, best_score, nodes_visited, time_taken)
        """
        self.nodes_visited = 0
        start_time = time.time()
        
        # Cập nhật ID người chơi theo trạng thái hiện tại của bàn cờ
        self.player_id = board.current_player
        self.opp_id = 3 - self.player_id
        self.center = board.size / 2
        
        best_score = -math.inf
        best_move = None
        
        legal_moves = board.get_legal_moves()
        # Move Ordering: Ưu tiên duyệt các nước đi gần trung tâm bàn cờ trước
        legal_moves.sort(key=lambda m: abs(m[0] - self.center) + abs(m[1] - self.center))
        
        if not legal_moves:
            return None, 0, 0, 0

        for move in legal_moves:
            board.make_move(*move)
            if mode == "minimax":
                score = self.minimax(board, self.depth - 1, False)
            else: # alpha_beta
                score = self.alpha_beta(board, self.depth - 1, -math.inf, math.inf, False)
            board.undo_move()
            
            if score > best_score:
                best_score = score
                best_move = move
                
        duration = time.time() - start_time
        return best_move, best_score, self.nodes_visited, duration

    def alpha_beta(self, board, depth, alpha, beta, is_maximizing):
        """Thuật toán Minimax với cắt tỉa Alpha-Beta (Level 2)."""
        self.nodes_visited += 1
        result = board.check_win()
        if result == self.player_id: return 1000000 + depth
        if result == self.opp_id: return -1000000 - depth
        if result == -1: return 0  # Hòa
        if depth == 0: return self.heuristic(board)

        legal_moves = board.get_legal_moves()

        if is_maximizing:
            max_eval = -math.inf
            for move in legal_moves:
                board.make_move(*move)
                val = self.alpha_beta(board, depth - 1, alpha, beta, False)
                board.undo_move()
                max_eval = max(max_eval, val)
                alpha = max(alpha, val)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = math.inf
            for move in legal_moves:
                board.make_move(*move)
                val = self.alpha_beta(board, depth - 1, alpha, beta, True)
                board.undo_move()
                min_eval = min(min_eval, val)
                beta = min(beta, val)
                if beta <= alpha:
                    break
            return min_eval

    def minimax(self, board, depth, is_maximizing):
        """Thuật toán Minimax thuần túy (Level 1)."""
        self.nodes_visited += 1
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
        """Trượt cửa sổ kích thước 4 để đếm quân và tính điểm (xét đầu mở)."""
        score = 0
        weights = [0, 10, 100, 1000, 10000]
        size = board.size
        grid = board.grid
        win_cond = 4 # Cố định 4 theo plan.md
        opp = 3 - player

        for r in range(size):
            for c in range(size):
                for dr, dc in board.DIRECTIONS:
                    # Kiểm tra cửa sổ nằm trong biên
                    end_r, end_c = r + (win_cond - 1) * dr, c + (win_cond - 1) * dc
                    if 0 <= end_r < size and 0 <= end_c < size:
                        p_count = 0
                        is_blocked = False
                        for i in range(win_cond):
                            val = grid[r + i * dr, c + i * dc]
                            if val == player: p_count += 1
                            elif val == opp:
                                is_blocked = True
                                break
                        
                        if not is_blocked and p_count > 0:
                            open_ends = 0
                            # Kiểm tra đầu mở phía trước
                            prev_r, prev_c = r - dr, c - dc
                            if 0 <= prev_r < size and 0 <= prev_c < size and grid[prev_r, prev_c] == 0:
                                open_ends += 1
                            # Kiểm tra đầu mở phía sau
                            next_r, next_c = end_r + dr, end_c + dc
                            if 0 <= next_r < size and 0 <= next_c < size and grid[next_r, next_c] == 0:
                                open_ends += 1
                            
                            # Áp dụng hệ số cho đầu mở
                            multiplier = 1.0
                            if open_ends == 2 and p_count >= 2: multiplier = 2.5
                            elif open_ends == 1: multiplier = 1.5
                            
                            score += weights[p_count] * multiplier
        return score