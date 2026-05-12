import sys
import os
import time

# Đảm bảo Python có thể tìm thấy các module trong source/ và gui/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from source.board import Board
from source.AI import CaroAI
from source.utils import log_benchmark_step

def run_console_mode():
    """Chế độ chơi trên Terminal dành cho Người 1 test logic hoặc chơi nhanh."""
    print("\n" + "═"*45)
    print("         CARO AI - CONSOLE TEST MODE")
    print("═"*45)
    
    # 1. Cấu hình ban đầu
    size = 9
    win_condition = 4
    board = Board(size=size, win_condition=win_condition)

    log_file = f"logs/game_console_{int(time.time())}.csv"
    turn_count = 0
    
    print(f"\n[!] Cấu hình: Bàn cờ {size}x{size}, Luật thắng: {win_condition} quân liên tiếp.")
    
    # 2. Chọn độ khó và thuật toán
    try:
        depth_in = input("Chọn độ sâu tìm kiếm (1-4, mặc định 3): ")
        depth = int(depth_in) if depth_in.isdigit() else 3
        
        mode_in = input("Chọn thuật toán (1: Alpha-Beta, 2: Minimax, mặc định 1): ")
        mode = "minimax" if mode_in == "2" else "alpha_beta"

        side_in = input("Bạn muốn chơi quân nào? (1: X - đi trước, 2: O - đi sau, mặc định 1): ")
        user_id = 2 if side_in == "2" else 1
        ai_id = 3 - user_id
    except Exception:
        depth = 3
        mode = "alpha_beta"
        user_id = 1
        ai_id = 2

    ai = CaroAI(player_id=ai_id, depth=depth)
    
    print(f"\n>>> BẮT ĐẦU: Bạn ({'X' if user_id == 1 else 'O'}), AI ({'X' if ai_id == 1 else 'O'}).")
    print(">>> Hệ thống: Nhập 'h c' (ví dụ: 4 4) để đi, 'u' để hoàn tác, 'q' để thoát.")
    print("─" * 45)

    while True:
        board.display()
        win_status = board.check_win()
        
        if win_status != 0:
            if win_status == user_id: print(f"\n🏆 KẾT THÚC: Bạn ({'X' if user_id == 1 else 'O'}) thắng!")
            elif win_status == ai_id: print(f"\n💻 KẾT THÚC: AI ({'X' if ai_id == 1 else 'O'}) thắng!")
            else: print("\n🤝 KẾT THÚC: Hòa!")
            break

        if board.current_player == user_id:
            user_input = input(f"\nLượt của bạn ({'X' if user_id == 1 else 'O'}): ").strip().lower()
            
            if user_input == 'q': break
            if user_input == 'u':
                if board.undo_move(): # Hoàn tác AI
                    board.undo_move() # Hoàn tác người
                    print(">>> Đã hoàn tác nước đi.")
                else:
                    print(">>> Không có nước đi để hoàn tác!")
                continue

            try:
                r, c = map(int, user_input.split())
                if not board.make_move(r, c):
                    print(">>> LỖI: Ô không hợp lệ hoặc đã có quân!")
                else:
                    turn_count += 1
                    log_benchmark_step(log_file, [turn_count, "Human", "-", "-", "-", "-", (r, c)])
            except ValueError:
                print(">>> LỖI: Nhập đúng định dạng 'hàng cột' (VD: 4 4)")
        else:
            print(f"\nAI (O) đang suy nghĩ (Mode: {mode}, Depth: {depth})...")
            move, score, nodes, duration = ai.get_move(board, mode=mode, time_limit=5.0)
            
            if move:
                board.make_move(*move)
                turn_count += 1
                log_benchmark_step(log_file, [turn_count, mode, depth, nodes, f"{duration:.4f}", score, move])
                print(f">>> AI đã đi vào ô {move}")
                print(f">>> Thống kê: Duyệt {nodes} nodes | {duration:.4f}s | Score: {score}")
            else:
                print(">>> AI không tìm thấy nước đi hợp lệ.")
                break

    print("\nCảm ơn bạn đã trải nghiệm chế độ Console!")

def main():
    """
    Điểm khởi chạy chính. 
    Tự động chuyển sang Terminal nếu không thể khởi động giao diện đồ họa.
    """
    if "--console" in sys.argv:
        run_console_mode()
        return

    try:
        # Thêm phần chọn quân trước khi vào GUI
        print("\n" + "═"*45)
        print("         CHỌN QUÂN CHƠI (Giao diện đồ họa)")
        print("═"*45)
        side_in = input("Bạn muốn chơi quân nào? (1: X - đi trước, 2: O - đi sau, mặc định 1): ")
        user_id = 2 if side_in == "2" else 1
        ai_id = 3 - user_id

        # Thử khởi chạy GUI
        from gui.interface import CaroGUI
        size = 9
        win_condition = 4
        board = Board(size=size, win_condition=win_condition)
        ai = CaroAI(player_id=ai_id, depth=3)
        app = CaroGUI(board=board, ai=ai)
        app.run()
    except Exception as e:
        # Nếu có bất kỳ lỗi nào (thiếu pygame, lỗi driver, v.v.)
        print(f"\n[!] Không thể chạy giao diện đồ họa (Lỗi: {e})")
        print("    Đang chuyển sang chế độ chơi trong Terminal...\n")
        run_console_mode()

if __name__ == "__main__":
    main()