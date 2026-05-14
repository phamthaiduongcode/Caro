import csv
import os

def log_game_result(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Timestamp', 'Winner', 'Moves', 'Duration'])
        writer.writerow(data)

def log_benchmark_step(file_path, data):
    """Ghi log chi tiết từng bước đi cho mục đích benchmark."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file_exists = os.path.isfile(file_path)
    with open(file_path, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Turn', 'Algorithm', 'Depth', 'Nodes_Visited', 'Time_Seconds', 'Score', 'Move'])
        writer.writerow(data)