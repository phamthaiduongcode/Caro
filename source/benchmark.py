import sys
import os

# Đảm bảo import được từ source/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from source.board import Board
from source.AI import CaroAI
from source.utils import log_benchmark_step

# 1. Định nghĩa 6 trạng thái bàn cờ (Mô phỏng thông qua danh sách tọa độ nước đi)
# Lượt đi sẽ tự động luân phiên: Nước 1(X), Nước 2(O), Nước 3(X)...
STATES = {
    "1. Dau van": [
        (4, 4) 
        # Chỉ có 1 nước ở giữa bàn, lượt tiếp theo là O.
    ],
    "2. Giua van": [
        (4, 4), (4, 5), 
        (3, 4), (5, 5), 
        (3, 5), (5, 4)
        # Các nước đan xen, chưa ai có lợi thế lớn, lượt của X.
    ],
    "3. May thang ngay (AI la X)": [
        (4, 2), (5, 2), 
        (4, 3), (5, 3), 
        (4, 4), (5, 4)
        # X đã có (4,2), (4,3), (4,4) hở 2 đầu. Tới lượt X, X chắc chắn thắng.
    ],
    "4. Nguoi choi sap thang (May la O phai chan)": [
        (4, 2), (2, 2), 
        (4, 3), (2, 3), 
        (4, 4)
        # X có 3 quân liên tiếp, tới lượt O bắt buộc phải đánh chặn.
    ],
    "5. Hai ben cung tan cong": [
        (2, 3), (2, 5), 
        (3, 3), (3, 5), 
        (5, 2), (5, 6)
        # Cả X và O đều đang xây dựng đường tấn công riêng.
    ],
    "6. Nhieu nuoc di hop le (Nhanh phuc tap)": [
        (4, 4), (3, 3), 
        (5, 5), (2, 2), 
        (3, 5), (5, 3), 
        (4, 2), (4, 6), 
        (2, 4), (6, 4)
        # Quân cờ tản mác khắp bàn, số lượng ô ứng viên (candidates) rất lớn.
    ]
}

def run_benchmark():
    log_file = "logs/logs_benchmark.csv"
    board_size = 9
    win_condition = 4
    
    # Test trên các độ sâu khác nhau (từ 1 đến 4)
    # Lưu ý: Nếu Depth quá cao (>=5), Minimax sẽ chạy cực kỳ lâu ở State 6.
    test_depths = [2, 3, 4] 
    algorithms = ["minimax", "alpha_beta"]

    print(f"=== BẮT ĐẦU BENCHMARK 2 THUẬT TOÁN ===")
    print(f"Dữ liệu sẽ được ghi vào: {log_file}\n")

    for state_name, moves in STATES.items():
        print(f"Đang xử lý: {state_name} ...")
        
        # Tạo lại bàn cờ cho mỗi trạng thái
        for depth in test_depths:
            for algo in algorithms:
                
                # 1. Khởi tạo bàn cờ và giả lập các nước đi
                board = Board(size=board_size, win_condition=win_condition)
                for r, c in moves:
                    board.make_move(r, c)
                
                # Xác định lượt hiện tại (dựa vào số nước đi chẵn/lẻ)
                turn = len(moves) + 1
                current_player = board.current_player
                
                # 2. Khởi tạo AI
                ai = CaroAI(player_id=current_player, depth=depth)
                
                # 3. Chạy thuật toán để tìm nước đi
                # time_limit=None để ép thuật toán chạy hết độ sâu thay vì bị ngắt giữa chừng
                best_move, best_score, nodes_visited, duration = ai.get_move(
                    board=board, 
                    mode=algo, 
                    time_limit=None 
                )

                # 4. Lưu lại kết quả theo đúng cấu trúc của hàm log_benchmark_step
                # ['Turn', 'Algorithm', 'Depth', 'Nodes_Visited', 'Time_Seconds', 'Score', 'Move']
                log_data = [
                    f"{state_name} (Turn {turn})",
                    algo,
                    depth,
                    nodes_visited,
                    round(duration, 4),
                    best_score,
                    str(best_move)
                ]
                log_benchmark_step(log_file, log_data)

if __name__ == "__main__":
    run_benchmark()