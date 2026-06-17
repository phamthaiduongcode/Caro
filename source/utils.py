import csv
import os

def log_game_result(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Winner', 'Moves', 'Duration'])
        writer.writerow(data)

def log_benchmark_step(file_path, data):
    """Ghi log chi tiết từng bước đi cho mục đích benchmark."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Turn', 'Algorithm', 'Depth', 'Nodes_Visited', 'Time_Seconds', 'Score', 'Move'])
        writer.writerow(data)

def log_ai_move(file_path, data):
    """Ghi log chi tiết từng nước đi của AI vào file csv."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Player', 'Move', 'Score', 'Nodes', 'Time_Seconds', 'Depth'])
        writer.writerow(data)

def pop_last_log_lines(file_path, count):
    """Xóa n dòng cuối cùng khỏi file log (dùng khi Undo)."""
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if len(lines) > count:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                f.writelines(lines[:-count])
    except: pass
