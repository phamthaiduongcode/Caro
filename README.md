# Caro
Gomoku (Caro) AI Project

## Cấu trúc thư mục
- `play.py`: Điểm khởi chạy chương trình.
- `requirements.txt`: Các thư viện cần thiết.
- `source/`: Chứa logic xử lý trò chơi và AI.
    - `board.py`: Logic bàn cờ và luật chơi.
    - `AI.py`: Thuật toán Minimax, Alpha-Beta Pruning.
    - `utils.py`: Tiện ích lưu log CSV.
    - `benchmark.py`: So sánh hiệu năng giữa các thuật toán.
- `gui/`: Giao diện người dùng.
    - `interface.py`: Xử lý giao diện chính bằng Pygame.
    - `button.py`: Widget nút bấm.
    - `analysis.py`: Vẽ biểu đồ kết quả benchmark.
- `logs/`: Chứa các file log kết quả (tự động tạo).
- `experiments/`: Chứa hình ảnh kết quả thực nghiệm.

## Hướng dẫn cài đặt
```bash
pip install -r requirements.txt
python play.py
```
