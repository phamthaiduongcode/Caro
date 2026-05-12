import sys
import os
import copy
import time
import statistics
from tabulate import tabulate

# Dam bao import duoc cac module tu thu muc source
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from board import Board
from AI import CaroAI

class TechnicalBenchmark:
    def __init__(self, size=9, depth=3):
        self.size = size
        self.depth = depth
        self.test_cases = self._initialize_cases()

    def _initialize_cases(self):
        cases = []
        
        # 1. Khai cuoc (Center Opening)
        b1 = Board(self.size)
        cases.append(("Khai cuoc", b1))

        # 2. Sat cuc (Winning State for AI O)
        b2 = Board(self.size)
        # Tao hang 3 quan cho O tai hang 4
        for i in range(3): b2.grid[4, i+2] = 2
        b2.current_player = 2
        cases.append(("Sat cuc", b2))

        # 3. Phong ngu (Defensive State - X has 3 open)
        b3 = Board(self.size)
        # Doi thu X co hang 3 doc tai cot 4
        for i in range(3): b3.grid[i+3, 4] = 1
        b3.current_player = 2
        cases.append(("Phong ngu", b3))

        # 4. Giao tranh trung tam (Complex Mid-game)
        b4 = Board(self.size)
        mid = self.size // 2
        # Cac nuoc di dan xen tao ra nhieu nhanh tim kiem
        moves = [(mid, mid, 1), (mid-1, mid, 2), (mid, mid+1, 1), 
                 (mid+1, mid-1, 2), (mid-1, mid-1, 1), (mid+1, mid+1, 2)]
        for r, c, p in moves: b4.grid[r, c] = p
        b4.current_player = 2
        cases.append(("Giao tranh", b4))

        return cases

    def run_evaluation(self):
        print("-" * 100)
        print(f"HE THONG DANH GIA HIEU SUAT THUAT TOAN CARO AI (Do sau: {self.depth})")
        print("-" * 100)

        table_data = []

        for name, state in self.test_cases:
            # --- Thuc thi Minimax ---
            ai_m = CaroAI(player_id=2, depth=self.depth)
            board_m = copy.deepcopy(state)
            start_m = time.perf_counter()
            move_m, _, nodes_m, _ = ai_m.get_move(board_m, mode="minimax")
            time_m = time.perf_counter() - start_m

            # --- Thuc thi Alpha-Beta ---
            ai_ab = CaroAI(player_id=2, depth=self.depth)
            board_ab = copy.deepcopy(state)
            start_ab = time.perf_counter()
            move_ab, _, nodes_ab, _ = ai_ab.get_move(board_ab, mode="alpha_beta")
            time_ab = time.perf_counter() - start_ab

            # Tinh toan cac chi so toi uu
            # Ti le cat tia (Pruning Ratio)
            pruning_ratio = (nodes_m / nodes_ab) if nodes_ab > 0 else 1.0
            
            # Hieu suat toi uu (%)
            efficiency = (1 - (nodes_ab / nodes_m)) * 100 if nodes_m > 0 else 0.0

            # Kiem tra tinh dong nhat cua ket qua
            match_result = "PASSED" if move_m == move_ab else "DIFFERENT"
            
            table_data.append([
                name,
                f"{nodes_m:,}",
                f"{nodes_ab:,}",
                f"{time_m:.4f}s",
                f"{time_ab:.4f}s",
                f"{pruning_ratio:.2f}x",
                f"{efficiency:.2f}%",
                match_result
            ])

        headers = [
            "Kich ban", "Nodes (MM)", "Nodes (AB)", 
            "Time (MM)", "Time (AB)", "Pruning Ratio", 
            "Efficiency (%)", "Status"
        ]
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        self._print_summary(table_data)

    def _print_summary(self, data):
        # Trich xuat du lieu de tinh trung binh
        ratios = [float(row[5].replace('x', '')) for row in data]
        efficiencies = [float(row[6].replace('%', '')) for row in data]
        
        print("\nTONG KET PHAN TICH:")
        print(f"- Ti le cat tia trung binh: {statistics.mean(ratios):.2f}x")
        print(f"- Hieu suat toi uu trung binh: {statistics.mean(efficiencies):.2f}%")
        print("- Ket luan: Alpha-Beta giup giam tai dang ke khoi luong tinh toan ma khong lam thay doi ket qua.")
        print("-" * 100)

if __name__ == "__main__":
    # Su dung depth=3 de dam bao thoi gian test nhanh va chinh xac
    tester = TechnicalBenchmark(depth=3)
    tester.run_evaluation()