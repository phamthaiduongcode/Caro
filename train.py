"""
train.py - Tối ưu weights heuristic và defense_multiplier bằng self-play
Hai AI đấu nhau, bộ tham số nào thắng nhiều hơn sẽ được giữ lại.
Kết quả lưu vào results/train_results.csv
"""

import csv
import os
import copy
import time
import random
from source.board import Board
from source.AI import CaroAI

# ── Cấu hình train ───────────────────────────────────────────
BOARD_SIZE      = 10
AI_DEPTH        = 1
GAMES_PER_PAIR  = 4        # Số ván mỗi cặp tham số (chơi cả 2 bên X và O)
NUM_CANDIDATES  = 8        # Số bộ tham số thử mỗi vòng
NUM_ROUNDS      = 5        # Số vòng train
OUTPUT_FILE     = "results/train_results.csv"

DEFAULT_WEIGHTS = {
    "open_three":          100_000,
    "half_open_three":      10_000,
    "open_two":              1_000,
    "half_open_two":           100,
    "single":                   10,
    "defense_multiplier":      1.2,
}


# ── AI có weights tùy chỉnh ──────────────────────────────────
class TunableAI(CaroAI):
    def __init__(self, player_id, weights, depth=AI_DEPTH):
        super().__init__(player_id=player_id, depth=depth,
                         defense_multiplier=weights["defense_multiplier"])
        self.weights = weights

    def calculate_player_score(self, board, player):
        score    = 0
        size     = board.size
        grid     = board.grid
        win_cond = board.win_condition
        opp      = 3 - player
        w        = self.weights

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

                    open_ends = 0
                    prev_r, prev_c = r - dr, c - dc
                    if 0 <= prev_r < size and 0 <= prev_c < size \
                            and grid[prev_r, prev_c] == 0:
                        open_ends += 1
                    next_r, next_c = end_r + dr, end_c + dc
                    if 0 <= next_r < size and 0 <= next_c < size \
                            and grid[next_r, next_c] == 0:
                        open_ends += 1

                    if p_count == 3:
                        if open_ends == 2:   score += w["open_three"]
                        elif open_ends == 1: score += w["half_open_three"]
                    elif p_count == 2:
                        if open_ends == 2:   score += w["open_two"]
                        elif open_ends == 1: score += w["half_open_two"]
                    elif p_count == 1:
                        if open_ends == 2:   score += w["single"]
                        else:                score += 1

        return score


# ── Sinh bộ weights đột biến ─────────────────────────────────
def mutate_weights(base_weights, scale=0.3):
    """Tạo bộ weights mới bằng cách biến đổi ngẫu nhiên từ base."""
    new_w = {}
    for key, val in base_weights.items():
        if key == "defense_multiplier":
            delta      = random.uniform(-scale, scale)
            new_w[key] = round(max(0.8, min(2.0, val + delta)), 3)
        else:
            factor     = random.uniform(1 - scale, 1 + scale)
            new_w[key] = max(1, int(val * factor))
    return new_w


# ── Chơi 1 ván ───────────────────────────────────────────────
def play_game(ai1, ai2, board_size=BOARD_SIZE, max_moves=150):
    """
    ai1 là X (player 1), ai2 là O (player 2).
    Trả về: 1 nếu ai1 thắng, 2 nếu ai2 thắng, 0 nếu hòa.
    """
    board         = Board(board_size)
    ai1.player_id = 1
    ai1.opp_id    = 2
    ai2.player_id = 2
    ai2.opp_id    = 1

    for _ in range(max_moves):
        current_ai    = ai1 if board.current_player == 1 else ai2
        move, _, _, _ = current_ai.get_move(board, mode="alpha_beta", time_limit=5.0)
        if move is None:
            break
        board.make_move(*move)
        result = board.check_win()
        if result == 1:  return 1
        if result == 2:  return 2
        if result == -1: return 0
    return 0


# ── Đánh giá 1 bộ weights ────────────────────────────────────
def evaluate(candidate_weights, best_weights, games=GAMES_PER_PAIR):
    """
    Chơi xen kẽ X/O để công bằng.
    Trả về số ván thắng của candidate.
    """
    wins = 0
    for i in range(games):
        if i % 2 == 0:
            ai_cand = TunableAI(player_id=1, weights=candidate_weights)
            ai_best = TunableAI(player_id=2, weights=best_weights)
            result  = play_game(ai_cand, ai_best)
            if result == 1: wins += 1
        else:
            ai_best = TunableAI(player_id=1, weights=best_weights)
            ai_cand = TunableAI(player_id=2, weights=candidate_weights)
            result  = play_game(ai_best, ai_cand)
            if result == 2: wins += 1
    return wins


# ── Ghi CSV ──────────────────────────────────────────────────
def save_result(round_num, weights, wins, total_games, duration):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "Round", "Wins", "Total_Games", "Duration_s",
                "open_three", "half_open_three", "open_two",
                "half_open_two", "single", "defense_multiplier"
            ])
        writer.writerow([
            round_num, wins, total_games, f"{duration:.2f}",
            weights["open_three"], weights["half_open_three"],
            weights["open_two"], weights["half_open_two"],
            weights["single"], f"{weights['defense_multiplier']:.3f}"
        ])


# ── Vòng lặp train chính ─────────────────────────────────────
def train():
    print("=" * 55)
    print("  SELF-PLAY TRAINING — Tối ưu weights & defense")
    print("=" * 55)

    best_weights = copy.deepcopy(DEFAULT_WEIGHTS)
    print(f"\nWeights ban đầu: {best_weights}\n")

    for round_num in range(1, NUM_ROUNDS + 1):
        print(f"── Vòng {round_num}/{NUM_ROUNDS} ──────────────────────────")
        round_start        = time.time()
        round_best_wins    = -1
        round_best_weights = None

        for i in range(NUM_CANDIDATES):
            candidate = mutate_weights(best_weights)
            wins      = evaluate(candidate, best_weights)
            print(f"  Candidate {i+1:2d}: wins={wins}/{GAMES_PER_PAIR} | "
                  f"def={candidate['defense_multiplier']:.2f} | "
                  f"o3={candidate['open_three']:,}")

            if wins > round_best_wins:
                round_best_wins    = wins
                round_best_weights = candidate

        duration = time.time() - round_start

        # Cập nhật nếu candidate thắng >= một nửa số ván
        if round_best_wins >= GAMES_PER_PAIR // 2:
            best_weights = round_best_weights
            print(f"\n  ✓ Cập nhật weights mới (thắng {round_best_wins}/{GAMES_PER_PAIR})")
        else:
            print(f"\n  → Giữ nguyên weights cũ (tốt nhất: {round_best_wins}/{GAMES_PER_PAIR})")

        save_result(round_num, best_weights, round_best_wins, GAMES_PER_PAIR, duration)
        print(f"  Thời gian vòng: {duration:.1f}s")
        print(f"  Weights hiện tại: {best_weights}\n")

    print("=" * 55)
    print("  TRAIN HOÀN TẤT")
    print(f"  Kết quả lưu tại: {OUTPUT_FILE}")
    print(f"  Weights tốt nhất: {best_weights}")
    print("=" * 55)
    return best_weights


if __name__ == "__main__":
    train()