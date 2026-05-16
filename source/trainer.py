"""
trainer.py — Genetic Algorithm để tối ưu trọng số heuristic cho CaroAI

Cách chạy:
    python source/trainer.py                      # GA đầy đủ (mặc định)
    python source/trainer.py --quick              # Chạy nhanh để test
    python source/trainer.py --workers 4          # Dùng 4 CPU cores

Kết quả best weights được lưu vào: logs/best_weights.json
"""

import sys
import os
import json
import random
import copy
import time
import argparse
import multiprocessing as mp
from multiprocessing import Pool

# Đảm bảo import được từ source/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from source.board import Board
from source.AI import CaroAI, DEFAULT_WEIGHTS


# ─────────────────────────────────────────────────────────────
# Cấu hình GA
# ─────────────────────────────────────────────────────────────
GA_CONFIG = {
    # Kích thước quần thể
    "population_size": 24,

    # Số thế hệ
    "generations": 38,

    # Số elite giữ nguyên sang thế hệ kế tiếp (không mutation)
    "elite_k": 4,

    # Số đối thủ ngẫu nhiên mỗi agent đấu với trong 1 generation
    "opponents_per_agent": 6,

    # Số ván đấu mỗi cặp (nên là số chẵn để cân bằng lượt X/O)
    "games_per_pair": 2,

    # Depth khi training — depth=2 nhanh hơn ~10x so với depth=3
    # Sau khi train xong, weights vẫn dùng tốt ở depth=3
    "train_depth": 2,

    # Xác suất mutation mỗi gene
    "mutation_rate": 0.20,

    # Biên độ mutation: weight *= uniform(1 - strength, 1 + strength)
    "mutation_strength": 0.30,

    # Tỷ lệ agent khởi tạo ngẫu nhiên hoàn toàn (tăng diversity)
    "random_init_ratio": 0.25,
}

# Các key cần tối ưu (bỏ defense_mult và center_bonus cũng có thể tune)
PARAM_KEYS = [
    "open3", "half3", "broken4",
    "open2", "half2", "broken3",
    "open1", "defense_mult", "center_bonus",
]

# Khoảng tìm kiếm hợp lý cho từng tham số
PARAM_BOUNDS = {
    "open3":        (20_000,   300_000),
    "half3":        ( 2_000,    80_000),
    "broken4":      (20_000,   200_000),
    "open2":        (   200,    10_000),
    "half2":        (    20,     2_000),
    "broken3":      (   500,    20_000),
    "open1":        (     2,       100),
    "defense_mult": (  0.80,      1.60),
    "center_bonus": (     0,       150),
}


# ─────────────────────────────────────────────────────────────
# Khởi tạo agent
# ─────────────────────────────────────────────────────────────
def random_agent():
    """Agent với trọng số ngẫu nhiên trong khoảng hợp lý."""
    return {k: random.uniform(*PARAM_BOUNDS[k]) for k in PARAM_KEYS}


def baseline_agent():
    """Agent khởi tạo từ DEFAULT_WEIGHTS (điểm xuất phát tốt)."""
    return {k: DEFAULT_WEIGHTS[k] for k in PARAM_KEYS}


def perturbed_agent(base=None, strength=0.2):
    """Agent từ baseline có nhiễu nhỏ — tốt hơn random hoàn toàn."""
    base = base or DEFAULT_WEIGHTS
    agent = {}
    for k in PARAM_KEYS:
        lo, hi = PARAM_BOUNDS[k]
        v = base[k] * random.uniform(1 - strength, 1 + strength)
        agent[k] = max(lo, min(hi, v))
    return agent


# ─────────────────────────────────────────────────────────────
# Genetic operators
# ─────────────────────────────────────────────────────────────
def crossover(parent_a, parent_b):
    """Uniform crossover: mỗi gene chọn ngẫu nhiên từ 1 trong 2 cha mẹ."""
    return {
        k: parent_a[k] if random.random() < 0.5 else parent_b[k]
        for k in PARAM_KEYS
    }


def mutate(agent, rate=0.20, strength=0.30):
    """Gaussian-like mutation: nhân mỗi gene với hệ số ngẫu nhiên."""
    w = copy.deepcopy(agent)
    for k in PARAM_KEYS:
        if random.random() < rate:
            lo, hi = PARAM_BOUNDS[k]
            w[k] *= random.uniform(1 - strength, 1 + strength)
            w[k]  = max(lo, min(hi, w[k]))
    return w


# ─────────────────────────────────────────────────────────────
# Thi đấu
# ─────────────────────────────────────────────────────────────
def play_one_game(weights_x, weights_o, board_size=9, depth=2):
    """
    Cho 2 agent đấu 1 ván.
    Agent X = weights_x, Agent O = weights_o
    Trả về: 1 nếu X thắng, 2 nếu O thắng, 0 nếu hòa
    """
    board = Board(board_size, win_condition=4)
    agents = {
        1: CaroAI(player_id=1, depth=depth, weights=copy.deepcopy(weights_x)),
        2: CaroAI(player_id=2, depth=depth, weights=copy.deepcopy(weights_o)),
    }
    max_moves = board_size * board_size

    for _ in range(max_moves):
        pid  = board.current_player
        move, _, _, _ = agents[pid].get_move(board, mode="alpha_beta", time_limit=None)
        if move is None:
            return 0
        board.make_move(*move)
        result = board.check_win()
        if result in (1, 2):
            return result
        if result == -1:
            return 0

    return 0  # Hòa do hết bàn


def evaluate_pair(args):
    """
    Wrapper cho multiprocessing.
    Đánh 2 ván cân bằng (1 ván đóng vai X, 1 ván đóng vai O).
    Trả về (wins_a, wins_b, draws).
    """
    weights_a, weights_b, depth = args
    wins_a = wins_b = draws = 0

    # Ván 1: A đánh X
    r1 = play_one_game(weights_a, weights_b, depth=depth)
    if r1 == 1:   wins_a += 1
    elif r1 == 2: wins_b += 1
    else:          draws  += 1

    # Ván 2: A đánh O
    r2 = play_one_game(weights_b, weights_a, depth=depth)
    if r2 == 1:   wins_b += 1
    elif r2 == 2: wins_a += 1
    else:          draws  += 1

    return wins_a, wins_b, draws


# ─────────────────────────────────────────────────────────────
# Đánh giá fitness toàn quần thể
# ─────────────────────────────────────────────────────────────
def evaluate_population(population, config, n_workers=1):
    """
    Mỗi agent đấu với opponents_per_agent đối thủ ngẫu nhiên.
    Fitness = win_rate ∈ [0, 1]
    Dùng multiprocessing nếu n_workers > 1.
    """
    pop_size     = len(population)
    opp_k        = min(config["opponents_per_agent"], pop_size - 1)
    depth        = config["train_depth"]

    # Xây dựng danh sách các trận đấu — mỗi cặp {i, j} chỉ xuất hiện 1 lần.
    # evaluate_pair đã tự chơi cả 2 chiều (A=X và A=O) nên dedup là đúng.
    # Nếu để cả (i,j) lẫn (j,i), cặp đó đấu 4 ván thay vì 2 → skew fitness.
    seen       = set()
    match_list = []
    for i in range(pop_size):
        opponents = random.sample([j for j in range(pop_size) if j != i], k=opp_k)
        for j in opponents:
            pair = (min(i, j), max(i, j))   # canonical key để dedup
            if pair not in seen:
                seen.add(pair)
                match_list.append((i, j))   # i = "agent A" trong evaluate_pair

    # Tạo args cho từng trận
    args_list = [
        (population[i], population[j], depth)
        for i, j in match_list
    ]

    # Chạy các trận đấu
    if n_workers > 1:
        with Pool(processes=n_workers) as pool:
            results = pool.map(evaluate_pair, args_list)
    else:
        results = [evaluate_pair(a) for a in args_list]

    # Tổng hợp điểm
    wins  = [0] * pop_size
    total = [0] * pop_size

    for (i, j), (wa, wb, _) in zip(match_list, results):
        wins[i]  += wa
        wins[j]  += wb
        total[i] += 2   # mỗi evaluate_pair chơi 2 ván
        total[j] += 2

    fitness = [
        wins[i] / total[i] if total[i] > 0 else 0.0
        for i in range(pop_size)
    ]
    return fitness


# ─────────────────────────────────────────────────────────────
# Vòng lặp GA chính
# ─────────────────────────────────────────────────────────────
def run_ga(config=None, n_workers=1, save_path="logs/best_weights.json",
           log_path="logs/training_log.csv"):
    if config is None:
        config = GA_CONFIG

    pop_size    = config["population_size"]
    generations = config["generations"]
    elite_k     = config["elite_k"]
    mut_rate    = config["mutation_rate"]
    mut_str     = config["mutation_strength"]
    rand_ratio  = config["random_init_ratio"]

    print("=" * 55)
    print("   CARO AI — GENETIC ALGORITHM TRAINER")
    print("=" * 55)
    print(f"  Population : {pop_size}")
    print(f"  Generations: {generations}")
    print(f"  Train depth: {config['train_depth']}")
    print(f"  Opponents  : {config['opponents_per_agent']} / agent")
    print(f"  CPU workers: {n_workers}")
    print(f"  Log CSV    : {log_path}")
    print("=" * 55)

    # ── Khởi tạo quần thể ──
    n_random   = max(1, int(pop_size * rand_ratio))
    n_perturb  = max(0, pop_size - n_random - 1)   # -1 cho baseline; guard âm
    population = (
        [baseline_agent()]
        + [perturbed_agent() for _ in range(n_perturb)]
        + [random_agent()    for _ in range(n_random)]
    )
    random.shuffle(population)

    best_ever  = None
    best_score = -1.0
    history    = []   # (gen, best_fitness, avg_fitness)

    for gen in range(1, generations + 1):
        t0      = time.time()
        fitness = evaluate_population(population, config, n_workers)
        elapsed = time.time() - t0

        avg_f = sum(fitness) / len(fitness)
        max_f = max(fitness)
        best_idx = fitness.index(max_f)

        if max_f > best_score:
            best_score = max_f
            best_ever  = copy.deepcopy(population[best_idx])
            _save_weights(best_ever, best_score, gen, save_path)

        history.append((gen, max_f, avg_f))
        print(f"Gen {gen:3d}/{generations} | "
              f"Best: {max_f:.3f}  Avg: {avg_f:.3f}  "
              f"All-time: {best_score:.3f}  ({elapsed:.1f}s)")

        # ── Ghi log CSV mỗi generation ──
        # Tính thêm min fitness và diversity (std)
        min_f = min(fitness)
        std_f = (sum((x - avg_f)**2 for x in fitness) / len(fitness)) ** 0.5
        _append_gen_log(log_path, {
            "generation":     gen,
            "best_fitness":   round(max_f, 4),
            "avg_fitness":    round(avg_f, 4),
            "min_fitness":    round(min_f, 4),
            "std_fitness":    round(std_f, 4),
            "alltime_best":   round(best_score, 4),
            "elapsed_sec":    round(elapsed, 2),
            # Ghi snapshot weights của best agent để phân tích sau
            **{f"w_{k}": round(population[best_idx][k], 2) for k in PARAM_KEYS},
        })

        # ── Selection: giữ elite ──
        ranked   = sorted(range(pop_size), key=lambda i: -fitness[i])
        elites   = [copy.deepcopy(population[i]) for i in ranked[:elite_k]]

        # ── Tạo thế hệ mới ──
        new_pop  = list(elites)

        # Thêm 1 agent random hoàn toàn để duy trì diversity
        new_pop.append(random_agent())

        while len(new_pop) < pop_size:
            # Tournament selection (size 3) để chọn cha mẹ
            p1 = _tournament(population, fitness, k=3)
            p2 = _tournament(population, fitness, k=3)
            child = mutate(crossover(p1, p2), mut_rate, mut_str)
            new_pop.append(child)

        population = new_pop

    print("\n" + "=" * 55)
    print("  TRAINING HOÀN TẤT")
    print(f"  Best win-rate: {best_score:.3f}")
    print("=" * 55)
    print("\nBest weights:")
    for k, v in best_ever.items():
        baseline_v = DEFAULT_WEIGHTS.get(k, "?")
        arrow = "↑" if v > baseline_v else "↓" if v < baseline_v else "="
        print(f"  {k:15s}: {v:10.1f}   (baseline: {baseline_v}) {arrow}")

    _save_weights(best_ever, best_score, generations, save_path)
    print(f"\nĐã lưu vào: {save_path}")
    return best_ever, history


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _tournament(population, fitness, k=3):
    """Chọn ngẫu nhiên k agent, trả về agent có fitness cao nhất."""
    candidates = random.sample(range(len(population)), k=min(k, len(population)))
    best       = max(candidates, key=lambda i: fitness[i])
    return copy.deepcopy(population[best])


def _append_gen_log(log_path, row: dict):
    """Ghi thêm 1 dòng stats vào CSV log của quá trình training."""
    import csv
    os.makedirs(os.path.dirname(log_path) if os.path.dirname(log_path) else ".", exist_ok=True)
    file_exists = os.path.isfile(log_path)
    with open(log_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def _save_weights(weights, score, gen, path):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    data = {
        "weights":    weights,
        "win_rate":   round(score, 4),
        "generation": gen,
        "timestamp":  time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_weights(path="logs/best_weights.json"):
    """Load weights đã train để dùng trong game."""
    with open(path) as f:
        data = json.load(f)
    print(f"Loaded weights từ gen {data['generation']}, "
          f"win-rate = {data['win_rate']}")
    return data["weights"]


# ─────────────────────────────────────────────────────────────
# Verify: so sánh trained vs baseline
# ─────────────────────────────────────────────────────────────
def verify_weights(trained_weights, n_games=20, depth=3):
    """
    Cho trained agent đấu với baseline tại depth=3.
    Dùng sau khi train xong để xác nhận kết quả.
    """
    print(f"\n=== VERIFY: Trained vs Baseline ({n_games} ván, depth={depth}) ===")
    wins_trained = wins_base = draws = 0

    for g in range(n_games):
        if g % 2 == 0:
            # Trained = X
            r = play_one_game(trained_weights, DEFAULT_WEIGHTS, depth=depth)
            if r == 1:    wins_trained += 1
            elif r == 2:  wins_base    += 1
            else:          draws       += 1
        else:
            # Trained = O
            r = play_one_game(DEFAULT_WEIGHTS, trained_weights, depth=depth)
            if r == 2:    wins_trained += 1
            elif r == 1:  wins_base    += 1
            else:          draws       += 1

        print(f"  Ván {g+1:2d}: Trained={wins_trained}  Baseline={wins_base}  "
              f"Draw={draws}", end="\r")

    print(f"\n  Kết quả: Trained {wins_trained}W / {draws}D / {wins_base}L "
          f"(win-rate = {wins_trained/n_games:.2f})")
    return wins_trained, draws, wins_base


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Caro AI — GA Trainer")
    parser.add_argument("--quick",   action="store_true",
                        help="Chạy nhanh để test (pop=8, gen=5)")
    parser.add_argument("--verify",  action="store_true",
                        help="Chỉ verify weights đã có (không train lại)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Số CPU worker (mặc định 1)")
    parser.add_argument("--output",  type=str, default="logs/best_weights.json",
                        help="Đường dẫn lưu kết quả weights")
    parser.add_argument("--log",     type=str, default="logs/training_log.csv",
                        help="Đường dẫn lưu CSV log từng generation")
    args = parser.parse_args()

    if args.verify:
        weights = load_weights(args.output)
        verify_weights(weights, n_games=20, depth=3)
        sys.exit(0)

    config = copy.deepcopy(GA_CONFIG)
    if args.quick:
        config.update({
            "population_size":    8,
            "generations":        5,
            "elite_k":            2,
            "opponents_per_agent": 3,
            "train_depth":        2,
        })
        print("[QUICK MODE] Chạy nhanh để kiểm tra pipeline...")

    # Trên Windows cần guard để multiprocessing hoạt động đúng
    best_weights, history = run_ga(
        config    = config,
        n_workers = args.workers,
        save_path = args.output,
        log_path  = args.log,
    )

    # Verify tự động sau khi train
    verify_weights(best_weights, n_games=10, depth=3)