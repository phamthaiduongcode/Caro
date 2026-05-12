"""
train.py - Tối ưu weights heuristic bằng Self-Play (Phiên bản Hoàn Hảo)
Kết hợp: (1+1) Evolution Strategy + Khai cuộc ngẫu nhiên + Double Round Robin
Giao diện: Trực quan, hiển thị FULL trọng số.
"""

import csv
import os
import copy
import time
import random
import sys

# Đảm bảo Python tìm thấy module source
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from board import Board
from AI import CaroAI

# ── Cấu hình train ───────────────────────────────────────────
BOARD_SIZE      = 9
AI_DEPTH        = 3        
ROUNDS_PER_CAND = 2        
NUM_CANDIDATES  = 5        
NUM_ROUNDS      = 50       
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE     = os.path.join(BASE_DIR, "results", "train_results.csv")

DEFAULT_WEIGHTS = {
    "_OOO_":          100_000,
    "OOO_":            10_000,
    "_OO_":             1_000,
    "OO_":                100,
    "_O_":                 10,
    "defense_multiplier": 1.2,
}

# ── AI có weights tùy chỉnh ──────────────────────────────────
class TunableAI(CaroAI):
    def __init__(self, player_id, weights, depth=AI_DEPTH):
        super().__init__(player_id=player_id, depth=depth,
                         defense_multiplier=weights["defense_multiplier"])
        self.weights = weights

    def calculate_player_score(self, board, player):
        score, size, grid, win_cond, opp, w = 0, board.size, board.grid, board.win_condition, 3 - player, self.weights
        for r in range(size):
            for c in range(size):
                for dr, dc in board.DIRECTIONS:
                    end_r, end_c = r + (win_cond - 1) * dr, c + (win_cond - 1) * dc
                    if not (0 <= end_r < size and 0 <= end_c < size): continue
                    p_count, is_blocked = 0, False
                    for i in range(win_cond):
                        val = grid[r + i * dr, c + i * dc]
                        if val == player: p_count += 1
                        elif val == opp: is_blocked = True; break
                    if is_blocked or p_count == 0: continue
                    open_ends = 0
                    prev_r, prev_c = r - dr, c - dc
                    if 0 <= prev_r < size and 0 <= prev_c < size and grid[prev_r, prev_c] == 0: open_ends += 1
                    next_r, next_c = end_r + dr, end_c + dc
                    if 0 <= next_r < size and 0 <= next_c < size and grid[next_r, next_c] == 0: open_ends += 1

                    if p_count == 3: score += w["_OOO_"] if open_ends == 2 else w["OOO_"]
                    elif p_count == 2: score += w["_OO_"] if open_ends == 2 else w["OO_"]
                    elif p_count == 1: score += w["_O_"] if open_ends == 2 else 1
        return score

# ── Hàm Hỗ Trợ ───────────────────────────────────────────────
def mutate_weights(base_weights, scale=0.3):
    new_w = {}
    for key, val in base_weights.items():
        if key == "defense_multiplier":
            new_w[key] = round(max(0.8, min(2.0, val + random.uniform(-scale, scale))), 3)
        else:
            new_w[key] = max(1, int(val * random.uniform(1 - scale, 1 + scale)))
    return new_w

def generate_random_start(size=BOARD_SIZE, moves=3):
    start_moves = []
    temp_board = Board(size)
    for _ in range(moves):
        r, c = random.randint(2, size-3), random.randint(2, size-3)
        if temp_board.make_move(r, c): start_moves.append((r, c))
    return start_moves

# ---> ĐÃ CẬP NHẬT: Hiển thị đầy đủ toàn bộ trọng số <---
def format_weights(w):
    return (f"Def: {w['defense_multiplier']:.2f} | "
            f"_OOO_: {w['_OOO_']:,} | OOO_: {w['OOO_']:,} | "
            f"_OO_: {w['_OO_']:,} | OO_: {w['OO_']:,} | _O_: {w['_O_']:,}")

def save_result(round_num, weights, score, duration):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Round", "Score", "Duration_s", "_OOO_", "OOO_", "_OO_", "OO_", "_O_", "defense_multiplier"])
        writer.writerow([round_num, score, f"{duration:.2f}", weights["_OOO_"], weights["OOO_"], weights["_OO_"], weights["OO_"], weights["_O_"], f"{weights['defense_multiplier']:.3f}"])

# ── Đánh giá bằng Double Round Robin & Khai cuộc ngẫu nhiên ──
def evaluate(candidate_weights, best_weights, rounds=ROUNDS_PER_CAND):
    stats = {'X_win': 0, 'X_draw': 0, 'X_loss': 0, 'O_win': 0, 'O_draw': 0, 'O_loss': 0, 'score': 0.0}

    for _ in range(rounds):
        start_moves = generate_random_start()

        for p1_is_candidate in [True, False]:
            board = Board(BOARD_SIZE)
            for r, c in start_moves: board.make_move(r, c)
            
            cid = board.current_player if p1_is_candidate else 3 - board.current_player
            bid = 3 - cid
            ai_cand = TunableAI(player_id=cid, weights=candidate_weights)
            ai_best = TunableAI(player_id=bid, weights=best_weights)

            while board.check_win() == 0:
                curr_ai = ai_cand if board.current_player == cid else ai_best
                move, _, _, _ = curr_ai.get_move(board, mode="alpha_beta", time_limit=0.2)
                if not move: break
                board.make_move(*move)
            
            res = board.check_win()

            if p1_is_candidate: 
                if res == cid: stats['X_win'] += 1; stats['score'] += 1.0
                elif res == 0: stats['X_draw'] += 1
                else:          stats['X_loss'] += 1
            else:               
                if res == cid: stats['O_win'] += 1; stats['score'] += 1.5
                elif res == 0: stats['O_draw'] += 1; stats['score'] += 1.0
                else:          stats['O_loss'] += 1

    return stats

# ── Vòng lặp train chính ─────────────────────────────────────
def train():
    print("\n" + "═" * 85)
    print("      HUẤN LUYỆN AI CARO - (1+1) EVOLUTION STRATEGY")
    print("      Core: Khai cuộc ngẫu nhiên & Double Round Robin")
    print("      Logic: Cầm X phải Thắng (+1), Cầm O cần Hòa (+1)")
    print("═" * 85)

    best_weights = copy.deepcopy(DEFAULT_WEIGHTS)
    print(f"\n[TRỌNG SỐ GỐC] {format_weights(best_weights)}")

    for round_num in range(1, NUM_ROUNDS + 1):
        print("\n" + "─" * 85)
        print(f" VÒNG {round_num}/{NUM_ROUNDS} | Đang tìm kiếm đột biến...")
        print("─" * 85)
        
        round_start        = time.time()
        round_best_score   = -1
        round_best_weights = None
        round_best_stats   = None

        for i in range(NUM_CANDIDATES):
            candidate = mutate_weights(best_weights)
            stats = evaluate(candidate, best_weights)
            
            print(f"\n  [Candidate {i+1}] {format_weights(candidate)}")
            print(f"   ├─ Tấn công (Cầm phe X): Thắng {stats['X_win']} | Hòa {stats['X_draw']} | Thua {stats['X_loss']}")
            print(f"   ├─ Phòng ngự (Cầm phe O): Thắng {stats['O_win']} | Hòa {stats['O_draw']} | Thua {stats['O_loss']}")
            print(f"   └─ TỔNG ĐIỂM: {stats['score']:.1f}")

            if stats['score'] > round_best_score:
                round_best_score   = stats['score']
                round_best_weights = candidate
                round_best_stats   = stats

        duration = time.time() - round_start

        if round_best_score > ROUNDS_PER_CAND: 
            best_weights = round_best_weights
            print("\n  >>> KẾT QUẢ VÒNG: BỘ TRỌNG SỐ MỚI ĐÃ ĐƯỢC CHỌN! <<<")
        else:
            print(f"\n  >>> KẾT QUẢ VÒNG: Không có Candidate nào đủ tốt (Max: {round_best_score:.1f}). Giữ bộ cũ. <<<")

        save_result(round_num, best_weights, round_best_score, duration)
        print(f"  [Trọng số hiện tại] {format_weights(best_weights)}")

    print("\n" + "═" * 85)
    print("  HUẤN LUYỆN HOÀN TẤT!")
    print(f"  Kết quả chi tiết được lưu tại: {OUTPUT_FILE}")
    print("═" * 85)

if __name__ == "__main__":
    train()